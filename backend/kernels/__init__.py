# -*- coding: utf-8 -*-
"""L3 Platform 공유 커널 (C-1 · DA-04).

**커널은 L3 에만 산다.** App(L4)·어댑터(L2)는 커널 API 를 **소비만** 한다 — 얇게.
이것은 재사용 편의가 아니라 **IP 방어**다: 커널 로직이 App 으로 새면
"본체=가이온 / 신규 연계=공동"(계약 8조3항)의 경계가 코드에서 소멸한다.

App 이 만질 수 있는 것은 각 커널의 **공개 면**뿐이다 —
`services` · `api` · `schemas` · `contracts` · `exceptions`.
`models` · `repositories` 는 커널의 속이고, 직접 import 하면
`scripts/verify_layers.py` 가 **exit 1** 로 멈춘다 (D-278).

  K1 k1_event      이벤트 — 만들고·모으고·찾고·판정한다   ← 이 App 의 심장
  K2 k2_notify     알림
  K3 k3_dashboard  역할별 대시보드 프레임
  K4 k4_report     보고서 엔진
  K5 k5_trust      신뢰(격리·계측)
  K6 k6_feedback   피드백·계측
  K7 k7_context    컨텍스트 (DA-05)

이름을 더할 때는 `scripts/verify_layers.KERNEL_NAMES` ·
`scripts/verify_tenant_scope.KERNEL_NAMES` · DA-04 §4 표를 **같은 커밋에서** 함께 고친다
— 모르는 커널을 만나면 게이트가 멈춘다 (D-264).
"""
