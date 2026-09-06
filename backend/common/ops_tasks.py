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


def backup_dir_is_separate_volume(out_dir: str):
    """보관처가 **정말 다른 볼륨인가.** 못 재면 `None` 이고, 그것은 참이 아니다.

    ★ 왜 이 검사가 필요한가 (OPS-12a · P-67 「목적지 별도 볼륨 `/backup`」)
      선언은 `/backup` 이라고 적을 수 있다. 그런데 그 경로가 **볼륨으로 안 붙어
      있으면** `mkdir` 이 컨테이너 루트 파일시스템에 평범한 폴더를 만들고, 백업은
      거기 떨어진다 — 컨테이너를 다시 만드는 순간 사라지고, 그 전까지는
      **「파일이 생겼다」가 초록으로 보인다.** 그것이 이 절의 착시다.

      리눅스에서 마운트 경계는 `st_dev` 로 드러난다. 루트와 장치 번호가 같으면
      그 경로는 **붙은 볼륨이 아니다.**

    Returns:
        참(다른 장치) · 거짓(루트와 같은 장치) · `None`(못 쟀다).
    """
    try:
        target = Path(out_dir)
        probe = target if target.exists() else target.parent
        if not probe.exists():
            return None
        return os.stat(str(probe)).st_dev != os.stat("/").st_dev
    except OSError as exc:                         # noqa: BLE001
        logger.warning("[OPS][BACKUP] 보관처가 별도 볼륨인지 못 쟀다: %s", exc)
        return None


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
        payload = {"measured_at": stamp, "verdict": "SKIPPED_UNDECLARED",
                   "reason": ("백업 목적지가 **선언되지 않았다**(`OPS_BACKUP_DIR`) — "
                              "**어디에 뜰지 모르는 백업은 백업이 아니다.** "
                              "기본 경로를 지어내지 않는다 (D-280 · P-67). "
                              "선언 자리: U5 설정 화면 · 개발·스테이징은 "
                              "config/retention_seed.py")}
        logger.error("[OPS][BACKUP] %s", payload["reason"])
        _write_evidence("backup_last", payload)
        return payload

    #: ★ 「같은 디스크는 백업이 아니다」 — 선언이 `/backup` 이어도 **붙어 있어야** 한다.
    separate = backup_dir_is_separate_volume(out_dir)
    if separate is not True:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "out_dir": out_dir, "separate_volume": separate,
                   "reason": (f"보관처 {out_dir!r} 가 **별도 볼륨으로 안 붙어 있다**"
                              if separate is False else
                              f"보관처 {out_dir!r} 가 별도 볼륨인지 **못 쟀다**")
                             + " — 여기에 뜨면 컨테이너와 함께 사라지고, 그 전까지 "
                               "「파일이 생겼다」가 초록으로 보인다. 붙이는 법은 "
                               "docker-compose 의 볼륨 선언(OPS_BACKUP_VOLUME)이고, "
                               "그것은 컨테이너 재생성이 필요하다"}
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
# 운영 자동화 ②b — **복구 시험이 주 1회 저절로 돈다** (P-67 · OPS-19 · 2026-09-06)
# ═══════════════════════════════════════════════════════════════════════════
#
#     **복구를 해 보지 않은 백업은 백업이 아니다** (D-354 ①).
#
# 그 문장은 2026-08-29 부터 이 저장소에 있었고, 복구를 **사람이 한 번** 해 본
# 기록도 있다(`docs/agent/evidence/D-354/restore_run.md`). 없던 것은 둘이다:
#     ㉠ **주기** — 손으로 하는 복구 시험은 바쁜 달에 안 한다.
#     ㉡ **RTO** — 「살아났다」만 있고 **몇 분 걸렸는지가 없었다.** SLA 초안
#        (GX-LAW-05)이 약속하려는 것은 「살아난다」가 아니라 **「30분 안에」**다.
#        재지 않은 수를 약속하면 그것은 종이다.
#
# ★ 왜 `ops_backup_beat` 이 복구까지 하지 않는가 — 그 파일이 이미 답했다:
#   「복구는 사람이 확인하는 일이고, 자동 복구는 운영 DB 를 건드리는 일이다.」
#   그 판단은 유효하다. 그래서 이 태스크도 **운영 DB 를 건드리지 않는다** —
#   `restore_check_` 로 시작하는 임시 DB 에 되살리고 지운다.
#
# ⚠ **이 환경에서는 회색이 나온다. 그 사실을 덮지 않는다** [실측 2026-09-06]:
#   앱 컨테이너의 `pg_restore` 는 17.7 이고 DB 서버는 18.1 이다. 낮은 판의
#   클라이언트는 높은 판의 덤프를 읽지 못한다 — `ops_backup.py` 머리말이 적어 둔
#   바로 그 사고다. 그래서 이 태스크는 판을 **먼저 재고**, 안 맞으면 exit 2 에
#   해당하는 `UNKNOWN` 을 낸다. 「못 쟀다」를 「복구 성공」으로 적지 않는다.
#   고치는 자리는 코드가 아니라 **워커 이미지의 postgresql-client 판**이다.
def restore_drill_enabled() -> bool:
    """복구 시험 주기가 켜져 있는가. **선언이 없으면 안 돈다** (P-67)."""
    return bool(getattr(settings, "OPS_RESTORE_DRILL_ENABLED", False))


def _pg(cmd: list, env_extra=None, timeout: int = 1800):
    """`pg_*` 를 부른다. `(rc, stdout, stderr)`. 값(비밀번호)은 로그에 안 적는다."""
    import subprocess

    env = dict(os.environ)
    env.update(env_extra or {})
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace",
                       timeout=timeout, env=env)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _newest_dump(out_dir: str):
    """보관처에서 **가장 최근** 덤프 하나. 없으면 `None`."""
    try:
        dumps = sorted(Path(out_dir).rglob("*.dump"),
                       key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return None
    return dumps[0] if dumps else None


@shared_task(name="common.ops_restore_drill_beat")
def ops_restore_drill_beat() -> dict:
    """주 1회 **복구 시험(dry-run)** — 임시 DB 에 되살리고 **RTO 를 분으로 잰다.**

    ★ 원본을 건드리지 않는 세 겹은 `scripts/ops_restore.py` 와 같은 규약이다:
      ㉠ 대상 이름이 원본과 같으면 시작하지 않는다
      ㉡ 대상 이름은 `restore_check_` 로 시작해야 한다
      ㉢ 끝나면 지운다 — 실패해도 지운다(`finally`)
    """
    started = datetime.now(timezone.utc)
    stamp = started.isoformat(timespec="seconds")

    if not restore_drill_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED",
                   "reason": ("복구 시험 주기가 선언되지 않았다 "
                              "(`OPS_RESTORE_DRILL_ENABLED`). 백업은 뜨는데 "
                              "살아나는지는 아무도 안 본다")}
        logger.info("[OPS][RESTORE] 건너뜀 — %s", payload["reason"])
        _write_evidence("restore_drill_last", payload)
        return payload

    out_dir = getattr(settings, "OPS_BACKUP_DIR", "") or ""
    if not out_dir:
        payload = {"measured_at": stamp, "verdict": "SKIPPED_UNDECLARED",
                   "reason": "백업 목적지가 선언되지 않았다 — 살릴 것이 없다 (P-67)"}
        logger.info("[OPS][RESTORE] 건너뜀 — %s", payload["reason"])
        _write_evidence("restore_drill_last", payload)
        return payload

    dump = _newest_dump(out_dir)
    if dump is None:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN", "out_dir": out_dir,
                   "reason": (f"보관처 {out_dir!r} 에 덤프가 **하나도 없다.** "
                              "「백업이 0회」와 「복구가 실패」는 다른 사실이다")}
        logger.error("[OPS][RESTORE] %s", payload["reason"])
        _write_evidence("restore_drill_last", payload)
        return payload

    db = settings.DATABASES["default"]
    source = db.get("NAME") or ""
    target = "restore_check_" + started.strftime("%Y%m%d%H%M%S")
    if not target.startswith("restore_check_") or target == source:
        payload = {"measured_at": stamp, "verdict": "ALARM",
                   "reason": "복구 대상 이름이 안전 규약을 어겼다 — 시작하지 않는다"}
        _write_evidence("restore_drill_last", payload)
        return payload

    conn = ["-h", str(db.get("HOST") or "localhost"),
            "-p", str(db.get("PORT") or 5432), "-U", str(db.get("USER") or "")]
    penv = {"PGPASSWORD": str(db.get("PASSWORD") or "")}

    #: ★ 판을 **먼저** 잰다. 안 맞으면 복구는 시작도 못 하고, 그 사실은 환경의
    #:   사실이지 백업의 사실이 아니다 — 색을 옮겨 붙이지 않는다(P-70).
    rc, client_ver, err = _pg(["pg_restore", "--version"], timeout=60)
    if rc != 0:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": f"`pg_restore` 를 부르지 못했다: {err or client_ver}"}
        logger.error("[OPS][RESTORE] %s", payload["reason"])
        _write_evidence("restore_drill_last", payload)
        return payload
    rc, server_ver, err = _pg(["psql", *conn, "-d", source, "-tAc",
                               "SHOW server_version"], penv, timeout=60)
    server_ver = server_ver if rc == 0 else ""

    def _major(text):
        import re
        m = re.search(r"(\d+)", text or "")
        return int(m.group(1)) if m else None

    cmaj, smaj = _major(client_ver), _major(server_ver)
    if cmaj is not None and smaj is not None and cmaj < smaj:
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "client": client_ver, "server": server_ver, "dump": str(dump),
                   "reason": (f"클라이언트 판({cmaj})이 서버 판({smaj})보다 낮다 — "
                              "낮은 판은 높은 판의 덤프를 읽지 못한다. **환경의 "
                              "사실**이고, 고치는 자리는 워커 이미지의 "
                              "postgresql-client 다. 못 잰 것을 「복구 성공」으로 "
                              "적지 않는다")}
        logger.error("[OPS][RESTORE] %s", payload["reason"])
        _write_evidence("restore_drill_last", payload)
        return payload

    commands, notes, ok = [], [], False
    t0 = datetime.now(timezone.utc)
    try:
        rc, _, err = _pg(["psql", *conn, "-d", "postgres", "-c",
                          f'CREATE DATABASE "{target}"'], penv, timeout=300)
        commands.append(f'psql -d postgres -c CREATE DATABASE "{target}" (rc={rc})')
        if rc != 0:
            notes.append(f"임시 DB 를 만들지 못했다: {err[:200]}")
            raise RuntimeError(err[:200])

        rc, _, err = _pg(["pg_restore", "--no-owner", "--no-privileges",
                          *conn, "-d", target, str(dump)], penv)
        commands.append(f"pg_restore --no-owner --no-privileges -d {target} "
                        f"{dump.name} (rc={rc})")
        #: `pg_restore` 는 경고만으로도 rc=1 을 낸다. **행이 살아났는가**로 판정한다.
        rc2, rows, _ = _pg(["psql", *conn, "-d", target, "-tAc",
                            "SELECT count(*) FROM information_schema.tables "
                            "WHERE table_schema='public'"], penv, timeout=300)
        tables = int(rows) if rc2 == 0 and rows.isdigit() else None
        rc3, srows, _ = _pg(["psql", *conn, "-d", source, "-tAc",
                             "SELECT count(*) FROM information_schema.tables "
                             "WHERE table_schema='public'"], penv, timeout=300)
        src_tables = int(srows) if rc3 == 0 and srows.isdigit() else None
        ok = bool(tables) and tables == src_tables
        if not ok:
            notes.append(f"표 수가 어긋났다 — 원본 {src_tables} · 복구 {tables}")
    except Exception as exc:                       # noqa: BLE001
        notes.append(f"{type(exc).__name__}: {exc}"[:300])
        tables = src_tables = None
    finally:
        rc, _, _ = _pg(["psql", *conn, "-d", "postgres", "-c",
                        f'DROP DATABASE IF EXISTS "{target}"'], penv, timeout=600)
        commands.append(f'psql -d postgres -c DROP DATABASE "{target}" (rc={rc})')
        if rc != 0:
            notes.append(f"임시 DB `{target}` 를 못 지웠다 — 사람이 지워야 한다")

    seconds = (datetime.now(timezone.utc) - t0).total_seconds()
    payload = {
        "measured_at": stamp,
        "verdict": "OK" if ok else "ALARM",
        "dump": str(dump), "dump_bytes": dump.stat().st_size,
        "source_db": source, "target_db": target,
        "tables_source": src_tables, "tables_restored": tables,
        #: ★ **RTO 는 분으로 적는다** — SLA 가 분으로 약속하기 때문이다.
        "rto_seconds": round(seconds, 1),
        "rto_minutes": round(seconds / 60.0, 2),
        "commands": commands, "notes": notes,
        "scope": ("DB 만이다. 객체저장(영상·캡처)은 이 시험에 **안 들어 있다** — "
                  "DB 만 살아나면 「영상이 있었다고 말하는 DB」가 된다"),
    }
    logger.info("[OPS][RESTORE] 복구 시험 %s — 표 %s/%s · RTO %.2f분",
                payload["verdict"], tables, src_tables, payload["rto_minutes"])
    _write_evidence("restore_drill_last", payload)
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
#     정리 : 「감사 로그를 며칠 보관할 것인가」 — 고객이 정하는 값이다.
#
# ⛔ **위 두 줄에 「제품 안에 이미 답이 있다 · 기본 90」이라고 적혀 있었다. 거짓이었다.**
#    지우지 않고 남긴다 — 어떻게 틀렸는지가 판정보다 값나간다.
#
#    [실측 2026-09-05 · 턴 F 차선 E · OPS-07b] `AdminConfig::System` 에
#    `security.audit_log_retention_days` 가 **없다.** 90은 dj-core
#    `purge_old_audit_logs` 의 **코드 기본값**이다 — 아무도 정한 적이 없다.
#    [재확인 2026-09-06 · 턴 G] 개발 DB 의 `System` 행에 `security` 키 자체가 없다.
#
#    즉 「고객이 정한 값이다」가 아니라 **「아무도 안 정했는데 90일에 지운다」**였다.
#    그리고 그 삭제는 `_base_manager.delete()` = **하드 삭제**다(되돌릴 수 없다).
#
# ★ 그래서 P-67 뒤로 이 태스크는 **선언을 요구한다** (2026-09-06 · 차선 G):
#     선언이 있으면  → 그 수로 지운다
#     선언이 없으면  → **한 행도 안 지운다.** 조용히 넘기지 않고 감사에 남긴다.
#   dj-core 태스크는 우리가 못 고치므로(§0.4), **부르지 않는 것**이 우리가 쥔 손잡이다.
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


#: 감사 로그 보존 일수를 선언하는 자리 — **고객의 선언이 언제나 이긴다.**
#: dj-core 가 읽는 자리와 **같은 자리**를 읽는다. 두 벌로 두면 우리가 「선언됐다」고
#: 판정한 뒤 dj-core 가 다른 수로 지우는 상태가 된다(D-369).
AUDIT_RETENTION_CONFIG = ("System", "security.audit_log_retention_days")

#: 개발·스테이징이 **그 자리에 심을 수** (`config/retention_seed.py` · 365).
#: ⚠ 이 값은 **읽는 자리가 아니라 심는 값**이다. 판정은 언제나 위
#:   `AUDIT_RETENTION_CONFIG` 한 자리에서만 한다 — 아래 함수의 머리말이 그 사유다.
AUDIT_RETENTION_SETTING = "AUDIT_LOG_RETENTION_DAYS"


def audit_retention_declared_days():
    """감사 로그 보존 일수. **선언이 없으면 `None`** — 지어낸 수로 지우지 않는다.

    ★ **왜 우리 쪽 설정(`AUDIT_LOG_RETENTION_DAYS`)을 읽지 않는가** — 그것이
      가장 그럴듯한 함정이기 때문이다.

      실제로 지우는 것은 dj-core `purge_old_audit_logs` 이고, 그 함수는
      `AdminConfig::System > security.audit_log_retention_days` **하나만** 읽는다
      (없으면 코드 기본값 90). 우리는 그 함수를 고칠 수 없다(§0.4).
      그러니 우리 쪽 설정을 「선언됐다」의 근거로 삼으면 이렇게 된다:

          우리 층 판정: 「365일로 선언됐다 — 돌려도 된다」
          실제 삭제  : **90일 기준으로 하드 삭제**

      「선언한 수」와 「지우는 수」가 갈리는 그 상태가 이 저장소가 가장 두려워하는
      모양이다(D-369). 그래서 **dj-core 가 읽는 자리 하나만** 읽는다.
      개발·스테이징의 365는 `scripts/seed_retention_declaration.py` 가 **그 자리에
      심는다** — 설정에 적어 두는 것이 아니라 심어야 뜻이 생긴다.

    Returns:
        선언된 일수(양의 정수) 또는 `None`(미선언). `None` 은 0일이 아니다.
    """
    name, path = AUDIT_RETENTION_CONFIG
    try:
        from core.configuration.utils import get_config_value_by_path

        raw = get_config_value_by_path(name, path, None)
    except Exception as exc:                       # noqa: BLE001
        # 못 읽은 것을 「미선언」과 같은 쪽(안 지운다)으로 보내되, 사유는 남긴다.
        logger.warning("[OPS][AUDIT] %s::%s 를 읽지 못했다: %s", name, path, exc)
        return None
    if raw is None:
        return None
    try:
        days = int(raw)
    except (TypeError, ValueError):
        logger.warning("[OPS][AUDIT] 보존 일수 %r 를 읽지 못했다 — **미선언으로 본다**",
                       raw)
        return None
    return days if days > 0 else None


def audit_retention_source() -> str:
    """그 수가 **어디서 왔는가.** 값만 보이면 다음 사람이 출처를 못 되짚는다."""
    name, path = AUDIT_RETENTION_CONFIG
    if audit_retention_declared_days() is not None:
        return f"선언 {name} > {path} (U5 설정 화면 · dj-core 가 읽는 자리)"
    seeded = getattr(settings, AUDIT_RETENTION_SETTING, None)
    if seeded is not None:
        return (f"미선언 — 심을 값 {seeded}일은 있으나 아직 심지 않았다 "
                f"(scripts/seed_retention_declaration.py)")
    return "미선언"


@shared_task(name="common.ops_audit_purge_beat")
def ops_audit_purge_beat() -> dict:
    """감사 로그 보존기간을 집행한다 — **선언된 일수 그대로. 선언이 없으면 안 돈다.**

    ★ 보존기간을 여기서 정하지 않는다. 우리는 **선언이 있는지**를 묻고, 없으면
      dj-core 태스크를 **부르지 않는다**. 부르면 그 안의 코드 기본값 90이 돌고,
      그것은 아무도 정하지 않은 수로 되돌릴 수 없게 지우는 일이다(P-67 · OPS-07b).
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not audit_purge_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED",
                   "reason": ("OPS_AUDIT_PURGE_ENABLED 가 거짓이다 — 보존기간을 "
                              "집행하지 않는다. 감사 로그는 무한히 쌓인다")}
        logger.info("[OPS][AUDIT] 건너뜀 — %s", payload["reason"])
        return payload

    #: ★ P-67 — **선언이 먼저다.** 여기서 돌아서는 것이 이 태스크의 가장 중요한 갈래다.
    declared = audit_retention_declared_days()
    if declared is None:
        payload = {"measured_at": stamp, "verdict": "SKIPPED_UNDECLARED",
                   "retention_days": None,
                   "source": audit_retention_source(),
                   "purged": 0,
                   "reason": ("감사 로그 보존 일수가 **선언되지 않았다** — 한 행도 "
                              "지우지 않는다. dj-core 의 코드 기본값 90은 아무도 "
                              "정한 적이 없는 수이고(OPS-07b 실측), 그 수로 지우면 "
                              "되돌릴 수 없다. 선언 자리: AdminConfig System > "
                              "security.audit_log_retention_days (U5) · "
                              "개발·스테이징은 config/retention_seed.py")}
        logger.info("[OPS][AUDIT] 건너뜀 — 보존 일수 미선언 (호출 0)")
        _write_evidence("audit_purge_last", payload)
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
                   "retention_days": declared,
                   "source": audit_retention_source(),
                   "rows_before": before, "rows_after": after,
                   "purged": before - after}
        logger.info("[OPS][AUDIT] 보존기간 집행 — %d일 선언 · %d건 중 %d건 정리 "
                    "(남은 %d건)", declared, before, before - after, after)
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


# ═══════════════════════════════════════════════════════════════════════════
# 운영 자동화 ④ — **영상 보존기간 집행** (LAW-02a · 2026-09-05 · 차선 L)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 감사 로그 정리(위 ③)와 **같은 모양으로** 선다. 새 방식을 들이지 않는다:
#   도구는 차선이 짓고 주기는 여기 걸린다 — 이 파일이 이미 세 번 그렇게 했다.
#
# ★ 왜 이것이 백업(꺼짐)이 아니라 감사 정리(켜짐) 쪽인가 — 질문이 같기 때문이다.
#     백업 : 「어디에 얼마나 쌓을 것인가」 — 제품 안에 답이 없다 → 끈다
#     정리 : 「며칠 보관할 것인가」        — **제품 안에 답이 있다** → 켠다
#   LAW-02a 가 그 답을 만들었다(`apps/dsm/retention.retention_days()`). 그리고
#   그 수는 **안내판에 인쇄되어 게시된다.** 게시된 수대로 지우지 않으면 그 종이는
#   법적 효력을 가진 거짓말이 된다 — 꺼 둘 수 있는 성질의 일이 아니다.
#
# ★ 그래도 손잡이는 둔다: `VIDEO_RETENTION_SWEEP_ENABLED=false` 면 안 돈다.
#   지우는 일에는 되돌림이 없고, 「우리는 영구 보관한다」는 고객이 있을 수 있다.
#   ⚠ 끄면 안내판의 「보관 기간이 지난 영상은 자동으로 지워집니다」가 거짓이 된다 —
#     그래서 끈 상태를 `ops_status()` 가 아니라 **보존 정책 응답이** 말한다
#     (`retention.policy()['enforced']`). 화면이 그 값을 본다.
#
# ★ L1 이 L4 를 부르는 것처럼 보이는 자리다 — **함수 안에서** 늦게 부른다.
#   위 ③이 dj-core 태스크를 감싼 것과 같은 모양이고, 계층 게이트
#   (`scripts/verify_layers.py`)가 보는 것은 `backend/apps` · `backend/kernels` ·
#   `backend/adapters` 셋이다. 판단은 그것과 별개로 적어 둔다: 주기는 제품의 것이고
#   태스크가 사는 자리는 celery 가 찾을 수 있는 곳이어야 한다. `apps/dsm` 은
#   Django 앱이 아니라 autodiscover 가 못 본다 [실측 · `apps/dsm/__init__.py`].
def video_retention_enabled() -> bool:
    """영상 보존기간 집행이 켜져 있는가. **기본은 켬**이다(위 사유)."""
    return bool(getattr(settings, "VIDEO_RETENTION_SWEEP_ENABLED", True))


@shared_task(name="common.video_retention_sweep_beat")
def video_retention_sweep_beat() -> dict:
    """보관 기간이 지난 영상을 **실제로 지운다** (LAW-02a · P-57).

    ★ 주기 실행은 `dry_run=False` 다 — 그것이 이 태스크의 존재 이유다.
      미리보기만 도는 주기는 「적었다」와 같은 상태이고, 그 상태가 안내판을
      거짓말로 만든다. 사람이 누르는 자리(HTTP)는 반대로 `dry_run` 이 기본이다.

    ★ **2026-09-05 · 차선 E — 부르는 손이 `sweep` 에서 `purge_all_declared` 로 바뀌었다.**
      태스크 **이름은 그대로다**(`common.video_retention_sweep_beat`) — beat 표는
      `config/celery.py` 에 있고 그 파일은 이 차선의 것이 아니다. 이름을 바꾸면
      beat 가 없는 태스크를 부르고, **없는 태스크를 부르는 주기는 조용히 아무것도
      안 한다.** 바뀐 것은 이름이 아니라 **범위**다:

          앞:  `sweep()`               — **전역.** 아무도 선언하지 않았어도 제품
                                        기본값 30일로 전 테넌트를 지운다.
          지금: `purge_all_declared()` — **선언한 테넌트만.** 선언이 먼저다.

      왜 바꾸나 (지시서 §4 함정 ㉡): celery 워커가 서면 이 주기가 **실제로 돈다.**
      그 순간 「우리는 영구 보관한다」고 알고 있던 테넌트의 영상이 30일에 사라진다.
      제품 기본값 30은 **안내판의 수**이지 남의 자료에 대한 파기 명령이 아니다.
      선언이 하나도 없으면 이 태스크는 **0건 파기**로 끝나고, 그것이 옳은 정지다.
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not video_retention_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED",
                   "reason": ("VIDEO_RETENTION_SWEEP_ENABLED 가 거짓이다 — "
                              "보존기간을 집행하지 않는다. 안내판에 적힌 보관 "
                              "기간은 지켜지지 않는다")}
        logger.info("[OPS][VIDEO] 건너뜀 — %s", payload["reason"])
        _write_evidence("video_retention_last", payload)
        return payload

    try:
        from apps.dsm.retention import purge_all_declared

        result = purge_all_declared(
            dry_run=False, actor=None,
            reason="주기 집행 — 선언한 보존 일수대로 지운다 (P-57 파기)")
        payload = {"measured_at": stamp, "verdict": "OK", **result}
        logger.info("[OPS][VIDEO] 테넌트 %s중 선언 %s — 만료 %s건 · 파기 %s건 · "
                    "객체 %s건",
                    result.get("tenants_total"), result.get("tenants_declared"),
                    result.get("expired_total"), result.get("deleted_total"),
                    result.get("objects_deleted_total"))
    except Exception as exc:                       # noqa: BLE001
        # 지우지 못한 것은 **판정 불가**이지 「0건 정리」가 아니다 (D-301).
        payload = {"measured_at": stamp, "verdict": "ALARM",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[OPS][VIDEO] 영상 보존기간 집행이 실패했다")

    _write_evidence("video_retention_last", payload)
    return payload
