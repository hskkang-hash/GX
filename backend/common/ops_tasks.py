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

from common import evidence_guard

logger = logging.getLogger("ops")

#: 저장소 안의 도구를 부른다. 컨테이너에서 `/repo` 로 마운트되고, 없으면 **없다고 적는다** —
#: 스크립트를 다시 구현하지 않는다(두 벌은 반드시 어긋난다 · D-369).
SCRIPTS_DIRS = ("/repo/scripts", "/app/../scripts")

#: 판정을 남기는 자리. 로그만 남기면 지나간 판정을 되짚을 수 없다.
EVIDENCE_DIR = "/docs/agent/evidence/D-373"

#: ★ P-155 — **5분마다 스스로 쓰는 파일은 저장소 안에 두지 않는다** (턴 S · 조율자).
#:   `ops_monitor_beat` 은 beat 일정으로 **5분마다** 돈다. 그 판정을 저장소 안
#:   (`D-373/monitor_last.json`)에 쓰면 훅이 도는 동안 그 파일이 바뀌고, pre-commit 은
#:   전후를 비교해 **「files were modified by this hook」** 으로 커밋을 되돌린다.
#:   그리고 되돌릴 때 **애먼 훅이 범인으로 지목된다** — 턴 R 에 `gx-tool-selftest` 가
#:   그렇게 지목됐고, 그 판정기를 따로 돌리면 exit 0 이었다. 멀쩡한 게이트를 의심하며
#:   한 번을 버렸다.
#:
#:   가르는 자리는 **뜻**이다: 「지금 상태」와 「지나온 자취」는 다른 것이다.
#:   5분마다 덮어써야 하는 것이 앞이고(저장소 밖), 남겨야 하는 것이 뒤다(증거에 append).
STATE_DIR = os.environ.get("GX_OPS_STATE_DIR", "/var/lib/gx/state")

#: 증거에 남는 쪽. **판정이 바뀐 줄만** 쌓인다 — 「OK 가 또 OK 였다」는 자취가 아니다.
MONITOR_SUMMARY = "monitor_summary.jsonl"


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


def _db_name() -> str:
    """지금 붙어 있는 DB 이름. 못 물으면 빈 문자열 — **지어내지 않는다.**"""
    try:
        from django.db import connection

        return str(connection.settings_dict.get("NAME") or "")
    except Exception:                                  # noqa: BLE001
        return ""


def _write_evidence(name: str, payload: dict) -> str | None:
    """판정을 증거 파일에 남긴다. **시험 중에는 남기지 않는다.**

    ★ [실측 2026-09-06 · 턴 H · 차선 E] 이 함수가 **시험 DB 의 수로 운영 증거를
      덮고 있었다.** `tests/test_dormant_wiring.py` 와 이번 턴의 새 시험이
      `ops_audit_purge_beat()` 을 부르는데, `gx-shell` 에는 `/docs` 가 붙어 있어
      그 호출이 `D-373/audit_purge_last.json` 을 **진짜로 고쳤다**:

          시험 뒤 파일 : {"verdict": "SKIPPED_UNDECLARED", "purged": 0}   ← 시험 DB 의 사실
          개발 DB 의 사실 : {"verdict": "SKIPPED_UNREVERSIBLE", "purged": 0}

      즉 증거 파일을 읽은 사람은 **개발 환경이 미선언이라고 읽는다.** 아니다.
      시험 DB 에 선언이 없었을 뿐이다. 「어느 DB 에서 난 수인가」가 사라지면
      그 파일은 증거가 아니라 소음이다.

    ★ [P-87 ④ · 2026-09-06 턴 I] **그 검사는 여기 한 곳에만 있었다.**
      증거 폴더에 쓰는 자리는 이 함수 하나가 아니다(장부 명령 둘 · 등재부 하나 ·
      시험 안의 부트스트랩 하나 · 시험이 불러 쓰는 `scripts/` 의 도구들).
      한 자리만 막은 가드는 「막혀 있다」는 착시를 준다 — 그래서 술어를
      `common.evidence_guard` 한 자리로 옮기고, 그 아래에 **바닥 그물**을 깔았다.
    """
    why = evidence_guard.blocked_reason(Path(EVIDENCE_DIR) / f"{name}.json",
                                        who="ops_tasks._write_evidence",
                                        db_name=_db_name())
    if why:
        logger.info("[OPS] 증거를 안 남겼다 — %s", why)
        return None
    try:
        out_dir = Path(EVIDENCE_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"{name}.json"
        #: ★ **어느 DB 에서 난 수인가를 파일에 적는다** (P-87 4 · 턴 I).
        #:   가드가 새는 날은 또 온다. 그때 이 칸이 있으면 다음 사람이 파일만 보고
        #:   「이건 시험 DB 의 수다」를 알 수 있다 — 가드는 막고, 이 칸은 **말한다.**
        stamped = dict(payload)
        stamped["_written_from"] = {"db": _db_name(),
                                    "under_pytest": evidence_guard.under_pytest()}
        #: ★ [2026-09-07 턴 J] **끝에 줄바꿈을 남긴다.** 없으면 pre-commit 의
        #:   `end-of-file-fixer` 가 매번 이 파일을 고치고, 훅이 파일을 고치면
        #:   커밋은 언제나 중단된다 — 그리고 이 태스크가 다시 돌면 다시 벗겨진다.
        #:   **커밋이 영원히 안 되는 고리**였다(턴 J 에 실제로 세 번 돌았다).
        #:   POSIX 텍스트 파일의 규약이기도 하다.
        out.write_text(json.dumps(stamped, ensure_ascii=False, indent=2, default=str) + "\n",
                       encoding="utf-8")
        return str(out)
    except OSError as exc:
        logger.warning("[OPS] 증거를 남기지 못했다: %s", exc)
        return None


def _append_monitor_summary(verdict: str, payload: dict) -> None:
    """감시 판정이 **바뀐 때만** 증거에 한 줄 더한다 (P-155).

    ★ 왜 「바뀐 때만」인가
      5분마다 「OK」를 적으면 그것은 자취가 아니라 **소음**이고, 소음은 저장소를
      5분마다 더럽혀 커밋을 막는다(턴 R 에 세 번). 사람이 되짚고 싶은 것은
      「언제부터 나빠졌나 · 언제 돌아왔나」이지 「그 사이에도 계속 OK 였다」가 아니다.
    ⚠ 이 파일은 **덮어쓰지 않는다** — 오직 append. 덮어쓰는 순간 대장이 줄고,
      대장은 줄지 않는다(턴 S 불변).
    """
    path = Path(EVIDENCE_DIR) / MONITOR_SUMMARY
    why = evidence_guard.blocked_reason(path, who="ops_tasks._append_monitor_summary",
                                        db_name=_db_name())
    if why:
        logger.info("[OPS] 요약을 안 남겼다 — %s", why)
        return
    try:
        prev = ""
        if path.is_file():
            lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                prev = str(json.loads(lines[-1]).get("verdict") or "")
        if prev == verdict:
            return                                     # ★ 안 바뀌었으면 **안 쓴다**
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "measured_at": payload.get("measured_at"),
                "verdict": verdict,
                "from": prev or "(처음)",
                "state_file": STATE_DIR + "/monitor_last.json",
                "note": payload.get("reason") or
                        "감시 3종 — 자세한 수는 저장소 밖 상태 파일에 있다 (P-155)",
                "_written_from": {"db": _db_name(),
                                  "under_pytest": evidence_guard.under_pytest()},
            }, ensure_ascii=False, default=str) + "\n")
    except (OSError, ValueError) as exc:               # noqa: BLE001
        logger.warning("[OPS][MONITOR] 요약을 남기지 못했다: %s", exc)


def _write_monitor_state(payload: dict) -> str | None:
    """감시 판정 — **지금 상태는 저장소 밖에, 바뀐 자취만 증거에** (P-155).

    옛 이름은 `_write_evidence("monitor_last", …)` 였고, 그 한 줄이 저장소 안의
    파일을 5분마다 고쳤다. 함수를 가른 것이 처방이다 — 부르는 자리를 고치는 것이
    아니라 **쓰는 자리**를 갈랐다.
    """
    written = None
    try:
        state = Path(STATE_DIR)
        state.mkdir(parents=True, exist_ok=True)
        out = state / "monitor_last.json"
        stamped = dict(payload)
        stamped["_written_from"] = {"db": _db_name(),
                                    "under_pytest": evidence_guard.under_pytest()}
        out.write_text(
            json.dumps(stamped, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8")
        written = str(out)
    except OSError as exc:                             # noqa: BLE001
        # ⚠ 상태를 못 남긴 것은 **감시가 죽은 것이 아니다.** 판정은 이미 났고
        #   호출자에게 돌아간다 — 여기서 예외를 올리면 감시가 저장소 사정으로 죽는다.
        logger.warning("[OPS][MONITOR] 상태를 남기지 못했다 (%s): %s", STATE_DIR, exc)

    _append_monitor_summary(str(payload.get("verdict") or "UNKNOWN"), payload)
    return written


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
        _write_monitor_state(payload)
        return payload

    try:
        report = module.collect()
    except Exception as exc:                       # noqa: BLE001 — 감시가 죽어도 앱은 산다
        payload = {"measured_at": stamp, "verdict": "UNKNOWN",
                   "reason": f"{type(exc).__name__}: {exc}"[:300]}
        logger.exception("[OPS][MONITOR] 감시가 터졌다 — 판정 불가")
        _write_monitor_state(payload)
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
def ops_backup_beat(invoked_by: str = "manual") -> dict:
    """백업을 뜬다 — **켜져 있을 때만.**

    ★ 꺼져 있으면 「건너뛰었다」고 **적고** 돌아간다. 조용히 아무것도 안 하면
      「돌았는데 아무 일 없었다」와 구별되지 않는다 (D-290).
    ★ 이 태스크는 `ops_restore` 를 부르지 않는다. **복구는 사람이 확인하는 일**이고
      (D-354 ① — 복구를 해 보지 않은 백업은 백업이 아니다), 자동 복구는
      운영 DB 를 건드리는 일이라 여기서 하지 않는다.

    ★★ 호출자 칸 — `invoked_by` (P-264 · OPS-19 · 턴 AE 차선 E)
    ------------------------------------------------------------
    지금까지 이 태스크가 남기는 판정문(`D-373/backup_last.json`)에는 **누가 불렀는지가
    없었다.** beat 이 매일 03:00(Ho_Chi_Minh)에 부른 것과 사람이 `gx-shell` 에서
    `ops_backup_beat()` 를 바로 부른 것이 **똑같은 판정문**을 남겼다 — 그래서 사람이
    beat 로그·celery 로그·금고 파일 셋을 대 봐야 「이것이 저절로 돈 것」을 알 수 있었고,
    로그가 회전하면 그 이음이 사라졌다(OPS-19 실측 2026-09-23).

    이 태스크는 **제 손으로 제가 불린 자리를 모른다** — celery 태스크의 실행 컨텍스트에는
    "beat 스케줄러가 발화시켰다" 를 말해 주는 표준 필드가 없다(django_celery_beat 가 넘기는
    `periodic_task_name` 옵션은 태스크 메시지에 실리지 않는다 — 확인함). 그래서 **명시로
    배선한다**: `config/celery.py` 의 `ops-backup-daily` 항목이 `kwargs={"invoked_by": "beat"}`
    를 **직접 건넨다.** 그 kwarg 없이 부르면(사람이 `ops_backup_beat()` 나 `.delay()` 를
    셸에서 바로 부르면) 기본값 `"manual"` 이 판정문에 그대로 남는다.

    ⚠ 이 칸은 **믿음이 아니라 배선**이다 — beat 항목이 이 kwarg 를 빼먹으면 다시
      구별이 안 된다. 그래서 `verify_backup_recovery.py` 의 ㉡ 는 이 칸을 **직접 읽고**,
      금고의 실제 파일과 이름이 맞는지도 대조한다(판정문만 믿지 않는다) — 아래 참조.
    """
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not backup_schedule_enabled():
        payload = {"measured_at": stamp, "verdict": "SKIPPED", "invoked_by": invoked_by,
                   "reason": ("백업 주기가 꺼져 있다 (OPS_BACKUP_SCHEDULE_ENABLED). "
                              "보관처와 보존 기간을 정하는 것은 운영의 판단이고, "
                              "기본값으로 켜면 우리가 남의 디스크에 대해 그것을 정하는 "
                              "일이 된다")}
        logger.info("[OPS][BACKUP] 건너뜀 — %s", payload["reason"])
        return payload

    out_dir = getattr(settings, "OPS_BACKUP_DIR", "") or ""
    if not out_dir:
        payload = {"measured_at": stamp, "verdict": "SKIPPED_UNDECLARED", "invoked_by": invoked_by,
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
        payload = {"measured_at": stamp, "verdict": "UNKNOWN", "invoked_by": invoked_by,
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
        payload = {"measured_at": stamp, "verdict": "UNKNOWN", "invoked_by": invoked_by,
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
        payload = {"measured_at": stamp, "invoked_by": invoked_by,
                   "verdict": "OK" if ok else "UNKNOWN",
                   "reason": "" if ok else ("대조표가 검증 가능하지 않다 — "
                                            "「파일이 생겼다」는 성공이 아니다"),
                   "manifest": manifest, "out_dir": str(target)}
    except Exception as exc:                       # noqa: BLE001
        payload = {"measured_at": stamp, "verdict": "ALARM", "invoked_by": invoked_by,
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

    #: ★★ OPS-07b 의 남은 조건 — **되돌릴 수 없으면 지우지 않는다.**
    #:   dj-core 의 삭제는 하드다(`_base_manager` 는 safedelete 매니저가 아니다).
    #:   그러므로 부르기 **전에** 지워질 행을 저널로 뜬다. 저널을 못 뜨면
    #:   dj-core 를 **호출 0** 으로 두고 돌아선다 — 「지웠는데 되돌릴 수 없다」보다
    #:   「안 지웠다」가 언제나 낫다. 감사 기록은 지운 뒤에 아쉬워할 자료가 아니다.
    from common import audit_purge_journal as journal_mod

    try:
        journal = journal_mod.write_journal(declared)
        #: 저널을 뜬 **직후** 다시 재서, 그 사이 만료선을 넘어간 행을 센다.
        journal["boundary_crossed"] = journal_mod.count_boundary_crossed(
            declared, journal.get("cutoff") or "")
    except Exception as exc:                       # noqa: BLE001
        payload = {"measured_at": stamp, "verdict": "SKIPPED_UNREVERSIBLE",
                   "retention_days": declared,
                   "source": audit_retention_source(),
                   "purged": 0,
                   "journal": {"dir": journal_mod.journal_dir()},
                   "reason": ("되돌림 저널을 뜨지 못했다 — **한 행도 지우지 "
                              "않는다**(호출 0). dj-core 의 삭제는 하드 삭제라 "
                              "저널이 없으면 되돌릴 수 없다(OPS-07b). "
                              f"{type(exc).__name__}: {exc}")[:400]}
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
                   "purged": before - after,
                   "journal": journal,
                   "undo": ("scripts/ops_audit_purge_undo.py --journal "
                            f"{journal.get('path')} --apply"
                            if journal.get("path") else
                            "지운 행이 없어 되돌릴 것도 없다")}
        #: ★ **저널에 없는 행이 지워졌는가** — 이 수를 **정확히** 잰다.
        #:
        #:   `rows_before - rows_after` 로는 못 잰다. 이 표는 살아 있고 다른 쪽이
        #:   그 사이에 감사 줄을 쓴다 — 실제로 한 실행에서 저널 3행을 지웠는데
        #:   `purged` 가 **2** 로 나왔다[실측 2026-09-06 · 그 사이 1행이 들어왔다].
        #:   순증감으로 삭제를 세면 남이 쓴 만큼 틀린다.
        #:
        #:   되돌릴 수 없는 삭제가 생기는 자리는 정확히 하나다: 저널을 뜬 시각과
        #:   dj-core 가 자르는 시각 **사이에 만료선을 넘어간 행**. 그 창을 그대로
        #:   센다. 창은 밀리초이고 그 행은 이미 365일 지난 행이라 거의 언제나 0이지만,
        #:   **0일 것 같은 것을 0이라고 적지 않는다** (D-301).
        crossed = int(journal.get("boundary_crossed") or 0)
        payload["unjournaled_deletes"] = crossed
        if crossed > 0:
            payload["verdict"] = "ALARM"
            payload["reason"] = (
                f"저널에 없는 행 {crossed}건이 지워졌다 — 저널을 뜬 뒤 dj-core 가 "
                "자르기 전 사이에 만료선을 넘어간 행이다. 그만큼은 되돌릴 수 없다")
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


# ═══════════════════════════════════════════════════════════════════════════
# 턴 U · 차선 U56 — **저장 상한 선언**과 **백업 회수증**. 판정은 여기 하나다 (D-212)
# ═══════════════════════════════════════════════════════════════════════════
#
# 왜 화면이 아니라 여기인가 — `scripts/ops_monitor.py` 와 `GET /api/dsm/system/*` 가
# **같은 질문**을 한다(「몇 % 찼나」 · 「마지막 회수증은 언제인가」). 두 자리에서
# 따로 판정하면 크론이 UNKNOWN 이라고 적는 날 화면은 초록을 그린다.

#: 저장 상한을 **선언하는 유일한 자리**. 환경이다 — DB 가 아니다(선등록 ② 원칙).
STORAGE_CAPACITY_ENV = "GX_STORAGE_CAPACITY_GB"

#: 상한이 없을 때 화면·크론이 **똑같이** 말해야 하는 문장. 두 벌로 적지 않는다.
STORAGE_UNDECLARED_SENTENCE = (
    "용량 상한이 선언되지 않았습니다 (%s) — 분모 없이 「몇 %% 찼나」에 답하지 "
    "않습니다 (D-301)." % STORAGE_CAPACITY_ENV)

#: ★★ [P-177 · 턴 V · 차선 U56] **분모와 분자가 같은 것을 재는가.**
#:
#: [실측 2026-09-18] 상한은 선언값 `GX_STORAGE_CAPACITY_GB` 이고, 사용량은
#: `storage_used_gb()` 가 **객체저장 버킷 하나**를 합친 수다. 둘은 **같은 그릇이 아니다** —
#: 그런데 화면은 그 둘로 나눈 `used_pct` 만 굵게 보여 주고 있었고, 그 수는 0.0% 였다.
#: 0.0% 는 「거의 안 찼다」로 읽히지만 실제로는 **「다른 것을 나눴다」**이다.
#:
#: 그래서 판정 옆에 **무엇을 나눈 수인지**를 같이 낸다. 수를 바꾸지 않는다 —
#: 수를 고치는 것은 상한의 뜻을 정하는 일이고 그것은 대표 결정이다(창 2).
#: 여기서 하는 일은 **말하지 않던 것을 말하게** 하는 것뿐이다.
STORAGE_CAPACITY_NOTE = (
    "상한은 **선언값**입니다(잰 값이 아닙니다) — %s 에 사람이 적은 수입니다. "
    "사용량은 객체저장 버킷 합계라 상한과 **같은 그릇을 재지 않습니다**. "
    "그래서 이 %%는 「디스크가 몇 %% 찼나」가 아니라 「선언한 상한 대비 객체저장이 "
    "얼마나 쓰는가」입니다." % STORAGE_CAPACITY_ENV)


def storage_capacity_gb() -> float:
    """선언된 상한(GB). **선언이 없으면 0** 이고 0 은 「무제한」이 아니라 「모른다」다."""
    try:
        return float(os.environ.get(STORAGE_CAPACITY_ENV, "") or
                     getattr(settings, "GX_STORAGE_CAPACITY_GB", "") or 0)
    except (TypeError, ValueError):
        return 0.0


def storage_capacity_source() -> str:
    """이 수를 **누가 어디에 적었는가.** 값이 아니라 **출처**다 (턴 W · WS-26 · P-177).

    ★ 왜 값만으로는 모자란가: 화면이 `50 GB` 만 보여 주면 그 수가 **누가 정한
      선언**인지 **코드가 지어낸 기본값**인지 구별되지 않는다. 「설정은 기본값이
      아니라 선언이다」 — 그래서 화면은 수 옆에 **어디서 온 수인지**를 함께 낸다.
    ★ 값은 여기서 바꾸지 않는다. 이 턴에 `.env*` 세 벌은 전부 **50 그대로**다
      (세종 이의 #2 · `docs/agent/evidence/P-177/저장상한_200_이의_20260918.md`).
    """
    if os.environ.get(STORAGE_CAPACITY_ENV, ""):
        return "환경 선언 — %s (컨테이너 환경에 적혀 있습니다)" % STORAGE_CAPACITY_ENV
    if getattr(settings, STORAGE_CAPACITY_ENV, ""):
        return ("설정 선언 — settings.%s (환경에는 없고 설정 파일이 들고 있습니다)"
                % STORAGE_CAPACITY_ENV)
    return "선언 없음 — %s 에 아무도 수를 적지 않았습니다" % STORAGE_CAPACITY_ENV


def storage_used_gb():
    """객체저장이 실제로 쓰는 용량(GB). **못 재면 `(None, 사유)`** — 0 이 아니다."""
    try:
        from minio import Minio

        endpoint = str(getattr(settings, "MINIO_ENDPOINT", "") or "")
        for scheme in ("http://", "https://"):
            if endpoint.startswith(scheme):
                endpoint = endpoint[len(scheme):]
        bucket = getattr(settings, "MINIO_STORAGE_MEDIA_BUCKET_NAME", "")
        # ★ **시간 상한 없이 밖을 부르지 않는다**(W0-17 · 커밋 게이트가 잡았다).
        #   이 함수는 화면(U5 저장 용량)과 크론이 함께 부른다 — 객체저장이 대답하지 않으면
        #   상한이 없는 호출은 **화면을 통째로 세운다**. 집계는 「못 셌다」로 끝나면 되는 일이다.
        #   자는 맥박 접속(`stream_monitors/utils/minio_client.py::_probe_client`)과 같은 결이다.
        import urllib3

        client = Minio(endpoint.rstrip("/"),
                       access_key=settings.MINIO_ACCESS_KEY,
                       secret_key=settings.MINIO_SECRET_KEY,
                       secure=bool(getattr(settings, "MINIO_USE_HTTPS", False)),
                       http_client=urllib3.PoolManager(
                           timeout=urllib3.Timeout(
                               connect=float(getattr(settings, "MINIO_STORAGE_CONNECT_TIMEOUT", 3.0)),
                               read=float(getattr(settings, "MINIO_STORAGE_READ_TIMEOUT", 10.0)))))
        total = sum(obj.size or 0 for obj in client.list_objects(bucket, recursive=True))
        # ⚠ 버킷 이름은 비밀이 아니지만 접속점·자격은 **절대 나가지 않는다**.
        return round(total / (1024 ** 3), 4), "객체저장 버킷 합계"
    except Exception as exc:                        # noqa: BLE001
        return None, "저장소 사용량을 못 셌습니다: %s" % type(exc).__name__


def storage_declaration() -> dict:
    """★ **하나의 판정.** 상한 · 사용량 · % — 셋 중 못 잰 것은 `null` 이고 UNKNOWN 이다.

    화면(`GET /api/dsm/system/storage`)과 크론(`scripts/ops_monitor.py`)이 **이
    함수 하나**를 읽는다. 「상한 미선언」과 「사용량을 못 쟀다」는 다른 사실이라
    사유 문장도 둘로 둔다 — 뭉치면 관리자는 상한을 선언하고도 여전히 회색을 본다.
    """
    capacity = storage_capacity_gb()
    used, used_note = storage_used_gb()
    declared = capacity > 0
    if not declared:
        return {"declared": False, "capacity_gb": None, "used_gb": used,
                "used_pct": None, "verdict": "UNKNOWN",
                "reason": STORAGE_UNDECLARED_SENTENCE, "used_note": used_note,
                "env_name": STORAGE_CAPACITY_ENV,
                "capacity_source": storage_capacity_source(),
                "capacity_note": STORAGE_CAPACITY_NOTE}
    if used is None:
        return {"declared": True, "capacity_gb": capacity, "used_gb": None,
                "used_pct": None, "verdict": "UNKNOWN",
                "reason": used_note, "used_note": used_note,
                "env_name": STORAGE_CAPACITY_ENV,
                "capacity_source": storage_capacity_source(),
                "capacity_note": STORAGE_CAPACITY_NOTE}
    return {"declared": True, "capacity_gb": capacity, "used_gb": used,
            "used_pct": round(used / capacity * 100, 2), "verdict": "OK",
            "reason": "", "used_note": used_note,
            "env_name": STORAGE_CAPACITY_ENV,
            "capacity_source": storage_capacity_source(),
            "capacity_note": STORAGE_CAPACITY_NOTE}


#: 회수증(대조표)을 찾는 뿌리. `/backup` 은 P-67 이 정한 별도 볼륨이다.
BACKUP_RECEIPT_ROOT_ENV = "GX_BACKUP_ROOT"
#: 대조표 파일 이름 — `scripts/ops_backup.py` 가 쓰는 그 이름이다(두 벌로 적지 않는다).
BACKUP_MANIFEST_NAME = "manifest.json"


def backup_receipt_roots() -> list:
    """대조표를 찾아볼 자리들. 앞이 정본(`/backup`)이고 뒤는 증거 폴더다."""
    roots = []
    declared = (os.environ.get(BACKUP_RECEIPT_ROOT_ENV, "") or
                getattr(settings, "OPS_BACKUP_DIR", "") or "/backup")
    roots.append(str(declared))
    evidence = getattr(settings, "OPS_BACKUP_EVIDENCE_DIR", "")
    if evidence:
        roots.append(str(evidence))
    return roots


def _manifest_is_verifiable(manifest: dict) -> bool:
    """이 회수증으로 **복구 성공을 판정할 수 있는가.** `ops_backup.manifest_is_verifiable`
    과 같은 규칙이다 — 파일만 있고 증인 표의 행 수가 없으면 못 한다."""
    db = manifest.get("db") or {}
    if not db.get("file"):
        return False
    rows = db.get("rows") or {}
    return any(value is not None for value in rows.values())


def backup_receipts(limit: int = 5) -> dict:
    """★ **회수증을 실물로 읽는다.** 없으면 회색이다 — 0 을 초록으로 적지 않는다.

    나가는 것: 시각 · 덤프 **파일 이름** · 검증 가능 여부 · 다음 예정.
    나가지 않는 것: `db_settings`(호스트·계정·포트) · 경로 전체 · 해시 전문 —
    이 응답은 관리자 화면이 읽지만, 회수증의 접속 정보는 화면이 알 일이 아니다.
    """
    found = []
    roots_seen = []
    for root in backup_receipt_roots():
        base = Path(root)
        roots_seen.append({"path": str(base), "exists": base.is_dir()})
        if not base.is_dir():
            continue
        candidates = [base / BACKUP_MANIFEST_NAME]
        try:
            candidates += sorted(base.glob("*/" + BACKUP_MANIFEST_NAME))
            candidates += sorted(base.glob("*/*/" + BACKUP_MANIFEST_NAME))
        except OSError:                              # noqa: BLE001
            pass
        for path in candidates:
            if not path.is_file():
                continue
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # ⚠ 읽을 수 없는 회수증은 **없는 것보다 나쁘다** — 세어 둔다.
                found.append({"created_at": None, "db_file": None,
                              "verifiable": False, "unreadable": True,
                              "where": path.parent.name})
                continue
            db = body.get("db") or {}
            found.append({
                "created_at": body.get("created_at"),
                "db_file": db.get("file"),
                "bytes": db.get("bytes"),
                "objects": (body.get("objects") or {}).get("objects"),
                "verifiable": _manifest_is_verifiable(body),
                "unreadable": False,
                "where": path.parent.name,
            })
    found.sort(key=lambda row: (row.get("created_at") or ""), reverse=True)
    enabled = backup_schedule_enabled()
    return {
        "roots": roots_seen,
        "receipts_found": len(found),
        "last": found[0] if found else None,
        "recent": found[:limit],
        "schedule_enabled": enabled,
        #: ★ 꺼져 있으면 **말로** 적는다. 「다음 예정 없음」만으로는 「아직 안 정했다」와
        #:   「꺼 두기로 했다」가 구별되지 않는다.
        "next_run": ("주기가 켜져 있습니다 — 다음 예정은 beat 일정이 정합니다."
                     if enabled else "예정 없음 — 꺼짐 (OPS_BACKUP_SCHEDULE_ENABLED)"),
        "verdict": "OK" if found else "UNKNOWN",
        "reason": "" if found else (
            "회수증(대조표)을 한 장도 못 찾았습니다 — 백업이 0건이라는 뜻이 아니라 "
            "이 자리에서 읽히지 않는다는 뜻입니다. 0 을 초록으로 적지 않습니다."),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 턴 W · 차선 U56 — **백업 선언을 읽는 자리** (`GET /api/dsm/ops/backup/declaration`)
# ═══════════════════════════════════════════════════════════════════════════
#
# ★ 왜 이 함수가 필요했나 [실측 2026-09-19]: `/dsm/system` 화면은 이 경로를 **처음부터
#   부르고 있었고** 서버에는 그 문이 없었다 — 404 다(U5-BACKUP-404 · P-74 §199 ·
#   UX-WALK `walk_20260919T062846.json`). 화면은 그 404 를 빨강이 아니라
#   **「백엔드 신호 대기」** 회색으로 그려 두었다. 즉 **선언은 서 있는데 아무도 못 읽는
#   상태**가 넉 달째였다. 이 함수가 그 회색을 없앤다.
# ★ **선언을 읽을 뿐 값을 정하지 않는다.** P-67 그대로 — 코드 기본값은 없다. 못 읽으면
#   `declared: False` 이고 빈 문자열이다(0·"매일 03:00" 같은 것을 지어내지 않는다).
# ★ 일정은 **beat 표에서 읽는다**(`config/celery.py`). 문서에 적힌 「매일 03:00」을 손으로
#   옮겨 적으면 beat 를 옮긴 날 화면만 옛 시각을 말한다 — 「분모는 손으로 적지 않는다」.

#: 백업을 선언하는 이름들. **화면이 이 이름을 그대로 보여 준다**(설정은 기본값이 아니라
#: 선언이다 — 이름을 감추면 다음 사람이 어디를 고칠지 못 찾는다).
BACKUP_DECLARATION_ENVS = (
    "OPS_BACKUP_SCHEDULE_ENABLED", "OPS_BACKUP_DIR",
    "OPS_BACKUP_RETENTION_DAYS", "OPS_RESTORE_DRILL_ENABLED")


def _beat_schedule_text(task_name: str) -> str:
    """beat 표에 적힌 그 태스크의 주기를 **사람 말로**. 못 읽으면 빈 문자열이다.

    ★ 지어내지 않는다 — 표에 그 태스크가 없으면 「등록 안 됨」이고, 그것은
      「꺼짐」과도 「매일 03:00」과도 다른 사실이다.
    """
    try:
        from config.celery import app as celery_app

        for entry in (celery_app.conf.beat_schedule or {}).values():
            if entry.get("task") != task_name:
                continue
            sched = entry.get("schedule")
            hour = sorted(getattr(sched, "hour", []) or [])
            minute = sorted(getattr(sched, "minute", []) or [])
            dow = sorted(getattr(sched, "day_of_week", []) or [])
            dom = sorted(getattr(sched, "day_of_month", []) or [])
            if len(hour) != 1 or len(minute) != 1:
                return str(sched)
            clock = "%02d:%02d" % (hour[0], minute[0])
            if len(dow) == 1:
                names = "일월화수목금토"
                return "주 1회 %s요일 %s" % (names[dow[0] % 7], clock)
            if len(dom) == 1:
                return "매월 %d일 %s" % (dom[0], clock)
            return "매일 %s" % clock
    except Exception as exc:                        # noqa: BLE001 — 표를 못 읽어도 화면은 산다
        logger.warning("[OPS][BACKUP] beat 표를 못 읽었다 (%s): %s", task_name,
                       type(exc).__name__)
    return ""


def backup_declaration() -> dict:
    """백업 **목적지 · 일정 · 보존 기간 · 복구 시험**의 선언. 없으면 「미선언」이다.

    나가는 것: 선언된 **값과 그 이름**, 그리고 누가 선언했는가(`source`).
    나가지 않는 것: 호스트·자격·경로 전문 — 목적지는 컨테이너 안의 마운트 지점
    (`/backup`)이라 그 자체는 비밀이 아니지만, 그 밖은 한 자도 싣지 않는다.
    """
    out_dir = str(getattr(settings, "OPS_BACKUP_DIR", "") or "")
    enabled = backup_schedule_enabled()
    beat = _beat_schedule_text("common.ops_backup_beat")
    drill_on = bool(getattr(settings, "OPS_RESTORE_DRILL_ENABLED", False))
    drill_beat = _beat_schedule_text("common.ops_restore_drill_beat")
    #: ★ [턴 X · U56 · 조율자 지적] 여기에 **기본 `0` 이 있었다**(턴 W 에 내가 넣었다).
    #:   `verify_retention_declared.py` ⑤ 가 그것을 빨강으로 잡았고 그 판정이 옳다:
    #:   보존 일수는 **되돌릴 수 없는 삭제**를 모는 수라, 「아무도 안 정했다」와
    #:   「0일로 정했다」가 같은 칸에 보이면 안 된다. `0 or 0` 은 미선언을 **수로 위장**한다.
    #:   ⚠ 고치는 자리를 `settings` 로 옮기지 않았다 — 기본값을 옮기는 것은 없애는 것이
    #:   아니고, 같은 판정기가 다음 턴에 그 자리에서 다시 빨개진다.
    #:   규약의 원본은 `apps/dsm/retention.retention_days()` 다 — 미선언이면 `None`.
    raw = getattr(settings, "OPS_BACKUP_RETENTION_DAYS", None)
    if raw is None or raw == "":
        days = None                     # **선언 없음.** 0 이 아니다
    else:
        try:
            days = int(raw)
        except (TypeError, ValueError):
            #: 선언은 있는데 수가 아니다 — 그것도 「선언 없음」이지 0 이 아니다.
            logger.warning("[OPS][BACKUP] OPS_BACKUP_RETENTION_DAYS 가 수가 아니다 "
                           "(%s) — 미선언으로 읽는다", type(raw).__name__)
            days = None

    #: ★ 「켜져 있다」와 「언제 도는지 안다」는 다른 사실이다 — 둘을 한 칸에 두지 않는다.
    if enabled:
        schedule = ("%s (beat: common.ops_backup_beat)" % beat if beat else
                    "켬 — 그런데 beat 표에 등록이 없습니다 (common.ops_backup_beat)")
    else:
        schedule = ""
    if drill_on:
        drill = ("%s (beat: common.ops_restore_drill_beat)" % drill_beat if drill_beat
                 else "켬 — 그런데 beat 표에 등록이 없습니다 (common.ops_restore_drill_beat)")
    else:
        drill = ""

    #: `days is not None and days > 0` — **`None` 과 `0` 을 갈라 읽는다.**
    #: 둘 다 「선언 안 됨」으로 끝나지만 사유가 다르고, 사유는 아래 `reason` 이 말한다.
    declared = bool(out_dir) and enabled and (days is not None and days > 0)
    return {
        "declared": declared,
        "destination": out_dir,
        "schedule": schedule,
        "schedule_enabled": enabled,
        #: ★ `days or None` 이었다 — 그러면 **누군가 0 을 선언한 것**과 **아무도 선언하지
        #:   않은 것**이 화면에서 같은 칸(`null`)이 된다. 그 둘은 다른 사실이다.
        #:   그대로 낸다: `None` = 선언 없음 · `0` = 0 일로 선언됨(그리고 `declared` 는 거짓).
        "retention_days": days,
        "restore_drill": drill,
        "restore_drill_enabled": drill_on,
        #: 누가 정했는가. 선언이 없는 환경에서는 그 말을 그대로 낸다(P-67).
        "source": str(getattr(settings, "RETENTION_DECLARATION_SOURCE", "") or
                      "선언 없음 — 고객이 U5 설정 화면에서 선언한다"),
        #: **이름을 숨기지 않는다.** 고칠 자리를 화면이 말해 준다.
        "env_names": list(BACKUP_DECLARATION_ENVS),
        "verdict": "OK" if declared else "UNDECLARED",
        #: 빈 칸을 **이름으로** 센다. 「완전하지 않다」만 말하면 어디가 빈지 코드를 읽어야 한다.
        "reason": "" if declared else (
            "백업 선언이 완전하지 않습니다 — 아직 아무도 정하지 않은 칸: %s. "
            "기본값을 지어내지 않습니다: 어디에 얼마나 오래 쌓을지는 운영의 "
            "판단입니다 (P-67). 고칠 자리의 이름: %s."
            % (" · ".join(
                ([] if out_dir else ["목적지"])
                + ([] if enabled else ["주기(꺼져 있음)"])
                + (["보존 일수(**선언 없음**)"] if days is None else
                   (["보존 일수(0 일로 선언됨 — 0 은 보존하지 않는다는 뜻이라 "
                     "선언으로 치지 않습니다)"] if days <= 0 else []))
               ) or ["(없음 — 위 칸은 다 찼는데 선언이 아닙니다)"],
               ", ".join(BACKUP_DECLARATION_ENVS))),
    }


@shared_task(name="common.monthly_report_beat")
def monthly_report_beat() -> dict:
    """UX-40 — **매월 1일 03:00, 조직마다 「이번 달 우리 센터」 한 행**(턴 U · 차선 U24 + 조율자).

    ★ 왜 배치가 만드는가 — **재난안전과(U4)는 스스로 못 만든다.** `view_only_*` 는 플랫폼
      문지기가 쓰기를 403 으로 끊는다(U24 실측). 그래서 이 자리의 규약은 「사람이 누르면
      만들어진다」가 아니라 **「배치가 만들어 두고 사람은 내려받는다」**다. 이 태스크가
      꺼지면 U4 의 월간 보고는 **조용히 사라진다** — 그래서 등재를 코드에 남긴다.
    ★ 한 조직이 실패해도 다음 조직을 계속한다(`run_monthly_all`) · 실패도 **행으로** 남는다
      (`status=failed` + 사유). 0건을 「없었다」로 읽지 않기 위해서다.
    ★ `trigger=auto` 가 남는다 — 사람이 만든 것과 배치가 만든 것을 표가 갈라 보인다(PRD §7.4).
    """
    from apps.dsm.monthly_report import run_monthly_all

    runs = run_monthly_all()
    ok = sum(1 for r in runs if getattr(r, "status", "") == "succeeded")
    payload = {"organizations": len(runs), "succeeded": ok, "failed": len(runs) - ok}
    if payload["failed"]:
        logger.warning("[U24-REPORT] 월간 자동본 실패 %d건 — 조직 %d 중",
                       payload["failed"], payload["organizations"])
    else:
        logger.info("[U24-REPORT] 월간 자동본 %d건", ok)
    return payload
