#!/usr/bin/env python3
"""GCS 서버 키와 클라이언트 키가 같은 값이면 실패시킨다 (W0-1a / D-003).

배경: backend 의 GCS_APIKEY 와 frontend 의 VITE_CGS_APIKEY 가 동일한 UUID 였다.
클라이언트 키는 브라우저 번들에 실려 사실상 공개되므로, 같은 값을 쓰면
서버 키까지 공개된 것과 같다. 재발급만 해서는 같은 상태가 반복된다.

gitleaks 는 파일 하나 안의 패턴만 본다. 두 파일의 '값이 같은지'는 볼 수 없어
별도 훅으로 검사한다.

검사 대상: 저장소 안의 모든 .env* 파일 (example 포함, gitignore 여부 무관).
플레이스홀더끼리 같은 것은 무시한다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SERVER_KEY = "GCS_APIKEY"
CLIENT_KEY = "VITE_CGS_APIKEY"

PLACEHOLDER = re.compile(r"^\s*$|^your[-_]|[-_]here$|^change[-_]?me", re.I)


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def main() -> int:
    server: dict[str, Path] = {}   # 값 -> 어느 파일에서 나왔나
    client: dict[str, Path] = {}

    for path in sorted(ROOT.rglob(".env*")):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue
        if not path.is_file():
            continue
        env = read_env(path)
        for key, bucket in ((SERVER_KEY, server), (CLIENT_KEY, client)):
            val = env.get(key)
            if val and not PLACEHOLDER.match(val):
                bucket.setdefault(val, path)

    shared = set(server) & set(client)
    if not shared:
        return 0

    print("FAIL: 서버 키와 클라이언트 키가 같은 값입니다 (D-003 위반)", file=sys.stderr)
    for val in sorted(shared):
        # 값 자체는 출력하지 않는다 — 로그가 다음 유출 경로가 된다.
        print(
            f"  {SERVER_KEY} ({server[val].relative_to(ROOT)}) "
            f"== {CLIENT_KEY} ({client[val].relative_to(ROOT)})  "
            f"[길이 {len(val)}, 앞 4자 {val[:4]}…]",
            file=sys.stderr,
        )
    print(
        "\n  클라이언트 키는 브라우저 번들에 실려 공개된 것으로 간주한다.\n"
        "  서버 키와 반드시 다른 값으로 발급하고, 클라이언트 키에는\n"
        "  권한 최소화 + Referer/도메인 제한을 건다. (W0-1b / W0-5)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
