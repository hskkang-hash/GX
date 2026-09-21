#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**본문으로 보냈는데 서버는 질의를 기다린다** — POST 인자 방식 대조 판정기 (2026-09-05 TC).

무엇이 이 판정기를 만들었나
---------------------------
턴 C 에 같은 결함을 **세 자리**에서 찾았다. 셋 다 화면은 멀쩡히 떠 있었다:

    카메라 일괄 등록      POST /api/dsm/cameras/import        본문 → 422
    훈련 모드 전환        POST /api/dsm/drill                 본문 → 422
    처리 단계 넘기기      POST /api/dsm/events/{id}/response  본문 → 422

django-ninja 는 **원시 타입 인자를 질의로 읽는다.** 그래서 본문으로 보내면
돌아오는 것은 `422 · loc:["query", …] · "Field required"` 이고, 그 422 는
「값이 틀렸다」가 아니라 **「인자가 없다」**이다. 둘을 헷갈리면 한나절이 간다.

★ **가장 나쁜 점은 조용하다는 것이다.** 화면은 뜬다. 캡처는 제목 글자만 단언하므로
  초록이 난다. 단추를 실제로 누르는 사람만 안다 — 그 사람이 첫 근무일의 관제요원이다.

★ **왜 세 번이나 빠졌나 — 조립을 화면마다 손으로 짰기 때문이다.** 맞게 짠 사본이
  하나 있었고(이벤트 상세), 그 사실이 오히려 「손으로 짜도 된다」로 읽혔다.
  그래서 조립을 한 곳(`dsmPostQuery`)으로 모으고, 이 판정기가 그것을 지킨다.

무엇을 세는가 — 두 면을 **따로** 센다
------------------------------------
    ① 서버 면   backend/apps/dsm/api.py 의 POST 라우트 전수 → 인자 방식 판정
                **판정은 Python AST 다.** 낱말 검색이 아니다 — 데코레이터·기본값·
                경로 조각·타입 표기를 전부 문법으로 읽는다.
    ② 화면 면   frontend/src 의 POST 호출 자리 전수 → 어느 자리로 보내는지 판정

    두 면을 이어 **어긋난 자리**를 낸다: 서버가 질의를 기다리는데 화면이 본문으로 보낸다.

⚠ **정직하게 적는다 — ②는 TypeScript AST 가 아니다.** 이 기계에는 게이트가 쓸 수 있는
  TS 파서가 없다(게이트는 호스트에서 Django·node 없이 돈다). 대신 낱말 검색도 아니다:
  저장소가 이미 쓰는 `verify_ui_secrets.strip_comments` 로 **주석과 문자열을 문법으로
  걷어 낸 뒤**, 괄호 균형을 세어 **호출식 하나를 통째로** 집는다. 줄 단위 정규식이면
  제네릭 호출(`dsmPostQuery<ImportPlan>(`)을 놓치는데 — 실제로 이번 턴에 사람이
  grep 으로 세다가 그 두 자리를 놓쳤다 — 이 방식은 놓치지 않는다.
  **못 읽는 것은 못 읽었다고 센다** — 0건 검사를 0건 위반으로 적지 않는다.

    python scripts/verify_post_arg_style.py            # 판정
    python scripts/verify_post_arg_style.py --list     # 두 면의 표 전수
    python scripts/verify_post_arg_style.py --self-test

종료 코드
---------
    0  어긋난 자리 0건
    1  어긋난 자리가 있다
    2  판정 불가 (읽을 파일이 없다 · 자기시험 실패)

호스트에서 돈다 — Django 가 필요 없다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_ui_secrets import frontend_files, strip_comments  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

#: 재는 서버 면. **이름으로 적는다** — 늘 때 사람이 여기를 고쳐야 한다(모수의 선언).
API_MODULES = (
    "backend/apps/dsm/api.py",
    #: ★ 2026-09-05 · 차선 L — 법·인증 면은 **다른 파일**에 산다(LAW-02a · LAW-06 ·
    #:   LAW-07). 여기 안 적으면 그 파일의 POST 는 이 게이트의 **눈 밖**이고,
    #:   눈 밖의 라우트는 규약이 깨져도 초록이다. 컨트롤러가 늘면 여기도 는다.
    "backend/apps/dsm/law_api.py",
)

#: 본문으로 읽히는 타입 표기의 표식. django-ninja 는 Schema/모델 타입을 본문으로 본다.
#: 이름 조각으로 본다 — 무엇이 Schema 를 상속했는지는 여기서 알 수 없다. 그래서
#: **못 가르면 unknown 으로 세고 위반으로 세지 않는다.**
BODY_TYPE_HINTS = ("Schema", "Payload", "Body", "Form", "File", "UploadedFile")

#: 화면이 POST 를 보내는 함수들. 뒤의 둘은 **질의로 조립하는 것이 확정**된 자리다.
#: ★ 이름을 늘리지 않는다. 화면마다 감싸는 함수를 만들면 그 이름을 여기 적어야 하고,
#:   적는 것을 잊으면 그 화면은 **판정기 밖**에 선다 — 판정기가 믿어야 할 이름이
#:   적을수록 판정기가 덜 틀린다. 그래서 이번 턴에 화면의 감싸개를 없앴다.
POST_CALLERS_BODY = ("dsmPost",)
POST_CALLERS_QUERY = ("dsmPostQuery", "mobilePostWithQuery")

#: 끝점 이름 → 경로를 정해 둔 파일. 여기 말고 다른 데서 경로를 만들면 못 잇는다.
ENDPOINT_FILES = (
    "frontend/src/features/dsm/api.ts",
    "frontend/src/features/mobile/api.ts",
)


# ═══════════════════════════════════════════════════════════════════════════
# ① 서버 면 — **Python AST**
# ═══════════════════════════════════════════════════════════════════════════
def _route_method_path(dec: ast.expr):
    """`@route.post("/x")` 에서 `("POST", "/x")`. 라우트가 아니면 None."""
    if not isinstance(dec, ast.Call):
        return None
    fn = dec.func
    if not (isinstance(fn, ast.Attribute)
            and isinstance(fn.value, ast.Name) and fn.value.id == "route"):
        return None
    path = ""
    if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
        path = dec.args[0].value
    for kw in dec.keywords:
        if kw.arg == "path" and isinstance(kw.value, ast.Constant):
            path = kw.value.value
    return fn.attr.upper(), path


def _path_names(path: str):
    """`/events/{int:event_id}/response` → {"event_id"}. 경로 조각은 질의가 아니다."""
    return {seg.split(":")[-1] for seg in re.findall(r"\{([^}]+)\}", path)}


def scan_api_module(path: Path):
    """그 모듈의 라우트 전수. 각 행은 인자 방식까지 판정돼 있다."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rows = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        found = None
        for dec in node.decorator_list:
            got = _route_method_path(dec)
            if got:
                found = got
        if not found:
            continue
        method, route_path = found
        in_path = _path_names(route_path)

        query, body, unknown = [], [], []
        args = node.args
        positional = list(args.posonlyargs) + list(args.args)
        for arg in positional + list(args.kwonlyargs):
            if arg.arg in ("self", "request") or arg.arg in in_path:
                continue
            ann = ast.unparse(arg.annotation) if arg.annotation else None
            if ann is None:
                unknown.append(arg.arg)      # 표기가 없으면 **모른다**고 센다
            elif any(h in ann for h in BODY_TYPE_HINTS):
                body.append(arg.arg)
            else:
                query.append(arg.arg)

        if query and not body:
            style = "QUERY"
        elif body and not query:
            style = "BODY"
        elif not query and not body and not unknown:
            style = "NOARG"
        else:
            style = "MIXED"          # 섞이면 사람이 봐야 한다 — 위반으로 세지 않는다
        rows.append({"method": method, "path": route_path, "name": node.name,
                     "line": node.lineno, "style": style,
                     "query": query, "body": body, "unknown": unknown})
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# ② 화면 면 — 주석·문자열을 걷어 낸 뒤 **괄호 균형으로 호출식을 통째로** 집는다
# ═══════════════════════════════════════════════════════════════════════════
#: 호출 머리. 제네릭이 붙어도 잡는다 — 줄 정규식이 놓친 그 자리다.
_CALL_HEAD = re.compile(
    r"\b(" + "|".join(POST_CALLERS_BODY + POST_CALLERS_QUERY) + r")\s*(?:<[^<>()]*>)?\s*\(")


def _blank_strings(src: str) -> str:
    """문자열 리터럴의 **속을** 같은 길이의 공백으로 바꾼다. 따옴표는 남긴다.

    ★ 왜 이것이 따로 필요한가 — `strip_comments` 는 **주석만** 지운다(문자열은 건드리지
      않는 것이 그 함수의 계약이다). 그런데 이 판정기가 찾는 것은 호출식이고,
      문자열 안에 적힌 호출 모양의 글자는 호출이 아니라 **글자**다. 그것을 세면
      고칠 것이 없는 자리가 빨개지고, 빨간 게이트는 곧 꺼진 게이트가 된다.

    ⚠ **자기시험이 이것을 잡았다.** 1차판은 걷지 않았고 문자열 안의 글자를 위반으로
      셌다 — 판정기의 자기시험이 판정기 자신의 결함을 잡은 자리다.
    ⚠ 길이와 줄 수를 보존한다. 줄이 밀리면 「어디」가 틀리고, 어디가 틀린 보고는
      고쳐지지 않는다.
    """
    out = list(src)
    i, n = 0, len(src)
    quote = None
    while i < n:
        ch = src[i]
        if quote:
            if ch == "\\":
                out[i] = " "
                if i + 1 < n and src[i + 1] != "\n":
                    out[i + 1] = " "
                i += 2
                continue
            if ch == quote:
                quote = None
            elif ch != "\n":
                out[i] = " "
            i += 1
            continue
        if ch in "'\"`":
            quote = ch
        i += 1
    return "".join(out)


def _split_top_level_args(inner: str):
    """괄호·중괄호·대괄호 깊이 0 의 쉼표로만 가른다."""
    out, depth, cur = [], 0, []
    for ch in inner:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur).strip())
            cur = []
            continue
        cur.append(ch)
    if "".join(cur).strip():
        out.append("".join(cur).strip())
    return out


def scan_call_sites(src: str):
    """한 파일의 POST 호출 자리 전수. **주석이 이미 걷힌 소스**를 받는다.

    ★ 찾기는 **문자열 속을 비운 사본**에서 하고, 인자 글자는 **원본에서** 떠 온다.
      둘을 가르는 이유: 문자열 안의 호출 모양을 세면 안 되지만(거짓 빨강),
      호출의 첫 인자가 문자열일 때는 그 글자가 있어야 어느 라우트인지 안다.
      두 사본은 길이가 같으므로 자리가 어긋나지 않는다.
    """
    scan = _blank_strings(src)
    sites = []
    for m in _CALL_HEAD.finditer(scan):
        caller = m.group(1)
        i, depth = m.end(), 1
        while i < len(scan) and depth:
            if scan[i] == "(":
                depth += 1
            elif scan[i] == ")":
                depth -= 1
            i += 1
        if depth:
            continue                      # 닫히지 않았다 — 집지 않는다
        inner = src[m.end():i - 1]
        parts = _split_top_level_args(inner)
        sites.append({
            "caller": caller,
            "line": scan.count("\n", 0, m.start()) + 1,
            "target": parts[0] if parts else "",
            "argc": len(parts),
        })
    return sites


def load_endpoints():
    """`dsmEndpoint.review` 같은 이름 → 경로. 두 파일의 상수표를 읽는다.

    이때는 문자열이 걷히기 **전의** 소스를 읽는다 — 여기서 필요한 것이 그 문자열이다.
    """
    table = {}
    lit = re.compile(r"(\w+)\s*:\s*['\"](/api/[^'\"]+)['\"]")
    fn = re.compile(r"(\w+)\s*:\s*\([^)]*\)\s*=>\s*[`'\"](/api/[^`'\"]+)")
    for rel in ENDPOINT_FILES:
        p = ROOT / rel
        if not p.exists():
            continue
        src = p.read_text(encoding="utf-8")
        for name, path in lit.findall(src):
            table.setdefault(name, path)
        for name, path in fn.findall(src):
            table.setdefault(name, path)
    return table


def _route_key(path: str) -> str:
    """경로의 **모양**만 남긴다 — 변수 조각을 하나로 접어 두 면을 잇는다."""
    path = re.sub(r"^/api/dsm", "", path)
    path = re.sub(r"\$\{[^}]*\}", "{}", path)
    path = re.sub(r"\{[^}]*\}", "{}", path)
    return path.rstrip("/") or "/"


def resolve_target(target: str, endpoints):
    """호출의 첫 인자가 가리키는 경로. 못 알아보면 None (= 잇지 못함)."""
    m = re.search(r"(?:dsm|mobile)Endpoint\.(\w+)", target)
    if m:
        return endpoints.get(m.group(1))
    m = re.search(r"['\"`](/api/[^'\"`?]+)", target)
    if m:
        return m.group(1)
    return None


# ═══════════════════════════════════════════════════════════════════════════
# 대조
# ═══════════════════════════════════════════════════════════════════════════
def judge():
    server = []
    for rel in API_MODULES:
        p = ROOT / rel
        if p.exists():
            server.extend(scan_api_module(p))
    by_key = {}
    for r in server:
        if r["method"] == "POST":
            by_key[_route_key(r["path"])] = r

    endpoints = load_endpoints()
    violations, unresolved, checked = [], [], 0
    all_callers = POST_CALLERS_BODY + POST_CALLERS_QUERY
    for path in frontend_files():
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if not any(c in raw for c in all_callers):
            continue
        stripped = strip_comments(raw)
        for site in scan_call_sites(stripped):
            # 조립 함수 **자신의 몸통**은 세지 않는다 — 그것이 옳은 조립이다.
            if path.name == "api.ts" and re.search(r"\burl\b", site["target"]):
                continue
            checked += 1
            if site["caller"] in POST_CALLERS_QUERY:
                continue                   # 질의로 조립하는 자리 — 맞다
            if site["argc"] < 2:
                continue                   # 두 번째 인자가 없다 = 본문을 안 보낸다
            resolved = resolve_target(site["target"], endpoints)
            if resolved is None:
                unresolved.append((path, site["line"], site["target"][:60]))
                continue
            row = by_key.get(_route_key(resolved))
            if row is None:
                unresolved.append((path, site["line"], resolved))
                continue
            if row["style"] == "QUERY":
                violations.append((path, site["line"], resolved, row["name"], row["query"]))
    return {"server": server, "posts": by_key, "checked": checked,
            "violations": violations, "unresolved": unresolved}


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — **판정기가 작동하는지 먼저 증명한다** (양성·음성 두 갈래)
# ═══════════════════════════════════════════════════════════════════════════
SELF_API = '''
class Ctl:
    @route.post("/events/{int:event_id}/response", auth=X())
    def advance_response(self, request, event_id: int, to_state: str, reason: str = ""):
        pass

    @route.post("/events/{int:event_id}/notify", auth=X())
    def notify(self, request, event_id: int):
        pass

    @route.post("/bulk", auth=X())
    def bulk(self, request, payload: BulkSchema):
        pass

    @route.get("/events", auth=X())
    def events(self, request, limit: int = 50):
        pass
'''


def self_test() -> bool:
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            ok = False
            print(f"[POSTARG] 자기시험 실패 — {label}: {got!r} != {want!r}")

    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "api.py"
        f.write_text(SELF_API, encoding="utf-8")
        rows = {r["name"]: r for r in scan_api_module(f)}

    # 양성 ① — 원시 타입 인자는 질의다 (출생 표본: advance_response)
    check("질의 라우트", rows["advance_response"]["style"], "QUERY")
    check("질의 인자", rows["advance_response"]["query"], ["to_state", "reason"])
    # 음성 ① — 경로 조각뿐이면 인자 없음. **질의로 세면 안 된다**
    check("인자 없는 라우트", rows["notify"]["style"], "NOARG")
    # 음성 ② — Schema 인자는 본문이다
    check("본문 라우트", rows["bulk"]["style"], "BODY")
    # 음성 ③ — GET 은 POST 표에 안 들어간다
    check("GET 제외", rows["events"]["method"], "GET")

    # 양성 ② — **제네릭 호출을 놓치지 않는가** (grep 이 이번 턴에 놓친 그 모양)
    sites = scan_call_sites("await dsmPostQuery<ImportPlan>(dsmEndpoint.cameraImport, {a: 1});")
    check("제네릭 호출 포착", [s["caller"] for s in sites], ["dsmPostQuery"])
    check("제네릭 호출 인자 수", sites[0]["argc"], 2)
    # 양성 ③ — 중첩 괄호 안의 쉼표에 속지 않는가
    sites = scan_call_sites("dsmPost(dsmEndpoint.response(id, x), { to_state: f(a, b) });")
    check("중첩 인자 가르기", sites[0]["argc"], 2)
    check("중첩 대상", sites[0]["target"], "dsmEndpoint.response(id, x)")
    # 음성 ④ — 인자 하나짜리는 본문을 안 보낸다
    sites = scan_call_sites("dsmPost(dsmEndpoint.notify(id));")
    check("인자 하나", sites[0]["argc"], 1)
    # 음성 ⑤ — **주석·문자열 안의 호출은 세지 않는다**
    stripped = strip_comments("// dsmPost(a, b)\nconst s = 'dsmPost(a, b)';\n")
    check("주석·문자열 제외", scan_call_sites(stripped), [])
    # 양성 ④ — 그런데 **첫 인자가 문자열이면 그 글자는 읽어야 한다.**
    #   문자열을 통째로 지웠다면 이 갈래가 빨개진다 — 두 사본을 가르는 이유가 이것이다.
    sites = scan_call_sites("dsmPost('/api/dsm/drill', { enabled: true });")
    check("문자열 대상 보존", sites[0]["target"], "'/api/dsm/drill'")
    check("문자열 대상 해석", resolve_target(sites[0]["target"], {}), "/api/dsm/drill")
    # 경로 모양 접기 — 두 면을 잇는 자리
    check("모양 접기 화면", _route_key("/api/dsm/events/${id}/response"), "/events/{}/response")
    check("모양 접기 서버", _route_key("/events/{int:event_id}/response"), "/events/{}/response")

    if ok:
        print("[POSTARG] 자기시험 통과 — 양성 6갈래 · 음성 5갈래 (출생 표본 셋 포함)")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="POST 인자 방식 대조 (2026-09-05 TC)")
    ap.add_argument("--list", action="store_true", help="두 면의 표 전수")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if not self_test():
        print("[POSTARG] 판정 불가 — 판정기 자신이 틀렸다")
        return EXIT_UNDECIDABLE
    if args.self_test:
        return EXIT_OK

    missing = [rel for rel in API_MODULES if not (ROOT / rel).exists()]
    if missing:
        print(f"[POSTARG] 판정 불가 — 잴 서버 면이 없다: {missing}")
        return EXIT_UNDECIDABLE

    res = judge()
    posts = res["posts"]
    styles = {}
    for r in posts.values():
        styles[r["style"]] = styles.get(r["style"], 0) + 1
    print(f"[POSTARG] [입력] 서버 면 {len(API_MODULES)}개 모듈 · 라우트 {len(res['server'])}건 중 "
          f"POST {len(posts)}건 (술어=Python AST · 데코레이터 route.post)")
    print("[POSTARG] POST 인자 방식: "
          + " · ".join(f"{k} {v}" for k, v in sorted(styles.items())))
    print(f"[POSTARG] [입력] 화면 면 POST 호출 자리 {res['checked']}건 "
          f"(술어=주석·문자열 걷어 낸 뒤 괄호 균형 · 낱말 검색 아님)")

    if args.list:
        for k, r in sorted(posts.items()):
            print(f"  {r['style']:6} POST {r['path']:45} {r['name']}:{r['line']} "
                  f"질의={r['query']} 본문={r['body']}")

    if res["unresolved"]:
        # 못 읽은 것을 **0건 위반으로 적지 않는다.**
        print(f"[POSTARG] 잇지 못한 호출 {len(res['unresolved'])}건 — "
              f"**모수 밖으로 낸다**(어긋났는지 모른다):")
        for p, line, what in res["unresolved"]:
            print(f"  · {p.relative_to(ROOT)}:{line}  {what}")

    if res["violations"]:
        print("[POSTARG] 위반 — **서버는 질의를 기다리는데 화면이 본문으로 보낸다**")
        for p, line, path, fn, qargs in res["violations"]:
            print(f"  · {p.relative_to(ROOT)}:{line}  →  POST {path} ({fn}) 질의 인자 {qargs}")
        print("[POSTARG] 고치는 법: dsmPostQuery(url, {…}) 로 바꾼다 — "
              "조립은 한 곳이고, 손으로 짜면 또 빠진다")
        return EXIT_FAIL

    print("[POSTARG] 통과 — 본문/질의가 어긋난 자리 0건")
    return EXIT_OK


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("POST 인자 관용(본문이냐 질의냐) — 서버 면 **분모 %d모듈**(모수의 선언 · 늘면 "
               "여기를 고친다) + 화면 면 POST 호출 자리 전수를 그 자리에서 훑는다"
               % len(API_MODULES)),
    )
    raise SystemExit(main())
