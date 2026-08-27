# -*- coding: utf-8 -*-
"""라우트가 **실제로 만지는 모델**을 소스에서 추적한다 — 앱 단위 매칭의 대체 (D-263).

왜 이 스크립트인가
-------------------
`build_leak_targets.py` 1차판은 **모델 이름과 경로 세그먼트**를 맞춰 후보를 뽑았다.
그 방식의 한계가 실측으로 드러났다:

  · 앱 단위 슬러그를 넣으면 `delivery` 12모델이 **똑같이** "단건 23건"이 된다 —
    수가 커서 진척처럼 보이지만 **아무것도 구별하지 못하는 수**다. (D-263 이 금지했다)
  · 앱 슬러그를 빼면 이번엔 **동사형 경로를 놓친다** — 이 저장소는
    `POST /{id}/change-status` · `POST /{id}/cancel-order` 처럼 모델 이름이
    경로에 안 나오는 라우트가 흔하다. 그래서 P2 가 99종이 됐다.

**둘 다 이름을 보고 있었다는 것이 문제다.** 이 스크립트는 이름 대신 **코드**를 본다:
핸들러 본문(과 그것이 부르는 저장소 안 함수들)에서 **어떤 모델 클래스를 참조하는가**를 AST 로 센다.

  라우트 → 핸들러 → (호출한 함수들) → 모델 클래스

D-263 의 "모델별 실경로 매칭"이 이것이다. 결과는 후보가 아니라 **근거(파일·행)를 가진 매핑**이다.

★ Django 를 import 하지 않는다. AST 로만 읽으므로 dj-core 없이 어느 머신에서나 돈다.
★ 그래도 **판정은 사람이 한다.** 이 매핑은 "이 라우트가 이 모델을 만진다"는 정적 근거이지,
  "그러므로 격리돼 있다/아니다"가 아니다. 자동 분류를 면제로 쓰면 D-263 이 금지한 그 상태가 된다.

사용법
------
    python scripts/map_routes_to_models.py             # 요약
    python scripts/map_routes_to_models.py --json      # evidence 로 저장
    python scripts/map_routes_to_models.py --model orders.Order   # 한 모델의 근거 전문
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"

# ★ 추적기는 `backend/common/ast_call_trace.py` 로 올렸다 — `common.tenant_tripwire`(D-275 §5-1
#   트립와이어)가 **같은 판정기**를 써야 하기 때문이다. 두 벌을 두면 두 판정이 갈라지고,
#   갈라진 판정은 어느 쪽이 사실인지 아무도 모르는 상태가 된다.
sys.path.insert(0, str(BACKEND))
from common.ast_call_trace import (          # noqa: E402
    GENERIC_CALLS,
    MAX_DEPTH,
    index_functions as _index_functions,
    index_models as _index_models,
    extract_controller_routes as _extract_controller_routes,
    models_touched,
    module_dotted as _module_dotted,
    parse_all as _parse_all,
    refs_in,
)
ROUTES_JSON = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "openapi_routes.json"
CENSUS = ROOT / "docs" / "agent" / "evidence" / "W0-13" / "backfill_dryrun.txt"
OUT = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "route_model_map.json"


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

PK_SEG = re.compile(r"\{[^}]+\}")
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CENSUS_ROW = re.compile(r"^([a-z_]+)\.([A-Za-z_][A-Za-z0-9_]*)\s+\d+\s+\d+\s+\d+\s+")


# ---------------------------------------------------------------------------
# 0. 소스 색인 — 파일을 한 번만 읽고 AST 를 재사용한다
# ---------------------------------------------------------------------------
def parse_all() -> dict[Path, ast.Module]:
    return _parse_all(BACKEND)


# ---------------------------------------------------------------------------
# 1. 모델 클래스 색인 — `*/models.py` · `*/models/*.py` 안의 클래스
# ---------------------------------------------------------------------------
def index_models(trees: dict[Path, ast.Module]) -> tuple[dict[str, set[str]], set[str]]:
    """(클래스명 색인, 인구조사 라벨). 색인은 공용 추적기가, 인구조사는 여기가 만든다."""
    by_name = _index_models(BACKEND, trees)

    census: set[str] = set()
    if CENSUS.exists():
        for line in CENSUS.read_text(encoding="utf-8", errors="replace").splitlines():
            m = CENSUS_ROW.match(line.strip())
            if m:
                census.add(f"{m.group(1)}.{m.group(2)}")
    return by_name, census


# ---------------------------------------------------------------------------
# 2. 함수 색인 — 호출을 따라가기 위해
# ---------------------------------------------------------------------------


def module_dotted(path: Path) -> str:
    return _module_dotted(BACKEND, path)


def index_functions(
    trees: dict[Path, ast.Module],
) -> tuple[dict[Path, dict[str, ast.AST]], dict[Path, set[Path]]]:
    return _index_functions(BACKEND, trees)


# ---------------------------------------------------------------------------
# 4. 라우트 추출 — @api_controller(prefix) + @route.<verb>(subpath)
# ---------------------------------------------------------------------------
def extract_routes(trees: dict[Path, ast.Module]) -> list[dict]:
    return _extract_controller_routes(ROOT, trees)


# ---------------------------------------------------------------------------
# 5. 등록 라우트(런타임 실측)와 대조 — 소스에만 있는 것은 등록되지 않았을 수 있다
# ---------------------------------------------------------------------------
def load_registered() -> dict[str, list[str]]:
    if not ROUTES_JSON.exists():
        return {}
    return json.loads(ROUTES_JSON.read_text(encoding="utf-8"))["routes"]


def _norm(p: str) -> str:
    return PK_SEG.sub("{}", p).rstrip("/") or "/"


def resolve(ctrl_path: str, method: str, registered: dict[str, list[str]]) -> list[str]:
    """컨트롤러 경로를 등록 경로의 **접미사**로 맞춘다 (마운트 접두사는 소스에 없다)."""
    target = _norm(ctrl_path)
    hits = []
    for full, methods in registered.items():
        if method in methods and _norm(full).endswith(target):
            hits.append(full)
    return sorted(hits)


# ---------------------------------------------------------------------------
def build() -> dict:
    trees = parse_all()
    model_names, census = index_models(trees)
    funcs, imports = index_functions(trees)
    routes = extract_routes(trees)
    registered = load_registered()

    # ★ 버킷을 넷으로 가른다. `write`(pk 있음)와 `write_nopk`(본문으로 대상을 지목)는
    #   **성격이 다르다**. 섞으면 "단건 경로"가 부풀고, 그러면 P0 가 부푼다 —
    #   수가 커서 진척처럼 보이지만 구별하지 못하는 수가 또 나온다 (D-263 과 같은 결함).
    #   pk 없는 쓰기도 남의 테넌트 행을 건드릴 수 있으므로 **버리지 않고 따로 센다.**
    per_model: dict[str, dict] = defaultdict(
        lambda: {"list": [], "detail": [], "write": [], "write_nopk": [], "unregistered": []}
    )
    ambiguous_all: set[str] = set()
    unresolved = 0

    for r in routes:
        touched, amb = models_touched(
            r.pop("_node"), ROOT / r["file"], funcs, imports, model_names
        )
        ambiguous_all |= amb
        full_paths = resolve(r["ctrl_path"], r["method"], registered)
        if not full_paths:
            unresolved += 1
        has_pk = bool(PK_SEG.search(r["ctrl_path"]))
        bucket = (
            "detail"
            if (has_pk and r["method"] == "GET")
            else "write"
            if (has_pk and r["method"] in WRITE_METHODS)
            else "list"
            if r["method"] == "GET"
            else "write_nopk"          # 본문으로 대상을 지목하는 쓰기 — 단건 경로가 아니다
        )
        entry = {
            "method": r["method"],
            "path": full_paths[0] if full_paths else r["ctrl_path"],
            "registered": bool(full_paths),
            "evidence": f"{r['file']}:{r['line']} {r['handler']}()",
        }
        for label in touched:
            per_model[label][bucket if full_paths else "unregistered"].append(entry)

    rows = []
    for label in sorted(census | set(per_model)):
        m = per_model.get(label) or {
            "list": [], "detail": [], "write": [], "write_nopk": [], "unregistered": []
        }
        single = len(m["detail"]) + len(m["write"])   # **pk 를 지목하는 경로만** 센다
        rows.append(
            {
                "label": label,
                "in_census": label in census,
                "single_record_routes": single,
                "list_routes": len(m["list"]),
                "body_write_routes": len(m["write_nopk"]),
                "unregistered_routes": len(m["unregistered"]),
                "routes": m,
            }
        )

    return {
        "note": (
            "라우트 → 핸들러 → 호출 → 모델 을 AST 로 추적한 실경로 매핑 (D-263). "
            "앱 단위 매칭을 쓰지 않는다. 근거(파일:행)가 붙어 있으나 **격리 여부의 판정은 아니다**."
        ),
        "max_depth": MAX_DEPTH,
        "source_routes": len(routes),
        "registered_routes": sum(len(v) for v in registered.values()),
        "routes_not_resolved_to_registered": unresolved,
        "census_models": len(census),
        "models_with_any_route": sum(1 for r in rows if r["single_record_routes"] or r["list_routes"]),
        "ambiguous_class_names": sorted(ambiguous_all),
        "models": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--model", help="한 모델의 근거 전문")
    args = ap.parse_args()

    data = build()
    census_rows = [r for r in data["models"] if r["in_census"]]
    with_single = [r for r in census_rows if r["single_record_routes"]]
    with_any = [r for r in census_rows if r["single_record_routes"] or r["list_routes"]]

    print(f"[MAP] 소스 라우트 {data['source_routes']}건 · 등록 라우트 {data['registered_routes']}건 "
          f"· 등록본과 못 맞춘 소스 라우트 {data['routes_not_resolved_to_registered']}건")
    print(f"[MAP] 테넌트성 모델 {data['census_models']}종 중 "
          f"**라우트가 닿는 것 {len(with_any)}종** (단건 경로 있음 {len(with_single)}종)")
    print(f"[MAP] 라우트가 전혀 닿지 않는 것 {len(census_rows) - len(with_any)}종 "
          "— 이것이 '면제 후보'이고, 자동 면제하지 않는다 (D-263)")
    if data["ambiguous_class_names"]:
        print(f"[MAP] ⚠ 두 앱에 같은 이름의 모델 {len(data['ambiguous_class_names'])}건: "
              f"{data['ambiguous_class_names'][:8]} — 과다 포함됐을 수 있다. 사람이 볼 것")

    if args.model:
        r = next((x for x in data["models"] if x["label"] == args.model), None)
        if not r:
            print(f"[MAP] 그런 모델이 없다: {args.model}")
            return 1
        print(f"\n=== {r['label']} ===")
        for bucket in ("list", "detail", "write", "write_nopk", "unregistered"):
            for e in r["routes"][bucket]:
                print(f"  {bucket:<12} {e['method']:<6} {e['path']:<58} {e['evidence']}")
    else:
        print("\n  단건 경로가 닿는 상위 15종 (증거 기반)")
        for r in sorted(with_single, key=lambda x: -x["single_record_routes"])[:15]:
            ex = (r["routes"]["detail"] or r["routes"]["write"])[0]
            print(f"    {r['label']:<46} 단건 {r['single_record_routes']:>3}  {ex['evidence']}")

    if args.json:
        OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        print(f"\n[MAP] 저장: {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
