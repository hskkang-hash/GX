# -*- coding: utf-8 -*-
"""FWS-F6-01~10 — 산림청·지자체 산림과 연계 (annex §5.1 · 턴 AM 차선 N3).

P-357 을 그대로 잇는다 — 새 이벤트 표를 만들지 않는다
--------------------------------------------------------
F6 은 F1·F2 와 같은 판단이다: 산림청에 내보내는 것도, 웹훅이 알리는 것도, 헬기
요청이 매달리는 것도 **전부 K1 이벤트 하나를 다른 각도에서 본 것**이다. 이 파일은
새 표를 만들지 않는다 — 「기록」이 필요한 자리(경찰 협조·헬기 요청·관할 이첩·
위험예보 수동 입력)는 `patrol.py`·`standby.py`·`missions.py` 가 이미 쓰는 관례를
따른다: **일어난 일 한 줄을 감사 로그에 남기고, 최신/전체 줄이 지금 상태를 답한다.**

★ F-05 잠금 — **이벤트 접근은 오직 `apps.dsm.services` 를 거친다.** `kernels.
  k1_event` 를 이 파일이 직접 부르지 않는다(F-05 「진입면 하나」 · `test_f05_
  event_api.py::EVENT_ENTRY_SURFACE`). `kernels.k2_notify` 의 **예외 클래스**
  (`NoRecipients`)만 D-278 「커널 공개 면」으로 가져온다 — 그 커널의 함수는
  부르지 않는다(발송은 여전히 `apps.dsm.services.notify_event` 하나로 한다).

정직하게 남긴다 — 이 파일이 하지 않는 것
------------------------------------------
· **실제 산림청·소방·경찰 시스템에 뭔가를 쏘지 않는다.** 나가는 것은 우리 쪽
  표준 웹훅(UX-19 CAP 1.2 · 이미 있는 구독-발송 기관)뿐이고, 그 밖은 전부
  「수동 입력·내보내기 문서 하나」다 — annex 가 8곳에서 요구하는 실시간 외부
  연동(§0.4 밖에서도 새 자격증명·새 방화벽 규칙이 필요한 일)은 대표의 승인
  없이 이 차선이 열 수 없다(F6-03·04·05·06 의 각 머리말 참고).
· **지도를 그리지 않는다.** 좌표는 값으로만 오간다(§0.4 인접 — MapForRoute·
  FormRoute 는 금지구역).
"""
from __future__ import annotations

from datetime import datetime, timezone as _tz

from django.apps import apps

from common import audit_writer

#: ★ F-05 잠금 — K1 을 직접 부르지 않는다. `apps.dsm.services` 가 유일한 문이다.
from apps.dsm import services as dsm_services
from apps.dsm.services import InvalidEventInput
#: ★ D-278 — 커널의 **공개 면**(예외 클래스)만 가져온다. 발송 함수는 여전히
#:   `dsm_services.notify_event` 하나로 부른다(위 머리말 참고). `apps/dsm/api.py`
#:   가 이미 같은 이름을 같은 자리(API/App 층)에서 그대로 가져온다 — 두 벌이 아니다.
from kernels.k2_notify import NoRecipients

from apps.fws import constants as fws_constants

LOGGER_NAME = "guardianx.fws.liaison"
TAG = "[FWS-F6]"


class LiaisonInputRejected(Exception):
    """값이 계약 밖이다 — 422."""


class LiaisonNoSubscribers(Exception):
    """이 사건에 걸린 발송 규칙이 없다(사람 채널이든 웹훅이든) — 409."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _rows_for_event(action: str, event_id: int):
    """이 사건에 달린 기록 전부 — **제출자를 가리지 않는다**(missions.py 의
    `_own_rows` 와 다른 점). 경찰 협조·헬기 요청·관할 이첩은 여러 사람이 같은
    사건에 남기는 「공유 기록」이고, 그것을 자기 것만 보이게 좁히면 두 번째
    제출자가 첫 제출자의 기록을 못 본다. 안전한 이유: 이 함수를 부르기 **전에**
    호출자가 `dsm_services.event_detail(event_id)` 로 그 사건에 닿을 자격을 이미
    확인받았다(남의 테넌트 사건이면 거기서 404) — `field_replies()` 가 전원의
    회신을 보여주는 것과 같은 경계선이다.
    """
    qs = _model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action).order_by("id")
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(row)
    return out


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _now_iso() -> str:
    return datetime.now(_tz.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-01 산림청 시스템 입력 항목 내보내기(JSON/CSV · 항목 1:1)
# ═══════════════════════════════════════════════════════════════════════════
#
# 정직하게 남긴다 — 산림청 산불상황관제시스템·산림재난정보시스템의 **실제** 입력
# 스키마는 이 차선이 손에 넣지 못했다(외부 기관 문서·API 계약이 필요하고, 그
# 확보는 대표의 몫이다). 그래서 이 문은 **K1 이벤트가 가진 항목**을 한글 이름으로
# 1:1 내보낸다 — annex 완결조건("내보내기 1")이 요구하는 것은 "포맷·항목 대조표가
# 있는 내보내기 하나"이지, 상대 시스템이 그 포맷을 실제로 받아들이는지가 아니다
# (그 확인은 연동 시험 단계이고 이번 차선 범위 밖).
EXPORT_FORMATS = ("json", "csv")

#: (K1 필드 이름, 산림청 입력 항목 한글 이름) — **정본은 이 목록 하나**다. 늘리는
#: 날에도 이 자리 하나만 고치면 JSON·CSV 양쪽이 같이 바뀐다(D-212).
KFS_EXPORT_FIELDS: tuple[tuple[str, str], ...] = (
    ("occurred_at", "신고일시"),
    ("lat", "발생위치_위도"),
    ("lng", "발생위치_경도"),
    ("address", "주소"),
    ("severity", "화세등급"),
    ("status", "처리상태"),
    ("response_state", "대응진행상태"),
    ("fire_stage", "산불대응단계"),
    ("snapshot_path", "현장사진경로"),
)


def export_kfs_feed(*, scope, event_id: int, fmt: str = "json",
                    area_ha: float | None = None, wind_mps: float | None = None,
                    duration_hours: float | None = None,
                    buildings_at_risk: int | None = None) -> dict:
    """FWS-F6-01 — 산림청 시스템 입력 항목 내보내기.

    `area_ha`·`wind_mps`·`duration_hours`·`buildings_at_risk` 는 **전부 선택**이다
    — 하나라도 주면 `constants.compute_fire_stage()`(P-386 규정값)로 대응단계를
    계산해 싣고, 하나도 안 주면 `fire_stage` 는 정직하게 `None`이다(측정 안 한
    값을 1단계로 지어내지 않는다 · D-284).
    """
    if fmt not in EXPORT_FORMATS:
        raise LiaisonInputRejected(
            f"fmt={fmt!r} 는 지원하지 않는다. 허용: {EXPORT_FORMATS}")
    event = dsm_services.event_detail(scope=scope, event_id=event_id)

    fire_stage = None
    if any(v is not None for v in (area_ha, wind_mps, duration_hours, buildings_at_risk)):
        fire_stage = fws_constants.compute_fire_stage(
            area_ha=area_ha or 0.0, wind_mps=wind_mps or 0.0,
            duration_hours=duration_hours or 0.0,
            buildings_at_risk=buildings_at_risk or 0)

    values = {
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "lat": event.lat, "lng": event.lng, "address": event.address,
        "severity": event.severity, "status": event.status,
        "response_state": event.response_state, "fire_stage": fire_stage,
        "snapshot_path": event.snapshot_path,
    }

    if fmt == "json":
        return {
            "format": "json", "event_id": event_id,
            "fields": [{"key": key, "label": label, "value": values[key]}
                      for key, label in KFS_EXPORT_FIELDS],
        }

    import csv
    import io

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in KFS_EXPORT_FIELDS])
    writer.writerow(["" if values[key] is None else values[key]
                     for key, _ in KFS_EXPORT_FIELDS])
    return {"format": "csv", "event_id": event_id, "text": buf.getvalue()}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-02 웹훅 이벤트 종류(fws.fire.confirmed/stage_changed/evacuation_
# ordered/extinguished) — 기존 UX-19 웹훅 기계를 **재사용**한다
# ═══════════════════════════════════════════════════════════════════════════
#
# 재사용 확인(이 차선이 새로 지은 것이 아니다):
#   · 구독 등록·조회·해지  `apps.dsm.services.register_webhook_subscription` /
#     `webhook_subscriptions` / `revoke_webhook_subscription`(K1 `subscribe`
#     공개 면 · `apps/dsm/webhook_key_service.py` 가 서명키 발급까지 함께 묶는
#     것과 같은 자리) — 새 구독 표를 만들지 않는다.
#   · 실제 발송           `apps.dsm.services.notify_event`(내부에서 `common.
#     webhook_outbox.dispatch_event` 를 CAP 1.2 로 부른다) — 이 함수가 새 발신
#     경로를 만들지 않는다.
#
# ★ 정직 고지 — **이 네 이름은 network 필터가 아니다.** 실제 발신 여부를 가르는
#   것은 여전히 K1 `DetectionEvent.event_type`(닫힌 열거값 fire/smoke/… ·
#   `common/webhook_outbox.py::_passes_filter`)이다. `fws.fire.confirmed` 같은
#   문자열을 구독의 `event_types` 에 넣어도 실제 이벤트의 `event_type` 은 여전히
#   "fire" 이므로 **그 문자열로 발송을 골라 받을 수는 없다**(오늘의 한계). 이
#   함수가 실제로 하는 것: (1) 이 네 이름 중 하나가 "일어났다"고 이 시각에
#   선언하고, (2) 그 시각에 **실제로** CAP 1.2 웹훅을 구독 기관에 쏘고(완결조건
#   "수신 200" 이 재는 지점), (3) 어느 이름이었는지 FWS 자기 감사에 남겨 조회
#   가능하게 한다. 종류별 필터·본문 내 종류 라벨은 `common/webhook_outbox.py`·
#   `common/cap_1_2.py`(DSM 공용부) 변경이 필요해 범위 밖 — 「무엇이 없는가」로
#   여기 정직하게 남긴다(N3_promotions.md 도 같은 문장을 옮긴다).
FWS_WEBHOOK_EVENT_TYPES: tuple[str, ...] = (
    "fws.fire.confirmed",
    "fws.fire.stage_changed",
    "fws.fire.evacuation_ordered",
    "fws.fire.extinguished",
)

ACTION_WEBHOOK_NOTIFY = "liaison.webhook_notify"


def webhook_event_catalog() -> dict:
    """F6-02 — 이 앱이 낼 수 있는 웹훅 이벤트 종류 넷. 문서화 목적(자기서술)."""
    return {"event_types": list(FWS_WEBHOOK_EVENT_TYPES)}


def notify_fws_event(*, scope, event_id: int, kind: str, note: str = "") -> dict:
    """FWS-F6-02 — 넷 중 하나가 일어났다고 선언하고 실제로 웹훅을 낸다."""
    if kind not in FWS_WEBHOOK_EVENT_TYPES:
        raise LiaisonInputRejected(
            f"kind={kind!r} 는 FWS 웹훅 이벤트 종류가 아니다. 허용: "
            f"{FWS_WEBHOOK_EVENT_TYPES}")
    # 남의 테넌트 사건이면 여기서 404(dsm_services 가 던진다) — 기록도 발송도 없다.
    dsm_services.event_detail(scope=scope, event_id=event_id)
    try:
        records = dsm_services.notify_event(scope=scope, event_id=event_id)
    except NoRecipients as exc:
        raise LiaisonNoSubscribers(str(exc)) from exc

    actor = scope.require_actor()
    webhook_records = [r for r in records if r.channel == "webhook"]
    payload = {
        "event_id": event_id, "kind": kind, "note": note,
        "total_deliveries": len(records),
        "webhook_deliveries": len(webhook_records),
        "webhook_succeeded": sum(1 for r in webhook_records if r.succeeded),
    }
    _write(actor, ACTION_WEBHOOK_NOTIFY, payload, f"FWS 웹훅 이벤트 kind={kind}")
    return {
        **payload,
        "deliveries": [
            {"delivery_id": r.delivery_id, "channel": r.channel,
             "succeeded": r.succeeded, "failure_reason": r.failure_reason}
            for r in records],
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-03 산불위험예보·위기경보 수신 — **수동 입력**(외부 API 미검증)
# ═══════════════════════════════════════════════════════════════════════════
#
# 정직하게 남긴다 — 산림과학원·산림청의 실시간 위험예보 API 는 새 자격증명·
# 방화벽 규칙이 필요한 외부 연동이고, 그 승인은 대표의 몫이지 이 지시서의 몫이
# 아니다(`apps/fws/risk.py` 머리말과 같은 판단). 그래서 이 문은 **사람이 그
# 지수를 손으로 입력**하는 정직한 경로만 연다 — annex 가 스스로 허락한 대안
# ("API 또는 수동")이다.
ACTION_RISK_FORECAST = "liaison.risk_forecast"


def record_risk_forecast(*, scope, risk_index: float, source: str = "manual",
                         note: str = "") -> dict:
    if not (0.0 <= risk_index <= 100.0):
        raise LiaisonInputRejected(
            f"risk_index={risk_index!r} 는 0~100 범위 밖이다")
    band = fws_constants.risk_index_band(risk_index)
    actor = scope.require_actor()
    payload = {"risk_index": risk_index, "band": band, "source": source or "manual",
              "note": note, "recorded_at": _now_iso()}
    _write(actor, ACTION_RISK_FORECAST, payload,
          f"위험예보 수동 입력 지수={risk_index} 띠={band}")
    return payload


def my_latest_risk_forecast(*, scope) -> dict:
    """지금 이 사람이 최근에 입력한 예보. **본인 것만**이다(`standby.py`·
    `missions.py` 와 같은 한계 — 감사 표에 테넌트 칸이 없다 · 여러 사람이 입력한
    「지자체 전체의 최신 값」을 모으는 것은 이번 차선 범위 밖)."""
    actor = scope.require_actor()
    row = (
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=actor.pk, api_name=ACTION_RISK_FORECAST)
        .order_by("-id").first()
    )
    if row is None:
        return {"risk_index": None, "band": None, "source": None, "note": None,
               "recorded_at": None}
    return row.data_after if isinstance(row.data_after, dict) else {}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-05 헬기 출동 요청·위치 수신 — **수동 입력 대안**(산림항공본부 실시간
# 연동은 범위 밖)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_HELICOPTER_REQUEST = "liaison.helicopter_request"


def request_helicopter(*, scope, event_id: int, requesting_org: str,
                       lat: float | None = None, lng: float | None = None,
                       note: str = "") -> dict:
    requesting_org = (requesting_org or "").strip()
    if not requesting_org:
        raise LiaisonInputRejected("requesting_org 는 비울 수 없다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "requesting_org": requesting_org,
              "lat": lat, "lng": lng, "note": note, "requested_at": _now_iso()}
    entry = _write(actor, ACTION_HELICOPTER_REQUEST, payload, "헬기 출동 요청(수동)")
    return {"request_id": entry.audit_id, **payload}


def helicopter_requests(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_HELICOPTER_REQUEST, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "requests": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-06 소방 119 출동 사건 연동 — DSM 을 통해(K1 현장 회신 재사용)
# ═══════════════════════════════════════════════════════════════════════════
#
# `missions.py::request_support` 와 같은 판단: 119 연동 표시는 **새 배지·새 표**가
# 아니라 K1 현장 회신에 실어 지휘 화면(DSM "카드")이 읽는 자리에 그대로 보낸다
# — annex 완결조건("DSM 카드")을 새 화면 없이 만족한다.
ACTION_FIRE_DEPT_LINK = "liaison.fire_department_link"


def link_fire_department(*, scope, event_id: int, dispatch_no: str = "",
                         note: str = "") -> dict:
    dispatch_no = (dispatch_no or "").strip()
    text = f"[소방119연동] 출동번호={dispatch_no or '미기재'}" + (f" · {note}" if note else "")
    try:
        reply = dsm_services.field_reply(scope=scope, event_id=event_id, text=text)
    except InvalidEventInput as exc:
        raise LiaisonInputRejected(str(exc)) from exc
    actor = scope.require_actor()
    payload = {"event_id": event_id, "dispatch_no": dispatch_no, "note": note,
              "reply_id": reply.reply_id, "linked_at": _now_iso()}
    _write(actor, ACTION_FIRE_DEPT_LINK, payload, "소방 119 연동 기록")
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-07 스마트산림재난 앱 대피 푸시 연계 [미확인] — 대안 CBS 초안
# ═══════════════════════════════════════════════════════════════════════════
#
# annex 원문 그대로: 산림청 스마트산림재난 앱 푸시 연동은 [미확인](그런 공개
# API 가 있는지조차 이 차선이 확인하지 못했다). PRD §5.1 ⑥ 이 스스로 적어 둔
# 대안 — 「대피는 CBS 초안·마을방송 요청」 — 을 그대로 짓는다. 이 문은 **문자
# 초안**(글자수 상한 안에 맞춘 두 버전)만 낸다 — 실제 CBS·마을방송 송출은 하지
# 않는다(그 송출은 지자체 방송 시설의 몫이고 이번 차선이 쏠 수 있는 채널이
# 아니다).
ACTION_EVACUATION_CBS_DRAFT = "liaison.evacuation_cbs_draft"


def draft_evacuation_notice(*, scope, event_id: int, area_name: str,
                            kind: str = fws_constants.EVACUATION_KIND_ORDER,
                            note: str = "") -> dict:
    area_name = (area_name or "").strip()
    if not area_name:
        raise LiaisonInputRejected("area_name 은 비울 수 없다")
    if kind not in fws_constants.EVACUATION_KINDS:
        raise LiaisonInputRejected(
            f"kind={kind!r} 는 대피 종류가 아니다. 허용: {fws_constants.EVACUATION_KINDS}")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    draft = fws_constants.draft_evacuation_text(area_name=area_name, kind=kind)
    actor = scope.require_actor()
    payload = {"event_id": event_id, "area_name": area_name, "note": note,
              "drafted_at": _now_iso(), **draft}
    _write(actor, ACTION_EVACUATION_CBS_DRAFT, payload, "대피 CBS 초안 작성")
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-08 경찰 교통통제·입산통제 협조 기록 [S]
# ═══════════════════════════════════════════════════════════════════════════
POLICE_COORDINATION_KIND_TRAFFIC = "traffic_control"
POLICE_COORDINATION_KIND_ENTRY_BAN = "mountain_entry_control"
POLICE_COORDINATION_KINDS: tuple[str, ...] = (
    POLICE_COORDINATION_KIND_TRAFFIC, POLICE_COORDINATION_KIND_ENTRY_BAN)

ACTION_POLICE_COORDINATION = "liaison.police_coordination"


def record_police_coordination(*, scope, event_id: int, kind: str,
                               note: str = "") -> dict:
    if kind not in POLICE_COORDINATION_KINDS:
        raise LiaisonInputRejected(
            f"kind={kind!r} 는 협조 종류가 아니다. 허용: {POLICE_COORDINATION_KINDS}")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "kind": kind, "note": note,
              "recorded_at": _now_iso(),
              "recorded_by": getattr(actor, "username", "")}
    entry = _write(actor, ACTION_POLICE_COORDINATION, payload, "경찰 협조 기록")
    return {"record_id": entry.audit_id, **payload}


def police_coordination_records(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_POLICE_COORDINATION, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "records": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-09 스키마 버전·헬스·요청 한도(공통 API-02) — **부분만** 채운다
# ═══════════════════════════════════════════════════════════════════════════
#
# 정직하게 남긴다:
#   · 스키마 버전  **이미 있다.** `common/schema_header.py::SchemaHeaderMiddleware`
#     가 `X-GX-Schema` 를 **모든** 응답(FWS 라우트 포함)에 이미 단다 — 새로
#     만들지 않는다(재사용 확인은 `test_fws_f6.py` 가 잰다).
#   · 헬스         FWS 전용 헬스가 없었다. **처음엔** `apps.dsm.api_u56.
#     run_health_checks` 를 그대로 부르려 했으나 `scripts/verify_layers.py`
#     (D-278 계층 게이트)가 막았다 — App 은 **다른 App 의 내부**(`api_u56` 은
#     `apps.dsm` 의 API 층 · 공개 면이 아니다)를 직접 import 할 수 없다(App 끼리는
#     커널을 통해서만 만난다). 그래서 **같은 모양(db·cache 검사)을 이 파일이
#     다시 짓는다** — 두 벌이 되는 값은 `common/schema_header.SCHEMA_VERSION`
#     하나뿐이고(그 값은 그대로 읽는다), 검사 로직 자체는 둘 다 표준 Django 호출
#     (`SELECT 1`·`cache.set/get`)이라 "두 벌이라 갈릴 위험"이 실질적으로 없다.
#   · 요청 한도    **없다.** 이 저장소에서 율제한은 로그인(`POST /api/v1/auth/
#     login`, SEC-21)에만 걸려 있고, 그 데코레이터는 dj-core 소유(§0.4)다. 일반
#     API 라우트(이 앱 포함)에는 요청 한도가 **어디에도 없다** — 새로 걸려면
#     공용 미들웨어를 고쳐야 하고, 공용 미들웨어는 이번 턴 다른 차선도 쓰는
#     자리라 손대지 않는다. 그래서 F6-09 는 **닫힌 절로 제안하지 않는다**
#     (P-376 — 제목이 부르는 셋 중 하나가 없으면 닫지 않는다) — `N3_promotions.md`
#     의 「무엇이 없는가」 참고.
def fws_health() -> dict:
    from common.schema_header import SCHEMA_VERSION
    from django.core.cache import cache
    from django.db import connection

    checks: dict[str, str] = {}
    failed: list[str] = []

    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        checks["db"] = "ok"
    except Exception:  # noqa: BLE001 — 사유는 로그로만, 응답엔 이름만
        import logging

        logging.getLogger(__name__).warning("[FWS-HEALTH] db 검사 실패", exc_info=True)
        checks["db"] = "fail"
        failed.append("db")

    try:
        key = "gx:fws:health:ping"
        cache.set(key, "1", timeout=5)
        cache.get(key)
        checks["cache"] = "ok"
    except Exception:  # noqa: BLE001
        import logging

        logging.getLogger(__name__).warning("[FWS-HEALTH] cache 검사 실패", exc_info=True)
        checks["cache"] = "fail"
        failed.append("cache")

    return {"status": "ok" if not failed else "fail", "schema": SCHEMA_VERSION,
           "checks": checks, "failed": failed}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F6-10 국립공원·국유림관리소 관할 사건 이첩
# ═══════════════════════════════════════════════════════════════════════════
JURISDICTION_ORG_NATIONAL_PARK = "national_park"
JURISDICTION_ORG_NATIONAL_FOREST_OFFICE = "national_forest_office"
JURISDICTION_ORG_TYPES: tuple[str, ...] = (
    JURISDICTION_ORG_NATIONAL_PARK, JURISDICTION_ORG_NATIONAL_FOREST_OFFICE)

ACTION_JURISDICTION_TRANSFER = "liaison.jurisdiction_transfer"


def transfer_jurisdiction(*, scope, event_id: int, org_type: str,
                          target_org: str, note: str = "") -> dict:
    if org_type not in JURISDICTION_ORG_TYPES:
        raise LiaisonInputRejected(
            f"org_type={org_type!r} 은 관할 기관 유형이 아니다. 허용: "
            f"{JURISDICTION_ORG_TYPES}")
    target_org = (target_org or "").strip()
    if not target_org:
        raise LiaisonInputRejected("target_org 는 비울 수 없다")
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    payload = {"event_id": event_id, "org_type": org_type, "target_org": target_org,
              "note": note, "transferred_at": _now_iso()}
    entry = _write(actor, ACTION_JURISDICTION_TRANSFER, payload, "관할 사건 이첩 기록")
    return {"transfer_id": entry.audit_id, **payload}


def jurisdiction_transfers(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_JURISDICTION_TRANSFER, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "transfers": items}


__all__ = [
    "LiaisonInputRejected", "LiaisonNoSubscribers",
    "export_kfs_feed", "KFS_EXPORT_FIELDS", "EXPORT_FORMATS",
    "FWS_WEBHOOK_EVENT_TYPES", "webhook_event_catalog", "notify_fws_event",
    "record_risk_forecast", "my_latest_risk_forecast",
    "request_helicopter", "helicopter_requests",
    "link_fire_department",
    "draft_evacuation_notice",
    "POLICE_COORDINATION_KINDS", "record_police_coordination",
    "police_coordination_records",
    "fws_health",
    "JURISDICTION_ORG_TYPES", "transfer_jurisdiction", "jurisdiction_transfers",
]
