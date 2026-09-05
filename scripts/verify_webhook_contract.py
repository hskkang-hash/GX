#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SEC-16 — 웹훅 서명·재시도 규약을 **강제하는 판정기** (PRD v2.5 §6 이 이름을 정했다).

무엇을 막는가
-------------
나가는 웹훅은 아직 **0개**다 — 문은 UX-19(CAP 1.2)가 낸다. 그래서 이 판정기는
「지금 나가는 것이 서명돼 있는가」를 잴 수 없다. 잴 수 없는 것을 재는 척하지 않는다(D-301).

대신 **문이 서는 순간을 잡는다.** 새 웹훅 발송자가 규약을 안 쓰고 태어나면 그 자리에서
exit 1 이다. 규약이 문보다 먼저 있는 이유가 그것이다 —
**규약이 나중에 오면 규약은 「이미 보내고 있는 모양」의 다른 이름이 된다.**

보는 것 — 다섯
--------------
  ① 규약이 실재하는가 — `common/webhook_contract.py` 가 있고, 닫는 조건 셋의
     이름(스키마 헤더 · 서명 검증 · 5회)이 **값으로** 박혀 있는가
  ② 닫는 조건 셋마다 **시험이 이름으로** 있는가 — 없는 시험은 문서다(§규율 2)
  ③ 서명 비교가 **상수시간**인가 — `hmac.compare_digest` 만. `==` 가 보이면 exit 1
  ④ 규약이 **문을 내지 않았는가** — 라우트·URL 등록이 있으면 새 인증 경로다
     (세종 §4-4 · P-37: 새 인증 경로 금지 · 무계정 링크 금지 · 익명 콜백 금지)
  ⑤ **래칫**(D-311) — 웹훅/콜백을 밖으로 쏘는 파일은 규약을 쓰거나 기준선에 이름이 있어야 한다.
     기준선은 §0.4 레거시를 **이름으로** 담는다. 새 발송자는 100% 의무다.

★ 0건은 초록이 아니다 (D-301)
    「웹훅 발송자 0건」과 「발송자를 못 찾았다」는 다르다. 그래서 이 판정기는
    **자기가 몇 개의 파일을 읽었는지** 먼저 적고, 0을 셀 때는 사유를 함께 적는다.

종료 코드 (저장소 규약 · D-400)
    0 = 쟀고 통과   1 = 쟀고 실패   2 = 못 쟀다 (회색)

    python scripts/verify_webhook_contract.py
    python scripts/verify_webhook_contract.py --list
    python scripts/verify_webhook_contract.py --freeze     # 발송자 기준선 갱신
    python scripts/verify_webhook_contract.py --self-test

호스트에서 돈다 — Django 도 컨테이너도 필요 없다. 소스를 읽는다.
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "backend" / "common" / "webhook_contract.py"
TESTS = ROOT / "backend" / "tests" / "test_s_webhook_contract.py"
BACKEND = ROOT / "backend"
EVIDENCE = ROOT / "docs" / "agent" / "evidence" / "SEC-16"
BASELINE = EVIDENCE / "webhook_senders_baseline.txt"

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# 술어 — 파일 없이 시험할 수 있게 문자열을 받는다 (자기시험이 저장소에 매이면 안 된다)
# ═══════════════════════════════════════════════════════════════════════════

#: ① 규약에 반드시 **값으로** 박혀 있어야 하는 상수. 문자열 검색이 아니라 AST 로 본다.
#:
#: ★ [실측 2026-09-05] 처음엔 문자열 검색이었고, **심은 결함을 놓쳤다.**
#:   `hmac.compare_digest` 를 `given != expected` 로 바꿔 심었는데 판정기가 초록을 냈다 —
#:   `compare_digest` 라는 낱말이 **독스트링에 남아 있었기** 때문이다. 규약을 설명하는
#:   문장이 규약을 지켰다는 증거로 셌다. 그래서 판정을 **코드의 구조**로 옮겼다.
REQUIRED_CONSTANTS: tuple[tuple[str, object, str], ...] = (
    ("SCHEMA_HEADER", "X-GX-Schema",
     "스키마 버전 헤더 이름 — PRD v2.5 §6 이 정한 이름. 갈리면 계약이 갈린다"),
    ("SCHEMA_VERSION", "1", "지금 내는 판"),
    ("MAX_ATTEMPTS", 5,
     "재시도 5회 — 정본이 정한 수. 여기서 조용히 늘리지 않는다"),
)

#: 규약에 반드시 있어야 하는 함수와 그 이유.
REQUIRED_FUNCTIONS: tuple[tuple[str, str], ...] = (
    ("sign", "서명을 만드는 자리"),
    ("verify", "받은 웹훅을 검증하는 자리. 없으면 규약이 아니라 발송 도우미다"),
    ("giveup_record",
     "5회 뒤 포기를 **행으로** 남기는 자리. 없으면 경보가 조용히 사라진다"),
    ("outbound_headers", "보낼 때 붙는 헤더를 한곳에서 만드는 자리"),
)

#: ② 닫는 조건 셋 → 그것을 재는 시험 함수 이름. **없는 시험은 문서다.**
REQUIRED_TESTS: tuple[tuple[str, str], ...] = (
    ("test_a_wrong_secret_is_rejected", "① 서명 불일치 거절"),
    ("test_a_dead_receiver_is_hit_exactly_five_times", "② 5회에서 멈춘다"),
    ("test_giving_up_leaves_a_row", "② 포기가 행으로 남는다"),
    ("test_a_missing_schema_header_is_rejected", "③ 스키마 버전 헤더 부재 거절"),
    ("test_the_module_declares_no_routes", "함정 — 새 인증 경로 금지(세종 §4-4 · P-37)"),
)

#: ③ 서명 비교를 문자열 등호로 하는 모양. 하나라도 보이면 실패다.
_TIMING_LEAK = re.compile(
    r"(signature|sig|digest|mac)\s*(==|!=)|(==|!=)\s*(expected_sig|expected_signature)",
    re.IGNORECASE)

#: ④ 규약 모듈이 문을 냈는가.
_ROUTE_MARKS = ("@route.", "@api_controller", "@router.", "urlpatterns",
                "path(", "re_path(")

#: ⑤ 웹훅/콜백을 밖으로 쏘는 파일의 모양 — **둘 다** 있어야 발송자로 본다.
_SENDER_SUBJECT = re.compile(r"webhook_url|callback_url|api_callback_url|webhook",
                             re.IGNORECASE)
_SENDER_VERB = re.compile(
    r"requests[.]post|requests[.]request|external_http[.]post|"
    r"external_http[.]request|httpx[.]post|session[.]post")

#: 발송자가 규약을 쓴다는 증거.
_USES_CONTRACT = re.compile(r"webhook_contract|outbound_headers|RetryPolicy")


def strip_noncode(source: str) -> str:
    """주석과 문자열 리터럴을 **지운** 소스. 판정은 코드에만 건다.

    ★ [실측 2026-09-05] 이 함수가 없을 때 판정기가 **자기 문서를 잡았다.**
      규약 모듈의 「`sig == expected` 를 쓰지 마라」는 설명 한 줄과 시험 파일의
      「skip·xfail 하지 말 것」이라는 금지 문구가 위반으로 셌다.
      금지를 적은 글이 금지 위반이 되면, 다음 사람은 **설명을 지워서** 초록을 만든다.
    """
    import io as _io
    import tokenize as _tok

    #: 이름·숫자끼리만 공백으로 가른다. **구두점에는 공백을 넣지 않는다** —
    #: 넣으면 `requests . post` 가 되어 `requests[.]post` 를 찾는 술어가 전부 눈이 먼다
    #: [실측 2026-09-05: 그렇게 해서 진짜 발송자 2건이 0건으로 셌다].
    joined: list[str] = []
    prev_word = False
    try:
        for tok in _tok.generate_tokens(_io.StringIO(source).readline):
            if tok.type in (_tok.COMMENT, _tok.STRING):
                prev_word = False
                continue
            if not tok.string.strip():
                continue
            word = tok.string[0].isalnum() or tok.string[0] == "_"
            if word and prev_word:
                joined.append(" ")
            joined.append(tok.string)
            prev_word = word
    except (_tok.TokenError, IndentationError, SyntaxError):
        # 읽지 못하면 **원문을 돌려준다** — 넓게 잡아 사람이 보게 한다.
        # 조용히 통과시키는 쪽으로 기울지 않는다 (D-301).
        return source
    return "".join(joined)


#: 시험을 조용히 죽이는 표식. **데코레이터로 실제로 붙은 것**만 본다 —
#: 「skip 하지 말 것」이라고 적은 문장까지 잡으면 금지를 적은 글이 위반이 된다.
_TEST_SILENCERS = ("@skip", "@unittest.skip", "@pytest.mark.skip",
                   "@expectedFailure", "@pytest.mark.xfail")


def silenced_tests(source: str) -> list[str]:
    """실제로 붙어 있는 죽이기 데코레이터들 (주석·문자열 제외)."""
    code = strip_noncode(source)
    # 토큰 사이에 공백이 끼므로 `@ skip` 모양으로도 찾는다.
    flat = code.replace(" ", "")
    return [mark for mark in _TEST_SILENCERS if mark.replace(" ", "") in flat]


def missing_names(source: str, required) -> list[str]:
    """규약/시험에서 빠진 이름들. `(빠진 이름, 왜 필요한가)` 로 돌려준다."""
    return ["%s — %s" % (name, why) for name, why in required if name not in source]


def has_timing_leak(source: str) -> bool:
    """(옛 술어 · 낱말 검색) 서명을 문자열 등호로 비교하는 **모양**인가.

    남겨 두되 판정에는 쓰지 않는다 — 이름을 `given`/`expected` 로 바꾸면 그대로 샌다.
    진짜 판정은 `judge_contract()` 안의 AST 검사다.
    """
    return bool(_TIMING_LEAK.search(source))


def judge_contract(source: str) -> list[str]:
    """규약 모듈을 **구조로** 판정한다. 어긋난 것들의 사유 목록.

    낱말 검색이 아니라 AST 인 이유 [실측 2026-09-05]: 낱말 검색은 **독스트링에 남은
    낱말을 증거로 셌고**, 그래서 심은 결함(`compare_digest` → `!=`)을 놓쳤다.
    """
    problems: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return ["규약 모듈을 파싱할 수 없다: %s" % exc]

    consts: dict[str, object] = {}
    funcs: dict[str, ast.AST] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1                 and isinstance(node.targets[0], ast.Name):
            try:
                consts[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                pass
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.setdefault(node.name, node)

    for name, expected, why in REQUIRED_CONSTANTS:
        if name not in consts:
            problems.append("규약에 %s 상수가 없다 — %s" % (name, why))
        elif consts[name] != expected:
            problems.append("규약의 %s 가 %r 이다 (정본은 %r) — %s"
                            % (name, consts[name], expected, why))

    for name, why in REQUIRED_FUNCTIONS:
        if name not in funcs:
            problems.append("규약에 %s() 가 없다 — %s" % (name, why))

    # ★ 상수시간 비교 — `verify()` **안**을 본다.
    verify_fn = funcs.get("verify")
    if verify_fn is not None:
        uses_compare_digest = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "compare_digest"
            for n in ast.walk(verify_fn))
        if not uses_compare_digest:
            problems.append(
                "verify() 가 `hmac.compare_digest` 를 부르지 않는다 — 서명 비교가 "
                "상수시간이 아니면 첫 다른 글자에서 끝나 시간이 샌다(타이밍 공격)")
        equality = [n for n in ast.walk(verify_fn)
                    if isinstance(n, ast.Compare)
                    and any(isinstance(op, (ast.Eq, ast.NotEq)) for op in n.ops)]
        if equality:
            problems.append(
                "verify() 안에 ==/!= 비교가 %d곳 있다 (%d행 부근) — 서명 판정에 "
                "문자열 등호를 쓰면 안 된다. 비교는 `hmac.compare_digest` 하나뿐이어야 한다"
                % (len(equality), equality[0].lineno))
    return problems


def opens_a_door(source: str) -> list[str]:
    """규약 모듈이 라우트를 열었는가. 열었으면 그 표식들."""
    return [mark for mark in _ROUTE_MARKS if mark in source]


def is_sender(source: str) -> bool:
    """이 파일이 웹훅/콜백을 **밖으로 쏘는가.** 주어와 동사가 둘 다 있어야 한다 —
    하나만으로 보면 모델 정의·열거값까지 발송자가 되고, 판정이 소음이 된다."""
    return bool(_SENDER_SUBJECT.search(source) and _SENDER_VERB.search(source))


def uses_contract(source: str) -> bool:
    return bool(_USES_CONTRACT.search(source))


# ═══════════════════════════════════════════════════════════════════════════
# 모으기
# ═══════════════════════════════════════════════════════════════════════════

def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def collect_senders() -> tuple[list[str], int]:
    """웹훅 발송자 후보와 **읽은 파일 수**. 읽은 수를 함께 돌려주는 이유는
    0건이 「없다」인지 「못 봤다」인지 부르는 쪽이 가릴 수 있게 하기 위해서다(D-301)."""
    senders: list[str] = []
    scanned = 0
    for path in sorted(BACKEND.rglob("*.py")):
        if "migrations" in path.parts:
            continue
        scanned += 1
        source = strip_noncode(read(path))
        if is_sender(source) and not uses_contract(source):
            senders.append(path.relative_to(ROOT).as_posix())
    return senders, scanned


def parse_baseline(text: str) -> set[str]:
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


_BASELINE_HEADER = """\
# SEC-16 ⑤ 래칫 기준선 — 규약을 쓰지 않는 **기존** 웹훅/콜백 발송자 (D-311)
#
# ★ 여기 있는 것은 §0.4 레거시이거나 SEC-16 이전에 태어난 자리다. 소급하지 않는다.
#   **새 발송자는 100% 의무다** — 이 목록에 손으로 한 줄을 더하는 것이
#   「이 자리는 서명 없이 밖으로 쏜다」는 선언이다. 사유 없이 더하지 말 것.
#
# --freeze 가 만든다.
"""


# ═══════════════════════════════════════════════════════════════════════════
# 자기시험 (D-310) — **심어 보고 잡는가**
# ═══════════════════════════════════════════════════════════════════════════

def self_test() -> int:
    checks: list[tuple[str, bool]] = []

    # ★ 출생 표본 — 서명을 `==` 로 비교하는 코드. 이것이 통과하면 이 게이트는 없느니만 못하다.
    checks.append(("★ 출생표본 — 서명을 == 로 비교하면 잡는다",
                   has_timing_leak("if signature == expected:")))
    checks.append(("★ 출생표본 — 이름이 sig 여도 잡는다",
                   has_timing_leak("if sig != expected_signature:")))
    checks.append(("음성 대조 — compare_digest 는 잡지 않는다",
                   not has_timing_leak("hmac.compare_digest(given, expected)")))
    checks.append(("음성 대조 — 관계없는 등호는 잡지 않는다",
                   not has_timing_leak("if attempt == 5:")))

    # ── 규약 구조 판정 (AST) ────────────────────────────────────────────────
    NL = chr(10)
    good = NL.join([
        'SCHEMA_HEADER = "X-GX-Schema"',
        'SCHEMA_VERSION = "1"',
        "MAX_ATTEMPTS = 5",
        "def sign(a, b, c): return a",
        "def outbound_headers(a, b): return {}",
        "def giveup_record(**kw): return kw",
        "def verify(secret, body, headers):",
        "    return hmac.compare_digest(given, expected), ''",
    ])
    checks.append(("음성 대조 — 구조가 갖춰지면 통과한다", not judge_contract(good)))
    checks.append(("★ 출생표본 — verify 가 != 로 비교하면 잡는다 [실측 2026-09-05]",
                   any("==/!=" in x for x in judge_contract(
                       good.replace("return hmac.compare_digest(given, expected), ''",
                                    "return given != expected, ''")))))
    checks.append(("★ 출생표본 — 독스트링에 남은 compare_digest 는 증거가 아니다",
                   any("compare_digest" in x for x in judge_contract(
                       good.replace("return hmac.compare_digest(given, expected), ''",
                                    "return True, ''")))))
    checks.append(("5회를 조용히 늘리면 잡는다",
                   any("MAX_ATTEMPTS" in x for x in
                       judge_contract(good.replace("MAX_ATTEMPTS = 5", "MAX_ATTEMPTS = 9")))))
    checks.append(("헤더 이름을 바꾸면 잡는다 (계약이 갈린다)",
                   any("SCHEMA_HEADER" in x for x in judge_contract(
                       good.replace('"X-GX-Schema"', '"X-Our-Schema"')))))
    checks.append(("giveup_record 가 없으면 잡는다",
                   any("giveup_record" in x for x in judge_contract(
                       good.replace("def giveup_record(**kw): return kw", "pass")))))

    # 문을 열면 잡는다
    checks.append(("★ 규약이 라우트를 열면 잡는다 (새 인증 경로 금지)",
                   opens_a_door('@route.post("/subscriptions")') == ["@route."]))
    checks.append(("음성 대조 — 순수 함수뿐이면 문이 없다",
                   not opens_a_door("def verify(secret, body, headers):")))

    # 발송자 술어 — 주어와 동사가 둘 다 있어야 한다
    checks.append(("★ 웹훅 URL 로 POST 하면 발송자다",
                   is_sender("requests.post(webhook_url, json=payload)")))
    checks.append(("주어만 있으면 발송자가 아니다 (모델·열거값)",
                   not is_sender('WEBHOOK = "webhook", "Webhook"')))
    checks.append(("동사만 있으면 발송자가 아니다",
                   not is_sender("requests.post(api_url, json=payload)")))
    checks.append(("규약을 쓰면 래칫에 걸리지 않는다",
                   uses_contract("from common.webhook_contract import outbound_headers")))

    # 시험 등재부
    checks.append(("닫는 조건의 시험이 없으면 잡는다 (없는 시험은 문서다)",
                   len(missing_names("def test_nothing(self): pass", REQUIRED_TESTS)) == 5))

    # ★ 출생 표본 둘 — **판정기가 자기 문서를 잡았다** [실측 2026-09-05].
    #   금지를 적은 글이 금지 위반이 되면, 다음 사람은 설명을 지워서 초록을 만든다.
    doc = chr(34) * 3 + " sig == expected 를 쓰지 마라 " + chr(34) * 3 + chr(10)
    checks.append(("★ 출생표본 — 「== 쓰지 마라」는 **설명**은 위반이 아니다",
                   not has_timing_leak(strip_noncode(doc + "x = 1"))))
    checks.append(("그래도 코드에 있으면 여전히 잡는다",
                   has_timing_leak(strip_noncode(doc + "if sig == expected: pass"))))
    note = chr(34) * 3 + " skip 하지 말 것 " + chr(34) * 3 + chr(10)
    checks.append(("★ 출생표본 — 「skip 하지 말 것」이라는 문장은 위반이 아니다",
                   not silenced_tests(note + "def test_x(): pass")))
    checks.append(("실제로 붙은 @skip 은 잡는다",
                   silenced_tests(note + "@skip" + chr(10) + "def test_x(): pass") == ["@skip"]))
    checks.append(("주석 속 발송자 흉내는 발송자가 아니다",
                   not is_sender(strip_noncode("# requests.post(webhook_url)" + chr(10)))))
    # ★ 출생 표본 셋 — **주석을 지우다가 진짜 발송자를 지웠다** [실측 2026-09-05].
    #   토큰 사이에 공백을 넣었더니 `requests . post` 가 되어 술어가 눈이 멀었고,
    #   실재하는 발송자 2건이 **0건**으로 셌다. 0건은 초록으로 보였다.
    checks.append(("★ 출생표본 — 주석을 지운 뒤에도 requests.post 를 본다",
                   is_sender(strip_noncode(
                       "# 주석" + chr(10) + "requests.post(callback_url, json=x)" + chr(10)))))
    checks.append(("★ 출생표본 — 지운 소스에서 이름이 붙어 버리지 않는다",
                   "import io" in strip_noncode("import io" + chr(10))))

    bad = 0
    for label, ok in checks:
        bad += 0 if ok else 1
        print("  %s   %s" % ("OK  " if ok else "FAIL", label))
    print("[WEBHOOK-CONTRACT] 자기시험 %d건 중 %d건 실패" % (len(checks), bad))
    return 1 if bad else 0


# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if not BACKEND.is_dir():
        # 못 쟀다 — 회색이다. 「검사할 것이 없었다」가 아니다 (D-301).
        print("[WEBHOOK-CONTRACT] GRAY backend/ 를 찾을 수 없다: %s" % BACKEND)
        return 2

    problems: list[str] = []

    # ① 규약이 실재하는가
    contract = read(CONTRACT)
    if not contract:
        problems.append("규약 파일이 없다: %s — 문보다 규약이 먼저다"
                        % CONTRACT.relative_to(ROOT).as_posix())
    else:
        # ①③ 구조로 판정한다 (상수 값 · 함수 실재 · 상수시간 비교)
        problems.extend(judge_contract(contract))
        # ④ 규약이 문을 냈는가
        doors = opens_a_door(strip_noncode(contract))
        if doors:
            problems.append("규약 모듈이 라우트를 열었다(%s) — 새 인증 경로 금지"
                            "(세종 §4-4 · P-37). 문은 UX-19 가 F-05 구독 등록 위에 낸다"
                            % ", ".join(doors))

    # ② 닫는 조건마다 시험이 있는가
    tests = read(TESTS)
    if not tests:
        problems.append("규약 시험 파일이 없다: %s — **증명 없는 구현은 문서다**"
                        % TESTS.relative_to(ROOT).as_posix())
    else:
        for gap in missing_names(tests, REQUIRED_TESTS):
            problems.append("닫는 조건을 재는 시험이 없다: " + gap)
        for banned in silenced_tests(tests):
            problems.append("규약 시험에 %s 가 붙어 있다 — 절대금지 #4 (D-105). "
                            "못 고친 결함은 조용히 끄지 말고 사유와 함께 등재한다" % banned)

    # ⑤ 래칫
    senders, scanned = collect_senders()
    baseline = parse_baseline(read(BASELINE)) if BASELINE.exists() else set()

    if args.freeze:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(
            _BASELINE_HEADER + "".join(name + "\n" for name in sorted(senders)),
            encoding="utf-8")
        print("[WEBHOOK-CONTRACT] 발송자 기준선 %d건으로 잠갔다" % len(senders))
        return 0

    new_senders = sorted(set(senders) - baseline)
    if new_senders:
        problems.append(
            "규약을 쓰지 않는 **새** 웹훅/콜백 발송자 %d건 — 서명 없는 웹훅은 누구나 보낼 수 "
            "있는 경보다. `common.webhook_contract` 를 쓰거나 기준선에 사유와 함께 더하라:\n    "
            % len(new_senders) + "\n    ".join(new_senders))

    # ── 출력. **자기가 무엇을 몇 건 보았는지 먼저 말한다** (D-301 · GATE_INPUTS_MARK)
    print("[WEBHOOK-CONTRACT] [입력] backend 파이썬 %d개 읽음 · 발송자 후보 %d건 "
          "(기준선 %d건) · 규약 검사 %d항목 · 시험 등재 %d건"
          % (scanned, len(senders), len(baseline),
             len(REQUIRED_CONSTANTS) + len(REQUIRED_FUNCTIONS) + 2, len(REQUIRED_TESTS)))
    if not senders:
        print("[WEBHOOK-CONTRACT] 발송자 0건 — **사유: 나가는 웹훅이 아직 없다.**"
              " 문은 UX-19 가 낸다. 0건은 「없다」이지 「못 봤다」가 아니다")

    if args.list:
        for name in sorted(senders):
            mark = "기준선" if name in baseline else "**새 발송자**"
            print("  %-12s %s" % (mark, name))
        for name, why in REQUIRED_TESTS:
            print("  %-12s %s — %s" % ("시험있음" if name in tests else "시험없음", name, why))

    if problems:
        for p in problems:
            print("[WEBHOOK-CONTRACT] FAIL %s" % p)
        return 1

    print("[WEBHOOK-CONTRACT] PASS 규약 실재 · 닫는 조건 셋 전부 시험 있음 · "
          "상수시간 비교 · 새 인증 경로 0 · 규약 밖 새 발송자 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
