#!/usr/bin/env python
"""P-W0-18-1 검증 — 대상 라우트의 **OpenAPI 응답 선언**을 뜬다 (W0-18).

`response=<단일 스키마>` 를 떼면 OpenAPI 문서가 무엇을 잃는가를 대조하기 위한 도구다.
제거 전후로 두 번 돌려 `diff` 한다 — 이 저장소에서는 **두 결과가 같았다**
(`docs/agent/evidence/W0-18/response_decl_before_after.md` §4).

읽기 전용이다 — DB 도 스키마도 건드리지 않는다. 결과는 **파일로** 쓴다: 이 앱은 기동 중
stdout 에 배너를 뿌려서 리다이렉트로는 JSON 이 오염된다 (dump_openapi_routes.py 와 같은 이유).

컨테이너 안에서 돌린다 (저장소 scripts/ 는 마운트되지 않는다):

    docker cp scripts/probe_openapi_response_decl.py gx-shell:/tmp/probe.py
    docker exec gx-shell python /tmp/probe.py /tmp/after.json
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

TARGETS = {
    "/api/report-template/openapi.json": [
        ("get", "/api/report-template/{id}"),
        ("post", "/api/report-template/"),
        ("put", "/api/report-template/{id}"),
        ("delete", "/api/report-template/delete/{ids}"),
        ("get", "/api/report-template/"),  # B 부류 — 무변경 대조군
    ],
    "/api/checklist-setting/openapi.json": [
        ("post", "/api/checklist-setting/"),
        ("put", "/api/checklist-setting/{id}"),
        ("delete", "/api/checklist-setting/delete/{ids}"),
        ("put", "/api/checklist-setting/{id}/activate"),
        ("get", "/api/checklist-setting/"),  # B 부류 — 무변경 대조군
    ],
}


def main() -> int:
    client = Client()
    result: dict[str, object] = {}
    for schema_url, ops in TARGETS.items():
        res = client.get(schema_url)
        if res.status_code != 200:
            result[schema_url] = {"_error": res.status_code}
            continue
        spec = json.loads(res.content)
        paths = spec.get("paths", {})
        for method, path in ops:
            entry = paths.get(path, {}).get(method)
            key = f"{method.upper()} {path}"
            if entry is None:
                result[key] = None
                continue
            responses = entry.get("responses", {})
            result[key] = {
                code: (body.get("content", {}) or {}).get("application/json", {}).get("schema")
                for code, body in responses.items()
            }
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/openapi_decl.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"[DECL] {len(result)} ops -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
