#!/usr/bin/env python
"""주석 처리된 권한 데코레이터 전수 — 그리고 그 라우트가 **지금 열려 있는가** (D-334).

왜 필요한가
    권한 검사는 **없는 것보다 주석 처리된 것이 더 위험하다.** 없으면 「아직 안 붙였다」로
    읽히지만, 주석은 **「한때 붙어 있었다」**는 뜻이다. 그리고 코드를 읽는 사람에게는
    붙어 있는 것처럼 보인다 — 착시의 가장 나쁜 형태다 (D-334).

무엇을 재나 — 셋을 따로 잰다. **한 칸에 두지 않는다** (D-290)
    ① 정적 전수 : 권한 계열 데코레이터가 주석 상태로 존재하는 자리. **분모와 함께** (D-301)
    ② 런타임 대조: 그 핸들러가 실제로 등록된 라우트인가. `auth=` 콜백이 붙어 있는가
                   — 정적 grep 이 아니라 ninja 레지스트리를 읽는다
                   (`scan_auth_surface.py` 와 같은 이유: 동적 등록을 놓치지 않는다)
    ③ 실호출    : Authorization 헤더 **없이** 때렸을 때 무엇이 돌아오는가
                   → 「코드를 읽어서 답하지 마라」 (D-210 실측 우선)

    ★ ①만으로는 「열려 있다」고 말할 수 없다. `@path_permission` 은 **권한**이고
      `auth=` 는 **인증**이다 — 같은 이름이 아니다 (D-337 동음이의 계열).
      주석 처리된 권한 + 살아 있는 인증 = **인증된 아무 역할이나 통과**이고,
      주석 처리된 권한 + 없는 인증 = **익명 통과**다. 둘은 다른 사실이다.

권한 계열의 술어 (D-324 — 금지선은 행위에 긋는다)
    「없어지면 접근이 넓어지는 데코레이터」만 센다.
    · 포함: path_permission · oauth2_required · scope_required · tenant_scoped · ensure_csrf_cookie
    · 제외: csrf_exempt (주석 처리되면 **좁아진다**) · require_http_methods (메서드 제한이지 권한이 아니다)

읽기 전용이다 — DB 도 설정도 건드리지 않는다. ③의 호출은 Django 시험 클라이언트이고
GET/HEAD 만 때린다 (쓰기 메서드는 부작용이 있으므로 호출하지 않고 not_probed 로 남긴다).

실행 (컨테이너 안. 저장소 scripts/ 는 /repo/scripts 로 마운트되어 있다)

    MSYS_NO_PATHCONV=1 docker exec -e DJANGO_SETTINGS_MODULE=config.settings gx-shell \
      python /repo/scripts/probe_commented_guards.py /docs/agent/evidence/D-334/commented_guards.json

    정적 부분만 보려면 호스트에서도 돈다 (Django 불필요):
    python scripts/probe_commented_guards.py --static-only
"""
from __future__ import annotations

import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: 권한 계열 — **없어지면 접근이 넓어지는 것**만. 위 술어를 참조.
GUARD_DECORATORS = (
    "path_permission",
    "oauth2_required",
    "scope_required",
    "tenant_scoped",
    "tenant_scope.tenant_scoped",
    "ensure_csrf_cookie",
)

#: 일부러 제외한 것. **왜 제외했는지를 코드에 남긴다** — 다음 사람이 다시 묻지 않도록.
EXCLUDED_WITH_REASON = {
    "csrf_exempt": "주석 처리되면 접근이 좁아진다 — 권한 계열의 반대편이다",
    "require_http_methods": "메서드 제한이지 권한 판정이 아니다",
}

_ALT = "|".join(d.replace(".", r"\.") for d in GUARD_DECORATORS)
RE_COMMENTED = re.compile(r"^\s*#\s*@\s*(" + _ALT + r")\b")
RE_ACTIVE = re.compile(r"^\s*@\s*(" + _ALT + r")\b")
RE_DEF = re.compile(r"^(\s*)(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
RE_CLASS = re.compile(r"^(\s*)class\s+([A-Za-z_][A-Za-z0-9_]*)")
RE_ROUTE = re.compile(r"^\s*@\s*(route\.[a-z]+|api\.[a-z]+|router\.[a-z]+)\s*\(")


def _backend_root():
    """컨테이너에서는 /repo/backend, 호스트에서는 ./backend."""
    for cand in ("/repo/backend", os.path.join(os.getcwd(), "backend")):
        if os.path.isdir(cand):
            return cand
    raise SystemExit("backend/ 를 찾지 못했다 — 저장소 루트에서 돌리거나 컨테이너에서 돌려라")


def _enclosing_class(lines, idx):
    for i in range(idx, -1, -1):
        m = RE_CLASS.match(lines[i])
        if m:
            return m.group(2)
    return None


def _handler_after(lines, idx):
    """주석 줄 **아래**의 첫 def. 데코레이터가 겹쳐 있어도 def 까지 내려간다."""
    for i in range(idx + 1, min(idx + 25, len(lines))):
        m = RE_DEF.match(lines[i])
        if m:
            return m.group(2)
    return None


def _route_decorator_near(lines, idx):
    """같은 핸들러에 붙은 @route.*(...) 줄. 위아래 모두 본다 — 순서가 파일마다 다르다.

    괄호가 여러 줄에 걸칠 수 있으므로 닫힐 때까지 이어 붙인다.
    """
    for i in range(max(0, idx - 12), min(idx + 25, len(lines))):
        if not RE_ROUTE.match(lines[i]):
            continue
        buf, depth = "", 0
        for j in range(i, min(i + 20, len(lines))):
            buf += lines[j]
            depth += lines[j].count("(") - lines[j].count(")")
            if depth <= 0 and "(" in buf:
                break
        return " ".join(buf.split())
    return None


def static_census(root):
    commented, active_count, files_scanned = [], 0, 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in
                       ("__pycache__", ".git", "node_modules", "migrations", "static", "media")]
        for name in sorted(filenames):
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            rel = "backend/" + os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            files_scanned += 1
            for i, line in enumerate(lines):
                if RE_ACTIVE.match(line):
                    active_count += 1
                    continue
                m = RE_COMMENTED.match(line)
                if not m:
                    continue
                route = _route_decorator_near(lines, i)
                commented.append({
                    "file": rel,
                    "line": i + 1,
                    "decorator": m.group(1),
                    "source": line.strip(),
                    "class": _enclosing_class(lines, i),
                    "handler": _handler_after(lines, i),
                    "route_decorator": route,
                    # 정적 힌트일 뿐이다. 진실은 런타임 레지스트리가 말한다.
                    "auth_kwarg_in_source": bool(route and "auth=" in route),
                })
    commented.sort(key=lambda r: (r["file"], r["line"]))
    return {
        "files_scanned": files_scanned,
        "guard_decorators": list(GUARD_DECORATORS),
        "excluded_with_reason": EXCLUDED_WITH_REASON,
        "denominator_total_guard_usages": active_count + len(commented),
        "active": active_count,
        "commented": len(commented),
        "commented_rows": commented,
    }


def runtime_cross_reference(census):
    """ninja 레지스트리에서 그 핸들러를 찾아 auth= 유무와 실제 경로를 확인한다."""
    sys.path.insert(0, "/app")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()

    from common.tenant_scope import _iter_ninja_apis, _join

    by_name = {}
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    qual = getattr(view, "__qualname__", getattr(view, "__name__", "?"))
                    callbacks = getattr(op, "auth_callbacks", None) or []
                    by_name.setdefault(qual.split(".")[-1], []).append({
                        "path": _join(mount, prefix, op_path),
                        "methods": ",".join(str(m).upper() for m in (getattr(op, "methods", []) or [])),
                        "qualname": qual,
                        "module": getattr(view, "__module__", "?"),
                        "has_auth": bool(callbacks),
                        "auth": [type(c).__name__ for c in callbacks],
                        "has_path_permission": bool(getattr(view, "_path_override", None)),
                    })

    for row in census["commented_rows"]:
        handler, klass = row.get("handler"), row.get("class")
        cands = by_name.get(handler or "", [])
        if klass:
            narrowed = [c for c in cands if c["qualname"].startswith(klass + ".")]
            cands = narrowed or cands
        row["runtime_matches"] = cands
        if not cands:
            row["registered"] = False
            row["verdict"] = "unregistered"            # 라우트로 등록되지 않았다 — 접근면이 아니다
        else:
            row["registered"] = True
            row["verdict"] = ("authn_only" if all(c["has_auth"] for c in cands)
                              else "no_authn_no_authz")  # ★ 익명 도달 후보
    return census


def _stub_probe_write(path, method):
    """쓰기 라우트가 **인증을 통과하는가**만 잰다 — 핸들러는 한 줄도 돌지 않는다.

    왜 이렇게까지 하나: 쓰기 메서드를 그냥 때리면 부작용이 남는다. 그렇다고 안 때리면
    「auth 콜백이 비어 있으니 열려 있을 것」이라는 **추정**이 된다 (D-280 금지).
    그래서 등록된 view_func 를 도달 표시만 남기는 대체물로 잠시 바꾸고 때린다.
    · 도달했다  = 인증 관문이 없다 (핸들러 자리까지 익명으로 왔다)
    · 401       = 인증 관문이 막았다
    끝나면 원래 함수를 반드시 되돌린다.
    """
    from django.test import Client
    from common.tenant_scope import _iter_ninja_apis, _join

    target, saved = None, None
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    if _join(mount, prefix, op_path) != path:
                        continue
                    if method not in [str(m).upper() for m in (getattr(op, "methods", []) or [])]:
                        continue
                    target = op
    if target is None:
        return {"reached": None, "status": None, "note": "라우트를 다시 찾지 못했다"}

    marker = {"hit": False}

    def _stub(request, *a, **kw):
        marker["hit"] = True
        raise _ReachedHandler()

    saved = target.view_func
    try:
        target.view_func = _stub
        client = Client(raise_request_exception=False)
        probe_path = re.sub(r"\{[^}]+\}", "1", path)
        try:
            resp = client.generic(method, probe_path, data=b"{}",
                                  content_type="application/json")
            status = resp.status_code
        except _ReachedHandler:
            status = None
        except Exception as exc:                # noqa: BLE001
            status = None
            marker.setdefault("exc", ("%s: %s" % (type(exc).__name__, exc))[:120])
    finally:
        target.view_func = saved

    return {
        "reached": marker["hit"],
        "status": status,
        "note": ("핸들러 자리 도달 — 인증 관문 없음 (대체물이 받았고 본체는 돌지 않았다)"
                 if marker["hit"] else "핸들러에 도달하지 못했다"),
    }


class _ReachedHandler(Exception):
    """대체물이 도달을 알리는 신호. 본체 대신 이것이 던져진다 — 부작용이 없다."""


def live_probe(census, probe_writes=False):
    """Authorization 헤더 **없이** 때린다. 코드를 읽어서 답하지 않는다 (D-210)."""
    from django.test import Client

    client = Client()
    seen = {}
    for row in census["commented_rows"]:
        results = []
        for c in row.get("runtime_matches", []):
            methods = [m for m in c["methods"].split(",") if m]
            if not any(m in ("GET", "HEAD") for m in methods):
                write_methods = [m for m in methods if m not in ("GET", "HEAD", "OPTIONS")]
                if probe_writes and write_methods and not c["has_auth"]:
                    rec = _stub_probe_write(c["path"], write_methods[0])
                    rec.update({"path": c["path"], "methods": c["methods"],
                                "probe_kind": "stub"})
                    results.append(rec)
                    continue
                results.append({"path": c["path"], "methods": c["methods"], "status": None,
                                "note": "not_probed — 쓰기 메서드는 부작용이 있어 때리지 않는다"})
                continue
            # 경로 파라미터는 1 로 채운다. 404 와 401/403 은 서로 다른 사실이다.
            path = re.sub(r"\{[^}]+\}", "1", c["path"])
            key = "GET " + path
            if key in seen:
                results.append(dict(seen[key], path=path, methods=c["methods"]))
                continue
            try:
                resp = client.get(path)
                rec = {"path": path, "methods": c["methods"], "status": resp.status_code, "note": ""}
            except Exception as exc:            # noqa: BLE001 — 무엇이 터졌는지도 사실이다
                rec = {"path": path, "methods": c["methods"], "status": None,
                       "note": ("raised: %s: %s" % (type(exc).__name__, exc))[:200]}
            seen[key] = rec
            results.append(rec)
        row["anonymous_probe"] = results
    return census


def _summarize(census):
    rows = census["commented_rows"]
    verdicts = {}
    for r in rows:
        v = r.get("verdict", "static_only")
        verdicts[v] = verdicts.get(v, 0) + 1
    by_file = {}
    for r in rows:
        by_file[r["file"]] = by_file.get(r["file"], 0) + 1
    reachable, reached = [], []
    for r in rows:
        for p in r.get("anonymous_probe", []) or []:
            row = {"file": r["file"], "line": r["line"], "handler": r["handler"]}
            row.update(p)
            # 2xx 를 익명으로 받았다면 그것이 「지금 열려 있다」이다.
            if p.get("status") is not None and 200 <= p["status"] < 300:
                reachable.append(row)
            # 401 이 아니면 인증 관문을 지난 것이다 — 4xx/5xx 라도 「핸들러에 닿았다」는 사실이다.
            if p.get("reached") is True or (
                    p.get("status") is not None and p["status"] not in (401, 403)):
                reached.append(row)
    return {
        "denominator_total_guard_usages": census["denominator_total_guard_usages"],
        "active": census["active"],
        "commented": census["commented"],
        "by_verdict": dict(sorted(verdicts.items())),
        "by_file": dict(sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))),
        "anonymously_reachable_2xx": reachable,
        "anonymously_reachable_count": len(reachable),
        # ★ 이쪽이 보안 판정의 본체다. 200 이 아니어도 인증 없이 핸들러에 닿았으면 열린 것이다.
        "anonymously_reached_handler": reached,
        "anonymously_reached_count": len(reached),
    }


def main():
    argv = list(sys.argv[1:])
    static_only = "--static-only" in argv
    probe_writes = "--probe-writes" in argv
    argv = [a for a in argv if not a.startswith("--")]

    census = static_census(_backend_root())
    if not static_only:
        census = runtime_cross_reference(census)
        census = live_probe(census, probe_writes=probe_writes)
    census["summary"] = _summarize(census)
    census["note"] = ("D-334 · 주석 처리된 권한 데코레이터 전수. verdict 는 셋이다: "
                      "unregistered(라우트 아님) · authn_only(인증은 있고 권한만 꺼짐) · "
                      "no_authn_no_authz(익명 도달 후보). anonymously_reachable_2xx 가 "
                      "「지금 열려 있는가」의 실측 답이다.")

    out = argv[0] if argv else None
    if out:
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(census, f, ensure_ascii=False, indent=2)
            f.write("\n")
    s = census["summary"]
    print("[GUARDS] 분모=%s 활성=%s 주석=%s 판정=%s 익명2xx=%s 익명도달=%s -> %s" % (
        s["denominator_total_guard_usages"], s["active"], s["commented"],
        s["by_verdict"], s["anonymously_reachable_count"],
        s.get("anonymously_reached_count"), out or "(stdout only)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
