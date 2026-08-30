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
