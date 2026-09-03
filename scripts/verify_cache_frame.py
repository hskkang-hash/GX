#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""**상태·가용성을 말하는 응답은 캐시를 지나지 않는다** (P-19).

    "응답 캐시 대상 라우트 목록 실측 → 상태·가용성을 말하는 것(health ·
     object_store_alive · media-data availability · 연계 상태 · 자격증명 상태)은
     캐시 우회 목록으로." — 세종 2026-09-20 §3 A3

왜 이 판정기가 따로 있는가 — **액자는 사진이 언제 찍혔는지 말하지 않는다**
---------------------------------------------------------------------------
`UniversalCacheMiddleware` 는 적중한 본문을 **언제나 `JsonResponse(200)`** 으로
다시 만든다. 그래서 바깥에서 죽은 것(저장소·외부 API·연계)이 **살아 있을 때 담긴
200 으로 계속 말한다.** 이것은 성능 설정이 아니라 **판정의 문제**다: 상태를 묻는
질문에 과거의 답을 주면, 그 답은 틀린 것이 아니라 **질문에 답한 것이 아니다.**

이 규칙은 09-19 에 한 번 사람의 눈으로 지켜졌다(D-412 · media-data). 사람의 눈은
다음 라우트에서 다시 필요하고, 그때 거기 없다. 그래서 도구로 옮긴다.

★ **출생 표본** (D-310) — 이 도구를 만들게 한 것은 **쉼표 하나**다.
   [실측 2026-09-20] `BYPASS_PATTERNS` 안에서

       'video-analysis','media-data'        ← 여기 쉼표가 없다
       # ============ TASK STATUS ============
       'task-status', 'upload-status', ...

   두 리터럴이 파이썬의 **암묵 이어붙이기**로 하나가 되어 있었다:

       'media-datatask-status'               ← 아무 경로에도 안 맞는다

   `'task-status'` 패턴은 **목록에 적혀 있는데 존재하지 않았다.** 사람이 목록을 읽으면
   있고, 정규식이 읽으면 없다. 게이트가 「등재됐다」로 세던 자리이고,
   `/api/task-status/...` 는 그동안 조용히 캐시되고 있었다.

   이 모양은 눈으로 못 잡는다 — **토큰 수와 원소 수를 견주면** 잡힌다. 판정 ②가 그것이다.

무엇을 보는가 — 셋이다
----------------------
  ① **상태·가용성 자리가 캐시 밖인가** (`STATE_SURFACES` · 이름으로 못 박는다)
  ② **이어 붙은 리터럴이 0건인가** (tokenize STRING 수 == AST 원소 수)
  ③ [입력] 캐시 등록부 전수 중 몇이 캐시 안/밖인가 — 0건이 아니라 **모수를 낸다**(D-301)

    python scripts/verify_cache_frame.py            # 판정
    python scripts/verify_cache_frame.py --list     # 등록부 경로별 캐시 안/밖
    python scripts/verify_cache_frame.py --self-test

종료 코드: 0 쟀고 통과 · 1 쟀고 실패 · 2 **못 쟀다**(파일·상수를 못 찾음)

호스트에서 돈다 — Django 가 필요 없다. 파일을 읽는다.
"""
from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPT = ROOT / "backend" / "common" / "universal_optimization.py"
REG = ROOT / "backend" / "common" / "cache_hint_registry.py"

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

#: ★ **상태·가용성을 말하는 자리.** 이름으로 못 박는다 — 규칙으로 적으면 다음 사람이
#:   「이 라우트는 상태인가」를 매번 다시 판단하고, 판단은 매번 달라진다.
#:   각 줄은 (경로 조각, **왜 상태인가**). 사유가 빈 줄은 이 판정기가 거절한다.
STATE_SURFACES: dict[str, str] = {
    "/health":
        "프로세스가 사는가 — 지난번에 살았다는 답은 이 질문의 답이 아니다",
    "/api/media-data/":
        "저장소 가용성(D-412). 목록의 진실은 우리 DB 가 아니라 **MinIO 가 사는가**에 "
        "달려 있고, 그 사실에는 무효화 신호가 없다",
    "/api/dsm/dashboard/link-state":
        "연계 상태 — 외부 연계가 지금 붙어 있는가. 끊긴 뒤에도 붙어 있다고 말하면 "
        "그것이 가장 나쁜 실패다",
    "/api/dsm/events":
        "재난 경보 목록. 캐시가 새 이벤트를 늦추면 **경보가 늦는다** — 이 도메인에서 "
        "늦은 참은 거짓과 같은 값이다",
    "/api/third-api/api-key-management": "자격증명 상태 — 회전·폐기한 **inbound** 키가 "
        "캐시 안에서 계속 유효해 보이면 안 된다. 들어오는 키(남이 우리를 부름)와 "
        "나가는 키는 다른 것이다 (D-337)",
    "/api/task-status/task-status":
        "작업 진행 상태. ★ 이 자리가 **출생 표본**이다 — 쉼표 하나가 이 패턴을 "
        "삼켜서, 목록에 적혀 있는 채로 캐시되고 있었다",
    "/api/stream-monitors/stream-monitors":
        "카메라 감시 상태 — 죽은 카메라를 살아 있다고 말하는 자리(평상 운영 ①)",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _bypass_patterns(src: str) -> list[str] | None:
    """`BYPASS_PATTERNS` 의 **실제 원소**(암묵 이어붙이기가 끝난 뒤의 값)."""
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "BYPASS_PATTERNS" for t in node.targets):
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                return None
            out = []
            for elt in node.value.elts:
                if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                    return None
                out.append(elt.value)
            return out
    return None


def _bypass_span(src: str) -> tuple[int, int] | None:
    """`BYPASS_PATTERNS` 리스트가 차지하는 줄 범위 (1-기반, 양끝 포함)."""
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "BYPASS_PATTERNS" for t in node.targets):
            return node.value.lineno, (node.value.end_lineno or node.value.lineno)
    return None


def glued_literals(src: str) -> list[tuple[int, str]]:
    """★ 판정 ② — **이어 붙은 리터럴**을 찾는다.

    원리: 파이썬은 `'a' 'b'` 를 컴파일 시각에 `'ab'` 로 만든다. AST 는 그것을
    **원소 하나**로 보고, 토크나이저는 **STRING 토큰 둘**로 본다. 두 수가 어긋나는
    자리가 곧 쉼표가 빠진 자리다.

    되돌려 주는 것: [(줄번호, 이어 붙은 값)] — 사람이 그 줄로 바로 갈 수 있게.
    """
    span = _bypass_span(src)
    values = _bypass_patterns(src)
    if span is None or values is None:
        return []
    lo, hi = span
    # 리스트 범위 안의 STRING 토큰을 **줄 순서대로** 모은다.
    toks: list[tuple[int, str]] = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.STRING and lo <= tok.start[0] <= hi:
            try:
                toks.append((tok.start[0], ast.literal_eval(tok.string)))
            except (ValueError, SyntaxError):
                return []
    if len(toks) == len(values):
        return []
    # 어긋났다 — 어느 원소가 몇 개의 토큰을 삼켰는지 앞에서부터 맞춰 본다.
    glued: list[tuple[int, str]] = []
    i = 0
    for value in values:
        acc, first_line, n = "", toks[i][0] if i < len(toks) else 0, 0
        while i < len(toks) and acc != value:
            acc += toks[i][1]
            i += 1
            n += 1
        if n > 1:
            glued.append((first_line, value))
    return glued


def is_cached(path: str, patterns: list[str]) -> bool:
    """그 경로가 **캐시를 지나는가.** `should_cache_request` 의 경로 판정만 옮긴 것.

    ★ 등록부(`PATH_HINT_REGISTRY`)까지 보지 않는 이유: 등록되지 않아 캐시를 안 타는
      것은 **우연**이지 규칙이 아니다. 등록부에 이름 하나가 늘면 그날부터 캐시된다.
      P-19 가 요구하는 것은 「지금 안 탄다」가 아니라 「**앞으로도 안 탄다**」이다.
    """
    low = path.lower()
    if "surveillance-dashboard" in low and "today-profiles-polygon" not in low:
        return False
    if not patterns:
        return True
    rx = re.compile("|".join(re.escape(p) for p in patterns), re.IGNORECASE)
    return not rx.search(low)


def registry_paths(src: str) -> list[str]:
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "PATH_HINT_REGISTRY":
            value = node.value
        elif isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "PATH_HINT_REGISTRY" for t in node.targets):
            value = node.value
        else:
            continue
        if not isinstance(value, ast.Dict):
            return []
        return [k.value for k in value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)]
    return []


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277 · D-300) — **이 판정기도 아무것도 안 보고 통과를 말할 수 있다**
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    ok = True

    #: ★ 첫 갈래가 이 도구의 **출생 표본**이다 — 그날 실제로 있던 모양 그대로.
    birth = (
        "BYPASS_PATTERNS = [\n"
        "    'media-data',\n"
        "    'video-analysis','media-data'\n"
        "\n"
        "    # comment\n"
        "    'task-status', 'upload-status',\n"
        "]\n"
    )
    good = (
        "BYPASS_PATTERNS = [\n"
        "    'media-data',\n"
        "    'video-analysis',\n"
        "    'task-status', 'upload-status',\n"
        "]\n"
    )
    cases = [
        ("★ 출생 표본 — 쉼표가 빠져 두 리터럴이 하나가 된 자리", birth, 1),
        ("쉼표가 다 있는 목록", good, 0),
    ]
    for label, src, want in cases:
        got = len(glued_literals(src))
        mark = "  " if got == want else "✗ "
        print(f"[CACHEFRAME] {mark}{label} — 이어붙임 {got}건 (기대 {want})")
        ok &= got == want

    # 캐시 안/밖 판정이 **양쪽으로** 도는가 — 한쪽만 맞으면 상수 반환과 구별되지 않는다
    pats = ["/health", "media-data"]
    for path, want_cached in (("/api/media-data/", False),
                              ("/health", False),
                              ("/api/orders/order", True)):
        got = is_cached(path, pats)
        mark = "  " if got == want_cached else "✗ "
        print(f"[CACHEFRAME] {mark}{path} — 캐시 {'안' if got else '밖'} (기대 "
              f"{'안' if want_cached else '밖'})")
        ok &= got == want_cached

    # 사유 없는 등재를 거절하는가
    empty = [p for p, why in STATE_SURFACES.items() if len((why or "").strip()) < 10]
    if empty:
        print(f"[CACHEFRAME] ✗ 사유가 빈 상태 자리: {empty}")
        ok = False

    print(f"[CACHEFRAME] 자기시험 {'통과' if ok else '실패'} (출생 표본 포함)")
    return EXIT_OK if ok else EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser(description="상태·가용성 응답은 캐시를 지나지 않는다 (P-19)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if self_test() != EXIT_OK:
        print("[CACHEFRAME] **자기시험이 실패했다** — 판정을 내지 않는다")
        return EXIT_FAIL

    if not (OPT.exists() and REG.exists()):
        print(f"[CACHEFRAME] 소스를 못 찾았다: {OPT} · {REG} — **판정 불가**")
        return EXIT_UNDECIDABLE

    opt_src, reg_src = _read(OPT), _read(REG)
    patterns = _bypass_patterns(opt_src)
    if not patterns:
        print("[CACHEFRAME] `BYPASS_PATTERNS` 를 못 읽었다 — **판정 불가** (D-301)")
        return EXIT_UNDECIDABLE
    paths = registry_paths(reg_src)
    if not paths:
        print("[CACHEFRAME] `PATH_HINT_REGISTRY` 를 못 읽었다 — **판정 불가**")
        return EXIT_UNDECIDABLE

    rc = EXIT_OK

    # ── ③ 모수 먼저 ────────────────────────────────────────────────────────
    cached = [p for p in paths if is_cached("/api/" + p, patterns)]
    print(f"[CACHEFRAME] [입력] {len(patterns)}건 — 캐시 우회 패턴")
    print(f"[CACHEFRAME] [입력] {len(paths)}건 — 캐시 등록부 경로 "
          f"(캐시 안 {len(cached)} · 캐시 밖 {len(paths) - len(cached)})")
    print(f"[CACHEFRAME] [입력] {len(STATE_SURFACES)}건 — 상태·가용성으로 못 박은 자리")

    if args.list:
        for p in paths:
            inside = is_cached("/api/" + p, patterns)
            print(f"[CACHEFRAME]   {'안 ' if inside else '밖 '} /api/{p}")

    # ── ② 이어 붙은 리터럴 ─────────────────────────────────────────────────
    glued = glued_literals(opt_src)
    if glued:
        rc = EXIT_FAIL
        for line, value in glued:
            print(f"[CACHEFRAME] ✗ {OPT.name}:{line} — 쉼표가 빠져 리터럴이 붙었다: "
                  f"{value!r}")
        print("[CACHEFRAME]   목록에 적혀 있는데 **존재하지 않는 패턴**이다. "
              "사람이 읽으면 있고 정규식이 읽으면 없다")
    else:
        print(f"[CACHEFRAME]   이어 붙은 리터럴 0건 (원소 {len(patterns)}건 전수 대조)")

    # ── ① 상태·가용성 자리가 캐시 밖인가 ───────────────────────────────────
    for path, why in STATE_SURFACES.items():
        if is_cached(path, patterns):
            rc = EXIT_FAIL
            print(f"[CACHEFRAME] ✗ {path} — **캐시를 지난다.** {why}")
            print(f"[CACHEFRAME]   고치는 법: `BYPASS_PATTERNS` 에 이 경로를 가리키는 "
                  f"조각을 넣는다 (universal_optimization.py)")
    if rc == EXIT_OK:
        print(f"[CACHEFRAME] 통과 — 상태·가용성 {len(STATE_SURFACES)}자리 전부 캐시 밖 · "
              f"이어 붙은 리터럴 0건")
    return rc


if __name__ == "__main__":
    sys.exit(main())
