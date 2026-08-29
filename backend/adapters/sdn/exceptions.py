# -*- coding: utf-8 -*-
"""SDN 어댑터의 오류 계약.

**200 + {"success": false} 를 만들지 않는다** (W0-18 · `docs/contracts/api-error-and-auth.md`).
이 저장소는 권한 거부를 200 으로 내보내던 구조를 가지고 있었고, 그중 8개 라우트는
**거부 사실이 아예 소멸**해 조용히 성공처럼 보였다. 신규 어댑터는 그 전철을 밟지 않는다.
"""
from __future__ import annotations


class SdnError(Exception):
    """SDN 어댑터 계열의 뿌리. App 은 이것만 잡아도 된다."""


class SpecNotReceived(SdnError):
    """명세를 못 받아 **아직 만들 수 없는 것**을 불렀다.

    이 예외는 결함이 아니라 **상태**다. 기술 문제가 아니라 계약 이행 문제이고
    (계약 3조2항 · 기한 2026-08-25 경과), 개발로는 풀 수 없다.

    ★ 메시지에 **무엇이 비었는지**를 실어 보낸다. "SDN 없음" 만 남는 로그는
      다음 사람에게 아무것도 알려 주지 않는다 — 미수령 A 등급 항목이 함께 찍히면
      그 로그 한 줄이 곧 독촉 근거가 된다.
    """

    def __init__(self, *, interface: str, missing=()):  # noqa: D107
        self.interface = interface
        self.missing = tuple(missing)
        detail = "\n".join(
            f"      · [{r.grade}] {r.key} {r.what} — 없으면: {r.blocks}"
            for r in self.missing
        )
        super().__init__(
            f"{interface} 어댑터는 아직 만들 수 없다 — 에스비정보기술의 SDN 컨트롤러 "
            f"API 명세 미수령(계약 DEV-SBIT-GX-20260810 3조2항, 기한 2026-08-25 경과).\n"
            f"    Mock 조차 만들 수 없다: I-1~I-5 의 필드 이름과 타입이 있어야 한다"
            f"(DA-02 §0). 추측한 필드 위의 어댑터는 재작업이 확정된다 (D-280).\n"
            f"    미수령 차단 항목 {len(self.missing)}건:\n{detail}\n"
            f"    해소는 개발이 아니라 **명세 수령**이다 — 대표 조치(계약 6조3항 기한 연장 "
            f"통지) 사안이며, 문안은 PRD v2.3 §5 에 있다."
        )


class SdnUnavailable(SdnError):
    """명세는 받았으나 **지금 저쪽이 안 된다** (연결·인증·타임아웃).

    `SpecNotReceived` 와 **다른 예외인 것이 요점이다**: 하나는 "만들 수 없다" 이고
    다른 하나는 "만들었는데 지금 안 된다" 다. 한 예외로 뭉치면 장애 대응이
    계약 독촉과 같은 칸에 들어간다.

    저하 운전(D-291 규약 ④)의 갈림도 여기서 난다 — 이 예외는 **핵심 경로를 죽이지
    않는다.** 화재·침수 판정과 알림은 SDN 없이 완결된다.
    """
