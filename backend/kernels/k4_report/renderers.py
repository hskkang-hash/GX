# -*- coding: utf-8 -*-
"""K4 렌더러 — **엔진을 호출 시점에 찾는다** (DA-04 §2 K4).

DA-04 는 엔진을 지목했다: *"엔진: `backend/report_template/`
(`ReportTemplate` · `api.py` · 폰트 다운로더까지 실재)."*
커널이 가져가는 것은 **로직이지 엔진이 아니다** — 엔진은 그대로 두고 감싼다.

왜 최상위에서 import 하지 않나 — 계층 (D-278)
---------------------------------------------
커널(L3)이 App 을 **정적으로** 가져오면 그 커널은 그 App 전용이 되고,
"한 번 개발해 두 번 판다"가 거짓이 된다. 그래서 엔진은 **레지스트리로 갈아 끼우는
어댑터**이고, 기본 어댑터만 호출 시점에 `report_template.utils` 를 찾는다.
`k2_notify/channels.py` 가 발송 업체에 대해 하는 일과 **같은 형**이다.

  ※ 실측 고지 — `scripts/verify_layers.py` 는 지금 이 위반을 **볼 수 없다.**
    그 검사는 `apps.` 로 시작하는 import 를 찾는데, 이 저장소의 App 은 최상위에 있다
    (`report_template`, `dashboard`, …). 즉 App 층 판정 대상이 0건이다
    (D-285 (3) 이 "대상 0건일 때 판정기 자체를 시험했다"고 적은 그 상태).
    **보이지 않는다고 없는 것이 아니므로**, 여기서는 게이트가 아니라 **설계로** 지킨다:
    커널 코드에 App 이름이 나오는 자리를 이 파일 한 곳으로 몰았다.
    검사 확장은 P-ENV-2 로 적재했다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RenderOutcome:
    """렌더 하나의 결과. **예외를 값으로 바꾼다** (K2 `SendOutcome` 과 같은 형)."""

    ok: bool
    pdf: bytes = b""
    reason: str = ""


class Renderer(Protocol):
    """렌더러가 지켜야 하는 것 — 이것뿐이다."""

    name: str

    def render(self, *, html: str) -> RenderOutcome:
        ...


class WeasyPrintRenderer:
    """저장소에 실재하는 엔진 (`report_template.utils.generate_pdf_report_template`).

    ★ 0바이트를 **성공으로 세지 않는다.** 빈 PDF 는 열리기는 하고 내용이 없다 —
      받는 사람은 "보고서가 비었다"로 읽고 시스템은 "생성했다"로 센다.
      그 둘이 갈리는 순간 U2 의 숫자가 거짓이 된다 (D-284 조용한 성공).
    """

    name = "weasyprint"

    def render(self, *, html: str) -> RenderOutcome:
        if not (html or "").strip():
            return RenderOutcome(False, reason="렌더할 HTML 이 비었다")
        try:
            # ★ 호출 시점 import — 위 모듈 독스트링의 이유.
            from report_template.utils import generate_pdf_report_template

            handle = generate_pdf_report_template(html)
            if handle is None:
                return RenderOutcome(False, reason="엔진이 아무것도 돌려주지 않았다")
            try:
                data = handle.read()
            finally:
                with_close = getattr(handle, "close", None)
                if callable(with_close):
                    with_close()
        except Exception as exc:
            log.warning("[K4][RENDER] 실패 err=%s", exc)
            return RenderOutcome(False, reason=f"{type(exc).__name__}: {exc}"[:240])

        if not data:
            return RenderOutcome(False, reason="엔진이 0바이트를 냈다 — 빈 PDF 는 성공이 아니다")
        return RenderOutcome(True, pdf=data)


#: 등록된 렌더러. **여기 없는 렌더러는 없는 렌더러다** (D-285 ②).
REGISTRY: dict[str, Renderer] = {
    WeasyPrintRenderer.name: WeasyPrintRenderer(),
}

#: 기본 렌더러 이름. 바꾸려면 설정이 아니라 **이 줄**을 고친다 — 어느 엔진으로
#: 고객에게 종이가 나가는지는 조용히 바뀌면 안 된다.
DEFAULT_RENDERER = WeasyPrintRenderer.name


class _RendererRegistry:
    """이름 → 렌더러. **테넌트를 만지지 않는다.**

    모듈 최상위 공개 함수로 두지 않는 이유는 `k2_notify/channels.py` 와 같다 —
    `kernels/` 의 최상위 공개 함수는 `*, scope: TenantScope` 를 요구받는다(D-281).
    규약에 면제를 내는 대신 모양을 맞춘다.
    """

    def get(self, name: str | None = None) -> Renderer | None:
        return REGISTRY.get(name or DEFAULT_RENDERER)

    def register(self, renderer: Renderer) -> Callable[[], None]:
        """렌더러를 끼운다. 되돌리는 함수를 돌려준다 — 시험이 전역 상태를 남기지 않게."""
        previous = REGISTRY.get(renderer.name)
        REGISTRY[renderer.name] = renderer

        def undo() -> None:
            if previous is None:
                REGISTRY.pop(renderer.name, None)
            else:
                REGISTRY[renderer.name] = previous

        return undo


_registry = _RendererRegistry()

get = _registry.get
register = _registry.register
