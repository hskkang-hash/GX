# W0-11 dj-core 우회 목록 사실 확인 — 중간 보고 (오프라인 확정분)

**작성** 에이전트 · 2026-08-15 · WP-1 (ENTRY 승인분)
**티켓** W0-11 · **상태** verify-pending (사내망 대기)
**결정 근거** D-202(사내망 부재 시 전진) · D-207(주 통제를 뷰로) · §0.4

> **여기서 코드를 고치지 않는다** — 티켓 spec 의 명시 조건. 조사만 한다.

---

## 1. ★ 오프라인에서 확정된 사실 — dj-core 는 이 저장소에 **없다**

티켓 spec 은 *"사내망 접속 시 dj-core 소스를 받아 `core/base.py` 의 `CustomManagerGroup` 을
확인한다"* 고 적었다. **전제가 맞다.** 다만 그 이유가 지금까지 기록된 적이 없어 여기 남긴다.

```bash
$ ls backend/core/
advanced_table
data                          ← 이 둘뿐이다

$ ls backend/core/base.py
ls: cannot access 'backend/core/base.py': No such file or directory

$ python -c "import importlib.util as u; print(u.find_spec('core'))"
ModuleSpec(name='core', loader=None,
           submodule_search_locations=_NamespacePath(['...\\backend\\core']))
                    ^^^^^^^^^^^^^^ loader=None — **네임스페이스 패키지**
```

**`backend/core/` 는 완전한 패키지가 아니라 네임스페이스 조각이다.**
`__init__.py` 가 없어 Python 이 암묵 네임스페이스 패키지로 잡고, 사내망에서 설치되는
`dj-core` 배포본이 **같은 `core` 이름 아래로 합류**하는 구조다.

### 그래서 지금 무엇이 불가능한가

저장소 안 코드가 실제로 import 하는 것 중 **이 트리에 존재하지 않는 것**들:

| import 문 | 어디서 쓰나 | 이 트리에 |
|---|---|---|
| `from core.base import BaseModel, BaseModelWithGroup` | 8개 앱의 모델 | **없음** |
| `from core.user.models import UserGroup, CoreUser, UserSettings` | handover 등 | **없음** |
| `from core.api.v1.auth import CustomJWTAuth` | 컨트롤러 다수 | **없음** |
| `from core.role.permission import path_permission` | 컨트롤러 다수 | **없음** |
| `core.middleware.*` (5종) | `settings.MIDDLEWARE` | **없음** |

> **이 한 줄이 열두 스프린트에 걸친 "오프라인 시험 0건"의 진짜 원인이다.**
> Docker 나 Postgres 가 없어서가 아니다. **`django.setup()` 자체가 ImportError 로 죽는다.**
> DB 를 띄워도 달라지지 않는다. 사내망 pip 인덱스가 유일한 해소 경로다.

---

## 2. 확인 항목별 현황

티켓이 지정한 확인 항목 2개와, 조사 중 추가로 필요해진 1개.

| # | 확인 항목 | 상태 | 지금까지 아는 것 |
|---|---|---|---|
| 1 | `performance_bypass_models`(또는 동등 우회 목록) 존재 여부와 원소 | **미확정** | dj-core 쪽 목록은 본 적이 없다. **이 저장소의 `common/base_model.py` 에는 있고 잔여 7종 전부 프레임워크 모델**이다 |
| 2 | `created_by__isnull` 관련 OR 조건 존재 여부 | **미확정** | 이 저장소 `common/base_model.py` 에는 **5곳**(156·158·167·189·193) |
| 3 | **★ 두 `BaseModelWithGroup` 중 어느 것이 실제로 쓰이는가** | **부분 확정** | 아래 §3 |

---

## 3. ★ 이 티켓이 정말로 답해야 하는 질문 (W0-3 실측의 승계)

`tests/test_tenant_isolation.py` 머리말이 이미 적어 둔 것을 여기서 다시 확인했다.
**이 코드베이스에는 `BaseModelWithGroup` 이 두 개 있다.**

| | A · `core.base.BaseModelWithGroup` | B · `common.base_model.BaseModelWithGroup` |
|---|---|---|
| 소유 | **dj-core (§0.4 금지구역)** | 이 저장소 |
| 사용 앱 | orders · terminals · stream_monitors · surveillance · checklist_setting · delivery · partner · drone_communication **(8개 앱)** | `dashboard.Dashboard` · `dashboard.DashboardPanel` **(2개 모델)** |
| 우회 목록 | **미확인** | 잔여 7종 (프레임워크) |
| `created_by__isnull` OR | **미확인** | 5곳 |

**그리고 W0-2 가 목록에서 뺀 `order`·`terminal` 등은 전부 A 를 쓴다.**

> 즉 **W0-2 의 수정은 그 모델들의 필터링을 바꾸지 못했을 가능성이 높다.**
> W0-2 의 DoD 는 *"목록에서 업무 모델 7종이 사라짐"* 이고 그것은 충족됐다.
> 그러나 **DoD 충족과 노출 차단은 같은 문장이 아니다.**
> 이 사실은 `tickets.yaml` W0-2 blocker 에 이미 기록돼 있으며, 여기서는
> **그 판단이 W0-11 의 조사 결과와 어긋나지 않음**을 확인한 것이다.

**이것이 D-207 의 정당성이다.** dj-core 를 못 고치므로 격리의 주 통제를 뷰로 옮긴다 —
그리고 그것이 W0-14 다. **W0-11 의 결과가 어떻게 나오든 W0-14 는 필요하다.**
반대는 성립하지 않는다: W0-11 이 "A 에도 우회 목록이 있다"로 나오면 W0-14 의 **긴급도만** 올라간다.

---

## 4. 사내망에서 실행할 것 (방문 당일 · 약 10분)

```bash
# 1) dj-core 수령 후 실제 경로 확인
python -c "import core.base as m; print(m.__file__)"

# 2) 우회 목록 (티켓 확인항목 1)
python - <<'PY'
import inspect, core.base as m
src = inspect.getsource(m)
for kw in ("performance_bypass_models", "grid_models", "bypass"):
    print(f"--- {kw}: {src.count(kw)}회")
print(src[:8000])
PY

# 3) created_by__isnull OR 조건 (티켓 확인항목 2)
python -c "import inspect,core.base as m; s=inspect.getsource(m); print('created_by__isnull:', s.count('created_by__isnull'))"

# 4) A/B 사용 실측 — 어느 베이스를 몇 모델이 쓰는가
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

**결과를 이 파일 §5 에 붙이면 W0-11 은 done 이 된다.** 코드 수정은 없다.

## 5. 실행 결과 (사내망 방문 후 기입)

_(미기입 — `192.168.0.22:22` 불통 · 2026-08-15 확인)_

| 항목 | 값 |
|---|---|
| `core.base` 실제 경로 | _(미기입)_ |
| 우회 목록 존재 | _(미기입)_ |
| 우회 목록 원소 | _(미기입)_ |
| `created_by__isnull` 출현 수 | _(미기입)_ |
| A 를 쓰는 모델 수 | _(미기입)_ |
| B 를 쓰는 모델 수 | _(미기입 · 정적 예상 2)_ |

**목록이 실재하면** §0.4 예외 승인 대상이므로 `decisions_pending.yaml` 에
D-207 후속 결정을 올린다 (티켓 spec 의 지시). 그 항목은 **결과를 본 뒤에** 적재한다 —
없는 것을 있다고 가정하고 미리 올리지 않는다.
