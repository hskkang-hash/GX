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
- DB: Docker 가능하면 `docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=devonly postgres:16` / 불가하면 Windows Postgres 설치.
- `.env` 는 `.env.example` 복사 후 로컬값. **외부 `*.gaion.dev` 의존(AI·MinIO·OpenSearch)은 전부 비우거나 더미로** — 기동 목표에 불필요. 죽는 지점이 있으면 해당 기능만 설정으로 끄고 기록.
- `python manage.py migrate` → `runserver` → `http://localhost:8000` 응답 확인.

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
