#!/usr/bin/env python
"""OpenAPI 라우트 실측 대장 — 경로 + 허용 메서드 (W0-14).

`route_baseline.json` 은 개수만 센다. 격리 시험이 실제로 부를 수 있는 경로를
고르려면 **경로 문자열과 허용 메서드**가 필요하다. django-ninja 는 앱마다
NinjaAPI 를 하나씩 두므로 `/api/<app>/openapi.json` 을 전부 긁어 합친다.

컨테이너 안에서 돌린다 (저장소 scripts/ 는 마운트되지 않는다):

    docker cp scripts/dump_openapi_routes.py gx-shell:/tmp/
    docker exec gx-shell python /tmp/dump_openapi_routes.py /docs/agent/evidence/W0-14/openapi_routes.json

결과는 **파일로** 쓴다 — 이 앱은 기동 중 stdout 에 배너를 뿌려서(MinIO·DJANGO_READY)
표준출력 리다이렉트로는 JSON 이 오염된다.

읽기 전용이다 — DB 를 건드리지 않는다.
"""
from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app")

import os  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.test import Client  # noqa: E402
from django.urls import get_resolver  # noqa: E402


def all_patterns(resolver, prefix: str = "") -> list[str]:
    out: list[str] = []
    for p in resolver.url_patterns:
        pat = prefix + str(p.pattern)
        if hasattr(p, "url_patterns"):
            out += all_patterns(p, pat)
        else:
            out.append(pat)
    return out


def main() -> int:
    schemas = sorted({u for u in all_patterns(get_resolver()) if u.endswith("openapi.json")})
    client = Client()
    routes: dict[str, list[str]] = {}
    failed: dict[str, int] = {}

    for schema_url in schemas:
        res = client.get("/" + schema_url)
        if res.status_code != 200:
            failed["/" + schema_url] = res.status_code
            continue
        spec = json.loads(res.content)
        # 이 저장소의 ninja API 는 spec path 에 마운트 prefix 를 **이미 포함**한다
        # (`/api/orders/order/`). 포함돼 있지 않은 API 만 prefix 를 덧붙인다 —
        # 무조건 붙이면 `/api/orders/api/orders/order/` 같은 유령 경로가 나온다.
        prefix = "/" + schema_url[: -len("openapi.json")]
        for path, ops in spec.get("paths", {}).items():
            if path.startswith(prefix):
                full = path
            else:
                full = (prefix.rstrip("/") + path) if path != "/" else prefix
            methods = sorted(m.upper() for m in ops if m.lower() in
                             {"get", "post", "put", "patch", "delete"})
            routes[full] = methods

    out_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/openapi_routes.json"
    payload = {
        "note": "W0-14 · openapi 실측 라우트 대장 (경로+메서드). 격리 시험 api_base 근거.",
        "schema_count": len(schemas),
        "route_count": len(routes),
        "failed_schemas": failed,
        "routes": dict(sorted(routes.items())),
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[ROUTES] schemas={len(schemas)} routes={len(routes)} failed={failed} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
