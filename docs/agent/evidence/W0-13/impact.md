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

## 5. 집계 결과 — **2026-08-22 · DB 를 띄우지 않고 냈다**

> **§4 의 스크립트를 쓰지 않았다.** 그것은 `django.setup()` → `apps.get_models()` →
> `_base_manager.count()` 경로라 dj-core + Postgres + 컨테이너 셋이 다 있어야 하고,
> 그 셋이 없어서 이 집계는 **열두 스프린트 동안 한 번도 돌지 못했다.**
>
> 대신 **운영 DB 덤프를 직접 읽었다.** `pg_dump` 의 COPY 형식은 NULL 을 `\N` 으로 적으므로,
> 컬럼 목록에서 `created_by_id` 의 위치를 찾아 그 열이 `\N` 인 행을 세면 된다.
>
> ```bash
> python scripts/scan_dump_created_by.py \
>   "C:/GuardianX/GuardianX build/gx-build-20260210/gx-build/database/02_database_gx_deploy.sql"
> ```
>
> **이 방식이 오히려 정확하다.** `objects` 로 세면 세는 행위 자체가 `CustomManagerGroup`
> 필터를 지나 **결함이 결함을 숨긴다**(그래서 §4 도 `_base_manager` 를 못박았다).
> 덤프는 매니저를 아예 통과하지 않으므로 그 함정이 원천적으로 없다.
>
> 전체 출력: `evidence/W0-13/dump_scan.txt` (141줄)

---

### 5-1. 총계 — **65.9%**

| 구분 | 값 |
|---|---|
| COPY 블록 (표) | 211 |
| `created_by` 보유 표 | 163 |
| 그중 **테넌트성** (group 컬럼 보유) | **159** |
| **테넌트성 표의 `created_by IS NULL` 행** | **29,971 / 45,499 = 65.9%** |
| NULL 이 1건 이상인 테넌트성 표 | **81** |
| **행 전체가 NULL 인 테넌트성 표** | **56** |

> **운영 데이터의 3분의 2가 소유자 없이 들어 있다.**
> 그리고 dj-core `base.py` L430 의 `Q(group=user_group) | Q(created_by__isnull=True)` 는
> **그 3분의 2를 모든 테넌트에 열어 준다** (W0-11 §5-2).
>
> 이 숫자가 W0-13 을 "정리 작업"에서 **"이 시스템의 다중 기관 격리는 지금 성립하지
> 않는다"** 로 바꾼다.

### 5-2. 상위 10 — 무엇이 새는가

| 표 | 전체 | NULL | 비율 | 무엇인가 |
|---|---:|---:|---:|---|
| `surveillance_missionwaypoint` | 8,877 | **8,877** | **100%** | **임무 경로점 전량.** 어느 기관이 어디를 비행했는지 |
| `orders_orderhistory` | 5,882 | 5,696 | 96.8% | 주문 이력 |
| `terminals_terminal` | 5,686 | 3,399 | 59.8% | 터미널 — W0-2 가 우회 목록에서 빼낸 바로 그 모델 |
| `orders_deliveryevent` | 3,033 | **3,033** | **100%** | 배송 이벤트 전량 |
| `delivery_deliveryoperationapprovalchecklist` | 3,013 | **3,013** | **100%** | 운항 승인 점검표 전량 |
| `terminals_routeterminal` | 2,062 | 1,807 | 87.6% | 경로-터미널 연결 |
| `advanced_table_gridsetting` | 1,088 | 903 | 83.0% | 그리드 설정 |
| `advanced_table_gridsettinguser` | 3,230 | 896 | 27.7% | 사용자별 그리드 |
| `user_timezone` | 598 | **598** | **100%** | 참조 데이터 (무해) |
| `delivery_deliveryoperationhistory` | 856 | 280 | 32.7% | 운항 이력 |

**1위가 `surveillance_missionwaypoint` 8,877행 전량**인 것이 이 표의 요지다.
비행 경로는 이 제품이 파는 것의 핵심이고, **지금 소유자 표시가 하나도 없다.**

### 5-3. 관제 핵심 모델

| 표 | 전체 | NULL | 비율 | 베이스 |
|---|---:|---:|---:|---|
| `stream_monitors_streammonitor` | 39 | 15 | 38.5% | **`core.base`** (dj-core · 금지구역) |
| `stream_monitors_aimodel` | 4 | **4** | **100%** | — |
| `dashboard_dashboardpanel` | 26 | 18 | 69.2% | **`common.base_model`** (저장소 · 고칠 수 있음) |
| `dashboard_dashboard` | 21 | 0 | 0.0% | `common.base_model` |
| `checklist_setting_category` | 3 | **3** | **100%** | `core.base` |
| `checklist_setting` | 77 | 0 | 0.0% | `core.base` |

**고칠 수 있는 쪽(dashboard 2모델)의 NULL 은 18행이다. 전체 29,971 중 18행.**
이것이 W0-13 을 spec 대로 해도 아무것도 닫히지 않는다는 것의 수치적 확인이다.

---

### 5-4. ★ 이 집계가 §1~§4 의 전제를 어떻게 바꾸나

| 이 문서가 앞서 적은 것 | 실측 후 |
|---|---|
| "실효 범위 17종 중 2종(11.8%)" | **표 159개 중 81개에 NULL 이 있다.** 2종이라는 수는 *저장소 소유 베이스*만 센 것이었다 |
| `created_by IS NULL` 은 예외적 상태 | **기본 상태에 가깝다 — 65.9%.** 예외 처리가 아니라 주 경로다 |
| 백필(③)로 정리 가능 | **3만 행의 소유자를 무엇으로 정할 것인가**가 먼저다. 정할 근거가 없는 행이 대부분이다 |

**백필은 여전히 하지 않는다.** 오히려 가치가 더 낮아졌다 —
백필로 `created_by` 를 채워도 **dj-core L430 의 OR 자체는 남고**, 그 OR 는
`created_by` 가 채워진 행에 대해서도 `group` 조건과 **OR** 로 묶여 있다.
즉 백필은 이 구멍의 입구를 좁힐 뿐 닫지 못한다.

---

### 5-5. 결론 — W0-13 의 설계 (W0-11 §5-4 와 같은 답)

| 안 | 이 집계가 말하는 것 |
|---|---|
| A. dj-core 필터 수정 | **불가** — §0.4 · 금지 #10. 사내 배포본이라 재빌드 경로도 없다 |
| B. `common.base_model` 만 수정 (현 spec) | **29,971 중 18행.** 0.06% 다 |
| **C. W0-14 뷰 레벨 스코프** | **유일한 경로.** ORM 매니저를 신뢰하지 않고 라우트에서 group 을 강제한다 |

**대표 판정 대기 항목** (WP-1 EXIT §7 신규 7-1):
W0-13 을 **C안으로 재정의**할 것인가, 아니면 **W0-14 에 흡수하고 W0-13 을 dropped 로
닫을** 것인가. 후자가 더 정직할 수 있다 — B 를 남겨 두면 "W0-13 done" 이 격리가
됐다는 착시를 만든다.

> **되돌릴 수 없는 것은 손대지 않았다**: `is_system` 스키마 변경 · `created_by` 백필.
> 이번 집계는 **읽기 전용**이었고 운영 DB 에 접속하지도 않았다 — 덤프 파일만 읽었다.
