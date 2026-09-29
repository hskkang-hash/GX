# -*- coding: utf-8 -*-
"""FWS-F3-11~20 — 산림과 담당 잔여(대피·상황보고·통계·오탐률·단속·훈련·온보딩)
(WO-GX-20260929-17 §5 P-397 · 턴 AN 차선 N3).

P-397 을 그대로 잇는다 — F1·F2·F5·F6 이 이미 연 문을 다시 열지 않는다
------------------------------------------------------------------------
이 파일은 새 표를 세우지 않는다(`patrol.py`·`standby.py`·`equipment.py` 와 같은
판단 — 감사 로그 한 줄이 정본이다, D-285 ②). 사건에 관한 것은 전부
`apps.dsm.services` 하나를 거친다(F-05 잠금 — `kernels.k1_event` 를 이 파일이
직접 부르지 않는다). 대피 문안은 `apps/fws/integration.py::draft_evacuation_
notice`(F6-07)를 그대로 부른다 — 글자수 상한·CBS 문안을 다시 짓지 않는다
(D-212). 훈련 시나리오는 `apps/fws/training.py`(F2-13)와 같은 판단으로
`dsm_services.set_drill_mode`/`drill_state`/`drill_report` 를 그대로 쓴다(DSM
훈련 스위치가 정본 — 새 스위치를 만들지 않는다).

정직하게 남긴다 — 무엇을 다시 재지 않는가
--------------------------------------------
· **골든타임 준수율**(annex §4.3 「헬기 투하·지상 도달 30분」)은 그 **도달
  시각을 이 앱이 갖고 있지 않다** — 그 시각은 `stream_monitors.services.
  response_clock` 안에 있고, 이 앱이 거치는 공개 문(`apps.dsm.services.
  response_latency`)은 p50/p95 **분포**만 내지 사건별 원값을 안 낸다(D-301 —
  분모를 감추지 않는 설계이지, 준수율 계산기가 아니다). 그래서 이 파일은
  **확인 회신 30분 이내 비율**(K1 이 이미 내주는 `occurred_at`→`reviewed_at`)로
  근사하고, 그 근사임을 응답의 `golden_time_note` 에 그대로 적는다(D-284 —
  지어내지 않고 무엇을 쟀는지 밝힌다).
· **계도·단속 통계**·**입산통제구역**은 `patrol.py`·`standby.py`·`equipment.py`
  와 같은 한계다 — 감사 표(`logger.AuditLogs`)에 테넌트 칸이 없어(§0.4 dj-core
  소유) **이 사람이 남긴 기록만** 센다. 조직 전체 집계는 이번 차선 범위 밖 —
  다른 F1/F2 모듈이 이미 같은 경계에 멈춰 선 자리와 같다.
· **원인 분류**(입산자실화·소각·담뱃불·건축물화재·기타)는 annex FF-7 원문
  그대로다(§6 FF-7) — 지어내지 않는다.
"""
from __future__ import annotations

import re
from collections import Counter
from datetime import datetime

from django.apps import apps
from django.utils import timezone

from common import audit_writer

from apps.dsm import services as dsm_services
from apps.fws import constants as fws_constants
from apps.fws import integration as fws_integration
from apps.fws import verification as fws_verification

LOGGER_NAME = "guardianx.fws.office2"
TAG = "[FWS-F3B]"


class Office2InputRejected(Exception):
    """값이 계약 밖이다 — 422."""


def _model():
    return apps.get_model("logger", "AuditLogs")


def _now():
    return timezone.now()


def _now_iso() -> str:
    return _now().isoformat()


def _write(actor, action: str, payload: dict, reason: str):
    return audit_writer.write(
        logger_name=LOGGER_NAME, tag=TAG, actor=actor, action=action,
        outcome=audit_writer.ALLOWED, reason=reason, after=payload,
        api_name=action, api_method="POST")


def _rows_for_event(action: str, event_id: int):
    """이 사건에 달린 기록 전부 — `integration.py::_rows_for_event` 와 같은 판단
    (여러 사람이 같은 사건에 남기는 공유 기록 · 부르는 쪽이 **먼저**
    `dsm_services.event_detail` 로 이 사건에 닿을 자격을 확인받은 뒤에만 쓴다 —
    남의 테넌트 사건이면 거기서 404 이고, 여기까지 오지 않는다)."""
    qs = _model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action).order_by("id")
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") == event_id:
            out.append(row)
    return out


def _rows_for_events(action: str, event_ids: set):
    """`_rows_for_event` 의 여러-사건 판(F3-16 통계 전용). 부르는 쪽이 **먼저**
    `dsm_services.recent_events`(테넌트로 이미 좁힌 결과)에서 `event_ids` 를
    만들어야 한다 — 그 집합 밖의 사건 id 는 여기서 걸러진다."""
    if not event_ids:
        return []
    qs = _model()._base_manager.filter(
        logger_name=LOGGER_NAME, api_name=action).order_by("id")
    out = []
    for row in qs:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("event_id") in event_ids:
            out.append(row)
    return out


def _rows_of(user_id: int, action: str):
    """이 **사람**의 감사 전건, 최신순 — `patrol.py::_rows_of` 와 같은 문지기."""
    return list(
        _model()._base_manager
        .filter(logger_name=LOGGER_NAME, user_id=user_id, api_name=action)
        .order_by("-id")[:2000])


def _parse_dt(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-11 대피 초안 — F6-07(`integration.draft_evacuation_notice`) 문 재사용
# ═══════════════════════════════════════════════════════════════════════════
STATUS_PENDING_F4_APPROVAL = "pending_f4_approval"
ACTION_EVAC_PLAN_DRAFT = "office2.evacuation.plan_draft"
MAX_VILLAGES = 20


def draft_evacuation_plan(*, scope, event_id: int, villages: list,
                          kind: str = fws_constants.EVACUATION_KIND_ORDER,
                          note: str = "") -> dict:
    """FWS-F3-11 — 대피 초안(대상 마을·대피소·문안 자동) → F4 승인 대기.

    마을마다 F6-07 문을 그대로 불러 CBS 90/157자 문안을 짓는다(`fws_constants.
    draft_evacuation_text` 를 다시 부르지 않는다 — D-212). 이 함수가 새로
    더하는 것은 **마을 목록을 하나의 계획으로 묶어 F4 승인 대기 상태로 남기는
    일**뿐이다."""
    if not isinstance(villages, list) or not villages:
        raise Office2InputRejected(
            "villages 가 비었다 — 대상 마을 없이는 대피 초안이 뜻을 갖지 못한다")
    if len(villages) > MAX_VILLAGES:
        raise Office2InputRejected(
            f"villages 가 {len(villages)}곳이다. 상한은 {MAX_VILLAGES}곳")

    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트(테넌트)

    drafted = []
    for entry in villages:
        if not isinstance(entry, dict):
            raise Office2InputRejected(
                "villages 의 각 항목은 {village, shelter} 모양이어야 한다")
        village = (entry.get("village") or "").strip()
        shelter = (entry.get("shelter") or "").strip()
        if not village:
            raise Office2InputRejected("village(마을 이름)가 비었다")
        if not shelter:
            raise Office2InputRejected("shelter(대피소)가 비었다")
        try:
            draft = fws_integration.draft_evacuation_notice(
                scope=scope, event_id=event_id, area_name=village, kind=kind,
                note=(f"대피소: {shelter}" + (f" · {note}" if note else "")))
        except fws_integration.LiaisonInputRejected as exc:
            raise Office2InputRejected(str(exc)) from exc
        drafted.append({"village": village, "shelter": shelter, **draft})

    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "kind": kind, "status": STATUS_PENDING_F4_APPROVAL,
        "villages": [{"village": d["village"], "shelter": d["shelter"]}
                    for d in drafted],
        "drafted_at": _now_iso(),
    }
    _write(actor, ACTION_EVAC_PLAN_DRAFT, payload,
          f"대피 계획 초안 · 사건{event_id} · 마을 {len(drafted)}곳 · F4 승인 대기")
    return {**payload, "drafts": drafted}


def _latest_plan(event_id: int):
    rows = _rows_for_event(ACTION_EVAC_PLAN_DRAFT, event_id)
    if not rows:
        return None
    return rows[-1].data_after


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-12 대피 이행 확인(마을별 완료·잔류자·요양시설)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_EVAC_PROGRESS = "office2.evacuation.progress"
MAX_PROGRESS_NOTE_CHARS = 300


def record_evacuation_progress(*, scope, event_id: int, village: str,
                               completed: bool, remaining_residents: int = 0,
                               care_facility_cleared: bool | None = None,
                               note: str = "") -> dict:
    """FWS-F3-12 — 대피 이행 확인 한 건(마을·완료 여부·잔류자·요양시설)."""
    village = (village or "").strip()
    if not village:
        raise Office2InputRejected("village 가 비었다")
    if remaining_residents < 0:
        raise Office2InputRejected(
            f"remaining_residents={remaining_residents} 는 음수일 수 없다")
    note = (note or "").strip()
    if len(note) > MAX_PROGRESS_NOTE_CHARS:
        raise Office2InputRejected(
            f"note 가 {len(note)}자다. 상한은 {MAX_PROGRESS_NOTE_CHARS}자")

    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트

    actor = scope.require_actor()
    payload = {
        "event_id": event_id, "village": village, "completed": bool(completed),
        "remaining_residents": remaining_residents,
        "care_facility_cleared": care_facility_cleared,
        "note": note, "recorded_at": _now_iso(),
        "recorded_by": getattr(actor, "username", ""),
    }
    _write(actor, ACTION_EVAC_PROGRESS, payload,
          f"대피 이행 확인 · 사건{event_id} · {village} · 완료={completed}")
    return payload


def evacuation_status(*, scope, event_id: int) -> dict:
    """FWS-F3-12 — 마을별 이행 % · 잔류자 · 요양시설 처리."""
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트

    plan = _latest_plan(event_id)
    plan_villages = [v["village"] for v in plan["villages"]] if plan else []

    latest_progress: dict = {}
    for row in _rows_for_event(ACTION_EVAC_PROGRESS, event_id):
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        village = payload.get("village")
        if village:
            latest_progress[village] = payload  # 뒤 행(시간순)이 앞 행을 덮는다

    all_villages = list(dict.fromkeys(plan_villages + list(latest_progress.keys())))
    rows_out = []
    completed_count = 0
    remaining_total = 0
    remaining_measured = False
    care_open_count = 0
    for village in all_villages:
        p = latest_progress.get(village)
        completed = bool(p["completed"]) if p else False
        remaining = p.get("remaining_residents") if p else None
        cleared = p.get("care_facility_cleared") if p else None
        if completed:
            completed_count += 1
        if remaining is not None:
            remaining_total += remaining
            remaining_measured = True
        if cleared is False:
            care_open_count += 1
        rows_out.append({
            "village": village, "completed": completed,
            "remaining_residents": remaining, "care_facility_cleared": cleared,
            "recorded_at": p.get("recorded_at") if p else None,
        })

    total = len(all_villages)
    percent = round(completed_count / total * 100, 1) if total else None
    return {
        "event_id": event_id, "plan_status": plan["status"] if plan else None,
        "villages": rows_out, "total_villages": total,
        "completed_villages": completed_count, "percent_complete": percent,
        "remaining_residents_total": remaining_total if remaining_measured else None,
        "care_facilities_open": care_open_count,
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-13 매시간 상황보고 초안 → 산림청 입력 항목 내보내기(F6-01 문 재사용)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_HOURLY_DRAFT = "office2.hourly_report.draft"
MAX_HOURLY_NOTE_CHARS = 500


def draft_hourly_report(*, scope, event_id: int,
                        personnel_count: int | None = None,
                        equipment_note: str = "",
                        casualties_count: int | None = None,
                        facility_note: str = "", weather_note: str = "") -> dict:
    """FWS-F3-13 — 매시간 상황보고 초안(발생·위치·면적·진화 현황·인력/장비·인명·
    시설·기상) → 승인 → 산림청 입력 항목 내보내기.

    내보내기는 `integration.export_kfs_feed`(F6-01)를 그대로 부른다 — 항목
    대조표를 두 벌로 만들지 않는다(D-212)."""
    for label, value in (("equipment_note", equipment_note),
                        ("facility_note", facility_note),
                        ("weather_note", weather_note)):
        if len(value or "") > MAX_HOURLY_NOTE_CHARS:
            raise Office2InputRejected(
                f"{label} 가 {len(value)}자다. 상한은 {MAX_HOURLY_NOTE_CHARS}자")

    event = dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    now = _now()
    payload = {
        "event_id": event_id, "hour": now.strftime("%Y-%m-%dT%H:00"),
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else None,
        "lat": event.lat, "lng": event.lng, "address": event.address,
        "response_state": event.response_state, "severity": event.severity,
        "personnel_count": personnel_count, "equipment_note": equipment_note,
        "casualties_count": casualties_count, "facility_note": facility_note,
        "weather_note": weather_note, "drafted_at": now.isoformat(),
    }
    _write(actor, ACTION_HOURLY_DRAFT, payload,
          f"매시간 상황보고 초안 · 사건{event_id} · {payload['hour']}")

    export = fws_integration.export_kfs_feed(scope=scope, event_id=event_id, fmt="json")
    return {**payload, "kfs_export": export}


def hourly_reports(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_HOURLY_DRAFT, event_id)
    items = [r.data_after for r in rows if isinstance(r.data_after, dict)]
    return {"event_id": event_id, "count": len(items), "reports": items}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-14 진화완료 보고·산불 통계 항목(산불정보ID·원인·면적·문자전송 여부·
# 일출몰) — 항목 1:1
# ═══════════════════════════════════════════════════════════════════════════
#: 원인 분류 5택 — annex §6 FF-7 원문 그대로(입산자 실화·소각·담뱃불·건축물
#: 화재·기타). 여기가 정본이다 — 지어내지 않는다.
FIRE_CAUSE_HIKER = "입산자실화"
FIRE_CAUSE_BURNING = "소각"
FIRE_CAUSE_CIGARETTE = "담뱃불"
FIRE_CAUSE_BUILDING = "건축물화재"
FIRE_CAUSE_OTHER = "기타"
FIRE_CAUSES: tuple = (FIRE_CAUSE_HIKER, FIRE_CAUSE_BURNING, FIRE_CAUSE_CIGARETTE,
                     FIRE_CAUSE_BUILDING, FIRE_CAUSE_OTHER)

ACTION_FINAL_REPORT = "office2.final_report.record"

#: (K 필드 이름, 한글 이름) — `integration.KFS_EXPORT_FIELDS` 와 같은 형(정본은
#: 이 목록 하나 · D-212).
FINAL_REPORT_FIELDS: tuple = (
    ("fire_info_id", "산불정보ID"), ("cause", "원인"), ("area_ha", "면적"),
    ("sms_sent", "문자전송 여부"), ("sunrise", "일출"), ("sunset", "일몰"),
)


def record_final_report(*, scope, event_id: int, cause: str, area_ha: float,
                        sms_sent: bool, sunrise: str = "", sunset: str = "",
                        fire_info_id: str = "") -> dict:
    """FWS-F3-14 — 진화완료 보고·산불 통계 항목. 완결조건은 「항목 1:1」이다."""
    if cause not in FIRE_CAUSES:
        raise Office2InputRejected(
            f"cause={cause!r} 는 원인 분류가 아니다. 허용: {FIRE_CAUSES}")
    if area_ha < 0:
        raise Office2InputRejected(f"area_ha={area_ha!r} 는 음수일 수 없다")

    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    actor = scope.require_actor()
    values = {
        "fire_info_id": (fire_info_id or "").strip() or f"FWS-{event_id}",
        "cause": cause, "area_ha": area_ha, "sms_sent": bool(sms_sent),
        "sunrise": sunrise or None, "sunset": sunset or None,
    }
    payload = {"event_id": event_id, **values, "recorded_at": _now_iso()}
    _write(actor, ACTION_FINAL_REPORT, payload,
          f"진화완료 보고 · 사건{event_id} · 원인={cause}")
    return {
        "event_id": event_id,
        "items": [{"key": k, "label": label, "value": values[k]}
                 for k, label in FINAL_REPORT_FIELDS],
        **payload,
    }


def final_report(*, scope, event_id: int) -> dict:
    dsm_services.event_detail(scope=scope, event_id=event_id)  # 404 게이트
    rows = _rows_for_event(ACTION_FINAL_REPORT, event_id)
    if not rows:
        return {
            "event_id": event_id, "recorded": False,
            "items": [{"key": k, "label": label, "value": None}
                     for k, label in FINAL_REPORT_FIELDS],
        }
    payload = rows[-1].data_after
    return {
        "event_id": event_id, "recorded": True,
        "items": [{"key": k, "label": label, "value": payload.get(k)}
                 for k, label in FINAL_REPORT_FIELDS],
        "recorded_at": payload.get("recorded_at"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-16 통계 — 발생·면적·원인·시간대·구역·오인율·확인 시간·골든타임 준수율
# ═══════════════════════════════════════════════════════════════════════════
#: 30분 — annex §4.3 「헬기 투하(골든타임)」·「지상 도달」 목표(신고 접수 기준).
GOLDEN_TIME_THRESHOLD_SEC = 1800


def fire_stats(*, scope, since: str = "", until: str = "") -> dict:
    """FWS-F3-16 — 통계 표. `dsm_services.recent_events`(K1 · F-05 문 하나)로
    테넌트 안 사건을 모으고, 면적·원인은 F3-14 최종보고 기록에서 되짚는다."""
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)
    rows = list(dsm_services.recent_events(
        scope=scope, since=since_dt, until=until_dt, limit=2000))

    by_hour: Counter = Counter()
    by_zone: Counter = Counter()
    reviewed = []
    false_alarm = 0
    verify_seconds: list = []
    for r in rows:
        if r.occurred_at:
            by_hour[r.occurred_at.hour] += 1
        by_zone[r.stream_monitor_name or "(미상)"] += 1
        if r.verdict is not None:
            reviewed.append(r)
            if r.verdict == "rejected":
                false_alarm += 1
        if r.occurred_at and r.reviewed_at:
            verify_seconds.append((r.reviewed_at - r.occurred_at).total_seconds())

    false_alarm_rate = (round(false_alarm / len(reviewed) * 100, 1)
                        if reviewed else None)
    verify_avg = (round(sum(verify_seconds) / len(verify_seconds), 1)
                 if verify_seconds else None)
    golden_compliant = sum(1 for s in verify_seconds if s <= GOLDEN_TIME_THRESHOLD_SEC)
    golden_rate = (round(golden_compliant / len(verify_seconds) * 100, 1)
                  if verify_seconds else None)

    event_ids = {r.event_id for r in rows}
    latest_final: dict = {}
    for row in _rows_for_events(ACTION_FINAL_REPORT, event_ids):
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        eid = payload.get("event_id")
        if eid is not None:
            latest_final[eid] = payload  # 뒤 행(시간순)이 앞 행을 덮는다
    area_total = sum((v.get("area_ha") or 0) for v in latest_final.values())
    cause_breakdown = Counter(
        v.get("cause") for v in latest_final.values() if v.get("cause"))

    return {
        "since": since or None, "until": until or None,
        "occurrence_count": len(rows),
        "by_hour": dict(sorted(by_hour.items())),
        "by_zone": dict(by_zone),
        "area_ha_total": round(area_total, 2) if latest_final else None,
        "area_measured_events": len(latest_final),
        "cause_breakdown": dict(cause_breakdown),
        "false_alarm_rate_pct": false_alarm_rate,
        "false_alarm_reviewed_n": len(reviewed),
        "verification_seconds_avg": verify_avg,
        "verification_n": len(verify_seconds),
        "golden_time_threshold_sec": GOLDEN_TIME_THRESHOLD_SEC,
        "golden_time_compliance_pct": golden_rate,
        "golden_time_note": (
            "근사치 — 확인 회신(occurred_at→reviewed_at) 기준. 헬기 투하·지상 "
            "도달의 실제 시각은 이 앱이 갖고 있지 않다(그 시각을 쥔 커널의 공개 "
            "문은 분포(p50/p95)만 내고 사건별 원값을 안 낸다) — 숨기지 않고 "
            "이 칸에 적는다."),
    }


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-17 카메라별 오탐률(안개·소각 …)·임계값 시험(K6·QA-12)
# ═══════════════════════════════════════════════════════════════════════════
ACTION_CAMERA_THRESHOLD_TEST = "office2.camera_fpr.threshold_test"
_REASON_CODE_RE = re.compile(r"\[(\w+)\]")


def camera_false_alarm_rates(*, scope, since: str = "", until: str = "") -> dict:
    """FWS-F3-17 — 카메라별 오탐률. `reject_reason` 안의 사유 부호를
    `verification.FALSE_ALARM_REASONS`(F1-06 문 재사용)로 되짚는다 — 사유
    분류를 두 벌로 짓지 않는다(D-212)."""
    since_dt = _parse_dt(since)
    until_dt = _parse_dt(until)
    rows = list(dsm_services.recent_events(
        scope=scope, since=since_dt, until=until_dt, limit=2000))

    by_camera: dict = {}
    for r in rows:
        cam = by_camera.setdefault(r.stream_monitor_id, {
            "stream_monitor_id": r.stream_monitor_id,
            "stream_monitor_name": r.stream_monitor_name,
            "total": 0, "reviewed": 0, "false_alarm": 0,
            "reason_breakdown": Counter(),
        })
        cam["total"] += 1
        if r.verdict is not None:
            cam["reviewed"] += 1
            if r.verdict == "rejected":
                cam["false_alarm"] += 1
                reason_code = None
                match = _REASON_CODE_RE.search(r.reject_reason or "")
                if match and match.group(1) in fws_verification.FALSE_ALARM_REASONS:
                    reason_code = match.group(1)
                cam["reason_breakdown"][reason_code or "미상"] += 1

    cameras = []
    for cam in by_camera.values():
        rate = (round(cam["false_alarm"] / cam["reviewed"] * 100, 1)
               if cam["reviewed"] else None)
        cameras.append({
            "stream_monitor_id": cam["stream_monitor_id"],
            "stream_monitor_name": cam["stream_monitor_name"],
            "total": cam["total"], "reviewed": cam["reviewed"],
            "false_alarm": cam["false_alarm"], "false_alarm_rate_pct": rate,
            "reason_breakdown": dict(cam["reason_breakdown"]),
        })
    return {"since": since or None, "until": until or None, "cameras": cameras}


def run_camera_threshold_test(*, scope, stream_monitor_id: int,
                              threshold_pct: float, since: str = "",
                              until: str = "") -> dict:
    """FWS-F3-17 — 임계값 시험(K6·QA-12). 완결조건은 「저장」— 판정 한 줄을
    감사에 남긴다."""
    if not (0.0 <= threshold_pct <= 100.0):
        raise Office2InputRejected(
            f"threshold_pct={threshold_pct!r} 는 0~100 범위 밖이다")
    stats = camera_false_alarm_rates(scope=scope, since=since, until=until)
    row = next((c for c in stats["cameras"]
               if c["stream_monitor_id"] == stream_monitor_id), None)
    rate = row["false_alarm_rate_pct"] if row else None
    if rate is None:
        result = "unmeasurable"
    elif rate <= threshold_pct:
        result = "pass"
    else:
        result = "fail"
    actor = scope.require_actor()
    payload = {
        "stream_monitor_id": stream_monitor_id, "threshold_pct": threshold_pct,
        "computed_false_alarm_rate_pct": rate, "result": result,
        "tested_at": _now_iso(),
    }
    _write(actor, ACTION_CAMERA_THRESHOLD_TEST, payload,
          f"카메라 {stream_monitor_id} 오탐률 임계값 시험 · 결과={result}")
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-18 계도·단속 통계 · 입산통제구역 관리
# ═══════════════════════════════════════════════════════════════════════════
#: `patrol.py`·`standby.py` 와 같은 한계 — 감사 표에 테넌트 칸이 없어 **본인
#: 기록만**(조직 전체 집계는 범위 밖).
KIND_GUIDANCE = "guidance"        # 계도
KIND_ENFORCEMENT = "enforcement"  # 단속
PATROL_ENFORCEMENT_KINDS: tuple = (KIND_GUIDANCE, KIND_ENFORCEMENT)
ACTION_PATROL_ENFORCEMENT = "office2.patrol_enforcement.record"

ZONE_STATUS_ACTIVE = "active"
ZONE_STATUS_LIFTED = "lifted"
ZONE_STATUSES: tuple = (ZONE_STATUS_ACTIVE, ZONE_STATUS_LIFTED)
ACTION_ENTRY_CONTROL_ZONE = "office2.entry_control_zone.set"

MAX_ZONE_NAME_CHARS = 60
MAX_LOCATION_CHARS = 120


def record_patrol_enforcement(*, scope, kind: str, location: str = "",
                             note: str = "") -> dict:
    """FWS-F3-18 — 계도·단속 기록 한 건."""
    if kind not in PATROL_ENFORCEMENT_KINDS:
        raise Office2InputRejected(
            f"kind={kind!r} 는 계도·단속 종류가 아니다. "
            f"허용: {PATROL_ENFORCEMENT_KINDS}")
    location = (location or "").strip()
    if len(location) > MAX_LOCATION_CHARS:
        raise Office2InputRejected(
            f"location 이 {len(location)}자다. 상한은 {MAX_LOCATION_CHARS}자")
    actor = scope.require_actor()
    payload = {"kind": kind, "location": location, "note": note,
              "recorded_at": _now_iso()}
    entry = _write(actor, ACTION_PATROL_ENFORCEMENT, payload,
                  f"{kind} 기록 · {location or '(장소 미기재)'}")
    return {"record_id": entry.audit_id, **payload}


def patrol_enforcement_stats(*, scope) -> dict:
    """FWS-F3-18 — 계도·단속 통계. **본인이 남긴 기록만**(`equipment.py::mine`
    과 같은 한계)."""
    actor = scope.require_actor()
    rows = _rows_of(actor.pk, ACTION_PATROL_ENFORCEMENT)
    counts: Counter = Counter()
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        if payload.get("kind"):
            counts[payload["kind"]] += 1
    return {"by_kind": dict(counts), "total": sum(counts.values()), "scope": "mine"}


def set_entry_control_zone(*, scope, zone_name: str, status: str) -> dict:
    """FWS-F3-18 — 입산통제구역 관리(설정/해제)."""
    zone_name = (zone_name or "").strip()
    if not zone_name:
        raise Office2InputRejected("zone_name 이 비었다")
    if len(zone_name) > MAX_ZONE_NAME_CHARS:
        raise Office2InputRejected(
            f"zone_name 이 {len(zone_name)}자다. 상한은 {MAX_ZONE_NAME_CHARS}자")
    if status not in ZONE_STATUSES:
        raise Office2InputRejected(
            f"status={status!r} 는 구역 상태가 아니다. 허용: {ZONE_STATUSES}")
    actor = scope.require_actor()
    payload = {"zone_name": zone_name, "status": status, "set_at": _now_iso()}
    _write(actor, ACTION_ENTRY_CONTROL_ZONE, payload,
          f"입산통제구역 {zone_name} → {status}")
    return payload


def entry_control_zones(*, scope) -> dict:
    """지금 이 사람이 설정한 구역들의 **최신 상태**(본인 것만 · 위와 같은 한계)."""
    actor = scope.require_actor()
    rows = _rows_of(actor.pk, ACTION_ENTRY_CONTROL_ZONE)  # 최신(-id)순
    latest: dict = {}
    for row in rows:
        payload = row.data_after if isinstance(row.data_after, dict) else {}
        name = payload.get("zone_name")
        if name and name not in latest:  # 처음 만난 것(=최신)만 남긴다
            latest[name] = payload
    return {"zones": list(latest.values()), "scope": "mine"}


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-19 훈련 시나리오 실행(가상 사건 · 실채널 0)
# ═══════════════════════════════════════════════════════════════════════════
#: `apps/fws/training.py`(F2-13)와 같은 판단 — DSM 의 훈련 스위치가 정본이고
#: 이 파일은 새 스위치를 만들지 않는다.
def start_drill_scenario(*, scope, reason: str) -> dict:
    """FWS-F3-19 — 훈련 시나리오 실행(가상 사건)."""
    reason = (reason or "").strip()
    if not reason:
        raise Office2InputRejected("reason(훈련 사유)이 비었다")
    return dsm_services.set_drill_mode(scope=scope, enabled=True, reason=reason)


def drill_scenario_status(*, scope) -> dict:
    return dsm_services.drill_state(scope=scope)


def end_drill_scenario(*, scope, reason: str = "") -> dict:
    """FWS-F3-19 — 훈련 종료 보고서. 첫 증거는 **실채널 발송 0**
    (`training.py` 머리말과 같은 완결조건 — `drill_report` 가 그 값을 잰다)."""
    dsm_services.set_drill_mode(
        scope=scope, enabled=False,
        reason=(reason or "").strip() or "훈련 시나리오 종료")
    return dsm_services.drill_report(scope=scope)


# ═══════════════════════════════════════════════════════════════════════════
# FWS-F3-20 온보딩 카드 7(조심기간 전)
# ═══════════════════════════════════════════════════════════════════════════
#
# `apps/dsm/onboarding.py::CARDS` 와 같은 모양(카드 키·문안·닫는 술어)이지만
# **두 벌을 만들지 않는다** — 그 표는 공용 파일(다른 차선도 쓴다)이고 DSM 의
# 여섯 역할(U1~U6)만 갖는다 · F3(산림과 담당) 역할은 없다. 그래서 이 표는 그
# 표를 고치지 않고(§0.4 인접 — 공용 파일 목록) **이 차선이 새로 연 문 일곱
# 개만으로** 진행률을 잰다 — annex §5.3 FWS-F3-20 「카드 7」의 실측.
F3_CARD_KEYS: tuple = (
    "f3.evacuation_plan", "f3.evacuation_progress", "f3.hourly_report",
    "f3.final_report", "f3.camera_threshold", "f3.patrol_enforcement", "f3.drill",
)

F3_CARD_PROMPTS: dict = {
    "f3.evacuation_plan": "대피 계획 초안 작성",
    "f3.evacuation_progress": "대피 이행 확인 기록",
    "f3.hourly_report": "매시간 상황보고 초안",
    "f3.final_report": "진화완료 보고 작성",
    "f3.camera_threshold": "카메라 오탐률 임계값 시험",
    "f3.patrol_enforcement": "계도·단속 기록",
    "f3.drill": "훈련 시나리오 실행",
}


def _closed_by_action(user_id: int, action: str) -> bool:
    return bool(_rows_of(user_id, action))


def f3_onboarding_progress(*, scope) -> dict:
    """FWS-F3-20 — 온보딩 카드 7. 카드마다 **이 사람이 실제로 그 문을 두드렸는가**
    로 닫는다(`apps/dsm/onboarding.py` 의 `closes` 술어와 같은 판단 — 화면을 열어
    본 사실이 아니라 서버 기록으로 잰다 · D-301)."""
    actor = scope.require_actor()
    closed_map = {
        "f3.evacuation_plan": _closed_by_action(actor.pk, ACTION_EVAC_PLAN_DRAFT),
        "f3.evacuation_progress": _closed_by_action(actor.pk, ACTION_EVAC_PROGRESS),
        "f3.hourly_report": _closed_by_action(actor.pk, ACTION_HOURLY_DRAFT),
        "f3.final_report": _closed_by_action(actor.pk, ACTION_FINAL_REPORT),
        "f3.camera_threshold": _closed_by_action(
            actor.pk, ACTION_CAMERA_THRESHOLD_TEST),
        "f3.patrol_enforcement": _closed_by_action(
            actor.pk, ACTION_PATROL_ENFORCEMENT),
        "f3.drill": bool(dsm_services.drill_report(scope=scope).get("measurable")),
    }
    cards = [{"key": k, "prompt": F3_CARD_PROMPTS[k], "closed": closed_map[k]}
            for k in F3_CARD_KEYS]
    done = sum(1 for c in cards if c["closed"])
    return {"cards": cards, "total": len(cards), "done": done,
           "percent": round(done / len(cards) * 100, 1)}
