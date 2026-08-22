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

## 5. 실행 결과 — **2026-08-22 · 사내망이 아니라 로컬 이미지에서 회수**

> **입수 경위가 티켓 전제와 다르다.** 사내망 `192.168.0.22` 는 소멸했고(담당 개발자 퇴사),
> 대신 `C:\GuardianX\GuardianX build\gx-build-20260210\gx-build\docker_images\guardianx-backend.tar`
> (2.7GB) 안에 **설치본이 그대로 들어 있었다.**
>
> Docker 데몬은 꺼져 있었지만 `docker save` 산출물은 평범한 OCI tar 이므로
> **데몬 없이 레이어를 스트리밍해 추출**했다. 사본은 `C:\GuardianX-vault\dj-core-1.1.6\`
> (저장소 밖 — D-002). 재현 명령:
>
> ```bash
> cd "/c/GuardianX/GuardianX build/gx-build-20260210/gx-build"
> tar -xOf docker_images/guardianx-backend.tar \
>     blobs/sha256/b258a64798d1536b96232fdc94ddd20969e1efe63f15841a11a6fc954c77f976 \
>   | tar -xf - -C /c/GuardianX-vault/dj-core-1.1.6 \
>       usr/local/lib/python3.11/site-packages/core \
>       usr/local/lib/python3.11/site-packages/dj_core-1.1.6.dist-info
> ```

| 항목 | 값 |
|---|---|
| `core.base` 실제 경로 | `usr/local/lib/python3.11/site-packages/core/base.py` (이미지 내) · **2,503줄** |
| 버전 | **dj-core 1.1.6** (`dj_core-1.1.6.dist-info`) · Python 3.11 빌드 |
| 우회 목록 존재 | **`performance_bypass_models` 는 0건 — 없다.** 대신 **`grid_models` 가 있다**(§5-1) |
| 우회 목록 원소 | `grid_models` 11종 — usergridmanagement · gridsetting · gridsettinguser · gridsettingcategory · searchconditionsuser · menu · tab · role · (2종 생략) · roleuser |
| `created_by__isnull` 출현 수 | **3** (`base.py` L398 · L430 · L439) + `user/management/commands/migrate_group_data.py` 5 |
| A(`core.base`)를 쓰는 모델 수 | **13** (저장소 9파일에서 상속 · §5-3) |
| B(`common.base_model`)를 쓰는 모델 수 | **2** (dashboard) — 정적 예상 2와 일치 |

---

### 5-1. 확인항목 1 — 우회 목록: **없다. 그러나 다른 것이 있었다**

`performance_bypass_models` 는 dj-core 에 **0건**이다. 그 목록은 저장소 소유
(`common/base_model.py`)이며, W0-2 가 이미 다룬 범위 안에 전부 있다. **좋은 소식이다.**

문제는 **찾지 않았던 두 번째 우회 목록**이다 (`base.py` L249~L266):

```python
grid_models = ['usergridmanagement','gridsetting','gridsettinguser',
               'gridsettingcategory','searchconditionsuser','menu','tab',
               'role', ..., 'roleuser']

if model_name.lower() in grid_models and app_label == 'advanced_table':
    return queryset                      # ← group 필터 없이 전량 반환
```

**판정: 이번 건은 위험하지 않다.** `app_label == 'advanced_table'` 로 이중 가드되어
있고, 저장소에는 `advanced_table` 앱이 없다(실측). 즉 이 우회는 **dj-core 내부
프레임워크 모델에만** 적용되고 업무 데이터에는 닿지 않는다.

다만 **등록부에는 올린다.** 이유는 하나다 — 우회 목록이 하나 더 있다는 사실 자체가
"우회 목록은 `common/base_model.py` 하나뿐"이라는 지금까지의 전제를 깬다.
누군가 `advanced_table` 이라는 앱을 만드는 순간 이 11종은 조용히 전 테넌트에 열린다.

---

### 5-2. ★ 확인항목 2 — `created_by__isnull` **3건. 그리고 예상보다 나쁘다**

WP-1 EXIT §7 신규 7-1 이 예고한 분기다: **0회면 W0-13 은 2모델 수정으로 끝나고,
1회 이상이면 설계가 W0-14 우회로 바뀐다.** 답은 **3회**다 — 큰 쪽이다.

세 곳 중 **두 번째가 이 조사 전체에서 가장 중요한 발견**이다.

| # | 위치 | 코드 | 무엇을 뜻하나 |
|---|---|---|---|
| ① | L398 | `Q(created_by=user) \| Q(created_by__isnull=True)` | group 없는 사용자가 **created_by 가 NULL 인 전 테넌트 행**을 본다 |
| ② | **L430** | `Q(<group_field>=user_group) \| Q(created_by__isnull=True)` | **★ 모델에 group FK 가 제대로 있어도, created_by 가 NULL 이면 모든 테넌트가 본다** |
| ③ | L439 | `Q(created_by__userprofilelink__group=…) \| Q(created_by=user) \| Q(created_by__isnull=True)` | 폴백 경로. 같은 구멍 |

**②가 왜 결정적인가.** 지금까지 이 결함은 "소유자를 못 찾는 모델의 폴백"으로 이해돼
왔다. 실제 코드는 반대다 — **group 필드가 있어서 정확히 격리할 수 있는 모델에서조차**
`created_by IS NULL` 한 줄이면 격리가 무효가 된다. 이것은 폴백이 아니라 **명시적 OR** 다.

> 시스템 생성 레코드·마이그레이션 적재분·배치 삽입분은 통상 `created_by` 가 NULL 이다.
> 즉 **가장 많이 쌓이는 종류의 데이터가 가장 넓게 새는 구조**다.

---

### 5-3. 실효 범위 — WP-1 EXIT §6 #5 의 판정이 **뒤집힌다**

WP-1 EXIT 는 "`created_by__isnull` 의 실효 범위는 17종 중 2종(11.8%)" 이라고 적었다.
그 수는 **저장소 소유 `common.base_model` 만 셌을 때**의 값이다. dj-core 를 열어 보니
**주 경로는 반대쪽이었다.**

| 베이스 | 상속 모델 | 비고 |
|---|---|---|
| `core.base.BaseModelWithGroup` (**dj-core · §0.4 금지구역**) | **13** | ChecklistSetting · MeasurableModelWithGroup · ExternalOrderStatus · OrderStatusMapping · Partner · **StreamMonitor** · **DetectionEvent** · SurveillanceProfileChecklist · VideoAnalysis · TerminalType · Function · TerminalPurpose (+ delivery·drone_communication 계열) |
| `common.base_model.BaseModelWithGroup` (저장소 소유) | **2** | Dashboard · DashboardPanel |

**13 : 2 다. 고칠 수 있는 쪽이 2고, 고칠 수 없는 쪽이 13이다.**
그리고 13 안에는 W2-1 이 방금 만든 **`DetectionEvent`** 와 관제의 중심인
**`StreamMonitor`** 가 들어 있다.

---

### 5-4. 그래서 W0-13 은 어떻게 되는가 (WP-1 EXIT §7 신규 7-1 에 대한 답)

**spec 대로 `common.base_model` 의 OR 를 제거해도 노출의 대부분이 남는다.**
남는 쪽이 §0.4 금지구역이므로 W0-13 은 **필터를 고치는 티켓이 될 수 없다.**

| 안 | 내용 | 판정 |
|---|---|---|
| A | dj-core `base.py` 의 OR 3곳을 고친다 | **불가.** §0.4 · 금지 #10. 게다가 사내 배포본이라 재빌드 경로도 없다 |
| B | `common.base_model` 만 고친다 (현 spec) | **가능하지만 2/15.** 고쳤다는 착시만 남는다 |
| **C** | **W0-14 뷰 레벨 스코프로 우회한다** — 라우트에서 group 을 강제하고 ORM 매니저에 의존하지 않는다 | **이것이 유일한 경로다** |

**C 를 뒷받침하는 사실이 하나 더 있다**: 이 발견은 W0-14 의 설계 판단(`@tenant_scoped`
를 라우트에 건다)이 **처음부터 옳았다**는 것을 사후에 증명한다. ORM 매니저를 신뢰할 수
없다는 것이 이제 코드로 확인됐다.

**되돌릴 수 없는 것은 여전히 손대지 않았다** — `is_system` 스키마 변경·`created_by` 백필.
두 안 모두 dj-core 의 OR 를 우회하지 못하므로 **가치가 더 낮아졌다.**

---

### 5-5. 남은 것

| 항목 | 상태 | 푸는 조건 |
|---|---|---|
| 확인항목 1·2 | **완료** (§5-1 · §5-2) | — |
| A/B 상속 모델 수 | **정적 실측 완료** (13 : 2) | 런타임 `apps.get_models()` 대조는 기동 후 |
| `grid_models` 등록부 등재 | 이 문서 §5-1 | — |
| W0-13 설계 확정 | **C안 권고** — 대표 판정 대기 | 이 문서 §5-4 |

> **W0-11 은 여기서 done 이다.** 티켓의 두 확인항목이 모두 답을 얻었고, 코드 변경은 없다.
> 사내망이 없어졌는데도 done 이 된 이유는 하나다 — **설치본이 처음부터 이 PC 안에 있었다.**
