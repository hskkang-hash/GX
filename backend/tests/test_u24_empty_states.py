# -*- coding: utf-8 -*-
"""P-185 ㉣ — **0건을 실제로 만들어 놓고 잰다** (턴 W · 차선 U24).

세종: 「0건일 때 화면이 무엇을 말하는가. … **0건일 때를 실제로 만들어서 눌러 봐라** —
**분모 0 을 안 보고 쓴 문구는 안 본 것이다.**」

이 파일이 하는 일은 **분모를 0 으로 만드는 것**이다
----------------------------------------------------
화면 문구를 고치는 것은 `.tsx` 의 일이고, 여기서는 그 문구가 걸리는 **조건이 실제로
나는지**를 서버 쪽에서 재 둔다. 0건 화면을 고쳐 놓고 0건을 한 번도 못 만들어 봤다면
그 문구는 **아무도 안 본 문장**이고, 그런 문장은 대개 틀려 있다.

잰 자리 둘 — 둘 다 **카메라 0대 · 보고서 0건인 새 테넌트**를 만들어서 두드린다.
  ① `GET /api/dsm/cameras/address-gap`  — `measurable` 이 **거짓**으로 온다
     (`total=0` 일 때 「0%」가 아니라 「잴 수 없다」. 화면은 이때 비율 카드를 안 그린다)
  ② `GET /api/dsm/reports/runs`         — `runs` 가 **빈 배열**로 온다
     (요청은 200 이다. 「못 가져온 것」과 「0건」이 여기서 갈린다)
  ③ `GET /api/dsm/system/requests`      — 「관리·설정」의 **재시작 요청 0건**
     (턴 X 에 닫은 셋째 자리 · 아래 `RestartRequestsEmptyStateTest`)

★ **셋째를 닫은 자리** [턴 X · 2026-09-20]
  턴 W 에는 「관리·설정」(`/dsm/system` · `SystemSettings.tsx`)을 **차선 U56 이 쓰고
  있어서** 못 눌렀다. 이번 턴에 U56 의 코드가 들어온 뒤 **그 0건을 실제로 만들어
  눌렀다**. 화면 쪽은 U56 이 이미 넣어 두어 U24 가 `.tsx` 를 **한 줄도 안 고쳤다** —
  남은 일은 **누르는 것**이었고 그것이 이 파일의 ③ 이다.

★★ **0건 시험에는 「1건」이 같이 있어야 한다**
  0건에서 빈 상태가 뜨는 것만 재면, **언제나 빈 상태를 그리는 화면**도 초록이다
  (「분모 0 인 초록은 초록이 아니다」의 뒤집힌 얼굴). 그래서 ③ 은 같은 문을
  **0건에서 한 번 · 1건을 만든 뒤 한 번** 두드린다. 두 번째가 빈 상태를 벗어나야
  첫 번째의 빈 상태가 **0건이라서** 뜬 것이 된다.

캐시 처리: 우회 — `Client(**NO_CACHE)` (`X-No-Cache` · D-341 착시 ⑦).
이 시험이 재는 것은 **분모가 0 인 순간의 응답**이다. 적중한 본문이 돌아오면
0 건이 아니던 옛 화면을 0 건으로 읽게 되고, 그것이 바로 이 시험이 막으려는
「분모 0 을 안 보고 쓴 문구」다 — 캐시를 타면 시험이 제 목적을 배반한다.
"""
from __future__ import annotations

import contextlib
import json

from django.apps import apps
from django.test import Client, TestCase

from tests.no_cache import NO_CACHE
from tests.test_api_contract import _bearer

PASSWORD = "u24-empty-test-only-not-a-secret"


def _forget_leftover_request() -> None:
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _ZeroTenant(TestCase):
    """**분모 0 인 테넌트 하나.** 카메라도 보고서도 한 건 없이 태어난 곳이다.

    ★ 시험이 아니라 **자리**다(이름이 `_` 로 시작한다). 이 클래스에 시험을 두면
      상속하는 쪽에서 **같은 시험이 한 번 더 돈다** — 그렇게 늘어난 수는 잰 자리가
      늘어난 것이 아니라 **같은 자리를 두 번 센 것**이다(부착률을 완결로 읽는
      착시 ① 의 시험 판).
    """

    @classmethod
    def setUpClass(cls):
        _forget_leftover_request()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        _forget_leftover_request()

    @classmethod
    def setUpTestData(cls):
        _forget_leftover_request()
        UserGroup = apps.get_model("user", "UserGroup")
        CoreUser = apps.get_model("user", "CoreUser")
        Role = apps.get_model("role", "Role")

        cls.group = UserGroup.objects.create(name="empty-state-tenant")
        UserGroup.objects.filter(pk=cls.group.pk).update(created_by=None)
        role, _ = Role.objects.get_or_create(
            code="admin", defaults={"role_name": "admin"})
        cls.user = CoreUser.objects.create_user(
            username="u24_empty_admin", password=PASSWORD, is_active=True,
            email="u24_empty_admin@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: cls.user, "group": cls.group})
        cls.user.roles.add(role)

    def setUp(self):
        _forget_leftover_request()
        super().setUp()
        self.client = Client(**NO_CACHE)

    def tearDown(self):
        super().tearDown()
        _forget_leftover_request()


class ZeroDenominatorTest(_ZeroTenant):
    """빈 상태 ①②③ 중 **①②와 청구 0건** — 카메라·보고서·청구를 0 에서 두드린다."""

    # ── ① 카메라 일괄 등록의 분모 ────────────────────────────────────────
    def test_address_gap_says_it_cannot_be_measured_at_zero(self):
        """★ 카메라 0대에서 비율은 **0% 가 아니라 「잴 수 없다」**다 (D-301).

        화면이 이 값을 보고 갈린다: 참이면 비율 카드, 거짓이면 빈 상태 한 장.
        종전에는 이 갈림이 없어서 **「0 / 0대」가 초록**으로 떴고, 초록 0 은 이 제품에서
        「다 채웠다」로 읽힌다 — 실제는 「아직 아무것도 없다」였다.
        """
        resp = self.client.get("/api/dsm/cameras/address-gap",
                               **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body["total"], 0, "이 테넌트에는 카메라가 없어야 한다")
        self.assertIs(body["measurable"], False)
        self.assertIsNone(body["coverage"],
                          "분모가 0 이면 비율은 **없다** — 0.0 으로 적지 않는다")

    # ── ② 보고서 0건 ────────────────────────────────────────────────────
    def test_report_runs_is_two_hundred_and_empty(self):
        """★ 0건은 **성공한 응답**이다. 오류와 같은 그림으로 그리면 안 되는 이유가 이것이다."""
        resp = self.client.get("/api/dsm/reports/runs", **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body.get("runs"), [],
                         "새 테넌트에는 실행 기록이 한 줄도 없어야 한다")

    # ── ③ 열람 청구 0건 (같은 화면의 표) ─────────────────────────────────
    def test_privacy_requests_is_two_hundred_and_empty(self):
        """청구 0건도 **200 + 빈 목록**이다. `unanswered` 가 0 으로 함께 온다."""
        resp = self.client.get("/api/dsm/law/privacy-requests?limit=10",
                               **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        body = json.loads(resp.content)
        self.assertEqual(body.get("items"), [])
        self.assertEqual(body.get("total"), 0)
        self.assertEqual(body.get("unanswered"), 0,
                         "0건과 「안 셌다」를 가른다 — 화면이 이 수를 쓴다")


class RestartRequestsEmptyStateTest(_ZeroTenant):
    """★★ **빈 상태 셋째 — 「관리·설정」의 재시작 요청 0건** (턴 X 에 눌러서 닫았다).

    화면(`SystemSettings.tsx`)이 이 응답을 보고 갈리는 자리는 **한 줄**이다:

        { isEmpty: (v) => (v?.requests?.length ?? 0) === 0 }

    참이면 `StateBoundary` 가 `empty` 를 그리고, 거짓이면 표를 그린다. 그 한 줄이
    보는 값이 **여기서 재는 값**이다 — 화면을 고쳐 놓고 이 응답을 한 번도 안 만들어
    봤다면 그 문구는 아무도 안 본 문장이다.

    ★ 왜 이 자리에 「기다리면 나타납니다」를 쓰면 안 되나 [실측]
      이 표의 행을 만드는 자리는 저장소 전체에서 **하나**다 —
      `api_u56.py::restart_request` 의 `DsmSystemRequest.objects.create(...)`.
      배치도 크론도 이 표에 행을 만들지 않는다. 그러므로 **가만히 두면 영원히 0건**이고,
      사전 기본 문구는 이 자리에서 거짓말이 된다. 그래서 화면이 `emptyNext` 로
      「위 칸에 사유를 적고 누르면 한 줄이 생긴다」를 제 말로 적는다.
      (보고서 0건에서 잡은 것과 **같은 뿌리**다 — 사람이 눌러야 생기는 표.)
    """

    DOOR = "/api/dsm/system/requests"
    WRITE_DOOR = "/api/dsm/system/restart-request"

    def _body(self):
        resp = self.client.get(self.DOOR, **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        return json.loads(resp.content)

    def _ask_for_restart(self, reason):
        """★ 행을 `objects.create` 로 **심지 않는다** — 화면이 누르는 그 문으로 만든다.

        이 표는 `TenantModel` 이고 그 `objects` 는 **스레드의 요청자 group** 으로
        좁혀진다(dj-core `CustomManagerGroup`). 시험이 스레드를 비워 둔 채 직접
        심으면 **소속 없는 행**이 생기고, 그 행은 화면의 질의에 안 잡힌다 —
        그러면 「1건을 만들었는데 빈 상태」가 나오고, 그 빨강은 제품의 흠이 아니라
        **시험이 만든 것**이다. 문으로 만들면 제품이 제 손으로 소속을 붙인다.
        """
        resp = self.client.post(f"{self.WRITE_DOOR}?reason={reason}", data=b"{}",
                                content_type="application/json",
                                **_bearer(self.user))
        self.assertEqual(resp.status_code, 200, resp.content[:300])
        return json.loads(resp.content)

    @staticmethod
    def _screen_says_empty(body) -> bool:
        """화면의 그 한 줄을 **그대로** 옮긴 것. 판단을 새로 짓지 않는다."""
        return len(body.get("requests") or []) == 0

    def test_zero_requests_is_two_hundred_and_empty(self):
        """① **0건일 때** — 요청은 성공하고, 목록은 비어 있고, 분모도 0 이다."""
        body = self._body()
        self.assertEqual(body.get("requests"), [],
                         "요청을 한 번도 안 올렸으니 한 줄도 없어야 한다")
        self.assertEqual(body.get("total"), 0,
                         "★ **분모도 0 이다.** 목록만 비고 분모가 1 이상이면 "
                         "「잘려서 안 보이는 것」이지 「없는 것」이 아니다")
        self.assertTrue(self._screen_says_empty(body),
                        "화면의 `isEmpty` 가 참이어야 빈 상태가 그려진다 — "
                        "거짓이면 antd 기본 「데이터 없음」이 뜨고, 그 말은 "
                        "「0건」과 「못 읽었다」를 같은 그림으로 만든다")

    def test_one_request_leaves_the_empty_state(self):
        """★★ ② **1건을 만들면 빈 상태를 벗어난다** — 이것이 ① 의 분모다.

        ① 만 재면 **언제나 빈 상태인 화면**도 초록이다. 두 번째가 있어야
        ① 의 빈 상태가 「0건이라서」 뜬 것이 된다.
        """
        before = self._body()
        self.assertTrue(self._screen_says_empty(before))

        self._ask_for_restart("빈 상태 분모 확인 — 이 줄이 생기면 빈 상태가 사라져야 한다")

        after = self._body()
        self.assertFalse(self._screen_says_empty(after),
                         "행이 생겼는데도 빈 상태면 화면은 **언제나** 빈 상태다")
        self.assertEqual(after.get("total"), 1)
        self.assertEqual(len(after.get("requests") or []), 1)

    def test_the_row_carries_the_reason_the_empty_copy_asks_for(self):
        """빈 상태 문구가 「사유를 적으라」고 한다 — **적은 사유가 실제로 돌아온다.**

        돌아오지 않으면 그 문구는 **지키지 못할 약속**이다(사유를 적으라 해 놓고
        적은 것을 안 보여 주는 화면).
        """
        said = "앞단 기동 순서 확인 뒤 잔존 연결 정리"
        self._ask_for_restart(said)
        row = (self._body().get("requests") or [])[0]
        self.assertEqual(row.get("reason"), said)
        self.assertEqual(row.get("requested_by"), self.user.username)
        self.assertTrue(row.get("status_label"),
                        "상태 칸이 비면 표가 「무엇이 됐는지」를 말하지 않는다")
