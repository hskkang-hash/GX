# -*- coding: utf-8 -*-
"""FWS-F1-01·02·11·13 — 근무 체크인·순찰 기록·내 실적·오프라인 재전송 (턴 AK 차선 N2).

왜 새 모델을 세우지 않았나 — `kernels/k1_event/field_reply.py` 판정을 그대로 따른다
-----------------------------------------------------------------------------------
체크인·순찰 트랙·순찰함 통과는 셋 다 **「일어난 일 한 줄」**이다(D-285 ②의 뜻과 같다) —
새 표 + 마이그레이션은 이번 턴 어느 차선도 공유하지 않는 파일을 만들고, 병합 충돌의
반경을 넓힌다. `logger.AuditLogs` 에 이미 있는 감사 한 줄로 충분하다(field_reply.py ·
apps/dsm/notify_prefs.py 의 push 구독이 같은 판단을 앞서 적어 두었다).

⚠ 좁히기를 표가 해 주지 못한다(감사 표는 §0.4 dj-core 소유라 테넌트 칼럼이 없다).
  그래서 **이 파일의 함수가** `user_id` 로 좁힌다 — `_rows_of` 가 유일한 문이다.

F1-13 오프라인 큐와 이 파일의 관계
-----------------------------------
산지에서 통신이 끊기면 화면(서비스워커)이 체크인·트랙 요청을 큐에 쌓았다가 복귀 시
다시 보낸다. 재전송이 **같은 요청을 두 번 세지 않으려면** 서버가 같은 의도를
알아봐야 한다 — 그 자리가 이미 있다: `common.idempotency.idempotent`(P-87,
`Idempotency-Key` 헤더). 이 파일이 그 장치를 새로 만들지 않는 이유는 두 벌을 두면
반드시 갈리기 때문이다(D-212) — `api.py` 가 그 데코레이터를 씌운다.
"""
from __future__ import annotations

from datetime import timedelta

from django.apps import apps
from django.utils import timezone

from common import audit_writer

LOGGER_NAME = "guardianx.fws.patrol"
TAG = "[FWS-PATROL]"
ACTION_CHECKIN = "patrol.checkin"
ACTION_TRACK_GPS = "patrol.track.gps"
ACTION_TRACK_CHECKPOINT = "patrol.track.checkpoint"

MAX_POST_CODE_CHARS = 40
ALLOWED_CHECKIN_METHODS = ("nfc", "gps")


class PatrolInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _rows_of(user_id: int, *, since=None, actions: tuple[str, ...] = ()):
    """이 **사람**의 순찰 감사 전건, 최신순. `user_id` 가 유일한 문지기다."""
    qs = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id)
    )
    if actions:
        qs = qs.filter(api_name__in=actions)
    if since is not None:
        qs = qs.filter(create_datetime__gte=since)
    return list(qs.order_by("-id")[:5000])


def _post_code(value: str) -> str:
    code = (value or "").strip()
    if not code:
        raise PatrolInputRejected(
            "초소 코드가 비었다 — 어느 초소인지 없이는 「근무 중」이 뜻을 갖지 못한다")
    if len(code) > MAX_POST_CODE_CHARS:
        raise PatrolInputRejected(
            f"초소 코드가 {len(code)}자다. 상한은 {MAX_POST_CODE_CHARS}자")
    return code


def checkin(*, scope, post_code: str, method: str,
           lat: float | None = None, lng: float | None = None) -> dict:
    """FWS-F1-01 — 근무 시작·초소 체크인. 응답이 곧 「초소 상태」다."""
    actor = scope.require_actor()
    code = _post_code(post_code)
    if method not in ALLOWED_CHECKIN_METHODS:
        raise PatrolInputRejected(
            f"method={method!r} 는 체크인 방식이 아니다. 허용: {ALLOWED_CHECKIN_METHODS}")
    now = timezone.now()
    location = {"lat": lat, "lng": lng} if (lat is not None and lng is not None) else None
    audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=ACTION_CHECKIN,
        outcome=audit_writer.ALLOWED,
        reason=f"초소 {code} 근무 시작({method})",
        after={"post_code": code, "method": method, "lat": lat, "lng": lng,
              "checked_in_at": now.isoformat()},
        api_name=ACTION_CHECKIN, api_method="POST")
    return {
        "post_code": code,
        "status": "on_duty",
        "method": method,
        "checked_in_at": now.isoformat(),
        "location": location,
    }


def track(*, scope, post_code: str, lat: float | None = None, lng: float | None = None,
         checkpoint_code: str = "") -> dict:
    """FWS-F1-02 — 순찰 경로 기록(GPS 트랙) · 전자순찰함 NFC 통과.

    한 요청은 **둘 중 하나**를 남긴다 — GPS 좌표 한 점, 또는 순찰함 통과 한 건.
    응답은 오늘 누적된 두 수를 함께 낸다(「트랙 1 · 순찰함 통과 N」— 명세서 §5.1
    FWS-F1-02 의 표시 그대로).
    """
    actor = scope.require_actor()
    code = _post_code(post_code)
    checkpoint = (checkpoint_code or "").strip()
    has_gps = lat is not None and lng is not None
    if not has_gps and not checkpoint:
        raise PatrolInputRejected(
            "GPS 좌표도 순찰함 코드도 없다 — 무엇을 지났는지 없이는 트랙이 아니다")

    now = timezone.now()
    if checkpoint:
        audit_writer.write(
            logger_name=LOGGER_NAME, tag=TAG, actor=actor,
            action=ACTION_TRACK_CHECKPOINT, outcome=audit_writer.ALLOWED,
            reason=f"초소 {code} 순찰함 {checkpoint} 통과",
            after={"post_code": code, "checkpoint_code": checkpoint,
                  "lat": lat, "lng": lng, "at": now.isoformat()},
            api_name=ACTION_TRACK_CHECKPOINT, api_method="POST")
    else:
        audit_writer.write(
            logger_name=LOGGER_NAME, tag=TAG, actor=actor,
            action=ACTION_TRACK_GPS, outcome=audit_writer.ALLOWED,
            reason=f"초소 {code} GPS 트랙 1점",
            after={"post_code": code, "lat": lat, "lng": lng, "at": now.isoformat()},
            api_name=ACTION_TRACK_GPS, api_method="POST")

    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    track_count = len(_rows_of(actor.pk, since=today_start,
                               actions=(ACTION_TRACK_GPS,)))
    checkpoint_count = len(_rows_of(actor.pk, since=today_start,
                                    actions=(ACTION_TRACK_CHECKPOINT,)))
    return {
        "post_code": code,
        "recorded_at": now.isoformat(),
        "track_count": track_count,
        "checkpoint_count": checkpoint_count,
    }


def mine(*, scope) -> dict:
    """FWS-F1-11 — 내 근무 기록·순찰 실적(일·주)."""
    actor = scope.require_actor()
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())

    def _counts(since):
        rows = _rows_of(actor.pk, since=since)
        out = {"checkins": 0, "tracks": 0, "checkpoints": 0}
        for row in rows:
            if row.api_name == ACTION_CHECKIN:
                out["checkins"] += 1
            elif row.api_name == ACTION_TRACK_GPS:
                out["tracks"] += 1
            elif row.api_name == ACTION_TRACK_CHECKPOINT:
                out["checkpoints"] += 1
        return out

    return {
        "today": _counts(today_start),
        "week": _counts(week_start),
        "as_of": now.isoformat(),
    }
