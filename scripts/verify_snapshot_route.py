#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-25 강제 도구 — **스냅샷 바이트가 나가는 문 하나**를 잰다 (2026-09-24).

왜 이 문을 냈나
---------------
화면은 스냅샷을 이미 그리고 있었다. 없던 것은 그 그림의 **바이트**를 인증 뒤에서
내려 줄 문 하나였다. 그 자리를 서명 URL(무계정 링크)로 메우는 것이 가장 쉬웠고,
그래서 안 했다 — 계정 없이 열리는 링크는 한 번 새면 **회수할 수 없다**.

    스냅샷은 11조가 말하는 원본 영상이 아니다. 정지 이미지 1장이다(DA-01 FR-01-3).
    **저장은 못 막는다. 그래서 출처를 남긴다** — 테넌트명과 열람 시각을 소인으로 찍는다.

보는 것 — 여섯
--------------
  ① **라우트 하나**가 있고 인증(`auth=`)과 테넌트 표식(`@tenant_scoped`)을 함께 단다
  ② **`attachment` 0건 · `inline` 1건** — 주석은 세지 않는다(설명을 지우게 만들지 않는다)
  ③ **캐시 금지 두 겹** — 응답 헤더 `no-store` + 미들웨어 우회 목록의 `dsm/` (P-19)
  ④ **무계정 링크 0건** — 서명 URL·파일 스트리밍 토큰이 라우트와 저장소 읽기 경로에 없다
  ⑤ **규약 넷의 시험이 이름으로 실재한다** — 하나가 지워지면 지워진 것이 보이지 않는다
  ⑥ **소인 실패 시 원본으로 되돌아가지 않는다** — 글꼴이 없으면 던지고, 라우트가 500 을 낸다

★ 왜 HTTP 를 때리지 않나
------------------------
익명 401 · 타 테넌트 404 는 **런타임 사실**이고, 그 둘은 `backend/tests/test_snapshot_route.py`
가 실제 요청으로 잰다(⑤가 그 시험의 실재를 강제한다). 게이트가 매번 서버를 요구하면
서버가 없는 날 게이트는 **회색이 아니라 초록으로** 죽는다 — 이 저장소가 이미 겪은 모양이다.

    python scripts/verify_snapshot_route.py
    python scripts/verify_snapshot_route.py --self-test
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = ROOT / "backend" / "apps" / "dsm" / "api.py"
SERVICES = ROOT / "backend" / "apps" / "dsm" / "services.py"
WATERMARK = ROOT / "backend" / "apps" / "dsm" / "watermark.py"
READER = ROOT / "backend" / "stream_monitors" / "services" / "detection_snapshot.py"
CACHE = ROOT / "backend" / "common" / "universal_optimization.py"
TEST = ROOT / "backend" / "tests" / "test_snapshot_route.py"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

EXIT_OK, EXIT_FAIL, EXIT_UNDECIDABLE = 0, 1, 2

ROUTE_PATH = "/events/{int:event_id}/snapshot"
BLOCK_START = "스냅샷 바이트 (P-25"
BLOCK_END = "F-11 상황 보고서"

#: 원본을 통째로 흘릴 수 있는 자리. `test_clip_playback` 의 규약 ④와 **같은 목록**이다 —
#: 스냅샷 문이 그 목록의 예외가 되면 11조의 구멍은 이름만 바뀐 것이다.
LEAK_TOKENS = ("presigned", "presigned_get_object", "get_presigned_url",
               "FileResponse", "StreamingHttpResponse", "X-Accel-Redirect")

#: 규약 넷의 시험 이름. `test_snapshot_route.REQUIRED_RULES` 와 **같아야 한다**.
REQUIRED_RULES = (
    "test_rule1_anonymous_gets_401",
    "test_rule2_another_tenant_gets_404",
    "test_rule3_bytes_carry_a_stamp",
    "test_rule4_inline_not_attachment",
)


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 순수 함수로 둔다
# ═══════════════════════════════════════════════════════════════════════════

def code_only(text: str) -> str:
    """주석 줄을 뺀 원문. **주석은 왜 안 쓰는지를 적는 자리**이고, 그것까지 세면
    설명을 지워야 초록이 나는 시험이 된다 (D-327 의 이웃)."""
    return "\n".join(line for line in text.splitlines()
                     if not line.strip().startswith("#"))


def route_block(api_src: str) -> str:
    """스냅샷 라우트의 원문 조각. 표지가 없으면 빈 문자열 — **판정은 부르는 쪽이 한다.**"""
    try:
        return api_src[api_src.index(BLOCK_START):api_src.index(BLOCK_END)]
    except ValueError:
        return ""


def judge_route(api_src: str) -> list[str]:
    """라우트 원문 하나를 판정한다. 어긋난 것들을 돌려준다."""
    bad: list[str] = []
    block = route_block(api_src)
    if not block:
        return [f"스냅샷 라우트 조각을 못 찾았다 — 표지 «{BLOCK_START}» 가 없다"]

    code = code_only(block)
    if ROUTE_PATH not in code:
        bad.append(f"라우트 경로 «{ROUTE_PATH}» 가 없다")
    if "auth=" not in code:
        bad.append("라우트에 `auth=` 가 없다 — 인증 없는 바이트 문이다")
    if "@tenant_scoped" not in code:
        bad.append("라우트에 `@tenant_scoped` 표식이 없다 — 분류를 잊은 것과 "
                   "분류가 필요 없는 것이 구별되지 않는다 (D-272)")
    if "attachment" in code:
        bad.append("라우트 코드에 `attachment` 가 있다 — 「파일로 받으라」는 반출의 모양이다")
    if '"inline"' not in code:
        bad.append('라우트가 `Content-Disposition: "inline"` 을 달지 않는다')
    if "no-store" not in code:
        bad.append("라우트가 `no-store` 를 달지 않는다 — 캐시 금지(P-19)의 첫 겹이 없다")
    for token in LEAK_TOKENS:
        if token in code:
            bad.append(f"라우트에 «{token}» 이 들어왔다 — 무계정 링크·통째 전송의 자리다")
    return bad


def judge_leak(name: str, src: str) -> list[str]:
    """저장소 읽기 경로에 통째 전송의 자리가 없는가."""
    code = code_only(src)
    return [f"{name} 에 «{token}» 이 있다 — 바이트는 우리 라우트로만 나간다"
            for token in LEAK_TOKENS if token in code]


def judge_fail_closed(services_src: str, watermark_src: str) -> list[str]:
    """소인을 못 찍었을 때 **원본으로 되돌아가지 않는가.**

    이 갈래가 이 도구의 출생 표본이다(D-310): 소인 실패에서 원본을 내보내면
    라우트가 준 것은 편의뿐이고 남긴 것은 없다 — 그리고 그것은 **조용하다**.
    """
    bad: list[str] = []
    if "WatermarkFontMissing" not in watermark_src:
        bad.append("글꼴이 없을 때 던지는 자리가 없다 — 소인 없는 이미지가 나갈 수 있다")
    if 'SnapshotUnavailable(\n            "stamp"' not in services_src and \
            '"stamp"' not in services_src:
        bad.append("소인 실패를 따로 부르는 이름이 없다 — 저장소 장애와 한 칸에 눌러앉는다")
    if re.search(r"except[^\n]*:\s*\n\s*return\s+data", services_src):
        bad.append("소인 실패에서 원본(`data`)을 그대로 돌려준다 — **조용한 성공**이다")
    return bad


def judge_tests(test_src: str) -> list[str]:
    return [f"규약 시험 «{name}» 이 없다 — 지워진 시험은 지워진 것이 보이지 않는다"
            for name in REQUIRED_RULES if f"def {name}" not in test_src]


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310)
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    good = (
        "    # ── 스냅샷 바이트 (P-25 · 2026-09-24) ──\n"
        "    # attachment 라는 낱말은 주석에 있어도 된다\n"
        '    @route.get("/events/{int:event_id}/snapshot", auth=JwtOrInboundKey())\n'
        "    @tenant_scoped(reason='스냅샷')\n"
        '    def event_snapshot(self, request, event_id: int):\n'
        '        response["Content-Disposition"] = "inline"\n'
        '        response["Cache-Control"] = "no-store"\n'
        "    # ── F-11 상황 보고서 ──\n")
    checks: list[tuple[str, bool]] = []

    checks.append(("★ 출생표본 — 온전한 라우트는 통과한다", not judge_route(good)))
    checks.append((
        "★ 출생표본 — `attachment` 헤더를 잡는다",
        any("반출의 모양" in p for p in judge_route(
            good.replace('= "inline"', '= "attachment; filename=x.jpg"')))))
    checks.append((
        "주석 속 `attachment` 는 잡지 않는다 — 설명을 지우게 만들지 않는다",
        not judge_route(good)))
    checks.append((
        "인증 없는 라우트를 잡는다",
        any("인증 없는" in p for p in judge_route(
            good.replace(", auth=JwtOrInboundKey()", "")))))
    checks.append((
        "테넌트 표식이 없으면 잡는다",
        any("tenant_scoped" in p for p in judge_route(
            good.replace("    @tenant_scoped(reason='스냅샷')\n", "")))))
    checks.append((
        "캐시 금지가 없으면 잡는다",
        any("no-store" in p for p in judge_route(
            good.replace('"no-store"', '"public, max-age=600"')))))
    checks.append((
        "★ 무계정 링크(서명 URL)가 들어오면 잡는다",
        any("무계정" in p for p in judge_route(
            good.replace("        response[", "        url = presigned(x)\n        response[")))))
    checks.append((
        "표지가 없으면 **회색이 아니라 실패**다 — 잴 것이 없어진 것도 사실이다",
        bool(judge_route("아무것도 없다"))))
    checks.append((
        "★ 출생표본 — 소인 실패에서 원본을 돌려주면 잡는다",
        any("조용한 성공" in p for p in judge_fail_closed(
            'x = 1\n    except Exception:\n        return data\n"stamp"',
            "WatermarkFontMissing"))))
    checks.append((
        "규약 넷 중 하나가 없으면 잡는다",
        len(judge_tests("def test_rule1_anonymous_gets_401(): pass")) == 3))
    checks.append((
        "저장소 읽기 경로의 통째 전송을 잡는다",
        any("우리 라우트로만" in p
            for p in judge_leak("x", "resp = FileResponse(f)"))))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[SNAPSHOT] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return EXIT_FAIL if bad else EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    missing = [p for p in (API, SERVICES, WATERMARK, READER, CACHE, TEST) if not p.exists()]
    if missing:
        # 판정 불가다 — 통과가 아니다 (P-12).
        for path in missing:
            print("[SNAPSHOT] 파일이 없다: %s" % path.relative_to(ROOT))
        print("[SNAPSHOT] 판정 불가 — 잴 파일이 없다 (exit 2)")
        return EXIT_UNDECIDABLE

    api_src = API.read_text(encoding="utf-8")
    services_src = SERVICES.read_text(encoding="utf-8")
    watermark_src = WATERMARK.read_text(encoding="utf-8")
    reader_src = READER.read_text(encoding="utf-8")
    cache_src = CACHE.read_text(encoding="utf-8")
    test_src = TEST.read_text(encoding="utf-8")

    problems: list[str] = []
    problems += judge_route(api_src)
    problems += judge_leak("apps/dsm/services.py", services_src)
    problems += judge_leak("stream_monitors/services/detection_snapshot.py", reader_src)
    problems += judge_fail_closed(services_src, watermark_src)
    problems += judge_tests(test_src)

    # ③의 두 번째 겹 — 미들웨어 우회 목록. 라우트 헤더만으로는 **우리 캐시**를 못 비낀다.
    if "'dsm/'" not in cache_src and '"dsm/"' not in cache_src:
        problems.append("캐시 우회 목록에 `dsm/` 이 없다 — 적중 본문이 200 으로 되살아난다 "
                        "(P-19 · D-412)")

    block = route_block(api_src)
    routes = len(re.findall(r"@route\.get\(", block))
    rules = sum(1 for name in REQUIRED_RULES if f"def {name}" in test_src)
    print("[SNAPSHOT] [입력] 라우트 %d개 · 규약 시험 %d/%d · 누출 토큰 후보 %d종 · "
          "파일 %d개" % (routes, rules, len(REQUIRED_RULES), len(LEAK_TOKENS), 6))

    # 소인 글꼴 — **이 기계의 사실**이다. 앱은 컨테이너에서 돌므로 여기서 못 찾은 것이
    # 곧 결함은 아니다. 그래서 판정에 넣지 않고 [입력] 으로만 적는다.
    sys.path.insert(0, str(ROOT / "backend"))
    fonts = re.findall(r'"(/[^"]+\.(?:ttf|ttc))"|"([A-Z]:/[^"]+\.ttf)"', watermark_src)
    found = [f for pair in fonts for f in pair if f and Path(f).exists()]
    print("[SNAPSHOT] [입력] 소인 글꼴 후보 %d개 · 이 기계에서 찾은 것 %d개%s"
          % (sum(1 for pair in fonts for f in pair if f), len(found),
             (" (%s)" % found[0]) if found else " — 앱은 컨테이너에서 돈다"))

    if problems:
        for p in problems:
            print("[SNAPSHOT] FAIL %s" % p)
        return EXIT_FAIL
    print("[SNAPSHOT] 통과 — 문 하나 · 인증과 테넌트 · 소인 · 다운로드 아님 · 캐시 두 겹")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
