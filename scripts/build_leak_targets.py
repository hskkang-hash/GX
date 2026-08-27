# -*- coding: utf-8 -*-
"""격리 시험이 **보지 않고 있는 것**을 센다 — W0-14c 의 작업 목록 생성기 (D-260).

왜 이 스크립트인가
-------------------
W0-14c 를 "648 라우트에 데코레이터 붙이기"로 읽으면 O(648) 이고, 그 부착률은
**EXIT 기준이 아니다**(D-249 · `evidence/W0-14/coverage.md` §3 "부착률을 성과로 읽지 말 것").
EXIT 기준은 **재현 누출 0건**이다.

그런데 "누출 0건"은 **모수를 밝히지 않으면 판정 자체가 성립하지 않는다.**
지금 격리 시험(`backend/tests/test_tenant_isolation.py`)의 `MODELS` 레지스트리는
**10종**이고, W0-13 이 실측한 테넌트성 모델은 **131종**이다.
나머지 121종에 대해 우리가 말할 수 있는 것은 "누출이 없다"가 아니라 **"모른다"** 다.

이 스크립트는 그 간격을 센다. 누출을 고치지 않는다 — 무엇을 보지 않고 있었는지까지다.

▲ **2026-08-27 2차 (D-263) — 이름 매칭을 폐기했다.**
   1차판은 모델 이름과 경로 세그먼트를 맞췄다. 그 방식은 두 방향으로 다 틀렸다:
   앱 슬러그를 넣으면 `delivery` 12모델이 똑같이 "단건 23건"이 되고(구별력 0),
   빼면 동사형 경로(`POST /{id}/cancel-order`)를 놓쳐 P2 가 99종으로 부풀었다.
   지금은 `scripts/map_routes_to_models.py` 가 **핸들러가 실제로 만지는 모델**을 AST 로
   추적한 결과(`evidence/W0-14/route_model_map.json`)를 읽는다 — 근거는 파일:행이다.

★ **새로 정의하지 않는다. 이미 잰 것을 대조한다.** (지시서 v2.0 §0.1 원칙 1 — 재사용 우선)
   테넌트성 모델의 정의를 여기서 다시 만들면 그 수는 W0-13 의 수와 갈리고,
   **어느 쪽이 진실인지 아무도 모르게 된다** (D-227 manifest 유실과 같은 실패 모양).
   그래서 셋 다 **기존 실측본**을 입력으로 읽는다:

     (a) `docs/agent/evidence/W0-13/backfill_dryrun.txt`  — 테넌트성 모델 131종 (Django 실측)
     (b) `docs/agent/evidence/W0-14/route_model_map.json` — 라우트↔모델 실경로 매핑 (AST 실측)
     (c) `backend/tests/test_tenant_isolation.py`         — 현재 시험 대상 (AST · import 없음)

   그러므로 이 스크립트는 **Django 도 dj-core 도 필요 없다.** 어느 머신에서나 돈다.

⚠ **분류는 자동, 판정은 수동.** 이 스크립트가 뽑는 것은 **후보**다. "안전하다"고 말하지 않는다.
   자동 분류를 면제로 쓰면 `PUBLIC_ROUTES` 도피로(coverage.md §2)와 같은 착시가 된다 —
   미분류가 면제로 위장하면 시험은 초록이 되고 노출은 그대로 남는다.

사용법
------
    python scripts/build_leak_targets.py            # 요약 + 커버리지 델타
    python scripts/build_leak_targets.py --json     # 원자료를 evidence 로 저장
    python scripts/build_leak_targets.py --md       # 표를 마크다운으로 (증거 문서용)
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CENSUS = ROOT / "docs" / "agent" / "evidence" / "W0-13" / "backfill_dryrun.txt"
ROUTE_MAP = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "route_model_map.json"
SUITE = ROOT / "backend" / "tests" / "test_tenant_isolation.py"
OUT_JSON = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "leak_targets.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 인구조사 표의 한 줄 — `surveillance.MissionWaypoint  8877  8877 ...`
CENSUS_ROW = re.compile(
    r"^(?P<app>[a-z_]+)\.(?P<model>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?P<total>\d+)\s+(?P<cb_null>\d+)\s+(?P<grp_null>\d+)\s+(?P<both>\d+)\s+"
    r"(?P<r1>\d+)\s+(?P<r2>\d+)\s+(?P<r3>\d+)\s+(?P<note>.*)$"
)

#: 경로에 pk 자리가 있는가 — `/api/terminals/terminals/{id}` · `/delete/{ids}`
PK_SEG = re.compile(r"\{[^}]+\}")

#: 단건 쓰기로 읽는 메서드. GET 은 상세, 나머지는 쓰기.
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

#: WP-DA2(10월 코드) 착수를 막는 2종 — DSM App 이 직접 쓸 데이터다 (D-266).
DA2_BLOCKERS = frozenset({"flight_log.FlightLog", "surveillance.VideoAnalysis"})


# ---------------------------------------------------------------------------
# 입력 (a) — 테넌트성 모델 인구조사
# ---------------------------------------------------------------------------
def read_census() -> list[dict]:
    """W0-13 dry-run 의 표를 읽는다. **이 파일이 모델 목록의 정본이다.**"""
    if not CENSUS.exists():
        raise SystemExit(f"[TARGETS] 인구조사가 없다: {CENSUS.relative_to(ROOT)}")
    out: list[dict] = []
    for line in CENSUS.read_text(encoding="utf-8", errors="replace").splitlines():
        m = CENSUS_ROW.match(line.strip())
        if not m:
            continue
        d = m.groupdict()
        out.append(
            {
                "app_label": d["app"],
                "model_name": d["model"],
                "label": f"{d['app']}.{d['model']}",
                "rows": int(d["total"]),
                "group_null": int(d["grp_null"]),
                "orphan_pct": round(100.0 * int(d["grp_null"]) / int(d["total"]), 1)
                if int(d["total"])
                else 0.0,
            }
        )
    return out


# ---------------------------------------------------------------------------
# 입력 (b) — 등록된 라우트
# ---------------------------------------------------------------------------
def read_route_map() -> dict[str, dict]:
    """모델 → 라우트(근거 포함). `map_routes_to_models.py --json` 의 산출물."""
    if not ROUTE_MAP.exists():
        raise SystemExit(
            f"[TARGETS] 실경로 매핑이 없다: {ROUTE_MAP.relative_to(ROOT)}\n"
            "         먼저 `python scripts/map_routes_to_models.py --json` 을 돌려라."
        )
    doc = json.loads(ROUTE_MAP.read_text(encoding="utf-8"))
    return {m["label"]: m for m in doc["models"]}


# ---------------------------------------------------------------------------
# 입력 (c) — 지금 시험이 보는 대상 (AST — 모듈을 import 하지 않는다)
# ---------------------------------------------------------------------------
def read_suite_targets() -> set[str]:
    """`MODELS = (Target("Order", "orders", "Order", ...), ...)` 에서 (app, model) 을 뽑는다.

    import 하지 않는 이유: 이 파일은 Django 설정과 dj-core 를 요구한다.
    AST 로 읽으면 어느 머신에서나 돈다 — 그리고 **읽기만 한다.**
    """
    tree = ast.parse(SUITE.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        # `MODELS: tuple[Target, ...] = (...)` 는 **AnnAssign** 이다 — Assign 만 보면 0종이 나온다.
        # 처음 판이 그랬고, "시험이 아무것도 보지 않는다"는 결과가 나와서야 드러났다.
        if isinstance(node, ast.AnnAssign):
            names = {node.target.id} if isinstance(node.target, ast.Name) else set()
        elif isinstance(node, ast.Assign):
            names = {t.id for t in node.targets if isinstance(t, ast.Name)}
        else:
            continue
        if "MODELS" not in names or node.value is None:
            continue
        for call in ast.walk(node.value):
            if not (isinstance(call, ast.Call) and getattr(call.func, "id", "") == "Target"):
                continue
            args = [a.value for a in call.args if isinstance(a, ast.Constant)]
            if len(args) >= 3:
                out.add(f"{args[1]}.{args[2]}")
    return out


# ---------------------------------------------------------------------------
# 대조 — 모델 ↔ 라우트 후보
# ---------------------------------------------------------------------------
# ★ 이름 기반 매칭(`_slugs` · `match_routes`)은 **삭제했다** — D-263.
#   남겨 두면 언젠가 누군가 그것을 다시 쓴다. 대체본은 map_routes_to_models.py 다.


def build() -> dict:
    census = read_census()
    rmap = read_route_map()
    covered = read_suite_targets()

    rows: list[dict] = []
    for m in census:
        rec = rmap.get(m["label"]) or {}
        routes = rec.get("routes") or {
            "list": [], "detail": [], "write": [], "write_nopk": [], "unregistered": []
        }
        # 단건 = **pk 를 지목하는** 경로만. 본문으로 대상을 지목하는 쓰기는 따로 센다 —
        # 섞으면 "단건 경로"가 부풀고 P0 가 부푼다 (2026-08-27 3차 시정).
        single = len(routes["detail"]) + len(routes["write"])
        listing = len(routes["list"])
        body_write = len(routes.get("write_nopk", []))
        in_suite = m["label"] in covered

        # 분류 — **자동 면제는 없다.** UNREVIEWED 는 "모른다"의 이름이지 "안전하다"가 아니다.
        if in_suite:
            prio, why = "covered", "격리 시험 MODELS 레지스트리에 등재돼 있다"
        elif single and m["rows"] >= 50:
            prio, why = "P0", f"단건 경로 {single}건이 이 모델을 만지고, 행 {m['rows']}건이 실재한다"
        elif single or listing or body_write:
            prio, why = "P1", (
                f"라우트가 닿는다(단건 {single} · 목록 {listing} · 본문지목쓰기 {body_write}) — "
                f"행 {m['rows']}건으로 P0 문턱(50) 미만이거나 **pk 를 지목하는 경로가 없다**. "
                "본문지목쓰기는 남의 행을 건드릴 수 있으나 IDOR 배선이 달라 P1 로 둔다"
            )
        else:
            prio, why = "UNREVIEWED", (
                "핸들러 AST 추적에서 이 모델을 만지는 라우트를 찾지 못했다. "
                "**'라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다** — "
                "동적 디스패치·시그널·태스크 경로는 이 추적이 보지 못한다 (D-263)"
            )

        rows.append({
            **m,
            "in_suite": in_suite,
            "single_record_routes": single,
            "list_routes": listing,
            "body_write_routes": body_write,
            "unregistered_routes": len(routes.get("unregistered", [])),
            "priority": prio,
            "reason": why,
            "routes": routes,
        })

    rows.sort(key=lambda r: (
        {"P0": 0, "P1": 1, "UNREVIEWED": 2, "covered": 3}[r["priority"]],
        -r["single_record_routes"], -r["rows"],
    ))
    missing = sorted(covered - {r["label"] for r in rows})
    return {
        "note": (
            "W0-14c 작업 목록 (D-260 · D-262 · D-263). 라우트↔모델은 AST 실경로 추적본을 쓴다 — "
            "이름 매칭 폐기. ★ 분류는 자동, 판정은 수동. UNREVIEWED 는 면제가 아니다."
        ),
        "inputs": {
            "census": str(CENSUS.relative_to(ROOT)).replace("\\", "/"),
            "route_map": str(ROUTE_MAP.relative_to(ROOT)).replace("\\", "/"),
            "suite": str(SUITE.relative_to(ROOT)).replace("\\", "/"),
        },
        "tenant_models": len(rows),
        "in_suite": sum(1 for r in rows if r["in_suite"]),
        "not_in_suite": sum(1 for r in rows if not r["in_suite"]),
        "by_priority": {
            p: sum(1 for r in rows if r["priority"] == p)
            for p in ("P0", "P1", "UNREVIEWED", "covered")
        },
        "in_suite_but_not_in_census": missing,
        "targets": rows,
    }


def render_appendix(data: dict) -> str:
    """D-262 ③④ 의 산출물. **재생성 가능**해야 한다 — 손으로 쓰면 정본과 갈린다."""
    try:
        import importlib.util as _u
        _p = ROOT / "backend" / "tests" / "tenant_classification.py"
        _s = _u.spec_from_file_location("tenant_classification", _p)
        _m = _u.module_from_spec(_s)
        _s.loader.exec_module(_m)
        declared = {"shared": _m.SHARED_MASTERS, "unassigned": _m.TENANT_UNASSIGNED,
                    "deferred": _m.DEFERRED}
    except Exception as exc:      # 등록부를 못 읽으면 **비어 있다고 말한다** — 조용히 넘기지 않는다
        declared = {"shared": {}, "unassigned": {}, "deferred": {}}
        print(f"[TARGETS] ⚠ 분류 등록부를 읽지 못했다: {exc}", file=sys.stderr)

    bp = data["by_priority"]
    p1 = [r for r in data["targets"] if r["priority"] == "P1"]
    un = [r for r in data["targets"] if r["priority"] == "UNREVIEWED"]
    L: list[str] = []
    A = L.append

    A("# WP-2 EXIT 부록 — 무엇을 검증했고 무엇을 아직 모르는가 (D-262 ③④)")
    A("")
    A("**생성** `python scripts/build_leak_targets.py --appendix` · **결정** D-262 · D-263 · D-261")
    A("**입력** W0-13 인구조사 · 실경로 매핑(AST) · 격리 시험 AST · 분류 등록부")
    A("")
    A("> D-262 는 EXIT 문서가 **스스로** 무엇을 검증했고 무엇을 모르는지 말하게 하라고 했다.")
    A("> **모르는 것을 모른다고 적은 문서가, 다 안다고 적은 거짓 문서보다 납품에 강하다.**")
    A("> 에스비 검수의 \"보안 점검 통과\"(계획서 7장)도 이 문서로 답한다.")
    A("")
    A("| 구분 | 종 | EXIT 조건 |")
    A("|---|---:|---|")
    A(f"| 검증됨 (격리 시험 `MODELS`) | {bp['covered']} | ① 시나리오 5/5 |")
    A(f"| **P0 — 전수 시험 필요** | **{bp['P0']}** | ② **EXIT 필수** |")
    A(f"| P1 — 계획 등재 | {bp['P1']} | ③ EXIT 필수 아님 |")
    A(f"| UNREVIEWED — 사유 첨부 | {bp['UNREVIEWED']} | ④ **자동 면제 금지** |")
    A(f"| 합계 (테넌트성 모델) | {data['tenant_models']} | |")
    A("")
    A("---")
    A("")
    A(f"## 1. P1 {len(p1)}종 — 시험 계획 등재 (D-262 ③)")
    A("")
    A("**EXIT 필수가 아니다.** 착수는 WP-2 EXIT **후**, P0 가 닫힌 다음이다.")
    A("여기 적는 이유는 착수가 아니라 **모수를 밝히기 위해서**다 — 이 표가 없으면")
    A("\"P0 만 봤다\"와 \"P0 밖에 없다\"가 구별되지 않는다.")
    A("")
    A("| 모델 | 행 | group NULL | 단건 | 목록 | 본문지목쓰기 | 사유 |")
    A("|---|---:|---:|---:|---:|---:|---|")
    for x in sorted(p1, key=lambda z: -z["rows"]):
        A(f"| `{x['label']}` | {x['rows']:,} | {x['orphan_pct']}% | "
          f"{x['single_record_routes']} | {x['list_routes']} | "
          f"{x.get('body_write_routes', 0)} | {x['reason']} |")
    A("")
    A("> **본문지목쓰기**(pk 가 아니라 요청 본문으로 대상을 고르는 쓰기)가 있는 항목은")
    A("> IDOR 배선이 달라 P1 로 두었을 뿐 **위험이 없다는 뜻이 아니다.**")
    A("> 남의 테넌트 행을 건드릴 수 있고, 시험 방식만 다르다.")
    A("")
    A("---")
    A("")
    A(f"## 2. UNREVIEWED {len(un)}종 — 분류 사유 전건 (D-262 ④ · D-263)")
    A("")
    A("> ★ **면제가 아니다.** 기계 사유는 전건 같다 —")
    A("> \"핸들러 AST 추적에서 이 모델을 만지는 라우트를 **찾지 못했다**\".")
    A("> **'라우트 없음'이 아니라 '못 찾았다'** 로 읽어야 한다. 동적 디스패치·시그널·")
    A("> Celery 태스크 경로는 이 추적이 보지 못한다.")
    A("")
    A("아래 **선언** 열이 사람 판단이다. 선언된 것은 `backend/tests/tenant_classification.py` 에")
    A("근거와 함께 등재돼 있고, **격리 시험이 그 선언을 단언으로 지킨다**(D-261 b·c).")
    A("빈 칸은 **아직 아무도 판단하지 않았다**는 뜻이다 — 그것도 사실대로 적는다.")
    A("")
    A("| 모델 | 행 | group NULL | 선언 | 근거 |")
    A("|---|---:|---:|---|---|")
    n_declared = 0
    for x in sorted(un, key=lambda z: -z["rows"]):
        lab = x["label"]
        if lab in declared["shared"]:
            kind, why = "**shared** (전 테넌트 조회 가능)", declared["shared"][lab]
            n_declared += 1
        elif lab in declared["unassigned"]:
            kind, why = "**tenant_unassigned** (전역 관리자 외 비노출)", declared["unassigned"][lab]
            n_declared += 1
        elif lab in declared["deferred"]:
            kind, why = "deferred (별도 판단 필요)", declared["deferred"][lab]
            n_declared += 1
        else:
            kind, why = "— (미판단)", "라우트를 못 찾았다는 것 외에 아직 근거가 없다"
        A(f"| `{lab}` | {x['rows']:,} | {x['orphan_pct']}% | {kind} | {why} |")
    A("")
    A(f"**선언 {n_declared}종 · 미판단 {len(un) - n_declared}종** "
      f"(합계 {sum(x['rows'] for x in un):,}행).")
    A("")
    A("> 미판단이 남아 있는 채로 EXIT 하는 것은 **허용된다** — D-262 ④ 가 요구한 것은")
    A("> \"전부 판단하라\"가 아니라 \"각각의 분류 사유를 문서로 첨부하라\"이기 때문이다.")
    A("> 다만 **미판단을 판단으로 위장하지 않는다.** 이 표의 빈 칸이 그 정직함의 자리다.")
    A("")
    A("---")
    A("")
    A("## 3. 이 부록이 답하는 질문")
    A("")
    A("| 질문 | 답 |")
    A("|---|---|")
    A(f"| 테넌트 격리를 몇 종에서 시험했나 | 지금 {bp['covered']}종 → EXIT 시 {bp['covered'] + bp['P0']}종 |")
    A(f"| 시험하지 않은 것은 몇 종인가 | {bp['P1'] + bp['UNREVIEWED']}종 — 그리고 **각각의 사유가 위에 있다** |")
    A("| 시험하지 않은 것이 안전하다고 말하나 | **아니다.** 모른다고 말한다 |")
    A("| 그 상태로 납품이 되나 | 모수를 밝힌 문서가 판정 가능한 문서다. \"100%\" 라 적고 대상이 9종인 것보다 강하다 |")
    A("")
    A("## 4. 재생성")
    A("")
    A("```bash")
    A("python scripts/map_routes_to_models.py --json   # 라우트↔모델 (AST)")
    A("python scripts/build_leak_targets.py --json     # 분류")
    A("python scripts/build_leak_targets.py --appendix > docs/agent/evidence/W0-14/exit_coverage_appendix.md")
    A("```")
    A("")
    A("※ 손으로 고치지 않는다. 손으로 고치면 정본과 갈리고, 그때 어느 쪽이 진실인지 알 수 없게 된다.")
    return "\n".join(L)


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="원자료를 evidence 로 저장")
    ap.add_argument("--md", action="store_true", help="상위 표를 마크다운으로 출력")
    ap.add_argument("--appendix", action="store_true",
                    help="EXIT 부록(D-262 ③④) — P1 계획 + UNREVIEWED 전건 사유")
    args = ap.parse_args()

    data = build()
    bp = data["by_priority"]

    if args.appendix:
        print(render_appendix(data))
        return 0

    print(f"[TARGETS] 테넌트성 모델 {data['tenant_models']}종 (W0-13 실측)")
    print(f"[TARGETS] 격리 시험이 보는 것 {data['in_suite']}종 · **보지 않는 것 {data['not_in_suite']}종**")
    print(f"[TARGETS] P0={bp['P0']} (EXIT 필수 · D-262)  P1={bp['P1']} (계획 등재)  "
          f"UNREVIEWED={bp['UNREVIEWED']} (사유 첨부)")
    print("[TARGETS] ⚠ UNREVIEWED 는 **면제가 아니다.** '라우트 없음'이 아니라 "
          "'AST 추적이 못 찾았다'는 뜻이다 (D-263)")

    if data["in_suite_but_not_in_census"]:
        print(
            "[TARGETS] ⚠ 시험에는 있으나 인구조사에 없다: "
            f"{data['in_suite_but_not_in_census']} — 둘 중 하나가 틀렸다. 사람이 볼 것"
        )

    print()
    print("  P0 — EXIT 필수 (D-262 조건 ②). ★ 표시는 WP-DA2 선결 2종 (D-266)")
    for r in [x for x in data["targets"] if x["priority"] == "P0"]:
        ex = (r["routes"]["detail"] or r["routes"]["write"])[0]
        star = "★" if r["label"] in DA2_BLOCKERS else " "
        print(
            f"  {star} {r['label']:<44} 행 {r['rows']:>6}  고아 {r['orphan_pct']:>5}%  "
            f"단건 {r['single_record_routes']:>3}  {ex['evidence']}"
        )

    if args.md:
        print("\n| 모델 | 행 | group NULL | 단건 경로 | 우선 | 대표 경로 |")
        print("|---|---:|---:|---:|:--:|---|")
        for r in data["targets"]:
            if r["priority"] not in ("P0", "P1"):
                continue
            ex = (r["routes"]["detail"] or r["routes"]["write"] or [{"path": "-"}])[0]
            print(
                f"| `{r['label']}` | {r['rows']} | {r['orphan_pct']}% | "
                f"{r['single_record_routes']} | {r['priority']} | `{ex.get('path','-')}` |"
            )

    if args.json:
        OUT_JSON.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        print(f"\n[TARGETS] 저장: {OUT_JSON.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
