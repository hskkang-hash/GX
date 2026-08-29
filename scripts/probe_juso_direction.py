#!/usr/bin/env python
"""juso.go.kr 이 **좌표 → 도로명주소(역방향)** 를 주는가 — 실호출 1회로 판정한다 (D-318).

왜 이것이 가장 값싸고 파급이 큰 한 걸음인가
--------------------------------------------
juso.go.kr 주소정보 연계서비스의 주력은 「검색어 → 도로명주소」와 「주소 → 좌표」다.
FX-5 가 필요한 것은 **그 반대 방향**(좌표 → 도로명주소, 역지오코딩)이다.
**역방향을 안 주면 키가 와도 FX-5 는 열리지 않는다** — 그때는 어댑터 설계가 아니라
**자원 선택**의 문제이고, 그 선택은 개발이 판정할 것이 아니다(D-318 ㉡).

호출 1회 · 30분 · 결과에 따라 FX-5 전체 설계가 갈린다. **빨리 알수록 좋은 것**의 전형이다.

    set GX_JUSO_API_KEY=...                    # 셸 환경변수. 저장소·문서에서 읽지 않는다
    python scripts/probe_juso_direction.py     # 실호출 1회 + 증거 기록
    python scripts/probe_juso_direction.py --dry-run   # 부르지 않고 무엇을 부를지만 본다

판정 셋 중 하나만 낸다 (D-318 ③)
---------------------------------
    ㉠ yes      역방향 지원 — 응답에서 도로명주소 필드를 실제로 받았다
    ㉡ no       정방향만 — 역방향 호출이 거부되거나 주소가 안 온다
    ㉢ unknown  판정 불가 — 키가 없거나 권한·승인 대기. **그 사실 자체를 사유로 적는다**

★ 이 스크립트는 **어댑터가 아니다** (D-298 · D-280)
---------------------------------------------------
아무것도 저장하지 않고, 아무 모델도 만들지 않고, 응답 필드 이름을 코드에 박지 않는다.
한 번 부르고, **본 것을 적고**, 끝난다. 응답을 보기 전에 어댑터를 만들지 않는다 —
그 금지는 키가 온 뒤에도 유효하다.

★ 키 취급 (D-319 · D-204)
--------------------------
  · 키는 **환경변수에서만** 읽는다. 인자로도 받지 않고 저장소 파일에서도 읽지 않는다.
  · 증거에 남기는 요청 URL 은 **키를 마스킹**한다. `docs/agent/evidence/` 는 커밋된다.
  · 응답 본문에 키가 되비쳐 나오는 경우까지 마스킹한다 — 일부 포털 API 가 그렇게 한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "D-318"
ENV_EXAMPLE = ROOT / "backend" / ".env.example"

#: 키가 사는 환경변수 이름. **값이 아니라 이름이다.**
KEY_ENV = "GX_JUSO_API_KEY"

#: 타임아웃 — 외부 호출에 기본값을 맡기지 않는다 (C-3.3).
TIMEOUT = 10.0

#: 시험해 볼 좌표. 안양천 보행교 부근 — 계약 현장이다.
#: ★ 이 값은 **질의이지 기대값이 아니다.** 어떤 주소가 나와야 한다고 적지 않는다(D-280).
PROBE_LAT, PROBE_LNG = 37.3943, 126.9568

#: 응답에서 **도로명주소로 보이는 것**을 찾을 때 쓰는 낱말. 필드 이름을 코드에 박는 것이
#: 아니라, 받은 응답 안에 그런 이름이 **있는지 세는** 용도다 — 판정을 위한 술어이지 계약이 아니다.
ROAD_ADDRESS_HINTS = ("roadAddr", "roadAddress", "road_addr", "도로명")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def endpoint() -> str:
    """`.env.example` 에 **실측으로 등재된** URL 을 읽는다. 여기서 새로 만들지 않는다."""
    if not ENV_EXAMPLE.is_file():
        return ""
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("JUSO_API_URL="):
            return line.split("=", 1)[1].split("#", 1)[0].strip()
    return ""


def mask(text: str, secret: str) -> str:
    if not secret:
        return text
    out = text.replace(secret, "***MASKED***")
    return out.replace(urllib.parse.quote(secret, safe=""), "***MASKED***")


def call(url: str, params: dict, key: str) -> tuple[int, str]:
    query = urllib.parse.urlencode({**params, "confmKey": key})
    full = f"{url}?{query}"
    req = urllib.request.Request(full, headers={"User-Agent": "GuardianX-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")
    except Exception as exc:                 # noqa: BLE001 — 사유를 그대로 적는다
        return 0, f"{type(exc).__name__}: {mask(str(exc), key)}"


def judge(status: int, body: str) -> tuple[str, str]:
    """(판정, 사유). **추정으로 채우지 않는다** — 본 것만 적는다."""
    if status == 0:
        return "unknown", f"호출 자체가 실패했다 — {body[:200]}"
    if status != 200:
        return "unknown", f"HTTP {status} — 권한·승인 대기이거나 잘못된 엔드포인트다"
    hits = [h for h in ROAD_ADDRESS_HINTS if h in body]
    if hits:
        return "yes", f"응답에 도로명주소로 보이는 필드가 있다: {hits}"
    return "no", ("200 이지만 응답에 도로명주소 필드가 없다 — 이 엔드포인트는 "
                  "역방향(좌표→주소)을 주지 않는 것으로 보인다")


def write_evidence(url: str, params: dict, status: int, body: str,
                   verdict: str, why: str, key: str) -> Path:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    path = EVIDENCE / "juso_reverse_probe.md"
    path.write_text(
        f"# juso.go.kr 역방향(좌표 → 도로명주소) 실측 — D-318\n\n"
        f"**실행** {date.today().isoformat()} · **판정** `{verdict}`\n\n"
        f"## 사유\n\n{why}\n\n"
        f"## 요청 (키 마스킹)\n\n```\n{mask(url, key)}\n"
        f"params={json.dumps(params, ensure_ascii=False)}\nconfmKey=***MASKED***\n```\n\n"
        f"## 응답\n\n```\nHTTP {status}\n{mask(body, key)[:4000]}\n```\n\n"
        f"★ 이 문서는 **본 것만** 적는다. 응답 필드 이름을 어댑터에 옮기는 일은 "
        f"판정이 `yes` 일 때 별건으로 한다 (D-298 · D-280).\n",
        encoding="utf-8")
    return path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    url = endpoint()
    print(f"[JUSO] 엔드포인트: {url or '(없음)'}")
    print(f"[JUSO] 키 환경변수: {KEY_ENV}")

    if not url:
        print("[JUSO] 판정 unknown — .env.example 에 JUSO_API_URL 이 없다")
        return 1

    params = {"resultType": "json", "x": PROBE_LNG, "y": PROBE_LAT}
    if args.dry_run:
        print(f"[JUSO] (dry-run) 부를 것: {url} params={params} + confmKey=<환경변수>")
        return 0

    key = os.environ.get(KEY_ENV, "").strip()
    if not key:
        # ★ ㉢ 판정 불가. **추정으로 채우지 않는다** — 키가 없다는 사실이 곧 사유다.
        print(f"[JUSO] 판정 **unknown** — {KEY_ENV} 가 이 환경에 없다.\n"
              f"       키를 환경변수에 넣고 다시 돌리면 1회 호출로 판정된다.\n"
              f"       (키 값을 저장소·문서·시험 어디에도 적지 않는다 · D-319)")
        return 2                            # 2 = 판정 불가. 실패(1)와 구별한다 (D-301)

    status, body = call(url, params, key)
    verdict, why = judge(status, body)
    path = write_evidence(url, params, status, body, verdict, why, key)
    print(f"[JUSO] HTTP {status} · 판정 **{verdict}** — {why}")
    print(f"[JUSO] 증거: {path.relative_to(ROOT)}")
    print(f"[JUSO] 다음: stream_monitors 가 아니라 adapters/juso/__init__.py 의 "
          f"JUSO_REVERSE_SUPPORTED 를 '{verdict}' 로 올리고, "
          f"yes 이면 스키마 스냅샷 시험을 붙인다")
    return 0 if verdict == "yes" else 2


if __name__ == "__main__":
    sys.exit(main())
