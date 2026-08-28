# -*- coding: utf-8 -*-
"""K3 역할별 대시보드 프레임 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다. `scripts/verify_layers.py` 가
그 밖의 import 를 exit 1 로 막는다 (D-278 · DA-04 §1-4).

    from kernels.k3_dashboard import get_preset, resolve_layout   # 이렇게 쓴다
    from dashboard.models import DashboardPanel                   # 이러면 CI 가 막는다

목록은 **DA-04 §2 K3 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k3_dashboard_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서** 고친다.

★ **위젯이 아니라 프레임이 커널이다.** 위젯의 내용은 여기 없다 —
  여기 있는 것은 "어느 화면인가"(프리셋)와 "각 칸이 어떤 상태인가"(5상태 주입)뿐이다.
"""
from kernels.k3_dashboard.exceptions import (
    InvalidLayoutInput,
    K3Error,
    NotImplementedYet,
)
from kernels.k3_dashboard.presets import (
    FALLBACK_PRESET,
    SETTING_WIDGETS,
    Preset,
    Visibility,
)
from kernels.k3_dashboard.schemas import (
    SERVER_EMITTED_STATES,
    PanelView,
    PresetView,
    WidgetState,
)
from kernels.k3_dashboard.services import (
    FIVE_STATES,
    get_preset,
    resolve_layout,
    widget_permission,
)

__all__ = [
    # DA-04 §2 K3 공개 면 3개
    "get_preset",
    "resolve_layout",
    "widget_permission",
    # 검수 보조 — "5상태 100%" 를 세지 않고 **보여 준다**
    "FIVE_STATES",
    # 나가는 값의 모양
    "PresetView",
    "PanelView",
    "WidgetState",
    "Preset",
    "Visibility",
    # 오류 계약
    "K3Error",
    "InvalidLayoutInput",
    "NotImplementedYet",
    # 계약이 정한 것 — 화면·시험·검수가 **같은 값**을 본다 (D-212)
    "SETTING_WIDGETS",
    "SERVER_EMITTED_STATES",
    "FALLBACK_PRESET",
]
