# -*- coding: utf-8 -*-
"""이벤트 ↔ 영상 — **구간 참조는 지금 돌고, 구간 추출은 선언된 미완성이다** (D-306).

한 문장
-------
    "어디를 보라" 까지가 이번에 여는 것이다. **바이트는 아직 나가지 않는다.**

무엇이 있고 무엇이 없나 (D-300 부작위 시험 대상)
------------------------------------------------
    있다  · `reference_for_event`  — 이벤트 시각의 녹화를 찾아 구간을 적는다 (쓰기 1곳)
          · `issue_ticket`         — 만료 서명 티켓. **구간에 묶여 있다**
          · `verify_ticket`        — 서명·만료·구간을 함께 본다
          · `CLIP_EXTRACTION_READY`— 추출 잠금 상수

    없다  · 구간 추출·트랜스코딩 · ffmpeg 호출 · 새 인코딩
          · **원본 객체를 통째로 주는 URL** — 계약 11조가 금지한다. 만들지 않았음을
            `test_clip_playback.py` 의 규약 ④ 가 잰다
          · 이벤트 밖에서 나중에 채우는 배치 — 그것이 `clip_path` 가 죽은 필드가 된 경로다

왜 티켓인가 — **프리사인드 URL 을 쓰지 않는 이유**
--------------------------------------------------
MinIO 의 프리사인드 URL 은 **객체 전체**를 준다. 그것을 내보내면 계약 11조(원본 영상
무반출)를 정면으로 어긴다 — 요청한 30초를 주려다 두 시간짜리 원본을 준다.

그래서 우리 티켓은 `(event_id · object_key · start · duration · exp)` 에 **묶여 서명된다.**
구간을 바꾸면 서명이 깨지고, 시간이 지나면 만료된다. 그리고 그 티켓으로 바이트를 받는
경로는 **아직 잠겨 있다**(`CLIP_EXTRACTION_READY=False`) — 지금은 어떤 바이트도 나가지 않는다.

  요컨대 이번에 연 것은 **"어디를 보라"를 안전하게 말하는 능력**이고,
  "보여 주는" 능력은 상수 하나 뒤에 선언된 채로 있다.

★ 세 번째 재사용 — 이제 이것은 우리 표준이다 (D-306)
----------------------------------------------------
SDN(`KERNEL_READY`) · ZONE(`ZONE_POLYGON_READY`) 에 이어 세 번째다.
잠긴 기능은 상수로 잠그고, 사유가 비면 게이트 exit 1, 상수를 올리면 그 기능의 계약 AC
시험이 즉시 의무가 된다.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from common.tenant_scope import TenantScope

#: E2E 등재부가 보는 선언. 구간 참조가 실재하므로 True 다 — 열리는 것은 참조까지다.
KERNEL_READY: bool = True

#: ★ 구간 추출·트랜스코딩의 잠금. False 인 동안 **어떤 바이트도 나가지 않는다.**
#:
#:   올리는 조건은 둘이다:
#:     ① `_extract_window` 가 실재할 것 (지금은 없다)
#:     ② 추출 결과의 무결성 시험이 실재할 것 —
#:        `backend/tests/test_clip_playback.py::test_extraction_integrity_contract_ac`
#:   ②가 없는데 올리면 `scripts/verify_clip_extraction.py` 가 exit 1 한다.
CLIP_EXTRACTION_READY: bool = False

#: `CLIP_EXTRACTION_READY=False` 일 때 **반드시 채워져 있어야 한다.** 비면 게이트가 exit 1.
CLIP_EXTRACTION_NOT_READY_REASON: str = (
    "구간 추출·트랜스코딩을 구현하지 않았다. 원본 녹화에서 30초를 잘라 내려면 "
    "① 객체 저장소에서 바이트 구간을 읽고 ② 키프레임 경계를 맞춰 재인코딩하고 "
    "③ 그 산출물을 다시 저장해야 한다 — 셋 다 이번 범위(D-306 '여는 것은 참조까지다')를 "
    "넘고, 특히 ②는 코덱·컨테이너별로 다른 판단이라 실측 없이 고르면 그 선택이 곧 "
    "F-09 의 계약이 된다(D-280). "
    "그동안 재생 라우트는 **구간에 묶인 만료 티켓**만 내고 바이트를 흘리지 않는다 — "
    "계약 11조(원본 영상 무반출)를 어기지 않는 유일한 상태다. "
    "해소는 F-09 영상 재생 설계(코덱·전송 방식·보존 기간) 확정이며, 그때 이 상수를 올리면 "
    "추출 무결성 시험이 즉시 의무가 된다."
)

#: 이벤트 앞뒤로 얼마를 잡는가. **여기 한 곳에만 둔다** — 흩으면 조용히 갈린다.
#: 값의 근거: 계약 AC 가 정한 수가 아니라 이 규칙의 값이다(D-280 — 계약이 안 정한 것은
#: 계약인 척하지 않는다). 앞 10초는 "무슨 일이 있기 직전", 뒤 20초는 "무엇이 벌어졌나".
PRE_ROLL_SECONDS: float = 10.0
POST_ROLL_SECONDS: float = 20.0

#: 티켓의 수명. 무기한 링크 금지(D-306 규약 ②).
TICKET_TTL = timedelta(minutes=5)


@dataclass(frozen=True)
class PlaybackTicket:
    """재생 티켓. **구간에 묶여 있고 만료된다.**

    이 값에는 **객체를 통째로 받을 수 있는 URL 이 없다.** 있는 것은 서명 하나와
    그 서명이 허락하는 구간뿐이다 — 계약 11조가 금지한 것이 정확히 "원본 반출" 이다.
    """

    event_id: int
    object_key: str
    start_offset: float
    duration: float
    expires_at: object          # datetime
    token: str
    #: 지금 이 티켓으로 바이트를 받을 수 있는가. 추출이 잠겨 있으면 거짓이다.
    playable: bool
    #: 못 받는 이유. 거짓일 때 **반드시 채워진다** (D-264).
    reason: str = ""


def _model(name: str):
    return apps.get_model("stream_monitors", name)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 구간 참조 — 쓰기 **한 곳**. 이벤트 생성 경로 안에서만 불린다 (D-306)
# ═══════════════════════════════════════════════════════════════════════════
def reference_for_event(event) -> object:
    """이벤트 시각의 녹화를 찾아 구간을 적는다. **행은 언제나 남는다.**

    녹화가 없으면 행을 안 만드는 것이 아니라 `unavailable` + 사유로 남긴다 —
    행이 없으면 "녹화가 없었다" 와 "아직 안 봤다" 가 구별되지 않고, 구별되지 않는 것은
    잊힌다 (D-290 · D-264).

    ★ 새 파일을 만들지 않는다. 이미 있는 `StreamMonitorRecord.object_path` 를 가리킬 뿐이다.
    """
    Clip = _model("EventClip")
    Record = _model("StreamMonitorRecord")

    existing = Clip._base_manager.filter(event_id=event.pk).first()
    if existing is not None:
        return existing                    # 이벤트 하나에 참조 하나. 접힌 관측은 새로 안 만든다

    stream = event.stream_monitor
    when = event.occurred_at

    #: 그 시각에 돌고 있던 녹화. `stream_id` 는 스트림 **코드**다(저장소 실측 —
    #: stream_monitor_services 가 `filter(stream_id=stream_code)` 로 쓴다).
    record = (
        Record.objects
        .filter(stream_id=stream.code, created_at__lte=when)
        .exclude(object_path__isnull=True)
        .exclude(object_path="")
        .order_by("-created_at", "-id")
        .first()
    )

    if record is None:
        return _own(Clip._base_manager.create(
            event=event,
            clip_status=Clip.ClipStatus.UNAVAILABLE,
            unavailable_reason=(
                f"그 시각에 스트림 '{stream.code}' 의 녹화가 없다 — 녹화를 켜지 않았거나 "
                f"객체 경로가 비어 있다. 재시도 대상이 아니다"),
        ), event)

    start = (when - record.created_at).total_seconds() - PRE_ROLL_SECONDS
    return _own(Clip._base_manager.create(
        event=event,
        object_key=record.object_path,
        start_offset=max(0.0, start),
        duration=PRE_ROLL_SECONDS + POST_ROLL_SECONDS,
        clip_status=Clip.ClipStatus.REFERENCED,
    ), event)


def _own(clip, event):
    """소유를 **이벤트에서 물려받는다.** 주인 없는 행은 §0.4 의 OR 절을 타고 모두에게 보인다.

    `k1_event.services._inherit_owner` 와 같은 판단이다 — 필드 이름을 하드코딩하지 않는다
    (실행 중인 dj-core 는 `group` FK 를 준다 · D-292 실측).
    """
    names = {f.name for f in type(clip)._meta.get_fields()}
    if "groups" in names:
        clip.groups.set(event.groups.all())
    elif "group" in names:
        clip.group = getattr(event, "group", None)
        clip.save(update_fields=["group"])
    return clip


# ═══════════════════════════════════════════════════════════════════════════
# 2. 티켓 — **구간에 묶여 서명되고, 만료된다** (규약 ② · ③)
# ═══════════════════════════════════════════════════════════════════════════
def _payload(event_id: int, object_key: str, start: float, duration: float,
             exp_epoch: int) -> str:
    return f"{event_id}|{object_key}|{start:.3f}|{duration:.3f}|{exp_epoch}"


def _sign(payload: str) -> str:
    """서명. 키는 배포마다 다른 `SECRET_KEY` 다 — 저장소에 상수로 두지 않는다(D-204)."""
    return hmac.new(settings.SECRET_KEY.encode("utf-8"),
                    payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_ticket(*, scope: TenantScope, event_id: int,
                 ttl: timedelta = TICKET_TTL) -> PlaybackTicket:
    """이벤트의 재생 티켓. **남의 이벤트면 404** — 존재도 알리지 않는다 (규약 ① · D-269).

    `Http404` 를 던진다. 403 이 아닌 이유: 403 은 "있는데 못 본다" 를 알려 주고,
    그것만으로도 남의 테넌트에 그 id 가 있다는 사실이 샌다.
    """
    from django.http import Http404

    from common.tenant_filters import get_scoped_or_404

    Event = _model("DetectionEvent")
    Clip = _model("EventClip")

    if scope.is_system:
        raise Http404("재생 티켓은 사람이 요청한다 — 시스템 스코프로 발급하지 않는다 (D-281)")
    event = get_scoped_or_404(Event, event_id, scope.actor)

    clip = Clip._base_manager.filter(event_id=event.pk).first()
    if clip is None or clip.clip_status == Clip.ClipStatus.UNAVAILABLE:
        raise Http404(
            "이 이벤트에는 영상 구간 참조가 없다"
            + (f" — {clip.unavailable_reason}" if clip is not None else ""))

    expires_at = timezone.now() + ttl
    exp = int(expires_at.timestamp())
    payload = _payload(event.pk, clip.object_key, clip.start_offset, clip.duration, exp)
    return PlaybackTicket(
        event_id=event.pk,
        object_key=clip.object_key,
        start_offset=clip.start_offset,
        duration=clip.duration,
        expires_at=expires_at,
        token=f"{exp}.{_sign(payload)}",
        playable=CLIP_EXTRACTION_READY,
        reason="" if CLIP_EXTRACTION_READY else CLIP_EXTRACTION_NOT_READY_REASON,
    )


def verify_ticket(*, token: str, event_id: int, object_key: str,
                  start_offset: float, duration: float) -> None:
    """서명·만료·**구간**을 함께 본다. 어긋나면 `Http404`.

    구간을 서명에 넣는 것이 규약 ③ 의 구현이다 — 티켓을 받은 사람이 시작점이나 길이를
    고쳐 다른 구간을 요구하면 서명이 깨진다. 구간 밖 바이트를 **요구할 수조차 없다.**
    """
    from django.http import Http404

    try:
        exp_str, signature = token.split(".", 1)
        exp = int(exp_str)
    except (ValueError, AttributeError) as exc:
        raise Http404("티켓 형식이 아니다") from exc

    if exp < int(timezone.now().timestamp()):
        raise Http404("티켓이 만료됐다 — 무기한 링크를 만들지 않는다 (D-306 규약 ②)")

    expected = _sign(_payload(event_id, object_key, start_offset, duration, exp))
    if not hmac.compare_digest(expected, signature):
        raise Http404(
            "티켓 서명이 맞지 않다 — 구간이 바뀌었거나 위조다 (D-306 규약 ③)")


def stream_window(*, token: str, event_id: int, object_key: str,
                  start_offset: float, duration: float):
    """구간의 바이트. **지금은 아무것도 돌려주지 않는다.**

    티켓을 먼저 검증하고, 그다음 잠금에서 멈춘다 — 순서가 중요하다. 잠금을 먼저 보면
    "티켓이 틀렸다" 와 "아직 못 준다" 가 같은 응답이 되고, 그러면 잠금이 풀린 날
    검증이 도는지 아무도 모른다.
    """
    verify_ticket(token=token, event_id=event_id, object_key=object_key,
                  start_offset=start_offset, duration=duration)
    if not CLIP_EXTRACTION_READY:
        raise NotImplementedError(
            f"구간 추출 미구현 — 계약 F-09 AC 대상. {CLIP_EXTRACTION_NOT_READY_REASON}")
    # 여기 아래는 CLIP_EXTRACTION_READY 를 True 로 올리는 사람이 채운다.
    raise NotImplementedError(
        "CLIP_EXTRACTION_READY 가 True 인데 _extract_window 구현이 없다 — "
        "상수만 올리고 구현을 안 올린 상태다")


def is_extraction_ready() -> bool:
    return CLIP_EXTRACTION_READY


__all__ = [
    "KERNEL_READY",
    "CLIP_EXTRACTION_READY",
    "CLIP_EXTRACTION_NOT_READY_REASON",
    "PRE_ROLL_SECONDS",
    "POST_ROLL_SECONDS",
    "TICKET_TTL",
    "PlaybackTicket",
    "reference_for_event",
    "issue_ticket",
    "verify_ticket",
    "stream_window",
    "is_extraction_ready",
]
