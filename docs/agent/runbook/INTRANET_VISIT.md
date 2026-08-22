# 사내망 방문 RUNBOOK — 1회 방문으로 WP-0·WP-1 미완 10건 종결

> # ⛔ §A 는 사문(死文)이다 — 2026-08-22
>
> **사내망 `192.168.0.22` 는 더 이상 존재하지 않는다(담당 개발자 퇴사).**
> 이 문서의 **§A(사내 pip 로 dj-core 수령)** 는 영원히 실행되지 않는다.
>
> **대체**: `docs/agent/RUNBOOK_로컬기동.md` — 설치본은 처음부터 이 PC 안에 있었다.
> `GuardianX build/.../docker_images/guardianx-backend.tar` 에서 **dj-core 1.1.6 을 이미 회수했다**
> (Docker 데몬 없이 OCI 레이어 스트리밍 · `evidence/W0-11/dj-core-findings.md` §5).
>
> **§B~§F 는 그대로 유효하다 — 실행 장소가 사내망에서 이 PC 로 바뀔 뿐이다.**
> 그리고 그중 셋은 **이미 끝났다**:
>
> | 절 | 상태 |
> |---|---|
> | §A 전제 해소 | **대체됨** → 로컬 이미지 회수 |
> | §B W0-11 | **완료** — 우회목록 없음 · `created_by__isnull` 3건 (L430 이 핵심) |
> | §F W0-13 ① | **완료** — DB 없이 덤프 파싱. 65.9% (`scripts/scan_dump_created_by.py`) |
> | §C·§D·§E | **남아 있음** — 컨테이너 기동 필요 (WSL2 커널 설치 대기) |

**작성** 에이전트 · 2026-08-22 · **baseline** `faebd91`
**출처** WP-0 EXIT §8 · WP-1 EXIT §8 · evidence/W0-11 §4 · evidence/W0-13 §4 · evidence/W0-14 §3
**대상** 사내망(`192.168.0.22`) 접속 가능한 사람 · 예상 **약 3시간**

> **이 문서 하나만 들고 가면 된다.** 명령은 전부 복사 실행용이고, 각 단계에
> **예상 결과**와 **실패 시 어디에 귀속되는가**가 미리 적혀 있다.
> 예상을 미리 못박은 이유는 하나다 — **끝난 뒤에 결과를 보고 말을 맞추지 않기 위해서다.**

---

## 왜 방문 1회가 10건을 푸는가

열두 스프린트 동안 오프라인 시험이 0건이었다. 원인은 오랫동안 "Docker 미기동"으로
기록돼 있었고, **그것이 틀렸다는 것이 WP-1 에서 확정됐다**(WP-1 EXIT §1-2).

```
$ ls backend/core/
advanced_table
data                      ← 이 둘뿐. core.base 도 core.user.models 도 없다

$ python -c "import core.base"
ModuleNotFoundError: No module named 'core'
```

`core.*` 는 **사내망 pip 배포본(dj-core)** 안에 있다. 이것이 없으면 `django.setup()` 이
ImportError 로 죽고, **그 아래 모든 테스트·마이그레이션·집계가 한 줄도 돌지 않는다.**
Docker 를 켜도, DB 를 띄워도 달라지지 않는다.

**즉 §A 하나가 열리면 나머지 9건이 동시에 열린다.** 그래서 §A 가 실패하면
이 runbook 은 §B 이후를 시도하지 말고 중단한다.

---

## 준비물

- [ ] 사내망 접속 (사무실 랜 또는 VPN) — `192.168.0.22:22` 도달
- [ ] 사내 git SSH 키 (rj-core · gcs-fe · dj-core 접근권)
- [ ] Docker Desktop 기동 가능 (DB·Redis용)
- [ ] Node 18+ / Python 3.11+
- [ ] **[병행]** Kakao·Google·MinIO·TURN·SMTP·OpenSearch 콘솔 로그인 정보 (§G-2 · 사내망 무관)

```bash
cd /c/GuardianX/guardianx-source
git log --oneline -1        # faebd91 인지 확인. 아니면 pull 후 시작
git status --short          # 비어 있어야 한다
```

---

## §A. 전제 해소 — 의존성 수령 ★ 여기가 열리지 않으면 중단

**소요 20분.** 이 단계의 성패가 나머지 전부를 결정한다.

```bash
# A-1. 접속 확인
nc -z -w3 192.168.0.22 22 && echo "INTRANET=true" || echo "INTRANET=false"
```

> `false` 면 **여기서 멈춘다.** VPN·방화벽 문제이며 아래는 전부 실패한다.

```bash
# A-2. 백엔드 의존성 (dj-core 수령) ★ 핵심
cd backend
pip install -r requirements.txt
python -c "import core.base as m; print('OK:', m.__file__)"
```

| 결과 | 의미 | 다음 |
|---|---|---|
| 경로가 출력됨 | **전제 해소.** 10건 전부 진행 가능 | §B 로 |
| `ModuleNotFoundError` 유지 | dj-core 설치 실패 | 사내 pip 인덱스 설정(`pip.conf`) 확인. 해결 못 하면 **중단** |

```bash
# A-3. 프론트 lock 생성 → W0-8 종결
cd ../frontend
npm install --package-lock-only
npm ls rj-core @gaion/gcs-fe          # private 2종이 해결됐는지
test -f package-lock.json && echo "W0-8 dod 1  OK"
npm ci --dry-run && echo "W0-8 dod 2  OK"
```

> **여기서 바로 커밋한다.** lock 파일은 방문의 최우선 산출물이다 — 다음 사람이 §A-3 을
> 반복하지 않게 만드는 것이 이 방문의 이자다.
>
> ```bash
> cd .. && git add frontend/package-lock.json
> git commit -m "chore(deps): package-lock 생성 — 사내망 private 2종 해결 [W0-8]"
> ```

---

## §B. 읽기만 하는 것 — W0-11 (코드 수정 0)

**소요 10분.** DB 도 컨테이너도 필요 없다. §A-2 만 되면 즉시 가능.

```bash
cd backend

# B-1. dj-core 우회 목록 (티켓 확인항목 1)
python - <<'PY'
import inspect, core.base as m
src = inspect.getsource(m)
for kw in ("performance_bypass_models", "grid_models", "bypass"):
    print(f"--- {kw}: {src.count(kw)}회")
print(src[:8000])
PY

# B-2. created_by__isnull OR 조건 (티켓 확인항목 2) ★ W0-13 의 설계를 가르는 입력
python -c "import inspect,core.base as m; s=inspect.getsource(m); print('created_by__isnull:', s.count('created_by__isnull'))"

# B-3. A/B 베이스 사용 실측
python - <<'PY'
import django, os
os.environ.setdefault("DJANGO_SETTINGS_MODULE","config.settings"); django.setup()
from django.apps import apps
import core.base, common.base_model
A, B = core.base.BaseModelWithGroup, common.base_model.BaseModelWithGroup
for base, name in ((A,"core.base"), (B,"common.base_model")):
    ms = [m._meta.label for m in apps.get_models() if issubclass(m, base)]
    print(f"{name}: {len(ms)}\n  " + "\n  ".join(sorted(ms)))
PY
```

**기입처**: `docs/agent/evidence/W0-11/dj-core-findings.md` **§5**

> ### ★ B-2 의 결과가 W0-13 의 작업량을 배로 가른다 (WP-1 EXIT §7 신규 7-1)
>
> | B-2 결과 | W0-13 의 설계 | 작업량 |
> |---|---|---|
> | **0회** | `common.base_model` 쪽 2모델만 고치면 끝 | 작다 |
> | **1회 이상** | `is_system` 을 dj-core 쪽에도 요구하게 되는데 **dj-core 는 §0.4 금지구역**이다 → 설계가 W0-14 우회로 바뀐다 | 배 이상 |
>
> **이 숫자를 적기 전에는 W0-13 의 ② 이후를 착수하지 않는다.**

**[동승 10분]** `delivery/services/status_mapping_service.py` 의 주석 7개가 **실재하지 않는
보호를 주장**하는지 확인 (WP-1 EXIT §7 신규 7-2). 읽기만 — §0.4 금지구역이라 수정 금지.

---

## §C. 테스트 실행 — W0-3 · W0-2 · W0-14 · W0-12

**소요 40분.** DB 필요.

```bash
cd .. && docker compose up -d db redis        # 또는 사내 DB 접속 설정
cd backend
python manage.py migrate --noinput            # 스키마 준비
```

### C-1. 테넌트 격리 스위트 (W0-3 · W0-2)

```bash
python manage.py test tests.test_tenant_isolation -v 2 2>&1 | tee ../docs/agent/evidence/W0-3/run.log
```

> ⚠️ **W0-2 의 정본 `verify` 에 적힌 `BypassListTest` 는 실재하지 않는다.** 실측 명령은 이것이다:
>
> ```bash
> python manage.py test tests.test_tenant_isolation.TenantIsolationRegistryTest.test_bypass_list_does_not_grow -v 2
> ```

**예상 결과 — 미리 못박는다** (`evidence/W0-3/coverage.md` §3):

| 테스트 | 예상 | 실패 시 귀속 |
|---|---|---|
| `test_registry_covers_all_isolatable_models` | **실패 확정** (미등록 11종) | W0-14 |
| `test_unisolated_set_has_not_grown` | 통과 예상 | 실패 = 새 비격리 모델 유입 |
| `test_bypass_list_does_not_grow` | 통과 예상 | 실패 = **W0-2 회귀** |
| `test_null_created_by_is_not_globally_visible` | 판정 불가 (dj-core 매니저) | W0-13 |
| `TenantIsolationAPITest` 5건 | 판정 불가 (`api_base` 미확인) | 404 면 **테스트가 아니라 `api_base` 를 고친다** |

> **초록이 아닌 것이 정상이다.** WP-0 의 goal 은 "격리 완결"이 아니라 "verify-pending 종결"이고,
> **실패를 분류해서 WP-1 입력으로 넘기면** 임무는 끝난다.
> **절대 금지 #5 — 테스트를 고치거나 skip 하지 않는다.**

**기입처**: `evidence/W0-3/coverage.md` **§4** 여섯 칸 (마지막 칸 = dj-core 안에 있던 격리 대상 수)

### C-2. 라우트 스코프 누락 탐지 (W0-14 · W0-12)

```bash
python manage.py test tests.test_route_tenant_scope -v 2 2>&1 | tee ../docs/agent/evidence/W0-14/run.log
grep '\[TENANT_SCOPE\]' ../docs/agent/evidence/W0-14/run.log
```

| 테스트 | 예상 | 의미 |
|---|---|---|
| `test_enumerator_finds_routes` | **불확실** | 열거기가 API 인스턴스 18개를 못 찾으면 여기서 먼저 깨진다 — **그러라고 넣은 테스트다** |
| `test_all_routes_are_tenant_scoped` | 통과 (대장 최초 생성) | `route_baseline.json` 이 만들어진다 |
| `ScopeDecoratorIntegrationTest` 2건 | **불확실** | **이 둘이 `@tenant_scoped` 롤아웃 가부를 정한다** (P-W0-14-1) |
| `ServiceLayerGroupSelectionTest` | 통과 예상 | W0-12 dod ③ 대체 경로 |

```bash
# ★ 생성된 대장을 반드시 커밋한다 — 안 하면 다음 실행이 또 '최초 생성'이 되어 계측이 죽는다
git add backend/tests/route_baseline.json
git commit -m "chore(test): 라우트 스코프 대장 최초 생성 [W0-14]"
```

**기입처**: `evidence/W0-14/coverage.md` **§3**

---

## §D. 마이그레이션 — W2-1 ⚠ dry-run 먼저

**소요 20분.** **순서를 바꾸지 않는다.** dry-run 리포트 없이 실행하면 hard_stop(`data-destructive`).

```bash
cd backend

# D-1. dry-run 리포트를 먼저 만들고 먼저 커밋한다
python manage.py makemigrations stream_monitors --dry-run -v 2 \
  2>&1 | tee ../docs/agent/evidence/W2-1/makemigrations_dryrun.log
cd .. && git add docs/agent/evidence/W2-1/makemigrations_dryrun.log
git commit -m "chore(migration): DetectionEvent dry-run 리포트 [W2-1]"

# D-2. 실제 생성 + SQL 보존
cd backend
python manage.py makemigrations stream_monitors
python manage.py sqlmigrate stream_monitors <생성된번호> \
  > ../docs/agent/evidence/W2-1/forward.sql

# D-3. 적용 + 잔여 확인
python manage.py migrate stream_monitors
python manage.py makemigrations --check --dry-run && echo "잔여 마이그레이션 0 — dod OK"
```

> **기존 컬럼 삭제가 리포트에 보이면 거기서 멈춘다.** 영향 행 수를 세어 보고하고
> 사람 판정을 받는다 (STOP: destructive-migration).

---

## §E. 프론트 빌드 격리 검증 — W0-4

**소요 20분.** §A-3 선행 필수.

```bash
cd frontend

# E-1. 프로덕션 빌드 — 데모가 없어야 한다
VITE_ENABLE_DEMO=false npm run build
grep -rlE 'mockupDemoUi|setup-demo-(file|url)' dist/assets ; echo "^ 0건이어야 통과"

# E-2. 대조군 — 게이트가 '실제로 작동하는지' 증명한다
VITE_ENABLE_DEMO=true npm run build
grep -rlE 'mockupDemoUi' dist/assets ; echo "^ 여기서는 나와야 한다"
```

> **E-2 를 생략하지 않는다.** E-1 만 하면 "게이트가 막았다"와 "빌드가 원래 그랬다"를
> 구별할 수 없다. 두 번 빌드해야 증거가 된다.

**기입처**: `evidence/W0-4/README.md`

---

## §F. DB 집계 — W0-13 ① (§B-2 결과 확인 후)

**소요 15분.**

```bash
cd backend
python - <<'PY'
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings"); django.setup()
from django.apps import apps

print(f"{'model':55} {'total':>8} {'null_cb':>8} {'pct':>6}")
rows = []
for m in apps.get_models():
    names = {f.name for f in m._meta.get_fields()}
    if "created_by" not in names:
        continue
    if not ({"groups", "group"} & names):      # 테넌트성 모델만
        continue
    mgr = m._base_manager                       # ★ 필터를 우회해서 진짜 수를 센다
    try:
        total = mgr.count()
        nulls = mgr.filter(created_by__isnull=True).count()
    except Exception as e:
        print(f"{m._meta.label:55} ERROR {e}"); continue
    pct = (100.0 * nulls / total) if total else 0.0
    rows.append((m._meta.label, total, nulls, pct))
for label, total, nulls, pct in sorted(rows, key=lambda r: -r[2]):
    print(f"{label:55} {total:8d} {nulls:8d} {pct:5.1f}%")
print(f"\n합계 NULL 행: {sum(r[2] for r in rows)} / {sum(r[1] for r in rows)}")
PY
```

> **`_base_manager` 를 쓰는 것이 핵심이다.** `objects` 로 세면 세는 행위 자체가
> `CustomManagerGroup` 필터를 지나 **결함이 결함을 숨긴다.**

**기입처**: `evidence/W0-13/impact.md` **§5**
**백필(③)은 하지 않는다** — 되돌릴 수 없어 보류된 2건 중 하나. dry-run 리포트 선행 필요.

---

## §G. 동승 작업 — 방문 1회를 아낀다

### G-1. W0-9 개발 이미지 저장 (선택 · 30분) — **적체를 영구히 없앤다**

```bash
docker compose build
docker save $(docker compose config --images | tr '\n' ' ') > guardianx-dev-images.tar
```

> 이것을 해두면 **다음부터 사외에서도 테스트가 돌아** verify-pending 적체가 사라진다(D-202).
> 이번 방문에서 가장 이자가 큰 항목이다.

### G-2. W0-1b 실키 재발급 (사내망 무관 · 병행 가능)

15개 항목을 **각 발급처에서 폐기 후 재발급**한다.

```
frontend: VITE_KAKAO_API_KEY · VITE_GOOGLE_MAPS_API_KEY ·
          VITE_TURN_USERNAME · VITE_TURN_PASSWORD · VITE_CGS_APIKEY
backend : DB_PASSWORD · MINIO_ACCESS_KEY · MINIO_SECRET_KEY ·
          SMTP_USERNAME · SMTP_PASSWORD · GCS_APIKEY ·
          OPENSEARCH_USERNAME · OPENSEARCH_PASSWORD ·
          KAKAO_API_KEY · ANYANG_SERVICE_KEY(발급기관 문의)
```

- ⚠️ **D-003**: `GCS_APIKEY`(서버)와 `VITE_CGS_APIKEY`(클라이언트)를 **다른 값**으로 발급한다.
  클라이언트 키는 권한 최소 + Referer/도메인 제한을 건다.
- ⚠️ 브라우저 번들에 실렸던 `VITE_*` 는 **이미 공개된 것으로 간주**한다. 예외 없이 폐기.
- **dod 증거**: 구 키로 API 호출 시 **401/403** 을 확인한 캡처. "재발급했다"는 증거가 아니다.
- 🚫 `.env.example` 에 실값을 적지 않는다. 실값은 운영 시크릿 저장소로만.

---

## 방문 종료 체크리스트

| # | 항목 | 티켓 | 완료 |
|---|---|---|---|
| 1 | `import core.base` 성공 | (전제) | ☐ |
| 2 | `package-lock.json` **커밋됨** | W0-8 | ☐ |
| 3 | `dj-core-findings.md` §5 기입 (**B-2 숫자 포함**) | W0-11 | ☐ |
| 4 | `coverage.md`(W0-3) §4 여섯 칸 기입 + `run.log` 저장 | W0-3 · W0-2 | ☐ |
| 5 | `coverage.md`(W0-14) §3 기입 + `route_baseline.json` **커밋됨** | W0-14 · W0-12 | ☐ |
| 6 | dry-run 리포트 **선커밋** → 마이그레이션 적용 → `--check` exit 0 | W2-1 | ☐ |
| 7 | 빌드 2회(false/true) 결과 기입 | W0-4 | ☐ |
| 8 | `impact.md` §5 집계 기입 | W0-13 ① | ☐ |
| 9 | (선택) 이미지 tar 확보 | W0-9 | ☐ |
| 10 | 실키 15개 재발급 + 구 키 401/403 확인 | W0-1b | ☐ |

**하지 않고 돌아온다** (되돌릴 수 없어 보류 — 사람 판정 대기):

- W0-13 ③ `created_by` 백필 · `is_system` 스키마 변경
- `@tenant_scoped` 를 실 컨트롤러에 부착 (P-W0-14-1 — §C-2 의 통합테스트 2건이 초록이 된 뒤)

---

## 돌아온 뒤 — 에이전트가 이어서 하는 일

1. 위 기입 결과를 읽고 **WP-0 EXIT §1 판정을 "부분적으로 참" → 재판정**
2. **WP-1 EXIT §1 판정을 "거짓" → 재판정** (goal 의 최종 증명은 `TenantIsolationAPITest`)
3. 통과한 티켓 `verify-pending` → `done`, 실패는 **분류해서 귀속 티켓에 blocker 기록**
4. §B-2 결과로 **W0-13 설계 확정** (WP-1 EXIT §7 신규 7-1)
5. 두 EXIT 재제출 → **사람 승인 → WP-2 착수**

> 이 방문이 없으면 WP-0 은 영구히 "부분적으로 참", WP-1 은 영구히 "거짓"으로 남는다.
> **그 상태 위에 WP-2 이후를 쌓는 것이 v4.0 이 막으려던 바로 그 일이다**(D-215).
