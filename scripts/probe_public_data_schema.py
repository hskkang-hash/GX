#!/usr/bin/env python
"""공공 데이터 API 응답 스키마 **실측** — 읽기 전용 (D-280 DA-05 확장).

무엇을 하나
-----------
`docs/agent/evidence/DA-05/sources.yaml` 의 원천을 **읽기 전용으로 한 번씩** 부르고,
실제 응답에서 필드 트리·rate limit·오류 코드를 뽑아
`docs/agent/evidence/DA-05/{source}_schema.md` 로 남긴다.

왜 지금 하나 — 코드는 2027.2 인데
---------------------------------
D-280:

    코드 구현은 여전히 2027.2 다(계약 M 기능 우선 · PRD v2.1 규칙②).
    다만 키가 생겼으므로 **읽기 전용 실호출로 응답 스키마를 실측**해 DA-05 스펙에 박아라.
    **추정으로 쓴 스펙은 2027.2 에 전부 재작업이 된다** — 지금 30분이 그때 며칠을 아낀다.

그래서 이 스크립트는 **어댑터가 아니다.** 아무것도 저장하지 않고, 아무 모델도 만들지 않는다.
한 번 부르고, 본 것을 적고, 끝난다.

★ 추정을 스펙에 박지 않는다
---------------------------
키가 없거나 엔드포인트가 미상이면 **문서를 쓰지 않는다.** 무엇이 없어서 못 썼는지만 적는다.
추정으로 채운 스펙은 2027.2 에 재작업이 되고, 그때는 그것이 추정이었다는 사실조차 남지 않는다.
`sources.yaml` 의 `verified: false` 를 참으로 바꾸는 것은 **이 스크립트의 실측뿐**이다.

★ 키 취급 (D-280 · D-204)
-------------------------
  · 키는 **환경변수에서만** 읽는다. 인자로도 받지 않고 저장소 파일에서도 읽지 않는다.
  · 요청 URL 을 출력할 때 키를 마스킹한다.
  · **응답 본문에 키가 섞여 나오는 경우까지** 마스킹한다 (일부 포털 API 는 요청을 그대로 되비춘다).
    지시가 특별히 못박은 부분이다.
  · 실패해도 예외 메시지에 키가 실리지 않게 URL 을 마스킹한 뒤 재발생시킨다.

사용법
------
    set GX_DATA_GO_KR_KEY=...        # 셸 환경변수. 저장소·vault 파일에서 읽지 않는다
    python scripts/probe_public_data_schema.py            # 전 원천
    python scripts/probe_public_data_schema.py --only kma_warning
    python scripts/probe_public_data_schema.py --dry-run  # 부르지 않고 무엇을 부를지만 본다
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
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "DA-05"
SOURCES = EVIDENCE / "sources.yaml"

#: 외부 호출에 타임아웃 없는 것을 금지한다 (W0-17 · C-3.3). 스크립트도 예외가 아니다 —
#: 타임아웃 없는 호출 하나가 늦으면 그것을 기다리는 사람이 선다.
TIMEOUT = 10

#: 한 원천당 한 번만 부른다. 실측이 목적이지 수집이 목적이 아니다.
#: rate limit 은 응답 헤더·오류에서 읽고, **부딪혀서** 알아내지 않는다.
MAX_CALLS_PER_SOURCE = 1

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def mask(text: str, secrets: list[str]) -> str:
    """키가 어디에 섞여 있든 지운다 — URL·본문·예외 메시지 전부."""
    out = text
    for s in secrets:
        if not s:
            continue
        for form in {s, urllib.parse.quote(s, safe=""), urllib.parse.unquote(s)}:
            if form:
                out = out.replace(form, "***KEY_MASKED***")
    return out


def field_tree(node: Any, prefix: str = "", depth: int = 0, out: list[str] | None = None) -> list[str]:
    """응답에서 **필드 트리만** 뽑는다. 값은 타입과 예시 한 조각만 남긴다.

    값을 통째로 남기지 않는 이유가 둘이다:
      · 키가 되비쳐 나올 수 있다 (마스킹으로도 막지만 애초에 안 싣는 것이 낫다).
      · 스펙에 필요한 것은 **모양**이지 그날의 값이 아니다.
    """
    out = [] if out is None else out
    if depth > 6:
        return out
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)):
                out.append(f"{here}  ({type(v).__name__})")
                field_tree(v, here, depth + 1, out)
            else:
                sample = str(v)
                if len(sample) > 40:
                    sample = sample[:40] + "…"
                out.append(f"{here}  ({type(v).__name__}) = {sample}")
    elif isinstance(node, list):
        if node:
            field_tree(node[0], f"{prefix}[]", depth + 1, out)
        else:
            out.append(f"{prefix}[]  (빈 배열 — 이 호출로는 원소 모양을 못 봤다)")
    return out


def call(url: str, params: dict, key: str) -> tuple[int, dict, str]:
    """읽기 전용 GET 한 번. `(status, headers, body)`. 키는 예외에도 안 실린다."""
    q = dict(params)
    q["serviceKey"] = key
    full = f"{url}?{urllib.parse.urlencode(q, safe='%')}"
    req = urllib.request.Request(full, headers={"User-Agent": "GuardianX-DA05-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        # 오류 응답도 **스펙의 일부**다 (D-280 이 "오류 코드"를 산출물로 요구했다).
        return exc.code, dict(exc.headers or {}), exc.read().decode("utf-8", "replace")
    except Exception as exc:
        raise RuntimeError(mask(f"{type(exc).__name__}: {exc}", [key])) from None


def render(src: dict, status: int, headers: dict, body: str, key: str) -> str:
    safe_body = mask(body, [key])
    try:
        parsed = json.loads(safe_body)
        fields = field_tree(parsed)
        shape = "JSON"
    except json.JSONDecodeError:
        parsed = None
        fields = []
        shape = "XML 또는 비-JSON"

    rate = {k: v for k, v in headers.items()
            if any(w in k.lower() for w in ("rate", "limit", "quota", "retry"))}

    lines = [
        f"# DA-05 응답 스키마 실측 — {src['title']} (`{src['id']}`)",
        "",
        f"**측정** {date.today().isoformat()} · **결정** D-280 · **호출** 읽기 전용 1회",
        f"**우선순위** {src['priority']} · **쓰임** {src['why']}",
        "",
        "> 이 문서는 **실측이다.** 문서를 보고 적은 것이 아니라 실제 응답에서 뽑았다.",
        "> 코드 구현은 여전히 2027.2 다 — 지금 박아 두는 것은 **스펙**이지 어댑터가 아니다.",
        "",
        "---",
        "",
        "## 1. 요청",
        "",
        "```",
        f"GET {src['endpoint']}",
        f"    ?{urllib.parse.urlencode(src.get('params') or {})}&serviceKey=***KEY_MASKED***",
        f"키 환경변수: {src['key_env']}   (값은 저장소·이 문서 어디에도 없다 — D-204)",
        f"타임아웃: {TIMEOUT}s   (W0-17 · C-3.3 — 타임아웃 없는 외부 호출 금지)",
        "```",
        "",
        "## 2. 응답",
        "",
        f"- HTTP 상태: **{status}**",
        f"- 본문 형식: **{shape}**",
        f"- Content-Type: `{headers.get('Content-Type', '(없음)')}`",
        "",
        "### 필드 트리",
        "",
        "```",
        *(fields or ["(파싱 불가 — 아래 원문 앞부분 참조)"]),
        "```",
        "",
        "### 본문 앞부분 (키 마스킹 적용)",
        "",
        "```",
        safe_body[:1200] + ("…" if len(safe_body) > 1200 else ""),
        "```",
        "",
        "## 3. rate limit",
        "",
    ]
    if rate:
        lines += ["```", *(f"{k}: {v}" for k, v in rate.items()), "```"]
    else:
        lines += [
            "응답 헤더에 rate limit 정보가 **없다.** 공공데이터포털은 헤더가 아니라",
            "**일일 트래픽 초과 시 오류 코드**(`22` LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR)로",
            "알린다. 즉 한도는 **부딪혀야 보이는 값**이므로 여기 적지 않는다 —",
            "포털 마이페이지의 신청 내역이 정본이다. 추정치를 스펙에 박지 않는다.",
        ]
    lines += [
        "",
        "## 4. 오류 코드",
        "",
        "이 호출에서 실제로 본 것만 적는다. 문서의 전체 목록을 옮겨 적지 않는다 —",
        "옮겨 적은 목록은 실측과 구별되지 않고, 구별되지 않으면 다음 사람이 그것을 믿는다.",
        "",
        f"- 이번 호출: HTTP {status}" + ("  (정상)" if status == 200 else "  ← **오류 응답의 모양이 위 §2 에 실측돼 있다**"),
        "",
        "## 5. 아직 모르는 것",
        "",
        "- 페이지네이션 상한, 동시 호출 허용치 — 이 1회 호출로는 안 보인다.",
        "- 응답 지연의 분포 — 1회 측정으로는 못 말한다.",
        "- 필드의 **누락 가능성** — 이번 응답에 있던 필드가 항상 있다는 보장은 없다.",
        "  2027.2 구현 시 어댑터는 **모든 필드를 optional 로** 시작해야 한다.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="원천 하나만")
    ap.add_argument("--dry-run", action="store_true", help="부르지 않고 계획만 본다")
    args = ap.parse_args()

    doc = yaml.safe_load(SOURCES.read_text(encoding="utf-8"))
    sources = [s for s in doc["sources"] if not args.only or s["id"] == args.only]

    print("[DA05] 공공 데이터 응답 스키마 실측 (D-280) — 읽기 전용")
    print(f"[DA05] 대상 {len(sources)}종 / 등록 {len(doc['sources'])}종")

    measured, skipped = [], []
    for src in sources:
        sid = src["id"]
        key = os.environ.get(src["key_env"], "")
        if not src.get("endpoint"):
            skipped.append((sid, f"엔드포인트 미상 — {src['endpoint_source'].strip().splitlines()[0]}"))
            continue
        if not key:
            skipped.append((sid, f"환경변수 {src['key_env']} 가 비어 있다 — "
                                 f"키는 C:\\GuardianX-vault\\ → 환경변수로만 (D-280)"))
            continue
        if args.dry_run:
            print(f"  [계획] {sid} → GET {src['endpoint']} (키 있음)")
            continue

        print(f"  [호출] {sid} → {src['endpoint']}")
        try:
            status, headers, body = call(src["endpoint"], src.get("params") or {}, key)
        except RuntimeError as exc:
            skipped.append((sid, f"호출 실패: {exc}"))
            continue

        out = EVIDENCE / f"{sid}_schema.md"
        tmp = out.with_suffix(".tmp")
        tmp.write_text(render(src, status, headers, body, key), encoding="utf-8")
        os.replace(tmp, out)            # D-270 ① 원자 교체
        measured.append((sid, status, out))
        print(f"         HTTP {status} → {out.relative_to(ROOT).as_posix()}")

    print()
    print(f"[DA05] 실측 {len(measured)}종 · 못 잰 것 {len(skipped)}종")
    for sid, why in skipped:
        print(f"  · {sid}: {why}")
    if skipped:
        print()
        print("[DA05] ★ 못 잰 것은 **추정으로 채우지 않는다.** 문서를 만들지 않았다 —")
        print("       추정으로 쓴 스펙은 2027.2 에 전부 재작업이 되고, 그때는 그것이")
        print("       추정이었다는 사실조차 남지 않는다 (D-280).")
    # 못 잰 것이 있어도 exit 0 이다. 이 스크립트는 게이트가 아니라 **측정기**다 —
    # 게이트로 만들면 키가 없는 사람의 커밋이 막히고, 그것은 이 일의 목적이 아니다.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
