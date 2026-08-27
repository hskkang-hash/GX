# D-281·282·283 이행 — 스코프는 시그니처다 · 착시 ⑤ 게이트 · **마이그레이션 사고 보고**

**작성** 2026-08-29 · 대상 W2-1 / W2-2 · 근거 D-281 · D-282 · D-283 · D-285 (4)

---

## 0. ★ 먼저 보고할 것 — **제가 절차를 어겼습니다** (D-283)

**0016 은 이미 적용돼 있었고, 적용한 것은 저입니다.** D-283 이 요구한 선행 3건
(① DDL 첨부 → ② 역방향 확인 → ③ 스냅샷) **을 하기 전에** 적용됐습니다.

### 무슨 일이 있었나

D-285 (4) 를 이행하려고 — 컨테이너에 `scripts/` 가 없어 시험 1건이 skip 되던 문제 —
`gx-shell` 컨테이너를 마운트만 더해 **재생성**했습니다. 그런데 이 이미지의
`ENTRYPOINT=/entrypoint.sh` 는 **무조건** `python manage.py migrate` 를 돕니다.

```
/entrypoint.sh:19    python manage.py migrate          ← 조건 없음
```

컨테이너가 뜨는 순간(13:28:12 UTC) 그 줄이 돌아 **마이그레이션 4건**이 적용됐습니다.

| 시각 (UTC) | 적용된 마이그레이션 | 성격 |
|---|---|---|
| 13:28:47 | `logger.0010_auditlogs_created_by_…` | ADD COLUMN ×7 · ALTER TYPE varchar ×7 · CREATE INDEX ×4 |
| 13:28:47 | `surveillance.0030_surveymission_hover_and_capture` | ADD COLUMN ×1 |
| 13:28:50 | `stream_monitors.0015_alter_streammonitoraimodel_…` | ADD COLUMN ×12 · CREATE INDEX ×7 |
| 13:28:51 | `stream_monitors.0016_detectionevent` | **CREATE TABLE ×1** ← D-283 이 승인한 것 |

**승인된 것은 1건인데 4건이 적용됐습니다.** 나머지 3건은 승인 범위 밖입니다.

### 지금 확인한 사실 — 추정 없이

* **운영 DB 는 건드리지 않았습니다.** 대상은 로컬 복제본(`postgres` 컨테이너,
  `database_guardianx`) 하나뿐입니다 (D-283 ③ 의 "로컬만"은 지켜졌습니다).
* **데이터 손실이 없습니다.** 4건의 DDL 전수를 뽑아 확인했고 `DROP` · `DELETE` 가
  **한 줄도 없습니다.** 전부 `ADD COLUMN`(NULL 또는 DEFAULT) · `CREATE INDEX` ·
  `CREATE TABLE` 입니다. `ALTER COLUMN … TYPE varchar(64)` 는 **넓히는** 쪽이고,
  PostgreSQL 은 넓힐 때 값을 자르지 않습니다(좁힐 때 초과분이 있으면 에러로 멈춥니다 —
  성공했다는 것이 곧 잘림이 없었다는 증거입니다).
* **행 수 실측** (적용 후):
  `logger_auditlogs` 1,068 · `surveillance_surveymission` 39 ·
  `stream_monitors_drawingsession` 1 · `stream_monitors_streammonitoraimodel` 14 ·
  `stream_monitors_streammonitor` 39 · `stream_monitors_detectionevent` **0**(신규 표).
* **4건 모두 역방향이 있습니다** (D-283 ②). `sqlmigrate --backwards` 가 4건 전부에
  DDL 을 냈고 `Irreversible` 은 없습니다. 되돌리려면 `DROP TABLE` ·
  `DROP COLUMN CASCADE` · `ALTER TYPE varchar(32|16)` 로 돌아갑니다.
* **선행 스냅샷은 없습니다.** 가장 가까운 이전 스냅샷은
  `C:\GuardianX-vault\gx_before_backfill_20260827.dump` (08-27 11:42 KST)이고,
  이것은 **W0-13 백필 25,296행보다 앞섭니다** — 이 건만 되돌리는 지점이 아닙니다.
  적용 후 스냅샷을 지금 떴습니다: `gx_after_migr_0013_0016_20260827.dump` (4.4MB).

### 배운 것 — "조심하자"가 아니다

**사람의 기억에 맡긴 절차는 도구가 우회합니다.** D-283 은 사람이 밟는 절차이고,
`docker run` 은 어떤 게이트도 보지 않는 자리입니다. 막을 수 있는 유일한 지점은
**셸을 만드는 방법 자체를 코드에 못박는 것**이었습니다.

조치 (`docker-compose.yml`):

```yaml
  shell:
    profiles: ["tools"]
    entrypoint: ["sleep"]        # ★ 이 줄이 자동 migrate 를 끊는다
    command: ["infinity"]
```

`gx-shell` 도 같은 형태(`--entrypoint=sleep`)로 다시 세웠고, 기동 로그에
`Applying …` 이 **0건**임을 확인했습니다.

### 판단을 구합니다

승인 범위(0016 1건) 밖의 **3건을 되돌릴지** 여부입니다. 저는 **되돌리지 않는 쪽을
권고**합니다:

* 셋 다 **가산적**이고 데이터 손실이 없으며, 셋 다 이 저장소의 모델 선언이
  **이미 요구하던 것**입니다(그래서 `makemigrations` 가 낸 것입니다). 되돌리면
  모델과 DB 가 다시 갈라지고, 그것이 정확히 D-282 가 막으려는 상태입니다.
* 되돌리는 쪽이 오히려 위험합니다 — `logger.0010` 의 역방향은 `varchar(64)→(32|16)`
  으로 **좁히는** 조작이라 그 사이 들어온 값이 있으면 실패합니다.

다만 **이것은 제 판단이 아니라 판정 사안**이므로, 되돌리라는 지시가 오면
`gx_before_backfill_20260827.dump` 가 아니라 **역방향 마이그레이션**으로 되돌리겠습니다
(백필을 함께 잃지 않기 위해서).

---

## 1. D-281 — 커널 스코프를 시그니처로 (P-K1-1 확정본)

### 무엇을 바꿨나

`TenantScope` 를 L1(`common/tenant_scope.py`)에 세우고, K1 공개 면 **6개 전부**를
키워드 전용 필수 인자로 옮겼습니다.

```python
def query_events(*, scope: TenantScope, ...)      # scope 없으면 TypeError
def get_event(event_id: int, *, scope: TenantScope)
def review_event(event_id: int, *, verdict: str, reason: str = "", scope: TenantScope)
def close_event(event_id: int, *, scope: TenantScope)
def record_detection(*, scope: TenantScope, stream_monitor_id: int, ...)
def subscribe(*, scope: TenantScope, webhook_url: str, ...)
```

### 사람 없는 호출을 어떻게 다뤘나 — 없애지 않고 **이름을 붙여 셉니다**

검출 파이프라인(gRPC 콜백)에는 요청자가 없습니다. 그렇다고 스코프 인자를 빼면
"테넌트를 생각하지 않은 호출"과 구별이 사라집니다. 그래서:

```python
TenantScope.of(user)                    # 사람이 부른다
TenantScope.system(reason="…")          # 사람이 없다 — 사유 필수
```

* **사유 없는 시스템 스코프는 만들 수 없습니다** (`__post_init__` 이 던집니다).
* **시스템 스코프로는 읽지 못합니다** (`require_actor()`). 읽기가 전역이 되는 길을 막습니다.
  `record_detection` 만 시스템 스코프를 받습니다.
* `grep "TenantScope.system"` 한 줄로 **전수가 세어집니다** — 수가 아니라 이름으로
  잠그는 D-285 (2) 와 같은 계열입니다.

### 곁가지로 막힌 것 — 쓰기 쪽 IDOR

`record_detection` 이 사람 스코프로 불릴 때 `assert_scoped(StreamMonitor, …)` 를
먼저 부르게 했습니다. 전에는 **아무나 남의 `stream_monitor_id` 로 남의 테넌트에
이벤트를 심을 수 있었습니다.** 시그니처만으로는 이것을 못 막습니다(스코프를 주기만
하면 되므로) — **시그니처가 1차, 문지기가 2차**라는 D-281 문언이 여기서 실질을 갖습니다.

부수 효과로 `record_detection` 이 `KERNEL_PUBLIC` 등재에서 **내려왔습니다.**
"테넌트를 안 만진다"는 선언이 더는 필요 없어졌기 때문입니다. PUBLIC 은 이제 1건
(`subscribe`, 구현 없음)뿐입니다.

### 게이트 — `verify_tenant_scope.py`

통과 사다리를 두 층으로 명시했습니다.

```
1차  키워드 전용 필수 인자 `scope: TenantScope`   ← 면제 없음. PUBLIC 등재도 이것을 대신 못 함
2차  문지기 호출 / PUBLIC 등재(사유+시험근거)
```

그리고 **커널에 `@tenant_scoped` 를 붙이는 것 자체를 반려**합니다 — 붙어 있다는 사실이
"여기는 막혀 있다"는 오해를 만들기 때문입니다.

실측:

```
[SCOPE] 커널 공개 함수 6개 — 1차 scope 시그니처 6/6 (술어=키워드 전용·기본값 없음, D-281)
                            · 2차 @tenant_scoped 0 · 문지기 호출 5 · PUBLIC 1
```

### ★ 양성 대조 4/4 (D-277)

게이트가 **실제로 막는지** 네 가지로 확인했습니다. 넷 다 `exit 1`, 복구 후 `exit 0`.

| # | 심은 결함 | 결과 |
|---|---|---|
| ① | `scope` 인자를 뺀다 | exit 1 — "키워드 전용 필수 인자가 없다" |
| ② | `scope: TenantScope = None` (기본값) | exit 1 — "기본값이 있으면 필수가 아니다" |
| ③ | `scope` 를 위치 인자로 | exit 1 — "호출부에서 `scope=` 글자가 사라진다" |
| ④ | 커널에 `@tenant_scoped()` | exit 1 — "D-281 이 금지한다" |

### 런타임 눈 — 시험 5건 신설 (`KernelScopeSignatureTest`)

정적 눈(AST)이 못 보는 것을 시험이 봅니다: 선언은 맞는데 런타임에 통과해 버리는 경우.

* `test_every_public_function_refuses_to_run_without_scope` — **6개 전부**를 스코프 없이
  불러 본다. ★ **실패는 뒤를 가리지 않게** 대상별 표를 냅니다 (D-274 승격 원칙).
* `test_subscribe_requires_scope_before_it_raises` — 구현이 없어도 **스코프가 먼저** 걸린다.
  이것이 갈라지지 않으면 `subscribe` 는 "구현이 없어서 안전한" 것이지 "스코프를 요구해서
  안전한" 것이 아닙니다.
* `test_system_scope_cannot_read` — 파이프라인 스코프로 읽기·판정 4경로 전부 거절.
* `test_scope_of_none_is_refused_at_construction` — 빈 스코프는 만들어지지도 않는다.
* `test_human_scope_cannot_write_into_another_tenants_stream` — 쓰기 쪽 IDOR 차단
  (**양성 대조 포함** — 자기 스트림에는 들어갑니다).

---

## 2. D-282 — 착시 ⑤ 게이트 (`scripts/verify_migrations.py`)

### 눈이 둘입니다 — ②는 문언을 넘어선 추가입니다

모델에서 표까지는 두 걸음이고, **이번 사고는 둘째 걸음에서** 났습니다.

| 눈 | 보는 것 | 근거 |
|---|---|---|
| ① 모델 → 마이그레이션 파일 | `makemigrations --check --dry-run` 과 같은 판정 | **D-282 문언** |
| ② 마이그레이션 파일 → DB | `migrate --check` 와 같은 판정 | **추가** (아래) |

**② 는 D-282 문언에 없습니다.** 더한 이유: `0016` 은 **파일로는 있었는데 DB 에
적용되지 않아** 표가 없었습니다. ①만 보면 그 상태는 **초록으로 보입니다.**
D-282 의 원칙이 "재는 자리가 실물인가"인데 ①은 실물(DB)을 아예 보지 않습니다.
**판정문에 없는 것을 더했으므로 여기에 명시하고 확인을 구합니다.**

### 못 센 것을 통과로 세지 않습니다

```
exit 0  두 눈 모두 0건 + 자기 시험 통과
exit 1  미반영/미적용이 있거나 탐지기가 자기 시험에 실패
exit 2  판정 불가 — Django 를 못 띄웠거나 DB 에 못 닿았다 (**통과가 아니다**)
```

`--no-db` 로 ②를 끄면 그 사실을 출력하고 **exit 2** 를 냅니다. DB 에 못 닿았을 때도
빈 목록을 "미적용 0건"으로 세지 않습니다 — **못 센 것과 0 은 다릅니다.**

### ★ 양성 대조 — 그리고 그것이 제 대조 코드를 잡았습니다

두 눈 각각에 대조를 붙였습니다.

* **①** 없던 필드 하나를 모델 상태에 심어 자동탐지기가 잡는지 본다.
* **②** 로더가 기억하는 "적용됨" 집합에서 항목 하나를 **메모리에서만** 빼고 다시 센다
  (DB 는 읽기만 — D-270).

②를 처음 짤 때 `build_graph()` 를 불렀는데, **그것이 DB 에서 적용 목록을 다시 읽어
방금 세운 가정을 지웠습니다.** 대조는 "탐지기가 눈멀었다"고 실패했고, 눈이 먼 것은
탐지기가 아니라 **대조 자신**이었습니다. 그 실패가 곧 이 대조가 작동한다는 증거입니다.

```
[MIGR] 양성 대조 — 가짜 필드 1건을 심자 탐지기가 잡았다. 판정기는 작동한다
[MIGR] 양성 대조(②) — 적용 표식 1건(admin.0003_logentry_add_action_flag_choices)을 빼자
                      미적용 1건으로 잡혔다. 판정기는 작동한다
[MIGR] ① 모델→마이그레이션 — 미반영 0건 (술어=MigrationAutodetector, 모수=INSTALLED_APPS 전수)
[MIGR] ② 마이그레이션→DB   — 미적용 0건 (술어=MigrationExecutor.migration_plan, 모수=leaf 전수)
[MIGR] 정합 — 모델 선언 = 마이그레이션 그래프 = DB
```

### 어디에 걸었나

| 자리 | 상태 |
|---|---|
| `backend/tests/…::test_migration_state_matches_models_and_db` | **돈다** — `--nomigrations` 실행 안에서 그 격차를 한 번 본다 |
| `.github/workflows/migration-check.yml` | 레지스트리 러너에서만. **없으면 `not-green` 잡이 "판정하지 못했다"를 로그에 남긴다** |
| `.gitlab-ci.yml : migration-check` | 같은 조건 |
| pre-commit | **걸지 않았다** — 호스트에 Django 가 없어 매 커밋이 exit 2 로 막힌다. 사실대로 남긴다 |

---

## 3. D-285 (4) — skip 1 해소

컨테이너에 `scripts/` 가 없어 `test_kernel_does_not_import_apps` 가 skip 되던 것을
마운트로 풀었습니다.

```yaml
- ./scripts:/repo/scripts:ro     # 읽기 전용 — 컨테이너가 저장소를 고칠 수 없다 (D-270)
- ./backend:/repo/backend:ro
```

시험도 함께 고쳤습니다: 이제 스크립트를 **못 찾으면 skip 이 아니라 실패**입니다.
마운트를 넣어 해소한 뒤이므로, 다시 사라지면 그것은 "환경 미비"가 아니라
**되돌아간 것**이기 때문입니다.

---

## 4. 실측 — 분모와 술어를 함께 (D-271 신설 규칙)

```
시험      118 passed · 0 skipped      (직전 111 passed · 1 skipped)
          술어 = pytest tests -q --nomigrations -p no:randomly, 모수 = tests/ 전수

게이트    verify_tenant_scope   exit 0   (커널 공개 함수 6/6 · 1차 시그니처 6/6)
          verify_layers         exit 0
          verify_classification exit 0
          verify_kernel_map     exit 0
          verify_timeout        exit 0
          verify_migrations     exit 0   (컨테이너) / exit 2 (호스트 — 판정 불가, 정상)

양성 대조 D-281 게이트 4/4 · D-282 ① 1/1 · D-282 ② 1/1 (대조가 자기 결함을 먼저 잡음)
```

---

## 5. 아직 모르는 것 / 안 한 것 — 지우지 않는다

1. **승인 범위 밖 3건의 처분이 미정입니다.** §0 의 판단 요청.
2. **"실제 마이그레이션을 적용한 DB 에서 도는 시험 경로"가 아직 없습니다.**
   D-282 는 "최소 1개 시험 경로"를 요구했는데, 지금 있는 것은
   `--nomigrations` 실행 **안에서 게이트를 부르는** 시험입니다. 그것은 격차를
   **보기는** 하지만 그 DB 위에서 **돌지는** 않습니다. 마이그레이션을 0부터 쌓아
   테스트 DB 를 만드는 경로는 아직 확인하지 않았습니다(P-LOCAL-1 계열).
   — 다음 턴 과제로 남깁니다. **지금 초록으로 세지 않습니다.**
3. **CI 의 gate 잡은 아직 한 번도 돌지 않았습니다.** `GX_PRIVATE_REGISTRY_AVAILABLE`
   러너가 없습니다(W0-6). 그래서 `not-green` 잡을 함께 뒀습니다 — 체크표시 옆에
   아무 말이 없으면 다음 사람이 검사된 줄 압니다.
4. **F-05 p95 500ms 는 여전히 못 잽니다.** 부하도 데이터도 없습니다(직전 턴과 동일).

---

## 6. 재현

```bash
# 커널 스코프 게이트 (호스트)
python scripts/verify_tenant_scope.py --list

# 마이그레이션 정합 (컨테이너 — 자동 migrate 없는 셸)
docker compose --profile tools up -d shell
docker compose exec shell python /repo/scripts/verify_migrations.py --list

# 시험 전수
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  PYTHONPATH=/app python -m pytest tests -q --nomigrations -p no:randomly'
```
