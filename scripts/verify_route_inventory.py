#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""D-343 ①②④ — 라우트 인벤토리와 3갈래 분류를 **대장으로 고정한다.**

무엇을 막는가
-------------
D-343 은 전역 적용(③)을 **인벤토리를 보고 판정한 뒤에** 하라고 했다. 그 사이에도
표면은 자란다 — 새 라우트가 하나 생기면 그것은 대장에 없는 채로 태어나고, 대장에
없는 것은 판정에 들어가지 않는다. 그래서 ③을 기다리는 동안 ④(래칫)를 먼저 건다.

    ★ **목록은 이름으로 고정한다.** 새 라우트가 목록에 없이 키를 받으면 exit 1.

보는 것 — 다섯
--------------
  ① 인벤토리의 라우트가 **전부** 대장에 있는가 (빠진 것 = 분류되지 않은 표면)
  ② 대장의 분류가 3갈래 안에 있는가 (`inbound_key_allowed`/`session_only`/`internal_only`)
  ③ 인벤토리가 `declared`(키 수용 선언)인 자리와 대장의 `inbound_key_allowed` 가 **같은가**
     — 코드가 열었는데 대장이 모르면 대장이 거짓말이고, 그 반대면 대장이 허가증이 된다
  ④ **래칫**(D-311) — `declared` · `open_anonymous` 건수가 기준선을 넘으면 exit 1
  ⑤ 인벤토리가 비어 있지 않은가 (D-301 — 0건은 「없다」가 아니라 「못 봤다」일 수 있다)

★ 왜 게이트가 컨테이너를 부르지 않나
------------------------------------
인벤토리는 **런타임 레지스트리**를 읽어야 나온다(`probe_route_inventory.py`). 게이트가
매번 컨테이너를 띄우면 게이트가 환경에 매인다 — 환경이 죽으면 게이트가 **초록으로**
죽는다(D-301). 그래서 게이트는 **커밋된 인벤토리 파일**을 본다. 인벤토리를 다시 뜨는 것은
사람의 일이고, 낡은 인벤토리는 `--max-age-days` 가 잡는다.

    python scripts/verify_route_inventory.py             # 판정
    python scripts/verify_route_inventory.py --list      # 분류별 건수
    python scripts/verify_route_inventory.py --freeze    # 대장·기준선 생성/갱신
    python scripts/verify_route_inventory.py --self-test
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "D-343"
INVENTORY = EVIDENCE / "route_inventory.json"
LEDGER = EVIDENCE / "route_classes.yaml"
BASELINE = EVIDENCE / "route_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

CLASSES = ("inbound_key_allowed", "session_only", "internal_only")

_LEDGER_HEADER = """\
# D-343 ② — 라우트 3갈래 분류 대장
#
# ★ `python scripts/verify_route_inventory.py --freeze` 가 만든다.
#   분류를 **바꾸는 것은 사람의 일이다** — 이 파일을 손으로 고치고 게이트를 돌려라.
#   (--freeze 는 새 라우트를 기본값 `session_only` 로 **더하기만** 한다. 사람이 정한
#    분류를 덮어쓰지 않는다 — 덮어쓰면 대장이 도구의 의견이 되고 사람의 판정이 사라진다.)
#
# 분류 (D-343 ②)
#   inbound_key_allowed : 외부 App 이 부를 면. 코드가 `inbound_key=True` 로 **선언**한 것만
#   session_only        : 사람 UI 전용. **분류의 기본값** — 판단이 서지 않으면 좁은 쪽
#   internal_only       : 내부 호출 전용
#
# 이 표는 버리지 않는다 (D-343 ▣): F-05 연동 규격서의 부록이고, 상용판 API 문서의
# 초안이며, 다음 파트너 기술 검토 자료다. **한 번 만들어 세 번 쓴다.**
"""

_BASELINE_HEADER = """\
# D-343 ④ 래칫 기준선 — 오늘의 건수. 늘면 exit 1 (D-311)
#
# ★ --freeze 가 만든다. 손으로 고치지 말 것.
#   declared       = 코드가 들어오는 키를 받겠다고 선언한 자리
#   open_anonymous = 인증 콜백이 아예 없는 자리 (관문 없음 — 「거절」이 아니다)
"""


# ═══════════════════════════════════════════════════════════════════════════
# 읽기 — YAML 없이 읽는다 (게이트가 의존을 늘리지 않는다)
# ═══════════════════════════════════════════════════════════════════════════

def parse_ledger(text: str) -> dict[str, str]:
    """`METHOD PATH: class` 한 줄 한 항목. 주석과 빈 줄은 건너뛴다."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.rpartition(":")
        key = key.strip().strip('"')
        value = value.strip().strip('"')
        if key and value:
            out[key] = value
    return out


def render_ledger(rows: list[dict], existing: dict[str, str]) -> str:
    lines = [_LEDGER_HEADER, "routes:"]
    for r in rows:
        key = "%s %s" % (r["method"], r["path"])
        klass = existing.get(key) or r["classification"]
        lines.append('  "%s": %s' % (key, klass))
    return "\n".join(lines) + "\n"


def parse_baseline(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, value = line.partition("\t")
        try:
            out[name.strip()] = int(value.strip())
        except ValueError:
            continue
    return out


# ═══════════════════════════════════════════════════════════════════════════
# 판정
# ═══════════════════════════════════════════════════════════════════════════

def judge(inventory: dict, ledger: dict[str, str], baseline: dict[str, int],
          max_age_days: int | None = None) -> tuple[list[str], dict[str, int]]:
    """어긋난 것들과 건수를 돌려준다. **판정은 부르는 쪽이 한다.**"""
    rows = inventory.get("routes", [])
    counts = {
        "routes": len(rows),
        "ledger": len(ledger),
        "declared": sum(1 for r in rows if r["inbound_key"] == "declared"),
        "open_anonymous": sum(1 for r in rows if r["inbound_key"] == "open_anonymous"),
        "accepts": sum(1 for r in rows if r["inbound_key"] == "accepts"),
    }
    problems: list[str] = []

    # ⑤ 비어 있으면 판정이 아니라 열거기 고장이다
    if not rows:
        problems.append("인벤토리가 비었다 — 판정이 아니라 열거기 고장이다 (D-301)")
        return problems, counts

    keys = ["%s %s" % (r["method"], r["path"]) for r in rows]

    # ① 전부 대장에 있는가
    missing = [k for k in keys if k not in ledger]
    if missing:
        problems.append(
            "대장에 없는 라우트 %d건 — 분류되지 않은 표면이다. --freeze 로 더한 뒤 분류하라:\n    "
            % len(missing) + "\n    ".join(missing[:10])
            + ("\n    … 외 %d건" % (len(missing) - 10) if len(missing) > 10 else ""))

    # ② 3갈래 밖의 값
    bad_class = sorted({v for v in ledger.values() if v not in CLASSES})
    if bad_class:
        problems.append("3갈래 밖의 분류: %s (허용 %s)" % (", ".join(bad_class), ", ".join(CLASSES)))

    # ③ 코드의 선언과 대장이 같은가
    declared = {k for k, r in zip(keys, rows) if r["inbound_key"] == "declared"}
    allowed = {k for k, v in ledger.items() if v == "inbound_key_allowed"}
    only_code = sorted(declared - allowed)
    only_ledger = sorted(allowed - declared)
    if only_code:
        problems.append("코드는 키를 받는데 대장이 모른다 (대장이 거짓말한다): " + ", ".join(only_code))
    if only_ledger:
        problems.append("대장은 허가했는데 코드가 안 받는다 (대장이 허가증이 된다): "
                        + ", ".join(only_ledger))

    # ④ 래칫
    for name in ("declared", "open_anonymous"):
        base = baseline.get(name)
        if base is None:
            problems.append("기준선에 %s 가 없다 — --freeze 로 잠가라" % name)
        elif counts[name] > base:
            problems.append("%s 가 늘었다: 기준선 %d → 지금 %d. 표면이 넓어졌다"
                            % (name, base, counts[name]))

    # 낡은 인벤토리
    if max_age_days is not None:
        measured = (inventory.get("measured_at") or "").strip()
        if not measured:
            problems.append("인벤토리에 measured_at 이 없다 — 언제 잰 수인지 모른다 (D-322)")
        else:
            try:
                age = (date.today() - date.fromisoformat(measured)).days
            except ValueError:
                problems.append("measured_at 이 날짜가 아니다: %r" % measured)
            else:
                if age > max_age_days:
                    problems.append("인벤토리가 %d일 지났다 (허용 %d) — 다시 떠라"
                                    % (age, max_age_days))
    return problems, counts


# ═══════════════════════════════════════════════════════════════════════════
# 사람이 읽는 표 — F-05 연동 규격서의 부록이 될 것 (D-343 ▣)
# ═══════════════════════════════════════════════════════════════════════════

def render_report(inventory: dict, ledger: dict[str, str]) -> str:
    rows = inventory.get("routes", [])
    measured = inventory.get("measured_at") or "미기재"

    def tally(key: str) -> list[tuple[str, int]]:
        c: dict[str, int] = {}
        for r in rows:
            c[r[key]] = c.get(r[key], 0) + 1
        return sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))

    by_app: dict[str, dict[str, int]] = {}
    for r in rows:
        slot = by_app.setdefault(r["app"], {"routes": 0, "accepts": 0, "open": 0, "scoped": 0})
        slot["routes"] += 1
        slot["accepts"] += r["inbound_key"] == "accepts"
        slot["open"] += r["inbound_key"] == "open_anonymous"
        slot["scoped"] += r["tenant_scope"] == "required"

    out: list[str] = []
    add = out.append
    add("# 라우트 인벤토리 — 전수 %d건 [실측 %s]\n" % (len(rows), measured))
    add("> D-343 ①②. `docker exec gx-shell python /repo/scripts/probe_route_inventory.py` 가 낸다.")
    add("> 런타임 ninja 레지스트리 전수 — 정적 grep 이 아니다.\n")
    add("> **이 표는 세 번 쓴다** (D-343 ▣): F-05 연동 규격서 부록 · 상용 API 문서 초안 ·")
    add("> 파트너 기술 검토 자료.\n")

    add("## 1. 들어오는 키 (inbound key) — 지금 어디까지 닿나\n")
    add("| 상태 | 건수 | 뜻 |")
    add("|---|---:|---|")
    meaning = {
        "accepts": "**지금 키가 닿는다.** dj-core `CustomJWTAuth` 가 받는다 — 좁혀지지 않은 자리",
        "declared": "우리가 `inbound_key=True` 로 **선언해서** 연 자리 (사유 기재)",
        "refuses": "우리 문지기 `JwtOrInboundKey` 가 기본값 거절로 막는다",
        "open_anonymous": "**인증 콜백이 없다.** 키를 검사하지도 않는다 — 「거절」이 아니다",
        "unknown": "우리가 모르는 인증 클래스. 모른다고 적는다 (D-301)",
    }
    for name, n in tally("inbound_key"):
        add("| `%s` | %d | %s |" % (name, n, meaning.get(name, "")))

    add("\n## 2. 3갈래 분류 — 기본값은 좁은 쪽 (D-343 ②)\n")
    c: dict[str, int] = {}
    for v in ledger.values():
        c[v] = c.get(v, 0) + 1
    add("| 갈래 | 건수 |")
    add("|---|---:|")
    for name in CLASSES:
        add("| `%s` | %d |" % (name, c.get(name, 0)))
    add("\n대장: `route_classes.yaml` · 래칫 기준선: `route_baseline.txt`")

    add("\n## 3. 테넌트 범위 검사\n")
    add("| 상태 | 건수 |")
    add("|---|---:|")
    for name, n in tally("tenant_scope"):
        add("| `%s` | %d |" % (name, n))

    add("\n## 4. 앱별 (상위 20)\n")
    add("| 앱 | 라우트 | 키가 닿음 | 관문 없음 | 테넌트 범위 |")
    add("|---|---:|---:|---:|---:|")
    for app, s in sorted(by_app.items(), key=lambda kv: -kv[1]["routes"])[:20]:
        add("| `%s` | %d | %d | %d | %d |"
            % (app, s["routes"], s["accepts"], s["open"], s["scoped"]))

    add("\n## 5. 지금 키를 받겠다고 **선언한** 자리\n")
    declared = [r for r in rows if r["inbound_key"] == "declared"]
    if declared:
        add("| 메서드 | 경로 | 사유 |")
        add("|---|---|---|")
        for r in declared:
            add("| %s | `%s` | %s |" % (r["method"], r["path"], r["inbound_key_reason"] or "—"))
    else:
        add("없음.")

    add("\n## 6. 인증 콜백이 없는 자리 (관문 없음)\n")
    anon = [r for r in rows if r["inbound_key"] == "open_anonymous"]
    add("전수 %d건. 그중 `@path_permission` 이 **활성**인 것 %d건 —"
        % (len(anon), sum(1 for r in anon if r["authz_path_permission"])))
    add("그 자리는 `probe_authn_gap_calls.py` 가 **호출로** 재고 결과를 "
        "`authn_gap_calls.json` 에 남긴다 (D-210 · D-342).\n")
    add("| 메서드 | 경로 | authz |")
    add("|---|---|---|")
    for r in anon:
        add("| %s | `%s` | %s |" % (r["method"], r["path"],
                                    "활성" if r["authz_path_permission"] else "없음"))
    return "\n".join(out) + "\n"


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    """★ 출생 표본 [실측 2026-09-07 · 사고 ②]:

    발급된 키 하나가 F-05 진입면 7자리에 닿았고 거기 `/clip/stream` 이 있었다.
    그 상태를 이 게이트에 넣으면 **잡혀야 한다** — 코드가 키를 받는데 대장에 없는 상태.
    거기서 초록이 나오면 이 게이트는 사고 ②를 다시 놓친다.
    """
    checks: list[tuple[str, bool]] = []

    def inv(rows):
        return {"measured_at": date.today().isoformat(), "routes": rows}

    stream = {"method": "GET", "path": "/api/dsm/events/{id}/clip/stream",
              "inbound_key": "declared", "classification": "inbound_key_allowed"}
    events = {"method": "GET", "path": "/api/dsm/events",
              "inbound_key": "declared", "classification": "inbound_key_allowed"}
    ui = {"method": "GET", "path": "/api/terminals/terminals",
          "inbound_key": "accepts", "classification": "session_only"}

    base = {"declared": 1, "open_anonymous": 0}

    # ★ 출생 표본 — clip/stream 이 키를 받는데 대장에 없다
    p, _ = judge(inv([events, stream]),
                 {"GET /api/dsm/events": "inbound_key_allowed",
                  "GET /api/dsm/events/{id}/clip/stream": "session_only"}, base)
    checks.append(("★ 출생표본 — 코드가 연 자리를 대장이 모르면 잡는다",
                   any("대장이 거짓말" in x for x in p)))
    checks.append(("★ 출생표본 — 그 때 declared 래칫도 함께 운다",
                   any("declared 가 늘었다" in x for x in p)))

    # 음성 대조 — 맞게 선언된 하나짜리는 통과한다
    p, _ = judge(inv([events, ui]),
                 {"GET /api/dsm/events": "inbound_key_allowed",
                  "GET /api/terminals/terminals": "session_only"}, base)
    checks.append(("음성 대조 — 대장과 코드가 맞으면 통과한다", not p))

    # 대장에 없는 새 라우트
    p, _ = judge(inv([events, ui]), {"GET /api/dsm/events": "inbound_key_allowed"}, base)
    checks.append(("새 라우트가 대장에 없으면 잡는다", any("대장에 없는 라우트" in x for x in p)))

    # 대장이 허가증이 되는 경우
    p, _ = judge(inv([ui]), {"GET /api/terminals/terminals": "inbound_key_allowed"},
                 {"declared": 0, "open_anonymous": 0})
    checks.append(("대장만 허가한 자리를 잡는다", any("허가증" in x for x in p)))

    # 3갈래 밖
    p, _ = judge(inv([ui]), {"GET /api/terminals/terminals": "maybe"},
                 {"declared": 0, "open_anonymous": 0})
    checks.append(("3갈래 밖의 분류를 잡는다", any("3갈래 밖" in x for x in p)))

    # 빈 인벤토리는 초록이 아니다 (D-301)
    p, _ = judge(inv([]), {}, base)
    checks.append(("빈 인벤토리는 초록이 아니다 (D-301)", any("열거기 고장" in x for x in p)))

    # open_anonymous 래칫
    anon = {"method": "GET", "path": "/api/x", "inbound_key": "open_anonymous",
            "classification": "session_only"}
    p, _ = judge(inv([anon]), {"GET /api/x": "session_only"},
                 {"declared": 0, "open_anonymous": 0})
    checks.append(("관문 없는 자리가 늘면 잡는다", any("open_anonymous 가 늘었다" in x for x in p)))

    # 대장 파서
    parsed = parse_ledger('# 주석\nroutes:\n  "GET /a": session_only\n  "POST /b": internal_only\n')
    checks.append(("대장 파서가 두 줄을 읽는다",
                   parsed == {"GET /a": "session_only", "POST /b": "internal_only"}))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[ROUTE-LEDGER] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="사람이 읽는 표를 INVENTORY.md 로 쓴다 (D-343 ▣ — 한 번 만들어 세 번 쓴다)")
    ap.add_argument("--max-age-days", type=int, default=None)
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not INVENTORY.exists():
        print("[ROUTE-LEDGER] 인벤토리가 없다: %s" % INVENTORY)
        print("[ROUTE-LEDGER] docker exec gx-shell python /repo/scripts/probe_route_inventory.py")
        return 1

    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = inventory.get("routes", [])
    ledger = parse_ledger(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}

    if args.freeze:
        LEDGER.write_text(render_ledger(rows, ledger), encoding="utf-8")
        counts = {
            "declared": sum(1 for r in rows if r["inbound_key"] == "declared"),
            "open_anonymous": sum(1 for r in rows if r["inbound_key"] == "open_anonymous"),
        }
        BASELINE.write_text(
            _BASELINE_HEADER + "".join("%s\t%d\n" % kv for kv in sorted(counts.items())),
            encoding="utf-8")
        print("[ROUTE-LEDGER] 대장 %d건 · 기준선 declared=%d open_anonymous=%d 로 잠갔다"
              % (len(rows), counts["declared"], counts["open_anonymous"]))
        return 0

    if args.report:
        (EVIDENCE / "INVENTORY.md").write_text(render_report(inventory, ledger), encoding="utf-8")
        print("[ROUTE-LEDGER] → %s" % (EVIDENCE / "INVENTORY.md"))
        return 0

    baseline = parse_baseline(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    problems, counts = judge(inventory, ledger, baseline, args.max_age_days)

    print("[ROUTE-LEDGER] [입력] 라우트 %d건 · 대장 %d건 (인벤토리 측정일 %s)"
          % (counts["routes"], counts["ledger"], inventory.get("measured_at") or "미기재"))
    print("[ROUTE-LEDGER] 들어오는 키: 선언 %d · 지금 닿는 자리 %d · 관문 없음 %d"
          % (counts["declared"], counts["accepts"], counts["open_anonymous"]))

    if args.list:
        by_class: dict[str, int] = {}
        for v in ledger.values():
            by_class[v] = by_class.get(v, 0) + 1
        for k, v in sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0])):
            print("  %6d  %s" % (v, k))
        for r in rows:
            if r["inbound_key"] in ("declared", "open_anonymous"):
                print("  %-14s %-6s %s" % (r["inbound_key"], r["method"], r["path"]))

    if problems:
        for p in problems:
            print("[ROUTE-LEDGER] FAIL %s" % p)
        return 1
    print("[ROUTE-LEDGER] 대장과 코드가 갈리지 않았다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
