#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-04 판정기 — **복구할 것이 남아 있는가.** (턴 AC · 차선 E · P-236 · WO-05 §9-1)

왜 이 파일이 생겼나
-------------------
    `ops_backup.py` 는 2026-09-09 부터 있었고, `ops_backup_beat` 은 매일 돌았고,
    `backup_last.json` 에는 **ALARM 이 적혀 있었다.** 그런데 **아무 색도 안 났다.**

    대장의 OPS-04 는 `proof:` 만 있고 `gate:` 가 **없었다.** `proof:` 는
    「한 번 해 봤다」는 말이고 `gate:` 는 **「지금도 그런가」를 묻는 술어**다.
    앞엣것만 있으면 절은 한 번 초록이 된 뒤 영원히 초록이다.

    그 사이에 실제로 있었던 일 [실측 2026-09-22 · 턴 AC · 차선 E]:
      · /backup/20260917 ~ 20260921 : 덤프 파일 **30개 · 전부 0 바이트**
      · 바이트가 있는 마지막 정기 덤프 : 20260907T191153 (40MB) — **15일 전**
      · pg_dump 는 `-f` 의 파일을 **먼저 만들고** 판 검사에서 죽는다.
        그래서 `ls` 는 「매일 백업이 있다」고 말하고 크기는 「아무것도 없다」고 말한다.

    ★ 그래서 이 판정기는 **판정문(json)만 읽지 않는다. 금고를 직접 센다.**
      「파일이 생겼다」는 성공이 아니다 — 그 문장은 `ops_backup.py` 머리말에 이미
      있었다. 없던 것은 그것을 **세는 술어**였다.

무엇을 재나 — 넷
----------------
  ㉠ `backup_last.json` 의 판정 — ALARM 이면 빨강
  ㉡ 금고에 **바이트가 있는** 덤프가 최근에 있는가 (0바이트는 덤프가 아니다)
  ㉢ 그 덤프를 **복구해 본 회수증**이 최근에 있는가
     (복구를 해 보지 않은 백업은 백업이 아니다 — D-354 ①)
  ㉣ 0바이트 덤프가 몇 개 남아 있는가 — **있으면 반드시 말한다.**
     이것이 「있는 것처럼 보이는」 모양 자체이기 때문이다.

부르는 방향 — **호스트에서 부른다**
-----------------------------------
    이 파일 안에 `docker exec` 가 있다. 그러므로 **호스트에서** 돈다.
    컨테이너 안에서 부르면 docker 가 없어 회색이 나오고, 그 회색은 뜻이 없다.

        python scripts/verify_backup_recovery.py
        python scripts/verify_backup_recovery.py --self-test

끝값
----
    0 = 초록 (복구할 것이 남아 있다)
    1 = 빨강 (복구할 것이 없거나, 있다고 말만 하고 있다)
    2 = 회색 (못 쟀다 — 초록이 아니다 · D-301)

되돌림: 이 스크립트는 **읽기만** 한다. 뜨지도 지우지도 않는다.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

REPO = Path(__file__).resolve().parents[1]
VERDICT_FILE = REPO / "docs/agent/evidence/D-373/backup_last.json"
DRILL_FILE = REPO / "docs/agent/evidence/D-373/restore_drill_last.json"
RECEIPT_DIR = REPO / "docs/agent/evidence/D-354"

#: 금고. P-67 이 정한 별도 볼륨이다. 컨테이너 밖에서는 이 이름으로만 닿는다.
VAULT_CONTAINER = "gx-celery-e"
VAULT_PATH = "/backup"

#: ★ 한도 — **왜 이 수인가**를 적는다. 안 적으면 다음 사람이 마음대로 늘린다.
#:   백업은 하루 주기다(`ops-backup-daily` 03:00). 하루를 놓치는 것은 사고이고
#:   이틀을 놓치는 것은 **고장**이다. 그래서 이틀을 빨강의 문턱으로 둔다.
FRESH_DUMP_HOURS = 48
#: 복구 시험은 주 1회다(`ops-restore-drill-weekly`). 한 회차를 놓쳐도 다음 회차가
#: 갚을 수 있게 8일을 준다 — P-245 「두 회차 규칙」의 백업판이다.
FRESH_RECEIPT_DAYS = 8
#: 0바이트가 아니라고 부를 최소 크기. pg_dump -Fc 는 빈 DB 라도 이보다 크다.
MIN_DUMP_BYTES = 1024


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(text):
    """ISO 시각을 읽는다. 못 읽으면 None — **0 이 아니라 모른다**이다."""
    if not text:
        return None
    try:
        value = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


# ───────────────────────────────────────────────────────────────────────────
# ㉡㉣ 금고를 직접 센다 — 판정문이 아니라 **바이트**를 본다
# ───────────────────────────────────────────────────────────────────────────
def list_vault(container=VAULT_CONTAINER, path=VAULT_PATH):
    """금고의 덤프를 (이름, 바이트) 로 돌려준다. 못 닿으면 None(회색).

    ★ `find -printf` 를 안 쓴다 — busybox 에는 없다. 없는 기능을 부르면 rc 가
      0 이 아니고, 그것이 「덤프 0개」로 읽히면 **못 잰 것이 빨강으로 둔갑**한다.
    """
    shell = ("find %s -name '*.dump' -type f -exec stat -c '%%s %%n' {} +"
             % path)
    argv = ["docker", "exec", container, "sh", "-c", shell]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return parse_stat_lines(proc.stdout or "")


def parse_stat_lines(text):
    """`stat -c '%s %n'` 의 줄들을 (이름, 바이트) 로 읽는다."""
    rows = []
    for line in text.splitlines():
        parts = line.strip().split(" ", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        rows.append((parts[1], int(parts[0])))
    return rows


def dump_stamp(name):
    """파일 이름에 박힌 시각을 읽는다. 이름이 정본이다 — mtime 은 복사하면 바뀐다."""
    stem = Path(name).stem
    for chunk in stem.split("_"):
        if len(chunk) == 16 and chunk[8] == "T" and chunk.endswith("Z"):
            try:
                return datetime.strptime(chunk, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def judge_vault(rows, now=None):
    """금고 판정. rows 가 None 이면 **회색이지 빨강이 아니다.**"""
    now = now or utcnow()
    if rows is None:
        return {"state": "UNDECIDABLE",
                "why": "금고에 못 닿았다 — docker 가 없거나 컨테이너가 죽었다"}
    empty = [n for n, size in rows if size < MIN_DUMP_BYTES]
    real = [(n, size) for n, size in rows if size >= MIN_DUMP_BYTES]
    newest, newest_at = None, None
    for name, size in real:
        stamp = dump_stamp(name)
        if stamp and (newest_at is None or stamp > newest_at):
            newest, newest_at = name, stamp
    out = {"total": len(rows), "empty": len(empty), "real": len(real),
           "newest": newest, "newest_at": newest_at.isoformat() if newest_at else None,
           "empty_names": empty[:5]}
    if newest_at is None:
        out["state"] = "FAIL"
        out["why"] = ("금고에 **바이트가 있는** 덤프가 하나도 없다 — 0바이트 %d개가 "
                      "덤프처럼 놓여 있다. 「파일이 생겼다」는 성공이 아니다" % len(empty))
        return out
    age = now - newest_at
    out["age_hours"] = round(age.total_seconds() / 3600, 1)
    if age > timedelta(hours=FRESH_DUMP_HOURS):
        out["state"] = "FAIL"
        out["why"] = ("바이트가 있는 가장 최근 덤프가 %.1f시간 전이다 (한도 %dh) — "
                      "정기 백업이 돌지 않고 있다" % (out["age_hours"], FRESH_DUMP_HOURS))
    else:
        out["state"] = "OK"
        out["why"] = "바이트가 있는 덤프가 %.1f시간 전에 있다" % out["age_hours"]
    return out


# ───────────────────────────────────────────────────────────────────────────
# ㉢ 복구 회수증 — **복구를 해 보지 않은 백업은 백업이 아니다**
# ───────────────────────────────────────────────────────────────────────────
def latest_receipt(receipt_dir=RECEIPT_DIR, drill_file=DRILL_FILE, now=None):
    """가장 최근의 **복구 성공** 회수증 시각. 손으로 한 것과 저절로 돈 것 둘 다 본다."""
    now = now or utcnow()
    best, source = None, None
    #: ★ **훑은 건수를 센다.** 「회수증이 없다」와 「볼 자리가 없었다」는 다른 사실이고,
    #:   분모를 말하지 않는 게이트는 게이트가 아니다(D-301).
    scanned = 0
    if receipt_dir.is_dir():
        for path in sorted(receipt_dir.glob("restore_run*.md")):
            scanned += 1
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            #: ★ 「복구 성공」이 안 적힌 문서는 회수증이 아니다. 뜬 기록은 회수증이 아니다.
            if "복구 성공" not in text:
                continue
            for line in text.splitlines():
                if "실행 시각" not in line:
                    continue
                for cell in line.split("|"):
                    stamp = parse_ts(cell.strip())
                    if stamp and (best is None or stamp > best):
                        best, source = stamp, path.name
                break
    if drill_file.is_file():
        try:
            data = json.loads(drill_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        scanned += 1
        if str(data.get("verdict", "")).upper() == "OK":
            stamp = parse_ts(data.get("measured_at"))
            if stamp and (best is None or stamp > best):
                best, source = stamp, drill_file.name
    if best is None:
        return {"state": "FAIL", "source": None, "scanned": scanned,
                "why": "복구 **성공** 회수증이 하나도 없다 — 복구를 해 보지 않은 백업은 백업이 아니다"}
    age = now - best
    out = {"source": source, "at": best.isoformat(), "scanned": scanned,
           "age_days": round(age.total_seconds() / 86400, 1)}
    if age > timedelta(days=FRESH_RECEIPT_DAYS):
        out["state"] = "FAIL"
        out["why"] = ("가장 최근 복구 회수증이 %.1f일 전이다 (한도 %d일) — "
                      "두 회차를 내리 놓쳤다" % (out["age_days"], FRESH_RECEIPT_DAYS))
    else:
        out["state"] = "OK"
        out["why"] = "복구 회수증이 %.1f일 전에 있다 (%s)" % (out["age_days"], source)
    return out


# ───────────────────────────────────────────────────────────────────────────
# ㉠ 판정문
# ───────────────────────────────────────────────────────────────────────────
def _read_verdict_raw(path=VERDICT_FILE) -> dict:
    """`backup_last.json` 을 **있는 그대로** 읽는다. 없거나 못 읽으면 `{}` — 지어내지 않는다.

    ★ ㉡(`judge_beat_dump`)이 이 원본을 쓴다 — `invoked_by` 와 `manifest.db.file` 은
      `judge_verdict()` 의 축약된 판정(OK/FAIL/UNDECIDABLE)에는 안 담기던 칸이다.
    """
    try:
        if not path.is_file():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def judge_verdict(path=VERDICT_FILE, now=None):
    now = now or utcnow()
    if not path.is_file():
        return {"state": "UNDECIDABLE",
                "why": "backup_last.json 이 없다 — 기계가 아직 한 번도 안 적었다"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {"state": "UNDECIDABLE", "why": "backup_last.json 을 못 읽었다: %s" % exc}
    verdict = str(data.get("verdict", "")).upper()
    stamp = parse_ts(data.get("measured_at"))
    out = {"verdict": verdict, "at": stamp.isoformat() if stamp else None,
           "reason": str(data.get("reason", ""))[:200],
           #: ★ 호출자 칸(P-264) — 없으면 `None` 이다. 「모른다」와 「manual」은 다른
           #:   말이 아니다: 둘 다 「beat 가 불렀다고 말하지 않았다」이고, ㉡ 은 둘 다 반려한다.
           "invoked_by": data.get("invoked_by")}
    if verdict == "ALARM":
        out["state"] = "FAIL"
        out["why"] = "기계가 ALARM 을 적었다: %s" % out["reason"]
    elif verdict == "OK":
        out["state"] = "OK"
        out["why"] = "기계가 OK 를 적었다"
    else:
        out["state"] = "UNDECIDABLE"
        out["why"] = "판정이 %r 이다 — 초록이 아니다" % verdict
    return out


# ───────────────────────────────────────────────────────────────────────────
# ㉡ — **마지막 beat 덤프의 나이** (P-264 · P-260 · 턴 AE 차선 E)
# ───────────────────────────────────────────────────────────────────────────
#: 왜 26h 인가 — 백업 주기는 매일 05:00 KST(P-260) 다. 하루를 놓치는 것은 사고이므로
#: 문턱은 하루(24h) + 여유 2h. 옛 ㉡(`judge_vault` 의 state, 48h)은 「덤프가 있냐」만
#: 잴 때의 문턱이었다 — 이제 「beat 가 오늘 불렀냐」를 재므로 이틀치 여유를 둘 이유가 없다.
FRESH_BEAT_DUMP_HOURS = 26


def judge_beat_dump(vault: dict, raw_verdict: dict, now=None) -> dict:
    """㉡ — 마지막 **beat** 덤프의 나이 ≤ 26h.

    ★ 왜 다시 지었나 [실측 2026-09-23 · OPS-19] — 옛 ㉡(`judge_vault` 의 state)은
      「금고에 바이트 있는 덤프가 최근에 있다」만 물었다. 그 술어는 **누가 그 덤프를
      냈는지**를 안 묻는다 — 그래서 사람이 손으로 뜬 덤프도 초록으로 세었다:
      「오늘 이 자동 덤프에도, 어제 손 덤프에도 똑같이 초록을 냈다」
      (`docs/agent/evidence/OPS-19/자동덤프_첫건_20260923.md` §④).

    이 술어는 **셋을 함께** 본다:
      ① 판정문의 `invoked_by` 가 정확히 `"beat"` 인가 — 없거나 `"manual"` 이면 반려.
      ② 그 판정문이 가리키는 덤프 파일 이름이 **금고의 가장 최근(바이트 있는) 덤프와
         같은가** — 판정문만 믿지 않는다. 판정문 이후에 다른 손 덤프가 떴으면 금고의
         "가장 최근"은 그 손 덤프이고, 이름이 달라지므로 여기서 잡힌다.
      ③ 그 순간이 `FRESH_BEAT_DUMP_HOURS` 이내인가.

    ★★ 이 함수의 자기시험은 **음성 대조를 반드시 포함한다**(`self_test()` 참조) —
      「금고에 바이트 있는 최근 덤프가 있어도 판정문이 manual 이면 빨강」이 없으면
      이 함수는 옛 ㉡ 과 똑같이 「손으로 뜬 덤프만 있는 금고」에도 초록을 낼 수 있다.
    """
    now = now or utcnow()
    invoked_by = raw_verdict.get("invoked_by")
    if invoked_by != "beat":
        return {"state": "FAIL", "invoked_by": invoked_by,
                "why": ("판정문의 호출자가 'beat' 가 아니다(%r) — 손으로 뜬 덤프는 "
                        "이 술어를 채우지 못한다(P-264)" % (invoked_by,))}

    newest_at_s = vault.get("newest_at")
    newest = vault.get("newest")
    if not newest_at_s:
        return {"state": "FAIL", "invoked_by": invoked_by,
                "why": "금고에 바이트가 있는 덤프가 없다"}

    dump_file = ((raw_verdict.get("manifest") or {}).get("db") or {}).get("file")
    if dump_file and newest and Path(dump_file).name != Path(newest).name:
        return {"state": "FAIL", "invoked_by": invoked_by,
                "newest_in_vault": Path(newest).name, "dump_file": dump_file,
                "why": ("판정문의 파일(%s)과 금고의 최신 덤프(%s)가 다르다 — "
                        "판정문 이후에 다른 덤프가 떴을 수 있다"
                        % (dump_file, Path(newest).name))}

    newest_at = parse_ts(newest_at_s)
    age_hours = round((now - newest_at).total_seconds() / 3600, 1)
    if age_hours > FRESH_BEAT_DUMP_HOURS:
        return {"state": "FAIL", "invoked_by": invoked_by, "age_hours": age_hours,
                "why": ("beat 가 부른 마지막 덤프가 %.1f시간 전이다 (한도 %dh) — "
                        "정기 백업이 돌지 않고 있다" % (age_hours, FRESH_BEAT_DUMP_HOURS))}
    return {"state": "OK", "invoked_by": invoked_by, "age_hours": age_hours,
            "why": "beat 가 부른 덤프가 %.1f시간 전에 있다" % age_hours}


def count_inputs(rows):
    """분모를 **센다** — 금고 덤프 + 회수증 후보 + 판정문.

    ★ 머리글이 이 수를 말해야 한다(P-204). `deferred:` 로 미루지 않는다 —
      이 분모는 **지금 잴 수 있고**, 잴 수 있는 것을 미루는 것은 모양만 바꾼 면제다(D-350).
    """
    receipts = len(list(RECEIPT_DIR.glob("restore_run*.md"))) if RECEIPT_DIR.is_dir() else 0
    receipts += 1 if DRILL_FILE.is_file() else 0
    vault = 0 if rows is None else len(rows)
    return {"vault": vault, "vault_known": rows is not None,
            "receipts": receipts, "verdict": 1 if VERDICT_FILE.is_file() else 0,
            "total": vault + receipts + (1 if VERDICT_FILE.is_file() else 0)}


def run(now=None, rows=...):
    now = now or utcnow()
    if rows is ...:
        rows = list_vault()
    #: ★ [조율자 교정 · 2026-09-23] 여기(OPS-04 — 「백업이 있고 그것으로 살아나는가」)의
    #:   ㉡ 은 **금고 신선도만** 잰다(원래대로). 「beat 가 불렀는가」는 **다른 질문**
    #:   (OPS-19 — 저절로 도는가·RPO)이고 그 답은 `scripts/verify_backup_autonomy.py`
    #:   가 ㉤ 로 낸다(`judge_beat_dump()` 를 그대로 가져다 쓴다 · D-369). 한 게이트에
    #:   두 물음을 넣었더니 OPS-04 의 참인 답(오늘 복구가 됐다)이 OPS-19 의 빨강에
    #:   덮여 마지막 줄이 세상과 어긋났다(「복구할 것이 없다」— 사실은 있었다) — 그래서
    #:   가른다.
    return {"verdict": judge_verdict(now=now),
            "vault": judge_vault(rows, now=now),
            "receipt": latest_receipt(now=now)}


def report(result) -> int:
    parts = [("㉠ 판정문", result["verdict"]), ("㉡ 금고", result["vault"]),
             ("㉢ 회수증", result["receipt"])]
    mark = {"OK": "초록", "FAIL": "빨강", "UNDECIDABLE": "회색"}
    #: ★ D-301 — **무엇을 몇 건 보았는지 밖으로 말한다.** 금고에 못 닿았으면 그 칸은
    #:   0 이 아니라 **모름**이고, 그때 이 게이트는 초록이 아니라 회색이 된다.
    vault_n = result["vault"].get("total")
    receipt_n = result["receipt"].get("scanned", 0)
    total = (vault_n or 0) + receipt_n + (1 if VERDICT_FILE.is_file() else 0)
    print("[OPS-04] [입력] 모수 %d — 금고 덤프 %s · 회수증 후보 %d · 판정문 %d"
          % (total, "못 셈" if vault_n is None else vault_n, receipt_n,
             1 if VERDICT_FILE.is_file() else 0))
    for label, item in parts:
        print("[OPS-04] %s %s — %s" % (label, mark.get(item.get("state"), "?"),
                                       item.get("why", "")))
    vault = result["vault"]
    if vault.get("empty"):
        print("[OPS-04] ㉣ ★ **0바이트 덤프 %d개**가 금고에 놓여 있다 — "
              "`ls` 는 「백업이 있다」고 말한다. 크기는 아니라고 말한다." % vault["empty"])
        for name in vault.get("empty_names", []):
            print("[OPS-04]      %s" % name)
    states = [item.get("state") for _, item in parts]
    if "FAIL" in states:
        print("[OPS-04] 빨강 — 복구할 것이 남아 있지 않다.")
        return EXIT_FAIL
    if "UNDECIDABLE" in states:
        print("[OPS-04] 회색 — 못 쟀다. **회색은 초록이 아니다.**")
        return EXIT_UNDECIDABLE
    print("[OPS-04] 초록 — 뜬 것이 있고, 그것을 살려 봤다.")
    return EXIT_OK


# ───────────────────────────────────────────────────────────────────────────
# 자기시험 — ★ **음성 대조를 반드시 포함한다.**
#   통과만 보는 자기시험은 「이 판정기가 빨강을 낼 줄 아는가」를 묻지 않는다.
#   ★ 분모를 손으로 넣지 않는다 — 여기 표본은 **모양**이지 분모가 아니다.
# ───────────────────────────────────────────────────────────────────────────
#: ★★ **출생 표본** (D-310) — 이 도구를 만들게 한 **바로 그 사례**다. 합성이 아니다.
#:
#:   [실측 2026-09-22 · 턴 AC] 금고 `/backup` 을 직접 세어 나온 실물이다.
#:   실패한 `pg_dump` 가 **0바이트 덤프 30개**를 남겼고, 바이트가 있는 마지막 덤프는
#:   `20260907T191153`(40MB · 15일 전)이었다. 그런데 대장의 OPS-04 는 `구현 · closed` 로
#:   **1.0 을 상용 점수에 보태고 있었다.**
#:   이 도구가 없었다면 그 상태가 **또 며칠** 조용했을 것이다.
#:
#:   ⚠ 이 표본을 시험에서 빼면 이 도구는 「0바이트만 있는 금고」를 다시 초록으로 낼 수
#:     있다 — 그것이 정확히 이 도구가 태어난 이유다.
BIRTH_SAMPLE_VAULT = (
    ("/backup/20260917/db_database_guardianx_20260917T093511Z.dump", 0),
    ("/backup/20260918/db_database_guardianx_20260918T200000Z.dump", 0),
    ("/backup/20260919/db_database_guardianx_20260919T200000Z.dump", 0),
    ("/backup/20260920/db_database_guardianx_20260920T200000Z.dump", 0),
    ("/backup/20260921/db_database_guardianx_20260921T200000Z.dump", 0),
    ("/backup/20260907/db_database_guardianx_20260907T191153Z.dump", 40_242_094),
)
#: 그날의 판정문. 기계는 **ALARM 을 적고 있었다** — 아무도 안 읽었을 뿐이다.
BIRTH_SAMPLE_VERDICT = {
    "measured_at": "2026-09-21T20:00:00+00:00",
    "verdict": "ALARM",
    "reason": ("RuntimeError: pg_dump 실패: pg_dump: error: aborting because of "
               "server version mismatch; server version: 18.1; pg_dump version: 17.7"),
}


def self_test() -> int:
    now = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
    fresh = "20260922T030000Z"
    old = "20260907T190000Z"
    cases = []

    # ★★ 출생 표본 — 2026-09-22 의 실제 금고. **빨강이어야 한다.**
    birth = judge_vault(list(BIRTH_SAMPLE_VAULT), now)
    cases.append(("★ 출생 표본: 2026-09-22 실제 금고는 빨강이다", birth["state"] == "FAIL"))
    cases.append(("★ 출생 표본: 0바이트 다섯을 세어 말한다", birth["empty"] == 5))
    cases.append(("★ 출생 표본: 바이트 있는 덤프가 15일 전이라 늙었다고 말한다",
                  "시간 전" in birth.get("why", "") and birth["real"] == 1))

    # 양성 1 — 금고에 바이트 있는 최근 덤프
    cases.append(("양성: 최근 덤프에 바이트가 있으면 초록",
                  judge_vault([("/backup/db_x_%s.dump" % fresh, 5_000_000)], now)["state"] == "OK"))
    # ★ 음성 1 — 0바이트만 있으면 **빨강**. 이 턴에 실제로 있었던 모양이다.
    r = judge_vault([("/backup/db_x_%s.dump" % fresh, 0),
                     ("/backup/db_x_20260921T200000Z.dump", 0)], now)
    cases.append(("음성: 0바이트만 있으면 빨강", r["state"] == "FAIL" and r["empty"] == 2))
    # ★ 음성 2 — 바이트는 있는데 늙었으면 빨강
    cases.append(("음성: 바이트가 있어도 15일 전이면 빨강",
                  judge_vault([("/backup/db_x_%s.dump" % old, 40_000_000)], now)["state"] == "FAIL"))
    # ★ 음성 3 — 금고에 못 닿으면 **회색이지 초록도 빨강도 아니다**
    cases.append(("음성: 금고에 못 닿으면 회색",
                  judge_vault(None, now)["state"] == "UNDECIDABLE"))
    # ★ 혼합 — 진짜가 있으면 초록이되 0바이트 개수는 **말한다**
    r = judge_vault([("/backup/db_x_%s.dump" % fresh, 5_000_000),
                     ("/backup/db_x_20260921T200000Z.dump", 0)], now)
    cases.append(("혼합: 진짜가 있으면 초록이되 0바이트 개수를 말한다",
                  r["state"] == "OK" and r["empty"] == 1))
    # 이름에 시각이 없으면 못 읽는다 — 0 이 아니라 모른다
    cases.append(("이름에 시각이 없으면 None", dump_stamp("/backup/whatever.dump") is None))
    # stat 줄 읽기 — busybox 출력 모양
    cases.append(("stat 줄 둘을 읽는다",
                  parse_stat_lines("0 /backup/a.dump\n5000000 /backup/b.dump") ==
                  [("/backup/a.dump", 0), ("/backup/b.dump", 5000000)]))

    #: ★ [조율자 교정 · 2026-09-23] `judge_beat_dump()` 의 자기시험(음성 대조·출생 표본
    #:   포함)은 여기 있지 않다 — **`scripts/verify_backup_autonomy.py`(OPS-19 전용
    #:   게이트)로 옮겼다.** OPS-04(이 파일)와 OPS-19(그 파일)는 다른 물음이고, 한
    #:   게이트가 둘을 같이 답하면 한쪽의 참이 다른 쪽의 빨강에 덮인다(조율자 실측
    #:   2026-09-23 — "복구할 것이 남아있지 않다"고 말했는데 사실은 있었다). `judge_beat_dump()`
    #:   자체는 **여기서 지우지 않았다** — 그 파일이 `import verify_backup_recovery` 로
    #:   가져다 쓴다(D-369 — 같은 물음의 두 벌은 반드시 어긋난다).

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "backup_last.json"
        # ★★ 출생 표본의 판정문 — 기계는 ALARM 을 적고 있었고 아무 색도 안 났다
        p.write_text(json.dumps(BIRTH_SAMPLE_VERDICT), encoding="utf-8")
        cases.append(("★ 출생 표본: 그날의 판정문(ALARM)은 빨강이다",
                      judge_verdict(p, now)["state"] == "FAIL"))
        p.write_text(json.dumps({"verdict": "UNKNOWN",
                                 "measured_at": "2026-09-22T05:00:00+00:00"}), encoding="utf-8")
        cases.append(("음성: 판정문이 UNKNOWN 이면 회색(초록 아님)",
                      judge_verdict(p, now)["state"] == "UNDECIDABLE"))
        cases.append(("음성: 판정문이 없으면 회색",
                      judge_verdict(Path(tmp) / "없다.json", now)["state"] == "UNDECIDABLE"))
        p.write_text(json.dumps({"verdict": "OK",
                                 "measured_at": "2026-09-22T05:00:00+00:00"}), encoding="utf-8")
        cases.append(("양성: 판정문이 OK 면 초록", judge_verdict(p, now)["state"] == "OK"))

        d = Path(tmp) / "D-354"
        d.mkdir()
        nowhere = Path(tmp) / "없다.json"
        (d / "restore_run_x.md").write_text(
            "| 실행 시각 | 2026-09-22T04:37:35+00:00 |", encoding="utf-8")
        cases.append(("음성: 「복구 성공」이 없는 문서는 회수증이 아니다",
                      latest_receipt(d, nowhere, now)["state"] == "FAIL"))
        (d / "restore_run_x.md").write_text(
            "| 실행 시각 | 2026-09-22T04:37:35+00:00 |\n| 판정 | **복구 성공** |",
            encoding="utf-8")
        cases.append(("양성: 「복구 성공」 + 최근 시각이면 초록",
                      latest_receipt(d, nowhere, now)["state"] == "OK"))
        (d / "restore_run_x.md").write_text(
            "| 실행 시각 | 2026-09-01T04:37:35+00:00 |\n| 판정 | **복구 성공** |",
            encoding="utf-8")
        cases.append(("음성: 성공했어도 21일 전이면 빨강",
                      latest_receipt(d, nowhere, now)["state"] == "FAIL"))
        # ★ 음성: 주기 시험이 UNKNOWN 이면 회수증으로 안 센다
        drill = Path(tmp) / "restore_drill_last.json"
        drill.write_text(json.dumps({"verdict": "UNKNOWN",
                                     "measured_at": "2026-09-22T05:00:00+00:00"}),
                         encoding="utf-8")
        cases.append(("음성: 주기 복구시험이 UNKNOWN 이면 회수증이 아니다",
                      latest_receipt(d, drill, now)["state"] == "FAIL"))

    bad = 0
    for label, ok in cases:
        print("  [%s] %s" % ("통과" if ok else "**실패**", label))
        bad += 0 if ok else 1
    print("[SELF-TEST] %d건 중 %d건 실패" % (len(cases), bad))
    return EXIT_OK if bad == 0 else EXIT_FAIL


def _header(rows) -> None:
    """P-107 머리글 — **무엇을 · 어디서 · 무슨 자격으로 재는지 먼저 말한다.**

    ★ [턴 AC · 차선 Q 가 잡아 줬다] 이 파일은 처음에 머리글을 **한 줄도** 안 불렀다.
      `verify_gate_header.py` 가 「세 줄 중 0줄」로 잡았다. 판정기를 새로 지으면서
      판정기의 규약을 어긴 것이다 — **새 게이트가 규약의 예외가 되면 규약이 준다.**
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header          # P-107 — TARGET/AS/SOURCE
    n = count_inputs(rows)
    vault_says = ("금고 덤프 %d" % n["vault"] if n["vault_known"]
                  else "금고에 **못 닿았다**(그 칸은 0 이 아니라 모름 — 이 게이트는 회색이 된다)")
    gate_header(
        __file__,
        target=("호스트 + 컨테이너 «%s» 의 금고 «%s» · 증거 파일 "
                "D-373/backup_last.json · D-373/restore_drill_last.json · D-354/restore_run*.md"
                % (VAULT_CONTAINER, VAULT_PATH)),
        as_=("(계정 없음) — `docker exec` 로 금고를 **읽기만** 한다. "
             "이 파일 안에 docker exec 가 있으므로 **호스트에서** 부른다"),
        source=("살아 있는 금고의 **바이트**와 기계가 쓴 판정문 — "
                "「백업이 있다」는 말이 아니라 파일 크기를 직접 잰다"),
        measured=("금고의 `*.dump` 를 **크기와 함께** 전수 + 회수증 후보 문서 전수 + 판정문 — "
                  "**분모 %d** (%s · 회수증 후보 %d · 판정문 %d). "
                  "「파일이 생겼다」가 아니라 **바이트**를 센다"
                  % (n["total"], vault_says, n["receipts"], n["verdict"])),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="OPS-04 — 복구할 것이 남아 있는가")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true", help="판정을 json 으로도 찍는다")
    args = ap.parse_args()
    #: ★ 머리글은 **자기시험 때도** 찍는다 — `verify_gate_header.py` 가 게이트를 여는
    #:   인자가 `--self-test` 다(`OPEN_ARGS`). 자기시험 뒤에 찍으면 「세 줄 중 0줄」이 된다.
    #: ★ 금고는 **한 번만** 센다 — 머리글이 말한 분모와 판정이 본 분모가 같아야 한다.
    #:   두 번 부르면 그 사이에 파일이 늘어 **말한 수와 잰 수가 갈린다.**
    rows = list_vault()
    _header(rows)
    if args.self_test:
        return self_test()
    result = run(rows=rows)
    rc = report(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return rc


if __name__ == "__main__":
    sys.exit(main())
