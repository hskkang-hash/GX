#!/usr/bin/env python
"""타임아웃 없는 외부 호출 실측 (W0-17 ② · 2026-08-27 C-3.3 로 확대).

무엇을 세나
    외부 의존 호출 중 **타임아웃이 걸리지 않은 것**. 타임아웃 없는 호출 하나가 늦으면
    워커가 잡히고, 잡힌 워커가 쌓이면 서비스 전체가 선다 — 부분 실패가 전면 정지가 되는 경로다.

    계열마다 타임아웃을 **거는 자리가 다르다**. 그래서 두 갈래로 잰다:
      · 호출마다 `timeout=` 을 받는 것 — requests · httpx · aiohttp · urllib(3) · socket · grpc
      · **생성자에서 한 번** 정하는 것 — MinIO (`http_client=PoolManager(timeout=…)`)
    호출 단위로만 세면 MinIO 는 "고칠 수 없는 21곳을 고치라"는 보고가 된다 (CTOR_TIMEOUT 주석).

왜 grep 이 아니라 AST 인가
    grep 은 주석·문자열·여러 줄 호출을 잘못 세고, 무엇보다 **이름이 비슷한 것을 같이 센다**
    (redis `client.get` · Django 테스트 `client.get` · dict `.get`). 이 파일은 `ast` 로
    호출 노드를 보고 `requests` 계열만 고른다. **이 수가 정본이다.**

    지시서의 "49건"은 grep 추정치였다. 실측은 아래 출력이 말한다 (D-214 · 실측 우선).

사용:
    python scripts/scan_request_timeouts.py backend            # 표
    python scripts/scan_request_timeouts.py backend --json     # 기계 판독
    python scripts/scan_request_timeouts.py backend --check    # 미조치 있으면 exit 1 (게이트용)

제외: 마이그레이션·가상환경·캐시. 관리 커맨드·배치는 **포함**한다 — 배치가 매달리는 것도
      같은 사고다.
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

#: 저장소 뿌리. 면제 목록(EXEMPT)의 키를 **호출 방식과 무관하게** 맞추기 위해 쓴다.
#:
#: 실측(2026-08-27): `verify_timeout.py` 가 절대경로로 부르자 rel 이 절대경로가 되어
#: 면제 4건이 **전부 풀렸다** — 게이트가 부르는 방법에 따라 다른 답을 냈다는 뜻이다.
#: 부르는 방법이 답을 바꾸면 그 수는 정본이 될 수 없다.
REPO_ROOT = Path(__file__).resolve().parent.parent

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "request"}
SKIP_PARTS = {"migrations", "venv", "node_modules", "__pycache__", ".git"}

# ─────────────────────────────────────────────────────────────────────────────
# 2026-08-27 확장 (C-3.3 · 규약 §2) — `requests` 만 보던 것을 **외부 의존 전부**로 넓힌다
#
# 왜: C-3.3 은 "SDN·기상·위성·**저장소** 등 외부 호출"이라고 썼는데, 이 파일은
#     `requests` 만 셌다. 실측하면 backend 에 `urllib` 9파일 · `urllib3` 2 · `aiohttp` 1 ·
#     `minio` 1 · `grpc` 2 · `socket` 1 이 더 있다 — **전부 이 게이트 밖이었다.**
#
# 이것이 이론이 아님을 오늘 봤다. 백필을 돌릴 때마다 MinIO 초기화가
# `minio.invalid` 를 향해 **5회 재시도**를 두 번 돌았다(로그 실증). 타임아웃이 없어서
# 매 실행이 그만큼 매달린다 — C-3.3 이 말한 "부분 실패가 전면 정지가 되는 경로" 그대로다.
#
# ★ 새 게이트를 만들지 않고 **이 엔진을 넓혔다** (원칙 1: 중복 0).
#   같은 일을 하는 스크립트가 둘이 되면 언젠가 두 수가 갈리고,
#   그때 어느 쪽이 진실인지 알 수 없게 된다 — D-227 이 만든 상태다.
#   규약 §2 가 이름 붙인 `verify_timeout.py` 는 이 엔진을 **호출하는 얇은 게이트**다.
# ─────────────────────────────────────────────────────────────────────────────

#: 외부 호출 계열 → (모듈 이름, 타임아웃 인자로 인정하는 키워드)
#:
#: ⚠ 계열을 **모듈 이름으로** 고른다. 메서드 이름만으로 세면 `dict.get` · Django 테스트
#:   `client.get` 이 같이 잡힌다(D-263 이름 매칭 금지). 사슬의 뿌리를 본다.
FAMILIES: dict[str, tuple[set[str], set[str]]] = {
    # requests — 기존 대상. Session 객체 추적은 아래 _session_names 가 따로 한다
    "requests": (HTTP_METHODS, {"timeout"}),
    # httpx — 동기/비동기 모두 timeout=
    "httpx": (HTTP_METHODS | {"stream"}, {"timeout"}),
    # aiohttp — ClientSession.get(...) 등. timeout= 또는 ClientTimeout 주입
    "aiohttp": (HTTP_METHODS, {"timeout"}),
    # urllib.request — urlopen(url, timeout=…)
    "urllib": ({"urlopen"}, {"timeout"}),
    "urlopen": ({"urlopen"}, {"timeout"}),
    # urllib3 — PoolManager.request(...)
    "urllib3": ({"request", "urlopen"}, {"timeout"}),
    # socket — connect 계열. create_connection(addr, timeout=…)
    "socket": ({"create_connection"}, {"timeout"}),
    # gRPC — 여기서는 timeout 이 아니라 deadline 개념이지만 인자 이름은 timeout 이다
    "grpc": ({"unary_unary", "unary_stream", "stream_unary", "stream_stream"},
             {"timeout"}),
    # MinIO — 호출 단위 메서드는 **비워 둔다.** 타임아웃은 생성자에서 정한다(CTOR_TIMEOUT).
    # 여기 남겨 두는 이유는 import 를 인식해 클라이언트 이름을 추적하기 위해서다.
    "minio": (set(), {"timeout"}),
}

#: ★ **생성자에서 타임아웃을 정하는 계열** — 호출마다 `timeout=` 을 받지 않는다.
#:
#: 첫 판은 MinIO 를 호출 단위로 셌다. 그래서 `get_object` · `fput_object` 21건이
#: "타임아웃 없음"으로 나왔다 — **그런데 MinIO 파이썬 SDK 는 그 인자를 받지 않는다.**
#: 타임아웃은 `Minio(..., http_client=urllib3.PoolManager(timeout=…))` 로 **한 번** 정한다.
#: 즉 21건을 고치라는 보고는 **고칠 수 없는 곳을 고치라는 말**이었다. 게이트가 틀린 곳을
#: 가리키면 사람은 그 게이트를 믿지 않게 되고, 안 믿는 게이트는 꺼진 게이트와 같다.
#: → 실측할 곳은 **생성 지점 하나**다. 그것이 진짜 결함이고 진짜 고칠 자리다.
CTOR_TIMEOUT: dict[str, set[str]] = {
    "Minio": {"http_client"},          # http_client=PoolManager(timeout=…) 로 준다
}

#: 사유와 함께 면제된 호출. `(파일 상대경로, 줄번호)` → 사유.
#: 여기에 넣는 것은 **"이 호출은 매달려도 된다"는 선언**이 아니라,
#: "정적으로 보이지 않을 뿐 타임아웃이 들어간다"는 선언이다. 추측으로 넣지 않는다.
#: 셋 다 `kwargs.setdefault("timeout", …)` 로 **직전 줄에서** 넣는 형태라 AST 가 못 본다.
EXEMPT: dict[tuple[str, int], str] = {
    ("backend/common/external_http.py", 77):
        "request() — 바로 위에서 kwargs.setdefault('timeout', default_timeout())",
    ("backend/common/external_http.py", 109):
        "fetch_json() — 바로 위에서 kwargs.setdefault('timeout', default_timeout())",
    ("backend/delivery/decorators.py", 381):
        "외부 연동 데코레이터 — request_kwargs.setdefault('timeout', default_timeout())",
    ("backend/stream_monitors/services/frame_detection_pb2_grpc.py", 87):
        "protoc 가 생성한 스텁이다. timeout 을 **위치 인자로** 넘기고 있어(13번째) AST 의 "
        "키워드 검사에 안 잡힌다. 손으로 쓴 호출이 아니므로 고칠 자리는 여기가 아니라 "
        "이 스텁을 부르는 쪽이다 — 그쪽에 deadline 을 주는지는 W0-17 후속에서 본다",
}


def _rel(path: Path) -> str:
    """저장소 뿌리 기준 상대경로. 절대경로로 불러도 면제 키가 맞아야 한다."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _session_names(tree: ast.AST) -> set[str]:
    """이 파일 안에서 `requests.Session()` 이 대입된 이름들."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if isinstance(func, ast.Attribute) and func.attr == "Session":
            base = func.value
            if isinstance(base, ast.Name) and base.id == "requests":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
                    elif isinstance(target, ast.Attribute):
                        names.add(target.attr)
    return names


def _chain_root(node: ast.AST) -> list[str]:
    """수신자 사슬을 뿌리까지. 이름 하나가 아니라 **닿는 곳**으로 계열을 가른다."""
    out: list[str] = []
    cur = node
    while True:
        if isinstance(cur, ast.Attribute):
            out.append(cur.attr); cur = cur.value
        elif isinstance(cur, ast.Call):
            cur = cur.func
        elif isinstance(cur, ast.Name):
            out.append(cur.id); break
        elif isinstance(cur, ast.Subscript):
            cur = cur.value
        else:
            break
    return list(reversed(out))


#: 외부 클라이언트를 만드는 생성자 → 그 클라이언트가 속한 계열.
#:
#: 왜 필요한가 — `requests.Session()` 을 이름으로 추적하던 것과 **같은 이유**다.
#: 실측: `minio_client.py` 는 `self.client = Minio(...)` 로 감싸고, 다른 파일들은
#: `minio_client.client.get_object(...)` 로 부른다. 사슬 어디에도 `minio` 라는 말이 없다.
#: 계열 이름만 찾으면 **MinIO 호출 전부를 놓친다** — 오늘 실제로 매달린 그 경로를.
CLIENT_CTORS: dict[str, str] = {
    "Minio": "minio",
    "PoolManager": "urllib3",
    "ClientSession": "aiohttp",
    "Client": "httpx",
    "AsyncClient": "httpx",
}


def _client_names(tree: ast.AST, families: set[str]) -> dict[str, str]:
    """`x = Minio(...)` · `self.client = Minio(...)` 의 이름 → 계열.

    ★ **생성자 이름만으로 세지 않는다** (D-263). `Client()` 는 httpx 도 쓰고
      Django 테스트 클라이언트도 쓴다 — 첫 판이 그 둘을 같이 세서
      `test_api_contract.py` 의 테스트 클라이언트 12건을 "타임아웃 없는 httpx 호출"로
      보고했다. **내가 막으려던 그 함정에 내가 빠진 것이다.**
      그래서 그 파일이 **그 계열을 실제로 import 했을 때만** 클라이언트로 인정한다.
    """
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        ctor = func.id if isinstance(func, ast.Name) else (
            func.attr if isinstance(func, ast.Attribute) else None)
        fam = CLIENT_CTORS.get(ctor or "")
        if not fam or fam not in families:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                out[target.id] = fam
            elif isinstance(target, ast.Attribute):
                out[target.attr] = fam       # self.client → 'client'
    return out


def _imported_families(tree: ast.AST) -> set[str]:
    """이 파일이 실제로 import 한 계열만 본다 — 이름이 겹치는 남의 객체를 안 세기 위해."""
    fams: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FAMILIES:
                    fams.add(root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in FAMILIES:
                fams.add(root)
            for a in node.names:                      # from urllib.request import urlopen
                if a.name in FAMILIES:
                    fams.add(a.name)
    return fams


def is_request_call(node: ast.Call, session_names: set[str],
                    families: set[str] | None = None,
                    clients: dict[str, str] | None = None) -> tuple[str, set[str]] | None:
    """외부 호출이면 `(표기, 타임아웃으로 인정할 키워드들)` 을 준다.

    `requests` 는 기존대로 보고, 나머지 계열은 **그 파일이 import 한 것**만 본다.
    import 하지 않은 이름이 우연히 같은 것은 외부 호출이 아니다 (D-263 이름 매칭 금지).
    """
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    attr = func.attr
    chain = _chain_root(func.value)
    names = set(chain)

    # ① requests — 모듈 직접 호출 또는 Session 객체
    if attr in HTTP_METHODS and ("requests" in names or names & session_names):
        who = "requests" if "requests" in names else next(iter(names & session_names))
        return f"{who}.{attr}", {"timeout"}

    # ② 감싼 클라이언트 — `self.client = Minio(...)` 를 `minio_client.client.get_object()` 로 부른다.
    #    계열 이름이 사슬에 없으므로 **생성자 추적**이 없으면 통째로 놓친다.
    if clients:
        for part in chain:
            fam = clients.get(part)
            if fam and attr in FAMILIES[fam][0]:
                return f"{part}({fam}).{attr}", FAMILIES[fam][1]

    # ③ 나머지 계열 — 사슬의 어느 마디든 계열 이름에 닿고, 그 계열을 import 했을 때만
    for fam, (methods, tkw) in FAMILIES.items():
        if fam == "requests" or attr not in methods:
            continue
        if families is not None and fam not in families:
            continue
        if fam in names:
            return f"{fam}…{attr}", tkw
    return None


def scan(root: Path) -> dict:
    missing: list[dict] = []
    with_timeout = 0
    unparsed: list[str] = []

    # ── 1차: 파일들을 읽고 **감싼 클라이언트 이름을 전 저장소에서 모은다** ──────────
    #   한 파일에서 `self.client = Minio(...)` 로 만들고 **다른 파일에서** 부르기 때문이다
    #   (`minio_client.client.get_object(...)`). 파일 단위로만 보면 그 호출이 안 보인다.
    parsed: list[tuple[Path, ast.AST]] = []
    clients: dict[str, str] = {}
    for path in sorted(root.rglob("*.py")):
        if set(path.parts) & SKIP_PARTS:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        # 확장 전에는 `"requests" not in text` 로 걸렀다 — 그래서 urllib·minio·grpc 가
        # **전부 보이지 않았다.** 계열 이름 중 하나라도 없으면 그때 건너뛴다.
        if not (any(f in text for f in FAMILIES) or any(c in text for c in CLIENT_CTORS)):
            continue
        try:
            tree = ast.parse(text, str(path))
        except SyntaxError as exc:
            # ★ 건너뛰지 않는다 (D-264). 못 읽은 파일은 "타임아웃이 있다"가 아니라
            #   **"보지 않았다"**이고, 조용히 지나가는 검사는 게이트가 아니라 장식이다.
            unparsed.append(f"{path.as_posix()}:{exc.lineno} {exc.msg}")
            continue
        parsed.append((path, tree))
        clients.update(_client_names(tree, _imported_families(tree)))

    # ── 2차: 판정 ───────────────────────────────────────────────────────────────
    for path, tree in parsed:
        sessions = _session_names(tree)
        families = _imported_families(tree)
        rel = _rel(path)

        # ① 생성자에서 타임아웃을 정하는 계열 (MinIO 등) — 만드는 자리 하나만 본다
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            ctor = fn.id if isinstance(fn, ast.Name) else (
                fn.attr if isinstance(fn, ast.Attribute) else None)
            need = CTOR_TIMEOUT.get(ctor or "")
            if need is None or CLIENT_CTORS.get(ctor or "") not in families:
                continue
            if any(k.arg in need for k in node.keywords if k.arg):
                with_timeout += 1
            else:
                missing.append({
                    "file": rel, "line": node.lineno,
                    "call": f"{ctor}(…) — {'/'.join(sorted(need))} 없음",
                    "exempt_reason": EXEMPT.get((rel, node.lineno)),
                })

        # ② 호출마다 timeout= 을 받는 계열
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            found = is_request_call(node, sessions, families, clients)
            if found is None:
                continue
            call, tkw = found
            if any(k.arg in tkw for k in node.keywords if k.arg):
                with_timeout += 1
                continue
            missing.append({
                "file": rel,
                "line": node.lineno,
                "call": call,
                "exempt_reason": EXEMPT.get((rel, node.lineno)),
            })
    return {"missing": missing, "with_timeout": with_timeout, "unparsed": unparsed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default="backend")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="면제되지 않은 미조치가 있으면 exit 1")
    args = ap.parse_args()

    result = scan(Path(args.root))
    missing = result["missing"]
    open_items = [f for f in missing if not f["exempt_reason"]]

    if args.json:
        print(json.dumps({
            "with_timeout": result["with_timeout"],
            "missing_total": len(missing),
            "open": len(open_items),
            "findings": missing,
        }, ensure_ascii=False, indent=2))
    else:
        by_file: dict[str, int] = {}
        for f in open_items:
            by_file[f["file"]] = by_file.get(f["file"], 0) + 1
        total = result["with_timeout"] + len(missing)
        print(f"[TIMEOUT] 외부 호출 {total}건 중 타임아웃 없는 것 {len(open_items)}건 "
              f"/ {len(by_file)}파일 (면제 {len(missing) - len(open_items)}건 · "
              f"타임아웃 있음 {result['with_timeout']}건)")
        print(f"[TIMEOUT] 본 계열: {' · '.join(sorted(FAMILIES))}")
        for name, count in sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"  {count:3d}  {name}")
        for f in sorted(open_items, key=lambda x: (x["file"], x["line"]))[:20]:
            print(f"      {f['file']}:{f['line']}  {f['call']}()")

    # ★ 못 읽은 파일은 실패다 (D-264). "타임아웃이 있다"가 아니라 "보지 않았다"이다.
    for u in result["unparsed"]:
        print(f"[TIMEOUT] ✗ 파싱 실패 — 판정하지 않았다: {u}")

    if args.check and (open_items or result["unparsed"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
