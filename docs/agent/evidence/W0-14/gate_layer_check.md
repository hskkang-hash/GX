# 계층 위반 정적 검사 — 실측 (D-278)

**측정** 2026-08-28 · **대상** WP-DA2 착수 조건 (3) · **K1 첫 커밋 전 green 필수**
**게이트** `scripts/verify_layers.py` · **CI** GitHub `layer-check` · GitLab `layer-check` · pre-commit `gx-layers`

---

## 0. 첫 줄 — 분모와 술어를 함께 적는다 (D-274)

```
대상        0개 파일        (술어 = backend/apps/** ∪ backend/kernels/** 의 .py 전수)
계층 위반   0건             (술어 = 아래 §2 의 금지 4규칙)
판정기 대조 14/14           (술어 = 양성 6 · 음성 7 · 파일 경로 1 — D-277)
게이트      exit 0
```

★ **대상이 0건이다.** 그 상태의 "위반 0" 은 초록이 아니라 **아무것도 재지 않은 것**이다.
그래서 이 게이트는 대상이 0건일 때 **판정기 자체를 시험한다**(아래 §3). 그 14건이
이 문서에서 유일하게 의미 있는 초록이다.

---

## 1. 왜 K1 **전에** 세우는가

D-259 의 WP-DA2 착수 조건 (3)이 이것이었고, D-278 이 **K1 전에** 세우라고 확정했다.

`backend/kernels/` 도 `backend/apps/` 도 아직 한 줄도 없다.
나중에 오는 게이트는 이미 쌓인 빚을 만나고, 그러면 래칫으로 잠그는 수밖에 없다 —
`verify_classification.py` 가 빚 113건을 안고 출발한 것이 정확히 그 모양이다.

**여기서만은 빚 0 으로 시작할 수 있다.** K1 의 첫 커밋부터 이 게이트가 서 있으면
래칫이 필요 없고, 위반은 한 건도 태어나지 않는다.
`verify_tenant_scope.py` 를 커널 0줄일 때 세운 것과 같은 계열이다.

**무엇을 지키나** — 재사용 편의가 아니라 **IP 방어**다 (DA-04 §1-1):

> 커널은 L3 Platform 에만 산다. App(L4)·어댑터(L2)는 커널 API 를 **소비만** 한다.
> 커널 로직이 App 으로 새면 **"본체=가이온 / 신규 연계=공동"(계약 8조3항)의 경계가
> 코드에서 소멸한다.**

그리고 DA-04 §1-4:

> 커널의 공개 면은 **서비스 함수**다. App 이 커널의 **모델을 직접 import 하지 않는다.**

이 두 문장은 지금까지 **문서에만** 있었다.

---

## 2. 판정 규칙 4건

| # | 금지 | 사유 |
|---|---|---|
| ① | `backend/apps/**` → `kernels.<k>.<비공개모듈>` | 모델·저장소는 커널의 속이다. 만지면 커널을 바꿀 때 App 이 깨지고 "한 번 개발"이 거짓이 된다 |
| ② | `backend/apps/**` → `kernels.` 를 우회한 커널 경로 / 커널 패키지 통째 | 경로를 우회해도 계층은 그대로다. 통째 import 는 무엇을 쓰는지 코드에 안 남긴다 |
| ③ | `backend/kernels/**` → `apps.**` | **계층 역전.** 커널이 App 을 알면 그 커널은 그 App 전용이고, 재사용 커널이라는 말이 거짓이 된다 |
| ④ | `backend/apps/**` → 다른 App 의 내부 | App 끼리는 커널을 통해 만난다. 직접 결합하면 App 하나를 떼어 팔 수 없다 |

**허용면**: `kernels.<k>` (최상위) · `kernels.<k>.{services, api, schemas, contracts, exceptions}`
`common.**`(L1 공용) · 자기 App 내부 · 상대 import.

> `KERNEL_PUBLIC_MODULES` 에 이름을 더하는 것은 "이 모듈은 커널의 계약이다"라는 **선언**이다.
> `models` 를 넣고 싶어지는 순간이 곧 커널이 새는 순간이므로, 넣지 않는다.

---

## 3. ★ 양성 대조 — 탐지기가 실제로 탐지하는가 (D-277)

착시 4형 ④ 는 "**재는 기계가 작동하나**"이고, 이 게이트는 대상이 0건이라 그 위험이 가장 크다.

### 3-1. 판정기 대조 13건 + 파일 경로 1건 — 전건 OK

```
OK   [app/dsm] kernels.k1_event.models          → 금지①   (커널 모델 직접 — 게이트의 존재 이유)
OK   [app/dsm] kernels.k1_event.repositories    → 금지①   (저장소도 비공개면)
OK   [app/dsm] kernels                          → 금지②   (패키지 통째)
OK   [app/dsm] k1_event.models                  → 금지②   (kernels. 우회)
OK   [app/dsm] apps.other_app.models            → 금지④   (App 간 직접 결합)
OK   [kernel/k1_event] apps.dsm.services        → 금지③   (계층 역전)
OK   [app/dsm] kernels.k1_event                 → 허용    (공개 면 최상위)
OK   [app/dsm] kernels.k1_event.services        → 허용    (서비스 함수 = 공개 면)
OK   [app/dsm] kernels.k2_notify.schemas        → 허용    (스키마는 계약의 일부)
OK   [app/dsm] apps.dsm.internal                → 허용    (자기 App 내부)
OK   [app/dsm] common.tenant_filters            → 허용    (L1 공용)
OK   [kernel/k1_event] common.tenant_scope      → 허용    (커널→공용은 정상)
OK   [kernel/k1_event] kernels.k2_notify.services → 허용  (커널끼리 공개 면 — 막을 근거가 DA-04 에 없다)
OK   파일 경로 대조 — 잡은 것 ['kernels.k1_event.models', 'kernels.k3_dashboard.repositories']
```

**음성 대조 7건을 함께 두는 이유**: 늘 빨간불인 탐지기는 늘 초록인 탐지기와 똑같이 쓸모없다.
막을 근거가 문서에 없는 것(커널↔커널)은 **막지 않는다** — 근거 없는 금지는 규칙이 아니라 취향이다.

### 3-2. 실물 대조 — 진짜 파일을 만들고 게이트를 돌렸다

```
backend/apps/dsm/views.py        from kernels.k1_event.models import Event
                                 from kernels.k1_event.services import record_detection
backend/kernels/k1_event/repo.py from apps.dsm.views import something
```

```
[LAYER] 대상 2개 파일 (apps 있음 · kernels 있음)
[LAYER] 계층 위반 2건 — 멈춘다
  · backend/apps/dsm/views.py:1  import kernels.k1_event.models        [금지①]
  · backend/kernels/k1_event/repo.py:1  import apps.dsm.views          [금지③]
EXIT=1
```

**같은 파일의 `kernels.k1_event.services` 는 잡히지 않았다** — 허용면이 실제로 통과한다는 증명이다.
심은 파일은 지웠다(저장소에 남아 있지 않다). 지운 뒤 재실행 `EXIT=0`.

---

## 4. 어디에 걸었나 — 세 곳, 같은 스크립트

| 자리 | 언제 | 대상 파일 필터 |
|---|---|---|
| pre-commit `gx-layers` | 커밋마다 | `backend/(apps\|kernels)/**.py` · `scripts/verify_layers.py` |
| GitHub Actions `layer-check` | push · PR | 전수 (`--self-test` 포함) |
| GitLab CI `layer-check` | branch · MR | 전수 (`--self-test` 포함) |

의존성이 없다 — `ast` 만 쓴다. **dj-core 없이 어느 러너에서나 돈다.**
D-001 이 CI 를 GitHub·GitLab 양쪽에 선제 배치한 것과 같은 이유로 둘 다 둔다.

---

## 5. 이 게이트가 **못** 하는 것

- **정적 import 만** 본다. `importlib.import_module("kernels.k1_event.models")` 같은
  동적 import 는 못 잡는다. 잡으려면 런타임 훅이 필요하고, 그것은 K1 이 선 뒤에 실측으로 정한다.
- **import 하지 않고 커널 로직을 베껴 쓰는 것**은 못 잡는다. 그것은 게이트가 아니라 리뷰의 몫이다.
- 계층은 보되 **테넌트는 보지 않는다.** 커널 함수의 스코프는
  `verify_tenant_scope.py`(C-3.1)가, 라우트는 트립와이어가 본다. 중복해서 세지 않는다.

---

## 6. 재현

```bash
python scripts/verify_layers.py              # exit 0
python scripts/verify_layers.py --self-test  # 대조 14건 출력
python scripts/verify_layers.py --list       # 파일별 import 전수
```
