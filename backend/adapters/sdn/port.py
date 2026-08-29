# -*- coding: utf-8 -*-
"""SDN 어댑터의 **포트** — 명세 없이도 확정할 수 있는 것만 세운다.

이 파일이 존재하는 이유
-----------------------
에스비정보기술의 SDN 컨트롤러 API 명세가 미수령이다(계약 3조2항, 기한 2026-08-25 경과).
그래서 **어댑터는 만들 수 없다** — Mock 조차 못 만든다(DA-02 §0 · D-297).

그런데 만들 수 없는 것과 **정할 수 없는 것**은 다르다.
DA-02 §3 이 이미 그 경계를 그어 두었다: *"명세를 기다리는 동안에도 이것들은 확정할 수
있다. 매핑서 v1.0 은 이 제약 위에 쓰인다."*

    저쪽이 정하는 것 — 엔드포인트 · 필드 이름 · 타입 · 오류 코드 · 인증 방식
    우리가 정하는 것 — **우리가 무엇을 요청하는가**(의도) · 타임아웃 · 실패 처리 ·
                       테넌트 경계 · 기록 · 비행 명령 미전송 불변식

이 파일은 **뒤쪽만** 적는다. 앞쪽은 한 줄도 없다.

무엇을 적지 않았는지 세어 보라 (D-280)
--------------------------------------
· 우선순위의 숫자 범위가 없다 — 1이 높은지 낮은지 모른다(DA-02 1-3, A 등급).
· 대역폭의 단위가 없다 — Mbps 인지 Kbps 인지 모른다(1-4, A 등급).
· 결과 코드 열거가 없다 — 코드표를 못 받았다(1-6, A 등급).
· 링크 ID 도 스트림 식별자도 **우리 것만** 있다 — 저쪽 식별자 체계를 모른다(1-2, A 등급).

  적었다면 그것은 명세가 아니라 **추측**이고, 추측 위의 어댑터는 재작업이 확정된다.

그러면 이 포트가 무슨 값을 하나
-------------------------------
명세가 도착한 날 해야 할 일이 **`SdnPort` 를 구현하는 것 하나로 줄어든다.**
호출하는 쪽(K1·K2·App)은 이 인터페이스만 보고 이미 쓸 수 있고, 실기든 Mock 이든
**같은 인터페이스를 구현한다**(DA-02 §3-5: "설정 한 줄로 갈아끼운다", D-212).

지금 이 포트를 부르면 `SpecNotReceived` 가 난다. **조용히 None 이나 성공을 돌려주지
않는다** — `detect_and_save` 가 정확히 그 모양이었고(독스트링은 "저장한다", 본문은 비어
있음), 그래서 부르는 쪽은 저장된 줄 알았다. 없는 것은 없다고 말한다 (D-284 · D-290).
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from adapters.sdn.exceptions import SpecNotReceived
from adapters.sdn.requirements import INTERFACES, missing_blocking


# ═══════════════════════════════════════════════════════════════════════════
# 우리 쪽 말 — 요청의 **의도**. 저쪽 필드가 아니다.
# ═══════════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class QosIntent:
    """I-1 요청의 **의도** — "이 스트림의 영상을 지금 살려 달라".

    ★ 숫자가 없는 것이 이 클래스의 요점이다. 우선순위 값도, 대역폭 값도 없다 —
      둘 다 저쪽 명세가 정하는 것이고(DA-02 1-3 · 1-4, 둘 다 A 등급), 여기서 정하면
      **어댑터가 아니라 도메인이 SDN 을 아는 것**이 된다(§3-2 위반).

      우리가 말할 수 있는 것은 "무엇을·왜·얼마나 오래" 뿐이고, 그것을 저쪽 숫자로
      옮기는 일은 명세를 받은 뒤 어댑터 구현이 한다.
    """

    #: **우리 식별자다.** SDN 이 아는 식별자와 같은 체계인지는 미수령 항목(1-2).
    #: 다르면 매핑 테이블이 신규 개발 항목이 되고, 그 항목은 지금 견적에 없다.
    stream_monitor_id: int
    #: 왜 올리는가. 사후 감사에서 "누가 왜 망을 흔들었나" 에 답하는 자리다.
    reason: str
    #: 얼마나 오래 유지할 것인가. 만료 시 자동 원복인지 해제 요청이 따로인지는 미수령(1-5).
    hold_for: timedelta
    #: 어느 이벤트가 촉발했는가. 없을 수 있다(사람이 손으로 올리는 경우).
    event_id: int | None = None


@dataclass(frozen=True)
class RerouteIntent:
    """I-2 요청의 의도 — "이 스트림이 저 링크를 피해 가게 해 달라".

    ★ 경로를 **고르지 않는다.** 우리가 경로를 고르려면 망 토폴로지를 알아야 하고,
      그것은 계약 범위 밖이다(DA-02 2-3). 우리는 "무엇이 막혔다" 까지만 말한다.
    """

    stream_monitor_id: int
    #: 장애 링크의 **저쪽 식별자**. I-3 통보로 받은 값을 그대로 되돌려주는 것이므로
    #: 우리가 형식을 정하지 않는다 — 받은 문자열을 불투명하게 나른다.
    failed_link_ref: str
    reason: str
    event_id: int | None = None


@dataclass(frozen=True)
class LinkStateNotice:
    """I-3 통보 — SDN 이 우리에게 주는 것.

    ★ 필드가 셋뿐이고 전부 불투명하다. 계약이 "링크 ID, 상태, 대역폭, 시각, 위치 매핑"
      이라고 적었지만 **그 형식은 명세가 정한다**(3-4 · 3-5, A 등급).
      `raw` 를 그대로 나르는 것은 게으름이 아니라 **경계다** — 해석은 명세를 받은 뒤
      어댑터가 하고, 그 전에는 해석하지 않는다.
    """

    link_ref: str
    received_at: datetime
    #: 저쪽이 보낸 것 그대로. **여기서 필드를 꺼내 쓰는 코드를 만들지 않는다** —
    #: 꺼내는 순간 그 이름이 우리 코드의 계약이 되고, 명세가 오면 전부 고쳐야 한다.
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ControlReceipt:
    """제어 요청 하나의 **우리 쪽 기록**.

    ★ 계약 10조1항 — **가이온의 책임은 요청·기록까지다.** 그래서 AC 문장을
      "SDN 이 이행했다" 가 아니라 **"요청이 나갔고 결과가 기록됐다"** 로 쓴다
      (DA-02 §3-3). 이 dataclass 가 그 문장의 코드판이다.

    `result_code` 는 **해석하지 않는다.** 코드표가 미수령이고(1-6, A 등급),
    해석하려면 표가 있어야 한다. 지금은 받은 문자열을 그대로 기록만 한다 —
    기록해 두면 표가 왔을 때 과거분까지 해석할 수 있다.
    """

    #: 우리가 만든 요청 ID. 저쪽이 발급하는지 우리가 만드는지는 미수령(4-1) —
    #: 그래서 **우리 것을 먼저 만들어 둔다.** 저쪽이 발급하는 쪽이면 아래 `remote_ref` 에 담는다.
    request_id: str
    interface: str
    requested_at: datetime
    #: 요청이 실제로 나갔는가. **저쪽이 이행했는가가 아니다.**
    dispatched: bool
    #: 저쪽이 준 식별자·코드. 해석 없이 보관한다.
    remote_ref: str = ""
    result_code: str = ""
    #: 실패했다면 왜. 비어 있으면 실패가 아니다 — 빈 문자열로 실패를 덮지 않는다(D-290).
    failure_reason: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# 포트 — 실기와 Mock 이 **같은 것을 구현한다** (DA-02 §3-5 · D-212)
# ═══════════════════════════════════════════════════════════════════════════
class SdnPort(abc.ABC):
    """SDN 컨트롤러와 말하는 자리. **다섯 개는 계약이 정한 수다** (별첨1 §4).

    구현체는 두 종류가 될 것이다 — 실기 어댑터와 Mock. **둘은 같은 인터페이스를
    구현한다**: 설정 한 줄로 갈아끼우기 위해서다(DA-02 §3-5). Mock 이 인터페이스를
    조금 다르게 만들면 그 순간 실기 전환이 코드 수정이 된다.

    ⚠ **Mock 도 아직 못 만든다.** DA-02 §0: *"각 인터페이스의 엔드포인트·필드 정의는
      갑이 제공하는 명세를 기준으로 확정한다. Mock 조차 I-1~I-5 의 필드 이름과 타입이
      있어야 만들 수 있다."* 그러므로 이 저장소에 `MockSdnPort` 는 **없다** —
      없는 것이 옳고, 있으면 그것이 추측이다.

    구현할 때 반드시 지키는 것 (DA-02 §3 · 명세와 무관하게 확정된 제약)
    -------------------------------------------------------------------
      1. **타임아웃 없는 외부 호출을 만들지 않는다.** 값은 settings 한 곳에서 온다
         (`EXTERNAL_API_TIMEOUT_SEC`). W0-17 이 17건을 0 으로 만들었고 게이트가 지킨다.
      2. **SDN 필드가 도메인 모델로 새어 들어가지 않는다.** 변환은 이 층에서만.
      3. **책임은 요청·기록까지다**(계약 10조1항). `ControlReceipt` 가 그 경계다.
      4. **오류는 HTTP 상태로 낸다.** `200 + {"success": false}` 를 만들지 않는다(W0-18).
      5. **비행 명령을 보내지 않는다.** F-13 은 제안까지이고, 승인은 사람이 한다.
         이 포트에 비행 관련 메서드가 **없는 것**이 그 불변식의 구조적 표현이다.
    """

    #: 구현체가 자기 이름을 밝힌다. 감사 로그와 `current()` 표시에 쓴다.
    name: str = "sdn"

    # ── I-1 ──────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def request_qos(self, intent: QosIntent) -> ControlReceipt:
        """I-1 영상 QoS 우선 제어 요청 (F-06). AC 는 **10초 내 요청·결과 코드 기록**."""

    # ── I-2 ──────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def request_reroute(self, intent: RerouteIntent) -> ControlReceipt:
        """I-2 경로 우회 요청 (F-07). AC 는 **대체 경로 요청과 전환 확인 기록**."""

    # ── I-3 ──────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def poll_link_states(self) -> tuple[LinkStateNotice, ...]:
        """I-3 링크·장비 상태 (F-08).

        Webhook 인가 폴링인가는 **계약이 '또는' 으로 열어 두었고 아직 정해지지 않았다**
        (DA-02 3-1, A 등급). 그래서 이름을 `poll_...` 로 박지 않고 싶었으나, 둘 중
        하나는 골라야 서명이 선다 — **폴링을 기본으로 두고**, Webhook 으로 확정되면
        수신부가 이 메서드를 호출하는 대신 `on_link_state()` 로 밀어 넣는다.
        그 갈림은 `docs/design/DA-02...md` 3-1 이 정해지는 날 닫힌다.
        """

    @abc.abstractmethod
    def on_link_state(self, notice: LinkStateNotice) -> None:
        """I-3 을 **밀어서** 받는 경우(Webhook). 폴링으로 확정되면 구현체가 no-op 로 둔다.

        둘 다 세워 두는 이유: 어느 쪽으로 정해지든 **호출하는 쪽 코드가 안 바뀌게** 하기
        위해서다. 하나만 세우면 다른 쪽으로 정해졌을 때 App 까지 고쳐야 한다.
        """

    # ── I-4 ──────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def fetch_results(self, *, since: datetime) -> tuple[ControlReceipt, ...]:
        """I-4 제어 결과·감사 이력 (F-09 표시 · F-11 보고서).

        요청 ID 를 누가 만드는지가 미수령이다(4-1, A 등급). 우리가 만든 `request_id` 로
        잇든 저쪽 `remote_ref` 로 잇든 **둘 다 `ControlReceipt` 에 자리가 있다** —
        어느 쪽으로 정해져도 스키마를 안 고친다.
        """

    # ── I-5 ──────────────────────────────────────────────────────────────
    @abc.abstractmethod
    def check_auth(self) -> bool:
        """I-5 인증 — **지금 말을 걸 수 있는가.**

        API Key 인지 OAuth2 인지가 미수령이고(C-2, A 등급) 둘은 갱신·만료 처리가 전혀
        다르다. 그래서 여기서는 방식을 묻지 않고 **결과만** 묻는다: 통하는가 아닌가.
        자격증명 값은 **코드 밖**에 있다 (D-204 · 계약 §4 I-5).
        """


class UnavailableSdnPort(SdnPort):
    """명세가 오기 전의 자리. **모든 호출이 멈춘다.**

    왜 "아무것도 안 하는 구현" 을 두나 — 조용한 성공을 만들지 않기 위해서다.
    포트를 아예 비워 두면 부르는 쪽이 `None` 을 받고, `None` 은 "안 했다" 와
    "실패했다" 와 "그런 건 없다" 를 한 값으로 뭉갠다 (D-290).

    이 구현은 그 대신 **왜 못 하는지를 말하며 멈춘다.** 예외 메시지에 미수령 A 등급
    항목이 실려 나가므로, 로그 한 줄이 곧 독촉 근거가 된다.
    """

    name = "unavailable"

    def _stop(self, interface: str):
        missing = missing_blocking(interface)
        raise SpecNotReceived(interface=interface, missing=missing)

    def request_qos(self, intent: QosIntent) -> ControlReceipt:
        self._stop("I-1")

    def request_reroute(self, intent: RerouteIntent) -> ControlReceipt:
        self._stop("I-2")

    def poll_link_states(self) -> tuple[LinkStateNotice, ...]:
        self._stop("I-3")

    def on_link_state(self, notice: LinkStateNotice) -> None:
        self._stop("I-3")

    def fetch_results(self, *, since: datetime) -> tuple[ControlReceipt, ...]:
        self._stop("I-4")

    def check_auth(self) -> bool:
        self._stop("I-5")


#: 계약이 정한 인터페이스 수와 포트의 추상 메서드가 **어긋나지 않게** 한다.
#: I-3 만 둘(pull/push)이므로 6개다 — 그 하나의 예외를 여기 적어 두지 않으면
#: 다음 사람이 "5개여야 하는데 6개네" 를 다시 조사한다.
PORT_METHODS: dict[str, tuple[str, ...]] = {
    "I-1": ("request_qos",),
    "I-2": ("request_reroute",),
    "I-3": ("poll_link_states", "on_link_state"),
    "I-4": ("fetch_results",),
    "I-5": ("check_auth",),
}

assert set(PORT_METHODS) == set(INTERFACES), (
    "포트 메서드 표와 계약 인터페이스 표가 갈렸다 — 둘 중 하나만 고쳤다"
)
