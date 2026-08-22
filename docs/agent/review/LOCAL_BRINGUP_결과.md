# 로컬 기동 결과 — RUNBOOK_로컬기동 실행 보고

**실행** 2026-08-22 · **에이전트** Claude Code · **근거 문서** `docs/agent/RUNBOOK_로컬기동.md` (D-242 · RESUME_NEXT §5-③)
**FREEZE 취급** D-236 의 "조사·측정 + 환경 복구" 예외로 실행. **소스는 한 줄도 고치지 않았다.**

> **한 줄 요약**: 목표 문장 — *"이 PC에서 `manage.py check` → 백엔드 기동 → 프론트 빌드"* — 은 **참이 되었다.**
> 열두 스프린트 동안 "오프라인 시험 0건"의 원인이던 `ImportError` 가 사라졌고,
> **미검증 재고가 처음으로 실행되어 예상표와 대조되었다.** 그 대조에서 예상이 두 곳 빗나갔다.

### 티켓 판정 요약

| 티켓 | 실행 전 | 실행 후 | 근거 |
|---|---|---|---|
| **W0-11** | done | done (유지) | dj-core 1.1.6 회수·조사 완료 |
| **W0-12** | verify-pending | **dod ①②③ 전부 충족** | verify#1 0건 + `test_service_layer_does_not_pick_arbitrary_group` **ok** |
| **W0-14** | verify-pending | **구현 실동작 확정 / 커버리지 0%** | 통합시험 2건 ok · 대장 생성 · **652 라우트 실측** |
| **W0-4** | verify-pending | **verify 통과 + 게이트 유효성 증명** | 빌드 exit 0 · 데모 6청크 ON/OFF 대조 |
| **W0-8** | ready (사내망 필요) | **사내망 불필요 — 회수 완료** | `package-lock.json` 106의존성 전부 일치 |
| **W0-2** | verify-pending | **①② 충족 / 테스트 실행됨** | `test_bypass_list_does_not_grow` **ok** |
| **W0-3** | verify-pending | **예상 1건 적중 + 예상 밖 3건** | §3-2 |
| **W2-1** | verify-pending | **dry-run 리포트 확보** | 드리프트는 DetectionEvent 하나뿐 |
| **W0-13** | decision-pending | 유지 — C안 근거 강화 | §3-3 |

> **★ 이 표 이후에 더 큰 것이 나왔다.** WP-1 goal 을 HTTP 로 직접 실측한 결과
> **테넌트 격리가 두 경로로 뚫려 있다** — `superuser` 역할 13계정(고객 테넌트에 배포됨)과
> `created_by IS NULL`. 전문: `docs/agent/evidence/W0-14/http_leak_probe.md`

---

## 1. 무엇이 열렸나 — 회수 경로 A 확정

| 항목 | 값 |
|---|---|
| dj-core | **1.1.6** · `/usr/local/lib/python3.11/site-packages/core/base.py` |
| 입수처 | `GuardianX build/gx-build-20260210/gx-build/docker_images/guardianx-backend.tar` |
| `import core.base` | **OK** (`django.setup()` 선행 필요 — `safedelete` 가 import 시점에 settings 를 읽는다) |
| `python manage.py check` | **`System check identified no issues (0 silenced).`** |
| DB | `postgres:latest` 이미지 + `database/02_database_gx_deploy.sql` 복원 · **211 테이블 / 422 마이그레이션** |
| 스택 버전 | Python 3.11 / Django 5.1.14 / dj-core 1.1.6 |
| ⚠ 부수 발견 | 빌드 폴더의 `docker-compose.yml` 이 **DB·OpenSearch 관리자 비밀번호를 평문으로** 담고 있다 (`.env` 참조가 아니라 파일 안에 직접). W0-1b 의 53개와 **별건**이며, 그 금고 격리로 가려지지 않는다 → §6-8 |

**경로 B(운영서버 SSH)는 필요 없었다.** 필요한 것은 전부 이 PC 안에 있었다.

### 1-1. 기동 방식 — venv 가 아니라 이미지 안에서 (RUNBOOK STEP 2A 변경)

RUNBOOK 은 `python -m venv .venv` 를 지시했다. **그 경로는 성립하지 않는다:**
이 PC 의 파이썬은 **3.14** 이고 회수본은 **cp311 빌드**다. 게다가 `dj-core` 는 사설 인덱스에만 있어
`pip install` 경로가 없다(사내망 소멸).

대신 **이미지의 `site-packages` 를 그대로 쓰고 저장소 `backend/` 를 `/app` 에 바인드마운트**했다.
pip 도 인터넷도 쓰지 않는다. 재현 명령:

```bash
docker load -i "<build>/docker_images/guardianx-backend.tar"     # + postgres.tar, redis.tar
docker network create gx-main-network
docker run -d --name postgres --network gx-main-network \
  -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=<빌드 폴더 compose 의 값> -v gx_pgdata:/var/lib/postgresql \
  -v "<build>/database/01_import_data.sh":/docker-entrypoint-initdb.d/01_import_data.sh:ro \
  -v "<build>/database/02_database_gx_deploy.sql":/docker-entrypoint-initdb.d/02_database_gx_deploy.sql:ro \
  -p 5433:5432 postgres:latest
docker run -d --name redis --network gx-main-network redis:latest
docker run -d --name gx-shell --network gx-main-network --env-file <로컬 더미 env> \
  -v "<repo>/backend":/app -v "<repo>/docs":/docs -w /app \
  --entrypoint sleep guardianx-backend:latest infinity
docker exec gx-shell python manage.py check
```

- `.env` 는 **저장소 밖 스크래치패드**에 더미값으로 만들었다(D-002 · 금지 #1). 외부 `*.gaion.dev`
  의존(AI·MinIO·OpenSearch)은 전부 `*.invalid` 로 두었다 — 기동에 불필요하고, 연결 경고만 남고 죽지 않는다.
- `/docs` 도 마운트했다. `tests/test_route_tenant_scope.py` 의 `BASELINE_PATH` 가 `parents[2]/"docs"` 를
  가리키므로 이 마운트가 있어야 대장이 저장소에 떨어진다.

---

## 2. ★ 상류 결함 — dj-core 1.1.6 은 **마이그레이션을 0부터 쌓을 수 없다**

`manage.py test` 는 test DB 를 마이그레이션으로 새로 만든다. 그 경로에서 죽는다.

```
LookupError: No installed app with label 'multilanguage'.
  core/logger/migrations/0009_auditaccesstype_auditaction_auditcommand_and_more.py:17
      MultiLanguageContent = apps.get_model("multilanguage", "MultiLanguageContent")
  dependencies = [('logger', '0008_...')]        ← multilanguage 의존성이 없다
```

`RunPython` 안에서 `multilanguage` 모델을 꺼내면서 **그 앱에 대한 의존성을 선언하지 않았다.**
마이그레이션 상태(`from_state.apps`)에 그 모델이 없으므로 반드시 실패한다.

**운영에서는 한 번도 드러나지 않았다.** 운영 DB 는 덤프 복원이고 `entrypoint.sh` 의 `migrate` 는
그 위에서 no-op 이기 때문이다. 즉 **"0부터 세우기"를 아무도 해 본 적이 없다.**

> §0.4 금지구역이라 고칠 수 없다(금지 #10). **AUTHOR-ERROR 가 아니라 벤더 결함**이므로
> `decisions_pending` 에 적재한다(P-LOCAL-1). dj-core 탈출 설계의 근거 항목이 하나 늘었다.

### 2-1. 우회 — 운영 스키마를 템플릿으로 test DB 를 만들고 `--keepdb`

```bash
docker exec postgres psql -U postgres -c "CREATE DATABASE test_database_guardianx"
docker exec postgres sh -c "pg_dump -U postgres --schema-only database_guardianx | psql -U postgres -d test_database_guardianx"
docker exec postgres sh -c "pg_dump -U postgres --data-only -t django_migrations database_guardianx | psql -U postgres -d test_database_guardianx"
docker exec gx-shell python manage.py test <label> --keepdb
```

**운영 데이터는 한 행도 넣지 않았다** — 스키마와 `django_migrations` 만이다. 그 위에서 Django 가
저장소의 신규 마이그레이션(`logger.0010`·`stream_monitors.0015`·`surveillance.0030`)을 정상 적용했다.

---

## 3. 검증 대개방 결과 — 예상표 대조

### 3-1. `tests.test_route_tenant_scope` — **9건 중 8 ok / 1 skip · 실패 0**

```
[TENANT_SCOPE] total=652 scoped=0 public=3 unreviewed=649 no_auth=143 coverage=0.0% enforcing=False
[TENANT_SCOPE] 대장을 새로 만들었습니다: docs/agent/evidence/W0-14/route_baseline.json
```

| 예상 (WP-1 EXIT) | 실측 | 판정 |
|---|---|---|
| 정적 실측 라우트 **466** | **런타임 652** | **빗나감 — 실제 표면이 40% 더 넓다** |
| 데코레이터가 ninja_extra 에서 실동작하는가 (미확인) | `ScopeDecoratorIntegrationTest` **2건 ok** | **확정** |
| 열거기가 라우트를 놓치지 않는가 | `test_enumerator_finds_routes` ok | **확정** |
| W0-12 dod③ `test_service_layer_does_not_pick_arbitrary_group` | **ok** | **충족** |

- **P-W0-14-1(D-241) 의 착수 조건이 충족됐다**: *"통합시험 2건 green 후 파일럿 1개부터"* — 그 2건이 green 이다.
- `test_all_group_models_are_covered` 는 대장 부재로 skip 됐다. **대장이 생겼으므로 다음 실행부터 돈다.**
  그 실행이 이미 예고한 것: group 보유 모델 소유 앱 28개 중 **12개 앱의 HTTP 표면이 열거되지 않는다**
  (`advanced_table · article · auth · configuration · discuss · file_management · guardian · logger · menu · role · tag · user` — 전부 dj-core 소유).

### 3-2. `tests.test_tenant_isolation` — **3건 실행 / 실패 2 · 에러 2**

| 테스트 | 예상 (W0-3 blocker) | 실측 |
|---|---|---|
| `test_bypass_list_does_not_grow` | 통과 | **ok** ✅ |
| `test_registry_covers_all_isolatable_models` | **실패 1건 확정** | **FAIL** — `dashboard.DashboardPanel` 미등록 ✅ 예상 적중 |
| `test_unisolated_set_has_not_grown` | 통과 예상 | **FAIL** ❌ **예상 빗나감** — §3-3 |
| `TenantIsolationORMTest` / `TenantIsolationAPITest` | 통과 예상 | **ERROR(setUpTestData)** ❌ **예상 빗나감** — §3-4 |

### 3-3. ★ `test_unisolated_set_has_not_grown` 실패 — **W0-11 §5-3 의 런타임 확증**

```
격리 메커니즘(groups M2M) 없는 모델이 새로 추가되었습니다:
['checklist_setting.ChecklistSetting', 'stream_monitors.DetectionEvent',
 'stream_monitors.StreamMonitor', 'surveillance.SurveillanceProfile', 'terminals.Terminal']
```

이 5종은 **`core.base.BaseModelWithGroup`(dj-core) 상속분**이다. 그리고 W2-1 dry-run 이
그 이유를 코드로 보여 준다:

```python
('group', models.ForeignKey(..., to='user.usergroup')),     # ← 단수 FK
```

**두 베이스는 격리 메커니즘 자체가 다르다.**

| 베이스 | 소유 | 필드 | 모델 수 |
|---|---|---|---|
| `core.base.BaseModelWithGroup` | dj-core (§0.4) | **`group` FK (단수)** | 13 |
| `common.base_model.BaseModelWithGroup` | 저장소 | **`groups` M2M (복수)** | 2 |

`is_group_isolatable()` 은 `groups` 만 본다. 그래서 dj-core 쪽 13종을 **전부 "격리 없음"으로 읽는다.**
테스트가 틀린 것도, 모델이 틀린 것도 아니다 — **저장소가 dj-core 의 격리 방식을 모르고 쓰여 있었다.**

> **이것이 W0-13 C안(뷰 레벨 스코프)의 마지막 근거다.** 저장소의 격리 판정 함수조차 주 경로를
> 못 보고 있었다. ORM 매니저에 격리를 맡기는 설계는 여기서 끝났다.

### 3-4. ORM/API 시험 2종 ERROR — **테스트 픽스처 결함 (수정하지 않았다)**

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "user_coreuser_email_key"
DETAIL:  Key (email)=() already exists.
  tests/test_tenant_isolation.py:148  CoreUser.objects.create_user(username=..., password=..., is_active=True)
```

`create_user` 에 `email` 을 주지 않아 두 사용자가 모두 `email=''` 로 들어가고,
dj-core 의 `CoreUser.email` **UNIQUE 제약**에 걸린다. 오프라인에서는 알 수 없던 사실이다.

**고치지 않았다.** 절대금지 #5 가 이 파일의 수정을 막고, 파일 머리말 자신이
*"테스트가 틀린 것 같으면 고치지 말고 멈추고 보고한다"* 고 적어 두었다. **보고가 여기다.**
`_make_user` 에 고유 email 을 넘기는 한 줄이면 풀린다 — **사람의 승인이 필요하다.**

> 부수 실측: **운영 DB 에서 email 이 빈 사용자는 최대 1명만 존재할 수 있다.** 스키마가 그렇게 강제한다.

### 3-5. W2-1 — dry-run 리포트 확보 (금지 #9 충족)

```
$ python manage.py makemigrations --check --dry-run     → exit 1
Migrations for 'stream_monitors':
  stream_monitors/migrations/0016_detectionevent.py
    + Create model DetectionEvent
```

**드리프트는 이 하나뿐이다** — 다른 앱은 모델과 마이그레이션이 일치한다.
전문은 `evidence/LOCAL_BRINGUP/W2-1_makemigrations_dryrun.txt`.
**마이그레이션 파일은 만들지 않았다** — 되돌릴 수 없는 유일한 작업이고 FREEZE 중이며 WP-0 ENTRY 가 미승인이다.

### 3-6. STEP 3 프론트 — **빌드 성공. 그리고 티켓의 verify 가 무력하다는 것을 알아냈다**

`guardianx-frontend.tar` 안에 **`node_modules`(778패키지)와 사설 의존 2건이 그대로 있었다.**
그 위에 저장소 `frontend/` 소스를 덮어써서 빌드했다 — `npm install` 도 인터넷도 쓰지 않았다.

```
node v18.20.8 / npm 10.8.2 / vite 5.4.21
NODE_OPTIONS=--max-old-space-size=6144      ← 기본 2GB 힙으로는 OOM 으로 죽는다
✓ built in 50.81s        dist 29.4MB / 190 청크
```

| 항목 | 결과 |
|---|---|
| W0-4 verify: `npm run build && ! grep -rl 'mockupDemoUi' dist/assets` | **PASS** (build exit 0 · grep 0건) |
| D-218 dod "게이트 유효성" | **증명됨** — 플래그 ON 재빌드 시 **6청크 증가** (`DemoPage.js`·`DemoUrlPage.js`·`Panel.js`+`index.js`×3). OFF 전용 청크는 0 |

> **⚠ AUTHOR-ERROR (D-214) — 그 verify 명령은 아무것도 증명하지 않는다.**
> `VITE_ENABLE_DEMO=true` 로 **데모를 포함시켜 빌드해도** `grep -rl 'mockupDemoUi' dist/assets` 는
> **0건**이다. minify 가 식별자를 지우기 때문이다. 즉 이 명령은 **데모가 들어 있어도 통과한다.**
> 실효 검증은 **청크 이름 대조**다. 정본 verify 를 그 방식으로 교체할 것을 요청한다.

**부수 발견 2건**:
1. **W0-8 이 사내망 없이 닫힌다.** 이미지의 `package-lock.json`(lockfileVersion 3 · 2,384 패키지)을
   금고로 회수했고, 저장소 `package.json` 의 **106개 의존성과 불일치 0**으로 검증했다.
   `C:\GuardianX-vault\frontend-lockfile-20260210\` · md5 `9d919a08… (전체 값은 금고 파일에서 직접 확인 · 금지 #2)`.
   **커밋은 승인 대기** (금지 #17 · 작업트리에 두지 않았다).
2. 소스 결함 1건: `src/features/operationalNotice/pages/EditOperationalNotice.tsx:207`
   JSX `disabled` 속성 중복. 고치지 않았다(FREEZE).

전문: `evidence/LOCAL_BRINGUP/W0-4_frontend_build.md`

---

## 4. ★ STEP 5 — 대표 증언 대조 결과: **"두 곳 내용은 같다"는 거짓이다**

이미지 `/app` (2026-02-10 빌드) 과 저장소 `backend/` 의 `*.py` 793 : 800 개를 md5 로 전수 대조했다.

| 구분 | 수 |
|---|---|
| 이미지에만 있는 파일 | **0** |
| 저장소에만 있는 파일 | 7 (전부 W0-12·W0-14·W0-3 산출물) |
| 내용이 다른 파일 | **78** |
| ├ 그중 우리 커밋(`4afca2b..HEAD`)이 건드린 것 | 5 |
| └ **베이스라인 시점부터 이미 달랐던 것** | **73 · 약 2,296줄** |

공백·개행 차이는 **0건**이다. 전부 실질 변경이다. 예: `terminals/views/routes_views.py` 는
저장소가 `MESSAGE_ENUM.ACTION_*` 로 리팩터링돼 있고 이미지는 옛 문자열을 쓴다.

> **운영에서 돌고 있는 것은 저장소 HEAD 가 아니다.** 저장소가 73파일 앞서 있다.
> 그러므로 **"운영서버에서 실측했다"로 내려진 판정은 저장소 기준으로 재확인이 필요하다.**
> (W0-13 의 `created_by` NULL 실측은 이 이미지와 짝인 2026-02-10 덤프를 쓴 것이라 **일관된다** — 그 건은 영향 없다.)

---

## 5. 우회한 것 · 하지 않은 것

| 항목 | 왜 |
|---|---|
| `.venv` 네이티브 기동 | 인터프리터 불일치(3.14 vs cp311) + 사설 인덱스 부재. 이미지 이식으로 대체 |
| test DB 를 마이그레이션으로 생성 | §2 상류 결함. 스키마 템플릿 + `--keepdb` 로 대체 |
| MinIO·OpenSearch·AI 실연결 | 기동 목표에 불필요. 더미 호스트로 두고 경고만 남김 |
| 프론트 **dev 서버** 기동 | 하지 않았다. W0-4 의 판정 기준은 프로덕션 **빌드 산출물**이고 그것은 확보했다 |
| `npm install` | 불필요 — 이미지의 `node_modules` 를 그대로 썼다 |
| **소스 수정 전부** | FREEZE(D-236) + WP-0 ENTRY 미승인 + 절대금지 #17 |
| **W2-1 마이그레이션 파일 생성** | 되돌릴 수 없음. dry-run 리포트까지만 (금지 #9) |
| **테스트 픽스처 수정** | 절대금지 #5 |

---

## 6. 사람이 판단해야 할 것

1. **§3-4 테스트 픽스처** — `_make_user` 에 고유 email 부여를 승인하는가. 이것 없이는 ORM/API 격리 시험
   5시나리오가 한 건도 돌지 않는다. **격리 증명의 본체가 여기 막혀 있다.**
2. **§3-3 격리 판정 함수** — `is_group_isolatable()` 이 `group` FK 를 함께 보도록 고칠 것인가,
   아니면 dj-core 13종을 `KNOWN_UNISOLATED` 로 옮길 것인가. 전자는 판정이 넓어지고 후자는 사실을 기록한다.
   **에이전트 권고: 전자.** 후자는 "격리 없음"이라는 틀린 사실을 정본에 새긴다.
3. **§4 드리프트 73파일** — 운영과 저장소 중 무엇이 정본인가. 이 답이 없으면 다음 배포에서
   2,296줄이 조용히 되돌아가거나 조용히 나간다.
4. **§2 dj-core 마이그레이션 결함** — 벤더 대응 창구가 없다(담당자 퇴사). 탈출 설계로 갈 것인가.
5. `route_baseline.json` **커밋 승인** — 이 파일이 있어야 다음 실행부터 미분류 증가 금지가 걸린다.
6. **§3-6 W0-4 verify 교체 승인** — 현행 명령은 데모가 들어 있어도 통과한다. 청크 이름 대조로 바꿔야 한다.
   `verify` 는 정본 필드라 에이전트가 고칠 수 없다(금지 #11).
7. **§3-6 `package-lock.json` 커밋 승인** — 금고에 회수해 두었다. 커밋하면 W0-8 이 닫힌다.
8. **★ P-LOCAL-5 — `superuser` 역할 13계정** (2026-08-22 추가 · `evidence/W0-14/http_leak_probe.md`)
   HTTP 레벨 실측에서 **테넌트 격리가 뚫려 있음이 확인됐다.** 고객 테넌트 안에 배포된 13개 계정이
   전 테넌트 데이터를 본다. **이 목록의 다른 무엇보다 먼저 답해야 한다** — `created_by` 를 전부
   채워도(P-LOCAL-2·W0-13) 이 13계정에는 아무 효과가 없다. 두 구멍은 독립이다.
9. **빌드 폴더 `docker-compose.yml` 의 평문 비밀번호** — W0-1b 는 `config/*.env` 2파일을 금고로
   옮겼지만, `docker-compose.yml` 안에 **직접 박힌** 관리자 비밀번호 2건은 그대로 남아 있다
   (`.env` 참조가 아니라 리터럴). 그 파일은 배포 스크립트라 옮길 수도 없다.
   **W0-1b 재발급 목록에 추가하고, 값을 `env_file` 참조로 빼는 것을 함께 판단해야 한다.**
   (이 문서에는 값을 적지 않았다 — 금지 #2)

---

## 7. 증거 파일

| 파일 | 내용 |
|---|---|
| `evidence/LOCAL_BRINGUP/test_route_tenant_scope.txt` | 9건 전문 · 652 라우트 실측 |
| `evidence/LOCAL_BRINGUP/test_tenant_isolation.txt` | 3건 + setUpClass 에러 2건 전문 |
| `evidence/LOCAL_BRINGUP/W2-1_makemigrations_dryrun.txt` | DetectionEvent 마이그레이션 전문 |
| `evidence/LOCAL_BRINGUP/W0-4_frontend_build.md` | 프론트 빌드·게이트 ON/OFF 대조·lockfile 회수 |
| `evidence/W0-14/route_baseline.json` | 미분류 잔여 대장 (신규) |
