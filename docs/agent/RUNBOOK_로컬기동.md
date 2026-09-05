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
90일이다. [실측 2026-09-05 오전] 이 기계에는 celery 워커가 **0개**였다(브로커는 살아
있었다). beat 일정 `ops-audit-purge-daily` 는 `config/celery.py` 에 적혀 있지만 그것을
실행할 워커가 없으므로 **이 환경에서는 아무것도 안 지워졌다.** `ops_log_collectors.py` 가
이제 그 자리를 따로 재고 빨강으로 찍는다 — **선언은 삭제가 아니다.**

> ⛔ **위 문단은 2026-09-05 17:36 에 절반이 옛말이 됐다. 지우지 않고 남긴다.**
> P-56 이 워커 1(`gx-celery-e`) · beat 1(`gx-beat-e`) 을 세웠다. 그러나
> **결론은 그대로다 — 여전히 아무것도 안 지워진다.** 사유만 바뀌었다:
> 「워커가 없어서」가 아니라 **「파기 항목을 DB 주기 표에서 꺼 두었기 때문」**이다
> (보존 일수 미선언 테넌트를 파기 대상에서 빼는 판정이 아직 없다 · P-57 대기).
> 그러므로 **워커가 섰다는 것을 「보존이 걸렸다」로 읽지 마라** — 그것이 이 절이
> 처음부터 경계한 바로 그 착각이고, 이번에는 착각의 재료만 바뀌었다.
> 켜는 조건과 명령은 `docker-compose.yml` 의 `beat` 서비스 머리말에 있다.
> 세우면서 실제로 벌어진 일(기동 즉시 14개 발화 · 3일치 12,468건 밀린 큐)은
> `docs/agent/evidence/P-56/` 에 있다.

## STEP 2C — 프런트 빌드 전에 **소스를 넣는다** (P-59 · 2026-09-05 턴 E)

> **`gx-fe-build` 의 `/app` 은 저장소를 물고 있지 않다 — 자기 사본이다.**
> 넣지 않고 빌드하면 그 `exit 0` 은 **직전 턴의 코드를 빌드한 것**이고,
> 이번 턴에 대해 아무 말도 하지 않는다. 턴 D 에서 조율자가 실제로 그 초록을 냈다.

```bash
# ① 소스와 설정을 넣는다 — 없으면 아래 exit 0 은 직전 턴 코드에 대한 것이다
docker cp frontend/src/. gx-fe-build:/app/src/
docker cp frontend/vite.config.ts gx-fe-build:/app/vite.config.ts

# ② 커밋 해시를 넘긴다 (P-59) — 컨테이너에는 `.git` 이 없어 스스로 알아낼 수 없다.
#    ⚠ 40자리를 넘긴다. `--short` 는 부딪힐 수 있고, 부딪히는 신원은 신원이 아니다.
docker exec -e NODE_OPTIONS=--max-old-space-size=6144 -e GX_COMMIT=$(git rev-parse HEAD)     gx-fe-build sh -c 'cd /app && npx vite build --outDir dist_te'

# ③ **배치** — 3002 를 내주는 것은 gx-shell 의 /app/_fe_dist 다(spa_server.py).
#    빌드만 하고 여기를 안 갈면 화면은 옛것 그대로다 — 턴 E 에 그 상태로 하루가 갔다.
docker exec gx-fe-build sh -c 'cd /app && tar cf - dist_te' | docker exec -i gx-shell sh -c     'rm -rf /app/_fe_dist_new && mkdir -p /app/_fe_dist_new && tar xf - -C /app/_fe_dist_new --strip-components=1 &&      rm -rf /app/_fe_dist && mv /app/_fe_dist_new /app/_fe_dist'

# ④ **적용을 잰다** — exit 0 은 무엇이 성공했는지 말해 주지 않는다
python scripts/verify_bundle_hash.py --dist <배치된 자리>     # 서버가 내는 번들 = 현재 커밋
```

> **순서가 곧 내용이다**: 커밋 → 빌드(새 HEAD) → 배치 → 잰다.
> 커밋 전에 빌드하면 그 번들은 태어나자마자 옛것이고, 게이트가 그것을 빨강으로 낸다.

마지막 줄이 이 절차의 핵심이다 — **`exit 0` 은 무엇이 성공했는지 말해 주지 않는다.**
번들 안에 이번 턴의 이름이 실재하는지 눈으로 본다. (게이트로도 잰다: `verify_bundle_hash.py`)

## STEP 2D — 재기동 창 **한 덩이** (P-55 · OPS-07 적용 · 2026-09-05 턴 E)

> **이 절은 「했다」가 아니라 「할 것」이다.** 2026-09-05 턴 E 에는 실행하지 않았다 —
> 그 시각 다섯 차선이 `gx-shell` 안에서 시험 DB(`test_gx_*`)를 만들고 지우는 중이었고,
> `postgres` 를 내리면 다섯이 한꺼번에 죽는다(지시서 §4 함정 ④).
> **조율자가 병합 직후 · 다른 에이전트 정지 뒤 · 15분 창에서** 아래를 통째로 붙여 넣는다.

### 왜 재기동 말고는 방법이 없나

도커의 `LogConfig` 는 컨테이너를 **만들 때** 굳는다. `docker update` 에 로그 옵션은
없고, compose 의 `logging:` 선언도 **다음 재생성** 때 닿는다. 그래서 이 절의 유일한
적용 방법은 **다시 만드는 것**이다.

### 지금 상태 [실측 2026-09-05 · `docs/agent/evidence/OPS-07/logcap_by_container.txt`]

| 컨테이너 | 상한 | 이 절에서 |
|---|---|---|
| `gx-nginx-e` · `gx-gunicorn-e` · `gx-celery-e` · `gx-beat-e` | **10m × 5 걸림** | 건드리지 않는다 |
| `gx-shell` · `postgres` · `redis` · `guardianx-source-minio-1` · `gx-fe-build` | **없음(무한)** | 아래에서 다시 만든다 |

⚠ `gx-nginx-e` 는 **재기동하지 않는다.** QA/E2E 차선이 8500 으로 부하를 내고 있고,
앞단을 내리면 그의 측정이 끊긴다. 앞단에 필요한 것은 재기동이 아니라 **reload** 하나다
(아래 ⑦ — `nginx/gx-front.conf` 의 `access_log` 를 stdout 으로 바꿔 두었다. 선언은
섰고 **적용은 reload 때**다).

---

### ⓪ 창을 열기 전 — **확인 셋**. 하나라도 아니면 멈춘다

```bash
# ㉠ 다른 차선이 정말 멈췄나 — 시험 DB 에 붙어 있는 연결이 0 이어야 한다
docker exec postgres psql -U postgres -t -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname LIKE 'test_gx%' OR datname LIKE 'test_database%'"

# ㉡ 자료가 **이름 붙은 볼륨**에 있나 — 없으면 여기서 멈춘다 (익명 볼륨이면 재생성 = 소실)
docker volume inspect gx_pgdata > /dev/null && echo "gx_pgdata OK"
docker inspect redis --format '{{range .Mounts}}{{.Name}}{{end}}'   # ← 이 이름을 ③에서 쓴다

# ㉢ 스냅샷 (D-002 · D-283) — 되돌릴 수 없는 조치 앞에는 반드시
docker exec postgres pg_dump -U postgres -Fc database_guardianx > /c/GuardianX-vault/gx_$(date +%Y%m%d_%H%M).dump
ls -l /c/GuardianX-vault/ | tail -2
```

### ① 지금 형상을 **파일로 뜬다** — 손으로 다시 치지 않는다

컨테이너의 환경변수에는 자격증명이 들어 있다. **저장소 밖**에 뜬다(D-204).

```bash
mkdir -p /c/GuardianX-vault/recreate && cd /c/GuardianX-vault/recreate
for c in gx-shell postgres redis gx-fe-build; do
  docker inspect $c --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | grep -vE '^(PATH|LANG|HOME|HOSTNAME|GPG_KEY|PYTHON_VERSION|PYTHON_SHA256|LD_LIBRARY_PATH|GOSU_VERSION|PG_MAJOR|PG_VERSION|REDIS_DOWNLOAD_URL|REDIS_DOWNLOAD_SHA|NODE_VERSION|YARN_VERSION)=' \
    | grep -v '^$' > $c.env
  docker inspect $c > $c.json            # 마운트·포트·망을 되짚을 원본
  echo "$c: $(wc -l < $c.env) vars"
done
```

### ② `gx-shell` — 다시 만든다 (자동 migrate 를 **끊은 채로**)

⚠ `--entrypoint sleep` 이 이 컨테이너의 존재 이유다. 이미지의 `ENTRYPOINT` 는
무조건 `manage.py migrate` 를 돌고, 그것이 2026-08-27 에 D-283 절차 **전에**
마이그레이션 4건을 적용시킨 사고의 원인이다(`docker-compose.yml` 의 `shell` 서비스 머리말).

```bash
docker rm -f gx-shell
MSYS_NO_PATHCONV=1 docker run -d --name gx-shell \
  --network gx-main-network \
  --env-file /c/GuardianX-vault/recreate/gx-shell.env \
  -v C:/GuardianX/guardianx-source/backend:/app \
  -v C:/GuardianX/guardianx-source/scripts:/repo/scripts:ro \
  -v C:/GuardianX/guardianx-source/backend:/repo/backend:ro \
  -v C:/GuardianX/guardianx-source/docs:/docs \
  -w /app --entrypoint sleep \
  --log-opt max-size=10m --log-opt max-file=5 \
  guardianx-backend:latest infinity
```

### ③ `redis` — 다시 만든다 (**볼륨 이름을 ⓪㉡ 에서 읽은 것으로**)

⚠ redis 는 브로커다. 익명 볼륨을 안 물려 주면 **큐에 남은 작업이 사라진다.**
[실측 2026-09-05 17:40] 워커가 0개이던 3일 동안 이 큐에 **12,468건**이 쌓여 있었고,
그 전부가 감사 로그 쓰기(`core.logger.tasks.task_add_log`)였다 — 볼륨을 잃으면
그만큼의 감사 기록이 사라진다. 그러므로 **먼저 큐를 비운다**:

```bash
docker exec redis redis-cli LLEN "default"$'\x06\x16'"9"   # ← 0 이 될 때까지 기다린다
VOL=$(docker inspect redis --format '{{range .Mounts}}{{.Name}}{{end}}')
docker rm -f redis
MSYS_NO_PATHCONV=1 docker run -d --name redis \
  --network gx-main-network -v $VOL:/data \
  --log-opt max-size=10m --log-opt max-file=5 \
  redis:latest
```

> ⓘ 큐 이름이 왜 이렇게 생겼나: celery 의 우선순위 큐는 `default` 뒤에
>   구분자 `\x06\x16` 와 우선순위 숫자가 붙는다. `LLEN default` 로 재면
>   **언제나 0** 이 나오고, 그 0 을 「큐가 비었다」로 읽으면 12,468건을 못 본다.
>   [실측] 이 함정에 2026-09-05 에 한 번 걸렸다.

### ④ `postgres` — 다시 만든다 (⚠ **여기서 모든 연결이 끊긴다**)

```bash
docker rm -f postgres
MSYS_NO_PATHCONV=1 docker run -d --name postgres \
  --network gx-main-network -p 5433:5432 \
  --env-file /c/GuardianX-vault/recreate/postgres.env \
  -e PGDATA=/var/lib/postgresql/18/docker \
  -v gx_pgdata:/var/lib/postgresql \
  --log-opt max-size=10m --log-opt max-file=5 \
  postgres:latest
```

> ⓘ `docker-entrypoint-initdb.d` 의 두 스크립트는 **다시 물리지 않는다.** 그것은
>   빈 데이터 디렉터리에서만 도는 초기 적재본이고, `gx_pgdata` 에 이미 자료가 있으므로
>   도커가 무시한다. 물려 봐야 아무 일도 안 하고, 안 물린다고 없어지는 것도 아니다.

### ⑤ `gx-fe-build` — 다시 만든다 (마운트 없음 · 기본 bridge)

⚠ 이 컨테이너의 `/app` 은 저장소를 **물고 있지 않다 — 자기 사본이다.** 다시 만들면
사본이 처음으로 돌아간다. 그러므로 재생성 뒤에는 **반드시 STEP 2C 를 다시 밟는다**
(`docker cp frontend/src/. gx-fe-build:/app/src/`). 그 줄을 빠뜨리면 다음 빌드의
`exit 0` 은 이번 턴에 대해 아무 말도 하지 않는다(P-59 거짓 초록).

```bash
docker rm -f gx-fe-build
MSYS_NO_PATHCONV=1 docker run -d --name gx-fe-build \
  -w /app --entrypoint sleep \
  --log-opt max-size=10m --log-opt max-file=5 \
  guardianx-frontend:latest infinity
```

### ⑥ `minio` — **compose 가 만든 것이므로 compose 로** 다시 만든다

이 하나만 compose 라벨을 갖고 있다. 그리고 이 기계의 나머지는 손으로 만든
`gx-main-network` 위에 있으므로 **망을 한 번 더 이어 준다** — `minio` 별칭이 없으면
뒷단이 객체저장소를 못 찾고, 그때 `/api/media-data` 두 자리가 **500** 이 되며
화면은 그 500 을 「0 of 0」으로 그린다(D-378).

```bash
docker compose up -d --force-recreate minio          # 뿌리 .env 에 MinIO 자격증명 필요
docker network connect --alias minio gx-main-network guardianx-source-minio-1
```

### ⑦ 앞단 — **재기동이 아니라 reload 하나** (QA 측정을 끊지 않는다)

```bash
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e nginx -t -c /etc/nginx/gx/gx-front.conf   # 먼저 문법
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e nginx -s reload -c /etc/nginx/gx/gx-front.conf
```

---

### ⑧ 확인 — **선언이 아니라 적용을 본다**

「고쳤다」와 「고친 것이 돌고 있다」는 다른 사실이다(D-301). 아래 넷을 **다** 본다.

```bash
# ㉠ 상한이 **걸렸는가** — compose 파일이 아니라 도커에게 묻는다. 빈칸이 하나도 없어야 한다
printf "%-26s %-10s %-8s %-8s\n" CONTAINER DRIVER MAXSIZE MAXFILE
for c in $(docker ps --format '{{.Names}}' | sort); do
  printf "%-26s %-10s %-8s %-8s\n" "$c" \
    "$(docker inspect -f '{{.HostConfig.LogConfig.Type}}' $c)" \
    "$(docker inspect -f '{{index .HostConfig.LogConfig.Config "max-size"}}' $c)" \
    "$(docker inspect -f '{{index .HostConfig.LogConfig.Config "max-file"}}' $c)"
done

# ㉡ 앞단 접근로그가 **파일을 떠났는가** — 파일이 더 이상 자라지 않아야 한다
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e sh -c 'ls -l /var/log/nginx/gx-front.access.log'
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8500/
docker logs --since 30s gx-nginx-e | tail -3          # ← 여기에 접근로그 줄이 보여야 한다
MSYS_NO_PATHCONV=1 docker exec gx-nginx-e sh -c 'ls -l /var/log/nginx/gx-front.access.log'   # 크기 그대로면 성공

# ㉢ 살아 있는가 — 상한만 걸고 서비스를 죽이면 아무 소용이 없다
docker exec postgres psql -U postgres -d database_guardianx -c 'SELECT 1' | tail -2
docker exec redis redis-cli ping
MSYS_NO_PATHCONV=1 docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings python manage.py check' 2>&1 | tail -3
MSYS_NO_PATHCONV=1 docker exec gx-celery-e python -m celery -A config inspect ping -t 10 | tail -3
curl -s -o /dev/null -w 'minio=%{http_code}\n' http://localhost:9000/minio/health/live

# ㉣ 판정기로 못박는다 — ②(보존 기간)와 ④(선언)가 초록이어야 한다
python scripts/ops_log_collectors.py --evidence docs/agent/evidence/OPS-07/collectors.md; echo "EXIT=$?"
```

**되돌리기**: ①에서 뜬 `*.json` 이 재생성 전 형상 그대로다. 어느 컨테이너가 안 서면
그 파일의 `Mounts`·`Env`·`NetworkSettings` 를 그대로 되짚어 다시 만든다.
**되돌렸으면 사유를 이 절 아래에 적는다** — 적지 않으면 다음 사람이 같은 것을 또 시도한다.

⚠ 이 절을 다 돌아도 `ops_log_collectors.py` 의 ②는 **DB 감사 로그 한 줄 때문에 빨강일 수
있다.** 그것은 로그 상한과 무관하다 — 파기 항목이 DB 주기 표에서 꺼져 있기 때문이고,
켜는 조건은 P-57(보존 일수 미선언 테넌트 제외 판정)이다. 명령은
`docker-compose.yml` 의 `beat` 서비스 머리말에 있다. **로그 상한을 다 걸었다고 그 줄이
초록이 되지 않는 것이 옳다.**

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
