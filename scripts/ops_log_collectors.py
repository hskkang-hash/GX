#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07 — **수집기 자체를 잰다.** 로그가 어디에 쌓이고 언제 지워지는가 (2026-09-04 · E3).

    OPS-07 로그 수집·보존 기간 — "**수집기 자체를 안 쟀다**"
        — docs/agent/remaining_40.md 43행

왜 「보존 기간」만으로는 절이 안 서나
------------------------------------
이 저장소에는 보존 기간이 **하나** 서 있다: 감사 로그(`ops_audit_purge_beat`,
매일 03:10, 고객이 정한 `security.audit_log_retention_days`). 그것을 근거로
「보존 기간이 있다」고 적으면 **거짓말이 된다** — 그 하나가 전부인지 아무도 안 봤기
때문이다. 절은 「어떤 수집기에 보존 기간이 있는가」가 아니라
**「보존 기간이 없는 수집기가 있는가」** 로 서야 한다.

그래서 이 판정기는 **수집기를 전수로 세는 것부터** 한다:

    ① 컨테이너 stdout   도커 `json-file` 드라이버. 컨테이너마다 하나씩
    ② DB 감사 로그      `logger_auditlogs` — 미들웨어가 `db` 로거로 밀어 넣는다
    ③ 파일              `settings.LOGGING` 의 파일 핸들러

그리고 각각에 대해 **자라는 속도**와 **지우는 자리**를 따로 잰다.
「쌓인다」와 「지워진다」는 다른 사실이고, 앞만 재면 디스크가 정책을 대신 정한다
(D-356 ④ · `ops_backup.py` 가 같은 말을 백업 쪽에서 했다).

★ 속도는 **한 시간 치를 재서 하루로 환산한다** — 총량이 아니라
------------------------------------------------------------
컨테이너 로그의 총량은 「그 컨테이너가 언제 떴는가」에 따라 달라진다. 그 수로는
"내일 얼마나 늘어날지"를 못 말한다. `docker logs --since 60m` 의 바이트가
**지금 이 시스템이 로그를 만드는 속도**이고, 보존 정책은 그 속도 위에서 정해진다.

    ⚠ 환산은 [추정]이다. 이 판정기는 실측(한 시간 치)과 추정(하루 치)을 **갈라서** 적는다.

    python scripts/ops_log_collectors.py --evidence docs/agent/evidence/OPS-07/collectors.md
    python scripts/ops_log_collectors.py --self-test     # 판정 규칙만 (도커 없이)

종료 코드: 0 전수를 쟀고 보존 기간이 다 있다 · 1 쟀고 **없는 수집기가 있다** ·
          2 못 쟀다(도커·DB 없음). 회색은 초록이 아니다.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 이 제품이 띄우는 컨테이너들. **여기 없는 컨테이너는 세지 않는다** — 남의 것을
#: 우리 수집기로 세면 수가 부풀고, 부푼 수 위에서 정한 정책은 틀린다.
PROJECT_CONTAINERS = ("gx-shell", "postgres", "redis",
                      "guardianx-source-minio-1", "gx-fe-build")

#: DB 쪽 사실을 물어볼 자리. dj-core 가 여기에만 있다.
APP_CONTAINER = "gx-shell"

#: 한 시간 치를 잰다. 이보다 짧으면 조용한 순간에 걸려 0 이 나오고,
#: 길면 판정기 한 번 도는 데 오래 걸린다.
WINDOW_MINUTES = 60


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list[tuple[str, bool, str]]:
    out = []
    sinks = facts.get("sinks")
    if sinks is None:
        return [("① 수집기 전수", False, "**못 쟀다** — 도커에 닿지 못했다"),
                ("② 보존 기간", False, "못 쟀다"),
                ("③ 자라는 속도", False, "못 쟀다")]

    unknown = [s["name"] for s in sinks if s.get("retention") is None]
    out.append(("① 수집기 전수", not unknown,
                "수집기 %d개를 전수로 셌다" % len(sinks) if not unknown
                else "보존 정책을 **못 읽은** 수집기: %s" % ", ".join(unknown)))

    forever = [s["name"] for s in sinks if s.get("retention") == "무한"]
    out.append(("② 보존 기간", not forever,
                "%d개 전부에 보존 기간이 있다" % len(sinks) if not forever
                else "**보존 기간이 없다**(무한 적재): %s" % ", ".join(forever)))

    unmeasured = [s["name"] for s in sinks if s.get("bytes_per_hour") is None]
    out.append(("③ 자라는 속도", not unmeasured,
                "%d개의 한 시간 치를 쟀다" % len(sinks) if not unmeasured
                else "속도를 **못 잰** 수집기: %s" % ", ".join(unmeasured)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 수집
# ═══════════════════════════════════════════════════════════════════════════
def docker(*args: str, timeout: int = 300, binary: bool = False):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    p = subprocess.run(["docker", *args], capture_output=True, timeout=timeout, env=env)
    if binary:
        return p.returncode, p.stdout, p.stderr
    return (p.returncode,
            p.stdout.decode("utf-8", "replace").strip(),
            p.stderr.decode("utf-8", "replace").strip())


def container_sinks() -> list[dict]:
    sinks = []
    for name in PROJECT_CONTAINERS:
        rc, out, _ = docker("inspect", name, "--format", "{{json .HostConfig.LogConfig}}")
        if rc != 0:
            continue
        try:
            cfg = json.loads(out)
        except ValueError:
            cfg = {}
        opts = cfg.get("Config") or {}
        driver = cfg.get("Type")
        max_size, max_file = opts.get("max-size"), opts.get("max-file")
        if driver == "json-file" and not max_size:
            # ★ `max-size` 가 없으면 도커는 **자르지 않는다.** 디스크가 찰 때까지 쌓인다.
            retention = "무한"
            detail = "드라이버 %s · max-size 없음 · max-file 없음" % driver
        elif driver == "json-file":
            retention = "%s × %s" % (max_size, max_file or "1")
            detail = "드라이버 %s · 회전 %s" % (driver, retention)
        elif driver in ("none",):
            retention = "0 (수집 안 함)"
            detail = "드라이버 none — 로그를 버린다"
        else:
            retention = None                    # 모르는 드라이버는 **모른다**고 적는다
            detail = "드라이버 %s — 이 판정기가 모르는 드라이버다" % driver

        rc, blob, _ = docker("logs", "--since", "%dm" % WINDOW_MINUTES, name,
                             binary=True)
        per_hour = len(blob) if rc == 0 else None
        sinks.append({"name": "컨테이너 stdout · %s" % name,
                      "kind": "docker", "retention": retention,
                      "detail": detail, "bytes_per_hour": per_hour})
    return sinks


#: gx-shell 안에서 돌 조각. **DB 에 직접 묻는다** — 화면이나 요약을 믿지 않는다.
DB_PROBE = r'''
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
out = {}
try:
    from core.logger.models import AuditLogs
    tab = AuditLogs._meta.db_table
    with connection.cursor() as c:
        c.execute("SELECT count(*) FROM %s" % tab); out["rows"] = c.fetchone()[0]
        c.execute("SELECT pg_total_relation_size(%s)", [tab]); out["bytes"] = c.fetchone()[0]
        # ★ 시각 칸의 이름을 **짐작하지 않는다** — 정보 스키마에게 묻는다.
        #   [실측 2026-09-04] 이 표의 시각 칸은 `create_datetime` 하나뿐이고,
        #   `created_on` 을 짐작한 첫 판은 조용히 0행을 셌다.
        c.execute("SELECT column_name FROM information_schema.columns "
                  "WHERE table_name=%s AND data_type LIKE 'timestamp%%'", [tab])
        cols = [r[0] for r in c.fetchall()]
        for pref in ("create_datetime", "created_on", "created_at"):
            if pref in cols:
                out["time_col"] = pref
                break
        else:
            out["time_col"] = cols[0] if cols else None
        out["time_col_candidates"] = cols
        if out["time_col"]:
            col = out["time_col"]
            c.execute('SELECT min("%s"), max("%s") FROM %s' % (col, col, tab))
            lo, hi = c.fetchone()
            out["oldest"], out["newest"] = str(lo), str(hi)
            c.execute("SELECT count(*) FROM %s WHERE \"%s\" >= now() - interval '1 hour'"
                      % (tab, col))
            out["rows_last_hour"] = c.fetchone()[0]
    out["table"] = tab
except Exception as exc:
    out["error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from core.configuration.utils import get_config_value_by_path
    # ★ 인자 둘이다: (name, fieldpath). dj-core 의 정리 태스크가 부르는 그대로 부른다 —
    #   한 인자로 부르면 TypeError 가 나고, 그 예외를 삼키면 「보존기간 없음」으로 보인다.
    out["retention_days"] = get_config_value_by_path(
        "System", "security.audit_log_retention_days", 90)
except Exception as exc:
    out["retention_days_error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from config.celery import app
    sched = app.conf.beat_schedule or {}
    out["purge_beat"] = {k: str(v.get("schedule")) for k, v in sched.items()
                         if "audit" in k or "audit" in str(v.get("task", ""))}
except Exception as exc:
    out["purge_beat_error"] = "%s: %s" % (type(exc).__name__, exc)

try:
    from django.conf import settings
    out["file_handlers"] = sorted(
        n for n, h in (settings.LOGGING.get("handlers") or {}).items()
        if "FileHandler" in str(h.get("class", "")))
except Exception as exc:
    out["file_handlers_error"] = "%s: %s" % (type(exc).__name__, exc)

print("###JSON###" + json.dumps(out, ensure_ascii=False, default=str))
'''


def db_sink() -> tuple[dict | None, dict]:
    rc, out, err = docker("exec", "-w", "/app", "-e", "PYTHONPATH=/app",
                          "-e", "DJANGO_SETTINGS_MODULE=config.settings",
                          APP_CONTAINER, "python", "-c", DB_PROBE, timeout=300)
    marker = "###JSON###"
    if marker not in out:
        return None, {"error": (err or out)[-300:]}
    try:
        info = json.loads(out.split(marker, 1)[1].strip().splitlines()[0])
    except ValueError as exc:
        return None, {"error": str(exc)}

    if info.get("error"):
        return None, info
    days = info.get("retention_days")
    beat = info.get("purge_beat") or {}
    if days and beat:
        retention = "%s일 (beat %s)" % (days, ", ".join(beat))
    elif days and not beat:
        # ★ 설정은 있는데 도는 자리가 없다 — 착시 ⑨. **무한과 같다.**
        retention = "무한"
    else:
        retention = None
    return {"name": "DB 감사 로그 · %s" % info.get("table", "?"),
            "kind": "db", "retention": retention,
            "detail": "행 %s개 · %s바이트 · 가장 오래된 %s"
                      % (info.get("rows"), info.get("bytes"), info.get("oldest")),
            "bytes_per_hour": info.get("rows_last_hour")}, info


def self_test() -> int:
    ok = True
    ok &= all(not p for _, p, _ in judge({}))

    good = {"sinks": [{"name": "a", "retention": "10m × 3", "bytes_per_hour": 100},
                      {"name": "b", "retention": "90일 (beat x)", "bytes_per_hour": 5}]}
    ok &= all(p for _, p, _ in judge(good))

    forever = {"sinks": [{"name": "a", "retention": "무한", "bytes_per_hour": 100}]}
    r = judge(forever)
    ok &= [p for _, p, _ in r] == [True, False, True]

    unknown = {"sinks": [{"name": "a", "retention": None, "bytes_per_hour": 100}]}
    r = judge(unknown)
    ok &= [p for _, p, _ in r] == [False, True, True]

    blind = {"sinks": [{"name": "a", "retention": "10m × 3", "bytes_per_hour": None}]}
    r = judge(blind)
    ok &= [p for _, p, _ in r] == [True, True, False]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    log: list[str] = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    rc, _, err = docker("version", "--format", "{{.Server.Version}}")
    if rc != 0:
        print("판정 불가(exit 2): 도커에 닿지 못했다 — %s" % err)
        return EXIT_UNDECIDABLE

    say("## 1. 수집기를 전수로 센다")
    say()
    sinks = container_sinks()
    dbs, dbinfo = db_sink()
    if dbs is not None:
        sinks.append(dbs)
    else:
        say("⚠ DB 수집기를 **못 쟀다** — %s" % dbinfo.get("error"))
        say("  「0건」이 아니라 「못 쟀다」다. 못 잰 것을 통과로 적지 않는다(D-301).")
        say()

    say("| 수집기 | 보존 기간 | 한 시간 치 [실측] | 하루 환산 [추정] | 비고 |")
    say("|---|---|---|---|---|")
    for s in sinks:
        per_h = s.get("bytes_per_hour")
        unit = "행" if s.get("kind") == "db" else "바이트"
        say("| %s | %s | %s%s | %s%s | %s |"
            % (s["name"], s.get("retention") or "**모름**",
               format(per_h, ",") if per_h is not None else "못 쟀다", unit if per_h is not None else "",
               format(per_h * 24, ",") if per_h is not None else "—",
               unit if per_h is not None else "",
               s.get("detail", "")))
    say()

    if dbs is not None:
        say("### DB 감사 로그의 자세한 사실")
        say()
        say("```")
        for k in ("table", "time_col", "time_col_candidates", "rows", "bytes",
                  "oldest", "newest", "rows_last_hour", "retention_days",
                  "purge_beat", "file_handlers"):
            if k in dbinfo:
                say("%-22s %s" % (k, dbinfo[k]))
        for k in sorted(dbinfo):                 # 못 읽은 것은 **못 읽었다고** 적는다
            if k.endswith("_error"):
                say("%-22s %s" % (k, dbinfo[k]))
        say("```")
        say()
        fh = dbinfo.get("file_handlers")
        if fh is not None:
            say("★ **파일 수집기는 %d개다.** `settings.LOGGING` 의 핸들러 중 `FileHandler` 는 %s — "
                % (len(fh), fh or "없다"))
            say("  즉 로그 파일이 디스크에 직접 쌓이는 자리는 없고, 전부 stdout 과 DB 로 간다.")
            say("  logrotate 를 찾을 이유가 없다는 뜻이고, 그 사실을 **찾아보고** 적는다.")
            say()

    say("## 2. 판정")
    say()
    facts = {"sinks": sinks}
    rows = judge(facts)
    for name, passed, why in rows:
        say("  %s %-14s %s" % ("OK  " if passed else "FAIL", name, why))
    ok = all(p for _, p, _ in rows)
    say()
    say("판정 **%s** — 통과가 목표가 아니다. **지금 어떤 수집기가 무한히 쌓이는지**를"
        % ("통과" if ok else "실패"))
    say("이 표가 처음으로 말한다. 고칠지 말지는 배포 형상이 정할 일이고, 고치는 자리는")
    say("`docker-compose.yml` 의 `logging.options.max-size`/`max-file` 하나다.")

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-07 — 로그 수집기를 전수로 쟀다 (%s)\n\n"
                        % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_log_collectors.py` 가 실행하며 적었다.**\n"
                        "한 시간 치는 [실측]이고 하루 환산은 [추정]이다 — 갈라서 적었다.\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
