# -*- coding: utf-8 -*-
"""검수 종이 가림 회귀 — **종이 전체에 `gxseed_*` 가 0건인가**
(2026-09-21 · 턴 AB · 차선 S · 대표 결정 ⑩).

캐시 처리: 해당 없음 — HTTP 를 한 번도 안 탄다.

★ 왜 차선 S 가 이 시험을 쥐는가
-------------------------------
서식 파일(`apps/dsm/incident_report.py` · `docx_export.py`)은 **U24 소유**다. 이 파일은
그 코드를 **한 줄도 안 고친다** — 읽고 잰다. 가린 쪽과 재는 쪽이 같은 손이면,
가림이 무너진 날 재는 쪽도 같이 무너진다.

★ 턴 AA 에 U24 가 다섯을 가렸다 [실측 2026-09-21 · 사건 4798 검수본]
--------------------------------------------------------------------
  ① **수신자 메일**   `geumsan@org.kr`               → `(비표시)@org.kr`
  ② **기기 토큰**     `drill:webpush:dc716379fa14`   → 「기기 등록 (식별자 비표시)」
  ③ **판정자**        `… (gxseed_u1_operator)`       → 계정명 없이
  ④ **발행자**        `… (gxseed_u4_official)`       → 계정명 없이
  ⑤ **설치 주소**     `경기도 안양시 만안구 안양천서로 100` → 동까지만

★ 이 시험이 묻는 것은 다섯 함수가 아니라 **종이 전체**다
--------------------------------------------------------
가림은 **함수마다** 걸려 있고, 종이는 **여러 서식**이 만든다. 한 서식에 가림을 걸고
다음 서식을 새로 배선하면 **새 서식에는 가림이 없다** — 그런데 다섯 함수 시험은
그대로 초록이다. 그래서 이 파일은:

  ㉮ 가린 자리 다섯을 **낱낱이** 누르고(분모),
  ㉯ 종이를 만드는 **공개 서식 전부를 열거해**, 훑지 않은 서식이 생기면 **빨개진다**.

  ⚠ ㉯ 가 이 파일의 값이다. 이 턴에 U24 가 **별지 1호 서식**을 새로 배선한다 —
    새 서식이 `incident_report` 에 들어오는 순간 이 파일이 그 이름을 부르며 멈춘다.
    「훑지 않았다」는 **「샘이 없다」가 아니다.** 안 본 것은 회색이지 0 이 아니다.

⚠ **낱말을 세되 무엇을 세는지는 정규식 한 벌에 둔다**(`SEED_PATTERN`). 여기서 세는 것은
  소스가 아니라 **산출된 종이**이므로 주석에 걸릴 일이 없다 — 주석은 종이에 안 나온다.
  (소스를 훑을 때는 AST 로 간다 — `test_law08_qr_anchor.py` · `test_law08_guard_fail_closed.py`.)
"""
from __future__ import annotations

import inspect
import re

from django.test import SimpleTestCase

from apps.dsm import incident_report as form

#: ★ 씨앗 계정의 모양. **실재 계정 이름을 여기에 나열하지 않는다** — 나열하면
#:   「그 다섯 개만」 막는 시험이 되고, 여섯 번째 계정이 생기는 날 조용히 통과한다.
SEED_PATTERN = re.compile(r"gxseed_[A-Za-z0-9_]+")

#: 탐침 계정도 같은 성질이다(턴 AA 에 `gxprobe_e2e` 가 판정자 칸에 사람 이름처럼 찍혔다).
PROBE_PATTERN = re.compile(r"gxprobe_[A-Za-z0-9_]+")


def seeds_in(text: str) -> list[str]:
    """이 종이에 남은 씨앗 계정들. **중복을 지우지 않는다** — 몇 줄에 박혔는지가 사실이다."""
    return SEED_PATTERN.findall(text or "") + PROBE_PATTERN.findall(text or "")


class _Stub:
    """계정명만 있는 사람 하나. **DB 를 안 연다.**

    ★ 이 시험이 노리는 자리가 정확히 여기다: `_display_name` 은 실명이 없으면
      **계정명으로 떨어진다.** 떨어진 값을 종이에 그대로 찍으면 읽는 사람은
      `gxseed_u1_operator` 를 **사람 이름으로** 읽는다.
    """

    def __init__(self, username: str) -> None:
        self.username = username


# ══════════════════════════════════════════════════════════════════════════
# 분모 — 세는 자가 실제로 잡는가
# ══════════════════════════════════════════════════════════════════════════

class TheScannerActuallyCatchesTest(SimpleTestCase):
    """★ 「0건」이 **아무것도 안 본 0** 이 아님을 먼저 고정한다 (D-301)."""

    def test_it_catches_a_planted_seed_account(self) -> None:
        self.assertEqual(seeds_in("판정자 김아무개 (gxseed_u1_operator)"),
                         ["gxseed_u1_operator"])

    def test_it_catches_a_probe_account_too(self) -> None:
        self.assertEqual(seeds_in("발행자 gxprobe_e2e"), ["gxprobe_e2e"])

    def test_it_catches_every_one_of_them_not_just_the_first(self) -> None:
        self.assertEqual(
            len(seeds_in("gxseed_u1_operator gxseed_u4_official gxseed_u5_sysop")), 3)

    def test_an_innocent_paper_is_not_flagged(self) -> None:
        """★ 분모의 반대쪽. 「다 잡는 스캐너」는 스캐너가 아니다."""
        self.assertEqual(seeds_in("판정자 김아무개 · 발행자 재난안전과 · 시드 급수"), [])


# ══════════════════════════════════════════════════════════════════════════
# 가린 칸 다섯 — 낱낱이
# ══════════════════════════════════════════════════════════════════════════

class TheFiveMaskedCellsStillHoldTest(SimpleTestCase):
    """★ 턴 AA 에 U24 가 가린 다섯. **그 다섯이 계속 가려져 있는가.**"""

    # ① 수신자 메일 ──────────────────────────────────────────────────────
    def test_a_recipient_mail_keeps_only_the_domain(self) -> None:
        got = form.mask_recipient("geumsan@org.kr", "email")
        self.assertNotIn("geumsan", got)
        self.assertIn("org.kr", got, "갈래를 지우면 메일로 보낸 것과 기기로 보낸 것이 뭉친다")

    def test_a_recipient_mail_that_is_a_seed_account_leaks_nothing(self) -> None:
        """★ 가장 새기 쉬운 자리 — **계정명이 그대로 메일 아이디인 경우.**"""
        got = form.mask_recipient("gxseed_u1_operator@org.kr", "email")
        self.assertEqual(seeds_in(got), [], f"수신자 칸에 계정명이 남았다: {got!r}")

    # ② 기기 토큰 ────────────────────────────────────────────────────────
    def test_a_device_token_is_not_printed(self) -> None:
        got = form.mask_recipient("drill:webpush:dc716379fa14", "webpush")
        self.assertNotIn("dc716379fa14", got)
        self.assertIn("기기", got)

    def test_a_device_token_that_carries_a_seed_account_leaks_nothing(self) -> None:
        got = form.mask_recipient("drill:webpush:gxseed_u5_sysop", "webpush")
        self.assertEqual(seeds_in(got), [], f"기기 칸에 계정명이 남았다: {got!r}")

    # ③④ 판정자 · 발행자 ────────────────────────────────────────────────
    def test_the_issuer_cell_never_prints_the_login_name(self) -> None:
        """④ 발행자 — `… (gxseed_u4_official)` 가 종이에 박히던 자리."""
        got = form.person_label(_Stub("gxseed_u4_official"))
        self.assertEqual(seeds_in(got), [], f"발행자 칸에 계정명이 남았다: {got!r}")
        self.assertTrue(got.strip(), "빈 칸은 가린 것이 아니다 — 없다고 적어야 한다")

    def test_the_reviewer_cell_never_prints_the_login_name(self) -> None:
        """③ 판정자 — 사람을 못 찾아도 **`#105` 도 계정명도** 안 찍는다."""
        got = form.person_label(_Stub("gxseed_u1_operator"))
        self.assertEqual(seeds_in(got), [], f"판정자 칸에 계정명이 남았다: {got!r}")

    def test_a_probe_account_is_masked_the_same_way(self) -> None:
        """턴 AA 실측 — `gxprobe_e2e` 가 판정자 105 로 종이에 있었다."""
        got = form.person_label(_Stub("gxprobe_e2e"))
        self.assertEqual(seeds_in(got), [], f"탐침 계정이 남았다: {got!r}")

    def test_a_real_name_is_still_printed(self) -> None:
        """★ 분모의 반대쪽 — **가리기만 하는 종이는 종이가 아니다.**

        실명이 있으면 그것은 나가야 한다. 다 가리면 읽는 사람이 누가 판정했는지 모른다.
        """
        person = _Stub("gxseed_u1_operator")
        person.full_name = "김아무개"
        self.assertEqual(form.person_label(person), "김아무개")

    def test_no_user_at_all_says_so_instead_of_guessing(self) -> None:
        self.assertIn("확인 불가", form.person_label(None))

    # ⑤ 설치 주소 ────────────────────────────────────────────────────────
    def test_the_address_stops_at_the_dong(self) -> None:
        got = form.mask_address("경기도 안양시 만안구 안양천서로 100")
        self.assertNotIn("100", got, "번지가 남았다")
        self.assertIn("안양시", got, "다 지우면 어느 지자체 일인지도 사라진다")

    def test_a_status_word_is_not_masked(self) -> None:
        """★ 가릴 것이 없는 칸을 가리면 「주소가 있는데 감췄다」로 읽힌다."""
        for word in ("확인 중", "확인 실패", "주소 변환 사용 안 함"):
            self.assertEqual(form.mask_address(word), word)

    # 각주 ───────────────────────────────────────────────────────────────
    def test_the_paper_says_what_it_hid(self) -> None:
        """★ **가렸다는 사실이 종이에 적혀야 한다.** 말없이 가리면 그것은 누락이다."""
        self.assertTrue(form.MASK_FOOTNOTE.strip())
        self.assertEqual(seeds_in(form.MASK_FOOTNOTE), [])


# ══════════════════════════════════════════════════════════════════════════
# ★ 종이 **전체** — 서식이 늘면 이 파일이 멈춘다
# ══════════════════════════════════════════════════════════════════════════

#: 이 파일이 **실제로 대 본** 서식들. 위 시험들이 이 함수들의 출력 칸을 누른다.
EXERCISED_BUILDERS = {
    "build_html",              # 사건 보고서 1쪽 — 판정자·발행자·수신자·주소가 여기 다 있다
    "build_incident_html",
    "build_situation_html",
    "build_situation_report",
    "build_monthly_html",
    "build_upper_html",
}

#: ★ 아직 **부를 수 없는** 서식과 그 사유. **비어 있는 것이 정상**이다 —
#:   여기에 이름이 늘어나는 것은 「가렸다」가 아니라 「못 쟀다」이고, 회색이다.
NOT_YET_REACHED: dict[str, str] = {}


def _public_builders() -> set[str]:
    """`incident_report` 가 종이를 만드는 **공개 서식** 전부. 손으로 안 적는다."""
    return {
        name for name, obj in vars(form).items()
        if name.startswith("build_") and inspect.isfunction(obj)
        and obj.__module__ == form.__name__
    }


class EveryPaperBuilderIsAccountedForTest(SimpleTestCase):
    """★★ 이 파일의 값이 여기 있다 — **새 서식이 조용히 태어나지 못한다.**

    이 턴에 U24 가 **별지 1호 서식**(`docs/design/GX-FORM_별지1호_v1.0.md`)을 새로
    배선한다. 새 서식은 새 함수로 들어오고, 새 함수는 **가림 함수를 안 부를 수 있다** —
    그런데 위의 「다섯 칸」 시험은 그래도 전부 초록이다. 가림은 함수마다 걸려 있고,
    종이는 서식마다 새로 만들어지기 때문이다.

    그래서 서식 목록 자체를 잠근다. 새 이름이 하나 생기면 **이 시험이 그 이름을 부르며
    멈춘다** — 그리고 멈춘 사람이 그 서식에 가림이 걸렸는지 보게 된다.

    ⚠ 이 시험이 빨개졌다고 **서식을 지우거나 이름을 여기에 적어 넣는 것으로 끄지 말 것.**
      끄는 올바른 방법은 그 서식의 산출물에 씨앗 계정이 0건인지 **재고** 적는 것이다.
    """

    def test_the_denominator_is_not_zero(self) -> None:
        """★ 서식을 하나도 못 찾았으면 그것은 초록이 아니라 **열거기 고장**이다."""
        self.assertGreaterEqual(
            len(_public_builders()), 6,
            "종이를 만드는 공개 서식을 %d개밖에 못 찾았다 — 열거기가 고장났다"
            % len(_public_builders()))

    def test_no_builder_is_unaccounted_for(self) -> None:
        found = _public_builders()
        unknown = sorted(found - EXERCISED_BUILDERS - set(NOT_YET_REACHED))
        self.assertEqual(
            unknown, [],
            "★ 종이를 만드는 **새 서식**이 생겼는데 가림을 아무도 안 쟀다: %s\n"
            "  이 턴의 별지 1호 서식이라면 바로 이 자리다 — 가림 다섯 칸이 그 서식에도 "
            "걸려 있는지 재고, 잰 뒤에 이름을 적는다. 이름만 적어 끄면 그 순간 이 파일은 "
            "아무것도 안 재게 된다" % ", ".join(unknown))

    def test_a_builder_we_listed_has_not_vanished(self) -> None:
        """★ 대장은 줄지 않는다 — 훑던 서식이 사라지면 그것도 사실이다."""
        gone = sorted(EXERCISED_BUILDERS - _public_builders())
        self.assertEqual(
            gone, [],
            "훑던 서식이 사라졌다: %s — 지운 것인지 이름이 바뀐 것인지 적는다" % ", ".join(gone))

    def test_nothing_is_parked_as_unmeasured_without_a_reason(self) -> None:
        for name, why in NOT_YET_REACHED.items():
            self.assertTrue(why.strip(), f"{name} 을 사유 없이 「못 쟀다」로 두었다")


#: 계정명·연락처·주소를 **날것으로** 들고 있는 칸 이름들.
RAW_FIELDS = {"username": "계정명", "recipient_address": "수신자 연락처"}

#: 그 칸을 **읽어도 되는** 함수들 — 가림이 사는 자리다. 여기 밖에서 읽으면
#: 그 값은 가림을 안 거치고 종이로 간다.
MAY_READ_RAW = {"person_label", "_role_display_name", "mask_recipient",
                "_looks_like_device_token", "reviewer_label", "_Stub"}


#: 값을 **가리는** 함수들. 날것을 읽어도 **곧바로 이 안으로 들어가면** 안 새는 것이다.
MASKERS = {"person_label", "reviewer_label", "mask_recipient", "mask_address"}


def _functions_reading(field: str, source: str, *, raw_only: bool = True) -> set[str]:
    """`obj.<field>` 를 읽는 **함수 이름들**. 낱말이 아니라 **AST** 로 본다.

    ⚠ 낱말을 세면 안 되는 이유가 이 파일에 특히 세다 — `incident_report.py` 의
      머리말에는 `gxseed_u1_operator` 와 「계정명」이 **설명으로** 여러 번 나온다.
      낱말을 세면 주석 한 줄에 빨개지고, 그런 시험은 다음 사람이 **주석을 고쳐** 끈다.

    ★ `raw_only` 면 **가림 함수의 인자로 바로 들어가는 읽기는 빼고** 센다.
      [실측 2026-09-21 · 턴 AB · 이 시험이 스스로를 고쳤다] 처음에는 읽기를 전부 셌더니
      `build_html` · `build_situation_html` 이 걸렸다 — 그런데 그 두 자리는
      `mask_recipient(getattr(row, 'recipient_address', ''), channel)` 로
      **이미 가림 안으로 넣고 있었다.** 옳은 코드를 빨갛게 만드는 시험은 오래 못 산다:
      다음 사람이 그 빨강을 끄고, 끄는 김에 **진짜 빨강도 같이 꺼진다.**
      그래서 「읽었는가」가 아니라 **「읽어서 어디로 보냈는가」**를 센다.
    """
    import ast

    tree = ast.parse(source)
    owner: dict[int, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                owner.setdefault(id(child), node.name)

    #: 가림 함수의 **인자 안**에 있는 노드들 — 이것들은 새는 읽기가 아니다.
    inside_mask: set[int] = set()
    if raw_only:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in MASKERS:
                for arg in list(node.args) + [kw.value for kw in node.keywords]:
                    for child in ast.walk(arg):
                        inside_mask.add(id(child))

    def _hit(node) -> None:
        if id(node) not in inside_mask:
            found.add(owner.get(id(node), "<모듈 바깥>"))

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == field:
            _hit(node)
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
            if name in ("getattr", "get") and len(node.args) >= 2:
                arg = node.args[1]
                if isinstance(arg, ast.Constant) and arg.value == field:
                    _hit(node)
    return found


class OnlyTheMaskingFunctionsTouchRawFieldsTest(SimpleTestCase):
    """★★ **별지 1호가 새는지 여기서 본다.**

    [실측 2026-09-21 · 턴 AB] U24 는 별지 1호를 **새 함수로** 배선하지 않았다 —
    `build_situation_html` · `build_situation_report` **안**에 넣었다
    (`SITUATION_TITLE = "재난 상황보고 (별지 제1호)"`). 그래서 위의 「서식 목록 잠금」은
    **안 멈춘다** — 목록이 안 늘었기 때문이다. 목록 잠금만으로는 이 경우를 못 잡는다.

    그래서 자리를 바꿔 본다: **계정명·연락처를 읽는 함수가 누구인가.**
    가림은 `person_label` · `mask_recipient` 안에 산다. 그 밖의 함수가 `.username` 이나
    `.recipient_address` 를 **직접** 읽으면, 그 값은 가림을 **안 거치고** 종이로 간다 —
    서식이 새로 생기든 옛 서식 안에 칸이 늘든 **똑같이** 걸린다.
    """

    @staticmethod
    def _source() -> str:
        path = inspect.getsourcefile(form)
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_the_scanner_catches_a_raw_read(self) -> None:
        """★ 분모. 스캐너가 실제로 잡는다."""
        leak = "def new_form(user):\n    return user.username\n"
        self.assertEqual(_functions_reading("username", leak), {"new_form"})

    def test_the_scanner_catches_a_getattr_read(self) -> None:
        leak = "def new_form(u):\n    return getattr(u, 'username', '')\n"
        self.assertEqual(_functions_reading("username", leak), {"new_form"})

    def test_an_innocent_module_is_not_flagged(self) -> None:
        """★ 분모의 반대쪽 — **주석에 나와도 안 잡는다.**"""
        clean = ("'gxseed_u1_operator 의 username 은 종이에 안 찍는다'\n"
                 "def fine(u):\n    return u.full_name\n")
        self.assertEqual(_functions_reading("username", clean), set())

    def test_a_read_that_goes_straight_into_a_mask_is_not_flagged(self) -> None:
        """★ **옳은 코드를 빨갛게 만들지 않는다** — 그런 빨강은 다음 사람이 끄고,
        끄는 김에 진짜 빨강도 같이 꺼진다.
        """
        wrapped = ("def form(row):\n"
                   "    return mask_recipient(getattr(row, 'recipient_address', ''), 'email')\n")
        self.assertEqual(_functions_reading("recipient_address", wrapped), set())
        #: 그러나 **가림을 안 거치면** 같은 줄이 걸려야 한다(분모의 반대쪽의 반대쪽).
        bare = ("def form(row):\n"
                "    return getattr(row, 'recipient_address', '')\n")
        self.assertEqual(_functions_reading("recipient_address", bare), {"form"})

    def test_no_new_form_reads_a_raw_field(self) -> None:
        src = self._source()
        for field, what in RAW_FIELDS.items():
            readers = _functions_reading(field, src)
            stray = sorted(readers - MAY_READ_RAW)
            self.assertEqual(
                stray, [],
                "★ 가림 밖에서 %s(`%s`)를 직접 읽는 자리가 있다: %s\n"
                "  별지 1호처럼 **옛 서식 안에 칸이 는 경우**가 바로 이 모양이다. "
                "값을 `person_label` · `mask_recipient` 로 넘겨야 종이에 안 새어 나간다"
                % (what, field, ", ".join(stray)))

    def test_the_denominator_is_not_zero(self) -> None:
        """★ 읽는 자리를 하나도 못 찾았으면 그것은 초록이 아니라 **스캐너 고장**이다."""
        src = self._source()
        self.assertTrue(
            _functions_reading("username", src),
            "`username` 을 읽는 함수를 하나도 못 찾았다 — 가림이 사는 자리조차 "
            "안 보인다면 이 시험의 「0건」은 아무것도 안 본 0 이다")


class TheMaskingCodeIsNotMineTest(SimpleTestCase):
    """★ 소유표 — `incident_report.py` · `docx_export.py` 는 **U24 소유**다.

    이 시험 파일은 그 두 파일을 **읽기만** 한다. 여기서 확인하는 것은
    「가림 함수가 아직 그 이름으로 거기 있는가」뿐이다 — 이름이 바뀌면 이 파일의
    나머지가 통째로 거짓 초록이 되므로, 그 사실을 먼저 멈춰서 알린다.
    """

    def test_the_five_masking_entry_points_still_exist(self) -> None:
        for name in ("mask_recipient", "mask_address", "person_label",
                     "reviewer_label", "MASK_FOOTNOTE"):
            self.assertTrue(
                hasattr(form, name),
                f"가림 자리 «{name}» 가 사라졌다 — 이 파일의 나머지 초록은 거짓이다")
