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
    render_html,
    render_period,
)

__all__ = [
    # DA-04 §2 K4 공개 면 3개 + 확장 2개(`render_html` 실재 · `render_period` 미구현)
    #
    # ★ `render_html` 은 **DA-04 §2 K4 표에 아직 없는 이름**이다 (P-125 · 2026-09-10).
    #   표를 고치는 권한이 이 차선에 없어 코드만 먼저 섰고, 그 사실을 여기 적어 둔다 —
    #   적어 두지 않으면 다음 사람이 표와 코드 중 어느 쪽이 뒤처졌는지 못 읽는다.
    #   ⚠ 인계: DA-04 §2 K4 「공개 면」 열에 `render_html`(서식이 표에 없는 1쪽 보고서)
    #     한 줄을 더해야 표와 코드가 같아진다.
    "render",
    "render_html",
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
