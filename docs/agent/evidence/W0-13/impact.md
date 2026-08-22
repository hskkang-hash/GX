# W0-13 ① 영향 조사 — `created_by IS NULL` 전 테넌트 노출

**작성** 에이전트 · 2026-08-15 · WP-1 (ENTRY 승인분)
**티켓** W0-13 ① · **상태** verify-pending (행 수 집계는 DB 대기)
**근거 결정** D-209(조사 → 표기 → 백필 → 제거 순서) · D-207 · §0.4

> 티켓 spec: *"① 영향 조사(읽기 전용): `created_by IS NULL` 레코드를 모델별로 센다.
> 결과 → `evidence/W0-13/impact.md`. **여기서 끝내고 커밋한다.**"*

이 파일은 두 가지를 낸다 — **(a) 무엇을 세야 하는지**(정적 확정, 여기서 끝)와
**(b) 어떻게 셀지**(방문 스크립트). (a)가 이번 스프린트의 산출물이고, 그 과정에서
**티켓이 전제하지 않은 사실 하나**가 나왔다(§2).

---

## 0. 측정 방법

```bash
cd backend
# 결함 위치
grep -REn 'created_by__isnull' --include=*.py common/

# 어느 모델이 그 필터를 실제로 지나는가 — 베이스 클래스를 AST 로 판정
python - <<'PY'
import ast, pathlib, collections
rows = collections.defaultdict(list)
for f in sorted(pathlib.Path(".").rglob("models.py")):
    if {"__pycache__", "migrations"} & set(f.parts): continue
    tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    origin = {a.asname or a.name: n.module
              for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module
              for a in n.names}
    for n in tree.body:
        if isinstance(n, ast.ClassDef):
            for b in n.bases:
                bn = getattr(b, "id", getattr(b, "attr", None))
                if bn and "WithGroup" in bn:
                    rows[(origin.get(bn, "?"), bn)].append(f"{f.parent.name}.{n.name}")
for k, v in sorted(rows.items()): print(k, len(v), v)
PY
```

**DB 없이 재현된다.** 행 수만 DB 가 필요하다(§4).

---

## 1. 결함 위치 — `common/base_model.py` 5곳

`CustomManagerGroup.get_queryset()` 이 `Q(created_by__isnull=True)` 를 **OR 로** 붙인다.
생성자가 없는 레코드(시드·마이그레이션·시스템 생성분)가 **전 테넌트에 보인다.**

| 줄 | 분기 | 조건 |
|---|---|---|
| 156 | 요청 캐시 히트 · `user_only` | `Q(created_by=user) \| Q(created_by__isnull=True)` |
| 158 | 요청 캐시 히트 · 그룹 목록 | `Q(created_by__in=…) \| Q(created_by__isnull=True) \| Q(groups=user_group)` |
| 167 | group 없는 사용자 | `Q(created_by=user) \| Q(created_by__isnull=True)` |
| 189 | 그룹 사용자 (최초 계산) | `Q(created_by__in=…) \| Q(created_by__isnull=True) \| Q(groups=user_group)` |
| 193 | 폴백 | `Q(created_by=user) \| Q(created_by__isnull=True)` |

**5곳이다.** 156·158 은 요청 캐시 히트 경로라 189·193 의 조건이 그대로 복제돼 있다.
**한 곳만 고치면 캐시가 살아 있는 요청에서 결함이 그대로 남는다** — 이 중복이 이 결함의
실제 위험이며, 티켓 spec 이 "필터"를 단수로 적은 자리다.

---

## 2. ★ 티켓이 전제하지 않은 것 — **이 수정의 실효 범위는 2/17 이다**

`CustomManagerGroup` 은 `objects` 로 **어디에 붙는가.** 실측 결과 단 한 곳이다.

```python
# common/base_model.py:201-208
class BaseModelWithGroup(BaseModel):
    groups = models.ManyToManyField(UserGroup, ...)
    objects = CustomManagerGroup()          # ← 이 매니저를 쓰는 모델만 영향을 받는다
```

그리고 이 저장소의 group 보유 모델 **17종**은 베이스가 셋으로 갈린다.

| 베이스 | 모델 수 | 이 결함의 영향 | 모델 |
|---|---|---|---|
| **`common.base_model.BaseModelWithGroup`** (이 저장소) | **2** | **받는다** | `dashboard.Dashboard` · `dashboard.DashboardPanel` |
| `common.measurable_model.MeasurableModelWithGroup` | 4 | **안 받는다** — `core.base.BaseModelWithGroup` 상속 | `flight_log.FlightLog` · `surveillance.SurveyMission` · `surveillance.SurveillanceProfile` · `terminals.Terminal` |
| `core.base.BaseModelWithGroup` (**dj-core · §0.4**) | 11 | **미확인** | `checklist_setting.ChecklistSetting` · `orders.ExternalOrderStatus` · `orders.OrderStatusMapping` · `partner.Partner` · `stream_monitors.StreamMonitor` · `stream_monitors.DetectionEvent` · `surveillance.SurveillanceProfileChecklist` · `surveillance.VideoAnalysis` · `terminals.TerminalType` · `terminals.Function` · `terminals.TerminalPurpose` |

> **W0-13 을 spec 그대로 완수해도 17종 중 2종(11.8%)만 닫힌다.**
> 나머지 15종은 dj-core 의 매니저를 지나며, 그 매니저에 같은 `created_by__isnull` OR 가
> 있는지는 **아무도 본 적이 없다**(W0-11 확인항목 2 · 미확정).

### 2-1. 부수 정정 — 격리 테스트 머리말이 B 사용처를 좁게 적었다

`tests/test_tenant_isolation.py` 머리말은 B 를 *"dashboard.Dashboard, dashboard.DashboardPanel (2개 모델뿐)"* 이라고 적었다.
**모델 수는 정확하다.** 다만 `import` 는 3개 앱에 있다 —
`dashboard/models.py` · `devices/models.py:5` · `operation_settings/models.py:2`.
뒤 둘은 **import 만 하고 상속에 쓰지 않는다**(미사용 import). 혼동을 남기지 않기 위해 적어 둔다.
(파일 수정은 절대금지 #5 — 여기 기록만 한다.)

### 2-2. 부수 발견 — 근거 없는 보호 주석

`delivery/services/status_mapping_service.py` 는 7곳에서
*"`CustomManagerGroup` automatically filters by user's group"* 이라고 주석하고 있다.
그런데 `delivery` 모델은 `core.base` 쪽 베이스를 쓴다. **이 저장소의 `CustomManagerGroup`
은 그 코드에 관여하지 않는다.** 주석이 가리키는 보호가 dj-core 안에 실재하는지는 미확인이며,
**실재하지 않으면 그 서비스는 필터가 없다고 믿고 다시 읽어야 한다.**
`delivery` 는 §0.4 금지구역이라 코드를 건드리지 않았다. W0-11 결과에 따라 판정한다.

---

## 3. 범위 밖 유사 패턴 — **일괄 치환하면 안 된다**

| 위치 | 성격 | 판정 |
|---|---|---|
| `drone_communication/services/group_service.py:101` | `Q(created_by__isnull=True)` 를 조회 조건으로 사용 | 검토 필요. W0-13 ④ 와 함께 본다 |
| `operation_settings/services/operation_settings_service.py:32` | `OperationSettings._base_manager.filter(created_by__isnull=True)` | **의도된 것.** "시스템 기본 설정"을 찾는 코드. `_base_manager` 로 필터를 우회해 명시적으로 조회한다 |
| `operation_settings/tasks.py:27` · `:100` | 동일 | 동일 |

> 뒤 셋은 **`created_by IS NULL` 을 "시스템 소유"의 뜻으로 이미 쓰고 있다.**
> 티켓 spec ②가 도입하라는 `is_system` 이 사실상 여기 암묵적으로 존재하는 셈이며,
> **③ 백필 시 이 세 곳의 대상 레코드를 특정 group 으로 귀속시키면 기본 설정 조회가 깨진다.**
> 백필 계획에 이 예외를 반드시 넣어야 한다 — 이것이 ①을 먼저 하라고 한 이유다.

---

## 4. 행 수 집계 (사내망/DB 방문 시 실행)

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

**`_base_manager` 를 쓰는 것이 핵심이다.** `objects` 로 세면 세는 행위 자체가
`CustomManagerGroup` 필터를 지나 **결함이 결함을 숨긴다.**

## 5. 집계 결과 (방문 후 기입)

_(미기입 — Docker 데몬 미기동 · `192.168.0.22:22` 불통 · 2026-08-15 확인)_

| 모델 | 전체 | `created_by IS NULL` | 비율 | 귀속 판정 |
|---|---|---|---|---|
| `dashboard.Dashboard` | _(미기입)_ | | | |
| `dashboard.DashboardPanel` | _(미기입)_ | | | |
| _(그 외 테넌트성 모델)_ | _(미기입)_ | | | |

**귀속 판정 열이 ③ 백필의 입력이다.** 판정 불가분은 "시스템 소유"로 표기한다(spec ③).

---

## 6. 남은 순서와, ②를 이번에 하지 않은 이유

| 단계 | 내용 | 이번 스프린트 |
|---|---|---|
| ① | 영향 조사 (읽기 전용) | **정적 범위 확정 완료** · 행 수는 대기 |
| ② | `is_system` 도입 (또는 전용 시스템 group) | **하지 않았다** ↓ |
| ③ | 데이터 마이그레이션 백필 (**dry-run 리포트 선행 필수**) | 대기 |
| ④ | 필터 5곳에서 `created_by__isnull` 제거 → `is_system=True` | 대기 |

**②를 앞당기지 않은 이유.** `is_system` 을 `BaseModel` 급에 넣으면 45개 앱에 마이그레이션이
퍼진다. `makemigrations --check` 를 돌릴 수 없는 상태에서(§`dj-core` 부재) 손으로 쓴
마이그레이션을 커밋하는 것은 되돌리기 비용이 크고, 그것을 사내망에서 처음 검증하게 된다.
**4원칙 ②(되돌리기 쉬운 쪽).**

그리고 §2 가 나온 이상 ②의 **설계 자체가 W0-11 결과에 달려 있다.**
dj-core 의 매니저에도 같은 OR 가 있으면 `is_system` 은 A·B 양쪽 베이스에 있어야 하고,
A 는 §0.4 라 손댈 수 없으므로 **뷰 레벨 통제(W0-14)로 우회하는 설계**가 된다.
없으면 B 에만 넣으면 된다. **두 설계의 작업량이 배 이상 차이 난다.**

> **순서 제안: W0-11(방문 10분) → W0-13 ①행수 → ② 설계 확정 → ③④.**
> `is_system` 을 지금 넣으면 W0-11 결과에 따라 되돌려야 할 수 있다.
