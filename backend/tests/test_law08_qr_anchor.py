# -*- coding: utf-8 -*-
"""LAW-08 QR 앵커 회귀 — **설계 v1.0 의 「안 하는 것」을 코드가 계속 안 하는가**
(2026-09-21 · 턴 AB · 차선 S).

캐시 처리: 해당 없음 — HTTP 를 한 번도 안 탄다. DB 도 안 탄다(전부 `SimpleTestCase`).

★ 이 파일이 재는 것은 「QR 이 예쁘게 나오는가」가 **아니다.**
  설계 v1.0 이 **하지 않기로 못 박은 것들**이 코드에서 계속 안 일어나는가다.
  QR 의 가치는 담은 것이 아니라 **안 담은 것**에 있다 — 담은 것은 다음 사람이 늘 늘리고
  싶어 하고, 늘리는 순간 종이는 기계 안으로 돌아간다.

  그래서 갈래 여섯을 누른다:

    ① **payload 에 URL 이 0** 이다(설계 §1 · §7②). 사유 둘 — **원이 닫힌다**(뚫린 기계가
       QR 도 찍고 「맞습니다」도 답한다) · **종이는 10년 뒤에 읽힌다**(그때 도메인은 없다).
    ② **`cmp.` 와 `ref.` 가 갈라져 있고, 대조기는 `ref.` 를 안 읽는다**(머리 해시 함정).
    ③ 상태는 **셋**이고 **못 읽음이 「같음」으로 접히지 않는다**(설계 §4-3 · §5).
    ④ **QR 과 16자가 다르면 그것이 사건**이다(설계 §5) — 「QR 이 고장났다」가 아니다.
    ⑤ **QR 과 사람 16자가 한 덩어리로만** 나온다 — 하나만 내는 갈래가 없다(§7④).
    ⑥ **바깥으로 한 바이트도 안 보낸다**(§7③) · **진입점이 하나**다(§7①).

⚠ ⑥ 는 **낱말이 아니라 AST 로** 훑는다. 이 모듈의 머리말에는 `http`·`www.` 가
  **설명으로** 여러 번 나온다(`URL_MARKERS`). 낱말을 세면 주석 한 줄에 빨개지고,
  그런 시험은 다음 사람이 **주석을 고쳐서** 끈다.

⚠ **운영 표에 한 행도 안 쓴다.** 이 파일은 연결을 한 번도 안 연다.
"""
from __future__ import annotations

import ast
import inspect
from datetime import date
from pathlib import Path

from django.test import SimpleTestCase

from common import paper_anchor_qr as qr

#: ★ **실측값이다**(차선 S · `verify_evidence_chain.py --anchor 2026-09-20 --qr`).
#:   2026-09-20 앵커는 턴 Z 오전 · 턴 Z 오후 · 턴 AA · 턴 AB **네 번 다 같았다.**
ANCHOR_0920 = "014cf31d3e94d46b03175fe5ceb981ec73a6f4913fec3eafd1d5438f42b57caa"
ANCHOR_0919 = "2d4e4980156a6ad51dfd017ea9357263a4365a49ecf87b92525e7f07a930c04c"

#: ★ 같은 앵커를 잰 **네 번의 머리 해시.** 네 값이 다 다르다 — 이것이 `ref.` 구역이
#:   형식 안에 있어야 하는 이유의 전부다. 대조 칸에 두면 **매일 빨강**이 나고,
#:   매일 나는 빨강 옆에서는 **진짜 빨강도 안 보인다.**
HEADS_SEEN = (
    "2a10f5d596474534" + "0" * 48,     # 턴 Z 오전
    "d90b5f405574a34e" + "0" * 48,     # 턴 Z 오후
    "12aa35fc3568f56d" + "0" * 48,     # 턴 AA
    "2d8010ad9490fe2d" + "0" * 48,     # 턴 AB (이 턴 실측)
)


def _payload(**over) -> str:
    kwargs = dict(
        for_day=date(2026, 9, 20), anchor=ANCHOR_0920,
        prev_day=date(2026, 9, 19), prev_anchor=ANCHOR_0919,
        rows=3999, chain=3710, gaps=23, head=HEADS_SEEN[3], exit_code=0)
    kwargs.update(over)
    return qr.build_payload(**kwargs)


# ══════════════════════════════════════════════════════════════════════════
# ① URL 을 안 담는다 — **원이 닫히지 않게**
# ══════════════════════════════════════════════════════════════════════════

class ThePayloadCarriesNoLinkTest(SimpleTestCase):
    """★ 설계 §1 — **검증 URL 을 QR 에 담지 않는다.**

    담으면 원이 닫힌다: 체인을 통째로 재계산한 기계가 QR 도 찍고 그 URL 에 「맞습니다」도
    답한다. 그리고 종이는 10년 뒤에 읽히는데 **그때 그 도메인은 없다.**
    """

    def test_a_built_payload_has_no_url_scheme_at_all(self) -> None:
        low = _payload().lower()
        for marker in qr.URL_MARKERS:
            self.assertNotIn(
                marker, low,
                f"payload 에 «{marker}» 가 있다 — 카메라가 「열기」를 권하는 순간 "
                f"탭 한 번이 대조를 대신한다(설계 §1-2)")

    def test_a_url_smuggled_into_a_ref_cell_is_refused(self) -> None:
        """★ 분모. 검사기가 **실제로 잡는다**는 것을 먼저 고정한다.

        가장 새기 쉬운 자리는 `ref.by` 다 — 사람이 적는 칸이라 무엇이든 들어온다.
        """
        with self.assertRaises(qr.PayloadError):
            _payload(by="https://gx.example.org/verify")

    def test_a_bare_domain_is_refused_too(self) -> None:
        with self.assertRaises(qr.PayloadError):
            _payload(by="www.example.org")

    def test_an_innocent_ref_by_is_not_refused(self) -> None:
        """★ 분모의 반대쪽. 「다 막는 검사기」는 검사기가 아니다."""
        self.assertIn("ref.by=dangbeon-3", _payload(by="dangbeon-3"))

    def test_the_payload_is_plain_ascii(self) -> None:
        """10년 뒤 아무 리더로도 읽혀야 한다(설계 §2 · §4-④)."""
        self.assertTrue(_payload().isascii())

    def test_the_first_line_names_the_format(self) -> None:
        self.assertEqual(_payload().splitlines()[0], qr.VERSION_LINE)


# ══════════════════════════════════════════════════════════════════════════
# ② `cmp.` 와 `ref.` — **머리 해시 함정을 형식에 박았다**
# ══════════════════════════════════════════════════════════════════════════

class TheHeadHashIsNeverACompareCellTest(SimpleTestCase):
    """★ 실측이 이 설계를 정했다: 같은 날 앵커를 **네 번** 떴는데
    앵커는 네 번 다 같고 **머리 해시는 네 번 다 달랐다.**
    """

    def test_the_four_measured_heads_really_are_all_different(self) -> None:
        """★ 분모. 이 시험의 전제가 아직 사실인지 먼저 누른다."""
        self.assertEqual(len(set(HEADS_SEEN)), 4)

    def test_the_anchor_sits_in_cmp_and_the_head_sits_in_ref(self) -> None:
        p = qr.parse_payload(_payload())
        self.assertIn("anchor", p.cmp)
        self.assertNotIn("head", p.cmp)
        self.assertIn("head", p.ref)
        self.assertNotIn("anchor", p.ref)

    def test_a_different_head_never_makes_a_difference(self) -> None:
        """★ 이 파일에서 가장 중요한 한 건.

        머리 해시만 다른 네 payload 를 같은 16자에 대 본다. **네 번 다 「같음」**이어야
        한다. 하나라도 「다름」이 나면 이 절차는 **매일 빨강**을 내고, 그 순간 다음 사람은
        대조 칸을 끄거나 매일 「같음」에 서명하기 시작한다.
        """
        want = ANCHOR_0920[:16]
        for head in HEADS_SEEN:
            state, why = qr.compare_with_human_cell(_payload(head=head), want)
            self.assertEqual(state, qr.STATE_SAME, f"head={head[:16]} 에서 {state} — {why}")

    def test_the_comparator_does_not_read_ref_lines_at_all(self) -> None:
        """`ref.` 줄을 통째로 쓰레기로 채워도 대조 결과가 안 바뀐다."""
        junk = _payload() + "\nref.head=zzzz\nref.exit=99\nref.nonsense=x"
        state, _ = qr.compare_with_human_cell(junk, ANCHOR_0920[:16])
        self.assertEqual(state, qr.STATE_SAME)

    def test_the_human_cell_is_the_front_sixteen_of_the_anchor(self) -> None:
        self.assertEqual(qr.human_cell(ANCHOR_0920), "014cf31d3e94d46b")
        self.assertEqual(len(qr.human_cell(ANCHOR_0920)), qr.HUMAN_LEN)

    def test_a_short_value_is_never_silently_trimmed(self) -> None:
        """★ 16자를 **잘라 만들지 않는다.** 자르면 틀린 값이 종이에 박힌다."""
        with self.assertRaises(qr.PayloadError):
            qr.human_cell("014cf31d3e94d46b")


# ══════════════════════════════════════════════════════════════════════════
# ③④ 상태 셋 — **못 읽음을 「같음」으로 접지 않는다** · **다르면 그것이 사건**
# ══════════════════════════════════════════════════════════════════════════

class ThreeStatesNotTwoTest(SimpleTestCase):
    """★ 설계 §4-3 · §5 — 상태는 **같음 / 다름 / 못 읽음** 셋이다.

    둘로 접는 순간 「못 읽음」은 반드시 **「같음」쪽으로** 접힌다(빨강을 만들고 싶은
    사람은 없으므로). 그러면 리더가 고장 난 날부터 이 절차는 **아무것도 안 재게 된다.**
    """

    def test_there_are_exactly_three_states_and_they_are_distinct(self) -> None:
        self.assertEqual(len(set(qr.STATES)), 3)

    def test_a_missing_qr_is_unreadable_not_same(self) -> None:
        for bad in (None, "", "   "):
            state, why = qr.compare_with_human_cell(bad, ANCHOR_0920[:16])
            self.assertEqual(state, qr.STATE_UNREADABLE, f"{bad!r} → {state}")
            self.assertNotEqual(state, qr.STATE_SAME, why)

    def test_a_smudged_qr_is_unreadable_not_same(self) -> None:
        state, _ = qr.compare_with_human_cell("GX-LAW08 v1\ncmp.anchor=014cf3", ANCHOR_0920[:16])
        self.assertEqual(state, qr.STATE_UNREADABLE)

    def test_a_wrong_format_version_is_unreadable_not_same(self) -> None:
        state, _ = qr.compare_with_human_cell(
            _payload().replace(qr.VERSION_LINE, "GX-LAW08 v9"), ANCHOR_0920[:16])
        self.assertEqual(state, qr.STATE_UNREADABLE)

    def test_a_blank_human_cell_is_unreadable_not_same(self) -> None:
        """종이 쪽이 비어 있어도 **대조가 성립한 척하지 않는다.**"""
        state, _ = qr.compare_with_human_cell(_payload(), "")
        self.assertEqual(state, qr.STATE_UNREADABLE)

    def test_a_matching_pair_is_same(self) -> None:
        state, _ = qr.compare_with_human_cell(_payload(), ANCHOR_0920[:16])
        self.assertEqual(state, qr.STATE_SAME)

    def test_qr_against_a_different_sixteen_is_an_incident(self) -> None:
        """★ **「QR 과 16자가 다르면 그것이 사건이다」** — 「QR 이 고장났다」가 아니다."""
        state, why = qr.compare_with_human_cell(_payload(), "dead" * 4)
        self.assertEqual(state, qr.STATE_DIFFERENT)
        self.assertIn("사건", why)
        self.assertIn("014cf31d3e94d46b", why)
        self.assertIn("deaddeaddeaddead", why)

    def test_the_case_of_the_human_cell_does_not_matter(self) -> None:
        state, _ = qr.compare_with_human_cell(_payload(), ANCHOR_0920[:16].upper())
        self.assertEqual(state, qr.STATE_SAME)


class YesterdaysPaperIsTheAnvilTest(SimpleTestCase):
    """★ 설계 §3 ① — **매일 만나는 자리.** 저장소는 어제 종이를 못 고친다."""

    def _yesterday(self) -> str:
        return qr.build_payload(
            for_day=date(2026, 9, 19), anchor=ANCHOR_0919,
            prev_day=date(2026, 9, 18), prev_anchor="ab" * 32,
            rows=3500, chain=3200, gaps=23, head=HEADS_SEEN[0])

    def test_today_remembers_yesterday(self) -> None:
        state, _ = qr.compare_to_yesterday(_payload(), self._yesterday())
        self.assertEqual(state, qr.STATE_SAME)

    def test_a_rewritten_yesterday_is_caught(self) -> None:
        """체인을 통째로 재계산한 기계도 **어제 종이는 못 속인다.**"""
        forged = _payload(prev_anchor="cd" * 32)
        state, why = qr.compare_to_yesterday(forged, self._yesterday())
        self.assertEqual(state, qr.STATE_DIFFERENT)
        self.assertIn("사건", why)

    def test_one_unreadable_side_is_unreadable_not_same(self) -> None:
        state, _ = qr.compare_to_yesterday(_payload(), None)
        self.assertEqual(state, qr.STATE_UNREADABLE)

    def test_a_skipped_day_cannot_even_be_built(self) -> None:
        """★ 연휴에 줄을 몰아 적다 하루를 건너뛰면 **여기서 걸린다**(설계 §2)."""
        with self.assertRaises(qr.PayloadError):
            _payload(prev_day=date(2026, 9, 17))

    def test_a_skipped_day_read_back_is_unreadable(self) -> None:
        broken = _payload().replace("cmp.prev=2026-09-19", "cmp.prev=2026-09-10")
        state, _ = qr.compare_with_human_cell(broken, ANCHOR_0920[:16])
        self.assertEqual(state, qr.STATE_UNREADABLE)


# ══════════════════════════════════════════════════════════════════════════
# ⑤ QR 과 사람 16자는 **반드시 나란히**
# ══════════════════════════════════════════════════════════════════════════

class TheQrIsWatchedByTheSixteenTest(SimpleTestCase):
    """★ 설계 §2 · §7④ — QR 만 있는 종이는 **QR 이 거짓말해도 아무도 모른다.**"""

    def test_the_printable_block_carries_both(self) -> None:
        block = qr.printable_block(_payload())
        self.assertIn("014cf31d3e94d46b", block)
        self.assertIn(ANCHOR_0920, block)          # QR 안 평문도 같은 종이에

    def test_the_block_names_the_three_states(self) -> None:
        block = qr.printable_block(_payload())
        for state in qr.STATES:
            self.assertIn(state, block)

    def test_the_block_says_the_ref_lines_are_not_compared(self) -> None:
        self.assertIn("`ref.`", qr.printable_block(_payload()))

    def test_a_failed_drawing_still_yields_the_sixteen(self) -> None:
        """★ 설계 §5 — **QR 이 없으면 대조가 불가능해지는 설계는 실패다.**

        그림이 안 나와도 종이는 나가고, 16자는 그대로 있고, 그 줄은 **유효하다.**
        """
        block = qr.printable_block(_payload(), qr="")
        self.assertIn("014cf31d3e94d46b", block)
        self.assertIn("QR 없음", block)

    def test_a_broken_payload_is_never_printed(self) -> None:
        with self.assertRaises(qr.PayloadError):
            qr.printable_block("GX-LAW08 v1\ncmp.anchor=nope")

    def test_drawing_never_raises(self) -> None:
        """★ 설계 §7⑥ — QR 실패는 **회색이지 빨강이 아니다.** 예외로 새 나가지 않는다."""
        self.assertIsNone(qr.render_qr_ascii(None))          # type: ignore[arg-type]

    def test_a_drawing_is_a_square_of_blocks_when_the_library_is_here(self) -> None:
        drawn = qr.render_qr_ascii(_payload())
        if drawn is None:
            self.skipTest("이 자리에 qrcode 가 없다 — 회색이다(초록으로 세지 않는다)")
        rows = drawn.splitlines()
        self.assertGreater(len(rows), 10)
        self.assertEqual(len(set(len(r) for r in rows)), 1, "줄 길이가 들쭉날쭉하다")


# ══════════════════════════════════════════════════════════════════════════
# ⑥ 바깥으로 안 보낸다 · 진입점은 하나 — **낱말이 아니라 AST 로**
# ══════════════════════════════════════════════════════════════════════════

#: 값을 밖으로 옮길 수 있는 것들. 하나라도 import 하면 **오프라인 생성이 아니다**.
NETWORK_ROOTS = {"requests", "urllib", "urllib3", "http", "httpx", "socket",
                 "ftplib", "smtplib", "aiohttp", "telnetlib", "xmlrpc"}

#: 이 모듈을 **불러도 되는 자리.** 여기 밖에서 부르면 진입점이 둘이 된다(설계 §7①).
ALLOWED_CALLERS = {"scripts/verify_evidence_chain.py",
                   "backend/tests/test_law08_qr_anchor.py"}

#: 훑는 범위. **분모를 손으로 적지 않는다** — 아래 시험이 실제로 센 수를 누른다.
SCAN_DIRS = ("backend/common", "backend/apps", "backend/kernels", "backend/config",
             "backend/dashboard", "backend/stream_monitors", "backend/surveillance",
             "scripts")


def _repo_root() -> Path | None:
    """저장소 뿌리. **찾은 것만 쓴다 — 못 찾으면 None(회색)** 이고 0 이 아니다.

    ⚠ [실측 2026-09-21 · 턴 AB] 여기서 한 번 틀렸다. `parents[2]` 로 잡으면 호스트에서는
      맞지만 **gx-shell 안에서는 `/` 가 된다**(backend 가 `/app` 에 통째로 붙는다).
      그러면 훑을 파일이 0개가 되고, 「우회로 0건」이 **아무것도 안 본 0** 이 된다.
      **분모 0 인 초록은 초록이 아니다** — 그래서 아래 시험이 분모를 따로 누른다.
      컨테이너에는 저장소가 `/repo` 로도 붙어 있다(`/repo/backend` · `/repo/scripts`).
    """
    here = Path(__file__).resolve()
    candidates = list(here.parents) + [Path("/repo")]
    for cand in candidates:
        if (cand / "backend" / "common").is_dir() and (cand / "scripts").is_dir():
            return cand
    return None


ROOT = _repo_root()


def imports_network(source: str) -> list[str]:
    """이 소스가 **바깥으로 나가는 문**을 여는가. 낱말이 아니라 구문을 본다."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in NETWORK_ROOTS:
                    found.append(f"import {alias.name} @{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and str(node.module or "").split(".")[0] in NETWORK_ROOTS:
                found.append(f"from {node.module} import … @{node.lineno}")
    return found


def imports_the_qr_module(source: str) -> list[str]:
    """이 소스가 `paper_anchor_qr` 를 부르는가. **AST 로** 본다.

    ⚠ 낱말을 세면 안 되는 이유가 여기 특히 세다 — 설계 문서 이름과 모듈 이름이
      주석·독스트링에 수없이 나온다. 낱말 세기는 **주석 한 줄로 켜지고 꺼진다.**
    """
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[-1] == "paper_anchor_qr":
                    found.append(f"import {alias.name} @{node.lineno}")
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "paper_anchor_qr":
                    found.append(f"from {node.module} import {alias.name} @{node.lineno}")
    return found


def _python_files() -> list[Path]:
    if ROOT is None:
        return []
    out: list[Path] = []
    for rel in SCAN_DIRS:
        base = ROOT / rel
        if base.is_dir():
            out.extend(p for p in base.rglob("*.py") if "migrations" not in p.parts)
    return out


class NothingLeavesThisMachineTest(SimpleTestCase):
    """★ 설계 §7③ — **외부 QR 생성 API 에 앵커를 한 번도 안 보낸다.**

    보내는 순간 그것은 편의가 아니라 **유출**이다. 그리고 유출은 되돌릴 수 없다 —
    받은 쪽이 지웠다고 말해도 그것은 우리가 관측할 수 없는 사실이다.
    """

    def test_the_scanner_catches_an_outbound_door(self) -> None:
        """★ 분모. 스캐너가 실제로 잡는다."""
        self.assertEqual(len(imports_network("import requests\nx = 1\n")), 1)
        self.assertEqual(len(imports_network("from urllib.request import urlopen\n")), 1)

    def test_an_innocent_module_is_not_flagged(self) -> None:
        """★ 분모의 반대쪽. 「다 잡는 스캐너」는 스캐너가 아니다."""
        self.assertEqual(
            imports_network("'requests 로 보내지 않는다'\nimport hashlib\n"), [])

    def test_the_qr_module_opens_no_outbound_door(self) -> None:
        src = Path(inspect.getsourcefile(qr)).read_text(encoding="utf-8")
        self.assertEqual(
            imports_network(src), [],
            "paper_anchor_qr 가 바깥으로 나가는 문을 열었다 — 앵커 값을 남의 서버에 "
            "보내는 순간 그것은 편의가 아니라 유출이다(설계 §7③)")


class TheEntryPointIsOneTest(SimpleTestCase):
    """★ 설계 §7① · §6-4 — **사람이 부른 호출 1회 = QR 1장.**

    크론이 매일 QR 을 찍어 종이를 만들면 그것이 바로 자기증명이고, 자기증명은
    아무것도 증명하지 않는다. 그래서 **웹 라우트·스케줄러에서 닿는 문을 만들지 않는다.**
    """

    def test_the_scanner_catches_a_caller(self) -> None:
        """★ 분모."""
        self.assertEqual(
            len(imports_the_qr_module("from common import paper_anchor_qr\n")), 1)
        self.assertEqual(
            len(imports_the_qr_module("import common.paper_anchor_qr\n")), 1)

    def test_an_innocent_module_is_not_flagged(self) -> None:
        """★ 분모의 반대쪽 — **주석에 이름이 나와도 안 잡는다.**"""
        self.assertEqual(
            imports_the_qr_module("'paper_anchor_qr 는 여기서 안 쓴다'\nimport json\n"), [])

    def test_the_root_was_actually_found(self) -> None:
        """★ 뿌리를 못 찾았으면 **회색**이다. 0 을 초록으로 읽지 않는다."""
        self.assertIsNotNone(
            ROOT, "저장소 뿌리를 못 찾았다 — 훑을 것이 0개다. 0 은 「우회로 없음」이 아니다")

    def test_the_denominator_is_not_written_by_hand(self) -> None:
        """★ 분모 0 인 초록은 초록이 아니다 — 실제로 훑은 파일 수를 누른다."""
        n = len(_python_files())
        self.assertGreater(
            n, 100, f"훑은 파일이 {n}개다 — 이 수로 낸 「0건」은 아무것도 안 본 0 이다")

    def test_only_the_one_judge_calls_the_qr_module(self) -> None:
        callers: dict[str, list[str]] = {}
        for path in _python_files():
            try:
                src = path.read_text(encoding="utf-8")
                hits = imports_the_qr_module(src)
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            if hits:
                callers[path.relative_to(ROOT).as_posix()] = hits
        unexpected = {k: v for k, v in callers.items() if k not in ALLOWED_CALLERS}
        self.assertEqual(
            unexpected, {},
            "QR 진입점이 둘 이상이다 — 사람이 부르지 않는 자리에서 QR 이 나오면 "
            "그것이 바로 자기증명이다(설계 §7① · §6-4)")
        self.assertIn(
            "scripts/verify_evidence_chain.py", callers,
            "진입점이 **하나도 없다** — 구현이 배선에서 빠졌다. 0 은 초록이 아니다")

    def test_no_url_module_nor_view_reaches_the_qr_module(self) -> None:
        """웹 라우트에서 닿으면 스캔이 서버에 남고, 남는 순간 기계가 흉내 낼 수 있다."""
        self.assertIsNotNone(ROOT, "저장소 뿌리를 못 찾았다 — 회색이다")
        for path in _python_files():
            name = path.name
            if name not in ("urls.py", "views.py", "api.py", "tasks.py", "celery.py"):
                continue
            try:
                hits = imports_the_qr_module(path.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            self.assertEqual(hits, [], f"{path.relative_to(ROOT).as_posix()} 가 QR 을 부른다")
