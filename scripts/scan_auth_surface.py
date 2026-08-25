#!/usr/bin/env python
"""인증 표면 실측 — `auth=` 콜백이 없는 라우트를 전수로 세고 성격별로 가른다 (P-W0-18-2).

왜 필요한가
    `@path_permission` 은 **권한**만 본다. 요청자가 누구인지는 `auth=` 콜백
    (`CustomJWTAuth`)이 정한다. 둘 중 하나만 붙은 라우트에서는 인증 관문 없이
    미들웨어가 복원한 사용자로 권한 판정까지 도달한다 (W0-18 영향조사 실측).
    P-W0-18-2 의 기본값 C 는 "24건 각각이 의도된 공개 라우트인지 먼저 조사"다.
    이 스크립트가 그 조사의 기계 판독 부분을 한다 — 판정은 사람이 한다.

무엇을 재나
    런타임 ninja 레지스트리를 훑어 라우트마다 넷을 기록한다:
      · auth 콜백 유무          (`Operation.auth_callbacks`)
      · @path_permission 유무   (`view_func._path_override`)
      · 뷰의 모듈·이름          (사람이 성격을 판정할 근거)
      · 자동 분류 힌트          (이름·경로에 공개 라우트 관용어가 있는가)
    **정적 grep 이 아니라 레지스트리를 읽는다** — 동적 등록을 놓치지 않기 위해서다
    (`common/api_contract.py::classify_permission_routes` 와 같은 이유).

    ⚠️ 힌트는 힌트다. "health" 라는 이름이 공개를 뜻하지는 않는다.
       이 스크립트는 사람이 볼 목록을 좁힐 뿐, 무엇도 공개로 판정하지 않는다.

읽기 전용이다 — DB 도 설정도 건드리지 않는다. 결과는 **파일로** 쓴다: 이 앱은 기동 중
stdout 에 배너를 뿌려서 리다이렉트로는 JSON 이 오염된다.

컨테이너 안에서 돌린다 (저장소 scripts/ 는 마운트되지 않는다):

    docker cp scripts/scan_auth_surface.py gx-shell:/tmp/
    docker exec gx-shell python /tmp/scan_auth_surface.py /docs/agent/evidence/W0-18/auth_surface.json
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

#: 공개 라우트에서 자주 쓰이는 말. **판정이 아니라 정렬용 힌트다.**
PUBLIC_HINTS = (
    "health", "healthz", "ping", "status", "readiness", "liveness",
    "webhook", "callback", "login", "token", "refresh", "register",
    "public", "docs", "openapi", "csrf", "version",
)


def _hint(label: str, view_name: str) -> list[str]:
    haystack = f"{label} {view_name}".lower()
    return [w for w in PUBLIC_HINTS if w in haystack]


def main() -> int:
    from common.tenant_scope import _iter_ninja_apis, _join

    rows: list[dict] = []
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    view = getattr(op, "view_func", None)
                    methods = ",".join(str(m).upper() for m in (getattr(op, "methods", []) or []))
                    path = _join(mount, prefix, op_path)
                    callbacks = getattr(op, "auth_callbacks", None) or []
                    view_name = "{}.{}".format(
                        getattr(view, "__module__", "?"),
                        getattr(view, "__qualname__", getattr(view, "__name__", "?")),
                    )
                    label = f"{methods} {path}"
                    rows.append({
                        "route": label,
                        "path": path,
                        "methods": methods,
                        "has_auth": bool(callbacks),
                        "auth": [type(c).__name__ for c in callbacks],
                        "has_path_permission": bool(getattr(view, "_path_override", None)),
                        "path_override": getattr(view, "_path_override", None),
                        "view": view_name,
                        "public_hints": _hint(label, view_name),
                    })

    rows.sort(key=lambda r: r["route"])
    no_auth = [r for r in rows if not r["has_auth"]]
    gap = [r for r in no_auth if r["has_path_permission"]]

    payload = {
        "note": "P-W0-18-2 · 인증 표면 실측. has_auth=false 이고 has_path_permission=true 가 "
                "'권한은 보는데 인증은 안 보는' 라우트다. public_hints 는 판정이 아니라 정렬용 힌트.",
        "totals": {
            "routes": len(rows),
            "no_auth": len(no_auth),
            "no_auth_with_path_permission": len(gap),
            "no_auth_without_path_permission": len(no_auth) - len(gap),
        },
        "by_app_gap": _count_by_app(gap),
        "gap_routes": gap,
        "no_auth_routes_without_permission": [r for r in no_auth if not r["has_path_permission"]],
        "all_routes": rows,
    }

    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/auth_surface.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("[AUTH] routes={routes} no_auth={no_auth} gap={no_auth_with_path_permission} -> {out}".format(
        out=out, **payload["totals"]))
    return 0


def _count_by_app(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        app = r["view"].split(".")[0]
        counts[app] = counts.get(app, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


if __name__ == "__main__":
    raise SystemExit(main())
