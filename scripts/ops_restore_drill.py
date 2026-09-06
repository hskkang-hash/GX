#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-19 — **복구 시험(dry-run)과 RTO 실측** (P-67 · 2026-09-06 · 차선 E).

    **복구를 해 보지 않은 백업은 백업이 아니다** (D-354 ①).
    그리고 **몇 분 걸리는지 모르는 복구는 RTO 가 아니다** (GX-LAW-05 초안 · RTO 30분).

무엇이 이미 있었고 이 파일은 무엇을 더하나
------------------------------------------
    `scripts/ops_restore.py`        있다 — **대조표(manifest)** 를 읽고 행 수를 맞춰 본다.
                                    호스트 파일 경로 위에서 돈다.
    `common/ops_tasks.py::ops_restore_drill_beat`
                                    있다(2026-09-06) — **주 1회** 저절로 돈다.
                                    ⚠ 이 기계에서는 회색이다: 앱 컨테이너의
                                      `pg_restore` 17.7 < 서버 18.1 [실측].

이 파일이 더하는 것은 하나다: **백업이 실제로 사는 자리(도커 볼륨)에서**,
**판이 맞는 클라이언트로**, **시계를 들고** 되살려 본다. 즉 위 둘이 못 서는
자리를 메우는 것이고, 새 술어를 만드는 것이 아니다 — 판정 낱말과 안전 규약은
`ops_restore.py` 의 것을 그대로 쓴다(D-369).

★ 원본을 건드리지 않는다 — 세 겹 (`ops_restore.py` 와 같은 규약)
----------------------------------------------------------------
    · 복구 대상 이름이 원본과 같으면 **시작하지 않는다**
    · 대상 이름은 `restore_check_` 로 시작해야 한다
    · 끝나면 지운다. 실패해도 지운다 (`finally`)
  원본 DB 에는 **읽기 질의만** 던진다(표 수 세기). 쓰기 연결을 열지 않는다.

★ 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다** (⚠ 지시 규약)
--------------------------------------------------------------------
  만드는 것: DB 서버 안의 임시 DB `restore_check_<시각>` 하나. **이 실행이 지운다.**
  쓰는 컨테이너: `--rm` 이라 명령이 끝나면 사라진다.
  건드리지 않는 것: `gx-shell` · `redis` · MinIO · `gx_pgdata` 볼륨 ·
                    그리고 백업 볼륨의 **파일**(읽기만 한다).

★ 못 잰 것을 잰 것으로 세지 않는다
----------------------------------
  객체저장(영상·캡처)은 이 시험에 **안 들어 있다.** DB 만 살아나면 「영상이
  있었다고 말하는 DB」가 된다 — 그 절반은 `ops_restore.py --objects` 의 몫이고,
  이 파일의 판정문에 그 사실을 함께 적는다.

    python scripts/ops_restore_drill.py --self-test
    python scripts/ops_restore_drill.py \
        --evidence docs/agent/evidence/OPS-19/restore_drill_20260906.md

종료 코드: 0 살아났고 RTO 를 쟀다 · 1 쟀는데 어긋났다 · 2 **못 쟀다**(도커·볼륨 없음)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ops_backup_volume import DEST_VOLUME, MOUNT_PATH, container_env  # noqa: E402

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

DB_CONTAINER = "postgres"
TARGET_PREFIX = "restore_check_"

#: SLA 초안(GX-LAW-05)이 약속하려는 수. **판정에 쓰지 않는다** — 이 실행이 이 수를
#: 넘겼다고 SLA 가 서는 것도, 넘었다고 백업이 실패인 것도 아니다. 나란히 적을 뿐이다.
SLA_RTO_MINUTES = 30


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list:
    """`None` 은 **못 쟀다**이지 0 도 거짓도 아니다 (D-301)."""
    out = []

    size = facts.get("dump_bytes")
    if size is None:
        out.append(("① 살릴 백업이 있는가", False, "**못 쟀다** — 덤프를 못 찾았다"))
    else:
        out.append(("① 살릴 백업이 있는가", size > 0,
                    "덤프 %s바이트" % format(size, ",") if size > 0
                    else "0바이트 — 살릴 것이 없다"))

    src, got = facts.get("tables_source"), facts.get("tables_restored")
    if src is None or got is None:
        out.append(("② 살아났는가", False, "**못 쟀다** — 표 수를 세지 못했다"))
    else:
        out.append(("② 살아났는가", got > 0 and got == src,
                    "원본 %d개 · 복구 %d개 — 같다" % (src, got) if got == src
                    else "원본 %d개 · 복구 %d개 — **어긋났다**" % (src, got)))

    rto = facts.get("rto_minutes")
    if rto is None:
        out.append(("③ RTO 를 쟀는가", False,
                    "**못 쟀다** — 재지 않은 수를 약속하면 그것은 종이다"))
    else:
        out.append(("③ RTO 를 쟀는가", True,
                    "**%.2f분** (SLA 초안 목표 %d분 · 이 수는 판정이 아니라 대조다)"
                    % (rto, SLA_RTO_MINUTES)))

    dropped = facts.get("target_dropped")
    if dropped is None:
        out.append(("④ 임시 DB 를 지웠는가", False, "**못 쟀다**"))
    else:
        out.append(("④ 임시 DB 를 지웠는가", bool(dropped),
                    "지웠다" if dropped else
                    "**안 지워졌다** — 사람이 지워야 한다. 남은 DB 는 사고다"))
    return out


def self_test() -> int:
    bad = []
    if any(ok for _, ok, _ in judge({})):
        bad.append("빈 사실에서 초록이 났다")
    good = {"dump_bytes": 9209410, "tables_source": 220, "tables_restored": 220,
            "rto_minutes": 1.2, "target_dropped": True}
    if [ok for _, ok, _ in judge(good)] != [True, True, True, True]:
        bad.append("정상 갈래가 초록이 아니다")
    miss = dict(good, tables_restored=214)
    if [ok for _, ok, _ in judge(miss)] != [True, False, True, True]:
        bad.append("표 수가 어긋난 것을 못 잡는다")
    slow = dict(good, rto_minutes=99.0)
    if [ok for _, ok, _ in judge(slow)] != [True, True, True, True]:
        bad.append("RTO 를 **판정**에 쓰고 있다 — 이 도구는 재기만 한다")
    left = dict(good, target_dropped=False)
    if [ok for _, ok, _ in judge(left)] != [True, True, True, False]:
        bad.append("임시 DB 가 남은 것을 못 잡는다")
    norto = dict(good, rto_minutes=None)
    if [ok for _, ok, _ in judge(norto)] != [True, True, False, True]:
        bad.append("RTO 를 못 쟀는데 초록이다")
    if bad:
        print("[OPS-19] 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):")
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("[OPS-19] 자기시험 통과 — 정상 1 · 음성 4 · 빈 사실 1")
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 도커 심부름
# ═══════════════════════════════════════════════════════════════════════════
def docker(*args: str, timeout: int = 1800):
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"       # Git Bash 가 /backup 을 C:\ 로 바꾸지 않게
    p = subprocess.run(["docker", *args], capture_output=True, text=True,
                       errors="replace", timeout=timeout, env=env)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def psql(creds: dict, dbname: str, sql: str, timeout: int = 600):
    return docker("exec", "-e", "PGPASSWORD=%s" % creds["DB_PASSWORD"], DB_CONTAINER,
                  "psql", "-h", "localhost", "-p", "5432", "-U", creds["DB_USER"],
                  "-d", dbname, "-tAc", sql, timeout=timeout)


def table_count(creds: dict, dbname: str):
    rc, out, _ = psql(creds, dbname,
                      "SELECT count(*) FROM information_schema.tables "
                      "WHERE table_schema='public'")
    return int(out) if rc == 0 and out.isdigit() else None


def main() -> int:
    ap = argparse.ArgumentParser(
        description="OPS-19 복구 시험 — 백업 볼륨에서 되살리고 RTO 를 잰다")
    ap.add_argument("--volume", default=DEST_VOLUME)
    ap.add_argument("--evidence", default=None)
    ap.add_argument("--json", default=None, help="판정 수를 JSON 으로도 남긴다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    log: list = []

    def say(line: str = "") -> None:
        print(line)
        log.append(line)

    rc, _, err = docker("version", "--format", "{{.Server.Version}}", timeout=60)
    if rc != 0:
        print("[OPS-19] **판정 불가(exit 2)** — 도커에 닿지 못했다: %s" % err)
        return EXIT_UNDECIDABLE

    creds = container_env("gx-shell")
    missing = [k for k in ("DB_NAME", "DB_USER", "DB_PASSWORD") if not creds.get(k)]
    if missing:
        print("[OPS-19] **판정 불가(exit 2)** — gx-shell 에서 %s 를 못 읽었다 "
              "(값은 저장소에 없다 · D-204)" % ", ".join(missing))
        return EXIT_UNDECIDABLE

    rc, image, _ = docker("inspect", DB_CONTAINER, "--format", "{{.Config.Image}}",
                          timeout=60)
    if rc != 0 or not image:
        print("[OPS-19] **판정 불가(exit 2)** — %r 컨테이너를 읽지 못했다"
              % DB_CONTAINER)
        return EXIT_UNDECIDABLE

    # ── 백업 볼륨에서 가장 최근 덤프를 고른다 ─────────────────────────────
    rc, listing, err = docker(
        "run", "--rm", "-v", "%s:%s:ro" % (args.volume, MOUNT_PATH), image,
        "sh", "-c", "ls -1t %s/*.dump 2>/dev/null | head -1" % MOUNT_PATH,
        timeout=300)
    dump = (listing or "").strip().splitlines()
    dump = dump[0] if dump else ""
    if rc != 0 or not dump:
        print("[OPS-19] **판정 불가(exit 2)** — 볼륨 %r 에 덤프가 없다. "
              "먼저 `scripts/ops_backup_volume.py` 를 돌린다" % args.volume)
        return EXIT_UNDECIDABLE

    rc, meta, _ = docker(
        "run", "--rm", "-v", "%s:%s:ro" % (args.volume, MOUNT_PATH), image,
        # ⚠ `stat -c %s` 의 `%` 를 두 번 적으면(`%%s`) 셸이 **낱말 그대로** 받는다 —
        #   그러면 크기가 `%s` 로 나오고 판정기는 「못 쟀다」를 낸다 [실측 2026-09-06].
        "sh", "-c", "stat -c %s '{f}'; sha256sum '{f}' | cut -d' ' -f1".format(f=dump),
        timeout=600)
    lines = (meta or "").splitlines()
    dump_bytes = int(lines[0]) if lines and lines[0].isdigit() else None
    dump_sha256 = lines[1] if len(lines) > 1 else ""

    source = creds["DB_NAME"]
    started = datetime.now(timezone.utc)
    target = TARGET_PREFIX + started.strftime("%Y%m%d%H%M%S")
    if target == source or not target.startswith(TARGET_PREFIX):
        print("[OPS-19] 거부 — 복구 대상 이름이 안전 규약을 어겼다")
        return EXIT_UNDECIDABLE

    say("# OPS-19 복구 시험 — **해 봤고, 몇 분인지 쟀다** (P-67 · 2026-09-06)")
    say()
    say("> `scripts/ops_restore_drill.py` 가 만든다 — 손으로 적지 않는다.")
    say()
    say("## 0. 무엇을 만들고 어떻게 지우는가 — **하기 전에 적는다**")
    say()
    say("만드는 것: DB 서버 안의 임시 DB `%s` 하나. **이 실행이 지운다.**" % target)
    say("원본 `%s` 에는 **읽기 질의만** 던진다(표 수 세기). 쓰기 연결을 안 연다."
        % source)
    say("건드리지 않는 것: `gx-shell` · `redis` · MinIO · `gx_pgdata` 볼륨 ·")
    say("백업 볼륨 `%s` 의 파일(읽기 전용으로 붙인다)." % args.volume)
    say()
    say("| | |")
    say("|---|---|")
    say("| 실행 시각 | %s |" % started.isoformat(timespec="seconds"))
    say("| 백업 볼륨 | `%s` → 컨테이너 안 `%s` |" % (args.volume, MOUNT_PATH))
    say("| 덤프 | `%s` · %s bytes |"
        % (dump, format(dump_bytes, ",") if dump_bytes else "?"))
    say("| sha256 | `%s` |" % dump_sha256)
    say("| 뜬 자리 | `%s` 컨테이너 (이미지 `%s`) |" % (DB_CONTAINER, image))
    say()

    facts = {"dump": dump, "dump_bytes": dump_bytes, "dump_sha256": dump_sha256,
             "source_db": source, "target_db": target, "volume": args.volume}
    commands: list = []
    notes: list = []
    dropped = None
    t0 = time.monotonic()
    try:
        rc, _, err = psql(creds, "postgres", 'CREATE DATABASE "%s"' % target)
        commands.append("docker exec %s psql -U *** -d postgres -c "
                        "'CREATE DATABASE \"%s\"'  → rc=%d" % (DB_CONTAINER, target, rc))
        if rc != 0:
            notes.append("임시 DB 를 못 만들었다: %s" % err[:200])
            raise RuntimeError(err[:200])

        # ★ 복구는 **DB 컨테이너 안에서** 돈다 — 판이 서버와 반드시 같다.
        #   백업 볼륨을 그 컨테이너에 붙일 수는 없으므로(재생성이 필요하다),
        #   같은 이미지의 `--rm` 컨테이너가 볼륨을 붙이고 **망을 건너** 복구한다.
        rc, net, _ = docker("inspect", DB_CONTAINER, "--format",
                            "{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}",
                            timeout=60)
        net = (net or "").split()[0] if net else ""
        restore_cmd = ("pg_restore --no-owner --no-privileges -h %s -p 5432 "
                       "-U %s -d %s %s" % (creds.get("DB_HOST") or DB_CONTAINER,
                                           creds["DB_USER"], target, dump))
        rc, out, err = docker(
            "run", "--rm", "--network", net,
            "-v", "%s:%s:ro" % (args.volume, MOUNT_PATH),
            "-e", "PGPASSWORD=%s" % creds["DB_PASSWORD"], image,
            "sh", "-c", restore_cmd)
        commands.append("docker run --rm --network %s -v %s:%s:ro %s\n    %s  → rc=%d"
                        % (net, args.volume, MOUNT_PATH, image, restore_cmd, rc))
        if err:
            tail = err.splitlines()[-1] if err.splitlines() else err
            notes.append("pg_restore 의 마지막 줄: %s" % tail[:200])

        # ★ `pg_restore` 는 경고만으로도 rc≠0 을 낸다. **행이 살아났는가**로 판정한다.
        facts["tables_restored"] = table_count(creds, target)
        facts["tables_source"] = table_count(creds, source)
    except Exception as exc:                                   # noqa: BLE001
        notes.append("%s: %s" % (type(exc).__name__, exc))
    finally:
        rc, _, err = psql(creds, "postgres",
                          'DROP DATABASE IF EXISTS "%s"' % target, timeout=900)
        commands.append("docker exec %s psql -U *** -d postgres -c "
                        "'DROP DATABASE \"%s\"'  → rc=%d" % (DB_CONTAINER, target, rc))
        dropped = rc == 0
        if not dropped:
            notes.append("임시 DB `%s` 를 못 지웠다 — **사람이 지워야 한다**: %s"
                         % (target, err[:200]))

    seconds = time.monotonic() - t0
    facts["target_dropped"] = dropped
    facts["rto_seconds"] = round(seconds, 1)
    facts["rto_minutes"] = round(seconds / 60.0, 2)
    facts["measured_at"] = started.isoformat(timespec="seconds")
    facts["scope"] = ("DB 만이다. 객체저장(영상·캡처)은 이 시험에 들어 있지 않다 — "
                      "DB 만 살아나면 「영상이 있었다고 말하는 DB」가 된다")

    say("## 1. 쓴 명령 — 그대로 재현할 수 있다")
    say()
    say("```")
    for c in commands:
        say(c)
    say("```")
    say()
    say("## 2. 판정")
    say()
    rows = judge(facts)
    for name, ok, why in rows:
        say("  %s %-22s %s" % ("OK " if ok else "X  ", name, why))
    ok_all = all(ok for _, ok, _ in rows)
    say()
    say("**RTO 실측 %.2f분** (%.1f초) — 임시 DB 만들기부터 지우기까지 벽시계다."
        % (facts["rto_minutes"], facts["rto_seconds"]))
    say("복구만 따로 재지 않는다: 새벽에 사람이 겪는 시간에는 **DB 를 만들고 치우는**")
    say("시간이 들어 있고, 그것을 빼면 RTO 가 실제보다 짧게 적힌다.")
    say()
    if notes:
        say("### 남긴 사실")
        say()
        for n in notes:
            say("- " + n)
        say()
    say("## 3. 아직 못 잰 것")
    say()
    say("- **객체저장(영상·캡처)은 이 시험에 없다.** DB 만 살아나면 「영상이 있었다고")
    say("  말하는 DB」가 된다 — 그 절반은 `ops_restore.py --objects` 의 몫이다.")
    say("- **다른 호스트가 아니다.** 볼륨을 갈랐다는 사실은 「저장소와 함께 죽지")
    say("  않는다」까지 말하고, 「이 기계와 함께 죽지 않는다」는 말하지 않는다.")
    say("- 이 실행은 **사람이 불렀다.** 주 1회 저절로 도는 자리는 beat 표의")
    say("  `ops-restore-drill-weekly` 이고, 그 태스크는 이 기계에서 회색이다")
    say("  (앱 컨테이너 `pg_restore` 17.7 < 서버 18.1 · 사유는 그 태스크가 낸다).")

    if args.evidence:
        path = Path(args.evidence)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(log) + "\n", encoding="utf-8")
        print("증거를 적었다: %s" % args.evidence)
    if args.json:
        path = Path(args.json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(facts, ensure_ascii=False, indent=2, default=str),
                        encoding="utf-8")
        print("판정 수를 적었다: %s" % args.json)

    return EXIT_OK if ok_all else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
