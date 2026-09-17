# -*- coding: utf-8 -*-
"""M4 · CH-03 — **웹푸시 구독**과 **내 알림 설정** (2026-09-16 · 턴 S · 차선 U3).

이 파일이 답하는 것 둘
----------------------
    ① **이 사람의 이 기기로 푸시를 보낼 수 있는가** — 구독 등록·목록·해지 (WS-08)
    ② **이 사람이 언제·어디서·어느 채널로 받겠다고 했는가** — M4 알림 설정 (WS-02)

왜 구독에 새 표를 만들지 않았나 [판정 · 턴 S]
---------------------------------------------
`kernels/k1_event/field_reply.py` 와 `stream_monitors/services/drill.py` 가 이미
같은 판단을 적어 두었다 — **감사 한 줄이 정본이다.** 구독에도 그대로 선다:

    · 모델·마이그레이션은 이번 턴 U3 의 소유가 아니다(`stream_monitors/models.py` ·
      F-DB 차선). 새 표를 이 차선이 세우면 병합에서 가장 비싼 충돌이 난다.
    · 구독은 **사건이지 상태가 아니다**: 언제 걸었나 · 누구의 어느 기기인가 ·
      언제 껐나. 그 셋이 없으면 「그날 왜 알림을 못 받았나」에 답할 수 없고,
      답 못 하는 미수신은 **장애와 구별되지 않는다**(drill.py 머리말과 같은 문장).
    · 지금 켜져 있는가는 **그 기기의 마지막 줄**이 답한다.

⚠ 그 대신 **읽기 좁히기를 표가 해 주지 못한다.** 감사 표(dj-core · §0.4)에는 테넌트
  칸이 없다. 그래서 좁히기는 이 파일의 함수가 한다 — `_live_rows` 가 **요청자 자신의
  행**만 모은다. 구독은 테넌트의 것이 아니라 **한 사람의 한 기기**의 것이다:
  같은 기관 동료의 휴대전화 구독이 내 화면에 보이면 그것도 누출이다.

무엇을 내보내지 않는가 — **엔드포인트는 자격이다**
--------------------------------------------------
푸시 엔드포인트 URL 은 그 자체가 **그 기기로 알림을 밀어 넣을 수 있는 주소**다
(웹훅 수신 URL 과 같은 급이고, 서명키와 같은 취급을 받아야 한다). 그래서 저장은
하되(보내려면 필요하다) **응답에는 절대 싣지 않는다** — 나가는 것은 `endpoint_sha12`
(sha256 앞 12자)와 사람이 고른 기기 이름뿐이다. 「어느 기기인가」를 사람이 가리기엔
그 둘로 충분하고, 새면 되돌릴 수 없는 값은 애초에 내보내지 않는다(D-335 ④ 와 같은 결).

VAPID 키 — **이름만 코드에 있고 값은 환경에만 있다**
-----------------------------------------------------
공개키는 정의상 공개다(브라우저가 `pushManager.subscribe` 에 그 값을 넣는다) —
그래서 라우트로 내보낸다. 비밀키는 **이 파일이 읽지 않는다**: 읽는 곳은 발송
어댑터 한 곳뿐이고(`kernels/k2_notify/channels.py::WebPushChannel`), 여기서는
「있는가/없는가」만 묻는다. 값도, 길이도, 지문도 남기지 않는다(D-204 · 게이트는
값을 출력하지 않는다).
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import time as _time

from django.apps import apps

from common import audit_writer
from common.tenant_filters import filter_by_group_field, get_user_group

# ═══════════════════════════════════════════════════════════════════════════
# 0. 이름 — **이 문자열들로 전건을 뽑는다** (D-285 ②)
# ═══════════════════════════════════════════════════════════════════════════
#: 구독 감사의 `logger_name`. 현장 회신(`…dsm.field_reply`)·대응 전이(`…dsm.response`)와
#: **다른 이름**이다: 섞으면 「회신 N건」·「전이 N건」이 구독 수만큼 부풀어 오른다.
LOGGER_NAME = "guardianx.dsm.push_subscription"
TAG = "[PUSH]"
ACTION_SUBSCRIBE = "push.subscribe"
ACTION_UNSUBSCRIBE = "push.unsubscribe"
ACTION_TEST_SEND = "push.test_send"

#: VAPID 자격의 **환경변수 이름 셋.** 값은 여기 없다 — 이름만 있다.
VAPID_PUBLIC_ENV = "GX_VAPID_PUBLIC_KEY"
VAPID_PRIVATE_ENV = "GX_VAPID_PRIVATE_KEY"
VAPID_SUBJECT_ENV = "GX_VAPID_SUBJECT"

#: 기기 이름의 상한. 사람이 적는 칸이고, 감사 `note` 에 들어간다.
MAX_LABEL_CHARS = 60

#: 한 사람이 걸 수 있는 기기 수. 상한이 없으면 **한 계정이 감사 표를 채운다**.
MAX_SUBSCRIPTIONS_PER_USER = 10

#: M4 가 고를 수 있는 채널. `DsmNotifyPrefs.channels` 주석이 선언한 셋 그대로다 —
#: 이름이 갈리면 저장은 되는데 아무 채널도 안 맞는 설정이 생긴다.
#: ★ [턴 T · 대표 결정 ① 「이메일 + 웹푸시」] `sms` 는 **선택지에서 뺀다**(CH-01 문자 범위 밖).
#:   DB 스키마 주석은 셋을 적고 있지만 화면이 고를 수 있는 것은 이 둘이다 — 옛 행에 `sms`
#:   가 남아 있어도 읽기는 그대로 내고, 새로 저장할 때만 거절한다.
ALLOWED_PREF_CHANNELS = ("email", "webpush")

#: 「관리자 승인 필요」 칸 — **서버가 내는 값**이다. 지금 이 설정의 항목 셋(차단 시간대 ·
#: 담당 구역 · 채널)은 전부 본인이 정하는 것이라 승인 대상이 **없다**. 대상이 생기면
#: 이 목록에 이름이 들어오고 `status` 가 `pending` 으로 바뀐다 — 화면은 이 값을 그대로 적는다.
APPROVAL_STATUS_NOT_REQUIRED = "not_required"
APPROVAL_ITEMS: tuple[str, ...] = ()

#: 이 파일이 만드는 설정 행의 목적 코드(ISO-03 · 설계서 §3 ③).
PURPOSE_CODE = "dsm.notify_prefs"


class PushSubscriptionRejected(Exception):
    """값이 계약 밖이다 — **422**. 문법이 아니라 값의 문제다(D-290)."""


class PushSubscriptionNotFound(Exception):
    """그런 구독이 없다 — **404**.

    ★ 남의 구독일 때도 이것이다. 403 을 내면 「그 번호는 있는데 네 것이 아니다」가
      새고, 존재 여부가 새는 것도 누출이다(`delete_webhook_subscription` 과 같은 판정).
    """


class PushSendNoEvent(Exception):
    """시험 발송을 매달 사건이 없다(409)."""


class NotifyPrefsRejected(Exception):
    """설정 값이 계약 밖이다 — **422**."""


# ═══════════════════════════════════════════════════════════════════════════
# 1. VAPID — 있는가/없는가만 묻는다
# ═══════════════════════════════════════════════════════════════════════════
def vapid_public_key() -> str:
    """브라우저가 구독에 쓰는 **공개키.** 없으면 빈 문자열이다.

    공개키를 내보내는 것은 누출이 아니다 — 그 값은 `applicationServerKey` 로
    모든 구독자의 브라우저에 들어간다. 비밀키는 이 함수가 **읽지도 않는다.**
    """
    return (os.environ.get(VAPID_PUBLIC_ENV, "") or "").strip()


def vapid_status() -> dict:
    """웹푸시를 보낼 수 있는 모양인가. **값은 한 글자도 내보내지 않는다.**

    ★★ [턴 S · 조율자 지시] 이 함수는 **상태만** 낸다 — 있다/없다 · 이름 ·
      sha256 앞 12자까지다. 공개키 **값**이 필요한 곳은 단 하나(브라우저의
      `applicationServerKey`)이고, 그 값은 라우트가 `vapid_public_key()` 를 따로
      불러 싣는다(`api_u3.py::push_vapid_key`). 둘을 한 함수에 두면 「상태를
      물었을 뿐인데 값이 따라 나오는」 자리가 되고, 그런 자리가 로그·증거·캡처에
      값을 흘린다(게이트 `verify_no_secret_echo` 가 매 커밋 도는 이유).

    ⚠ 「설정됐다」는 「도달한다」가 아니다 — `EmailChannel.configured()` 머리말의
      그 구별이 여기에도 그대로 선다. 이 함수는 **보내 보지 않는다**: 보내 보면
      그것은 이미 발송이고, 「설정됐는가」를 묻는 데 이력을 만들면 이력이 오염된다.
    """
    public = vapid_public_key()
    private_present = bool((os.environ.get(VAPID_PRIVATE_ENV, "") or "").strip())
    subject = (os.environ.get(VAPID_SUBJECT_ENV, "") or "").strip()
    missing = [name for name, ok in (
        (VAPID_PUBLIC_ENV, bool(public)),
        (VAPID_PRIVATE_ENV, private_present),
        (VAPID_SUBJECT_ENV, bool(subject)),
    ) if not ok]
    return {
        "configured": not missing,
        #: **이름만** 적는다 — 없는 것을 사람이 채우려면 이름이 필요하고, 이름은 비밀이 아니다.
        "missing_env": missing,
        "env_names": [VAPID_PUBLIC_ENV, VAPID_PRIVATE_ENV, VAPID_SUBJECT_ENV],
        #: 지문 12자 — 「지금 선 키가 내가 넣은 그 키인가」를 값 없이 대조하는 자리
        #: (메모리 「판정기의 [입력] 줄이 거짓말한다」가 자격을 이렇게 대조하라고 적은 그대로).
        "public_key_sha12": (hashlib.sha256(public.encode("utf-8")).hexdigest()[:12]
                             if public else ""),
        "reason": ("" if not missing else
                   "웹푸시 자격이 이 환경에 없습니다 — 비어 있는 환경변수: "
                   + ", ".join(missing)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. 구독 — 감사 한 줄이 정본이다
# ═══════════════════════════════════════════════════════════════════════════
def _audit_model():
    return apps.get_model("logger", "AuditLogs")


def endpoint_fingerprint(endpoint: str) -> str:
    """엔드포인트의 **지문 12자.** 이것이 밖으로 나가는 유일한 식별자다. sha256"""
    digest = hashlib.sha256((endpoint or "").encode("utf-8")).hexdigest()
    return digest[:12]


def _payload_of(row) -> dict:
    """`data_after` 를 사전으로. **못 읽으면 빈 것으로 본다** — 던지지 않는다.

    감사 한 줄이 깨졌다고 나머지 구독을 못 읽게 되면 고장 하나가 화면 전체를 비운다
    (`field_reply._payload_of` 와 같은 규약).
    """
    raw = getattr(row, "data_after", None)
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, (str, bytes)):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _rows_of(user_id: int) -> list:
    """이 **사람**의 구독 전환 전건, 최신순.

    ⚠ 좁히기를 표가 해 주지 못한다(머리말 ⚠). 그래서 이 한 줄이 문지기다 —
      `user_id` 로 거르는 것을 빼면 같은 기관 동료의 기기가 내 목록에 들어온다.
    """
    rows = (
        _audit_model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id)
        .exclude(api_name=ACTION_TEST_SEND)
        .order_by("-id")[:2000]
    )
    return list(rows)


def _live_subscriptions(user_id: int) -> list[dict]:
    """지금 살아 있는 구독들. **기기마다 마지막 줄이 답한다**(drill.py 와 같은 형)."""
    seen: dict[str, dict] = {}
    for row in _rows_of(user_id):
        payload = _payload_of(row)
        fingerprint = str(payload.get("endpoint_sha12") or "")
        if not fingerprint or fingerprint in seen:
            continue          # 최신순이므로 처음 만난 줄이 그 기기의 현재 상태다
        seen[fingerprint] = {
            "subscription_id": row.pk,
            "endpoint_sha12": fingerprint,
            "label": str(payload.get("label") or ""),
            "created_at": getattr(row, "create_datetime", None) or getattr(
                row, "created_on", None),
            "live": str(payload.get("action") or "") == ACTION_SUBSCRIBE,
            #: 밖으로 나가지 않는다 — 발송기만 본다.
            "_endpoint": str(payload.get("endpoint") or ""),
            "_p256dh": str(payload.get("p256dh") or ""),
            "_auth": str(payload.get("auth") or ""),
        }
    return [row for row in seen.values() if row["live"]]


def _public(row: dict) -> dict:
    """화면·API 가 보는 모양. **엔드포인트도 키도 없다**(머리말 「무엇을 내보내지 않는가」)."""
    return {
        "subscription_id": row["subscription_id"],
        "endpoint_sha12": row["endpoint_sha12"],
        "label": row["label"],
        "created_at": row["created_at"],
    }


def subscribe(*, scope, endpoint: str, p256dh: str, auth_secret: str,
              label: str = "") -> dict:
    """이 기기를 등록한다 (WS-08).

    ★ 인자 이름이 `auth_secret` 인 것은 **동음이의를 피하려는 것**이다 (D-337 ·
      게이트 `verify_homonyms`). 이 저장소에서 `auth` 는 **인증(누구인가)** 을 뜻하고
      (`@route.post(auth=…)` 가 그 자리다), 여기 오는 값은 그것이 아니라 **웹푸시
      구독의 복호화 비밀**(RFC 8291 `keys.auth`)이다. 두 뜻이 한 낱말이면 다음 사람이
      이 값을 문지기로 읽는다.
    ⚠ 규격이 정한 이름(`keys.auth`)은 **JSON 칸으로만** 남는다 — 그 자리는 브라우저와
      발송기가 맞춰야 하는 모양이라 우리가 바꿀 수 없고, 바꾸면 발송이 죽는다.

    문턱 넷:
        ① **사람인가** — 시스템 스코프는 구독할 기기가 없다. 행위자 없는 구독은
           「누구에게 보내는가」에 답하지 못한다(회신·판정과 같은 판단 · D-281).
        ② **세 값이 다 있는가** — 엔드포인트만으로는 **암호화를 못 한다.** 키 없이
           등록을 받아 두면 「구독했는데 아무것도 안 온다」가 되고, 그 침묵은
           권한 거부·차단 시간과 구별되지 않는다.
        ③ **상한** — 한 사람 `MAX_SUBSCRIPTIONS_PER_USER` 대까지.
        ④ **같은 기기를 두 번 세지 않는다** — 지문이 같으면 **갱신**이다(브라우저가
           구독을 갱신하면 키만 바뀌고 사람은 같은 기기라고 생각한다).
    """
    actor = scope.require_actor()      # ① 시스템 스코프면 SystemScopeCannotRead

    endpoint = (endpoint or "").strip()
    p256dh = (p256dh or "").strip()
    auth_secret = (auth_secret or "").strip()
    if not endpoint or not p256dh or not auth_secret:
        raise PushSubscriptionRejected(
            "구독에는 endpoint · p256dh · auth 셋이 모두 필요합니다. "
            "키 없는 구독은 암호화를 못 해 **보낼 수 없는 구독**이 되고, "
            "그 침묵은 「차단 시간」·「권한 없음」과 구별되지 않습니다.")
    if not endpoint.startswith("https://"):
        raise PushSubscriptionRejected(
            "푸시 엔드포인트는 https 여야 합니다 — 평문은 받지 않습니다.")

    fingerprint = endpoint_fingerprint(endpoint)
    live = _live_subscriptions(getattr(actor, "pk", None))
    if (len(live) >= MAX_SUBSCRIPTIONS_PER_USER
            and fingerprint not in {r["endpoint_sha12"] for r in live}):
        raise PushSubscriptionRejected(
            f"한 사람이 걸 수 있는 기기는 {MAX_SUBSCRIPTIONS_PER_USER}대까지입니다. "
            f"쓰지 않는 기기를 먼저 해지해 주십시오.")

    clean_label = (label or "").strip()[:MAX_LABEL_CHARS] or "이름 없는 기기"

    entry = audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=ACTION_SUBSCRIBE, outcome=audit_writer.ALLOWED,
        #: ★ 사유에 **값을 적지 않는다** — 감사 `note` 는 사람이 눈으로 훑는 자리다.
        reason=f"웹푸시 구독 등록 — {clean_label} ({fingerprint})",
        after={
            "action": ACTION_SUBSCRIBE,
            "endpoint_sha12": fingerprint,
            "label": clean_label,
            #: 보내려면 있어야 한다. **응답에는 안 나간다**(`_public`).
            "endpoint": endpoint,
            #: ★ 칸 이름은 **규격의 것**이다(`keys.p256dh` · `keys.auth`) — 발송기와
            #:   브라우저가 이 모양으로 맞춘다. 파이썬 쪽 이름만 주체를 붙였다.
            "p256dh": p256dh,
            "auth": auth_secret,
        },
        api_name=ACTION_SUBSCRIBE, api_method="POST",
    )
    return {
        "subscription_id": entry.audit_id,
        "endpoint_sha12": fingerprint,
        "label": clean_label,
        "created_at": None,
    }


def list_subscriptions(*, scope) -> tuple[dict, ...]:
    """내 기기들. **남의 기기는 한 대도 안 나온다**(머리말 ⚠)."""
    actor = scope.require_actor()
    return tuple(_public(r) for r in _live_subscriptions(getattr(actor, "pk", None)))


def unsubscribe(*, scope, subscription_id: int) -> dict:
    """이 기기를 끈다. **행을 지우지 않는다** — 언제 무엇을 받았는지가 함께 사라진다.

    ★ 끄는 것도 감사 한 줄이다. 그래야 「그 밤에 왜 안 왔나」에 답할 수 있다.
    """
    actor = scope.require_actor()
    user_id = getattr(actor, "pk", None)

    target = None
    for row in _rows_of(user_id):
        if row.pk == subscription_id:
            target = row
            break
    if target is None:
        #: 남의 구독도 여기로 온다 — `_rows_of` 가 이미 요청자로 좁혔다.
        raise PushSubscriptionNotFound("그런 구독이 없습니다.")

    payload = _payload_of(target)
    fingerprint = str(payload.get("endpoint_sha12") or "")
    label = str(payload.get("label") or "")

    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=ACTION_UNSUBSCRIBE, outcome=audit_writer.ALLOWED,
        reason=f"웹푸시 구독 해지 — {label} ({fingerprint})",
        after={
            "action": ACTION_UNSUBSCRIBE,
            "endpoint_sha12": fingerprint,
            "label": label,
            #: 해지 줄에는 자격을 다시 적지 않는다 — 끈 뒤에도 남을 이유가 없다.
        },
        api_name=ACTION_UNSUBSCRIBE, api_method="DELETE",
    )
    return {"subscription_id": subscription_id, "endpoint_sha12": fingerprint,
            "label": label, "live": False}


# ═══════════════════════════════════════════════════════════════════════════
# 3. 시험 발송 — **훈련 알림이고, 내 기기로만 간다**
# ═══════════════════════════════════════════════════════════════════════════
#: 시험 발송 본문의 머리. 잠금화면에 이 글자가 뜬다 — 받은 사람이 **진짜 경보와
#: 즉시 가른다.** 이것이 없으면 시험 한 번이 현장 출동 한 번이 된다.
DRILL_TITLE = "[훈련] GuardianX 알림 시험"
DRILL_BODY = "이 알림은 시험입니다 — 출동하지 마십시오."

#: 턴 S 의 사유 문장 — **이제 쓰이지 않는다.** 이름은 남긴다: 턴 S 화면 문구·보고가 이 이름을
#: 인용했고, 「문이 없었다」는 사실은 지워지지 않는다(D-284). 문은 턴 T 에 열렸다(P-160 ③).
KERNEL_SENDER_MISSING = (
    "웹푸시 발송 문이 커널 공개 면에 아직 없습니다 — `kernels.k2_notify` 가 "
    "`send_webpush` 를 내주면 이 자리가 그대로 씁니다. 어댑터(`WebPushChannel`)는 "
    "이미 서 있고, 남은 것은 공개 면 한 줄입니다(조율자에게 청함)."
)


class PushSendNotConfigured(Exception):
    """VAPID 자격·발송기가 이 환경에 없다. `missing_env` 는 **이름 목록**이다 — 값이 아니다."""

    def __init__(self, missing_env: list[str], reason: str) -> None:
        self.missing_env = list(missing_env)
        super().__init__(reason)


def _anchor_event_id(scope, event_id: int | None):
    """시험 발송 행이 매달릴 **훈련 사건**. 준 것이 없으면 내 기관의 가장 최근 사건.

    왜 사건이 필요한가 — `deliveries` 는 사건에 매달린 표다(F-10 의 두 점). 사건 없는
    행은 만들 수 없고, 만들면 그 표의 뜻이 바뀐다. 사건이 0건이면 **없다고 말한다**
    (409) — 지어내지 않는다.
    """
    Event = apps.get_model("stream_monitors", "DetectionEvent")
    if event_id:
        return int(event_id)
    qs = filter_by_group_field(Event._base_manager.all(), scope.actor, field="group")
    latest = qs.order_by("-occurred_at", "-id").values_list("pk", flat=True).first()
    return latest


def send_test_push(*, scope, title: str = "", body: str = "",
                   event_id: int | None = None) -> dict:
    """내 기기들로 **훈련 알림**을 한 번 보낸다 — 커널의 `send_webpush` 문을 탄다(P-160 ③).

    ★ 턴 S 까지 이 함수는 커널을 부르지 않았다 — 공개 이름이 없었기 때문이다. 턴 T 에
      그 이름이 **부르는 쪽(여기)과 같은 커밋**에 열렸고, 이제 한 통이 실제로 나간다.
    ★ **행은 남는다** — `deliveries` `channel=webpush`. 다만 훈련 표식(`drill:`)을 달아
      5분 억제의 근거가 되지 않는다(턴 S 시험이 지키던 「다음 진짜 경보를 삼키지 않는다」는
      그대로 선다 — 방법이 「행을 안 만든다」에서 「행에 표식을 단다」로 바뀌었다).
    ★ 받는 사람은 요청자 자신뿐이다. 남의 기기를 고를 인자가 없다.
    ★ 본문이 자신을 훈련이라 말한다 — 제목이 `[훈련]` 으로 시작하지 않으면 붙인다.
    ★ 자격이 없으면 503 감(`PushSendNotConfigured` · `missing_env` 이름 목록) — 행 0.
    """
    from kernels.k2_notify import (
        WebPushNotConfigured, send_webpush, webpush_missing_env)
    from stream_monitors.services.drill import is_drill_mode

    actor = scope.require_actor()
    rows = _live_subscriptions(getattr(actor, "pk", None))
    if not rows:
        raise PushSubscriptionRejected(
            "등록된 기기가 없습니다 — 먼저 이 기기에서 「알림 받기」를 켜 주십시오. "
            "(구독 0건과 발송 실패는 다른 사실입니다.)")

    missing = webpush_missing_env(scope=scope)
    if missing:
        raise PushSendNotConfigured(
            missing, "웹푸시 자격이 이 환경에 없습니다 — 비어 있는 환경변수: "
                     + ", ".join(missing) + ". 값은 저장소 밖 `.env` 로만 줍니다(D-204).")

    anchor = _anchor_event_id(scope, event_id)
    if not anchor:
        raise PushSendNoEvent(
            "시험 발송을 매달 사건이 이 기관에 없습니다 — 발송 이력은 사건에 매달리는 "
            "표라 사건 0건이면 한 통도 기록할 수 없습니다.")

    group = get_user_group(actor)
    drill = is_drill_mode(group_id=getattr(group, "pk", None))

    subject = (title or "").strip() or DRILL_TITLE
    if not subject.startswith("[훈련]"):
        subject = "[훈련] " + subject
    message = (body or "").strip() or DRILL_BODY

    results = []
    for row in rows:
        subscription = {"endpoint": row["_endpoint"],
                        "keys": {"p256dh": row["_p256dh"], "auth": row["_auth"]}}
        try:
            view = send_webpush(scope=scope, subscription=subscription,
                                title=subject, body=message, event_id=anchor)
        except WebPushNotConfigured as exc:
            raise PushSendNotConfigured(exc.missing_env, str(exc)) from exc
        results.append({
            "endpoint_sha12": row["endpoint_sha12"],
            "label": row["label"],
            "sent": bool(view.succeeded),
            "delivery_id": view.delivery_id,
            "succeeded": bool(view.succeeded),
            #: 실패 사유는 **이름·문장**이지 값이 아니다 — 어댑터가 예외 종류만 남긴다.
            "failure_reason": view.failure_reason,
            "reason": view.failure_reason or "",
        })

    sent = sum(1 for r in results if r["sent"])
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor,
        action=ACTION_TEST_SEND, outcome=audit_writer.ALLOWED,
        reason=f"웹푸시 시험 발송 — 기기 {len(results)}대 중 {sent}대 성공"
               + (" (훈련 모드)" if drill else ""),
        after={"action": ACTION_TEST_SEND, "devices": len(results), "sent": sent,
               "drill_mode": drill, "event_id": anchor,
               "delivery_ids": [r["delivery_id"] for r in results]},
        api_name=ACTION_TEST_SEND, api_method="POST",
    )
    first = results[0]
    return {
        "devices": len(results),
        #: 0 을 「없음」으로 적지 않는다 — **모수와 함께** 적는다(D-301).
        "sent": sent,
        "drill_mode": drill,
        "title": subject,
        "event_id": anchor,
        "channel": "webpush",
        #: 첫 기기의 결과를 위로 올린다 — 화면 상태 칸 한 줄이 이 셋을 읽는다.
        "delivery_id": first["delivery_id"],
        "succeeded": first["succeeded"],
        "failure_reason": first["failure_reason"],
        "results": results,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 4. M4 — 내 알림 설정 (WS-02 · `dsm_notify_prefs`)
# ═══════════════════════════════════════════════════════════════════════════
def _prefs_model():
    return apps.get_model("stream_monitors", "DsmNotifyPrefs")


def _row_of(user_id: int):
    return (_prefs_model()._base_manager
            .filter(user_id=user_id, deleted__isnull=True)
            .order_by("-id").first())


def _hhmm(value) -> str:
    """`time` → `"22:00"`. 없으면 빈 문자열 — `None` 과 `""` 를 섞지 않는다."""
    return value.strftime("%H:%M") if value else ""


def _parse_hhmm(raw: str, field: str):
    """`"22:00"` → `time`. 비면 `None`. 모양이 틀리면 **던진다** — 조용히 안 접는다."""
    text = (raw or "").strip()
    if not text:
        return None
    parts = text.split(":")
    if len(parts) != 2:
        raise NotifyPrefsRejected(f"{field} 는 `HH:MM` 이어야 합니다 — 받은 값: {text!r}")
    try:
        hour, minute = int(parts[0]), int(parts[1])
        return _time(hour=hour, minute=minute)
    except (TypeError, ValueError) as exc:
        raise NotifyPrefsRejected(
            f"{field} 를 시각으로 읽지 못했습니다 — 받은 값: {text!r}") from exc


def _view(row) -> dict:
    """설정 한 벌의 모양. **행이 없어도 모양은 같다** — 「아직 안 정했다」는 빈 칸이다.

    ⚠ 빈 칸의 뜻은 전부 **「좁히지 않는다」**다(`DsmNotifyPrefs` 머리말). 이 설정은
      규칙이 고른 수신을 좁히기만 하고 넓히지 못한다 — 그래서 빈 설정은 「아무것도
      안 받는다」가 아니라 「규칙 그대로 받는다」다.
    """
    return {
        "quiet_start": _hhmm(getattr(row, "quiet_start", None)),
        "quiet_end": _hhmm(getattr(row, "quiet_end", None)),
        "zone_ids": list(getattr(row, "zone_ids", None) or []),
        "channels": list(getattr(row, "channels", None) or []),
        "saved": row is not None,
        "allowed_channels": list(ALLOWED_PREF_CHANNELS),
        #: 「관리자 승인 필요」 — 서버 판정. 화면은 이 두 칸을 그대로 적는다.
        "approval": {
            "status": APPROVAL_STATUS_NOT_REQUIRED,
            "items": list(APPROVAL_ITEMS),
            "note": ("이 설정의 항목은 본인이 정합니다 — 관리자 승인이 필요한 항목이 "
                     "지금은 없습니다."),
        },
        "note": ("빈 칸은 「좁히지 않는다」는 뜻입니다 — 이 설정은 규칙이 고른 수신을 "
                 "좁히기만 하고 넓히지 못합니다."),
    }


def notify_prefs(*, scope) -> dict:
    """내 알림 설정. **없으면 빈 설정**이고, 그 사실을 `saved` 가 말한다."""
    actor = scope.require_actor()
    return _view(_row_of(getattr(actor, "pk", None)))


def save_notify_prefs(*, scope, quiet_start: str = "", quiet_end: str = "",
                      zone_ids: str = "", channels: str = "") -> dict:
    """설정을 저장한다 (M4 · WS-02). 살아 있는 행은 **계정당 하나**다.

    거절 셋 — 전부 `NotifyPrefsRejected`(422):
        · 차단 시간대를 **한쪽만** 채웠다 — DB CHECK 가 막는 그 자리를 먼저 사람의
          말로 막는다. DB 오류로 떨어지면 화면이 무엇을 고칠지 모른다.
        · 채널 이름이 계약 밖이다 — 저장은 되는데 아무 채널도 안 맞는 설정이 된다.
        · 구역 id 가 수가 아니다.
    """
    actor = scope.require_actor()
    user_id = getattr(actor, "pk", None)

    start = _parse_hhmm(quiet_start, "근무 외 시작")
    end = _parse_hhmm(quiet_end, "근무 외 종료")
    if (start is None) != (end is None):
        raise NotifyPrefsRejected(
            "근무 외 차단 시간대는 시작과 종료를 **함께** 정해야 합니다. "
            "한쪽만 있으면 언제부터 언제까지 안 받는지 아무도 모릅니다.")

    names = [c.strip() for c in (channels or "").split(",") if c.strip()]
    unknown = [c for c in names if c not in ALLOWED_PREF_CHANNELS]
    if unknown:
        raise NotifyPrefsRejected(
            f"모르는 채널: {', '.join(unknown)}. "
            f"쓸 수 있는 것: {', '.join(ALLOWED_PREF_CHANNELS)}")

    zones: list[int] = []
    for chunk in (zone_ids or "").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            zones.append(int(chunk))
        except ValueError as exc:
            raise NotifyPrefsRejected(
                f"구역 번호가 수가 아닙니다: {chunk!r}") from exc

    group = get_user_group(actor)
    if group is None:
        raise NotifyPrefsRejected(
            "소속 조직이 없어 알림 설정을 저장할 수 없습니다 — 어느 기관의 규칙을 "
            "좁히는 설정인지 정할 수 없기 때문입니다.")

    Prefs = _prefs_model()
    row = _row_of(user_id)
    if row is None:
        row = Prefs.objects.create(
            user_id=user_id, quiet_start=start, quiet_end=end,
            zone_ids=zones, channels=names, group=group,
            purpose_code=PURPOSE_CODE)
    else:
        row.quiet_start = start
        row.quiet_end = end
        row.zone_ids = zones
        row.channels = names
        row.save(update_fields=["quiet_start", "quiet_end", "zone_ids", "channels"])
    return _view(row)
