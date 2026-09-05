# -*- coding: utf-8 -*-
"""UX-24 — 역할별 동시 세션 상한. **재현 가능한 증거는 브라우저가 아니라 이 파일이다.**

이 저장소는 화면 동시 접속이 하나뿐이라 「월 모드와 자리 화면을 같이 켜 본다」를
사람이 할 수 없다. 그래서 다중 세션을 **Django 시험 클라이언트**로 짓는다 —
그리고 그것이 오히려 낫다: 캡처는 한 번의 사실이고 이 파일은 매번 다시 잰다.

이 파일이 못박는 것 넷
----------------------
  ① **지금은 동시 1개다** — characterization. 결함을 숨기지 않고 **고정**한다
     (`test_auth_surface.py` 와 같은 방식). dj-core 가 여러 세션을 받게 되는 날
     이 시험이 빨개지고, **그날이 UX-24 를 다시 여는 날**이다.
  ② 밀려난 화면이 **왜 밀려났는지** 말한다 — 사전 문구 그대로.
  ③ 상한 표와 축출 순서 — 순수 함수로. 저장소가 무엇이든 답은 같다.
  ④ **토큰 수명을 안 바꿨다** — 월 모드 12시간이 그 값을 요구하지 않는다는 판정을
     시험이 지킨다. 누가 200분을 720분으로 올리면 여기가 빨개진다.

캐시 처리: **비움** — `SessionRegistry` 가 캐시를 대장으로 쓴다. 시험마다 비우지 않으면
앞 시험이 남긴 행이 다음 시험의 상한을 먹는다. 401 을 재는 갈래는 `X-No-Cache` 로
우회한다(D-341 착시 ⑦ — 관문을 재는 시험이 캐시를 재면 안 된다).

절대 금지 (AGENT_LOOP 절대금지 #4·#5): skip·xfail 금지. 못 잰 것은 사유와 함께 센다.

실행
    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
      DB_TEST_NAME=test_gx_sec python -m pytest tests/test_s_session_limit.py -q \
      --nomigrations -p no:randomly --tb=short 2>/dev/null'
"""

from __future__ import annotations

import json
import uuid

import jwt as pyjwt
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from ninja_jwt.tokens import RefreshToken

from common.session_limit import (
    COPY_EVICTED,
    COPY_OVER_CAP,
    DEFAULT_SESSION_CAP,
    DJCORE_DIFFERENT_SESSION,
    DJCORE_WIRE_DETAIL,
    WALL_MODE_SESSION_TTL_SECONDS,
    SessionRecord,
    SessionRegistry,
    admit,
    cap_for_role_codes,
)
from config.k3_roles import (
    K3_ROLE_EXECUTIVES,
    K3_ROLE_MANAGERS,
    K3_ROLE_OPERATORS,
    K3_ROLE_SYSOPS,
)
from tests.no_cache import NO_CACHE

# ═══════════════════════════════════════════════════════════════════════════
# ★ 출생 표본 (D-310) — **이 절을 만들게 한 바로 그 사실**
# ═══════════════════════════════════════════════════════════════════════════
#
# [실측 2026-09-05 · dj-core 소스 전수]
#
#     core/user/models.py:577   user.token = enc("<session_id>:<access_jti>")  ← 칸 하나
#     core/api/v1/auth.py:706   로그인이 새 uuid4() 로 그 칸을 **덮어쓴다**
#     core/auth.py:63           토큰의 session_id ≠ user.token 의 session_id
#                               → 401 "Token from different session"
#
# 관제실은 월 모드 대형 화면 · 자리 데스크톱 · 휴대전화를 **동시에** 켠다.
# 그런데 두 번째 로그인이 첫 화면을 죽인다 — 그리고 첫 화면에는 영문 401 한 줄만 남아
# **사람이 고장과 구별하지 못한다.** 아래 `DjCoreSingleSessionTest` 가 그 사실 그대로다.
#
# ★★ 그리고 착수하면서 **더 나쁜 것 둘**을 쟀다 — 지시서에 없던 것이다:
#
#   ㉠ **그 사유는 화면에 절대 닿지 않는다.** 두 겹의 `except` 가 삼킨다:
#        core/auth.py:119         바깥 except 가 "Token from different session" 을 잡아
#                                 "Token invalid" 로 바꾼다
#        core/api/v1/auth.py:197  `CustomJWTAuth.authenticate` 의 `except Exception: pass`
#                                 가 그것마저 삼키고 None 을 돌려준다
#      화면이 받는 것은 `401 {"detail": "Unauthorized"}` 하나다 — **밀려난 화면과
#      토큰이 깨진 화면이 글자 하나까지 같다.** 그래서 우리 층은 응답이 아니라
#      **요청이 들고 온 토큰**으로 둘을 가른다.
#
#   ㉡ **밀려난 화면이 요청 한 번을 보내면 그 사용자의 살아 있는 재발급 토큰이
#      전부 블랙리스트된다** (`core/auth.py` 의 바깥 except 가 그렇게 한다).
#      즉 죽은 화면 한 장이 **지금 앉아 있는 사람의 세션 갱신까지 끊는다.**
#      `test_stale_token_blacklists_the_live_session` 이 그 사실을 고정한다.
#
# ⚠ 이 표본은 「우리가 만든 결함」이 아니라 **「우리가 못 고치는 결함」**이다(§0.4).
#   그래서 시험은 고침을 요구하지 않고 **사실을 고정**한다.
BIRTH_SAMPLE_DJCORE_401 = DJCORE_DIFFERENT_SESSION

#: 익명이면 401 이 나오는 자리 하나 — 즉 `CustomJWTAuth` 를 실제로 지나는 라우트다
#: (`tests/test_api_contract.py::test_unauthenticated_401_is_untouched` 가 쓰는 자리).
ROUTE_BEHIND_JWT = "/api/report-template/1"


def _session_token(user, session_id: str, *, bind: bool) -> str:
    """이 사용자의 접근 토큰 하나.

    `bind=True` 면 로그인이 하는 일을 그대로 한다 — `user.token` 을 이 세션으로 덮어쓴다.
    `bind=False` 면 토큰만 만든다: **앞서 로그인해 두었다가 밀려난 화면**의 모양이다.
    """
    refresh = RefreshToken.for_user(user)
    refresh["session_id"] = session_id
    access = str(refresh.access_token)
    if bind:
        decoded = pyjwt.decode(
            access,
            settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")],
        )
        user.set_encrypted_session_token(session_id, decoded.get("jti"))
        user.save()
    return access


class _UserMixin:
    PASSWORD = "test-only-not-a-secret"

    @classmethod
    def _make_user(cls, username: str, role_code: str | None = None):
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")
        Role = apps.get_model("role", "Role")

        group = UserGroup.objects.create(name=f"ux24-{username}")
        user = CoreUser.objects.create_user(
            username=username,
            password=cls.PASSWORD,
            is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group}
        )
        code = role_code or f"ux24_{username}"
        role, _ = Role.objects.get_or_create(code=code, defaults={"role_name": code})
        user.roles.set([role])
        return user


# ═══════════════════════════════════════════════════════════════════════════
# ① 지금은 동시 1개다 — 결함을 고정한다 (characterization)
# ═══════════════════════════════════════════════════════════════════════════

class DjCoreSingleSessionTest(_UserMixin, TestCase):
    """월 모드와 자리 화면을 **같은 계정으로 동시에** 켜 본다 — HTTP 로.

    이것이 이 절의 유일한 실측 증거다. 브라우저를 열지 않는다(동시 접속 1개이고
    이번 턴 그 자리는 QA/E2E 것이다) — 그리고 열 필요가 없다.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = cls._make_user("ux24_two_screens", role_code="operator")

    def setUp(self):
        cache.clear()          # 캐시 처리: 비움 — 대장이 캐시다
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_dj_core_admits_exactly_one_session(self):
        """자리 화면으로 들어간 뒤 **월 모드로 또 들어가면 자리 화면이 죽는다.**

        ★ 이 시험이 초록인 것은 「잘 돌아간다」가 아니라 **「지금 상태가 이렇다」**이다.
          UX-24 가 요구한 「U1 3대 동시」는 이 벽 뒤에 있고, 벽은 §0.4 안이다.
        """
        desk = uuid.uuid4().hex
        wall = uuid.uuid4().hex

        desk_token = _session_token(self.user, desk, bind=True)
        first = self.client.get(ROUTE_BEHIND_JWT, HTTP_AUTHORIZATION=f"Bearer {desk_token}")
        self.assertNotEqual(
            first.status_code, 401,
            "자리 화면이 처음부터 못 들어갔다 — 이 시험이 재려는 것은 그 다음이다",
        )

        # 월 모드가 로그인한다. dj-core 는 user.token 을 이 세션으로 덮어쓴다.
        _session_token(self.user, wall, bind=True)

        again = self.client.get(ROUTE_BEHIND_JWT, HTTP_AUTHORIZATION=f"Bearer {desk_token}")
        self.assertEqual(
            again.status_code, 401,
            "동시 2개가 살아 있다 — dj-core 의 세션 벽이 걷혔다. "
            "그렇다면 UX-24 를 다시 열어야 한다(authn_paths §8).",
        )

    def test_evicted_screen_is_told_why_in_korean(self):
        """② 밀려난 화면이 **왜** 밀려났는지 말한다 — 사전 문구 그대로.

        바꾼 것은 **글자뿐**이다. 상태는 401 그대로여야 한다 — 앞단의 재로그인 경로가
        상태로 판정하기 때문이다.
        """
        stale = _session_token(self.user, uuid.uuid4().hex, bind=False)
        _session_token(self.user, uuid.uuid4().hex, bind=True)

        resp = self.client.get(ROUTE_BEHIND_JWT, HTTP_AUTHORIZATION=f"Bearer {stale}")
        self.assertEqual(resp.status_code, 401, "상태코드를 바꾸면 앞단이 길을 잃는다")
        body = json.loads(resp.content)
        self.assertEqual(body.get("detail"), COPY_EVICTED)
        self.assertEqual(body.get("reason_code"), "session_evicted")
        self.assertEqual(
            body.get("origin_detail"), DJCORE_WIRE_DETAIL,
            "원문을 지웠다 — 로그와 연동자가 읽던 값이 사라지면 그것도 계약 파손이다",
        )

    @override_settings(SESSION_LIMIT_ENABLED=False)
    def test_rollback_switch_restores_djcore_wording(self):
        """되돌리기 한 줄이 정말 되돌리는가. 안 되돌아가면 그것은 스위치가 아니다."""
        stale = _session_token(self.user, uuid.uuid4().hex, bind=False)
        _session_token(self.user, uuid.uuid4().hex, bind=True)

        resp = self.client.get(ROUTE_BEHIND_JWT, HTTP_AUTHORIZATION=f"Bearer {stale}")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(json.loads(resp.content).get("detail"), DJCORE_WIRE_DETAIL)

    def test_stale_token_blacklists_the_live_session(self):
        """㉡ **죽은 화면 한 장이 살아 있는 세션의 갱신을 끊는다** — 고정한다.

        `core/auth.py` 의 바깥 `except` 는 사유를 바꾸기 전에 그 사용자의 **만료 안 된
        재발급 토큰을 전부 블랙리스트**한다. 밀려난 월 모드가 20초마다 갱신을 두드리는
        화면이라는 것을 생각하면, 이것은 「가끔 로그아웃된다」의 유력한 뿌리다.

        ★ 우리는 못 고친다(§0.4). 이 시험은 **그 사실이 조용히 바뀌지 않게** 지킨다 —
          dj-core 가 이 부작용을 없애면 여기가 빨개지고, 그때 이 문단을 지운다.
        """
        BlacklistedToken = apps.get_model("token_blacklist", "BlacklistedToken")
        stale = _session_token(self.user, uuid.uuid4().hex, bind=False)
        _session_token(self.user, uuid.uuid4().hex, bind=True)

        before = BlacklistedToken.objects.filter(token__user_id=self.user.id).count()
        self.client.get(ROUTE_BEHIND_JWT, HTTP_AUTHORIZATION=f"Bearer {stale}")
        after = BlacklistedToken.objects.filter(token__user_id=self.user.id).count()

        self.assertGreater(
            after, before,
            "부작용이 사라졌다 — dj-core 가 고쳐졌다면 이 문단과 authn_paths §8 을 고쳐라",
        )

    def test_unrelated_401_is_not_relabelled(self):
        """음성 대조 — **아무 401 이나 이 문구를 받으면 안 된다.**

        익명 요청의 401 은 「다른 기기에서 로그인되었습니다」가 아니다. 넓게 잡으면
        비밀번호를 틀린 사람이 없는 기기를 찾는다.
        """
        resp = self.client.get(ROUTE_BEHIND_JWT)
        self.assertEqual(resp.status_code, 401)
        self.assertNotEqual(json.loads(resp.content).get("detail"), COPY_EVICTED)


# ═══════════════════════════════════════════════════════════════════════════
# ③ 상한 표와 축출 — 순수 함수
# ═══════════════════════════════════════════════════════════════════════════

class SessionCapTableTest(TestCase):
    """세종 판정 U1 3 · U2 3 · U4 2 · U5 2 를 코드가 그대로 말하는가."""

    def test_caps_match_the_ruling(self):
        expected = [
            ("U1 관제요원", K3_ROLE_OPERATORS, 3),
            ("U2 관제팀장", K3_ROLE_MANAGERS, 3),
            ("U4 재난안전과", K3_ROLE_EXECUTIVES, 2),
            ("U5 시스템 관리자", K3_ROLE_SYSOPS, 2),
        ]
        for label, codes, cap in expected:
            for code in codes:
                with self.subTest(who=label, code=code):
                    self.assertEqual(cap_for_role_codes([code])[0], cap)

    def test_unmapped_role_keeps_todays_value(self):
        """매핑 없는 역할에 2·3 을 주면 그것은 판정이 아니라 추측이다 (D-280)."""
        cap, why = cap_for_role_codes(["delivery_admin"])
        self.assertEqual(cap, DEFAULT_SESSION_CAP)
        self.assertEqual(cap, 1, "오늘의 값은 1이다 — 지금 제품이 그렇다")
        self.assertIn("상한 표에 없는", why)

    def test_no_roles_at_all(self):
        self.assertEqual(cap_for_role_codes([])[0], DEFAULT_SESSION_CAP)

    def test_multiple_roles_take_the_wider_cap(self):
        """겸직이 벌이 되면 안 된다 — 팀장이 관제요원 역할을 겸해도 좁아지지 않는다."""
        cap, _ = cap_for_role_codes([K3_ROLE_EXECUTIVES[0], K3_ROLE_MANAGERS[0]])
        self.assertEqual(cap, 3)

    def test_reason_names_the_source_of_truth(self):
        """수만 돌려주면 다음 사람이 「왜 3인가」를 다시 캔다."""
        _, why = cap_for_role_codes([K3_ROLE_OPERATORS[0]])
        self.assertIn("k3_roles", why)


class AdmitTest(TestCase):
    """축출 순서 — **가장 오래 켜 둔 화면**을 닫는다. 사전 문구가 그렇게 말한다."""

    def _rec(self, sid: str, started: float, wall: bool = False) -> SessionRecord:
        return SessionRecord(session_id=sid, user_id=7, started_at=started, wall_mode=wall)

    def test_under_cap_evicts_nothing(self):
        kept, evicted = admit([self._rec("a", 100.0)], self._rec("b", 200.0), cap=3, now=300.0)
        self.assertEqual(evicted, [])
        self.assertEqual([s.session_id for s in kept], ["a", "b"])

    def test_over_cap_evicts_the_oldest(self):
        existing = [self._rec("wall", 100.0), self._rec("desk", 200.0), self._rec("phone", 300.0)]
        kept, evicted = admit(existing, self._rec("new", 400.0), cap=3, now=500.0)
        self.assertEqual([s.session_id for s in evicted], ["wall"],
                         "가장 최근에 앉은 사람을 쫓아내면 안 된다")
        self.assertEqual([s.session_id for s in kept], ["desk", "phone", "new"])

    def test_cap_one_is_todays_product(self):
        """상한 1 — 지금 dj-core 가 하는 일과 같은 답이 나와야 한다."""
        kept, evicted = admit([self._rec("desk", 100.0)], self._rec("wall", 200.0),
                              cap=1, now=300.0)
        self.assertEqual([s.session_id for s in evicted], ["desk"])
        self.assertEqual([s.session_id for s in kept], ["wall"])

    def test_same_session_id_is_a_refresh_not_a_new_device(self):
        """재발급 회전은 새 기기가 아니다 — 이걸 놓치면 30분마다 자기가 자기를 쫓아낸다."""
        kept, evicted = admit([self._rec("desk", 100.0)], self._rec("desk", 200.0),
                              cap=1, now=300.0)
        self.assertEqual(evicted, [])
        self.assertEqual([s.session_id for s in kept], ["desk"])

    def test_expired_wall_session_frees_the_slot_without_being_evicted(self):
        """12시간 지난 월 모드는 **끊긴 것이 아니라 만료된 것**이다.

        둘을 한 자루에 담으면 사람이 있지도 않은 다른 기기를 찾는다.
        """
        old_wall = self._rec("wall", 0.0, wall=True)
        now = WALL_MODE_SESSION_TTL_SECONDS + 1
        kept, evicted = admit([old_wall], self._rec("desk", now), cap=1, now=now)
        self.assertEqual(evicted, [], "만료를 축출로 세면 안내가 거짓말을 한다")
        self.assertEqual([s.session_id for s in kept], ["desk"])

    def test_wall_session_lives_the_full_twelve_hours(self):
        """11시간 59분에는 살아 있어야 한다 — 교대(8h)를 못 넘기면 절이 닫히지 않는다."""
        wall = self._rec("wall", 0.0, wall=True)
        self.assertFalse(wall.expired_at(WALL_MODE_SESSION_TTL_SECONDS - 60))
        self.assertTrue(wall.expired_at(WALL_MODE_SESSION_TTL_SECONDS))

    def test_desk_session_is_not_capped_at_twelve_hours(self):
        """자리 화면에 월 모드 수명을 적용하면 사람이 근무 중에 튕긴다."""
        desk = self._rec("desk", 0.0, wall=False)
        self.assertFalse(desk.expired_at(WALL_MODE_SESSION_TTL_SECONDS + 1))


class SessionRegistryTest(TestCase):
    """대장이 캐시여도 판정은 같아야 한다."""

    def setUp(self):
        cache.clear()          # 캐시 처리: 비움 — 이 시험의 대상이 캐시다
        self.registry = SessionRegistry()

    def test_record_and_read_back(self):
        rec = SessionRecord(session_id="a", user_id=42, started_at=100.0)
        self.assertEqual(self.registry.record(rec, cap=3, now=100.0), [])
        self.assertEqual([s.session_id for s in self.registry.active(42, now=100.0)], ["a"])

    def test_registry_evicts_oldest_like_the_pure_function(self):
        for i, sid in enumerate(("wall", "desk")):
            self.registry.record(
                SessionRecord(session_id=sid, user_id=42, started_at=100.0 + i),
                cap=2, now=100.0 + i,
            )
        evicted = self.registry.record(
            SessionRecord(session_id="phone", user_id=42, started_at=200.0), cap=2, now=200.0
        )
        self.assertEqual([s.session_id for s in evicted], ["wall"])
        self.assertEqual(
            sorted(s.session_id for s in self.registry.active(42, now=200.0)),
            ["desk", "phone"],
        )

    def test_logout_frees_the_slot(self):
        """사람이 스스로 닫은 화면은 대장에서도 지운다.

        안 지우면 닫힌 화면이 상한 한 자리를 계속 먹고, 사람은 「두 대만 켰는데
        밀려난다」를 겪는다 — 그 원인은 화면 어디에도 안 보인다.
        """
        for i, sid in enumerate(("desk", "phone")):
            self.registry.record(
                SessionRecord(session_id=sid, user_id=42, started_at=100.0 + i),
                cap=2, now=100.0 + i,
            )
        self.registry.drop(42, "desk", now=150.0)
        self.assertEqual([s.session_id for s in self.registry.active(42, now=200.0)], ["phone"])
        # 자리가 비었으니 새 화면이 아무도 밀어내지 않고 들어온다.
        evicted = self.registry.record(
            SessionRecord(session_id="wall", user_id=42, started_at=300.0), cap=2, now=300.0
        )
        self.assertEqual(evicted, [])

    def test_empty_registry_means_unknown_not_zero(self):
        """재기동하면 대장이 빈다. 그 사실을 시험이 알고 있어야 한다."""
        self.assertEqual(self.registry.active(999), [])

    def test_corrupt_row_does_not_take_the_product_down(self):
        cache.set("gx:ux24:sessions:42", "not json at all", 60)
        self.assertEqual(self.registry.active(42), [])


class CopyTest(TestCase):
    """④ 낱말 — 사전에 있는 글자 그대로인가. 여기서 문구를 만들면 사전과 갈라진다."""

    def test_copy_is_verbatim_from_the_dictionary(self):
        self.assertEqual(COPY_EVICTED, "다른 기기에서 로그인되었습니다")
        self.assertEqual(
            COPY_OVER_CAP,
            "이 계정으로 함께 쓸 수 있는 기기 수를 넘었습니다. "
            "가장 오래 켜 둔 화면을 닫았습니다.",
        )

    def test_copy_says_what_closed_not_just_that_something_happened(self):
        """「세션 만료」류로 되돌아가는 것을 막는다 — 원인을 말하지 않는 문구는 안 된다."""
        self.assertNotIn("세션", COPY_EVICTED)
        self.assertIn("가장 오래", COPY_OVER_CAP)


# ═══════════════════════════════════════════════════════════════════════════
# ⑤ 토큰 수명 — 내가 안 늘렸다는 것을 시험이 못박는다
# ═══════════════════════════════════════════════════════════════════════════

class TokenLifetimeTest(TestCase):
    """월 모드 12시간이 `NINJA_JWT` 를 요구하는가 — **요구하지 않는다** (UX-16).

    접근 토큰을 720분으로 올리면 대형 화면 한 장을 위해 **제품 전체의 탈취 창**이
    3.3시간에서 12시간으로 넓어진다. 그것은 절을 닫는 일이 아니라 보안 결정이다.
    """

    def test_token_lifetime_unchanged(self):
        self.assertEqual(
            settings.NINJA_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(), 200 * 60,
            "접근 토큰 수명이 움직였다 — 그 결정은 이 절의 것이 아니다",
        )
        self.assertEqual(
            settings.NINJA_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(), 7 * 24 * 3600
        )
        self.assertIs(settings.NINJA_JWT["ROTATE_REFRESH_TOKENS"], True,
                      "회전이 꺼지면 12시간을 잇는 다리가 끊긴다")

    def test_wall_ttl_does_not_exceed_the_refresh_token(self):
        """대장에 살아 있는데 서버는 거절하는 유령 행을 만들지 않는다."""
        self.assertLess(
            WALL_MODE_SESSION_TTL_SECONDS,
            settings.NINJA_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds(),
        )
