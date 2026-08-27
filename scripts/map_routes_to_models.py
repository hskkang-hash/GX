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
ROUTES_JSON = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "openapi_routes.json"
CENSUS = ROOT / "docs" / "agent" / "evidence" / "W0-13" / "backfill_dryrun.txt"
OUT = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "route_model_map.json"

#: 호출 그래프를 몇 단계까지 따라가나. 1 = 핸들러만 / 2 = 서비스 / 3 = 리포지토리.
#: 이 저장소는 뷰 → 서비스 → 리포지토리 3층이 흔하므로 3 을 쓴다.
MAX_DEPTH = 3

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
def iter_py() -> list[Path]:
    skip = {"__pycache__", "migrations", ".venv", "node_modules"}
    return [
        p
        for p in BACKEND.rglob("*.py")
        if not (set(p.parts) & skip)
    ]


def parse_all() -> dict[Path, ast.Module]:
    out: dict[Path, ast.Module] = {}
    for p in iter_py():
        try:
            out[p] = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        except SyntaxError:
            # 문법이 깨진 파일은 조용히 넘기지 않는다 — 세지 못한 것을 세지 못했다고 말해야 한다.
            print(f"[MAP] ⚠ 파싱 실패(건너뜀): {p.relative_to(ROOT)}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# 1. 모델 클래스 색인 — `*/models.py` · `*/models/*.py` 안의 클래스
# ---------------------------------------------------------------------------
def index_models(trees: dict[Path, ast.Module]) -> tuple[dict[str, set[str]], set[str]]:
    """클래스명 → {"app.Class", ...}. 같은 이름이 두 앱에 있으면 둘 다 담는다(모호로 표시)."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for path, tree in trees.items():
        parts = path.relative_to(BACKEND).parts
        if "models" not in {parts[-1].removesuffix(".py"), *parts[:-1]}:
            continue
        app = parts[0]
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                by_name[node.name].add(f"{app}.{node.name}")

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
#: 따라가지 않는 함수 이름 — 어느 모듈에나 있는 일반명이라 호출 그래프를 폭발시킨다.
#: (1차판이 이것을 안 막아 `ChecklistSetting` 이 "단건 313건"으로 나왔다 — 앱을 넘나든 결과다.)
GENERIC_CALLS = frozenset({
    "get", "all", "filter", "first", "last", "create", "update", "delete", "save",
    "count", "exists", "values", "values_list", "annotate", "order_by", "select_related",
    "prefetch_related", "len", "str", "int", "list", "dict", "set", "print", "format",
    "append", "join", "isinstance", "getattr", "setattr", "hasattr", "super", "range",
    "sorted", "map", "any", "all_objects", "json", "loads", "dumps", "now", "today",
})


def module_dotted(path: Path) -> str:
    """backend/flight_log/views.py → 'flight_log.views'"""
    rel = path.relative_to(BACKEND).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def index_functions(
    trees: dict[Path, ast.Module],
) -> tuple[dict[Path, dict[str, ast.AST]], dict[Path, set[Path]]]:
    """(모듈별 함수 색인, 모듈별 import 대상 모듈 집합).

    ★ 1차판은 **이름만으로** 함수를 찾았다. 그러면 `delivery` 의 헬퍼가 `flight_log` 의
      핸들러에 붙고, 그 결과가 "단건 313건" 같은 수다 — 수가 커서 진척처럼 보이지만
      **아무것도 구별하지 못하는 수**다. D-263 이 앱 단위 매칭을 금지한 것과 같은 결함이다.
      그래서 호출은 **그 모듈 자신 + 그 모듈이 실제로 import 한 모듈** 안에서만 해석한다.
    """
    dotted: dict[str, Path] = {module_dotted(p): p for p in trees}
    funcs: dict[Path, dict[str, ast.AST]] = {}
    imports: dict[Path, set[Path]] = {}

    for path, tree in trees.items():
        local: dict[str, ast.AST] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                local.setdefault(node.name, node)
        funcs[path] = local

        targets: set[Path] = set()
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                mods.append(node.module)
                # `from app.services import x` 뿐 아니라 `from app import services` 도 잡는다
                mods += [f"{node.module}.{a.name}" for a in node.names]
            elif isinstance(node, ast.Import):
                mods += [a.name for a in node.names]
            for m in mods:
                if m in dotted:
                    targets.add(dotted[m])
        imports[path] = targets
    return funcs, imports


# ---------------------------------------------------------------------------
# 3. 참조 수집 — 한 함수 본문이 만지는 모델 + 부르는 함수
# ---------------------------------------------------------------------------
def refs_in(node: ast.AST) -> tuple[set[str], set[str]]:
    """(참조한 클래스명, 호출한 함수명)

    ★ `Attribute.attr` 을 무조건 클래스명으로 세지 않는다. 그러면 메서드 이름이 모델 이름과
      겹칠 때마다 거짓 양성이 된다. **모듈 별칭 뒤에 올 때만** 센다 — `models.Order` 는 세고
      `foo.Order()` 도 세되, `x.save` 같은 것은 세지 않는다(어차피 모델명과 안 겹친다).
    """
    names: set[str] = set()
    calls: set[str] = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            names.add(n.id)
        elif isinstance(n, ast.Attribute):
            base = n.value
            if isinstance(base, ast.Name) and "model" in base.id.lower():
                names.add(n.attr)
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                calls.add(f.attr)
    return names, calls - GENERIC_CALLS


def models_touched(
    start: ast.AST,
    home: Path,
    funcs: dict[Path, dict[str, ast.AST]],
    imports: dict[Path, set[Path]],
    model_names: dict[str, set[str]],
) -> tuple[set[str], set[str]]:
    """핸들러에서 시작해 **import 그래프 안에서만** MAX_DEPTH 까지 따라간다."""
    seen: set[tuple[str, int]] = set()
    found: set[str] = set()
    ambiguous: set[str] = set()
    frontier: list[tuple[ast.AST, Path, int]] = [(start, home, 0)]

    while frontier:
        node, mod, depth = frontier.pop()
        names, calls = refs_in(node)
        for nm in names & model_names.keys():
            labels = model_names[nm]
            found |= labels
            if len(labels) > 1:
                ambiguous.add(nm)
        if depth >= MAX_DEPTH:
            continue
        # 해석 범위: 그 모듈 자신 + 그 모듈이 import 한 저장소 모듈
        scope = [mod, *sorted(imports.get(mod, ()))]
        for c in calls:
            # ★ **첫 해석에서 멈추지 않는다.** 그렇게 했더니 거짓 음성이 났다:
            #   flight_log 의 핸들러 `get_flight_log_detail` 이 **자기와 같은 이름의**
            #   서비스 메서드(FlightLogService.get_flight_log_detail)를 가려서,
            #   해석이 자기 자신으로 끝나고 서비스에 닿지 못했다.
            #   그 결과 FlightLog 는 "detail 라우트 없음"이 됐다 — 즉 **조용한 면제**다(D-263).
            #   이제 스코프 안의 해석을 전부 본다. 스코프가 import 로 이미 좁혀져 있으므로
            #   1차판의 전역 이름 탐색 같은 폭주는 나지 않는다.
            hits = 0
            for m in scope:
                fn = funcs.get(m, {}).get(c)
                if fn is None or fn is node:
                    continue
                key = (f"{m}:{c}", depth)
                if key in seen:
                    continue
                seen.add(key)
                frontier.append((fn, m, depth + 1))
                hits += 1
                if hits >= 3:  # 한 이름당 3개까지 — 상한은 두되 첫 하나로 끊지 않는다
                    break
    return found, ambiguous


# ---------------------------------------------------------------------------
# 4. 라우트 추출 — @api_controller(prefix) + @route.<verb>(subpath)
# ---------------------------------------------------------------------------
def _str_arg(call: ast.Call) -> str:
    for a in call.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return a.value
    return ""


def extract_routes(trees: dict[Path, ast.Module]) -> list[dict]:
    out: list[dict] = []
    for path, tree in trees.items():
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            prefix = None
            for d in cls.decorator_list:
                call = d if isinstance(d, ast.Call) else None
                fname = getattr(getattr(call, "func", d), "id", None) or getattr(
                    getattr(call, "func", d), "attr", None
                )
                if fname == "api_controller":
                    prefix = _str_arg(call) if call else ""
            if prefix is None:
                continue
            for fn in cls.body:
                if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for d in fn.decorator_list:
                    if not isinstance(d, ast.Call):
                        continue
                    f = d.func
                    if not (isinstance(f, ast.Attribute) and getattr(f.value, "id", "") == "route"):
                        continue
                    verb = f.attr.upper()
                    sub = _str_arg(d)
                    out.append(
                        {
                            "method": verb,
                            "ctrl_path": ("/" + prefix.strip("/") + "/" + sub.strip("/")).replace(
                                "//", "/"
                            ).rstrip("/")
                            or "/",
                            "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                            "line": fn.lineno,
                            "handler": fn.name,
                            "_node": fn,
                        }
                    )
    return out


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
