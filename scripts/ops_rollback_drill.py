#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-08 — **되돌려 본다.** 매뉴얼 §5 의 문장을 실제로 쳐 본다 (2026-09-04 · 차선 E3).

    OPS-08 되돌리기 절차 (배포 실패 시) — "절차 문서는 있으나 **해 본 적이 없다**"
        — docs/agent/remaining_40.md 42행 · 「첫 증거는 되돌려 본 기록」

왜 문서가 있는데도 못 닫혀 있었나
--------------------------------
`설치운영매뉴얼_v0.1.md` §5 는 표 하나로 되돌리는 명령을 적어 두었다:

    | 마이그레이션 0020 | `manage.py migrate stream_monitors 0019` |

그 문장은 **적혀 있을 뿐 쳐 본 적이 없다.** 「이 명령을 치면 된다」는 [추정]이고
「쳤더니 이렇게 됐다」가 [실측]이다. 배포가 새벽에 실패했을 때 처음 치는 명령이
검증된 적 없다면, 그 절은 서 있는 것이 아니다.

★ 되돌리기는 **되돌아온 것까지** 봐야 끝난다
--------------------------------------------
많은 롤백 절차가 「명령이 rc=0 이었다」에서 멈춘다. 그것은 **명령이 죽지 않았다**일
뿐이다. 이 훈련은 스키마를 세 번 잰다:

    ① 세운 직후    0020 이 만든 칸(`address`·`address_status`)이 **있다**
    ② 되돌린 뒤    그 칸이 **없다**              ← 여기가 「진짜 되돌아갔다」
    ③ 다시 민 뒤   그 칸이 **다시 있다**          ← 여기가 「되돌린 뒤에도 복구된다」

②를 안 재면 「rc=0 인데 아무 일도 안 일어난」 경우와 구별되지 않는다.
③을 안 재면 되돌린 환경을 **되살릴 수 있는지**를 모른 채 되돌리게 된다.

★ 원본을 건드리지 않는다 — 세 겹 (ops_restore.py 와 같은 규약 · D-354)
----------------------------------------------------------------------
  · 대상 이름이 지금 붙어 있는 DB 와 같으면 **시작하지 않는다**
  · 대상 이름은 `e_rollback_check` 처럼 **접두가 강제**된다 (차선 E3 의 접두 `e_`)
  · 끝나면 지운다. 실패해도 지운다(`finally`). `--keep` 을 줘야 남는다

  ⚠ 개발 DB(`database_guardianx`)에는 지금 **다른 차선 셋의 runserver 가 붙어 있다.**
    그래서 `CREATE DATABASE … TEMPLATE database_guardianx` 는 쓰지 않는다 — 템플릿에
    다른 접속이 있으면 PostgreSQL 이 거부하고, 거부당하지 않으려면 남의 서버를 끊어야
    한다. 대신 **빈 DB 를 매뉴얼 §2-3 대로 세운다.** 그 편이 OPS-02 의 절반(빈 DB 에서
    매뉴얼대로 세우기)을 **같은 실행에서 다시 재는** 이득도 있다.

무엇을 남기나
-------------
`--evidence <경로>` 에 **친 명령과 rc 와 스키마 세 컷**을 그대로 적는다. 사람이 그
파일만 보고 같은 일을 다시 할 수 있어야 한다.

    docker exec -w /app -e PYTHONPATH=/app gx-shell \
        python /repo/scripts/ops_rollback_drill.py \
            --evidence /docs/agent/evidence/OPS-08/rollback_drill.md
    python scripts/ops_rollback_drill.py --self-test     # 판정 규칙만 (DB 없이)

종료 코드: 0 되돌렸고 되살렸다 · 1 쟀는데 어긋났다 · 2 **못 쟀다**(환경 없음)
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
import time

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 훈련용 DB 이름. **접두가 곧 안전장치다** — 이 접두가 아니면 만들지도 지우지도 않는다.
DRILL_DB_PREFIX = "e_rollback_check"

#: 절대 건드리면 안 되는 이름. 운영 복제본(D-245)과 그 파생.
PROTECTED = {"database_guardianx", "guardianx-v2", "postgres", "template0", "template1"}

#: 매뉴얼 §2-3 이 적은 **세 줄**. 한 줄로는 빈 DB 에서 죽는다(P-ENV-1).
#: 여기 순서를 바꾸면 매뉴얼과 갈린다 — 갈린 두 절차는 어긋나도 아무도 모른다(D-369).
INSTALL_STEPS = (
    ("migrate user", ["migrate", "user"]),
    ("migrate multilanguage", ["migrate", "multilanguage"]),
    ("migrate", ["migrate"]),
    ("migrate --check", ["migrate", "--check"]),
)

#: 매뉴얼 §5 가 적은 되돌림. **문장 그대로** 친다.
ROLLBACK_STEP = ("migrate stream_monitors 0019", ["migrate", "stream_monitors", "0019"])
ROLLFORWARD_STEP = ("migrate stream_monitors", ["migrate", "stream_monitors"])

#: 0020 이 만든 칸. 되돌리면 **없어져야** 한다. (0020_detectionevent_address_address_status)
PROBE_COLUMNS = (
    ("stream_monitors_detectionevent", "address"),
    ("stream_monitors_detectionevent", "address_status"),
)
#: 0019 가 만든 표. 0019 까지 되돌리는 것이므로 **남아 있어야** 한다 — 되돌림이
#: 목표 지점을 지나쳐 버리지 않았는지 보는 눈금이다.
PROBE_TABLES = ("stream_monitors_zone",)


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수. **판정기도 시험받는다**(D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(shots: dict) -> list[tuple[str, bool, str]]:
    """스키마 세 컷을 판정한다. `None` 은 **못 쟀다**이지 없음이 아니다(D-301)."""
    out = []
    before, after, again = shots.get("before"), shots.get("after"), shots.get("again")

    if before is None:
        return [("① 세운 직후", False, "**못 쟀다**"),
                ("② 되돌린 뒤", False, "못 쟀다"),
                ("③ 다시 민 뒤", False, "못 쟀다"),
                ("④ 0019 눈금", False, "못 쟀다")]

    have = [c for c in PROBE_COLUMNS if before.get("col:%s.%s" % c)]
    out.append(("① 세운 직후", len(have) == len(PROBE_COLUMNS),
                "0020 의 칸 %d/%d 개가 있다" % (len(have), len(PROBE_COLUMNS))))

    if after is None:
        out.append(("② 되돌린 뒤", False, "**못 쟀다** — 되돌림이 안 돌았다"))
    else:
        left = [".".join(c) for c in PROBE_COLUMNS if after.get("col:%s.%s" % c)]
        out.append(("② 되돌린 뒤", not left,
                    "0020 의 칸이 **사라졌다**" if not left
                    else "rc=0 이었는데 칸이 남아 있다: %s — 아무 일도 안 일어났다"
                         % ", ".join(left)))

    if again is None:
        out.append(("③ 다시 민 뒤", False, "**못 쟀다** — 되살리지 못했다"))
    else:
        back = [c for c in PROBE_COLUMNS if again.get("col:%s.%s" % c)]
        out.append(("③ 다시 민 뒤", len(back) == len(PROBE_COLUMNS),
                    "칸 %d/%d 개가 **되돌아왔다**" % (len(back), len(PROBE_COLUMNS))))

    if after is None:
        out.append(("④ 0019 눈금", False, "못 쟀다"))
    else:
        kept = [t for t in PROBE_TABLES if after.get("tab:%s" % t)]
        out.append(("④ 0019 눈금", len(kept) == len(PROBE_TABLES),
                    "0019 의 표 %d/%d 개가 남아 있다 — 목표 지점을 지나치지 않았다"
                    % (len(kept), len(PROBE_TABLES))))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 실행
# ═══════════════════════════════════════════════════════════════════════════
def run(cmd: list[str], env: dict, cwd: str = "/app") -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       errors="replace")
    tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-6:])
    return p.returncode, tail


def manage(args: list[str], db: str) -> tuple[int, str]:
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    env["DB_NAME"] = db
    return run([sys.executable, "manage.py"] + args, env)


def psql(sql: str, db: str = "postgres") -> tuple[int, str]:
    """DB 를 만들고 지우는 자리. `manage.py` 로는 못 한다."""
    env = dict(os.environ)
    env["PGPASSWORD"] = env.get("DB_PASSWORD", "")
    host = env.get("DB_HOST", "postgres")
    user = env.get("DB_USER", "postgres")
    return run(["psql", "-h", host, "-U", user, "-d", db, "-v", "ON_ERROR_STOP=1",
                "-c", sql], env, cwd="/tmp")


def snapshot(db: str) -> dict | None:
    """스키마 한 컷. **정보 스키마에게 묻는다** — 모델을 믿지 않는다."""
    import psycopg2
    try:
        conn = psycopg2.connect(
            dbname=db, user=os.environ.get("DB_USER", "postgres"),
            password=os.environ.get("DB_PASSWORD", ""),
            host=os.environ.get("DB_HOST", "postgres"),
            port=os.environ.get("DB_PORT", "5432"))
    except Exception:                                          # noqa: BLE001
        return None
    shot: dict = {}
    try:
        with conn.cursor() as c:
            for tab, col in PROBE_COLUMNS:
                c.execute("SELECT 1 FROM information_schema.columns "
                          "WHERE table_name=%s AND column_name=%s", (tab, col))
                shot["col:%s.%s" % (tab, col)] = c.fetchone() is not None
            for tab in PROBE_TABLES:
                c.execute("SELECT to_regclass(%s)", (tab,))
                shot["tab:%s" % tab] = c.fetchone()[0] is not None
            c.execute("SELECT count(*) FROM information_schema.tables "
                      "WHERE table_schema='public'")
            shot["tables"] = c.fetchone()[0]
            c.execute("SELECT name FROM django_migrations WHERE app='stream_monitors' "
                      "ORDER BY id DESC LIMIT 1")
            row = c.fetchone()
            shot["stream_monitors_head"] = row[0] if row else None
    finally:
        conn.close()
    return shot


def self_test() -> int:
    ok = True
    ok &= all(not p for _, p, _ in judge({}))

    full = {"col:stream_monitors_detectionevent.address": True,
            "col:stream_monitors_detectionevent.address_status": True,
            "tab:stream_monitors_zone": True}
    rolled = {"col:stream_monitors_detectionevent.address": False,
              "col:stream_monitors_detectionevent.address_status": False,
              "tab:stream_monitors_zone": True}
    ok &= all(p for _, p, _ in judge({"before": full, "after": rolled, "again": full}))

    # rc=0 이었는데 아무 일도 안 일어난 경우 → ② 만 실패해야 한다
    r = judge({"before": full, "after": full, "again": full})
    ok &= [p for _, p, _ in r] == [True, False, True, True]

    # 되돌리다 0019 의 표까지 날아간 경우 → ④ 가 잡아야 한다
    over = dict(rolled); over["tab:stream_monitors_zone"] = False
    r = judge({"before": full, "after": over, "again": full})
    ok &= [p for _, p, _ in r] == [True, True, True, False]

    print("self-test: %s" % ("통과" if ok else "실패"))
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=DRILL_DB_PREFIX)
    ap.add_argument("--evidence", default=None, help="여기에 친 명령과 결과를 적는다")
    ap.add_argument("--keep", action="store_true", help="끝나고 지우지 않는다")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    db = args.db
    if not db.startswith(DRILL_DB_PREFIX):
        print("거부: 훈련 DB 이름은 %r 로 시작해야 한다 (받은 것: %r)"
              % (DRILL_DB_PREFIX, db))
        return EXIT_UNDECIDABLE
    if db in PROTECTED or db == os.environ.get("DB_NAME"):
        print("거부: %r 는 보호 대상이다. 훈련은 새 DB 에서만 한다 (D-245)" % db)
        return EXIT_UNDECIDABLE

    log: list[str] = []

    def say(line: str) -> None:
        print(line)
        log.append(line)

    rc, out = psql("SELECT 1")
    if rc != 0:
        print("판정 불가(exit 2): postgres 에 닿지 못했다 — %s" % out)
        return EXIT_UNDECIDABLE

    say("## 0. 무엇을 지우고 어떻게 되살리는가 — **하기 전에 적는다**")
    say("")
    say("지우는 것: 훈련용 DB `%s` **하나뿐**이다. 이 실행이 방금 만든 것이고," % db)
    say("다른 차선이 쓰는 `database_guardianx`·`postgres`·`gx-shell` 은 건드리지 않는다.")
    say("되살리는 절차: 없다 — **되살릴 것이 없다.** 훈련이 끝나면 사라지는 것이 정상이고,")
    say("다시 필요하면 이 스크립트를 한 번 더 돌리면 같은 것이 처음부터 선다.")
    say("")

    shots: dict = {}
    started = time.time()
    try:
        say("## 1. 빈 DB 를 만든다")
        say("")
        say("```")
        for sql in ('DROP DATABASE IF EXISTS "%s"' % db, 'CREATE DATABASE "%s"' % db):
            rc, out = psql(sql)
            say("psql -c %-46s rc=%d" % (sql, rc))
            if rc != 0:
                say(out)
                return EXIT_UNDECIDABLE
        say("```")
        say("")

        say("## 2. 매뉴얼 §2-3 대로 세운다 — **세 줄이다**")
        say("")
        say("```")
        for label, argv in INSTALL_STEPS:
            rc, out = manage(argv, db)
            say("manage.py %-28s rc=%d" % (label, rc))
            if rc != 0:
                say(out)
                say("```")
                say("**세우지 못했다.** 되돌리기 훈련은 여기서 멈춘다 — 세우지 못한 것을")
                say("되돌릴 수는 없다.")
                return EXIT_FAIL
        say("```")
        shots["before"] = snapshot(db)
        say("")
        say("세운 직후: 표 %s개 · stream_monitors 머리 `%s`"
            % (shots["before"].get("tables"), shots["before"].get("stream_monitors_head")))
        say("")

        say("## 3. 매뉴얼 §5 의 문장을 **친다**")
        say("")
        label, argv = ROLLBACK_STEP
        rc, out = manage(argv, db)
        say("```")
        say("manage.py %-28s rc=%d" % (label, rc))
        say(out)
        say("```")
        shots["after"] = snapshot(db)
        say("")
        say("되돌린 뒤: 표 %s개 · stream_monitors 머리 `%s`"
            % (shots["after"].get("tables"), shots["after"].get("stream_monitors_head")))
        say("")

        say("## 4. 되살린다 — **되돌린 뒤에 다시 설 수 있는가**")
        say("")
        label, argv = ROLLFORWARD_STEP
        rc, out = manage(argv, db)
        say("```")
        say("manage.py %-28s rc=%d" % (label, rc))
        say(out)
        say("```")
        shots["again"] = snapshot(db)
        say("")
        say("다시 민 뒤: 표 %s개 · stream_monitors 머리 `%s`"
            % (shots["again"].get("tables"), shots["again"].get("stream_monitors_head")))
        say("")
    finally:
        if args.keep:
            say("훈련 DB `%s` 를 **남겼다**(--keep)." % db)
        else:
            rc, _ = psql('DROP DATABASE IF EXISTS "%s"' % db)
            say("훈련 DB `%s` 를 지웠다 (rc=%d)." % (db, rc))

    say("")
    say("## 5. 판정")
    say("")
    rows = judge(shots)
    for name, passed, why in rows:
        say("  %s %-12s %s" % ("OK  " if passed else "FAIL", name, why))
    ok = all(p for _, p, _ in rows)
    say("")
    say("걸린 시간 %.0f초 · 판정 **%s**" % (time.time() - started, "통과" if ok else "실패"))

    if args.evidence:
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with io.open(args.evidence, "w", encoding="utf-8") as f:
                f.write("# OPS-08 — 되돌려 본 기록 (%s)\n\n"
                        % time.strftime("%Y-%m-%d %H:%M:%S"))
                f.write("**이 파일은 `scripts/ops_rollback_drill.py` 가 실행하며 적었다.**\n"
                        "손으로 옮겨 적은 문장이 아니다 — 아래 rc 는 전부 그 실행의 것이다.\n\n")
                f.write("\n".join(log) + "\n")
            print("증거를 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 증거를 못 적었다: %s" % exc)
    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
