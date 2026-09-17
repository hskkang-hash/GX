# -*- coding: utf-8 -*-
"""K2 채널 어댑터 — **인터페이스를 먼저 고정하고 구현체를 나중에 끼운다** (DA2-21 (2)).

발송 업체가 미정이다 (DA-04 D4-1 · 계약·비용 사안). 그렇다고 채널 개념을 나중으로
미루면 나중에 `send()` 의 시그니처가 바뀌고, 그때는 부르는 곳이 이미 여럿이다.
그래서 **자리는 지금 만들고 구현만 비운다.**

미정을 어떻게 표현하나 — 조용히 성공하지 않는다
-----------------------------------------------
등록되지 않은 채널로 보내려 하면 **실패 이력이 남는다**. 예외로 전체를 끊지 않는 이유는
저하 운전 때문이다(DA2-21 (4)): 메일이 되는데 SMS 어댑터가 없다고 메일까지 못 가면
그것은 저하 운전이 아니라 전면 정지다. 대신 그 실패는 **행으로 보인다** —
"보낸 적 없음"과 "보내려다 실패"가 같은 상태(행 없음)가 되지 않는다 (D-290).

타임아웃 — 값은 한 곳에 (D-212 · W0-17)
---------------------------------------
*"외부 발송 업체 호출은 **타임아웃 필수**. 발송이 느리다고 관제가 멈추면 안 된다"*
(DA-04 K2). 숫자를 어댑터마다 적지 않는다. 설정을 읽고, 설정이 없으면 바닥값을 쓴다 —
`common/external_http.py` 가 HTTP 에 대해 하는 일과 같은 형이다.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Protocol

from django.conf import settings

log = logging.getLogger(__name__)

#: 설정이 없을 때의 바닥값(초). **"타임아웃 없음"으로 떨어지는 것을 막는 값**이다.
#: 운영 경로는 항상 `settings.EMAIL_TIMEOUT` 을 읽는다.
FALLBACK_EMAIL_TIMEOUT = 10.0

#: 실발송 허용 도메인을 **못 읽었을 때**의 값 (P-41 · 2026-09-05).
#:
#: ★ **빈 튜플이다.** 타임아웃의 바닥값과 방향이 반대인 이유: 타임아웃을 못 읽으면
#:   위험한 쪽은 「무한 대기」이므로 값을 **채워** 준다. 허용 목록을 못 읽으면 위험한
#:   쪽은 「전부 나간다」이므로 **비워** 둔다. 바닥값은 언제나 사고가 아닌 쪽이다.
FALLBACK_SEND_ALLOWED_DOMAINS: tuple[str, ...] = ()


def _allowed_domains() -> frozenset[str]:
    """실발송이 허용된 도메인. 설정을 읽고, **없으면 빈 집합**이다.

    ⚠ 빈 집합은 「제한 없음」이 아니라 **「아무 데도 안 보냄」**이다. 목록을 잊은 것과
      전부 허용한 것이 같은 모양이 되면(D-290), 잊은 날 42명에게 진짜로 나간다.
    """
    raw = getattr(settings, "K2_SEND_ALLOWED_DOMAINS", None)
    if raw is None:
        raw = FALLBACK_SEND_ALLOWED_DOMAINS
    if isinstance(raw, str):                 # `env.list` 를 안 거친 손 설정을 받아 준다
        raw = raw.split(",")
    out = set()
    for item in raw:
        # `@example.com` · ` Example.COM ` · `example.com.` 을 같은 것으로 읽는다.
        name = str(item).strip().lower().lstrip("@").rstrip(".")
        if name:
            out.add(name)
    return frozenset(out)


def _domain_of(address: str) -> str:
    """주소의 도메인. 「주소가 아니다」는 **빈 문자열**로 돌려준다 — 그리고 빈 도메인은
    어떤 허용 목록에도 들지 못하므로, 이상한 주소는 **자동으로 막히는 쪽**으로 간다."""
    parts = (address or "").strip().lower().rsplit("@", 1)
    return parts[1].rstrip(".") if len(parts) == 2 else ""


def _email_timeout() -> float:
    """설정을 읽고, 없으면 바닥값. **밑줄로 시작하는 이유는 커널 규약이다** —
    `kernels/` 안의 모듈 최상위 공개 함수는 `*, scope: TenantScope` 를 요구받는다(D-281).
    채널 어댑터의 속살은 테넌트를 만지지 않으므로 공개 면이 아니고, 그 사실을
    **이름으로** 말한다. 밖에서 필요한 것은 `EmailChannel.timeout()` 이다.
    """
    value = getattr(settings, "EMAIL_TIMEOUT", None)
    try:
        return float(value) if value else FALLBACK_EMAIL_TIMEOUT
    except (TypeError, ValueError):
        return FALLBACK_EMAIL_TIMEOUT


@dataclass(frozen=True)
class SendOutcome:
    """어댑터 하나의 결과. **예외를 값으로 바꾼다** (`external_http.fetch_json` 과 같은 형).

    부르는 쪽이 try/except 를 흩뿌리면 어딘가 하나가 빠지고, 빠진 그 하나가
    조용한 유실이 된다.
    """

    ok: bool
    #: 실패 사유. 성공이면 빈 문자열이다 — `None` 과 `""` 를 섞지 않는다.
    reason: str = ""


class Channel(Protocol):
    """채널 어댑터가 지켜야 하는 것 — 이것뿐이다."""

    name: str

    def send(self, *, address: str, subject: str, body: str) -> SendOutcome:
        ...


class EmailChannel:
    """메일 — **지금 붙어 있는 유일한 구현체** (D4-1 미정 대응).

    Django 의 메일 백엔드를 쓴다. 시험에서는 locmem 백엔드가 들어가므로 실제로
    나가지 않으면서 **보냈다는 사실은 실물로 확인**된다 (합성 mock 이 아니다 — D-289).
    """

    name = "email"

    @staticmethod
    def timeout() -> float:
        """이 어댑터가 쓰는 타임아웃. **빠뜨릴 수 없다** (W0-17 · C-3.3)."""
        return _email_timeout()

    @staticmethod
    def configured() -> SendOutcome:
        """SMTP 가 **실제로 설정돼 있는가**. `ok=False` 는 회색이다 (OPS-10 · 2026-09-24).

        왜 이것이 따로 필요한가 — **자리 표시자는 값처럼 보인다**
        --------------------------------------------------------
        `settings.EMAIL_HOST_USER` 의 기본값은 `your-email@gmail.com` 이고
        `EMAIL_HOST_PASSWORD` 의 기본값은 `your-app-password` 다. `getattr` 로 읽으면
        **둘 다 값이 있다.** 그래서 "설정됐는가"를 진위로 물으면 언제나 참이 나오고,
        진짜 실패는 발송을 시도한 **뒤에야** SMTP 인증 오류로 드러난다.
        「설정 안 함」과 「설정했는데 틀림」이 같은 모양이 되는 자리다(D-290).

        그래서 자리 표시자의 목록을 설정에 두고(`EMAIL_PLACEHOLDER_VALUES`) 여기서 읽는다.
        **판정식을 여기에 복사하지 않는다**(D-212) — 목록이 늘면 한 곳만 는다.

        ★ 이 함수는 **보내 보지 않는다.** 보내 보면 그것은 이미 발송이고, 발송 시도는
          이력을 남긴다. 「설정됐는가」를 묻는 데 이력을 만들면 이력이 오염된다.
          그러므로 이 판정은 「보낼 수 있는 모양인가」까지이고, **실제로 도달했는가는
          사람의 수신함만 답한다.** 그 둘을 섞지 않는 것이 OPS-10 의 요점이다.
        """
        placeholders = set(getattr(settings, "EMAIL_PLACEHOLDER_VALUES", None) or ("",))
        missing = []
        for key in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD",
                    "DEFAULT_FROM_EMAIL"):
            value = (getattr(settings, key, "") or "").strip()
            if value in placeholders:
                missing.append(key)
        backend = str(getattr(settings, "EMAIL_BACKEND", ""))
        if missing:
            return SendOutcome(
                False,
                "SMTP 미설정 — %s 이(가) 자리 표시자 그대로다. "
                "값은 로컬 `.env` 로만 준다(저장소에 넣지 않는다 · D-204). "
                "백엔드=%s" % (", ".join(missing), backend))
        return SendOutcome(True)

    @staticmethod
    def deliverable(address: str) -> SendOutcome:
        """이 주소로 **사람이 받을 수 있는가**. 주소가 있다와 도달한다는 다르다.

        시드 사람의 주소는 `@seed.invalid` 다 — RFC 2606 이 절대 존재하지 않는다고
        못 박은 TLD 이고, 일부러 그렇게 두었다(실수로 나가도 갈 곳이 없게). 그 주소를
        「수신자가 있다」로 세면 **경보가 도달한다**는 거짓 초록이 선다.
        """
        addr = (address or "").strip().lower()
        if not addr:
            return SendOutcome(False, "주소가 비었다")
        for suffix in (getattr(settings, "UNDELIVERABLE_EMAIL_SUFFIXES", None)
                       or (".invalid",)):
            if addr.endswith(suffix):
                return SendOutcome(
                    False,
                    "%s 는 **도달할 수 없는 주소**다(%s · RFC 2606). 발송 이력은 남지만 "
                    "사람은 받지 못한다" % (address, suffix))
        return SendOutcome(True)

    @staticmethod
    def send_allowed(address: str) -> SendOutcome:
        """이 주소로 **실제로 보내도 되는가** (P-41 · 2026-09-05 · 세종 판정).

        `deliverable()` 과 무엇이 다른가 — **닿는가**와 **보내도 되는가**는 다른 질문
        ------------------------------------------------------------------------
        `deliverable()` 은 「이 주소에 사람이 있는가」를 묻는다(`.invalid` 는 없다).
        이것은 「사람이 있어도 **지금 우리가 보내도 되는가**」를 묻는다. 개발 계정
        `@yopmail.com` 24개는 **닿는다.** 닿기 때문에 위험하다 —
        [실측 2026-09-05 · 턴 B] 규칙이 고르는 수신자 42명 중 30명이 개발 계정이다.

        ★ **허용 목록이다.** 여기 없는 도메인은 전부 막힌다. 차단 목록으로 만들면
          내일 생길 43번째 개발 계정이 자동으로 통과한다 — 실수의 방향이 사고 쪽이다.
        ★ **정확히 같은 도메인**만 통과한다. 꼬리 일치를 쓰면 `notyopmail.com` 이
          `yopmail.com` 을 타고 나간다.
        """
        allowed = _allowed_domains()
        domain = _domain_of(address)
        if not allowed:
            return SendOutcome(
                False,
                "실발송 허용 도메인 목록이 **비어 있다** — 아무 도메인도 실발송하지 "
                "않는다(P-41). 이것은 「제한 없음」이 아니라 「아무 데도 안 보냄」이다. "
                "보낼 도메인은 `K2_SEND_ALLOWED_DOMAINS` 에 하나씩 적는다")
        if not domain:
            return SendOutcome(False, f"주소에서 도메인을 읽지 못했다: {address!r}")
        if domain not in allowed:
            return SendOutcome(
                False,
                "%s 는 **실발송 허용 도메인 목록 밖**이다(P-41). 허용된 것: %s"
                % (domain, ", ".join(sorted(allowed))))
        return SendOutcome(True)

    def send(self, *, address: str, subject: str, body: str) -> SendOutcome:
        from django.core.mail import get_connection, send_mail

        if not address:
            return SendOutcome(False, "수신 주소가 비었다 — 보낼 곳이 없다")

        # ★★ **허용 목록이 채널보다 앞에 선다** (P-41 · 2026-09-05).
        #    「보내기로 정했다」(채널=email)와 「이 사람에게 보내도 된다」는 다른 판단이고,
        #    뒤엣것을 앞엣것이 대신하게 두면 **첫 발송이 곧 사고**다.
        #
        #    ⚠ 이 판정은 `send_mail` **앞**에 있어야 한다. 보내고 나서 세는 것은 늦다 —
        #      나간 메일은 취소되지 않는다. 게이트(`scripts/verify_send_allowlist.py`)가
        #      낱말이 아니라 **AST 로** 이 순서를 본다.
        #
        #    ⚠ 떨어뜨린 뒤 `ok=True` 를 내지 않는다. 로그에 닿은 것을 사람에게 닿았다고
        #      말하면 그것이 「조용한 성공」이다(D-284). 대신 **사유가 행에 남는다** —
        #      발송 이력의 `failure_reason` 에 「목록 밖」이 적히고, 화면은 그것을 읽는다.
        gate = self.send_allowed(address)
        if not gate.ok:
            fallback = REGISTRY.get(LogChannel.name) or LogChannel()
            fallback.send(address=address, subject=subject, body=body)
            return SendOutcome(
                False, f"실발송 차단 — 로그 어댑터로 떨어뜨렸다. {gate.reason}"[:240])

        try:
            connection = get_connection(timeout=self.timeout())
            sent = send_mail(
                subject=subject, message=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=[address], connection=connection,
                fail_silently=False,
            )
        except Exception as exc:  # 저하 운전 — 관제를 멈추지 않는다 (W0-17)
            log.warning("[K2][EMAIL] 발송 실패 address=%s err=%s", address, exc)
            return SendOutcome(False, f"{type(exc).__name__}: {exc}"[:240])
        if not sent:
            # ★ `send_mail` 은 **보낸 개수**를 돌려준다. 0 은 실패다.
            #   여기서 True 를 내면 D-284 가 이름 붙인 "조용한 성공"이 된다.
            return SendOutcome(False, "백엔드가 0건 발송을 보고했다")
        return SendOutcome(True)


class LogChannel:
    """로그 — **사람이 아니라 로그에 도달한다** (P-20 ① · 2026-09-22).

    왜 이것이 있나 — **검수 환경에는 도달할 수신자가 없다**
    -----------------------------------------------------
    발송 업체는 미정이고(D4-1), 메일 백엔드는 이 환경에서 SMTP 를 가리킨다. 그 상태로
    시드가 `send` 를 부르면 발송 이력은 **전부 실패 행**이 되고, 그러면 모바일 M1
    (내게 온 이벤트)이 「알림이 있었다」와 「알림이 실패했다」를 구별하는 화면이 아니라
    **실패만 보이는 화면**이 된다. 그것은 배선의 사실이 아니라 환경의 사실이다.

    ⚠ **이 채널은 사람에게 도달했다고 주장하지 않는다.** 도달한 곳은 로그다.
      그 사실은 지워지지 않는다 — 발송 이력의 `channel` 칸에 `log` 라고 **남는다**.
      화면과 보고서는 그 값을 읽을 수 있고, 읽으면 "이 알림은 사람이 아니라 로그로
      갔다"가 그대로 보인다. 이름을 `email` 로 가장하면 그 순간 거짓말이 된다(D-284).

    ⚠ 운영 규칙에 이 채널을 넣으면 **당직자는 아무것도 못 받는다.** 그래서 이름을
      숨기지 않고 등록한다 — 숨긴 채널은 감사에서 안 보이고, 안 보이는 것은 못 고친다.
    """

    name = "log"

    def send(self, *, address: str, subject: str, body: str) -> SendOutcome:
        if not address:
            # 메일과 같은 판정. 주소 없는 수신자는 **로그로도** 도달하지 않는다 —
            # 여기서 참을 내면 「받을 사람이 없음」이 「보냈음」으로 둔갑한다.
            return SendOutcome(False, "수신 주소가 비었다 — 보낼 곳이 없다")
        log.info("[K2][LOG] **사람이 아니라 로그에 남긴다** to=%s subject=%s | %s",
                 address, subject, " / ".join(body.splitlines()))
        return SendOutcome(True)


class WebPushChannel:
    """웹푸시 — **업체가 필요 없는 유일한 푸시** (CH-03 · 2026-09-16 턴 S · 차선 U3).

    왜 이것은 `UNAVAILABLE` 이 아닌가
    ---------------------------------
    아래 `UNAVAILABLE["push"]` 는 **앱 푸시**(FCM/APNs)이고 업체·앱 배포가 선행이다.
    웹푸시는 다르다 — 브라우저가 이미 푸시 서비스를 들고 있고, 우리가 갖출 것은
    **VAPID 키 한 쌍**뿐이다. 그래서 자리를 비워 두지 않고 구현을 넣는다.

    ★ `address` 는 **구독 한 벌**이다 — 메일 주소 자리에 JSON 이 온다:
          `{"endpoint": "https://…", "keys": {"p256dh": "…", "auth": "…"}}`
      왜 엔드포인트 문자열만 받지 않나: 웹푸시 본문은 **구독 키로 암호화**해야 하고
      (RFC 8291), 키 없이 받으면 「등록은 됐는데 아무것도 안 온다」가 된다.
      `Channel` 프로토콜을 넓히지 않은 이유는 그 프로토콜이 메일·SMS·로그와
      공유되는 자리라서다 — 한 채널 때문에 셋의 모양을 바꾸지 않는다.

    ★ **못 보내면 못 보낸다고 말한다.** 이 환경에는 지금 발송기가 없다
      [실측 2026-09-16 · `pywebpush` 미설치 · VAPID 환경변수 3개 전부 없음].
      그 상태에서 `ok=True` 를 내는 것이 「조용한 성공」이고(D-284), 그러면
      **아무에게도 안 간 알림이 간 것으로** 집계된다. 사유는 행에 남는다.

    ⚠ 값을 로그에 남기지 않는다 — 실패 사유에도 엔드포인트·키를 적지 않는다.
      푸시 엔드포인트는 그 기기로 알림을 밀어 넣는 주소이고, 로그는 새는 자리다.
    """

    name = "webpush"

    #: 발송기·자격의 이름. **값이 아니라 이름이다**(D-204 · 게이트는 값을 출력하지 않는다).
    LIBRARY = "pywebpush"
    PUBLIC_ENV = "GX_VAPID_PUBLIC_KEY"
    PRIVATE_ENV = "GX_VAPID_PRIVATE_KEY"
    SUBJECT_ENV = "GX_VAPID_SUBJECT"

    #: 설정을 못 읽었을 때의 바닥값(초). 타임아웃과 같은 방향 — 위험한 쪽은 무한 대기다.
    FALLBACK_TIMEOUT = 10.0

    @staticmethod
    def timeout() -> float:
        value = getattr(settings, "K2_WEBPUSH_TIMEOUT", None)
        try:
            return float(value) if value else WebPushChannel.FALLBACK_TIMEOUT
        except (TypeError, ValueError):
            return WebPushChannel.FALLBACK_TIMEOUT

    @staticmethod
    def configured() -> SendOutcome:
        """보낼 수 있는 모양인가. **보내 보지 않는다**(`EmailChannel.configured` 와 같은 규약).

        `ok=False` 는 회색이 아니라 **선언된 부재**다 — 무엇이 없는지 이름으로 적는다.
        """
        import os

        missing = [name for name in (WebPushChannel.PUBLIC_ENV,
                                     WebPushChannel.PRIVATE_ENV,
                                     WebPushChannel.SUBJECT_ENV)
                   if not (os.environ.get(name, "") or "").strip()]
        try:
            import pywebpush  # noqa: F401
        except Exception:      # noqa: BLE001 — 없는 것도 상태다
            return SendOutcome(
                False,
                f"웹푸시 발송기({WebPushChannel.LIBRARY})가 이 환경에 없습니다. "
                f"설치 전까지 웹푸시는 **보낼 수 없습니다** — 빈 성공으로 넘기지 "
                f"않습니다." + (f" 환경변수도 비어 있습니다: {', '.join(missing)}"
                                if missing else ""))
        if missing:
            return SendOutcome(
                False,
                "VAPID 자격이 이 환경에 없습니다 — 비어 있는 환경변수: "
                + ", ".join(missing) + ". 값은 저장소 밖 `.env` 로만 줍니다(D-204).")
        return SendOutcome(True)

    @staticmethod
    def _subscription(address: str) -> dict | None:
        """`address` → 구독 사전. 못 읽으면 `None` — **지어내지 않는다.**"""
        import json

        if not address:
            return None
        try:
            parsed = json.loads(address)
        except (ValueError, TypeError):
            return None
        if not isinstance(parsed, dict) or not parsed.get("endpoint"):
            return None
        keys = parsed.get("keys")
        if not isinstance(keys, dict) or not keys.get("p256dh") or not keys.get("auth"):
            return None
        return parsed

    def send(self, *, address: str, subject: str, body: str) -> SendOutcome:
        import json
        import os

        subscription = self._subscription(address)
        if subscription is None:
            #: ⚠ 받은 값을 사유에 **되풀이하지 않는다** — 그 값이 자격이다.
            return SendOutcome(
                False,
                "구독 한 벌을 읽지 못했습니다 — endpoint 와 keys(p256dh·auth)가 "
                "함께 있어야 합니다. 키 없이는 본문을 암호화할 수 없습니다(RFC 8291).")

        ready = self.configured()
        if not ready.ok:
            return SendOutcome(False, ready.reason[:240])

        try:
            from pywebpush import webpush
        except Exception as exc:      # noqa: BLE001
            return SendOutcome(False, f"발송기를 가져오지 못했습니다: {type(exc).__name__}"[:240])

        #: 서비스워커(`frontend/public/field-push-sw.js::readPayload`)가 읽는 모양.
        #: 셋 중 하나가 없으면 그쪽이 자리표로 채운다 — 여기서 지어내지 않는다.
        payload = json.dumps({"title": subject, "body": body, "url": "/m/inbox"})
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=(os.environ.get(self.PRIVATE_ENV, "") or "").strip(),
                vapid_claims={"sub": (os.environ.get(self.SUBJECT_ENV, "") or "").strip()},
                timeout=self.timeout(),
            )
        except Exception as exc:      # 저하 운전 — 발송 하나가 관제를 세우지 않는다(W0-17)
            #: ★ 예외 **종류**만 남긴다. 메시지에 엔드포인트가 실려 오는 라이브러리가 있다.
            log.warning("[K2][WEBPUSH] 발송 실패 err=%s", type(exc).__name__)
            return SendOutcome(
                False,
                f"푸시 서비스가 거절했습니다({type(exc).__name__}) — 구독이 만료됐거나 "
                f"자격이 맞지 않습니다. 해지 후 다시 등록하면 됩니다."[:240])
        return SendOutcome(True)


#: 등록된 어댑터. **여기 없는 채널은 없는 채널이다** — 이름으로 잠근다 (D-285 ②).
#: SMS·푸시(앱)·Webhook 은 업체 선정(D4-1) 후 여기에 한 줄로 들어온다.
#: ★ 2026-09-16 (턴 S · 차선 U3) **하나가 늘었다** — `webpush`. 업체가 필요 없는
#:   유일한 푸시라 자리를 비워 두지 않고 구현을 넣었다(위 머리말).
REGISTRY: dict[str, Channel] = {
    EmailChannel.name: EmailChannel(),
    LogChannel.name: LogChannel(),
    WebPushChannel.name: WebPushChannel(),
}

#: **사람에게 도달하지 않는 채널.** 검수·시드용이고, 운영 규칙에 넣으면 당직자가
#: 아무것도 못 받는다. 이름을 목록으로 두는 이유는 화면·보고서가 「이 발송은 사람에게
#: 간 것이 아니다」를 판정식 복제 없이 물어볼 수 있게 하기 위해서다 (D-212).
NON_HUMAN: frozenset[str] = frozenset({LogChannel.name})

#: 자리는 있으나 구현이 없는 채널. **사유 필수** — 빈 자리는 잊힌 자리다 (D-264).
UNAVAILABLE: dict[str, str] = {
    "sms": "발송 업체 미선정 (DA-04 D4-1 · 계약·비용 사안). WP-DA2b ENTRY 까지 판단 대기.",
    "push": "발송 업체 미선정 (DA-04 D4-1). 앱 푸시는 모바일 클라이언트 배포와 함께 온다.",
    "webhook": "수신 URL 의 테넌트 소유 판정과 서명키 보관이 선행 — K1.subscribe 와 같은 선행이다.",
    # ★ [턴 S · 차선 U56] **이름이 이미 저장소에 있었다.** `stream_monitors.models
    #   .DsmNotifyPrefs.channels` 가 「`email` · `sms` · `webpush` 중에서」라고 적어 두었는데
    #   (마이그 0029 · 턴 Q), 이 목록에는 그 이름이 없어서 **`webpush` 규칙을 저장하면
    #   「모르는 채널」로 400** 이었다 [실측 2026-09-16]. 스키마와 검사가 다른 이름을 쓰면
    #   화면이 고를 수 있는 채널을 서버가 거절한다 — 두 벌이 갈린 자리다(D-212).
    #   자리를 여기 세워 **고르고 저장까지는 되게** 한다. 발송기(VAPID·서비스워커)는
    #   U3 차선이 짓고, 그것이 서면 `REGISTRY` 에 한 줄로 들어와 이 줄보다 먼저 잡힌다
    #   (`_ChannelRegistry.get` 이 REGISTRY 를 먼저 본다 — 두 경로가 충돌하지 않는다).
    "webpush": "웹푸시 발송기(VAPID 키·서비스워커)가 선행 — U3 차선이 짓는다. "
               "이름은 `DsmNotifyPrefs.channels` 스키마가 이미 쓰고 있어 자리를 맞췄다.",
}


# ─────────────────────────────────────────────────────────────────────────────
# 조회·등록 — **모듈 최상위 함수로 두지 않는다**
# ─────────────────────────────────────────────────────────────────────────────
#
# `kernels/` 안의 모듈 최상위 공개 함수는 `*, scope: TenantScope` 를 **필수로** 요구받는다
# (D-281 · `scripts/verify_tenant_scope.py`). 그 규약에는 면제가 없고, 있어서도 안 된다 —
# 면제를 하나 열면 다음 함수가 그 문으로 들어온다.
#
# 그런데 아래 셋은 **테넌트 데이터를 만지지 않는다.** 채널 이름을 어댑터에 잇는 사전 조회다.
# 그러므로 규약을 무르게 하는 대신 **모양을 바꾼다**: 레지스트리 객체의 메서드로 둔다.
# 이제 이 파일에 커널 공개 함수는 0개이고, 게이트는 무를 것 없이 통과한다.
class _ChannelRegistry:
    """채널 이름 → 어댑터. 테넌트를 만지지 않는다."""

    def get(self, channel: str) -> Channel | None:
        return REGISTRY.get(channel)

    def why_unavailable(self, channel: str) -> str:
        """왜 이 채널로 못 보내는가. **모르는 채널과 미정 채널을 가른다.**"""
        if channel in UNAVAILABLE:
            return f"채널 미구현 — {UNAVAILABLE[channel]}"
        return (f"알 수 없는 채널 {channel!r} — 등록된 채널: "
                f"{', '.join(sorted(REGISTRY))} / 미구현: {', '.join(sorted(UNAVAILABLE))}")

    def register(self, channel: Channel) -> Callable[[], None]:
        """어댑터를 끼운다. **되돌리는 함수를 돌려준다** — 시험이 전역 상태를 남기지 않게."""
        previous = REGISTRY.get(channel.name)
        REGISTRY[channel.name] = channel

        def undo() -> None:
            if previous is None:
                REGISTRY.pop(channel.name, None)
            else:
                REGISTRY[channel.name] = previous

        return undo


#: 부르는 쪽이 쓰는 이름. `channels.get(...)` 이 `channels.channels.get(...)` 이 되지 않게
#: 모듈 수준 이름 하나로 노출한다.
_registry = _ChannelRegistry()

get = _registry.get
why_unavailable = _registry.why_unavailable
register = _registry.register
