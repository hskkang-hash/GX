#!/usr/bin/env python
"""D-316 — **외부 자원은 「문서에 있다」가 아니라 「계정에서 보았다」로만 등재한다.**

경위
----
우리는 대표께서 주신 API 목록 **문서**를 근거로 `.env.example` 에 자리를 잡았다.
그 문서는 *"받을 수 있는 것"* 의 목록이었지 **"받은 것" 의 목록이 아니었다.**
활용신청 현황 18건 전수 실측 결과 **셋이 계정에 없었다**(CCTV·국립공원·아동센터).

D-292 — 내 판단의 근거가 실측이 아니라 문서였던 사건 — 와 **같은 얼굴**이다.
거기선 도구가 자기를 못 봤고(D-310), 여기선 **대장이 바깥을 못 봤다.**

무엇을 보는가
-------------
  ① 외부 자원 항목마다 `# source:` 근거가 있는가 (없으면 exit 1)
  ② `source` 가 열거 안인가 — `account_verified` | `doc_only`
  ③ ★ **`doc_only` 항목을 참조하는 어댑터가 있으면 exit 1**
     — 문서로만 아는 자원 위에 코드를 얹으면 그 코드는 재작업이 확정된다(D-280).
  ④ 건수 출력 — 항목 수 · account_verified 수 · doc_only 수 (D-301)

    python scripts/verify_external_sources.py          # 판정
    python scripts/verify_external_sources.py --list   # 항목별 근거
    python scripts/verify_external_sources.py --self-test

★ 출생 표본 (D-310)
-------------------
태어난 사유: *"문서에만 있는 자원(DISASTER_CCTV)에 자리를 잡아 두고, 그 자리를 근거로
어댑터를 만들 뻔했다."* 자기시험의 첫 갈래가 **「doc_only 인데 어댑터가 그 이름을 쓴다」**다.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = ROOT / "backend" / ".env.example"
SOURCES = ROOT / "docs" / "agent" / "evidence" / "DA-05" / "sources.yaml"

#: ★ D-333 — 외부 의존을 대장에 올리기 전에 **「우리가 이미 아는 것으로 되는가」**를 적는다.
#:   두 칸이 비면 등재를 거부한다. 외부 의존 하나를 **안 만드는 것**이,
#:   외부 의존 하나를 잘 만드는 것보다 언제나 싸다 — 만들지 않은 것은 고장 나지 않는다.
D333_FIELDS = ("internal_alternative_considered", "why_not")
ADAPTERS = ROOT / "backend" / "adapters"

VALID_SOURCES = ("account_verified", "doc_only")

#: 외부 자원 구역의 시작. 이 위의 변수(DB·Redis 등)는 외부 공공 자원이 아니다.
SECTION_MARK = "외부 공공데이터 API"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def parse(text: str) -> list[dict]:
    """[{name, source, status}] — 외부 자원 구역의 변수 전수.

    직전 주석 블록의 `# source:` / `# status:` 를 그 아래 변수들에 붙인다.
    한 주석 블록이 변수 여럿을 덮는 경우가 있고(포털 3종), 그것이 실제 모양이다.
    """
    if SECTION_MARK not in text:
        return []
    body = text.split(SECTION_MARK, 1)[1]
    rows: list[dict] = []
    source = status = ""
    for line in body.split("\n"):
        stripped = line.strip()
        m = re.match(r"^#\s*source:\s*(\S+)", stripped)
        if m:
            source = m.group(1)
            continue
        m = re.match(r"^#\s*status:\s*(\S+)", stripped)
        if m:
            status = m.group(1)
            continue
        if stripped.startswith("#") or not stripped:
            # 빈 줄은 블록의 끝 — 다음 변수 묶음은 자기 근거를 다시 적어야 한다
            if not stripped:
                source = status = ""
            continue
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", stripped)
        if m:
            rows.append({"name": m.group(1), "source": source, "status": status})
    return rows


#: **설정을 읽는 자리**의 모양. 이름이 소스 어딘가에 나오는 것과, 그 설정을 **읽는 것**은
#: 다르다 — 전자는 설명일 수 있고 후자만 의존이다.
#:
#: ★ 정정 둘을 거쳐 여기 왔다 (D-310 — 술어를 좁힐 때마다 반례를 시험에 넣는다):
#:   ① 첫 판: 소스에 이름이 나오면 참조로 셌다 → 독스트링의 설명이 잡혔다(거짓 양성).
#:   ② 둘째 판: 문자열을 통째로 버렸다 → `os.environ["X"]` 를 놓쳤다(거짓 음성).
#:      환경변수 참조는 **언제나 문자열 리터럴**이다.
#:   ③ 지금: **읽는 문법**을 본다. 산문에 이름이 있어도 읽지 않으면 의존이 아니다.
ENV_READ_PATTERNS = (
    r'os\.environ\[\s*["\']([A-Z][A-Z0-9_]{3,})["\']',
    r'os\.environ\.get\(\s*["\']([A-Z][A-Z0-9_]{3,})["\']',
    r'os\.getenv\(\s*["\']([A-Z][A-Z0-9_]{3,})["\']',
    r'settings\.([A-Z][A-Z0-9_]{3,})\b',
    r'\benv\(\s*["\']([A-Z][A-Z0-9_]{3,})["\']',
    r'\bconfig\(\s*["\']([A-Z][A-Z0-9_]{3,})["\']',
)


def adapter_sources() -> dict[str, str]:
    """어댑터가 **설정으로 읽는** 환경변수 이름 → 그 파일. 없으면 빈 dict."""
    out: dict[str, str] = {}
    if not ADAPTERS.is_dir():
        return out
    for path in ADAPTERS.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        src = _code_only(path.read_text(encoding="utf-8", errors="replace"))
        for pattern in ENV_READ_PATTERNS:
            for name in re.findall(pattern, src):
                out.setdefault(name, str(path.relative_to(ROOT)).replace("\\", "/"))
    return out


def _code_only(src: str) -> str:
    """주석과 문자열(독스트링 포함)을 뺀 소스.

    ★ 첫 판은 원문을 그대로 훑었고, `adapters/juso/__init__.py` 의 **독스트링에 적힌**
      "요청 URL 은 …(JUSO_API_URL)" 한 줄을 **어댑터가 그 자원 위에 서 있다**로 읽었다.
      설명하는 문장과 의존하는 코드는 다르다 — 그 둘을 못 가르면 이 게이트의 빨간불은
      뜻이 둘이 되고, 뜻이 둘인 빨간불은 곧 꺼진다(D-295 가 게이트를 나눈 이유).

      `test_clip_playback.py` 가 독스트링의 'ffmpeg' 때문에 같은 방식으로 잡혔던 것과
      **같은 얼굴**이다. 술어를 좁힐 때마다 그 반례를 자기시험에 넣는다(D-310).
    """
    import ast
    import io
    import tokenize

    # ★ 두 번째 정정: **문자열을 통째로 버리면 안 된다.**
    #   환경변수 참조는 언제나 문자열 리터럴이다 — `os.environ["JUSO_API_URL"]`.
    #   전부 버렸더니 이번엔 **진짜 참조를 놓쳤다**(거짓 음성). 술어를 좁히다 반대편으로
    #   넘어간 것이고, 자기시험의 둘째 반례가 그 자리에서 잡았다.
    #   그래서 **독스트링만** 버린다 — 설명하는 문자열과 값으로 쓰는 문자열은 다르다.
    doc_lines: set[int] = set()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None) or []
        if not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            doc_lines.update(range(first.lineno, (first.end_lineno or first.lineno) + 1))

    # ★ 세 번째 정정: 토큰을 **공백으로 이어 붙이면 안 된다.**
    #   `os.environ["X"]` 가 `os . environ [ "X" ]` 가 되어 읽기 문법 정규식이 못 맞췄다 —
    #   자기시험의 셋째 반례가 그 자리에서 잡았다. 그래서 **원문의 자리를 지키고**
    #   버릴 줄만 지운다.
    lines = src.split("\n")
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                row, col = tok.start
                if 1 <= row <= len(lines):
                    lines[row - 1] = lines[row - 1][:col]
    except (tokenize.TokenError, IndentationError):
        return src                          # 못 읽으면 넉넉한 쪽으로 — 놓치기보다 잡는다
    for row in doc_lines:
        if 1 <= row <= len(lines):
            lines[row - 1] = ""
    return "\n".join(lines)


#: 외부 자원이 아닌 공통 동작 설정 — 키가 아니고 계정과 무관하다.
NOT_A_SOURCE = ("EXTERNAL_API_TIMEOUT_SEC", "EXTERNAL_API_RETRY",
                "EXTERNAL_API_CACHE_TTL_SEC", "EXTERNAL_API_ENABLED")


def check_internal_first(sources: list[dict]) -> list[str]:
    """★ D-333 — 외부 원천마다 **내부 대안을 검토했다는 기록**이 있는가. **순수 함수다.**

    출생 표본은 FX-5 다: 좌표→주소를 외부에서 사려고 키를 신청하고 실측기를 만들고
    잠금을 세웠는데, 답은 **카메라가 고정 설치물**이라는 우리가 이미 아는 사실이었다.
    그 검토를 적을 칸이 없었기 때문에 아무도 묻지 않았다.
    """
    problems: list[str] = []
    for s in sources:
        sid = s.get("id", "?")
        for field in D333_FIELDS:
            if not str(s.get(field) or "").strip():
                problems.append(
                    f"{sid}: `{field}` 가 비었다 — 외부 자원을 올리기 전에 "
                    f"「우리가 이미 아는 것으로 되는가」를 먼저 적는다(D-333). "
                    f"검토한 게 없으면 \"없음\" 이라고 적어라. "
                    f"묻지 않고 가는 것만 금지한다")
    return problems


def check(rows: list[dict], used: dict[str, str]) -> list[str]:
    problems: list[str] = []
    for row in rows:
        name = row["name"]
        if name in NOT_A_SOURCE:
            continue
        source = (row.get("source") or "").strip()
        if not source:
            problems.append(
                f"{name}: `# source:` 근거가 없다 — 문서에서 안 것인지 계정에서 본 것인지 "
                f"구별되지 않는다. 구별되지 않으면 문서가 실측 행세를 한다 (D-316)")
            continue
        if source not in VALID_SOURCES:
            problems.append(f"{name}: source='{source}' 는 열거 밖이다 {VALID_SOURCES}")
            continue
        # ★ 핵심 — 문서로만 아는 자원 위에 코드를 얹지 않는다
        if source == "doc_only" and name in used:
            problems.append(
                f"{name}: **doc_only 인데 어댑터가 참조한다** ({used[name]}). "
                f"문서로만 아는 자원 위의 코드는 재작업이 확정된다 (D-280 · D-316). "
                f"계정에서 확인한 뒤 source 를 account_verified 로 올리고 나서 쓴다")
    return problems


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 — ★ 첫 갈래가 **이 도구를 태어나게 한 표본**이다 (D-310)
# ═══════════════════════════════════════════════════════════════════════════
def self_test() -> int:
    verified = [{"name": "KMA_APIHUB_KEY", "source": "account_verified", "status": ""}]
    doc_only = [{"name": "DISASTER_CCTV_URL", "source": "doc_only", "status": "not_required"}]
    no_source = [{"name": "MYSTERY_URL", "source": "", "status": ""}]
    bad_source = [{"name": "X_URL", "source": "maybe", "status": ""}]

    cases = (
        # ★ 출생 표본 — 문서에만 있는 자원에 어댑터가 붙은 상태.
        #   DISASTER_CCTV 가 계정에 없는데 자리가 있었고, 그 자리를 근거로 어댑터를
        #   만들 뻔했다. 그 갈래가 이것이다.
        ("★ 출생 표본 — doc_only 인데 어댑터가 참조한다",
         doc_only, {"DISASTER_CCTV_URL": "backend/adapters/x.py"}, True),
        ("doc_only 인데 아무도 안 쓰면 안 잡는다", doc_only, {}, False),
        ("account_verified 는 어댑터가 써도 된다",
         verified, {"KMA_APIHUB_KEY": "backend/adapters/kma.py"}, False),
        ("근거가 없으면 잡는다", no_source, {}, True),
        ("열거 밖 근거를 잡는다", bad_source, {}, True),
    )
    bad = 0
    for label, rows, used, should_fail in cases:
        ok = bool(check(rows, used)) == should_fail
        print(f"  {'OK  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad += 1

    # ★ 술어를 좁힐 때마다 그 반례 둘을 넣는다 (D-310).
    #   첫 판이 독스트링의 언급을 코드 참조로 셌고, 그것은 거짓 양성이었다.
    doc_mention = '"""등재됐다(JUSO_API_URL)."""\nX = 1\n'
    code_use = 'import os\nURL = os.environ["JUSO_API_URL"]\n'
    prose_const = 'REASON = "요청 URL 은 등재됐다(JUSO_API_URL)."' + chr(10)

    def reads(text: str) -> bool:
        body = _code_only(text)
        return any(re.findall(pat, body) for pat in ENV_READ_PATTERNS)

    for label, sample, want in (
            ("★ 산문 상수 안의 언급은 참조가 아니다 (셋째 판이 이걸 갈랐다)",
             prose_const, False),
            ("★ 독스트링의 언급도 참조가 아니다 (첫 판이 이걸 잡았다)", doc_mention, False),
            ("진짜 설정 읽기는 그대로 잡는다 (둘째 판이 이걸 놓쳤다)", code_use, True)):
        if reads(sample) != want:
            print(f"  FAIL {label}")
            bad += 1
        else:
            print(f"  OK   {label}")

    # ★ D-333 출생 표본 — FX-5: 밖에서 사려던 것을 우리는 이미 알고 있었다
    for label, sample, should_fail in (
            ("★ D-333 출생표본 내부 대안 칸이 비면 잡는다",
             [{"id": "juso_coord2addr"}], True),
            ("두 칸이 다 있으면 안 잡는다",
             [{"id": "x", "internal_alternative_considered": "카메라 설치 주소",
               "why_not": "내부가 이겼다"}], False),
            ("\"없음\" 이라고 적은 것은 빈 것이 아니다",
             [{"id": "x", "internal_alternative_considered": "없음",
               "why_not": "계약 AC 가 부르지 않는다"}], False)):
        got = bool(check_internal_first(sample))
        if got != should_fail:
            print(f"  FAIL {label}")
            bad += 1
        else:
            print(f"  OK   {label}")

    parsed = parse(ENV_EXAMPLE.read_text(encoding="utf-8")) if ENV_EXAMPLE.is_file() else []
    ok_parse = len(parsed) >= 8
    print(f"  {'OK  ' if ok_parse else 'FAIL'} 파서가 .env.example 을 읽는다 ({len(parsed)}건)")
    if not ok_parse:
        bad += 1
    if bad:
        print(f"[EXTSRC] 자기시험 {bad}건 실패 — 이 판정기는 눈이 멀었다")
        return 1
    print(f"[EXTSRC] 자기시험 {len(cases) + 7}건 통과 (출생 표본 2 + 술어 반례 3 + D-333 3)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not ENV_EXAMPLE.is_file():
        print(f"[EXTSRC] .env.example 이 없다: {ENV_EXAMPLE} — 판정할 수 없으므로 멈춘다")
        return 1
    if self_test() != 0:
        return 1

    rows = [r for r in parse(ENV_EXAMPLE.read_text(encoding="utf-8"))
            if r["name"] not in NOT_A_SOURCE]
    used = adapter_sources()
    verified = [r for r in rows if r["source"] == "account_verified"]
    doc_only = [r for r in rows if r["source"] == "doc_only"]

    print(f"[EXTSRC] 검사 **{len(rows)}건** (모수=.env.example 의 외부 공공데이터 구역 변수 "
          f"전수 · 술어=`# source:` 근거 + doc_only 참조 여부)")
    if not rows:
        print("[EXTSRC] 항목을 한 건도 못 찾았다 — 열거기가 눈이 멀었다 (D-301)")
        return 1
    print(f"[EXTSRC] account_verified **{len(verified)}** · doc_only **{len(doc_only)}** "
          f"· 근거 없음 {len(rows) - len(verified) - len(doc_only)}")
    if doc_only:
        print("[EXTSRC] doc_only — **어댑터 금지**: "
              + ", ".join(r["name"] for r in doc_only))

    if args.list:
        for r in rows:
            extra = f" · {r['status']}" if r.get("status") else ""
            mark = "쓰임" if r["name"] in used else "    "
            print(f"  {mark}  {r['name']:34} {r['source'] or '(근거 없음)'}{extra}")

    problems = check(rows, used)

    # ★ D-333 — 외부 원천 등록부에도 같은 두 칸을 요구한다.
    if SOURCES.is_file():
        import yaml

        doc = yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or {}
        srcs = doc.get("sources") or []
        print(f"[EXTSRC] D-333 내부 대안 검토 — 원천 **{len(srcs)}건** 전수 "
              f"(술어=internal_alternative_considered · why_not 두 칸이 채워졌는가)")
        if not srcs:
            problems.append("sources.yaml 에서 원천을 한 건도 못 읽었다 — "
                            "판정 불가이지 통과가 아니다 (D-301)")
        problems += check_internal_first(srcs)
    else:
        problems.append(f"{SOURCES.relative_to(ROOT)} 가 없다 — D-333 을 판정할 수 없다")

    if problems:
        print("[EXTSRC] 위반 — 문서로 안 것이 실측 행세를 하고 있다")
        for p in problems:
            print(f"  · {p}")
        return 1
    print("[EXTSRC] 통과 — 항목마다 근거가 있고, 문서로만 아는 자원 위에 코드가 없다")
    return 0


if __name__ == "__main__":
    from _gate_header import gate_header  # P-107 — TARGET/AS/SOURCE
    gate_header(
        __file__,
        measured=("바깥 출처를 쓴다고 **선언한 어댑터**가 D-333 두 칸을 적었는가 — 어댑터 "
               "**분모 %d파일**(지금 셌다 · `backend/adapters` 전수) · 허용 출처 %d종"
               % (len(list(ADAPTERS.rglob("*.py"))) if ADAPTERS.is_dir() else 0,
                  len(VALID_SOURCES))),
    )
    sys.exit(main())
