# -*- coding: utf-8 -*-
"""핸들러가 **실제로 만지는 모델**을 소스에서 추적한다 — 공용 추적기.

원본은 `scripts/map_routes_to_models.py` 에 있었다 (D-263 대응). 그 판정 논리를
`common.tenant_tripwire` 도 써야 하는데, 같은 추적을 두 벌 두면 **두 곳의 판정이 갈라진다** —
갈라진 판정은 어느 쪽이 사실인지 아무도 모르는 상태다. 그래서 여기로 올리고 둘 다 이것을 부른다.

Django 를 import 하지 않는다. AST 로만 읽으므로 dj-core 없이 어느 머신에서나 돈다.
pre-commit(장고 없음)과 시험(장고 있음)이 **같은 판정기**를 쓸 수 있는 이유가 이것이다.

★ 이 추적기는 "이 핸들러가 이 모델을 만진다"는 **정적 근거**이지, "그러므로 격리돼 있다/아니다"가
  아니다. 자동 분류를 면제로 쓰면 D-263 이 금지한 그 상태가 된다.
"""
from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path

#: 호출 그래프를 몇 단계까지 따라가나. 1 = 핸들러만 / 2 = 서비스 / 3 = 리포지토리.
#: 이 저장소는 뷰 → 서비스 → 리포지토리 3층이 흔하므로 3 을 쓴다.
MAX_DEPTH = 3

#: 따라가지 않는 함수 이름 — 어느 모듈에나 있는 일반명이라 호출 그래프를 폭발시킨다.
#: (1차판이 이것을 안 막아 `ChecklistSetting` 이 "단건 313건"으로 나왔다 — 앱을 넘나든 결과다.)
GENERIC_CALLS = frozenset({
    "get", "all", "filter", "first", "last", "create", "update", "delete", "save",
    "count", "exists", "values", "values_list", "annotate", "order_by", "select_related",
    "prefetch_related", "len", "str", "int", "list", "dict", "set", "print", "format",
    "append", "join", "isinstance", "getattr", "setattr", "hasattr", "super", "range",
    "sorted", "map", "any", "all_objects", "json", "loads", "dumps", "now", "today",
})

_SKIP_DIRS = {"__pycache__", "migrations", ".venv", "node_modules"}


# ---------------------------------------------------------------------------
# 0. 소스 색인 — 파일을 한 번만 읽고 AST 를 재사용한다
# ---------------------------------------------------------------------------
def iter_py(backend: Path) -> list[Path]:
    return [p for p in backend.rglob("*.py") if not (set(p.parts) & _SKIP_DIRS)]


def parse_all(backend: Path) -> dict[Path, ast.Module]:
    out: dict[Path, ast.Module] = {}
    for p in iter_py(backend):
        try:
            out[p] = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        except SyntaxError:
            # 문법이 깨진 파일은 조용히 넘기지 않는다 — 세지 못한 것을 세지 못했다고 말해야 한다.
            print(f"[TRACE] WARN 파싱 실패(건너뜀): {p}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# 1. 모델 클래스 색인 — `*/models.py` · `*/models/*.py` 안의 클래스
# ---------------------------------------------------------------------------
def index_models(backend: Path, trees: dict[Path, ast.Module]) -> dict[str, set[str]]:
    """클래스명 → {"app.Class", ...}. 같은 이름이 두 앱에 있으면 둘 다 담는다(모호로 표시)."""
    by_name: dict[str, set[str]] = defaultdict(set)
    for path, tree in trees.items():
        parts = path.relative_to(backend).parts
        if "models" not in {parts[-1].removesuffix(".py"), *parts[:-1]}:
            continue
        app = parts[0]
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                by_name[node.name].add(f"{app}.{node.name}")
    return by_name


# ---------------------------------------------------------------------------
# 2. 함수 색인 — 호출을 따라가기 위해
# ---------------------------------------------------------------------------
def module_dotted(backend: Path, path: Path) -> str:
    """backend/flight_log/views.py -> 'flight_log.views'"""
    rel = path.relative_to(backend).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def index_functions(
    backend: Path, trees: dict[Path, ast.Module]
) -> tuple[dict[Path, dict[str, ast.AST]], dict[Path, set[Path]]]:
    """(모듈별 함수 색인, 모듈별 import 대상 모듈 집합).

    ★ 1차판은 **이름만으로** 함수를 찾았다. 그러면 `delivery` 의 헬퍼가 `flight_log` 의
      핸들러에 붙고, 그 결과가 "단건 313건" 같은 수다 — 수가 커서 진척처럼 보이지만
      **아무것도 구별하지 못하는 수**다. D-263 이 앱 단위 매칭을 금지한 것과 같은 결함이다.
      그래서 호출은 **그 모듈 자신 + 그 모듈이 실제로 import 한 모듈** 안에서만 해석한다.
    """
    dotted: dict[str, Path] = {module_dotted(backend, p): p for p in trees}
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


class Trace:
    """추적 1회의 결과. 모델뿐 아니라 **지나간 호출 이름 전부**를 남긴다.

    문지기 판정(`tenant_tripwire`)이 이 호출 집합을 본다 — 모델만 남기고 버리면
    "무엇을 만졌나"는 알아도 "누가 지켰나"는 알 수 없다.
    """

    __slots__ = ("models", "ambiguous", "calls", "decorators")

    def __init__(self) -> None:
        self.models: set[str] = set()
        self.ambiguous: set[str] = set()
        self.calls: set[str] = set()
        self.decorators: set[str] = set()


def decorator_names(fn: ast.AST) -> set[str]:
    out: set[str] = set()
    for dec in getattr(fn, "decorator_list", []) or []:
        node = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(node, ast.Name):
            out.add(node.id)
        elif isinstance(node, ast.Attribute):
            out.add(node.attr)
    return out


def trace_from(
    start: ast.AST,
    home: Path,
    funcs: dict[Path, dict[str, ast.AST]],
    imports: dict[Path, set[Path]],
    model_names: dict[str, set[str]],
    *,
    max_depth: int = MAX_DEPTH,
) -> Trace:
    """핸들러에서 시작해 **import 그래프 안에서만** `max_depth` 까지 따라간다."""
    out = Trace()
    out.decorators = decorator_names(start)
    seen: set[tuple[str, int]] = set()
    frontier: list[tuple[ast.AST, Path, int]] = [(start, home, 0)]

    while frontier:
        node, mod, depth = frontier.pop()
        names, calls = refs_in(node)
        out.calls |= calls
        for nm in names & model_names.keys():
            labels = model_names[nm]
            out.models |= labels
            if len(labels) > 1:
                out.ambiguous.add(nm)
        if depth >= max_depth:
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
    return out


def models_touched(
    start: ast.AST,
    home: Path,
    funcs: dict[Path, dict[str, ast.AST]],
    imports: dict[Path, set[Path]],
    model_names: dict[str, set[str]],
) -> tuple[set[str], set[str]]:
    """구판 호출부 호환 — `(모델, 모호이름)` 만 낸다."""
    t = trace_from(start, home, funcs, imports, model_names)
    return t.models, t.ambiguous


# ---------------------------------------------------------------------------
# 4. 라우트 추출 — @api_controller(prefix) + @route.<verb>(subpath)
# ---------------------------------------------------------------------------
def _str_arg(call: ast.Call) -> str:
    for a in call.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return a.value
    return ""


def extract_controller_routes(root: Path, trees: dict[Path, ast.Module]) -> list[dict]:
    """소스에 적힌 라우트를 전부 낸다. **런타임 등록본과 대조하기 위한 한쪽 눈**이다.

    `root` 는 경로를 상대로 적을 기준 디렉터리(저장소 루트)다.
    `_node` 는 호출부가 `trace_from` 에 넘길 함수 노드이며, 쓰고 나면 버린다.
    """
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
                            "file": str(path.relative_to(root)).replace("\\", "/"),
                            "line": fn.lineno,
                            "handler": fn.name,
                            "ctrl": cls.name,
                            "_node": fn,
                        }
                    )
    return out


class Index:
    """한 번 색인해 두고 여러 핸들러를 추적한다."""

    def __init__(self, backend: Path) -> None:
        self.backend = backend
        self.trees = parse_all(backend)
        self.model_names = index_models(backend, self.trees)
        self.funcs, self.imports = index_functions(backend, self.trees)
        self._by_dotted = {module_dotted(backend, p): p for p in self.trees}

    def path_of(self, dotted: str) -> Path | None:
        return self._by_dotted.get(dotted)

    def find_function(self, dotted: str, qualname: str) -> tuple[ast.AST, Path] | None:
        """`('flight_log.views', 'FlightLogController.get_detail')` -> 함수 노드.

        런타임 열거가 준 이름을 소스로 되돌리는 자리다. 못 찾으면 **None 을 낸다** —
        여기서 조용히 "만지는 모델 없음"으로 떨어뜨리면 그것이 곧 조용한 면제다.
        호출부가 그 사실을 받아 `unresolved` 로 세게 한다.
        """
        path = self._by_dotted.get(dotted)
        if path is None:
            return None
        name = qualname.split(".")[-1]
        fn = self.funcs.get(path, {}).get(name)
        return (fn, path) if fn is not None else None

    def trace(self, node: ast.AST, home: Path) -> Trace:
        return trace_from(node, home, self.funcs, self.imports, self.model_names)
