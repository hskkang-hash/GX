# -*- coding: utf-8 -*-
"""운영 자동화 — **도구는 이미 있었다. 없던 것은 「저절로 도는 것」이다** (D-373).

★ 착수 전 실측 (D-333 ④ · D-369)
--------------------------------
지시 D-371 표적 ②는 「백업 자동화 + 모니터링 3종」이었다. 만들기 전에 뒤졌다:

    scripts/ops_backup.py    있다 (2026-09-09 · D-354 ①) — DB + 객체저장 + 대조표
    scripts/ops_restore.py   있다 — 대조표와 **해시로** 맞춰 본다
    scripts/ops_monitor.py   있다 — 감시 3종(살아 있는가 · 밀리는가 · 채워지는가)

**셋 다 있었다.** 그러니 이 파일이 만드는 것은 도구가 아니라 **주기**다.
「백업 스크립트가 있다」와 「백업이 매일 돈다」는 다른 사실이고,
사람이 손으로 부르는 백업은 **바쁜 날 안 돌아간다.**

왜 크론이 아니라 Celery beat 인가
---------------------------------
크론은 **운영 호스트의 것**이다. 저장소에 crontab 을 커밋해도 그것은 문서이고,
문서는 기억을 요구한다(D-286). 이 제품은 이미 celery beat 를 띄우므로
**제품과 같은 수명**을 갖는 자리에 둔다 — 앱이 뜨면 감시도 뜬다.

★ 감시는 켜고, 백업은 **끈 채로 둔다** — 그리고 그것이 판단이다
---------------------------------------------------------------
    감시 (`ops_monitor_beat`)  기본 **켬**. 읽기만 한다. 켜서 나빠질 것이 없고,
                               꺼 두면 「죽었을 때 사람이 모른다」가 그대로 남는다
    백업 (`ops_backup_beat`)   기본 **끔**. `OPS_BACKUP_SCHEDULE_ENABLED=true` 라야 돈다

  백업을 기본으로 켜지 않는 이유는 겁이 나서가 아니다. 백업은 **어디에 얼마나
  오래 쌓을 것인가**를 정해야 도는 일이고, 그 답은 고객 환경마다 다르다.
  기본값으로 켜면 우리가 남의 디스크에 대해 그 답을 정하는 것이 된다 —
  「보내는 자리(메일·문자)를 여기서 정하지 않는다」는 `ops_monitor.py` 의 판단과 같다.
  ★ 그리고 **끈 것을 켠 것처럼 보고하지 않는다**: `ops_status()` 가 둘의 상태를 낸다.

경보를 어디로 보내나 — **여기서 정하지 않는다**
-----------------------------------------------
`ops_monitor.py` 가 이미 그렇게 정했고 그 판단을 따른다. 이 태스크는 판정을
**로그와 증거 파일**에 남긴다. 그 둘을 사람에게 보내는 자리는 고객 환경의 것이다.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("ops")

#: 저장소 안의 도구를 부른다. 컨테이너에서 `/repo` 로 마운트되고, 없으면 **없다고 적는다** —
#: 스크립트를 다시 구현하지 않는다(두 벌은 반드시 어긋난다 · D-369).
SCRIPTS_DIRS = ("/repo/scripts", "/app/../scripts")

#: 판정을 남기는 자리. 로그만 남기면 지나간 판정을 되짚을 수 없다.
EVIDENCE_DIR = "/docs/agent/evidence/D-373"


def _load(name: str):
    """`scripts/` 의 도구 하나를 모듈로 불러온다. 못 부르면 `None` — 조용히 넘기지 않는다."""
    import importlib.util

    for base in SCRIPTS_DIRS:
        path = Path(base) / f"{name}.py"
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(f"_ops_{name}", path)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules.setdefault(f"_ops_{name}", module)
        spec.loader.exec_module(module)
        return module
    return None


def _write_evidence(name: str, payload: dict) -> str | None:
    try:
        out_dir = Path(EVIDENCE_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{name}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
        return str(out)
    except OSError as exc:
        logger.warning("[OPS] 증거를 남기지 못했다: %s", exc)
        return None


def backup_schedule_enabled() -> bool:
    """백업 주기가 켜져 있는가. **기본값은 꺼짐**이고, 그것이 판단이다(머리말)."""
    return bool(getattr(settings, "OPS_BACKUP_SCHEDULE_ENABLED", False))


def ops_status() -> dict:
    """감시·백업 주기의 **지금 상태**. 「켰다고 적는 것」과 「켜진 것」을 가른다 (D-284)."""
    return {
        "감시_주기": "켬 (읽기만 한다)",
        "백업_주기": "켬" if backup_schedule_enabled() else
                     "끔 — OPS_BACKUP_SCHEDULE_ENABLED 가 참이라야 돈다",
        "백업_보관처": getattr(settings, "OPS_BACKUP_DIR", "") or "정해지지 않았다",
        "도구를_찾았는가": {
            "ops_monitor": _load("ops_monitor") is not None,
            "ops_backup": _load("ops_backup") is not None,
        },
    }


@shared_task(name="common.ops_monitor_beat")
def ops_monitor_beat() -> dict:
    """감시 3종을 돌린다 — **살아 있는가 · 밀리는가 · 채워지는가.**

    ★ 「닿지 못했다」와 「0이다」를 가른다 (D-301). 도구를 못 찾으면 `UNKNOWN` 이고
      **정상이 아니다** — 감시가 죽은 것을 초록으로 적으면 감시가 없는 것만 못하다.
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    module = _load("ops_monitor")
    if module is None:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": (f"ops_monitor.py 를 찾지 못했다 (찾은 자리: "
                              f"{', '.join(SCRIPTS_DIRS)}) — **정상이 아니라 판정 불가**다")}
        logger.error("[OPS][MONITOR] %s", payload["reason"])
        _write_evidence("monitor_last", payload)
        return payload

    try:
        report = module.collect()
    except Exception as exc:                       # noqa: BLE001 — 감시가 죽어도 앱은 산다
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[OPS][MONITOR] 감시가 터졌다 — 판정 불가")
        _write_evidence("monitor_last", payload)
        return payload

    verdicts = [v for v in _iter_verdicts(report)]
    if "ALARM" in verdicts:
        overall = "ALARM"
    elif "UNKNOWN" in verdicts:
        overall = "UNKNOWN"
    else:
        overall = "OK"

    # ★ [2026-09-24] **생존 알림이 안 온 것도 신호다** (OPS-14 나머지 절반).
    #   보내는 것만 있으면 이 절은 「보낸다」에서 끝나고, 안 온 것을 알아채는 일이
    #   사람의 기억에 남는다 — 그러면 장치가 아니다. 감시는 5분마다 도므로
    #   「오늘 08:00 것이 왔는가」를 물어볼 자리로 여기가 맞다.
    #   ⚠ 여기서 **다시 보내지 않는다.** 감시가 발송을 겸하면 감시가 부하를 만들고
    #     그 부하가 다시 감시 대상이 된다.
    try:
        from common.tenant_scope import TenantScope
        from kernels.k2_notify import heartbeat_watch

        watch = heartbeat_watch(
            scope=TenantScope.system(reason="OPS-14 생존 알림 감시 — 요청자가 없다"))
        late = [(gid, why) for (gid, is_late_, why) in watch if is_late_]
        report["heartbeat_late"] = {
            "value": len(late), "verdict": "ALARM" if late else "OK",
            "note": (late[0][1] if late else
                     "오늘 것이 왔거나 아직 유예 안이다 — 본 테넌트 %d" % len(watch)),
        }
        if late:
            overall = "ALARM"
            logger.error("[OPS][HEARTBEAT] **안 왔다** — 테넌트 %d개: %s",
                         len(late), late[0][1])
    except Exception as exc:                       # noqa: BLE001
        # 감시가 못 잰 것은 **판정 불가**이지 정상이 아니다 (D-301).
        report["heartbeat_late"] = {
            "value": None, "verdict": "UNKNOWN",
            "note": f"재지 못했다: {type(exc).__name__}: {exc}"[:200]}
        if overall == "OK":
            overall = "UNKNOWN"
        logger.warning("[OPS][HEARTBEAT] 생존 알림 감시가 못 쟀다: %s", exc)

    payload = {"measured_at": stamp, "verdict": overall, "report": report}
    _write_evidence("monitor_last", payload)
    log = logger.error if overall == "ALARM" else (
        logger.warning if overall == "UNKNOWN" else logger.info)
    log("[OPS][MONITOR] %s — 신호 %d개 (경보를 사람에게 보내는 자리는 "
        "고객 환경의 것이다)", overall, len(verdicts))
    return payload


def _iter_verdicts(report) -> list[str]:
    """판정 문자열만 훑는다. 보고서의 모양을 여기서 다시 정의하지 않는다 (D-212)."""
    found: list[str] = []
    stack = [report]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("verdict", "판정") and isinstance(value, str):
                    found.append(value.upper())
                else:
                    stack.append(value)
        elif isinstance(node, (list, tuple)):
            stack.extend(node)
    return found


@shared_task(name="common.ops_backup_beat")
def ops_backup_beat() -> dict:
    """백업을 뜬다 — **켜져 있을 때만.**

    ★ 꺼져 있으면 「건너뛰었다」고 **적고** 돌아간다. 조용히 아무것도 안 하면
      「돌았는데 아무 일 없었다」와 구별되지 않는다 (D-290).
    ★ 이 태스크는 `ops_restore` 를 부르지 않는다. **복구는 사람이 확인하는 일**이고
      (D-354 ① — 복구를 해 보지 않은 백업은 백업이 아니다), 자동 복구는
      운영 DB 를 건드리는 일이라 여기서 하지 않는다.
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not backup_schedule_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED",
                   "reason": ("백업 주기가 꺼져 있다 (OPS_BACKUP_SCHEDULE_ENABLED). "
                              "보관처와 보존 기간을 정하는 것은 운영의 판단이고, "
                              "기본값으로 켜면 우리가 남의 디스크에 대해 그것을 정하는 "
                              "일이 된다")}
        logger.info("[OPS][BACKUP] 건너뜀 — %s", payload["reason"])
        return payload

    out_dir = getattr(settings, "OPS_BACKUP_DIR", "") or ""
    if not out_dir:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": ("백업 주기는 켜졌는데 `OPS_BACKUP_DIR` 이 비었다 — "
                              "**어디에 뜰지 모르는 백업은 백업이 아니다.** "
                              "기본 경로를 지어내지 않는다 (D-280)")}
        logger.error("[OPS][BACKUP] %s", payload["reason"])
        _write_evidence("backup_last", payload)
        return payload

    module = _load("ops_backup")
    if module is None:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": "ops_backup.py 를 찾지 못했다 — 판정 불가"}
        logger.error("[OPS][BACKUP] %s", payload["reason"])
        _write_evidence("backup_last", payload)
        return payload

    target = Path(out_dir) / datetime.now(timezone.utc).strftime("%Y%m%d")
    try:
        target.mkdir(parents=True, exist_ok=True)
        db = module.dump_db(target)
        objects = module.mirror_objects(target, scope="event_bound")
        manifest = {"measured_at": stamp, "db": db, "objects": objects}
        ok = module.manifest_is_verifiable(manifest)
        payload = {"measured_at": stamp,
                   "verdict": "OK" if ok else "UNKNOWN",
                   "reason": "" if ok else ("대조표가 검증 가능하지 않다 — "
                                            "「파일이 생겼다」는 성공이 아니다"),
                   "manifest": manifest, "out_dir": str(target)}
    except Exception as exc:                       # noqa: BLE001
        payload = {"measured_at": stamp, "verdict": "ALARM",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[OPS][BACKUP] 백업이 실패했다")

    _write_evidence("backup_last", payload)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 운영 자동화 ③ — **감사 로그 보존기간 집행** (D-377 · 착시 ⑨ 전수에서 나왔다)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 착수 전 실측 (D-379) — **이미 있었다.** 또다.
#
#     dj-core `core/logger/tasks.py::purge_old_audit_logs` 가 **있다.**
#     `config/celery.py` 의 beat 표에 그 항목이 **주석으로 꺼진 채** 있었다:
#
#         # "purge-audit-logs-daily": {
#         #        "task": "core.logger.tasks.purge_old_audit_logs",
#         #        "schedule": crontab(hour=3, minute=0),
#         #    },
#
#     누군가 켰다가 껐고, **끈 사유는 어디에도 없다.** 이것이 ㉡(주기 없음)의
#     가장 순수한 형태다 — `verify_dormant.py` 가 주석 처리된 beat 항목을 따로
#     세는 이유가 이것이다.
#
# ★ 왜 백업(D-375)과 달리 **켜는가** — 두 질문이 다르기 때문이다
# ---------------------------------------------------------------
#     백업 : 「어디에 얼마나 오래 쌓을 것인가」 — 제품 안에 **답이 없다.**
#            기본값으로 켜면 우리가 남의 디스크에 대해 그 답을 정하는 것이 된다. → 끈다
#     정리 : 「감사 로그를 며칠 보관할 것인가」 — 제품 안에 **이미 답이 있다.**
#            `System > security.audit_log_retention_days` (기본 90). 고객이 정한 값이다.
#
#     ★ 그러니 정리를 꺼 두는 것은 **고객이 정한 보존기간이 아무 일도 하지 않는다**는
#       뜻이다. 설정은 있는데 그 설정이 도는 자리가 없는 것 — 그것이 착시 ⑨ 다.
#       켜는 것이 그 설정을 처음으로 **뜻있게** 만든다.
#
# ★ 왜 dj-core 태스크를 beat 에 직접 걸지 않고 여기서 감싸는가
# ------------------------------------------------------------
#     ① dj-core 는 §0.4 이관 자산이라 우리가 그 태스크의 로그·판정을 못 바꾼다.
#        감싸면 **몇 건을 지웠는지, 어느 보존기간으로 지웠는지**를 우리가 적을 수 있다.
#        「돌았다」와 「무엇을 했다」는 다른 사실이다 (D-290).
#     ② 끄는 손잡이가 필요하다. 지우는 일에는 되돌림이 없으므로,
#        고객이 「우리는 영구 보관한다」면 그 자리에서 끌 수 있어야 한다.
#     ③ ★ 그래도 **기본은 켬**이다. 끈 채로 등록만 해 두면 그것이 착시 ⑨ 의 재발이다 —
#        「켜기만 하고 안 도는 것」. 켤 수 없는 것만 꺼 둔다.
def audit_purge_enabled() -> bool:
    return bool(getattr(settings, "OPS_AUDIT_PURGE_ENABLED", True))


@shared_task(name="common.ops_audit_purge_beat")
def ops_audit_purge_beat() -> dict:
    """감사 로그 보존기간을 집행한다 — **고객이 정한 일수 그대로.**

    ★ 보존기간을 여기서 정하지 않는다. dj-core 의 설정을 읽는 것이 그 태스크의 몫이고,
      우리는 **몇 건이 남았고 몇 건이 사라졌는지**를 적는다. 두 벌로 정하면 어긋난다(D-369).
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not audit_purge_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED",
                   "reason": ("OPS_AUDIT_PURGE_ENABLED 가 거짓이다 — 보존기간을 "
                              "집행하지 않는다. 감사 로그는 무한히 쌓인다")}
        logger.info("[OPS][AUDIT] 건너뜀 — %s", payload["reason"])
        return payload

    try:
        from core.logger.models import AuditLogs
        from core.logger.tasks import purge_old_audit_logs
    except Exception as exc:                       # noqa: BLE001
        # 도구를 못 찾은 것은 **판정 불가**이지 정상이 아니다 (D-301).
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": f"dj-core 감사 로그 정리를 찾지 못했다: "
                             f"{type(exc).__name__}: {exc}"[:300]}
        logger.error("[OPS][AUDIT] %s", payload["reason"])
        _write_evidence("audit_purge_last", payload)
        return payload

    try:
        before = AuditLogs._base_manager.count()
        purge_old_audit_logs()
        after = AuditLogs._base_manager.count()
        payload = {"measured_at": stamp, "verdict": "OK",
                   "rows_before": before, "rows_after": after,
                   "purged": before - after}
        logger.info("[OPS][AUDIT] 보존기간 집행 — %d건 중 %d건 정리 (남은 %d건)",
                    before, before - after, after)
    except Exception as exc:                       # noqa: BLE001
        payload = {"measured_at": stamp, "verdict": "ALARM",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[OPS][AUDIT] 감사 로그 정리가 실패했다")

    _write_evidence("audit_purge_last", payload)
    return payload


# ═══════════════════════════════════════════════════════════════════════════
# 2파 주기 둘 — **도구는 차선이 지었고 주기는 조율자가 건다** (2026-09-24)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ D-373 이 이 파일에 적어 둔 문장이 그대로 다시 쓰인다:
#   「백업 스크립트가 있다」와 「백업이 매일 돈다」는 다른 사실이다.
#   차선 Q 가 OPS-14·OPS-15 의 **함수**를 세웠고, 주기가 없으면 그 둘은
#   **사람이 손으로 부를 때만** 도는 기능이다 — 그리고 바쁜 날 안 불린다.

@shared_task(name="common.heartbeat_digest_beat")
def heartbeat_digest_beat() -> dict:
    """OPS-14 — 테넌트마다 매일 08:00 한 통. **안 오면 장애다.**

    ★ 테넌트를 돌면서 부른다. `group` 없이 한 번 부르면 **전 테넌트의 수가 한 통에**
      실리고, 그것은 안부 인사가 아니라 남의 관제 현황 반출이다(D-281).
    ★ 수신자가 0명인 테넌트를 **조용히 넘기지 않는다** — 수로 남긴다. 「보냈는데
      대상이 없었다」가 성공으로 보이는 것이 재난 시스템에서 가장 조용한 고장이다.
    """
    from django.apps import apps

    from common.tenant_scope import TenantScope
    from kernels.k2_notify import NoRecipients, send_heartbeat_digest

    scope = TenantScope.system(reason="OPS-14 생존 알림 크론 — 요청자가 없다")
    out = {"sent": 0, "no_recipients": 0, "failed": 0}
    for group in apps.get_model("user", "UserGroup").objects.all():
        try:
            send_heartbeat_digest(scope=scope, group=group)
            out["sent"] += 1
        except NoRecipients:
            out["no_recipients"] += 1
        except Exception as exc:                   # noqa: BLE001
            out["failed"] += 1
            logger.exception("[OPS][HEARTBEAT] group=%s 에 못 보냈다: %s",
                             getattr(group, "pk", None), exc)
    logger.info("[OPS][HEARTBEAT] 생존 알림 — 보냄 %d · 수신자 0명 %d · 실패 %d",
                out["sent"], out["no_recipients"], out["failed"])
    return out


@shared_task(name="stream_monitors.camera_pulse_scan_beat")
def camera_pulse_scan_beat() -> dict:
    """OPS-15 — 구역 맥박 검사. **1분 주기다.**

    왜 1분인가: 규칙의 창이 5분이다. 5분마다 재면 창 하나를 통째로 놓칠 수 있고,
    놓친 군집 두절은 **아무 흔적도 남기지 않는다**. 1분이면 창 안에 다섯 번 본다.
    """
    from common.tenant_scope import TenantScope
    from stream_monitors.services.camera_pulse import scan_clusters

    result = scan_clusters(
        scope=TenantScope.system(reason="OPS-15 맥박 검사 — 요청자가 없다"))
    payload = {"zones": result.zones_seen, "cameras": result.cameras_seen,
               "created": result.created}
    if payload["created"]:
        logger.warning("[OPS][PULSE] 군집 두절 %d건 — 구역 %d · 카메라 %d",
                       payload["created"], payload["zones"], payload["cameras"])
    return payload


@shared_task(name="common.evidence_anchor_beat")
def evidence_anchor_beat() -> dict:
    """LAW-08 — 매일 00:05, **그날의 마지막 해시**를 재고 남긴다.

    ★ 왜 매일 재나: 체인은 **고치면 어긋난다**가 전부이고, 어긋난 것을 **언제** 아는가가
      그 값을 정한다. 사고가 난 뒤에 처음 돌리면 「언제부터 틀렸나」를 못 말한다.
    ★ 여기서 내는 앵커 40자가 일일 보고서 꼬리에 인쇄될 값이다 —
      **종이가 앵커다.** 인쇄 자리(K4)는 아직 없고, 값과 기록은 여기서부터 선다.
    ★ 무엇을 해시했는지 함께 남긴다: 필드 목록이 없으면 나중에 같은 값을 다시 못 만든다.
    """
    from datetime import date, timedelta

    from common import evidence_chain

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    day = date.today() - timedelta(days=1)
    try:
        report = evidence_chain.verify_chain()
        anchor = evidence_chain.daily_anchor(day)
        payload = {
            "measured_at": stamp,
            "verdict": "OK" if report.ok else "ALARM",
            "day": day.isoformat(),
            "anchor": anchor,
            "anchor_line": evidence_chain.anchor_line(day, anchor),
            "total": report.total,
            "chained": report.chained,
            "breaks": len(report.breaks),
            "hashed_fields": list(evidence_chain.iter_hashed_fields()),
        }
        if not report.ok:
            logger.error("[LAW-08] **체인이 어긋났다** — 끊긴 자리 %d건 (day=%s)",
                         len(report.breaks), day)
        else:
            logger.info("[LAW-08] 체인 온전 — 전체 %d · 이어진 것 %d · 앵커 %s",
                        report.total, report.chained, (anchor or "(그날 기록 없음)")[:16])
    except Exception as exc:                       # noqa: BLE001
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[LAW-08] 앵커를 재지 못했다 — 판정 불가")

    _write_evidence("evidence_anchor_last", payload)
    return payload

@shared_task(name="common.key_rotation_watch_beat")
def key_rotation_watch_beat() -> dict:
    """SEC-07 — **돌려야 할 키가 있는가.** 매일 03:50.

    ★ 자동으로 돌리지 않는다. 회전은 상대의 연동을 흔들고, 언제 흔들지는 사람이 정한다.
      이 자리가 하는 일은 하나다 — **때가 됐다는 사실을 사람에게 말한다.**
    ★ 이 beat 가 없으면 `key_rotation.py` 는 「있는데 아무도 안 부르는 코드」다.
      절차를 문서로만 두면 그 절차는 바쁜 날 돌지 않는다(D-373 이 백업에서 만난 그것).
    ★ 03:10 정리 · 03:30 백업 뒤다 — 하루의 정리가 끝난 뒤에 내일의 빚을 센다.
    """
    from common import key_rotation

    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    due = key_rotation.keys_due_for_rotation()
    payload = {
        "measured_at": stamp,
        "due": len(due),
        "policy_days": key_rotation.KEY_MAX_AGE_DAYS,
        "overlap_days": key_rotation.KEY_ROTATION_OVERLAP_DAYS,
        "keys": [{"key_id": d.key_id, "prefix": d.prefix, "owner": d.owner,
                  "age_days": d.age_days, "days_left": d.days_left, "why": d.why}
                 for d in due],
    }
    if due:
        logger.warning("[SEC-07] 돌려야 할 들어오는 키 %d건 — %s", len(due),
                       " · ".join(f"{d.prefix}({d.why})" for d in due[:5]))
    else:
        logger.info("[SEC-07] 돌려야 할 키 0건 (정책 %d일)", key_rotation.KEY_MAX_AGE_DAYS)
    _write_evidence("key_rotation_last", payload)
    return payload
