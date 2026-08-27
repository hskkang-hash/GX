# -*- coding: utf-8 -*-
"""P0 모델의 격리 시험 `Target` **초안**을 만든다 — ④ 준비 (D-262 ② · D-266).

왜 이 스크립트인가
-------------------
W0-14b 를 죽인 것은 격리 로직이 아니라 **배선**이었다. 실측된 결함 4종 중 가장 큰 것이
**필수 FK 24건** — `Order.recipient_address` · `ChecklistSetting.category` ·
`SurveillanceProfile.mission` · `HandoverDocument.shift` 같은 것들이 없어서
시험이 **판정에 도달하기 전에 죽었다**.

이제 P0 **19종**을 시험에 올려야 한다(D-262 ②). 같은 일을 19번 되풀이하면
기동본 세션이 배선 디버깅으로 끝난다. 그래서 **미리 정적으로 뽑는다**:

  · 어떤 라우트가 이 모델을 만지는가        → `route_model_map.json` (AST 실측 · 등록 확인분)
  · 레코드 하나를 만들려면 무엇이 필요한가   → 모델 선언을 AST 로 읽어 **필수 필드**를 뽑는다
                                              (`null=True` 도 `default=` 도 없는 필드)

한계를 먼저 적는다 — 이것은 **초안**이지 정답이 아니다
------------------------------------------------------
  · **dj-core 의 부모 클래스 필드는 보이지 않는다.** `core.base.BaseModel` 은 저장소 밖이다.
    저장소 안 부모(`common/measurable_model.py` 등)는 따라가지만, 외부 부모는 **표시만** 한다.
  · 실제 시험 통과 여부는 **기동본에서만** 안다. `manage.py` 가 없는 곳에서 만든 초안이다.
  · 그러므로 이 산출물을 그대로 `MODELS` 에 붙여넣지 **않는다.** 기동본에서 하나씩 확인하며 올린다.
    W0-14b 의 교훈이 정확히 그것이다 — 추정한 경로 위에 배선을 쌓으면 전부 다시 해야 한다.

사용
----
    python scripts/draft_isolation_targets.py            # 표 (사람이 읽는 용)
    python scripts/draft_isolation_targets.py --py       # Target(...) 초안 코드
    python scripts/draft_isolation_targets.py --md > docs/agent/evidence/W0-14/p0_target_draft.md
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
TARGETS = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "leak_targets.json"
RMAP = ROOT / "docs" / "agent" / "evidence" / "W0-14" / "route_model_map.json"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

PK_SEG = re.compile(r"\{[^}]+\}")

#: 값을 주지 않아도 되는 필드 종류 — 자동으로 채워지거나 pk 다.
AUTO_FIELDS = {"AutoField", "BigAutoField", "SmallAutoField", "UUIDField"}

#: WP-DA2 착수를 막는 2종 (D-266) — 이 초안에서도 최우선으로 표시한다.
DA2_BLOCKERS = {"flight_log.FlightLog", "surveillance.VideoAnalysis"}


# ---------------------------------------------------------------------------
def model_class_index() -> dict[str, tuple[Path, ast.ClassDef]]:
    """'app.Model' → (파일, 클래스 노드). models 모듈만 본다."""
    out: dict[str, tuple[Path, ast.ClassDef]] = {}
    for path in BACKEND.rglob("*.py"):
        parts = path.relative_to(BACKEND).parts
        if "__pycache__" in parts or "migrations" in parts:
            continue
        if "models" not in {parts[-1].removesuffix(".py"), *parts[:-1]}:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        app = parts[0]
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                out[f"{app}.{node.name}"] = (path, node)
    return out


def _kw(call: ast.Call, name: str):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def _is_true(node) -> bool:
    return isinstance(node, ast.Constant) and node.value is True


def fields_of(cls: ast.ClassDef) -> list[dict]:
    """클래스 **자신이 선언한** 필드. 부모 필드는 따로 처리한다."""
    out = []
    for stmt in cls.body:
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        tgt = stmt.targets[0]
        if not isinstance(tgt, ast.Name) or not isinstance(stmt.value, ast.Call):
            continue
        func = stmt.value.func
        ftype = getattr(func, "attr", None) or getattr(func, "id", None)
        if not ftype or not ftype.endswith("Field") and ftype not in {
            "ForeignKey", "OneToOneField", "ManyToManyField",
        }:
            continue
        call = stmt.value
        nullable = _is_true(_kw(call, "null"))
        has_default = _kw(call, "default") is not None
        auto = _is_true(_kw(call, "auto_now")) or _is_true(_kw(call, "auto_now_add"))
        rel = None
        if ftype in {"ForeignKey", "OneToOneField", "ManyToManyField"} and call.args:
            a = call.args[0]
            rel = getattr(a, "id", None) or (a.value if isinstance(a, ast.Constant) else None) \
                or getattr(a, "attr", None)
        out.append({
            "name": tgt.id,
            "type": ftype,
            "required": not (nullable or has_default or auto or ftype in AUTO_FIELDS
                             or ftype == "ManyToManyField"),
            "relation": rel,
        })
    return out


def bases_of(cls: ast.ClassDef) -> list[str]:
    out = []
    for b in cls.bases:
        n = getattr(b, "id", None) or getattr(b, "attr", None)
        if n:
            out.append(n)
    return out


def required_fields(label: str, index: dict, seen: set[str] | None = None) -> tuple[list[dict], list[str]]:
    """필수 필드 + **보지 못한 외부 부모** 목록."""
    seen = seen or set()
    if label in seen or label not in index:
        return [], []
    seen.add(label)
    _path, cls = index[label]
    req = [f for f in fields_of(cls) if f["required"]]
    external: list[str] = []
    app = label.split(".")[0]
    for base in bases_of(cls):
        # 같은 앱 → 다른 앱 순으로 부모를 찾는다. 못 찾으면 저장소 밖(dj-core)이다.
        cand = f"{app}.{base}"
        if cand not in index:
            cand = next((k for k in index if k.endswith("." + base)), None)
        if cand:
            r, e = required_fields(cand, index, seen)
            req += r
            external += e
        elif base not in {"object", "models.Model", "Model"}:
            external.append(base)
    return req, external


# ---------------------------------------------------------------------------
def build() -> list[dict]:
    if not TARGETS.exists() or not RMAP.exists():
        raise SystemExit(
            "[DRAFT] 입력이 없다. 먼저:\n"
            "  python scripts/map_routes_to_models.py --json\n"
            "  python scripts/build_leak_targets.py --json"
        )
    tdoc = json.loads(TARGETS.read_text(encoding="utf-8"))
    rdoc = {m["label"]: m for m in json.loads(RMAP.read_text(encoding="utf-8"))["models"]}
    index = model_class_index()

    out = []
    for row in tdoc["targets"]:
        if row["priority"] != "P0":
            continue
        label = row["label"]
        routes = (rdoc.get(label) or {}).get("routes", {})
        req, external = required_fields(label, index)
        # 같은 이름이 부모에서 다시 선언될 수 있다 — 뒤엣것을 버린다
        uniq, seen_n = [], set()
        for f in req:
            if f["name"] not in seen_n:
                seen_n.add(f["name"])
                uniq.append(f)
        out.append({
            "label": label,
            "rows": row["rows"],
            "orphan_pct": row["orphan_pct"],
            "blocker": label in DA2_BLOCKERS,
            "in_index": label in index,
            "required": uniq,
            "required_fk": [f for f in uniq if f["relation"]],
            "external_bases": sorted(set(external)),
            "list": [e for e in routes.get("list", []) if e.get("registered")],
            "detail": [e for e in routes.get("detail", []) if e.get("registered")],
            "write": [e for e in routes.get("write", []) if e.get("registered")],
        })
    # 착수 순서: D-266 2종 먼저, 그 다음 배선이 쉬운 것(필수 FK 적은 것)부터
    out.sort(key=lambda r: (not r["blocker"], len(r["required_fk"]), -r["rows"]))
    return out


def _pk_path(entries: list[dict]) -> str | None:
    for e in entries:
        if PK_SEG.search(e["path"]):
            return f'{e["method"]} {e["path"]}'
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--py", action="store_true", help="Target(...) 초안 코드")
    ap.add_argument("--md", action="store_true", help="마크다운 표")
    args = ap.parse_args()
    rows = build()

    if args.py:
        print("# ⚠ 초안이다. 기동본에서 하나씩 확인하며 MODELS 에 올린다 (W0-14b 교훈).")
        print("# 필수 FK 는 Deps 헬퍼로 만든다. 외부 부모(dj-core)의 필수 필드는 여기 없다.")
        for r in rows:
            det, wr = _pk_path(r["detail"]), _pk_path(r["write"])
            lst = r["list"][0]["path"] if r["list"] else None
            app, name = r["label"].split(".")
            fk = ", ".join(f'"{f["name"]}": d.{f["relation"].lower() if f["relation"] else "?"}()'
                           for f in r["required_fk"]) or ""
            print(f'\n    # {r["label"]} — 행 {r["rows"]:,} · 필수FK {len(r["required_fk"])}'
                  + ("  ★ D-266 선결" if r["blocker"] else ""))
            print(f'    Target(\n        "{name}", "{app}", "{name}",')
            print(f'        list_path={lst!r},' if lst else "        # list_path: NO_ROUTE 사유 필요")
            print(f'        detail=Route({det.split(" ")[0]!r}, {det.split(" ")[1]!r}),' if det
                  else "        # detail: NO_ROUTE 사유 필요")
            if wr:
                print(f'        # 쓰기 후보: {wr}  ← 수정/삭제 구분은 기동본에서 확인')
            print(f'        factory=lambda d, n: {{{fk}}},' if fk
                  else "        factory=lambda d, n: {},   # 필수 FK 없음(정적 판정)")
            print("    ),")
        return 0

    if args.md:
        print("| # | 모델 | 행 | group NULL | 필수 FK | 단건 경로 | 외부 부모 |")
        print("|---:|---|---:|---:|---:|---|---|")
        for i, r in enumerate(rows, 1):
            det = _pk_path(r["detail"]) or _pk_path(r["write"]) or "—"
            star = " ★" if r["blocker"] else ""
            fk = ", ".join(f'`{f["name"]}`→{f["relation"]}' for f in r["required_fk"]) or "없음"
            print(f'| {i} | `{r["label"]}`{star} | {r["rows"]:,} | {r["orphan_pct"]}% | '
                  f'{fk} | `{det}` | {", ".join(r["external_bases"]) or "—"} |')
        return 0

    print(f"[DRAFT] P0 {len(rows)}종 · 착수 순서 = D-266 선결 2종 → 필수 FK 적은 순")
    nofk = sum(1 for r in rows if not r["required_fk"])
    print(f"[DRAFT] 필수 FK 가 **없는** 모델 {nofk}종 — 배선이 가장 싸다. 여기서 먼저 초록을 만든다")
    miss = [r["label"] for r in rows if not r["in_index"]]
    if miss:
        print(f"[DRAFT] ⚠ 모델 선언을 찾지 못한 것 {len(miss)}종: {miss} — 사람이 볼 것")
    print()
    for i, r in enumerate(rows, 1):
        det = _pk_path(r["detail"]) or _pk_path(r["write"]) or "단건 경로 없음"
        star = "★" if r["blocker"] else " "
        print(f"  {star}{i:>2}. {r['label']:<44} 행 {r['rows']:>6}  필수FK {len(r['required_fk'])}  {det[:64]}")
        if r["required_fk"]:
            print("        필요: " + ", ".join(f'{f["name"]}→{f["relation"]}' for f in r["required_fk"]))
        if r["external_bases"]:
            print(f"        ⚠ 외부 부모(정적 분석이 못 봄): {', '.join(r['external_bases'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
