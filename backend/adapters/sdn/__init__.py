# -*- coding: utf-8 -*-
"""SDN 어댑터 — **표준만 서 있고 구현은 없다** (D-297 · 대표 지시 2026-08-31).

한 문장
-------
    연결할 자리는 만들어 두고, **연결은 명세가 온 뒤에 한다.**

무엇이 있고 무엇이 없나
-----------------------
    있다  · `SdnPort`            — 계약 [별첨1] §4 가 정한 인터페이스 5종의 포트
          · `QosIntent` 등        — **우리 쪽 말**로 된 요청 의도
          · `ControlReceipt`      — 요청·기록의 모양 (계약 10조1항의 코드판)
          · `requirements`        — 무엇을 받아야 만들 수 있는지의 기계가 읽는 목록
          · `UnavailableSdnPort`  — 부르면 **왜 못 하는지 말하며 멈추는** 자리

    없다  · 엔드포인트 · 필드 이름 · 타입 · 오류 코드 · 인증 방식
          · **Mock 어댑터** — DA-02 §0: "Mock 조차 I-1~I-5 의 필드 이름과 타입이
            있어야 만들 수 있다." 없는 것이 옳고, 있으면 그것이 추측이다 (D-280).

왜 `KERNEL_READY = False` 인가 — **파일이 있는 것과 잴 수 있는 것은 다르다**
---------------------------------------------------------------------------
`tests/e2e/e2e_contract.py` 는 해금을 **import 로** 판정한다: *"티켓 status 는 사람이
쓰고, import 는 코드가 답한다."* 그 원칙은 옳다. 그런데 이 패키지가 import 되는 순간
E2E-3 이 **의무가 되고** E2E-1 의 7단계(SDN QoS)가 열린다 — 잴 수 없는 것을 재라고
요구하게 된다.

그래서 판정을 한 겹 좁혔다: **import 되는가 + 그 모듈이 준비됐다고 말하는가.**
`KERNEL_READY` 는 선언이지만 값싼 선언이 아니다 —

  · `NOT_READY_REASON` 이 비면 `scripts/verify_e2e_contract.py` 가 exit 1 로 멈춘다.
  · 이 값을 True 로 올리는 순간 E2E-3 전체와 E2E-1 7단계가 **자동으로 의무가 된다.**
    구현 없이 올리면 그 시험들이 즉시 실패한다. 즉 거짓말이 통하지 않는다.

  요컨대 "안 됐다" 는 말은 **사유를 요구하고**, "됐다" 는 말은 **시험을 부른다.**

명세가 도착하면 — 할 일 네 가지
-------------------------------
  ① `docs/design/DA-02_SDN_API_매핑서_v0.1_수령요건.md` 의 빈칸을 채워 v1.0 으로 승격
  ② `requirements.py` 의 해당 항목에 `received=True` + 근거(문서명·날짜)
  ③ `SdnPort` 구현체 작성 — **여기서 처음으로** 저쪽 필드 이름이 등장한다
  ④ `KERNEL_READY = True` · `register(구현체)` → E2E-3 이 의무가 된다

★ 그 전까지는 어떤 어댑터도 만들지 않는다. 만들면 재작업이 확정되고 D-280 위반이다.
"""
from __future__ import annotations

from adapters.sdn.exceptions import SdnError, SdnUnavailable, SpecNotReceived
from adapters.sdn.port import (
    PORT_METHODS,
    ControlReceipt,
    LinkStateNotice,
    QosIntent,
    RerouteIntent,
    SdnPort,
    UnavailableSdnPort,
)
from adapters.sdn.requirements import (
    INTERFACES,
    REQUIREMENTS,
    Requirement,
    can_start,
    missing_blocking,
    summary,
)

#: ★ 이 어댑터가 **잴 수 있는 상태인가.** False 인 동안 E2E-3 은 잠겨 있고,
#:   E2E-1 의 7단계(SDN QoS)는 단계표에 **잠김**으로 나온다 — 미측정을 통과로 읽지 않는다.
#:
#:   올리는 조건은 하나다: `missing_blocking()` 이 비고, `SdnPort` 구현체가 등록될 것.
#:   그 둘 없이 올리면 E2E-3 이 즉시 실패한다.
KERNEL_READY: bool = False

#: ★ `KERNEL_READY=False` 일 때 **반드시 채워져 있어야 한다.** 비면 게이트가 exit 1.
#:   "안 됐다" 를 사유 없이 적는 것은 D-264(모르면 멈춘다)가 금지한 모양이다.
NOT_READY_REASON: str = (
    "에스비정보기술의 SDN 컨트롤러 API 명세 미수령. 계약 DEV-SBIT-GX-20260810 3조2항이 "
    "정한 제공 기한(착수 15일 내 · 2026-08-25)이 경과했다. Mock 조차 I-1~I-5 의 필드 "
    "이름과 타입이 있어야 만들 수 있으므로(DA-02 §0) 어댑터 착수 자체가 불가하고, "
    "추측 필드 위의 어댑터는 재작업이 확정된다(D-280). "
    "해소는 개발이 아니라 명세 수령이며 계약 6조3항(협조 지연 시 기한 연장) 사안이다 — "
    "대표 조치 대기(PRD v2.3 §5 발송문). "
    "그동안 화재·침수 시나리오는 SDN 없이 완결되므로 '릴리스 후보(SDN 제외판)' 를 "
    "정식 산출물로 낸다(D-297)."
)

#: 지금 꽂혀 있는 포트. 기본값은 **부르면 멈추는 자리**다 (조용한 성공 금지 · D-290).
_current: SdnPort = UnavailableSdnPort()


def register(port: SdnPort) -> "callable":
    """포트를 꽂는다. **되돌리는 함수를 돌려준다** — `k2_notify.channels.register` 와 같은 규약.

    되돌리기를 함께 주는 이유: 시험이 꽂은 것을 시험이 스스로 뽑게 하기 위해서다.
    전역 상태를 시험이 남기면 다음 시험이 그 상태를 물려받고, 그러면 시험 순서가
    결과를 바꾼다 — 순서가 결과를 바꾸는 시험은 시험이 아니다.
    """
    global _current
    if not isinstance(port, SdnPort):
        raise TypeError(
            f"{type(port).__name__} 은 SdnPort 가 아니다. 실기든 Mock 이든 **같은 "
            f"인터페이스**를 구현해야 설정 한 줄로 갈아끼울 수 있다 (DA-02 §3-5 · D-212)")
    previous, _current = _current, port

    def undo() -> None:
        global _current
        _current = previous

    return undo


def current() -> SdnPort:
    """지금 꽂혀 있는 포트. 부르는 쪽은 이것만 안다 — 실기인지 Mock 인지 묻지 않는다."""
    return _current


def is_ready() -> bool:
    """**잴 수 있는가.** 선언(`KERNEL_READY`)과 실물(등록된 포트)을 함께 본다.

    선언만 보면 사람이 True 로 적어 놓고 구현을 안 할 수 있고, 실물만 보면
    시험이 잠깐 꽂은 것을 준비 완료로 읽는다. 둘 다 참일 때만 참이다.
    """
    return KERNEL_READY and not isinstance(_current, UnavailableSdnPort)


__all__ = [
    # 준비 상태 — E2E 해금이 이것을 본다
    "KERNEL_READY",
    "NOT_READY_REASON",
    "is_ready",
    # 포트
    "SdnPort",
    "UnavailableSdnPort",
    "register",
    "current",
    "PORT_METHODS",
    # 우리 쪽 말
    "QosIntent",
    "RerouteIntent",
    "LinkStateNotice",
    "ControlReceipt",
    # 수령 요건 — 무엇을 받아야 만들 수 있는가
    "INTERFACES",
    "REQUIREMENTS",
    "Requirement",
    "missing_blocking",
    "can_start",
    "summary",
    # 오류 계약
    "SdnError",
    "SpecNotReceived",
    "SdnUnavailable",
]
