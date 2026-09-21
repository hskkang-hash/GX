#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P-208 U24 ② — **파기·집행 문이 U4 에게 닫혀 있는가 · 그리고 그것을 재는 겹이 둘인가**
(2026-09-20 · 턴 Y · 차선 U24).

    시험 파일은 지워질 수 있다. **게이트는 대장에 이름으로 남는다.**

무엇이 이 파일을 만들게 했나 — **실제로 있었던 사고**
-----------------------------------------------------
턴 W(2026-09-19 · 차선 U24)에서 LAW-07′ 다섯 문을 U4 에게 열 때, 문지기 이름
`_admin` 을 **한 번에 치환**했다. 그 한 번이 `law_api.py` 의 `_admin` 전부를 바꿨고,
**청구 면 다섯이 아니라 파기·집행 문까지** U4 에게 열렸다. 그 자리에서 되돌렸지만,
커밋됐으면 읽기 전용 지자체 담당관이 「보관 기간이 지난 영상 지우기」 면을 보게 됐다.

    넓히는 작업에서 **일괄 치환은 도구가 아니라 사고**다.

★★ 그리고 턴 X 에 그 사고를 **그대로 재현해 보니 더 나쁜 것이 나왔다**
-----------------------------------------------------------------------
치환을 넣고 눌렀더니 **POST 둘은 그대로 403** 이었다:

    GET  /law/purge/tenants    → 라우트의 `_admin` 이 막는다      ← 치환하면 **200 으로 샌다**
    POST /law/purge            → **미들웨어**(P-119 읽기 전용 쓰기 금지)가 먼저 막는다
                                  ← 치환해도 **403 그대로**. `_admin` 까지 가지도 않는다

즉 **쓰기 문만 재는 시험은 이 사고를 못 잡고, 관문이 사고를 덮는다.** 한 겹만 재고
「막힌다」고 적으면 다른 겹이 열려 있어도 아무도 모른다. 그래서 두 겹을 **갈라서** 잰다:

    ① `GET` 두 문으로 `_admin` 을 **직접** 잰다 (읽기는 관문이 안 본다)
    ② 쓰기 둘은 `READONLY_ROLE_GATE_ENABLED=False` 로 **관문을 끄고** 한 번 더 누른다

이 판정기가 **두 가지**를 잰다 — 섞지 않는다
--------------------------------------------
  ① **제품**  `law_api.py` 를 AST 로 읽어 「어느 문이 어느 문지기를 쓰는가」를 본다.
     일괄 치환이 나면 **여기가 먼저** 빨개지고, **어느 문이 옮겨 갔는지 이름으로** 난다.
  ② **시험의 겹**  두 겹을 재는 갈래가 아직 그 시험 파일에 서 있는가.
     겹 하나가 조용히 지워지면 남은 쪽은 여전히 초록이고, 그 초록이 사고를 덮는다.

  두 면을 **따로 센다.** 한 수로 합치면 「시험이 통째로 사라졌는데 제품이 멀쩡해서
  초록」이 가능해진다 — D-301 이 금지한 바로 그 모양이다.

★ **이름으로 박는다** (D-285 ②)
--------------------------------
「`_admin` 문은 넷이다」처럼 **개수로** 박으면, 하나가 지워질 때 **새 문이 들어올 자리**
가 생긴다(수는 그대로니 초록이다). 그래서 이 파일의 표는 전부 **메서드 + 경로 이름**
이고, 판정은 「`_admin` 을 쓰는 라우트의 **이름 집합**」을 통째로 대 보는 것이다.

★ **grep 이 아니라 AST 로 읽는다**
----------------------------------
주석과 문자열에 적힌 `_admin` 은 AST 에 없다. 이 파일의 머리말에도 `_admin` 이
수십 번 나오고, grep 으로 세는 판정기는 자기 머리말을 세고 초록을 낸다.

★ 살아 있는 것을 재지 않는다 — 그래서 **회색이 없다**
-----------------------------------------------------
이 게이트는 자격증명도 서버도 쓰지 않는다. 저장소 파일 바이트만 읽으므로 「못 쟀다」가
날 자리는 **파일이 없을 때**뿐이고, 그때는 회색이 아니라 **빨강**이다 — 재야 할 파일이
없는 것도 사실이고, 그 사실은 초록이 아니다.

  ⚠ 그 대신 이 게이트는 「지금 U4 가 정말 403 을 받는가」를 **못 본다.** 그것은
    `backend/tests/test_u24_admin_doors_stay_403.py` 가 HTTP 로 눌러서 잰다(D-210).
    이 파일은 **그 시험이 여전히 두 겹을 재는지**를 지킨다. 둘은 다른 질문이다.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAW_API = ROOT / "backend" / "apps" / "dsm" / "law_api.py"
DOORS_TEST = ROOT / "backend" / "tests" / "test_u24_admin_doors_stay_403.py"

TAG = "[P-208]"
EXIT_OK, EXIT_RED = 0, 1

MOUNT = "/api/dsm"

#: ★ 문지기 `_admin` 이 지키는 문 — **이름으로**. 턴 W 의 일괄 치환이 넓힐 뻔한 집합.
ADMIN_DOORS = {
    ("GET", "/api/dsm/law/purge/tenants"): "파기 대상 목록",
    ("POST", "/api/dsm/law/purge"): "파기 집행",
    ("GET", "/api/dsm/law/purge/history"): "파기 기록",
    ("POST", "/api/dsm/law/retention/sweep"): "보존기간 집행",
}
#: ★ 문지기 `_privacy_officer` 가 지키는 문 — **넓힌 쪽**. 같이 재야 「요청만큼만」이 선다.
OFFICER_DOORS = {
    ("GET", "/api/dsm/law/privacy-requests"): "청구 목록",
    ("POST", "/api/dsm/law/privacy-requests"): "청구 접수",
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}"): "청구 상세",
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}/masked"): "마스킹본",
    ("POST", "/api/dsm/law/privacy-requests/{receipt_no}/reply"): "청구 회신",
}

GUARD_ADMIN = "_admin"
GUARD_OFFICER = "_privacy_officer"

#: ★ 시험 파일에 **서 있어야 하는 갈래 넷**. 이름이 아니라 **하는 일**로 적는다.
#:   (열쇠, 사람이 읽는 말, 그 갈래가 없으면 무엇이 안 재어지는가)
TEST_BRANCHES = (
    ("겹① 읽기 문으로 문지기 직접",
     "READ_DOORS 를 눌러 라우트의 `_admin` 을 직접 잰다",
     "치환이 나도 관문이 덮어 아무도 못 본다"),
    ("겹② 관문 끄고 쓰기 문",
     "READONLY_ROLE_GATE_ENABLED=False 로 관문을 끄고 그 아래를 본다",
     "관문이 꺼진 날 파기 문이 열려 있어도 초록이다"),
    ("분모 U5",
     "같은 네 문을 운영자로 눌러 **문이 살아 있음**을 본다",
     "서버가 통째로 고장 나도 「전부 403」이라 초록이다"),
    ("넓힌 쪽",
     "청구 다섯 문이 U4 에게 열려 있음을 같은 파일에서 본다",
     "LAW-07′ 를 통째로 되돌려 놔도 초록이다"),
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. 제품 — `law_api.py` 의 문지기 배치를 AST 로 읽는다
# ═══════════════════════════════════════════════════════════════════════════
def guard_table(source: str) -> dict:
    """`{문지기 이름: {(메서드, 경로), …}}`. 본문이 **부르는** 이름만 센다."""
    table: dict = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        doors = _routes_of(node)
        if not doors:
            continue
        for called in _guards_called(node):
            table.setdefault(called, set()).update(doors)
    return table


def _routes_of(fn) -> set:
    out = set()
    for dec in fn.decorator_list:
        if not isinstance(dec, ast.Call):
            continue
        f = dec.func
        if not (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id == "route"):
            continue
        if not dec.args or not isinstance(dec.args[0], ast.Constant):
            continue
        out.add((f.attr.upper(), MOUNT + str(dec.args[0].value)))
    return out


def _guards_called(fn) -> set:
    wanted = {GUARD_ADMIN, GUARD_OFFICER}
    return {n.func.id for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id in wanted}


def judge_product(source: str) -> list:
    """제품 면의 어긋남. **어느 문이 옮겨 갔는지 이름으로** 적는다."""
    table = guard_table(source)
    bad = []
    got_admin = table.get(GUARD_ADMIN, set())
    want_admin = set(ADMIN_DOORS)
    if got_admin != want_admin:
        bad.append(
            "`%s` 이 지키는 문의 **이름 집합**이 달라졌다 — 빠진 문=%s · 새로 든 문=%s"
            % (GUARD_ADMIN,
               sorted(ADMIN_DOORS[d] for d in want_admin - got_admin),
               sorted("%s %s" % d for d in got_admin - want_admin)))
    got_officer = table.get(GUARD_OFFICER, set())
    want_officer = set(OFFICER_DOORS)
    if got_officer != want_officer:
        bad.append(
            "`%s` 이 지키는 문의 이름 집합이 달라졌다 — 빠진 문=%s · 새로 든 문=%s"
            % (GUARD_OFFICER,
               sorted(OFFICER_DOORS[d] for d in want_officer - got_officer),
               sorted("%s %s" % d for d in got_officer - want_officer)))
    both = got_admin & got_officer
    if both:
        bad.append("한 문에 문지기 둘이 섰다 — 어느 쪽이 정본인지 아무도 모른다: %s"
                   % sorted("%s %s" % d for d in both))
    crossed = got_officer & want_admin
    if crossed:
        bad.append("★ 청구 면 문지기가 **파기·집행 문**에 걸렸다 — **그것이 턴 W 의 그 사고다**: %s"
                   % sorted(ADMIN_DOORS[d] for d in crossed))
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# 2. 시험의 겹 — 갈래 넷이 아직 서 있는가
# ═══════════════════════════════════════════════════════════════════════════
def present_branches(source: str) -> dict:
    """갈래마다 「서 있나」. **본문**을 본다 — 주석에 적힌 말은 갈래가 아니다."""
    tree = ast.parse(source)
    #: 주석·독스트링을 빼고 **코드로 남은 글자**만 본다. AST 를 되돌려 적으면
    #: 주석은 사라지고 문자열 리터럴은 남으므로, 독스트링도 따로 지운다.
    code = _code_only(tree)
    return {
        "겹① 읽기 문으로 문지기 직접":
            "ADMIN_READ_DOORS" in code and "ADMIN_DENIAL_SAYS" in code,
        "겹② 관문 끄고 쓰기 문":
            "READONLY_ROLE_GATE_ENABLED" in code and "False" in code
            and "ADMIN_WRITE_DOORS" in code,
        "분모 U5": "u5" in code,
        "넓힌 쪽": "privacy" in code.lower() or "door_list" in code,
    }


def _code_only(tree) -> str:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                #: 독스트링을 **지우지 않고** 빈 상수로 바꾼다 — 지우면 빈 본문이 된다.
                body[0].value.value = ""
    return ast.unparse(tree)


def judge_test(source: str) -> list:
    bad = []
    got = present_branches(source)
    for key, what, lost in TEST_BRANCHES:
        if not got.get(key):
            bad.append("시험의 갈래 「%s」 가 없다 (%s) — 없으면: %s" % (key, what, lost))
    return bad


# ═══════════════════════════════════════════════════════════════════════════
# 3. 재고 말한다
# ═══════════════════════════════════════════════════════════════════════════
def run() -> int:
    bad = []
    n_doors = n_branches = 0

    if not LAW_API.is_file():
        bad.append("제품 파일이 없다: %s — 재야 할 것이 없는 것도 사실이고, 초록이 아니다"
                   % LAW_API)
    else:
        product = judge_product(LAW_API.read_text(encoding="utf-8"))
        n_doors = len(ADMIN_DOORS) + len(OFFICER_DOORS)
        bad += product
        print("%s 제품 — `law_api.py` 문지기 배치 (AST · 문 %d)" % (TAG, n_doors))
        for door, name in sorted(ADMIN_DOORS.items()):
            print("    %s %-6s %-46s → %s" % ("X" if product else "O", door[0], door[1],
                                              GUARD_ADMIN))
        for door, name in sorted(OFFICER_DOORS.items()):
            print("    %s %-6s %-46s → %s" % ("X" if product else "O", door[0], door[1],
                                              GUARD_OFFICER))

    if not DOORS_TEST.is_file():
        bad.append("두 겹 시험 파일이 없다: %s — **겹을 재는 것이 사라졌다.** "
                   "제품이 멀쩡해도 다음 치환을 잡을 눈이 없다" % DOORS_TEST)
    else:
        got = present_branches(DOORS_TEST.read_text(encoding="utf-8"))
        n_branches = len(TEST_BRANCHES)
        bad += judge_test(DOORS_TEST.read_text(encoding="utf-8"))
        print("%s 시험 — 두 겹 갈래 (갈래 %d)" % (TAG, n_branches))
        for key, what, _lost in TEST_BRANCHES:
            print("    %s %-26s %s" % ("O" if got.get(key) else "X", key, what))

    print("%s 훑은 문 %d개 · 훑은 갈래 %d개" % (TAG, n_doors, n_branches))
    if bad:
        print("")
        for why in bad:
            print("%s   ✗ %s" % (TAG, why))
        return EXIT_RED
    return EXIT_OK


# ═══════════════════════════════════════════════════════════════════════════
# 4. 자기시험 — **출생 표본 다섯** · 표본은 **얼린 원본**에 댄다
#
# ★★ [2026-09-20 · 이 게이트를 실제로 빨갛게 해 보고 고친 자리 — 자진 오판]
#   첫 판은 양성 표본으로 **살아 있는 `law_api.py`** 를 썼다. 그래서 일괄 치환을 진짜로
#   넣고 게이트를 부르니 **「판정 자기시험 실패 — 이 게이트는 눈이 멀었다」**가 떴다.
#   제품이 무너졌는데 게이트는 **제 눈을 의심**했고, 자기시험에서 멈추는 바람에
#   `inputs` 줄이 안 찍혀 D-301 빨강까지 덧붙었다. **세 사실이 한 칸에 섞였다**:
#       「판정기가 고장」 · 「제품이 옮겨 갔다」 · 「건수를 말 안 했다」
#   판정기가 자기 판정 대상을 **자기 양성 표본으로 쓰면** 이 섞임은 반드시 난다.
#
#   그래서 가른다:
#       자기시험 = **얼린 원본**(아래 `SPECIMEN_*`)에만 댄다 — 제품 상태와 무관하다
#       run()    = **살아 있는 파일**을 잰다 — 색은 오직 여기서 난다
#
# ★ 그 대신 얼린 원본이 **장난감이 되지 못하게** 못 박는다: 표본의 문 집합이
#   `ADMIN_DOORS`·`OFFICER_DOORS`(= run() 이 쓰는 그 상수)와 **같아야** 자기시험이
#   통과한다. 합성 표본이 제품에서 떨어져 나가는 자리(D-310)를 그 한 줄이 막는다.
# ═══════════════════════════════════════════════════════════════════════════
BIRTH = "%s [출생 표본]" % TAG


def _specimen_law_api() -> str:
    """얼린 `law_api.py` — **진짜 경로 · 진짜 문지기 이름 · 진짜 데코레이터 모양.**

    장식만 뺐다. 문 아홉은 위 상수에서 **그대로 뽑아** 만든다 — 손으로 다시 적으면
    그 순간 표본과 제품이 갈리고, 갈린 표본으로 낸 초록은 초록이 아니다.
    """
    lines = ["from ninja_extra import route", "", "", "class Spec:"]
    for doors, guard in ((ADMIN_DOORS, GUARD_ADMIN), (OFFICER_DOORS, GUARD_OFFICER)):
        for (method, path), name in sorted(doors.items()):
            fn = path.replace(MOUNT, "").strip("/").replace("/", "_") \
                     .replace("{", "").replace("}", "").replace("-", "_")
            lines += [
                '    @route.%s("%s")' % (method.lower(), path[len(MOUNT):]),
                "    def %s_%s(self, request):" % (method.lower(), fn),
                '        """%s"""' % name,
                "        %s(request)" % guard,
                "        return {}",
                "",
            ]
    return "\n".join(lines)


#: 얼린 두 겹 시험 — **갈래 넷이 서 있는 최소한의 모양.** 글자가 아니라 **하는 일**이다.
SPECIMEN_TEST = '''
from django.test import override_settings

ADMIN_READ_DOORS = [("GET", "/api/dsm/law/purge/tenants")]
ADMIN_WRITE_DOORS = [("POST", "/api/dsm/law/purge")]
ADMIN_DENIAL_SAYS = "관리자만"


class T:
    def test_read_doors_hit_the_route_guard(self):
        for door in ADMIN_READ_DOORS:
            assert self.press(self.u4, door).status_code == 403
            assert ADMIN_DENIAL_SAYS in self.said(self.press(self.u4, door))

    @override_settings(READONLY_ROLE_GATE_ENABLED=False)
    def test_with_the_gate_off_admin_still_refuses(self):
        for door in ADMIN_WRITE_DOORS:
            assert self.press(self.u4, door).status_code == 403

    def test_u5_passes(self):
        assert self.press(self.u5, ADMIN_READ_DOORS[0]).status_code != 403

    def test_the_widened_privacy_doors_stay_open(self):
        assert self.door_list(self.u4).status_code == 200
'''


def _mutate_batch_substitution(src: str) -> str:
    """★ 턴 W 의 그 손 — 호출부 `_admin(request)` 를 **일괄 치환**한다(`def` 는 그대로)."""
    return src.replace("%s(request)" % GUARD_ADMIN, "%s(request)" % GUARD_OFFICER)


def _mutate_one_door_moves(src: str) -> str:
    """★ **한 문만** 옮긴다 — 수는 그대로다(`_admin` 3 + `_privacy_officer` 6).

    개수로 박은 판정기는 이 손을 못 잡는다. 이름으로 박았는지를 여기서 잰다.
    """
    return src.replace("%s(request)" % GUARD_ADMIN, "%s(request)" % GUARD_OFFICER, 1)


def _mutate_drop_gate_off(src: str) -> str:
    """★ 겹② 를 조용히 뗀다 — 남은 쪽은 **여전히 초록**이고, 그 초록이 사고를 덮는다."""
    return src.replace("READONLY_ROLE_GATE_ENABLED", "READONLY_ROLE_GATE_DISABLED_TYPO")


def _mutate_drop_denominator(src: str) -> str:
    """★ 분모(U5)를 뗀다 — 「전부 403」인 죽은 서버가 초록이 된다."""
    return src.replace("u5", "u4")


def _mutate_comment_only(src: str) -> str:
    """★ 반대 방향의 표본 — **주석·독스트링에만** `_privacy_officer` 를 적는다.

    grep 으로 세는 판정기는 여기서 빨개진다(거짓 빨강). AST 로 읽으면 안 세어진다.
    """
    return ("#: %s %s %s\n" % ((GUARD_OFFICER,) * 3)) + src.replace(
        '"""파기 집행"""', '"""파기 집행 — %s 아니다"""' % GUARD_OFFICER, 1)


def self_test() -> int:
    law = _specimen_law_api()
    test = SPECIMEN_TEST
    fails = []

    def expect(label, got_bad, want_red, hint=""):
        red = bool(got_bad)
        ok = red == want_red
        print("    %s %-52s %s" % ("O" if ok else "X", label, "빨강" if red else "초록"))
        if not ok:
            fails.append("%s — %s (%s)%s" % (
                label, "빨개져야 한다" if want_red else "초록이어야 한다", hint,
                "" if not got_bad else "\n        " + "\n        ".join(got_bad)))

    print("%s 다섯 + 양성 둘 — **얼린 원본**에 댄다 (살아 있는 파일은 run() 이 잰다)" % BIRTH)
    #: ① 표본이 **장난감이 아닌가** — 문 아홉이 제품 상수와 같은지 먼저 본다.
    spec_doors = set()
    for guard_doors in guard_table(law).values():
        spec_doors |= guard_doors
    if spec_doors != set(ADMIN_DOORS) | set(OFFICER_DOORS):
        print("    X %-52s" % "표본이 제품 상수와 갈렸다")
        fails.append("얼린 표본의 문 집합이 ADMIN_DOORS|OFFICER_DOORS 와 다르다 — "
                     "갈린 표본으로 낸 초록은 초록이 아니다 (D-310)")
    else:
        print("    O %-52s 문 %d" % ("표본이 제품 상수와 같다 (장난감이 아니다)",
                                     len(spec_doors)))
    #: ② 양성 — 옳은 원본은 초록이다. 이것이 초록이 아니면 나머지 넷은 뜻이 없다.
    expect("양성 ① 옳은 문지기 배치", judge_product(law), False)
    expect("양성 ② 갈래 넷이 선 시험", judge_test(test), False)
    #: ③ 출생 표본 — 실제로 있었던 손 · 놓치기 쉬운 손
    expect("표본 ① 일괄 치환 (턴 W 의 그 사고)",
           judge_product(_mutate_batch_substitution(law)), True,
           "이것을 못 잡으면 이 게이트는 존재 이유가 없다")
    expect("표본 ② 문 하나만 옮김 (수는 그대로)",
           judge_product(_mutate_one_door_moves(law)), True,
           "개수로 박으면 여기가 초록이다 — 이름으로 박는다 (D-285 ②)")
    expect("표본 ③ 겹② 관문 끄기 갈래 제거",
           judge_test(_mutate_drop_gate_off(test)), True,
           "겹 하나가 사라져도 남은 쪽은 초록이다")
    expect("표본 ④ 분모(U5) 제거",
           judge_test(_mutate_drop_denominator(test)), True,
           "「전부 403」인 죽은 서버가 초록이 된다")
    expect("표본 ⑤ 주석·독스트링에만 문지기 이름 (거짓 빨강 표본)",
           judge_product(_mutate_comment_only(law)), False,
           "grep 으로 세면 여기서 거짓 빨강이 난다 — AST 로 읽는다")

    if fails:
        print("")
        for why in fails:
            print("%s   ✗ 자기시험: %s" % (TAG, why))
        return EXIT_RED
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description="파기·집행 문의 문지기 + 두 겹 시험 (P-208 U24 ②)")
    ap.add_argument("--self-test", action="store_true", help="판정 규칙만 — 출생 표본 5 + 양성 2")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    #: ★ 재기 전에 **자기를 먼저 잰다.** 눈이 먼 판정기의 초록은 초록이 아니다 (D-350).
    rc = self_test()
    if rc != EXIT_OK:
        print("%s 자기시험이 깨졌다 — 재지 않는다" % TAG)
        return rc
    print("")
    return run()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _gate_header import gate_header

    gate_header(
        __file__,
        target="저장소 파일 — backend/apps/dsm/law_api.py · backend/tests/test_u24_admin_doors_stay_403.py",
        as_="자격 없음 — 소스를 AST 로 읽는다. 서버에 요청을 보내지 않는다",
        source="저장소 작업본 트리 (지금 읽는다 · 사진이 아니다)",
        measured="law_api.py 의 문지기 배치(AST)와 두 겹 시험의 갈래 · "
                 "분모 13 (문 9 = _admin 4 + _privacy_officer 5 · 갈래 4)",
        files=[LAW_API, DOORS_TEST],
    )
    raise SystemExit(main())
