#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""OPS-07 — **선언한 보존 기간을 표에 대 본다. 한 행도 지우지 않는다** (P-230 · 턴 AB · 차선 F).

    세종 판정 P-230: 「감사 **2년** · 사건 기록 **영구** · 수집기 로그 **90일**.
    이 턴은 만료 **표식·건수 산출**·`gate:` 부착까지. **삭제 실행은 대표 한 마디 뒤.**」

★★ 이 판정기에는 **지우는 손이 없다**
--------------------------------------
`DELETE` 도 `TRUNCATE` 도 `.delete()` 도 이 파일에 없고, 자기시험이 **제 소스를
읽어 그것을 확인한다**(`--self-test`). 「지울 생각이 없었다」는 증명이 아니다 —
없다는 것을 매 실행마다 기계가 말해야 한다. **결정문에 없는 삭제는 삭제가 아니다**(P-222).

여기서 말하는 「표식」이란
-------------------------
행에 표를 **쓰지 않는다.** 표식은 증거 파일에 적는 **경계**다:
부류마다 ㉠ 선언 일수 ㉡ 그 일수가 가리키는 **잘라내는 시각** ㉢ 그 시각보다 오래된
**건수**와 **id 대역**. 그 셋이 있으면 다음 사람이 「무엇이 지워질 뻔했는가」를
한 행도 건드리지 않고 되짚을 수 있다. 운영 표에는 **한 바이트도 안 쓴다.**

★ 이 판정기가 묻는 넷
---------------------
    ① **선언이 있는가**       세 부류가 임자·근거와 함께 선언돼 있는가 (정적)
    ② **선언과 집행이 같은가** 선언한 수와 **dj-core 가 읽는 자리의 수**가 같은가
    ③ **만료 건수를 쟀는가**   세 부류의 만료 건수를 실제로 셌는가 (못 세면 **회색**)
    ④ **영구에 파기 경로가 없는가**  사건 기록의 만료 표식이 **0행**인가

②가 이 자리 고유의 위험이다. 「선언했다」와 「그 수로 지운다」가 갈린 채로 초록이 나면,
화면이 말하는 보존 기간과 실제로 지우는 수가 **다른 채로** 아무도 모른다(D-369).

부르는 방향 — **호스트에서 부른다**
-----------------------------------
이 파일에 `docker exec` 가 있다. 그러므로 **호스트에서** 돈다. 컨테이너 안에서
부르면 `docker` 가 없어 **exit 2(회색)** 이고, 회색은 초록이 아니다.

    PYTHONIOENCODING=utf-8 python scripts/ops_retention_policy.py
    PYTHONIOENCODING=utf-8 python scripts/ops_retention_policy.py \
        --evidence docs/agent/evidence/OPS-07/retention_marks.json
    python scripts/ops_retention_policy.py --self-test        # 도커 없이 판정 규칙만

종료 코드: 0 쟀고 다 맞았다 · 1 쟀고 **갈렸다** · 2 **못 쟀다**(도커·DB 없음).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

ROOT = Path(__file__).resolve().parents[1]
TAG = "[P-230]"
SHELL_CONTAINER = "gx-shell"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def _policy():
    """선언을 **저장소의 그 파일에서** 읽는다. 여기에 수를 베껴 적지 않는다.

    베껴 적으면 선언이 두 벌이 되고, 두 벌이 갈리는 순간 판정기가 **제 수**로
    제품을 재게 된다 — 이 저장소가 내내 걷어낸 병이다(D-212).
    """
    import importlib.util

    path = ROOT / "backend" / "common" / "log_retention_policy.py"
    spec = importlib.util.spec_from_file_location("gx_log_retention_policy", str(path))
    mod = importlib.util.module_from_spec(spec)
    # ★ `sys.modules` 에 먼저 꽂는다 — `@dataclass` 가 제 모듈을 그 표에서 되찾는다.
    #   안 꽂으면 `AttributeError: 'NoneType' object has no attribute '__dict__'` 로
    #   죽고, 그 죽음은 「선언이 없다」처럼 보인다(회색이 아니라 고장이다).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ═══════════════════════════════════════════════════════════════════════════
# 판정 규칙 — 순수 함수 (D-277)
# ═══════════════════════════════════════════════════════════════════════════
def judge(facts: dict) -> list[tuple[str, bool, str]]:
    pol = facts.get("policy") or {}
    out: list[tuple[str, bool, str]] = []

    declared = [k for k, v in pol.items() if v.get("declared_by")]
    out.append(("① 선언", len(declared) == len(pol) and bool(pol),
                "부류 %d개가 임자·근거와 함께 선언돼 있다" % len(declared) if pol
                else "**선언이 비었다** — 선언 없는 보존 기간은 코드 기본값이다"))

    seeded = facts.get("seeded_days", "못읽음")
    want = (pol.get("audit") or {}).get("days")
    if seeded == "못읽음":
        out.append(("② 선언↔집행", False,
                    "**못 쟀다** — 집행 자리를 읽지 못했다. 회색은 초록이 아니다"))
    else:
        same = seeded is not None and seeded == want
        out.append(("② 선언↔집행", same,
                    "선언 %s일 = 집행 자리 %s일" % (want, seeded) if same
                    else "**갈렸다** — 선언 %s일인데 dj-core 가 읽는 자리는 %s다. "
                         "화면이 말하는 수와 지우는 수가 다르다(D-369). "
                         "맞추는 것은 `AdminConfig` 공용 마스터 쓰기이고, "
                         "이 턴의 차선 몫이 아니다 — **갈렸다는 사실을 적는다**"
                         % (want, "미선언" if seeded is None else "%s일" % seeded)))

    marks = facts.get("marks")
    if marks is None:
        out.append(("③ 만료 건수", False,
                    "**못 쟀다** — DB 에 닿지 못했다. 「0건」이 아니라 「못 쟀다」다"))
    else:
        ungauged = [k for k, m in marks.items() if m.get("expired") is None
                    and not m.get("forever")]
        out.append(("③ 만료 건수", not ungauged,
                    "부류 %d개의 만료 건수를 셌다" % len(marks) if not ungauged
                    else "건수를 **못 잰** 부류: %s" % ", ".join(ungauged)))

        forever = [k for k, m in marks.items() if m.get("forever")]
        bad = [k for k in forever if (marks[k].get("expired") or 0) > 0]
        out.append(("④ 영구=파기 없음", not bad,
                    "영구 부류 %d개에 만료 표식 0행" % len(forever) if not bad
                    else "**영구인데 만료 표식이 붙었다**: %s — `days=None` 을 "
                         "0 으로 읽은 자리가 있다" % ", ".join(bad)))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **제 소스에 지우는 손이 없다는 것까지 잰다**
# ═══════════════════════════════════════════════════════════════════════════
#: 지우는 손의 **부름 이름**. 이름으로 grep 하지 않는다 — 이 파일의 머리말이
#: 그 낱말들을 설명하려고 쓰고 있어서, 글자로 세면 **제 설명에 걸린다**(D-263 과 같은 함정).
#: 그래서 AST 로 **부름과 SQL 문자열만** 본다. 주석·머리말은 코드가 아니다.
_DELETE_CALLS = ("delete", "truncate", "drop", "purge", "destroy")
_DELETE_SQL = ("delete from", "truncate", "drop table")


def _no_delete_hand() -> tuple[bool, str]:
    """**제 소스에 지우는 손이 없다**는 것을 AST 로 확인한다.

    「지울 생각이 없었다」는 증명이 아니다. 매 실행마다 기계가 말해야 한다.
    머리말이 `DELETE` 를 **설명하는 것**과 코드가 그것을 **부르는 것**은 다르다 —
    글자로 세면 둘이 같아지고, 같아진 검사는 지울 수 없는 빨강이 되어 꺼진다(D-353).
    """
    import ast

    src = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    #: 머리말(docstring)은 코드가 아니다 — 문자열 검사에서 뺀다.
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstrings.add(doc)

    #: ★ 이 검사의 **과녁 목록 자신**은 과녁이 아니다. 빼지 않으면 검사가 제 꼬리를
    #:   물고 영원히 빨갛다 — 지울 수 없는 빨강은 다음 사람이 그냥 끈다(D-353).
    own = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "").startswith("_DELETE") for t in node.targets):
            for sub in ast.walk(node.value):
                own.add(id(sub))

    hits = []
    for node in ast.walk(tree):
        if id(node) in own:
            continue
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "attr", None) or getattr(fn, "id", None)
            if name and name.lower() in _DELETE_CALLS:
                hits.append("부름 %s()" % name)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in docstrings:
                continue
            low = node.value.lower()
            for w in _DELETE_SQL:
                if w in low:
                    hits.append("SQL 문자열 %r" % w)
    return (not hits,
            "제 소스에 지우는 손이 없다 (AST · 부름 %d종 · SQL %d종 대조)"
            % (len(_DELETE_CALLS), len(_DELETE_SQL)) if not hits
            else "**지우는 손이 들어왔다**: %s" % ", ".join(sorted(set(hits))))


def self_test() -> int:
    bad = []
    ok, why = _no_delete_hand()
    if not ok:
        bad.append(why)

    pol = {"audit": {"days": 730, "declared_by": "세종"},
           "incident": {"days": None, "declared_by": "세종"},
           "collector": {"days": 90, "declared_by": "세종"}}
    good = {"policy": pol, "seeded_days": 730,
            "marks": {"audit": {"expired": 0}, "incident": {"expired": 0, "forever": True},
                      "collector": {"expired": None, "forever": False, "size_based": True}}}
    # 수집기는 크기 기반이라 건수를 못 잰다 — **그 회색이 초록으로 덮이면 안 된다**
    r = [p for _, p, _ in judge(good)]
    if r != [True, True, False, True]:
        bad.append("크기 기반 수집기의 회색이 초록으로 덮인다: %s" % r)

    split = dict(good, seeded_days=365)
    if [p for _, p, _ in judge(split)][1]:
        bad.append("선언 730 · 집행 365 인데 ②가 초록이다")

    unseeded = dict(good, seeded_days=None)
    if [p for _, p, _ in judge(unseeded)][1]:
        bad.append("미선언인데 ②가 초록이다")

    blind = dict(good, seeded_days="못읽음", marks=None)
    r = [p for _, p, _ in judge(blind)]
    if r != [True, False, False]:
        bad.append("못 잰 것이 초록으로 나온다: %s" % r)

    forever_bad = dict(good)
    forever_bad["marks"] = dict(good["marks"],
                                incident={"expired": 3, "forever": True})
    if [p for _, p, _ in judge(forever_bad)][3]:
        bad.append("영구 부류에 만료 3행인데 ④가 초록이다")

    if bad:
        print("%s 자기시험 실패 — 판정기를 먼저 의심한다 (D-350):" % TAG)
        for b in bad:
            print("    " + b)
        return EXIT_FAIL
    print("%s 자기시험 통과 — 정상 1 · 음성 5 · 삭제손 대조 1 (%s)" % (TAG, why))
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 수집 — gx-shell 안에 **읽기만 하는** 조각을 보낸다
# ═══════════════════════════════════════════════════════════════════════════
#: ★ 이 조각에는 `SELECT` 밖에 없다. 세는 일과 지우는 일을 한 파일에 두지 않는다.
DB_PROBE = r'''
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from django.db import connection
out = {}
try:
    from core.logger.models import AuditLogs
    tab = AuditLogs._meta.db_table
    out["table"] = tab
    with connection.cursor() as c:
        c.execute("SELECT column_name FROM information_schema.columns "
                  "WHERE table_name=%s AND data_type LIKE 'timestamp%%'", [tab])
        cols = [r[0] for r in c.fetchall()]
        col = None
        for pref in ("create_datetime", "created_on", "created_at"):
            if pref in cols:
                col = pref
                break
        out["time_col"] = col
        c.execute("SELECT count(*) FROM " + tab)
        out["rows"] = c.fetchone()[0]
        if col:
            c.execute('SELECT min("%s"), max("%s") FROM %s' % (col, col, tab))
            lo, hi = c.fetchone()
            out["oldest"], out["newest"] = str(lo), str(hi)
            for d in (90, 365, 730):
                c.execute("SELECT count(*), min(id), max(id) FROM %s "
                          "WHERE \"%s\" < now() - interval '%d days'" % (tab, col, d))
                n, lo_id, hi_id = c.fetchone()
                out["expired_%dd" % d] = {"count": n, "min_id": lo_id, "max_id": hi_id,
                                          "cutoff_days": d}
except Exception as exc:
    out["error"] = "%s: %s" % (type(exc).__name__, exc)
try:
    from common import ops_tasks as OT
    out["seeded_days"] = OT.audit_retention_declared_days()
    out["seed_source"] = OT.audit_retention_source()
    out["purge_enabled"] = bool(OT.audit_purge_enabled())
except Exception as exc:
    out["seed_error"] = "%s: %s" % (type(exc).__name__, exc)
try:
    from django_celery_beat.models import PeriodicTask
    out["purge_rows"] = [
        {"name": r.name, "task": r.task, "enabled": r.enabled,
         "last_run_at": str(r.last_run_at)}
        for r in PeriodicTask.objects.filter(
            task__in=("common.ops_audit_purge_beat",
                      "core.logger.tasks.purge_old_audit_logs"))]
except Exception as exc:
    out["purge_rows_error"] = "%s: %s" % (type(exc).__name__, exc)
print("GX_RETENTION_JSON " + json.dumps(out, ensure_ascii=False))
'''


def probe() -> dict:
    """gx-shell 안에서 읽어 온 사실. 못 닿으면 `{"error": …}`."""
    env = dict(os.environ)
    env["MSYS_NO_PATHCONV"] = "1"
    cmd = ["docker", "exec", "-e", "DJANGO_SETTINGS_MODULE=config.settings",
           SHELL_CONTAINER, "python", "-c", DB_PROBE]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=300, env=env)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": "%s: %s" % (type(exc).__name__, exc)}
    text = (p.stdout or b"").decode("utf-8", "replace")
    for line in text.splitlines():
        if line.startswith("GX_RETENTION_JSON "):
            return json.loads(line[len("GX_RETENTION_JSON "):])
    return {"error": "탐침이 판을 안 냈다 (rc=%d) — %s"
                     % (p.returncode, (p.stderr or b"").decode("utf-8", "replace")[-400:])}


def marks_from(pol, info: dict) -> dict | None:
    """부류마다 **만료 표식** — 경계와 건수. 행에는 아무것도 안 쓴다."""
    if info.get("error") or info.get("time_col") is None:
        return None
    out = {}
    for key in pol.ORDER:
        spec = pol.POLICY[key]
        if spec.days is None:
            # ★ 영구 — 만료가 **정의상 없다.** 세지 않는 것이 아니라 0 이다.
            out[key] = {"days": None, "forever": True, "expired": 0,
                        "cutoff": "없다(영구)", "note": spec.enforced_where}
            continue
        if key == "collector":
            # ★ 크기 기반 회전이라 **날짜로 못 센다.** 0 이라고 적지 않는다.
            out[key] = {"days": spec.days, "forever": False, "expired": None,
                        "size_based": True, "cutoff": "날짜 경계가 없다",
                        "note": "`json-file` 은 날짜를 모른다 — 선언은 기간이고 "
                                "집행은 크기다. **회색이 옳다**"}
            continue
        hit = info.get("expired_%dd" % spec.days)
        if hit is None:
            out[key] = {"days": spec.days, "forever": False, "expired": None,
                        "note": "탐침이 이 경계를 안 셌다"}
            continue
        out[key] = {"days": spec.days, "forever": False,
                    "expired": hit["count"], "min_id": hit["min_id"],
                    "max_id": hit["max_id"], "table": info.get("table"),
                    "time_col": info.get("time_col"),
                    "cutoff": "now() - %d days" % spec.days,
                    "rows_total": info.get("rows"),
                    "oldest": info.get("oldest")}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="OPS-07 P-230 보존 선언을 표에 대 본다 (삭제 0)")
    ap.add_argument("--evidence", default=None, help="표식을 적을 판(JSON)")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        return EXIT_FAIL

    pol = _policy()
    print("%s 선언 — 임자 %s (%s)" % (TAG, pol.DECLARED_BY, pol.DECLARED_AT))
    print("%s 근거 — %s" % (TAG, pol.LEGAL_BASIS))
    print()
    print("| 부류 | 선언 | 어디에 걸리는가 |")
    print("|---|---|---|")
    for key in pol.ORDER:
        s = pol.POLICY[key]
        print("| %s | %s | %s |"
              % (s.title, "영구(파기 없음)" if s.days is None else "%d일" % s.days,
                 s.enforced_where))
    print()

    info = probe()
    if info.get("error"):
        print("%s **판정 불가(exit 2)** — %s" % (TAG, info["error"]))
        print("%s 호스트에서 부른다. 「0건」이 아니라 「못 쟀다」다 — 회색은 초록이 아니다"
              % TAG)
        return EXIT_UNDECIDABLE

    seeded = info.get("seeded_days", "못읽음") if "seed_error" not in info else "못읽음"
    print("### 감사 보존 — **세 수를 나란히 적는다. 맞추지 않는다**")
    print()
    for name, value in pol.divergence(None if seeded == "못읽음" else seeded):
        print("    %-52s %s" % (name, "미선언/못 읽음" if value is None else "%s일" % value))
    print()
    if "seed_source" in info:
        print("    출처: %s" % info["seed_source"])
    print("    파기 스위치(OPS_AUDIT_PURGE_ENABLED): %s" % info.get("purge_enabled"))
    for r in info.get("purge_rows") or []:
        print("    주기 표: %s · task=%s · **켜짐=%s** · 마지막 발화 %s"
              % (r["name"], r["task"], r["enabled"], r["last_run_at"]))
    print()

    marks = marks_from(pol, info)
    print("### 만료 표식 — **경계와 건수뿐이다. 한 행도 안 건드렸다**")
    print()
    print("| 부류 | 선언 | 잘라내는 자리 | 만료 건수 | id 대역 |")
    print("|---|---|---|---|---|")
    for key in pol.ORDER:
        m = (marks or {}).get(key) or {}
        n = m.get("expired")
        print("| %s | %s | %s | %s | %s |"
              % (key,
                 "영구" if m.get("forever") else ("%s일" % m.get("days")),
                 m.get("cutoff", "—"),
                 "**못 쟀다**" if n is None else format(n, ","),
                 "—" if m.get("min_id") is None else "%s~%s" % (m["min_id"], m["max_id"])))
    print()
    print("표 전체 %s행 · 가장 오래된 행 %s"
          % (format(info.get("rows") or 0, ","), info.get("oldest")))
    print()

    facts = {"policy": {k: {"days": v.days, "declared_by": pol.DECLARED_BY}
                        for k, v in pol.POLICY.items()},
             "seeded_days": seeded, "marks": marks}
    rows = judge(facts)
    print("## 판정")
    print()
    for name, passed, why in rows:
        print("  %s %-16s %s" % ("OK  " if passed else "FAIL", name, why))
    ok = all(p for _, p, _ in rows)
    print()
    print("%s 삭제 실행 **0건** — 이 판정기에는 지우는 손이 없다(자기시험이 소스를 읽어 "
          "확인했다). 삭제는 대표 자리다(P-222)" % TAG)
    print("판정 **%s**." % ("통과" if ok else "실패"))

    if args.evidence:
        payload = {
            "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "declared_by": pol.DECLARED_BY, "legal_basis": pol.LEGAL_BASIS,
            "enforcement_site": pol.ENFORCEMENT_SITE,
            "divergence": [{"name": n, "days": v}
                           for n, v in pol.divergence(
                               None if seeded == "못읽음" else seeded)],
            "marks": marks, "table_rows": info.get("rows"),
            "oldest": info.get("oldest"), "newest": info.get("newest"),
            "purge_enabled": info.get("purge_enabled"),
            "purge_rows": info.get("purge_rows"),
            "deleted": 0,
            "deleted_note": "이 판정기는 한 행도 지우지 않는다 (P-230 · P-222)",
            "verdict": [{"name": n, "passed": p, "why": w} for n, p, w in rows],
        }
        try:
            os.makedirs(os.path.dirname(args.evidence), exist_ok=True)
            with open(args.evidence, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print("표식을 적었다: %s" % args.evidence)
        except OSError as exc:
            print("⚠ 표식을 못 적었다: %s" % exc)

    return EXIT_OK if ok else EXIT_FAIL


if __name__ == "__main__":
    raise SystemExit(main())
