# -*- coding: utf-8 -*-
"""K4 보고서 엔진 확장 — **공개 면**.

App(L4)이 만질 수 있는 것은 여기 있는 이름뿐이다 (D-278 · DA-04 §1-4).

    from kernels.k4_report import build_context, render      # 이렇게 쓴다
    from report_template.models import ReportTemplate        # 이러면 경계가 사라진다

목록은 **DA-04 §2 K4 표 그대로**다. 표를 바꾸려면 그 문서와 이 파일과
`tests/test_k4_report_kernel.KernelPublicSurfaceTest.SURFACE` 를 **같은 커밋에서** 고친다.

★ **조치 이력은 K2 의 `DeliveryRecord` 를 그대로 읽는다.** 보고서용으로 다시 적재하지
  않는다 — 두 벌이면 알림과 보고서가 다른 말을 한다 (DA-04 §2 K2 이중 AC).
"""
from kernels.k4_report.exceptions import (
    InvalidReportInput,
    K4Error,
    NotImplementedYet,
    RenderFailed,
)
from kernels.k4_report.schemas import (
    REQUIRED_VARIABLES,
    ActionRow,
    CaptureRow,
    ReportContext,
    TemplateView,
)
from kernels.k4_report.services import (
    DEFAULT_PERIOD,
    build_context,
    list_templates,
    render,
    render_period,
)

__all__ = [
    # DA-04 §2 K4 공개 면 3개 + 확장 1개(미구현)
    "render",
    "build_context",
    "list_templates",
    "render_period",
    # 나가는 값의 모양
    "ReportContext",
    "TemplateView",
    "ActionRow",
    "CaptureRow",
    # 오류 계약
    "K4Error",
    "InvalidReportInput",
    "RenderFailed",
    "NotImplementedYet",
    # 계약이 정한 것 — 시험·검수가 **같은 값**을 본다 (D-212)
    "REQUIRED_VARIABLES",
    "DEFAULT_PERIOD",
]
