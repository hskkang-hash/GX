# -*- coding: utf-8 -*-
"""신규 경로 트립와이어 — **문지기 없는 새 경로가 생기면 그 순간 잡는다** (D-275 §5-1).

왜 이것이 EXIT 승인의 **유일한 필수 부대조건**인가
--------------------------------------------------
WP-2 EXIT §5-1 이 남긴 미지 하나는 이것이었다:

    주인 없는 행(`created_by IS NULL`)은 매니저 수준에서 여전히 보인다.
    근원(`CustomManagerGroup` 의 `created_by__isnull` OR 절)은 저장소 밖이라 고칠 수 없다(§0.4).
    지금 닫혀 있는 이유는 **라우트마다 문지기를 손으로 달았기 때문**이다.
    → **문지기 없는 새 경로가 하나 생기면 그 순간 다시 샌다.**

그 문장을 사람의 기억이 아니라 **게이트가 지키게** 하는 것이 이 모듈이다.
고칠 수 없는 결함을 **다시 열리지 않게 잠그는** 방식이다.

판정 한 줄
----------
    라우트가 **테넌트 모델을 만지는데** 문지기가 하나도 없으면 → **unguarded**.
    unguarded 가 **등재부에 없던 것으로 새로 나타나면** → **fail**.

수가 아니라 **이름**으로 잠근다 (D-249 · D-277)
-----------------------------------------------
`PUBLIC_BASELINE` 처럼 **수**로 래칫을 걸면, 낡은 라우트 하나가 지워질 때마다
새 라우트 하나가 조용히 들어올 자리가 생긴다. 수는 그대로인데 노출은 바뀐다.
그래서 이 게이트는 **라우트 하나하나의 이름(키)** 을 등재부에 적고 그 집합을 비교한다.
줄어드는 것은 환영이고, **없던 이름이 나타나는 것만** 실패다.

두 눈으로 본다 — 정적 / 런타임
-------------------------------
같은 판정기(`judge`)를 두 열거기가 각각 먹인다.

  · **정적**  `common.ast_call_trace.extract_controller_routes` — 소스의 `@route.*`.
              Django 가 없어도 돈다. pre-commit(`scripts/verify_tenant_scope.py`)이 쓴다.
  · **런타임** `common.tenant_scope.enumerate_operations` — 등록된 오퍼레이션 실측.
              동적 등록까지 본다. 시험(`tests/test_route_tripwire.py`)이 쓴다.

지시가 요구한 것은 **런타임 전수 열거**다. 정적 눈은 그것을 대신하는 것이 아니라,
커밋 시점에 먼저 걸러 주는 앞눈이고 **런타임 눈이 무엇을 놓치는지 대조하는 자**다.
둘 중 하나가 0 을 세면 그것은 통과가 아니라 **열거기 고장**이다.

무엇을 **못** 하나 — 경계를 적는다 (D-277)
------------------------------------------
문지기 판정은 **AST 호출 그래프 3단계**다. 그래서:

  · 동적 디스패치(`getattr(svc, name)()`)로 부른 문지기는 **못 본다** → 거짓 양성(과다 검출).
  · 미들웨어·시그널에 숨은 문지기도 못 본다 → 거짓 양성.
  · 반대로 **문지기를 부르기만 하고 그 결과를 안 쓰는 코드**는 통과로 본다 → 거짓 음성.

거짓 양성은 등재부에 사유와 함께 올려 해소한다. 거짓 음성은 이 게이트가 아니라
`tests/test_tenant_isolation.py` 의 **실 HTTP 프로브**가 잡는다. 여기서 둘을 다 하려 들지 않는다.
"""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from common import ast_call_trace as trace

#: 경로는 **자기 위치에서** 구한다. 컨테이너는 `backend/` 를 `/app` 로, `docs/` 를 `/docs` 로
#: 마운트하므로 저장소 루트가 존재하지 않는다 — 루트를 인자로 받으면 컨테이너에서 못 돈다.
#: `BACKEND.parent` 는 호스트에서 저장소 루트, 컨테이너에서 `/` 이고 둘 다 `docs` 가 옆에 있다.
BACKEND: Path = Path(__file__).resolve().parent.parent
DOCS: Path = BACKEND.parent / "docs"

#: 이 저장소가 인정하는 **문지기**. 하나라도 호출 그래프에 있으면 guarded 로 본다.
#:
#: ⚠ 여기에 이름을 추가하는 것은 "이 함수를 부르면 테넌트가 지켜진다"는 **선언**이다.
#:   `common/tenant_filters.py` 안에서 실제로 group 으로 거르는 함수만 올린다.
#:   편의 헬퍼를 올리면 초록만 늘고 노출은 그대로 남는다 — 착시 ①(D-249)의 모양이다.
GATEKEEPER_CALLS: frozenset[str] = frozenset({
    "assert_scoped",          # 쓰기 경로 문지기 (W0-14c)
    "get_scoped_or_404",      # 단건 조회 문지기 (IDOR 차단)
    "filter_by_group_field",  # group FK 목록 필터
    "filter_users_by_group",  # M2M 목록 필터
    "require_user_group",     # 요청자의 group 을 강제로 요구 (없으면 예외)
})

#: 데코레이터로 건 스코프. 런타임에서는 `RouteInfo.scope` 로도 보인다.
GATEKEEPER_DECORATORS: frozenset[str] = frozenset({"tenant_scoped"})

#: `get_user_group` 은 **문지기가 아니다.** group 을 읽기만 하고 거르지 않는다.
#: 여기 적어 두는 이유는 다음 사람이 "이것도 문지기 아닌가" 하고 다시 올리지 않게 하기 위해서다.
NOT_GATEKEEPERS: frozenset[str] = frozenset({"get_user_group", "is_global_admin"})

BASELINE_NAME = "tripwire_baseline.json"


# ---------------------------------------------------------------------------
# 인구조사(모수) — 표를 import 하지 않고 AST 로 읽는다
# ---------------------------------------------------------------------------
def load_census_labels() -> set[str]:
    """`backend/tests/tenant_census.py` 의 `CENSUS` 키 집합 = 테넌트 모델 모수.

    import 하지 않고 AST 로 읽는 이유: 이 판정기는 **Django 없이도** 돌아야 한다.
    못 읽으면 빈 집합을 내지 않고 **예외를 던진다** — 모수 0 위의 초록은
    D-271 이 지적한 그 착시(작은 모수)의 극단이다.
    """
    census = BACKEND / "tests" / "tenant_census.py"
    if not census.is_file():
        raise FileNotFoundError(
            f"인구조사를 못 찾았다: {census} — 모수 없이 판정하지 않는다 (D-271 ②)"
        )
    tree = ast.parse(census.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        tgt = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            tgt = node.target.id
        elif isinstance(node, ast.Assign) and node.targets and isinstance(node.targets[0], ast.Name):
            tgt = node.targets[0].id
        if tgt == "CENSUS" and isinstance(node.value, ast.Dict):
            return {k.value for k in node.value.keys if isinstance(k, ast.Constant)}
    raise ValueError(
        "tenant_census.CENSUS 를 읽지 못했다 — 형태가 바뀌었다면 이 판정기도 함께 고쳐라. "
        "못 읽은 채 통과시키지 않는다"
    )


# ---------------------------------------------------------------------------
# 판정 — 순수 함수. 양성 대조가 겨누는 과녁이 여기다 (D-277)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Verdict:
    key: str
    verdict: str            # guarded / public / clean / unguarded / unresolved
    method: str
    path: str
    where: str              # module.qualname 또는 file:line
    models: tuple[str, ...] = ()
    gatekeepers: tuple[str, ...] = ()
    note: str = ""

    #: 등재부가 **이름으로** 잠그는 갈래. 셋 다 "우리가 지금 못 지키는 것"이고,
    #: 지킬 수 없다는 사실이 **늘어나는 것**만 실패로 본다.
    TRACKED = ("unguarded", "unresolved", "outside")

    @property
    def is_problem(self) -> bool:
        return self.verdict in self.TRACKED


def judge(
    *,
    key: str,
    method: str,
    path: str,
    where: str,
    resolved: bool,
    models: Iterable[str],
    calls: Iterable[str],
    decorators: Iterable[str],
    scoped_at_runtime: bool = False,
    public_reason: str | None = None,
    census: set[str],
) -> Verdict:
    """라우트 하나를 판정한다. **이 함수 하나가 정본**이고 두 열거기가 이것을 부른다.

    순서에 뜻이 있다:
      1. **못 찾은 것은 못 찾았다고 말한다.** 소스를 못 되짚으면 `unresolved` —
         조용히 "만지는 모델 없음"으로 떨어뜨리는 것이 곧 자동 면제다 (D-263).
      2. 문지기가 있으면 `guarded`.
      3. PUBLIC 등재는 그 다음. 단 **테넌트 모델을 만지는 PUBLIC** 은 note 로 남긴다 —
         "테넌트 데이터를 반환하지 않는다"는 선언과 어긋나기 때문이다.
      4. 테넌트 모델을 만지는데 아무것도 없으면 `unguarded`.
      5. 안 만지면 `clean`.
    """
    touched = tuple(sorted(set(models) & census))
    guards = tuple(sorted((set(calls) & GATEKEEPER_CALLS)
                          | (set(decorators) & GATEKEEPER_DECORATORS)))
    if scoped_at_runtime and "tenant_scoped" not in guards:
        guards = tuple(sorted({*guards, "tenant_scoped"}))

    if not resolved:
        return Verdict(key, "unresolved", method, path, where, touched, guards,
                       "핸들러 소스를 되짚지 못했다 — 만지는 모델을 셀 수 없다. "
                       "못 센 것을 통과로 세지 않는다")
    if guards:
        return Verdict(key, "guarded", method, path, where, touched, guards)
    if public_reason:
        note = ""
        if touched:
            note = (f"PUBLIC 인데 테넌트 모델을 만진다({', '.join(touched)}) — "
                    f"PUBLIC 선언과 어긋난다. 사유를 다시 볼 것")
        return Verdict(key, "public", method, path, where, touched, guards, note)
    if touched:
        return Verdict(key, "unguarded", method, path, where, touched, guards,
                       "테넌트 모델을 만지는데 문지기가 없다")
    return Verdict(key, "clean", method, path, where, touched, guards)


# ---------------------------------------------------------------------------
# 열거기 A — 정적 (Django 불필요)
# ---------------------------------------------------------------------------
def _public_reason_by_suffix(method: str, ctrl_path: str) -> str | None:
    """정적 눈은 마운트 접두사를 모른다. PUBLIC 대장과 **접미사**로 맞춘다."""
    try:
        from common.tenant_scope import PUBLIC_PREFIXES, PUBLIC_ROUTES
    except Exception:
        # Django 없이 도는 경로 — AST 로 읽는 대신 없는 셈 친다.
        # PUBLIC 4건은 전부 dj-core/ninja-jwt 쪽이라 이 저장소 컨트롤러에 안 나온다.
        return None
    for (m, p), reason in PUBLIC_ROUTES.items():
        if m == method.upper() and p.rstrip("/").endswith(ctrl_path.rstrip("/")):
            return reason
    for prefix in PUBLIC_PREFIXES:
        if ctrl_path.startswith(prefix):
            return f"공개 접두어 {prefix}"
    return None


def scan_static() -> list[Verdict]:
    """소스의 `@route.*` 를 전수로 훑는다. pre-commit 이 쓰는 눈."""
    backend = BACKEND
    census = load_census_labels()
    idx = trace.Index(backend)
    out: list[Verdict] = []
    for r in trace.extract_controller_routes(backend, idx.trees):
        node = r.pop("_node")
        home = backend / r["file"]
        t = idx.trace(node, home)
        key = f"{r['method']} {trace.module_dotted(backend, home)}.{r['ctrl']}.{r['handler']}"
        out.append(judge(
            key=key,
            method=r["method"],
            path=r["ctrl_path"],
            where=f"{r['file']}:{r['line']}",
            resolved=True,
            models=t.models,
            calls=t.calls,
            decorators=t.decorators,
            public_reason=_public_reason_by_suffix(r["method"], r["ctrl_path"]),
            census=census,
        ))
    out.sort(key=lambda v: v.key)
    return out


# ---------------------------------------------------------------------------
# 열거기 B — 런타임 (Django 필요). **지시가 요구한 전수 열거가 이것이다**
# ---------------------------------------------------------------------------
def scan_runtime(routes: Iterable[Any] | None = None) -> list[Verdict]:
    """등록된 전 라우트를 런타임 레지스트리에서 열고, 각각을 소스로 되짚어 판정한다.

    정적 눈이 못 보는 것을 이 눈이 본다 — 동적으로 등록된 컨트롤러,
    `@route` 가 아닌 방식으로 붙은 오퍼레이션, 다른 앱에서 register 된 것.

    `routes` 를 주면 그것을 대신 쓴다. **양성 대조(D-277)가 이 구멍으로 들어온다** —
    문지기 없는 라우트를 하나 심어 놓고 이 판정기가 정말 잡는지 보기 위해서다.
    실패할 수 없는 시험은 시험이 아니다.
    """
    from common import tenant_scope

    backend = BACKEND
    census = load_census_labels()
    idx = trace.Index(backend)
    out: list[Verdict] = []
    for r in (tenant_scope.enumerate_operations() if routes is None else routes):
        found = idx.find_function(r.module, r.handler)
        key = f"{r.method} {r.module}.{r.handler}"
        if found is None:
            # ★ **"금지구역"은 파일 경로로 확인한 뒤에만 붙인다** (D-279).
            #   추정으로 붙이면 고칠 수 있는 것을 포기하게 된다 — 문지기 7곳이 전부
            #   저장소 코드였는데 §0.4 로 적혀 있던 것이 그 사고였다.
            #   여기서의 확인은 하나뿐이다: **그 모듈의 소스 파일이 backend/ 안에 있는가.**
            #   없으면 dj-core·ninja-jwt 처럼 관할 밖이고, 있으면 우리 코드인데 못 찾은 것이다.
            in_repo = idx.path_of(r.module) is not None
            out.append(Verdict(
                key, "unresolved" if in_repo else "outside", r.method, r.path,
                r.module + "." + r.handler, (), (),
                "저장소 안 모듈인데 핸들러를 못 찾았다 — 열거기와 색인이 어긋났다"
                if in_repo else
                "핸들러 소스가 backend/ 안에 없다 — 관할 밖(§0.4). "
                "고칠 수 없으므로 **늘어나는 것만** 본다",
            ))
            continue
        node, home = found
        t = idx.trace(node, home)
        out.append(judge(
            key=key,
            method=r.method,
            path=r.path,
            where=f"{r.module}.{r.handler}",
            resolved=True,
            models=t.models,
            calls=t.calls,
            decorators=t.decorators,
            scoped_at_runtime=r.scope is not None,
            public_reason=tenant_scope.is_public(r.method, r.path),
            census=census,
        ))
    out.sort(key=lambda v: v.key)
    return out


# ---------------------------------------------------------------------------
# 등재부 대조 — 이름으로 잠근다
# ---------------------------------------------------------------------------
@dataclass
class Report:
    eye: str                       # "static" | "runtime"
    verdicts: list[Verdict]
    baseline: dict[str, Any] | None = None
    problems: list[str] = field(default_factory=list)
    #: 실패는 아니지만 사람이 봐야 하는 것 (등재부가 낡았다 등).
    notes: list[str] = field(default_factory=list)

    def by(self, name: str) -> list[Verdict]:
        return [v for v in self.verdicts if v.verdict == name]

    @property
    def summary(self) -> str:
        counts = {}
        for v in self.verdicts:
            counts[v.verdict] = counts.get(v.verdict, 0) + 1
        parts = " · ".join(f"{k} {counts[k]}" for k in sorted(counts))
        return f"[TRIPWIRE:{self.eye}] 라우트 {len(self.verdicts)}건 — {parts}"


def baseline_path() -> Path:
    return DOCS / "agent" / "evidence" / "W0-14" / BASELINE_NAME


def load_baseline() -> dict[str, Any] | None:
    p = baseline_path()
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def build_baseline(reports: Iterable[Report], measured_at: str) -> dict[str, Any]:
    """등재부를 만든다. **다른 눈의 구획은 보존한다** — 정적 눈은 호스트에서, 런타임 눈은
    컨테이너에서 재므로, 한쪽만 다시 잰다고 다른 쪽 기록을 지워서는 안 된다.
    지우면 그 눈의 등재부가 사라지고, 등재부 없는 게이트는 다음 실행에서 통과한다.
    """
    payload: dict[str, Any] = dict(load_baseline() or {})
    payload.update({
        "note": (
            "신규 경로 트립와이어 등재부 (D-275 §5-1). **수가 아니라 이름으로 잠근다** — "
            "여기 없는 라우트가 unguarded 로 나타나면 게이트가 실패한다. "
            "줄어드는 것은 환영이고, 줄었으면 이 파일을 다시 만들어 커밋한다."
        ),
        "how_to_regenerate": (
            "정적: python scripts/verify_tenant_scope.py --write-baseline / "
            "런타임: 시험 컨테이너에서 --runtime 과 함께"
        ),
    })
    payload.setdefault("measured_at", {})
    for rep in reports:
        payload["measured_at"][rep.eye] = measured_at
        payload[rep.eye] = {
            "total": len(rep.verdicts),
            **{kind: [v.key for v in rep.by(kind)] for kind in Verdict.TRACKED},
        }
    return payload


#: 열거기가 이보다 적게 세면 **고장**으로 본다. 정적 실측 466(2026-08-15) 의 절반.
#: 열거가 0 인데 "unguarded 0" 이 나오면 그것은 초록이 아니라 눈이 감긴 것이다 (D-277 ④).
MIN_EXPECTED_ROUTES = 233


def compare(rep: Report) -> Report:
    """등재부와 대조해 **없던 이름이 나타났는지**만 본다."""
    base = load_baseline()
    rep.baseline = base

    if len(rep.verdicts) < MIN_EXPECTED_ROUTES:
        rep.problems.append(
            f"[{rep.eye}] 라우트를 {len(rep.verdicts)}건밖에 못 셌다 (하한 {MIN_EXPECTED_ROUTES}). "
            f"열거기가 고장난 것으로 본다 — 이 상태의 '위반 0' 은 초록이 아니라 눈이 감긴 것이다"
        )
        return rep

    if base is None:
        rep.problems.append(
            f"[{rep.eye}] 등재부가 없다 ({baseline_path()}). "
            f"`python scripts/verify_tenant_scope.py --write-baseline` 로 만들고 커밋하라 — "
            f"등재부 없이 통과시키면 무엇이 늘었는지 아무도 모른다"
        )
        return rep

    known = base.get(rep.eye) or {}
    for kind in Verdict.TRACKED:
        was = set(known.get(kind, []))
        now = {v.key for v in rep.by(kind)}
        for key in sorted(now - was):
            v = next(x for x in rep.verdicts if x.key == key)
            rep.problems.append(
                f"[{rep.eye}] 새 {kind} 라우트: {key}\n"
                f"      경로 {v.method} {v.path}  ({v.where})\n"
                f"      만지는 테넌트 모델: {', '.join(v.models) or '(없음)'}\n"
                f"      → {v.note}\n"
                f"      조치: common.tenant_filters 의 문지기"
                f"({' / '.join(sorted(GATEKEEPER_CALLS))}) 를 붙이거나, "
                f"@tenant_scoped 를 걸어라. 면제가 필요하면 사유와 함께 대표 승인을 받는다"
            )
        gone = was - now
        if gone:
            # 감소는 **실패가 아니다.** 다만 등재부를 갱신하지 않으면 다음에 그 자리로
            # 새 라우트가 들어와도 안 보인다 — 수 래칫이 조용해지는 것과 같은 구멍이다.
            rep.notes.append(
                f"[{rep.eye}] ↓ {kind} {len(was)} → {len(now)} 로 줄었다 "
                f"({', '.join(sorted(gone)[:3])}{' 외' if len(gone) > 3 else ''}) — "
                f"`--write-baseline` 로 등재부를 다시 만들어 커밋하라"
            )
    return rep
