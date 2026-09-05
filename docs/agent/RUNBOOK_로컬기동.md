# GuardianX 로컬 100% 기동 런북 — Code 실행용
**발행** 2026-08-16 · **대상** Claude Code (대표 PC에서 실행)
**전제(대표 증언)**: 운영환경은 `C:\GuardianX\GuardianX build` + `C:\GuardianX\guardianx-source` 두 폴더만으로 100% 세팅됐고, 두 곳 내용은 같다.

> **목표 한 문장**: 이 PC에서 `manage.py check` → 백엔드 기동 → 프론트 기동 → 로그인 화면까지.
> 이것이 되면 **동결(D-236)이 해제**되고, 미검증 재고 1,217줄을 전부 검증한다.
> **FREEZE 예외 승인**: 이 런북 실행은 D-236의 "조사·측정" + "환경 복구"로 허용한다. 소스 수정은 여전히 금지.

---

## STEP 1 — `GuardianX build` 인벤토리 (15분)

대표 증언이 사실이라면 잠긴 패키지 3개(dj-core·rj-core·gcs-fe)의 **설치본 또는 사본이 이 폴더 안에 있어야 한다.** 찾아라.

```powershell
cd "C:\GuardianX\GuardianX build"
# ① 파이썬 쪽 — dj-core 흔적
Get-ChildItem -Recurse -Depth 6 -Include "dj_core*","dj-core*","core" -Directory | Select FullName
Get-ChildItem -Recurse -Include "*.whl","*.tar.gz" | Select FullName
Get-ChildItem -Recurse -Include "site-packages" -Directory | Select FullName   # venv 통째로 있는지
# ② 노드 쪽 — rj-core / gcs-fe
Get-ChildItem -Recurse -Depth 6 -Include "rj-core","gcs-fe" -Directory | Select FullName
Get-ChildItem -Recurse -Include "node_modules" -Directory -Depth 4 | Select FullName
# ③ 도커 쪽 — 이미지/컴포즈
Get-ChildItem -Recurse -Include "*.tar","Dockerfile","docker-compose*" | Select FullName
# ④ minio.tar 등 데이터
Get-ChildItem -Recurse -Include "*.sql","*.dump","minio*" | Select FullName
```

**판정표** — 발견물에 따라 경로가 갈린다:

| 발견 | 경로 |
|---|---|
| `site-packages/core/base.py` 또는 dj-core wheel | **A: 그대로 이식** — STEP 2A |
| venv 통째 (python.exe 포함) | **A′: venv 재사용** — 버전 확인 후 STEP 2A |
| `node_modules/rj-core` + `node_modules/@gaion/gcs-fe` | 프론트 해결 — STEP 3 에서 복사 |
| 도커 이미지 tar | **B: 이미지 로드** — `docker load` 후 컨테이너에서 추출 |
| 셋 다 없음 | **대표 증언과 불일치.** 무엇이 있는지 목록만 보고하고 STOP — 이때만 운영서버 추출로 회귀 |

⚠️ **찾은 사본은 즉시 3중 백업** (`C:\GuardianX-vault\` 신설 + 클라우드 + 외장매체). 저장소 안에는 넣지 않는다(D-002).

## STEP 2A — 백엔드 기동 (30분)

```powershell
cd C:\GuardianX\guardianx-source\backend
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
# dj-core 를 먼저 — wheel 이면:
pip install <발견한 dj-core wheel 경로>
# site-packages 사본이면: 사본의 core/, 그리고 dj-core 의존 패키지들을 .venv Lib\site-packages 로 복사
pip install -r requirements.txt --no-deps 실패시 개별 처리   # dj-core 줄은 주석 처리(이미 설치됨)
python -c "import core.base; import core.user.models; print('dj-core OK')"   # ★ 관문
python manage.py check
```
- DB: Docker 가능하면 `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=devonly --log-opt max-size=10m --log-opt max-file=5 postgres:16` / 불가하면 Windows Postgres 설치.
- ⚠ **`docker run` 으로 띄우는 컨테이너에는 `--log-opt` 를 반드시 붙인다** (OPS-07 · 2026-09-24).
  `docker-compose.yml` 의 `logging` 선언은 **compose 가 만든 컨테이너에만** 닿는다.
  손으로 띄운 컨테이너(`postgres` · `gx-fe-build` · `gx-shell`)는 그 선언 밖이고,
  `max-size` 가 없으면 도커는 **자르지 않는다** — 디스크가 찰 때까지 쌓인다
  ([실측] `scripts/ops_log_collectors.py` 가 그 상태를 빨강으로 찍는다).
  값은 compose 와 **같은 값**을 쓴다: `--log-opt max-size=10m --log-opt max-file=5`
  (컨테이너당 상한 50MB. 근거는 `docker-compose.yml` 머리말).
- `.env` 는 `.env.example` 복사 후 로컬값. **외부 `*.gaion.dev` 의존(AI·MinIO·OpenSearch)은 전부 비우거나 더미로** — 기동 목표에 불필요. 죽는 지점이 있으면 해당 기능만 설정으로 끄고 기록.
- `python manage.py migrate` → `runserver` → `http://localhost:8000` 응답 확인.

## STEP 2B — 로그 상한을 **실제로 걸기** (OPS-07 · 2026-09-05 · 턴 D)

> **「선언이 섰다」는 「보존이 걸렸다」가 아니다.** 도커의 `LogConfig` 는 컨테이너를
> **만들 때** 굳는다 — compose 를 고쳐도, `--log-opt` 를 RUNBOOK 에 적어도, **이미
> 떠 있는 컨테이너에는 닿지 않는다.** 이 절의 유일한 적용 방법은 **다시 만드는 것**이다.

### 지금 어디가 걸려 있고 어디가 안 걸려 있나 — 먼저 재라

```powershell
python scripts/ops_log_collectors.py          # exit 0 통과 · 1 실패 · 2 못 쟀다
for c in $(docker ps --format '{{.Names}}'); do
    echo -n "$c "; docker inspect -f '{{json .HostConfig.LogConfig}}' $c
done
```

### 상한을 거는 세 가지 자리 — **셋 다 다르다**

| 어떻게 뜬 컨테이너 | 상한이 사는 자리 | 적용되는 때 |
|---|---|---|
| compose 가 만든 것 | `docker-compose*.yml` 의 `logging: *gx-logging` | **다음 `up`(재생성) 때** |
| `docker run` 으로 띄운 것 | **그 명령줄의 `--log-opt`** | 그 명령을 다시 칠 때 |
| 컨테이너 **안에서 파일로** 쌓는 것 | **어디에도 없다** — 위 둘이 안 닿는다 | 걸리지 않는다 |

⚠ 셋째 줄이 이 절에서 가장 놓치기 쉬운 자리다. [실측 2026-09-05] 앞단 `gx-nginx-e` 는
`access_log /var/log/nginx/gx-front.access.log` 로 **컨테이너 안의 파일**에 적는다.
`--log-opt` 를 붙여 띄웠어도 그 파일에는 아무 상한이 없고, `nginx:alpine` 에는
logrotate 도 없다. **컨테이너에 상한을 걸었다 ≠ 그 컨테이너의 로그에 상한이 걸렸다.**

### compose 밖 컨테이너를 compose 안으로 들이는 절차 (postgres 기준)

`docker-compose.yml` 에 `postgres` 서비스를 **선언해 두었다**(`profiles: ["local"]`).
적용은 **재생성**이므로 아래 절차가 필요하다:

```bash
# ① 자료가 이름 붙인 볼륨에 있는지 먼저 확인한다 — 없으면 여기서 멈춘다
docker volume inspect gx_pgdata

# ② 뿌리 .env 에 POSTGRES_PASSWORD 를 넣는다 (없으면 compose 가 그 자리에서 멈춘다)

# ③ 지금 것을 내리고 compose 로 다시 만든다  ⚠ 여기서 연결이 끊긴다
docker rm -f postgres
docker compose --profile local up -d postgres

# ④ 이 기계의 컨테이너는 손으로 만든 망 위에 있다 — 한 번 더 이어 준다
docker network connect --alias postgres gx-main-network guardianx-source-postgres-1

# ⑤ 걸렸는지 **재서** 확인한다 (선언이 아니라 적용을 본다)
docker inspect -f '{{json .HostConfig.LogConfig}}' guardianx-source-postgres-1
```

⛔ **2026-09-05 에는 ③을 하지 않았다.** 그 순간 `gx-shell` 안에서 다른 차선 셋이
시험 DB(`test_gx_*`)를 만들고 지우는 중이었고, postgres 를 내리면 그 셋이 한꺼번에
죽는다. **재기동이 필요한 조치를 「했다」로 적지 않는다** — 절차를 남기고 왜 안 했는지를
적는 것이 정직한 산출이다(조율자 지시 · 턴 D).

### 손으로 띄우는 컨테이너 — 명령 그대로

```bash
docker run -d --name postgres --log-opt max-size=10m --log-opt max-file=5 …
docker run -d --name gx-fe-build --log-opt max-size=10m --log-opt max-file=5 …
docker run -d --name gx-shell   --log-opt max-size=10m --log-opt max-file=5 …
```

값은 compose 와 **같은 값**을 쓴다(컨테이너당 상한 50MB · 근거는 `docker-compose.yml`
머리말). 두 벌로 적으면 어긋나고, 어긋난 뒤에는 어느 쪽이 정본인지 아무도 모른다.

### ★ 정본은 무엇인가 — **한 문장**

> **감사에 답하는 것은 DB 감사 로그(`logger_auditlogs`)이고, 컨테이너 stdout 은
> 운영 디버깅용 단기 버퍼다.**

그리고 그 정본에는 조건이 하나 붙는다 — **지우는 자리가 실제로 돌 때만** 90일이
90일이다. [실측 2026-09-05] 이 기계에는 celery 워커가 **0개**다(브로커는 살아 있다).
beat 일정 `ops-audit-purge-daily` 는 `config/celery.py` 에 적혀 있지만 그것을 실행할
워커가 없으므로 **이 환경에서는 아무것도 안 지워진다.** `ops_log_collectors.py` 가
이제 그 자리를 따로 재고 빨강으로 찍는다 — **선언은 삭제가 아니다.**

## STEP 3 — 프론트 기동 (20분)

```powershell
cd C:\GuardianX\guardianx-source\frontend
npm install   # rj-core/gcs-fe 에서 실패하면:
#   발견한 node_modules 사본에서 node_modules\rj-core, node_modules\@gaion 을 통째로 복사한 뒤
#   package.json 의 두 줄을 "file:./vendor/rj-core" 방식으로 바꾸지 말고 — 소스 수정 금지 —
#   npm install --ignore-scripts 후 사본 덮어쓰기로 우회. 방법과 결과를 기록.
npm run dev   # 로그인 화면 뜨면 성공
```

## STEP 4 — 검증 대개방 (동결 해제 조건)

```powershell
python manage.py test tests.test_route_tenant_scope -v 2      # 미검증 재고 — EXIT §8 예상표와 대조
python manage.py test tests.test_tenant_isolation -v 2
python manage.py makemigrations stream_monitors --dry-run     # W2-1
```
결과를 `review/LOCAL_BRINGUP_결과.md` 에 기록: 각 단계 실제 명령·출력, 예상 대비 차이, 우회한 것 목록.
**여기까지 green 이면 WP-0·WP-1 EXIT 를 갱신 재제출하고 멈춘다.** 동결 해제는 대표 승인으로.

## STEP 5 — 부수 확인 (10분)

- `GuardianX build` 와 `guardianx-source` 가 "같은 내용"인지 **diff 로 실측** — 코드 부분만: `git diff --no-index` 요약. 다르면 무엇이 다른지 10줄 이내 보고 (운영서버 대조의 대체재).
- 발견한 사본의 dj-core 버전 문자열 기록 (향후 탈출 설계의 기준점).
