# -*- coding: utf-8 -*-
"""주소 어댑터 (FX-5) — **좌표를 사람이 읽는 주소로.** L2 어댑터 (D-298 예외 승인분).

한 문장
-------
    주소는 **보조 정보다.** 주소를 못 얻어도 이벤트는 난다 — 그것이 이 어댑터의
    첫 번째 요구사항이고, 마지막 요구사항이다.

무엇이 있고 무엇이 없나 (D-300 부작위 시험 대상)
------------------------------------------------
    있다  · `AddressPort`        — 좌표 → 도로명 주소의 포트
          · `AddressResult`      — 나가는 값. **상태를 함께 낸다**(D-290)
          · `resolve`            — 부르는 쪽이 쓰는 유일한 함수. **예외를 던지지 않는다**
          · `register`/`current` — 갈아끼우기 자리 (SDN 어댑터와 같은 규약)
          · 타임아웃 상수 · 실패 처리 · 저하 운전

    없다  · **HTTP 구현체** — juso.go.kr 응답의 필드 이름·구조를 **실측하지 않았다.**
            `docs/agent/evidence/DA-05/sources.yaml` 의 `juso_coord2addr` 가 `verified: false`
            이고, D-298 이 못박았다: *"엔드포인트 미상 항목은 포털 활용신청 상세에서
            실측해 채운다. 추정 금지(D-280). 확인 전에는 빈 값으로 두고 어댑터를 만들지
            않는다."* 추측한 필드명 위의 파서는 첫 실호출에서 전부 재작업이 된다.
          · 좌표계 변환 — juso API 가 어느 좌표계를 받는지(WGS84/GRS80TM) 미실측
          · ★ **방향은 판정이 끝났다 — `JUSO_REVERSE_SUPPORTED='no'`** (D-329, 2026-09-06).
            발급된 승인키 2건의 API 유형이 둘 다 「도로명주소 팝업 API」였다. 그것은
            브라우저 UI 위젯이지 서버 조회 API 가 아니다 — **실호출 없이 확정됐다.**
            그리고 FX-5 자체가 **카메라 설치 주소**로 대체됐다(D-330) — 밖에서 사 오려던
            것을 우리는 이미 알고 있었다. 이 어댑터는 지우지 않고 남긴다:
            유형이 다른 키가 생기면 그때 이 자리가 그대로 쓰인다
          · 캐시·재시도 정책 — 재시도 **대상**만 상태로 표시하고, 재시도기는 만들지 않았다

    → 남은 일은 **`AddressPort` 구현 하나**다. SDN 표준과 같은 모양이고 같은 이유다.

그래서 지금 무엇이 도는가 — **저하 운전 전부**
----------------------------------------------
꽂힌 포트가 없으면 `resolve` 는 `status='disabled'` 를 돌려준다. 예외가 아니다 —
여기서 예외를 던지면 부르는 쪽(`record_detection`)이 그것을 감싸야 하고, 감싸는 코드가
늘면 언젠가 한 곳이 빠진다. 그러면 **주소 API 가 이벤트 생성을 끌고 내려간다.**
그 형태를 코드로 불가능하게 만드는 것이 이 파일의 설계다 (C-3.3 · W0-17).

포트가 꽂혀 있고 그것이 죽으면 `status='failed'` 다. `'pending'`(아직 안 함)과
**같은 값으로 두지 않는다** — D-290. 둘을 합치면 재시도 대상 목록이 만들어지지 않는다.
"""
from __future__ import annotations

import abc
import logging
from dataclasses import dataclass

log = logging.getLogger(__name__)

#: ★ 외부 호출의 타임아웃 (C-3.3 · 규약 §2). **기본값을 None 으로 두지 않는다** —
#:   타임아웃 없는 호출 하나가 요청 스레드를 붙잡으면 그것이 곧 장애다.
#:   주소는 보조 정보이므로 짧다: 사람이 알림을 기다리는 시간을 주소가 잡아먹으면 안 된다.
TIMEOUT_SECONDS: float = 2.0

#: ★ **juso 가 우리가 필요한 방향을 주는가** — 3값이다 (D-318 · D-290).
#:
#:   'unknown' 아직 실호출로 확인하지 않았다. **재시도 대상이다**
#:   'yes'     역방향(좌표 → 도로명주소)을 준다. 어댑터를 만들 수 있다
#:   'no'      정방향만 준다. **키가 와도 FX-5 는 이 자원으로 열리지 않는다** —
#:             그때는 어댑터 설계가 아니라 **자원 선택**의 문제이고, 그 선택은
#:             개발이 판정하지 않는다(D-318 ㉡)
#:
#:   왜 2값이 아니라 3값인가: 'no' 와 'unknown' 을 합치면 **"안 준다" 와 "안 물어봤다"가
#:   같은 값**이 되고, 그러면 대체 자원을 찾아야 하는지 아직 물어보면 되는지 모른다.
#:   D-290 이 pending/failed 를 가른 것과 같은 이유다.
#:
#:   올리는 방법은 하나뿐이다: `python scripts/probe_juso_direction.py` 로 **실호출 1회.**
#:   증거는 `docs/agent/evidence/D-318/` 에 남는다. 문서를 읽고 올리지 않는다(D-316).
#: ★ 2026-09-06 **'no' 로 확정** (D-329). 실호출이 아니라 **신청서 유형**으로 확정했다.
#:   API 유형 = 「도로명주소 팝업 API」 [실측·대표 승인 화면 2건]. 팝업 API 는 웹 화면에
#:   주소검색 창을 띄우는 UI 위젯이고, 역지오코딩이 아닌 것은 물론 **서버끼리 주고받는
#:   조회 API 조차 아니다.** 그래서 실호출 없이 답이 났다.
#:   ★ 우리가 물은 것은 「키가 있는가」였고 「어떤 키인가」는 묻지 않았다 — 그 교정이 D-328 이다.
JUSO_REVERSE_SUPPORTED: str = "no"

#: 무엇을 근거로 확정했는가. **실호출이 아니라는 사실을 정직하게 적는다**(D-322 정신).
REVERSE_DECIDED_BY: str = "신청서 유형(도로명주소 팝업 API) · 대표 승인 화면 2건 · 2026-09-06"

#: 판정 사유. 비면 `scripts/verify_juso_direction.py` 가 exit 1 —
#: **자원을 버리는 판정이므로 근거가 남아야 한다**(D-316).
JUSO_REVERSE_UNKNOWN_REASON: str = (
    "★ 2026-09-06 확정 'no' — 근거는 **실호출이 아니라 신청서 유형**이다. "
    "발급된 승인키 2건의 API 유형이 둘 다 「도로명주소 팝업 API」였다"
    "[실측·대표 승인 화면 2건]. 팝업 API 는 브라우저에 주소검색 창을 띄우는 UI 위젯이고 "
    "서버 조회 API 가 아니므로, 좌표→도로명주소는 이 자원으로 열리지 않는다. "
    "그리고 **FX-5 자체가 필요 없어졌다**(D-330): 카메라는 고정 설치물이므로 설치 주소를 "
    "적어 두면 이벤트 위치가 곧 그 카메라의 주소다 — 외부 호출 0건. "
    "이 키는 버리지 않는다: 카메라 주소 **입력 팝업**이 정확히 그 키가 하는 일이다(D-331). "
    "직전 상태('unknown')의 사유는 다음과 같았고 그대로 남긴다 — "
    "승인키가 이 개발 환경에 없어 실호출을 못 했다(2026-09-04 실측: "
    "C:/GuardianX-vault/secrets-20260210/gx_be.env 에 juso 항목 없음 · 환경변수 "
    "GX_JUSO_API_KEY 없음 · backend/.env 파일 자체가 없음). 대표께서 승인키 2건을 "
    "발급하셨다는 회신은 받았으나 **문서로 안 것을 계정에서 본 것으로 등재하지 않는다**"
    "(D-316). 해소는 개발이 아니라 키를 환경변수에 넣고 프로브를 1회 돌리는 것이며, "
    "그러면 이 상수가 yes/no 로 확정되고 FX-5 의 설계가 갈린다."
)

#: 이 어댑터가 **잴 수 있는 상태인가.** SDN 과 같은 규약이다.
#: 구현체가 없으므로 False 이고, 사유가 비면 `scripts/verify_e2e_contract.py` 가 exit 1.
KERNEL_READY: bool = False

NOT_READY_REASON: str = (
    "juso.go.kr 좌표→도로명주소 API 의 **응답 스키마를 실측하지 않았다.** "
    "요청 URL 은 D-298 로 .env.example 에 등재됐으나(JUSO_API_URL), 응답의 필드 이름·"
    "중첩 구조·오류 코드는 실호출로 확인해야 한다. 추측한 필드명 위의 파서는 첫 실호출에서 "
    "전부 재작업이 되고, 그때는 그것이 추측이었다는 사실조차 남지 않는다(D-280 · D-298). "
    "실측 절차는 이미 서 있다: 키를 환경변수에 넣고 "
    "`python scripts/probe_public_data_schema.py --only juso_coord2addr` 를 한 번 돌리면 "
    "`docs/agent/evidence/DA-05/juso_coord2addr_schema.md` 가 생긴다. "
    "그 문서가 생긴 뒤 `AddressPort` 구현체 하나를 채우고 register 하면 끝난다 — "
    "해소는 개발이 아니라 **키 발급 + 실측 1회**다."
)


# ═══════════════════════════════════════════════════════════════════════════
# 나가는 값 — **상태를 주소와 함께 낸다** (D-290)
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class AddressResult:
    """좌표 하나에 대한 답. **주소가 없다는 사실에도 종류가 있다.**

    `address` 만 돌려주면 `None` 이 세 가지 뜻을 갖는다 — 아직 안 물어봤다 · 물어봤는데
    실패했다 · 물어볼 대상이 아니다. 셋은 다음 행동이 각각 다르다(재시도 · 재시도+사람에게
    좌표 표시 · 아무것도 안 함). 한 값으로 두면 그 셋이 영영 구별되지 않는다.
    """

    #: `DetectionEvent.AddressStatus` 와 **같은 문자열**을 쓴다. 열거를 두 벌로 두면 갈린다.
    status: str
    #: 도로명 주소. `status='resolved'` 일 때만 값이 있다.
    address: str | None = None
    #: 왜 이 상태인가. 실패·비활성의 사유를 사람이 읽는 문장으로 남긴다 (D-264).
    reason: str = ""


class AddressPort(abc.ABC):
    """좌표 → 도로명 주소. **실기든 Mock 이든 이 인터페이스를 구현한다.**

    구현체는 예외를 던져도 된다 — `resolve` 가 잡아서 `failed` 로 번역한다.
    그래야 구현체가 "죽는 법"을 따로 배우지 않아도 저하 운전이 성립한다.
    """

    @abc.abstractmethod
    def lookup(self, *, lat: float, lng: float, timeout: float) -> str | None:
        """도로명 주소를 돌려준다. 못 찾으면 `None` — **빈 문자열이 아니다.**

        `timeout` 은 **인자로 받는다**(C-3.3). 구현체가 자기 기본값을 쓰면 그 값이
        어디 적혀 있는지 아무도 모르게 되고, 게이트가 세는 자리에서도 사라진다.
        """
        raise NotImplementedError


class UnmeasuredAddressPort(AddressPort):
    """기본으로 꽂혀 있는 자리 — **부르면 왜 못 하는지 말한다.**

    SDN 의 `UnavailableSdnPort` 와 같은 계열이지만 **예외를 던지지 않는다.** 차이의
    이유는 계약이 다르기 때문이다: SDN 요청은 실패하면 그 요청이 실패한 것이고,
    주소 조회는 실패해도 **이벤트는 나야 한다.** 조용한 성공을 만들지 않으면서
    (상태와 사유를 낸다) 저하 운전을 지킨다.
    """

    def lookup(self, *, lat: float, lng: float, timeout: float) -> str | None:
        raise NotImplementedError(NOT_READY_REASON)


_current: AddressPort | None = None


def register(port: AddressPort) -> "callable":
    """포트를 꽂는다. **되돌리는 함수를 돌려준다** — `k2_notify.channels.register` 와 같은 규약.

    시험이 꽂은 것을 시험이 스스로 뽑게 한다. 전역 상태를 시험이 남기면 다음 시험이
    그것을 물려받고, 그러면 시험 순서가 결과를 바꾼다.
    """
    global _current
    if not isinstance(port, AddressPort):
        raise TypeError(
            f"{type(port).__name__} 은 AddressPort 가 아니다 — 실기든 Mock 이든 같은 "
            f"인터페이스를 구현해야 설정 한 줄로 갈아끼울 수 있다 (D-212)")
    previous, _current = _current, port

    def undo() -> None:
        global _current
        _current = previous

    return undo


def current() -> AddressPort | None:
    """지금 꽂혀 있는 포트. 없으면 `None` — 없는 것을 있는 척하지 않는다."""
    return _current


def is_ready() -> bool:
    """주소 조회가 **실제로 될 상태인가.** 선언과 실물을 함께 본다."""
    return KERNEL_READY and _current is not None and not isinstance(
        _current, UnmeasuredAddressPort)


# ═══════════════════════════════════════════════════════════════════════════
# 부르는 쪽이 쓰는 유일한 함수 — **절대 예외를 던지지 않는다**
# ═══════════════════════════════════════════════════════════════════════════
def resolve(*, lat: float | None, lng: float | None,
            timeout: float = TIMEOUT_SECONDS) -> AddressResult:
    """좌표를 주소로. **어떤 경우에도 예외가 나가지 않는다.**

    이 함수가 예외를 던지면 부르는 쪽이 감싸야 하고, 감싸는 코드가 늘면 언젠가 한 곳이
    빠진다 — 그 순간 주소 API 가 이벤트 생성을 끌고 내려간다. 그래서 **여기서 끝낸다.**

    돌려주는 상태 넷은 각각 다음 행동이 다르다:
        disabled  좌표가 없거나 포트가 안 꽂혔다.       → 재시도하지 않는다
        resolved  주소를 받았다.                        → 알림·보고서에 그대로 쓴다
        failed    포트는 있는데 죽었거나 못 찾았다.      → 재시도 대상 + "주소 확인 불가(좌표: …)"
        pending   (이 함수는 내지 않는다 — 저장 시 기본값이고, 아직 안 부른 상태다)
    """
    if lat is None or lng is None:
        return AddressResult(
            status="disabled",
            reason="좌표가 없다 — 조회할 대상이 없으므로 재시도 대상이 아니다")

    port = _current
    if port is None or isinstance(port, UnmeasuredAddressPort):
        return AddressResult(status="disabled", reason=NOT_READY_REASON)

    try:
        address = port.lookup(lat=lat, lng=lng, timeout=timeout)
    except Exception as exc:                      # noqa: BLE001 — 저하 운전이 목적이다
        # ★ 좌표를 로그에 남기고 **주소 API 의 응답 본문은 남기지 않는다** —
        #   포털 API 는 요청을 그대로 되비추는 경우가 있고, 그러면 키가 로그에 실린다
        #   (probe_public_data_schema.py 가 같은 이유로 마스킹한다 · D-204).
        log.warning("FX-5 주소 조회 실패 (%.6f, %.6f): %s", lat, lng, type(exc).__name__)
        return AddressResult(
            status="failed",
            reason=f"주소 조회가 실패했다: {type(exc).__name__}. "
                   f"알림에는 '주소 확인 불가(좌표: {lat}, {lng})' 로 나간다")
    if not address:
        return AddressResult(
            status="failed",
            reason="주소 조회는 됐으나 해당 좌표의 도로명 주소가 없다 — "
                   "하천·산지 등 도로명이 부여되지 않은 지점일 수 있다")
    return AddressResult(status="resolved", address=address)


__all__ = [
    "TIMEOUT_SECONDS",
    "JUSO_REVERSE_SUPPORTED",
    "JUSO_REVERSE_UNKNOWN_REASON",
    "KERNEL_READY",
    "NOT_READY_REASON",
    "AddressPort",
    "AddressResult",
    "UnmeasuredAddressPort",
    "register",
    "current",
    "is_ready",
    "resolve",
]
