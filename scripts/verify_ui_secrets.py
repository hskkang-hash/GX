#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-27 [P0] — **화면이 우리 서랍을 열어 보여 주는가.** 기밀 노출 폐쇄 판정기.

무엇이 이 판정기를 만들었나 (사고 · 2026-09-25)
-----------------------------------------------
`preset=system` 화면의 「연계 상태」 상자가 관제요원 앞에서 이렇게 말하고 있었다:

    에스비정보기술의 SDN 컨트롤러 API 명세 미수령. 계약 DEV-SBIT-GX-20260810 3조2항이
    정한 제공 기한(착수 15일 내 · 2026-08-25)이 경과했다 …

이것은 정직이 아니라 **누출**이다. 상대사명 · 계약번호 · 조항 · 미이행 사실이
고객 화면에 문단으로 떠 있었다. 화면을 켜 놓은 채 손님이 지나가면 그것으로 끝이다.

뿌리는 하나다 — **사유를 화면에 적으라고 시켰고, 그 사유가 우리 언어였다.**
사유·출처·판정 근거는 관리자 자리와 문서의 자리에 산다. 사용자 본문에는 사용자 언어만.

무엇을 세는가 — 두 면
---------------------
    ① 프런트 **렌더 문자열** (기본)   frontend/src 의 주석을 걷어 낸 소스 전부
    ② **API 응답 본문** (`--api`)     로그인해서 /api/dsm/** 를 실제로 받아 본다

    ★ ①은 병합 게이트다(호스트 · 의존성 없음). ②는 [실측]이고 서버가 있어야 한다 —
      **서버가 없으면 exit 2**(판정 불가)다. 재지 못한 것은 초록이 아니다(D-400).

왜 주석은 세지 않는가
---------------------
`D-421` 도 `kernels.k1_event` 도 **주석에는 있어야 한다.** 코드가 왜 그렇게 생겼는지는
거기서만 전해진다. 금지된 것은 「사용자 본문」이지 「소스」가 아니다(09-25 §7).
그래서 이 판정기는 주석을 **걷어 내고** 본다 — 걷어 내는 일 자체가 자기시험 대상이다
(음성 표본: 주석 안의 `D-347` 하나는 잡히면 **안 된다**).

⚠ 놓치는 쪽으로 틀린다. 서버가 조립해 내려보내는 문자열은 ①이 못 본다 —
  그래서 ②가 따로 있고, 그 둘을 하나의 초록으로 합치지 않는다.

    python scripts/verify_ui_secrets.py              # 판정 (프런트 렌더 문자열)
    python scripts/verify_ui_secrets.py --list       # 걸린 자리 전수
    python scripts/verify_ui_secrets.py --api        # + API 응답 본문 [실측 · 서버 필요]
    python scripts/verify_ui_secrets.py --self-test  # 양성·음성 대조 (D-277)

호스트에서 돈다 — Django 가 필요 없다(--api 는 서버가 필요하다).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 금지 패턴 — 09-25 §1 P-27 이 이름으로 적은 여섯
# ═══════════════════════════════════════════════════════════════════════════
#: 이름을 여기 한 벌만 둔다. 두 벌을 두면 한쪽만 늘어나고, 그 순간 한쪽은 거짓말이 된다.
PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("상대사 코드", r"DEV-SBIT", "계약번호의 접두 — 화면은 상대를 부르지 않는다"),
    ("상대사명", r"에스비정보기술", "상대사명은 화면이 아니라 문서의 자리다"),
    ("계약 조항", r"\d\s*조\s*\d\s*항", "조·항은 계약서에 있다"),
    # `(?!\d)` — 뒤에 숫자가 더 붙으면 그것은 결정 번호가 아니라 **장비 일련번호**다
    # (`D-12345678103`). 없으면 배송 대시보드의 기기 번호가 매번 걸린다 [실측].
    ("결정 번호", r"D-\d{3}(?!\d)", "우리 대장의 이름이다 — 사용자에게는 뜻이 없다"),
    ("탐침 표식", r"WRITE_NO_PROBE", "쓰기 면 선등록 표식 — 개발 대장의 말"),
    ("커널 경로", r"kernels\.", "내부 경로다 — 화면이 우리 폴더 구조를 알려 준다"),
)
COMPILED = tuple((name, re.compile(rx), why) for name, rx, why in PATTERNS)

#: ★ **출생 표본** (D-310) — 그날 화면에 실제로 떠 있던 문단의 첫 줄이다.
#:   이 문자열이 판정기를 통과하면 판정기부터 의심한다.
BIRTH_SAMPLE = (
    "에스비정보기술의 SDN 컨트롤러 API 명세 미수령. "
    "계약 DEV-SBIT-GX-20260810 3조2항이 정한 제공 기한이 경과했다."
)

#: 프런트에서 볼 파일. `.d.ts` 는 타입 선언이라 렌더되지 않는다.
SUFFIXES = (".ts", ".tsx", ".js", ".jsx")
SKIP_DIRS = {"node_modules", "dist", "build", "__generated__", ".vite"}

#: API 면 — `/api/dsm/**` 중 **매개변수 없는** 읽기 라우트. 값이 든 경로는 그 순간의
#: 씨앗을 가리키므로 때리지 않는다(D-347 ④ · 씨앗은 캡처가 끝나며 지워진다).
API_PATHS = (
    "/api/dsm/dashboard/link-state",
    "/api/dsm/dashboard/frame",
    "/api/dsm/events",
    "/api/dsm/settings",
    "/api/dsm/notify/recipients",
)


# ═══════════════════════════════════════════════════════════════════════════
# 주석 걷어내기 — 이 함수가 이 판정기의 심장이다
# ═══════════════════════════════════════════════════════════════════════════
def strip_comments(src: str) -> str:
    """JS/TS 소스에서 주석만 지운다. **문자열 안의 `//` 는 주석이 아니다.**

    지운 자리에 공백을 같은 길이로 채운다 — 그래야 줄 번호와 열이 원본과 같고,
    걸린 자리를 사람이 **파일에서 바로 찾을 수 있다**. 지워서 줄이 밀리면
    「어디」가 틀리고, 어디가 틀린 보고는 고쳐지지 않는다.

    JSX 주석 `{/* … */}` 은 블록 주석이므로 같은 규칙으로 걷힌다.
    """
    out = list(src)
    i, n = 0, len(src)
    quote: str | None = None          # 지금 열려 있는 따옴표 ' " `
    while i < n:
        ch = src[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "'\"`":
            quote = ch
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = src[i + 1]
            if nxt == "/":
                j = src.find("\n", i)
                j = n if j < 0 else j
                for k in range(i, j):
                    out[k] = " "
                i = j
                continue
            if nxt == "*":
                j = src.find("*/", i + 2)
                j = n if j < 0 else j + 2
                for k in range(i, j):
                    if out[k] != "\n":
                        out[k] = " "
                i = j
                continue
        i += 1
    return "".join(out)


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """주석을 걷어 낸 텍스트에서 금지 패턴을 찾는다. `(줄, 패턴이름, 발췌)`."""
    hits: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for name, rx, _why in COMPILED:
            m = rx.search(line)
            if m:
                snippet = line.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "…"
                hits.append((lineno, name, snippet))
    return hits


def frontend_files() -> list[Path]:
    if not FRONTEND.exists():
        return []
    files: list[Path] = []
    for path in FRONTEND.rglob("*"):
        if path.suffix not in SUFFIXES or not path.is_file():
            continue
        if path.name.endswith(".d.ts"):
            continue
        if SKIP_DIRS & set(path.parts):
            continue
        files.append(path)
    return sorted(files)


def scan_frontend() -> tuple[int, list[tuple[Path, int, str, str]]]:
    """`(본 파일 수, 걸린 자리)`."""
    findings: list[tuple[Path, int, str, str]] = []
    files = frontend_files()
    for path in files:
        try:
            src = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, name, snippet in scan_text(strip_comments(src)):
            findings.append((path, lineno, name, snippet))
    return len(files), findings


# ═══════════════════════════════════════════════════════════════════════════
# ② API 응답 본문 — [실측]. 정적 검사가 못 보는 자리다
# ═══════════════════════════════════════════════════════════════════════════
def _walk_strings(node: object, path: str = "$"):
    """JSON 안의 **문자열 필드만** 훑는다 — 키 이름이 아니라 값이 화면에 뜬다."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for idx, v in enumerate(node[:50]):
            yield from _walk_strings(v, f"{path}[{idx}]")


def scan_api() -> tuple[int, list[tuple[str, str, str, str]], str | None]:
    """로그인해서 `/api/dsm/**` 를 받아 본문 문자열을 훑는다.

    돌려주는 것: `(본 라우트 수, 걸린 자리, 못 잰 사유)`.
    **못 잰 것과 0건을 같은 칸에 넣지 않는다** (D-301).

    로그인·두드리기는 `verify_route_alive` 의 것을 **그대로 쓴다** — 두 벌을 두면
    반드시 어긋나고(D-369), 그 파일에는 2026-09-17 의 교훈(401 판독)이 얽혀 있다.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from verify_route_alive import hit, login          # noqa: PLC0415
    except Exception as exc:                                # noqa: BLE001
        return 0, [], f"verify_route_alive 를 못 읽었다: {type(exc).__name__} {exc}"

    api = os.environ.get("GX_API", "").rstrip("/")
    user = os.environ.get("GX_ROUTE_USER", "")
    password = os.environ.get("GX_ROUTE_PASSWORD", "")
    if not api or not user or not password:
        return 0, [], ("자격증명이 없다 — GX_API · GX_ROUTE_USER · GX_ROUTE_PASSWORD "
                       "(docs/agent/ENV_EXAMPLE_게이트자격증명.txt)")

    token = login(api, user, password)
    if not token:
        return 0, [], f"로그인 실패 — {api} 가 서 있는가 (동시 접속 1개다)"

    findings: list[tuple[str, str, str, str]] = []
    seen = 0
    for route in API_PATHS:
        status, body = hit(api, "GET", route, token, with_body=True)
        if status == 0:
            continue
        seen += 1
        text = body.decode("utf-8", "replace")
        try:
            data = json.loads(text)
        except ValueError:
            data = text
        for field, value in _walk_strings(data):
            for name, rx, _why in COMPILED:
                if rx.search(value):
                    snippet = value.strip().replace("\n", " ")
                    if len(snippet) > 120:
                        snippet = snippet[:117] + "…"
                    findings.append((route, field, name, snippet))
                    break
    if seen == 0:
        return 0, [], "한 라우트도 응답을 못 받았다 — 서버가 서 있는가"
    return seen, findings, None


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-277) — 양성 하나, 음성 둘
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    """이 판정기가 **무엇을 잡고 무엇을 안 잡는지**를 두 방향으로 대조한다.

    양성을 못 잡으면 게이트가 없는 것과 같다. 음성을 잡으면 **주석을 못 쓰게 되고**,
    주석을 못 쓰면 사람은 게이트를 끈다 — 꺼진 게이트는 없는 게이트보다 나쁘다.
    """
    fails = 0

    # ① 양성 — 그날 화면에 떠 있던 그 문단. 못 잡으면 이 판정기는 태어난 이유가 없다.
    positive = f'<Text>{BIRTH_SAMPLE}</Text>'
    hits = scan_text(strip_comments(positive))
    if not hits:
        print("[SECRETS] 자기시험 FAIL ① 출생 표본을 못 잡았다 — 판정기가 비었다")
        fails += 1
    else:
        names = {h[1] for h in hits}
        need = {"상대사명", "상대사 코드", "계약 조항"}
        if not need <= names:
            print(f"[SECRETS] 자기시험 FAIL ① 출생 표본에서 {sorted(need - names)} 를 놓쳤다")
            fails += 1

    # ② 음성 — 주석 안의 대장 번호·커널 경로는 **잡히면 안 된다**
    negative_comment = (
        "// D-347 이 그 칸 주석에 적어 둔 그대로 (kernels.k1_event.record_dispatch)\n"
        "/* WRITE_NO_PROBE 선등록 · 에스비정보기술 명세 대기 */\n"
        "const label = '연계 대기';\n"
    )
    hits = scan_text(strip_comments(negative_comment))
    if hits:
        print(f"[SECRETS] 자기시험 FAIL ② 주석을 잡았다 {hits} — 소스가 아니라 화면을 본다")
        fails += 1

    # ③ 음성 — 문자열 **안**의 `//` 를 주석으로 읽으면 그 뒤가 통째로 안 보인다
    tricky = "const u = 'https://x/'; const bad = 'DEV-SBIT-GX-20260810';\n"
    hits = scan_text(strip_comments(tricky))
    if not hits:
        print("[SECRETS] 자기시험 FAIL ③ 'https://' 를 주석으로 읽고 그 뒤를 못 봤다")
        fails += 1

    # ④ 줄 번호가 원본과 같은가 — 어디가 틀린 보고는 고쳐지지 않는다
    shifted = "/* 여러\n줄\n주석 */\nconst x = 'D-421';\n"
    hits = scan_text(strip_comments(shifted))
    if not hits or hits[0][0] != 4:
        print(f"[SECRETS] 자기시험 FAIL ④ 줄 번호가 밀렸다 {hits}")
        fails += 1

    if fails:
        print(f"[SECRETS] 자기시험 {fails}건 실패")
        return 1
    print("[SECRETS] 자기시험 통과 — 양성 1 · 음성 3")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="P-27 화면 기밀 노출 판정기")
    ap.add_argument("--list", action="store_true", help="걸린 자리 전수")
    ap.add_argument("--api", action="store_true", help="+ API 응답 본문 [실측 · 서버 필요]")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    #: ★ 두 면을 **따로** 판정한다 (D-400). 실패 · 판정 불가 · 통과는 셋이고,
    #:   그 셋을 한 칸에 뭉치면 「못 쟀다」가 「통과」 뒤에 숨는다.
    failed = 0
    ungauged: list[str] = []

    # ── ① 프런트 렌더 문자열 ────────────────────────────────────────────
    seen, findings = scan_frontend()
    if seen == 0:
        #: 컨테이너 안에서는 프런트 마운트가 없다 — **없는 것을 0건이라 적지 않는다.**
        print(f"[SECRETS] 프런트 면 **판정 불가** — {FRONTEND} 아래에서 파일을 못 읽었다 "
              "(0건 검사와 검사 못 함은 다르다 · D-301)")
        ungauged.append("프런트")
    else:
        print(f"[SECRETS] [입력] {seen}개 프런트 파일 (주석 걷어낸 뒤) · 패턴 {len(COMPILED)}종")
        if findings and (args.list or len(findings) <= 40):
            for path, lineno, name, snippet in findings:
                rel = path.relative_to(ROOT).as_posix()
                print(f"          {rel}:{lineno}  [{name}]  {snippet}")
        if findings:
            print(f"[SECRETS] FAIL 렌더 문자열에 {len(findings)}건 — 화면이 우리 서랍을 열었다")
            failed += len(findings)
        else:
            print("[SECRETS] 렌더 문자열 0건")

    # ── ② API 응답 본문 ─────────────────────────────────────────────────
    if args.api:
        routes, api_findings, why = scan_api()
        if why:
            print(f"[SECRETS] API 면 **판정 불가** — {why}")
            ungauged.append("API")
        else:
            print(f"[SECRETS] [입력] API {routes}개 라우트 응답 본문 (문자열 필드 전수)")
            for route, field, name, snippet in api_findings:
                print(f"          {route}  {field}  [{name}]  {snippet}")
            if api_findings:
                print(f"[SECRETS] FAIL API 응답에 {len(api_findings)}건")
                failed += len(api_findings)
            else:
                print("[SECRETS] API 응답 0건 [실측]")

    if failed:
        return 1
    if ungauged:
        print(f"[SECRETS] 못 잰 면: {' · '.join(ungauged)} — "
              "재지 못한 것은 초록이 아니다 (D-400)")
        return 2
    print("[SECRETS] 통과 — 화면과 응답이 우리 언어로 말하지 않는다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
