# -*- coding: utf-8 -*-
"""★★ **파기·집행 문은 U4 에게 403 으로 남는다** — 일괄 치환 사고의 음성 대조.

무엇이 이 파일을 만들게 했나 — **실제로 있었던 사고**
-----------------------------------------------------
턴 W (2026-09-19 · 차선 U24)에서 LAW-07′ 다섯 문을 U4 에게 열 때, 문지기 이름
`_admin` 을 **한 번에 치환**했다. 그 한 번이 `law_api.py` 의 `_admin` **전부**를
바꿨고, 그래서 **청구 면 다섯이 아니라 파기·집행 문까지** U4 에게 열렸다.
그 자리에서 알아채 되돌렸지만, 커밋됐으면 읽기 전용 지자체 담당관이
「보관 기간이 지난 영상 지우기」 면을 보게 될 뻔했다.

    넓히는 작업에서 **일괄 치환은 도구가 아니라 사고**다.

되돌린 것으로는 부족하다 — 되돌림은 **다음에 같은 손이 오는 것을 막지 못한다.**
그래서 세종이 그 사고의 **음성 대조를 시험으로 박으라**고 했다. 이 파일이 그것이다.

★ 이 파일이 **양쪽을 같이** 재는 이유
-------------------------------------
안 넓힌 쪽(파기 문 403)만 재면 **「전부 403」인 코드**도 통과한다 — 즉 LAW-07′ 를
통째로 되돌려 놔도 이 파일은 초록이다. 넓힌 쪽(청구 다섯 문 U4 200)만 재면
**「전부 200」인 코드**(= 그 일괄 치환 그대로)가 통과한다.
**두 쪽을 같은 파일 · 같은 계정 · 같은 순간에** 재야 「요청만큼만 넓혔다」가 성립한다.

★ **이름으로 박는다** (D-285 ②)
--------------------------------
「`_admin` 문은 넷이다」처럼 **개수로** 박으면, 하나가 지워질 때 **새 문이 들어올
자리**가 생긴다(수는 그대로니 초록이다). 그래서 이 파일의 표는 전부
**메서드 + 경로 이름**이고, 구조 시험은 「`_admin` 을 쓰는 라우트의 **이름 집합**」과
「`_privacy_officer` 를 쓰는 라우트의 **이름 집합**」을 통째로 대 본다.
어느 쪽으로든 문이 옮겨 가면 **어느 문이 옮겨 갔는지 이름으로** 빨강이 난다.

★ 겹이 둘이다 — **따로 잰다**
-----------------------------
U4 가 파기 문에서 막히는 자리는 **메서드에 따라 다르다**:

    GET  /law/purge/tenants    → 라우트의 `_admin` 이 막는다 (읽기는 관문이 안 본다)
    POST /law/purge            → **미들웨어**(P-119 읽기 전용 쓰기 금지)가 먼저 막는다

POST 쪽 403 은 `_admin` 을 **증명하지 않는다** — 관문이 앞에서 끊어 `_admin` 까지
가지도 않기 때문이다. 즉 `_admin` 을 넓혀도 POST 쪽은 그대로 403 이고, POST 만
재는 시험은 **그 치환을 못 잡는다.** 그래서 이 파일은
  ① GET 두 문으로 `_admin` 을 **직접** 재고,
  ② 쓰기 둘은 관문을 **일부러 끄고**(`READONLY_ROLE_GATE_ENABLED=False`) 한 번 더 눌러
     그 아래의 `_admin` 도 U4 를 막는지 본다.
한 겹만 재고 「막힌다」고 적으면, 다른 겹이 열려 있어도 모른다.

★ 분모를 같이 잰다 — **「전부 403」은 초록이 아니다**
-----------------------------------------------------
403 만 세면 서버가 통째로 고장 나도 초록이다. 그래서 같은 네 문을 **U5(운영자)로도**
누른다. U5 가 지나가야 「이 문들은 살아 있고, 다만 U4 를 막는 것」이 된다.

★ 함수가 아니라 **문을 두드린다** (D-210)
-----------------------------------------
`_admin()` 을 직접 불러 재면 그 앞의 `RoleGateMiddleware` 를 못 본다. 그리고 겹이
둘이라는 사실 자체가 이 파일의 절반이다 — HTTP 로 두드린다.

캐시 처리: 우회 — `Client(**NO_CACHE)` (`X-No-Cache` · D-341 착시 ⑦).
**이 파일이 막는 것**: 같은 네 문을 U4 → U5 로 **잇달아** 누르기 때문에, 응답 캐시가
켜진 채로 재면 U5 의 200 본문이 U4 의 요청에 그대로 돌아와 **「파기 문이 U4 에게 403」을
재는 줄이 조용히 200 을 보고**, 반대로 U4 의 403 이 U5 줄을 빨갛게 만든다. 즉 캐시를
안 비키면 이 파일이 잡으려는 **바로 그 사고(문이 U4 에게 열림)가 캐시에 덮인다.**
"""
from __future__ import annotations

import ast
import json
import pathlib

from django.test import override_settings

from common import role_gate
from tests.test_api_contract import _bearer
from tests.test_u24_law07_authz import BASE, _Persona

#: ★ 문지기 `_admin` 이 지키는 문 — **이름으로** 적는다. 개수가 아니다.
#:   턴 W 의 일괄 치환이 넓힐 뻔했던 바로 그 집합이다.
ADMIN_DOORS: dict[tuple[str, str], str] = {
    ("GET", "/api/dsm/law/purge/tenants"): "파기 대상 목록",
    ("POST", "/api/dsm/law/purge"): "파기 집행",
    ("GET", "/api/dsm/law/purge/history"): "파기 기록",
    ("POST", "/api/dsm/law/retention/sweep"): "보존기간 집행",
}

#: 그중 **읽기**인 둘. 이 둘만이 `_admin` 을 직접 잰다(관문이 읽기를 안 보므로).
ADMIN_READ_DOORS = [d for d in ADMIN_DOORS if d[0] == "GET"]
#: 그중 **쓰기**인 둘. 이쪽은 관문이 먼저 막는다 — 겹을 갈라서 잰다.
ADMIN_WRITE_DOORS = [d for d in ADMIN_DOORS if d[0] != "GET"]

#: ★ 문지기 `_privacy_officer` 가 지키는 문 — **넓힌 쪽**. 같은 파일에서 같이 잰다.
OFFICER_DOORS: frozenset = frozenset({
    ("GET", "/api/dsm/law/privacy-requests"),
    ("POST", "/api/dsm/law/privacy-requests"),
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}"),
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}/masked"),
    ("POST", "/api/dsm/law/privacy-requests/{receipt_no}/reply"),
})

#: `_admin` 이 스스로 내는 거절 문장. 이 글자가 보이면 **라우트가** 막은 것이다.
ADMIN_DENIAL_SAYS = "관리자만"

LAW_API = pathlib.Path(__file__).resolve().parents[1] / "apps" / "dsm" / "law_api.py"


class _Doors(_Persona):
    """네 문을 누르는 손. `_Persona` 가 U2·U4·U5 를 **한 테넌트 안에** 세워 준다."""

    def press(self, who, door):
        method, path = door
        #: 쓰기 문은 기본값으로 누른다 — `dry_run` 기본이 참이라 **아무것도 안 지운다.**
        #: 설령 문지기를 지나쳐도 세기만 한다. 되돌릴 수 없는 일을 시험이 하지 않는다.
        if method == "GET":
            return self.client.get(path, **self._auth(who))
        return self.client.post(f"{path}?dry_run=true", data=b"{}",
                                content_type="application/json", **self._auth(who))

    def _auth(self, who):
        return _bearer(who)

    def said(self, resp) -> str:
        try:
            return json.dumps(json.loads(resp.content), ensure_ascii=False)
        except Exception:               # noqa: BLE001  — 본문이 JSON 이 아니면 그대로 본다
            return resp.content.decode("utf-8", "replace")


class PurgeDoorsStay403ForU4Test(_Doors):
    """★★ **안 넓힌 쪽.** 네 문 전부가 U4 에게 403 이다 — 이름으로 박는다."""

    def test_all_four_admin_doors_refuse_u4(self):
        """표 한 벌. 어느 칸이 열렸는지 **이름으로** 나온다."""
        got = {ADMIN_DOORS[d]: self.press(self.u4, d).status_code
               for d in ADMIN_DOORS}
        self.assertEqual(got, {name: 403 for name in ADMIN_DOORS.values()},
                         f"파기·집행 문이 U4 에게 열렸다: {got}")

    def test_the_read_doors_are_refused_by_the_route_not_the_gate(self):
        """★ **이 줄이 `_admin` 을 직접 잰다.**

        읽기는 P-119 관문이 안 본다 — 그러니 여기서 나오는 403 은 **라우트의
        `_admin`** 이 낸 것이다. `_admin` 을 `_privacy_officer` 로 치환하면
        **이 줄이 200 으로 빨개진다**(턴 W 의 그 사고를 잡는 줄).
        """
        for door in ADMIN_READ_DOORS:
            with self.subTest(door=ADMIN_DOORS[door]):
                resp = self.press(self.u4, door)
                self.assertEqual(resp.status_code, 403)
                said = self.said(resp)
                self.assertIn(ADMIN_DENIAL_SAYS, said,
                              "라우트의 `_admin` 이 낸 403 이어야 한다")
                self.assertNotIn(role_gate.READONLY_DENIAL_CODE, said,
                                 "읽기 문이 읽기 전용 관문에 막힐 리 없다 — "
                                 "사유가 섞이면 어느 겹이 막았는지 모른다")

    def test_the_write_doors_are_refused_by_the_gate_first(self):
        """쓰기 둘은 **관문**이 먼저 막는다. 그래서 이 403 은 `_admin` 의 증거가 아니다.

        이 줄은 「막힌다」를 자랑하려고 있는 것이 아니라, **다음 줄이 왜 필요한지**를
        적어 두려고 있다 — 겹을 안 가르면 `_admin` 이 열려도 여기는 초록이다.
        """
        for door in ADMIN_WRITE_DOORS:
            with self.subTest(door=ADMIN_DOORS[door]):
                resp = self.press(self.u4, door)
                self.assertEqual(resp.status_code, 403)
                self.assertEqual(json.loads(resp.content).get("code"),
                                 role_gate.READONLY_DENIAL_CODE)

    @override_settings(READONLY_ROLE_GATE_ENABLED=False)
    def test_with_the_gate_switched_off_admin_still_refuses_u4_on_writes(self):
        """★★ **관문을 끄고 그 아래를 본다.** 겹 하나만 믿지 않는다.

        되돌리기 한 줄(`READONLY_ROLE_GATE_ENABLED=False`)로 관문을 끄면 요청이
        `_admin` 까지 간다. 거기서도 U4 는 403 이어야 한다 — 그래야 「관문이 꺼진
        날에도 파기 문은 닫혀 있다」가 참이다. 이 줄 역시 일괄 치환이 나면 빨개진다.
        """
        self.assertFalse(role_gate.readonly_enabled(),
                         "끄는 스위치가 안 먹으면 이 시험은 아무것도 안 잰다")
        for door in ADMIN_WRITE_DOORS:
            with self.subTest(door=ADMIN_DOORS[door]):
                resp = self.press(self.u4, door)
                self.assertEqual(resp.status_code, 403,
                                 "관문 아래의 `_admin` 이 U4 를 막아야 한다")
                said = self.said(resp)
                self.assertIn(ADMIN_DENIAL_SAYS, said)
                self.assertNotIn(role_gate.READONLY_DENIAL_CODE, said,
                                 "관문을 껐는데 관문 사유가 나오면 스위치가 거짓이다")


class TheseDoorsAreAliveTest(_Doors):
    """★★ **분모.** 「전부 403」은 초록이 아니다 — U5 가 지나가는 것을 같이 본다."""

    def test_u5_passes_the_same_four_doors(self):
        """같은 네 문을 운영자로 누른다. 403 이 아니어야 한다.

        ★ 200 을 못 박지 않는 이유: `POST /law/purge` 는 소속·파기 대상에 따라
          422 를 낼 수 있고, 그것은 **문지기를 지나 핸들러가 낸 답**이다(P-83 눈금).
          여기서 재는 것은 「**막히지 않는다**」이지 핸들러의 결과가 아니다.
        """
        got = {ADMIN_DOORS[d]: self.press(self.u5, d).status_code for d in ADMIN_DOORS}
        stuck = {k: v for k, v in got.items() if v == 403}
        self.assertEqual(stuck, {},
                         f"운영자까지 막혔다 — U4 의 403 이 「문이 죽어서」일 수 있다: {got}")

    def test_u2_is_also_still_refused(self):
        """대조 하나 더 — 관제팀장도 종전 그대로 파기 면에 못 들어간다."""
        got = {ADMIN_DOORS[d]: self.press(self.u2, d).status_code for d in ADMIN_DOORS}
        self.assertEqual(got, {name: 403 for name in ADMIN_DOORS.values()}, f"{got}")


class TheWidenedSideMeasuredHereTooTest(_Persona):
    """★★ **넓힌 쪽.** 한쪽만 재면 「전부 403」인 코드도 통과한다 — 같이 잰다.

    이 클래스가 없으면 이 파일은 **LAW-07′ 를 통째로 되돌린 코드에도 초록**이다.
    그러면 「파기 문은 닫혀 있다」는 참이지만 「청구 면은 열려 있다」를 아무도 안 잰다.
    """

    def test_u4_still_passes_all_five_privacy_request_doors(self):
        receipt = self.a_receipt()
        got = {
            "목록": self.door_list(self.u4).status_code,
            "접수": self.door_accept(self.u4).status_code,
            "상세": self.door_detail(self.u4, receipt).status_code,
            "마스킹본": self.door_masked(self.u4, receipt).status_code,
            "회신": self.door_reply(self.u4, receipt).status_code,
        }
        self.assertEqual(got, {k: 200 for k in got},
                         f"넓힌 쪽이 닫혔다 — 이 파일은 양쪽을 같이 잰다: {got}")

    def test_the_two_sides_are_different_at_the_same_moment(self):
        """★ **같은 계정 · 같은 토큰 · 같은 순간**에 한쪽은 200 · 한쪽은 403.

        다른 것은 **문지기 하나**다. 이 한 줄이 「전부 403」과 「전부 200」을
        **동시에** 기각한다.
        """
        widened = self.door_list(self.u4).status_code
        kept = self.client.get("/api/dsm/law/purge/tenants",
                               **_bearer(self.u4)).status_code
        self.assertEqual((widened, kept), (200, 403),
                         f"넓힌 쪽 200 · 안 넓힌 쪽 403 이어야 한다: {(widened, kept)}")


class GuardAssignmentIsPinnedByNameTest(_Persona):
    """★★ **어느 문이 어느 문지기를 쓰는가** — 원본을 읽어 **이름 집합**으로 박는다.

    위 HTTP 시험은 「지금 U4 가 막힌다」를 재고, 이 시험은 「**그 이유가 그 문지기**」를
    잰다. 둘은 다른 질문이다 — 계정 하나가 바뀌어도 HTTP 는 흔들리지만 이 표는 안 흔들린다.

    ★ 왜 런타임이 아니라 **원본 AST** 인가: 문지기는 함수 **본문**에서 불린다. 런타임
      레지스트리(`enumerate_operations`)는 라우트의 메서드·경로·인증기까지는 보여 주지만
      「본문이 `_admin` 을 부르는가」는 못 본다. 그리고 이 파일이 잡으려는 사고는
      **본문 한 단어의 치환**이다. 그래서 여기만 원본을 읽는다 — grep 이 아니라 AST 로
      읽어 주석·문자열에 적힌 `_admin` 을 세지 않는다.
    """

    MOUNT = "/api/dsm"

    @classmethod
    def _guard_table(cls) -> dict[str, set[tuple[str, str]]]:
        tree = ast.parse(LAW_API.read_text(encoding="utf-8"))
        table: dict[str, set[tuple[str, str]]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doors = cls._routes_of(node)
            if not doors:
                continue
            for called in cls._guards_called(node):
                table.setdefault(called, set()).update(doors)
        return table

    @staticmethod
    def _routes_of(fn) -> set[tuple[str, str]]:
        out = set()
        for dec in fn.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            f = dec.func
            if not (isinstance(f, ast.Attribute)
                    and isinstance(f.value, ast.Name) and f.value.id == "route"):
                continue
            if not dec.args or not isinstance(dec.args[0], ast.Constant):
                continue
            out.add((f.attr.upper(),
                     GuardAssignmentIsPinnedByNameTest.MOUNT + str(dec.args[0].value)))
        return out

    @staticmethod
    def _guards_called(fn) -> set[str]:
        """본문이 **부르는** 문지기 이름. 주석·문자열은 AST 에 없으므로 안 세어진다."""
        wanted = {"_admin", "_privacy_officer", "_scope"}
        return {n.func.id for n in ast.walk(fn)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id in wanted}

    def test_admin_guards_exactly_these_four_doors_by_name(self):
        """★ 일괄 치환이 나면 **여기가 먼저** 빨개진다 — 어느 문이 빠졌는지 이름으로."""
        got = self._guard_table().get("_admin", set())
        self.assertEqual(got, set(ADMIN_DOORS),
                         "`_admin` 이 지키는 문의 **이름 집합**이 달라졌다. "
                         f"빠진 문={set(ADMIN_DOORS) - got} · 새로 든 문={got - set(ADMIN_DOORS)}")

    def test_the_officer_guard_never_reaches_a_purge_door(self):
        """★ **반대 방향으로도 박는다.** `_privacy_officer` 는 청구 다섯 문에만 있다."""
        got = self._guard_table().get("_privacy_officer", set())
        self.assertEqual(got, set(OFFICER_DOORS),
                         "청구 면의 문지기가 다른 문으로 번졌거나 문에서 빠졌다. "
                         f"새로 든 문={got - set(OFFICER_DOORS)}")
        self.assertEqual(got & set(ADMIN_DOORS), set(),
                         "청구 면 문지기가 파기·집행 문에 걸렸다 — 그것이 턴 W 의 그 사고다")

    def test_the_two_guards_do_not_share_a_door(self):
        """한 문에 문지기 둘이 서면 어느 쪽이 정본인지 아무도 모른다."""
        table = self._guard_table()
        both = table.get("_admin", set()) & table.get("_privacy_officer", set())
        self.assertEqual(both, set(), f"두 문지기가 같이 선 문: {both}")


class MeteringWasNeverAdminGatedTest(_Doors):
    """★ **턴 W 의 말을 실측이 정정한다** — 「파기·**사용량**」이라고 적었는데,

    사용량(OPS-16 계량) 세 문은 `_admin` 이 **아니다.** `_scope` 다 — 인증만 되면
    자기 테넌트 사용량을 본다. 그러므로 그 셋은 **일괄 치환으로 넓어질 수 있는 문이
    아니었고**, 지금도 U4 에게 403 이 아니다. 「403 을 지킨다」고 적으면 **없는 것을
    지킨다**고 적는 것이고, 그 문장은 언젠가 「왜 200 이지」로 되돌아온다.

    그래서 이 클래스는 **금지가 아니라 사실**을 박는다: 이 셋은 열려 있다.
    """

    METERING = [("GET", "/api/dsm/metering"),
                ("GET", "/api/dsm/metering/series"),
                ("GET", "/api/dsm/metering/csv")]

    def test_metering_is_not_behind_the_admin_guard(self):
        table = GuardAssignmentIsPinnedByNameTest._guard_table()
        for door in self.METERING:
            with self.subTest(door=door):
                self.assertNotIn(door, table.get("_admin", set()))
                self.assertNotIn(door, table.get("_privacy_officer", set()))
                self.assertIn(door, table.get("_scope", set()),
                              "사용량은 `_scope` 문지기다 — 인증만 본다")

    def test_u4_is_not_403_on_metering_right_now(self):
        """실제로 눌러서 본다. **403 이 아니다** — 막힌 적이 없기 때문이다."""
        got = {path: self.press(self.u4, (m, path)).status_code
               for m, path in self.METERING}
        self.assertEqual([c for c in got.values() if c == 403], [],
                         f"사용량이 U4 에게 막혔다면 그것은 새로 생긴 일이다: {got}")


class TheRefusalDoesNotLeakTest(_Doors):
    """파기 면의 거절이 **테넌트 자료를 한 자도** 안 흘린다."""

    def test_the_403_body_carries_no_tenant_rows(self):
        for door in ADMIN_READ_DOORS:
            with self.subTest(door=ADMIN_DOORS[door]):
                said = self.said(self.press(self.u4, door))
                for leak in ("declared", "entries", "count"):
                    self.assertNotIn(f'"{leak}"', said,
                                     "막은 응답이 목록의 모양을 흘리면 막은 것이 아니다")


class TheWidenedPathListStillHasNoPurgeTest(_Persona):
    """읽기 전용에 비켜 준 **모양 둘**에 파기·집행이 없다 — 순수 함수로 잰다."""

    def test_no_purge_path_is_in_the_readonly_bypass(self):
        allow = role_gate.is_readonly_allowed_path
        for path in ("/api/dsm/law/purge",
                     "/api/dsm/law/purge/tenants",
                     "/api/dsm/law/purge/history",
                     "/api/dsm/law/retention/sweep"):
            with self.subTest(path=path):
                self.assertFalse(allow(path), "파기·집행이 관문을 비키면 안 된다")

    def test_the_two_bypassed_shapes_are_still_the_claim_face(self):
        allow = role_gate.is_readonly_allowed_path
        self.assertTrue(allow(BASE))
        self.assertTrue(allow(f"{BASE}/GX-PR-20260920-AB12CD/reply"))
