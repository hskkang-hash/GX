# -*- coding: utf-8 -*-
"""UX-24a — **월(wall) 표시 토큰.** 이 파일이 「쓰기 0」을 주장이 아니라 **수**로 만든다.

무엇을 못박나 — 다섯
--------------------
  ① **쓰기 0.** 쓰기 문을 여럿 이 토큰으로 두드려 **전부 거부**되는지 센다. 목록에는
     이 절이 연 두 읽기 문의 **바로 옆 쓰기 문**과 §0.4 경로가 들어간다. 「몇 개 두드려
     몇 개 거부」가 이 파일이 내는 수다.
  ② **데스크 세션이 산다.** 자리 화면으로 들어간 뒤 월 토큰으로 `/wall` 의 문을 열어도
     자리 화면이 계속 200 이다 — 그리고 `user.token` 이 **한 자도 안 바뀐다.**
     이것이 P-62 가 요구한 바로 그것이고, 이 절이 존재하는 이유다.
  ③ **경로 하나.** 목록 밖 경로는 서명이 맞아도 403 이다.
  ④ **영역 분리.** 월 토큰을 `Authorization` 에 실어도, JWT 를 `X-GX-Wall-Token` 에
     실어도 통하지 않는다. 두 문은 서로의 열쇠로 열리지 않는다.
  ⑤ **부작위** — 런타임 레지스트리에서 「월 토큰을 받는 라우트」를 전수로 읽어
     선언 목록과 **같은지** 본다. 새 라우트가 조용히 이 토큰을 받기 시작하면 빨개진다.

★ 왜 시험이 캡처보다 나은가: 캡처는 **한 번의 사실**이고 이 파일은 **매번 다시 잰다.**
  그리고 이 제품은 동시 접속이 1개라, 「월과 자리를 같이 켜 본다」를 사람이 브라우저로
  하려면 계정이 둘 필요하다 — 그러면 재려던 것(같은 계정)이 아니게 된다.

캐시 처리: **우회 + 비움** — 회수 목록이 캐시에 산다(`is_revoked`). 시험마다 비우지 않으면
앞 시험이 회수한 jti 가 다음 시험에 남는다. 응답 캐시는 `X-No-Cache` 로 우회한다
(관문을 재는 시험이 캐시를 재면 안 된다 · D-341 착시 ⑦).

절대 금지: skip·xfail 금지. 못 잰 것은 **사유와 함께 센다**.

실행
    docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
      DB_TEST_NAME=test_gx_s python -m pytest tests/test_s_wall_token.py -q \
      --nomigrations -p no:randomly --tb=short 2>/dev/null'
"""
from __future__ import annotations

import contextlib
import time
import uuid

import jwt as pyjwt
from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from ninja_jwt.tokens import RefreshToken

from common.wall_token import (
    WALL_SCREEN_PATH,
    WALL_TOKEN_HEADER,
    WALL_TOKEN_PATHS,
    WALL_TOKEN_PREFIX,
    WALL_TOKEN_READ_METHODS,
    WALL_TOKEN_TTL_SECONDS,
    JwtOrWallToken,
    WallTokenMiddleware,
    issue,
    revoke,
    verify,
    wall_token_routes,
)
from tests.no_cache import NO_CACHE

#: 시험 클라이언트가 헤더를 싣는 자리 (WSGI 환경 이름).
WALL_HEADER_ENV = "HTTP_" + WALL_TOKEN_HEADER.upper().replace("-", "_")

# ═══════════════════════════════════════════════════════════════════════════
# ★ 출생 표본 — **이 절을 만들게 한 사실** (D-310)
# ═══════════════════════════════════════════════════════════════════════════
#
# [실측 턴 E · `docs/agent/authn_paths.md` §8]
#     core/user/models.py:577   user.token = enc("<session_id>:<access_jti>")  ← 칸 하나
#     core/api/v1/auth.py:706   로그인이 그 칸을 **덮어쓴다**
#
# 그러므로 월 화면이 **로그인하면** 자리 데스크톱이 죽는다. 세종 판정 P-62 는 그 자리에서
# 물음을 바꿨다: 「월이 로그인해야 하는가?」 — **아니다. 월 모드는 세션이 필요 없다.**
# 그래서 이 절의 토큰은 로그인 문을 부르지 않고, `user.token` 을 만지지 않는다.
#
# ⚠ 아래 `DeskSessionSurvivesTest` 가 그 사실을 **매번 다시 잰다.**

#: ★ **쓰기 0 을 재는 문들.** 두 읽기 문의 바로 옆에 있는 쓰기 문 + §0.4 경로.
#:   경로에 실린 id 는 없는 것이어도 된다 — 우리가 재는 것은 **문지기이지 자원이 아니다**.
#:   (도달했다면 404/422 가 나올 자리다. 403/401 이 나와야 이 절이 참이다.)
WRITE_PROBES: tuple[tuple[str, str], ...] = (
    # ── 월 화면 바로 옆의 쓰기 문 — 관제요원이 실제로 누르는 자리들
    ("POST", "/api/dsm/events/1/review"),            # 진위 판정 (D-414)
    ("POST", "/api/dsm/events/1/response"),          # 대응 진행 접수 (D-399)
    ("POST", "/api/dsm/events/1/notify"),            # 알림 발송
    ("POST", "/api/dsm/events/1/field-reply"),       # 현장 회신
    # ── 설정 쓰기 — 여기가 열리면 월 화면 한 장이 제품 설정을 바꾼다
    ("POST", "/api/dsm/settings/thresholds"),
    ("POST", "/api/dsm/settings/zones"),
    ("POST", "/api/dsm/settings/api-keys"),          # F-05 키 발급
    ("POST", "/api/dsm/settings/grade-rules"),
    ("DELETE", "/api/dsm/settings/api-keys/1"),
    ("POST", "/api/dsm/settings/api-keys/1/rotate"),
    # ── 훈련 모드 · 벌크 등록 — 상태를 바꾸는 문
    ("POST", "/api/dsm/drill"),
    ("POST", "/api/dsm/cameras/import"),
    ("POST", "/api/dsm/webhook-subscriptions"),
    # ── ★ §0.4 금지구역. 라우트 선언에 손댈 수 없는 자리 — **미들웨어 한 겹이 덮는다**
    ("POST", "/api/delivery/etri-mock/receive-delivery"),
    ("POST", "/api/orders/banks"),
    ("POST", "/api/terminals/terminals"),
    # ── 인증 면 자체. 월 토큰으로 세션을 세우려는 시도
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/logout"),
    # ── 같은 경로, 쓰기 메서드. **목록에 있는 경로라도 쓰기는 안 된다**
    ("POST", WALL_TOKEN_PATHS[0]),
    ("PUT", WALL_TOKEN_PATHS[1]),
)

#: 목록 밖 **읽기** 문. 서명이 맞아도 닿으면 안 된다 — 「읽기니까 괜찮다」가 아니다.
READ_PROBES_OUTSIDE_SCOPE: tuple[tuple[str, str], ...] = (
    ("GET", "/api/dsm/events"),                      # 목록 전체
    ("GET", "/api/dsm/events/1"),                    # 상세
    ("GET", "/api/dsm/events/1/clip/stream"),        # ★ 원본 영상 (계약 11조 · D-306)
    ("GET", "/api/dsm/events/1/snapshot"),
    ("GET", "/api/dsm/settings/api_keys"),           # 나가는 키 표 (표 ② · D-337)
    ("GET", "/api/dsm/law/privacy-requests"),
    ("GET", "/api/dsm/metering"),
    ("GET", "/api/delivery/drone-monitoring/drone-status"),   # §0.4
)


def _clear_thread_request() -> None:
    """★ **실측된 함정** — HTTP 를 때린 시험은 스레드에 요청을 남긴다.

    [실측 2026-09-05 턴 F] 이 파일을 `tests/test_s_session_limit.py` 와 **함께** 돌렸더니
    저쪽 5건이 픽스처 만들다 죽었다:

        psycopg2.errors.ForeignKeyViolation: user_usergroup.created_by_id=(3)
        is not present in table "user_coreuser"

    뿌리는 이 파일이다. 월 토큰 미들웨어가 `request.user` 를 세우고, 그 요청이
    `thread_local.request` 에 남는다. 시험이 끝나 그 사용자는 롤백으로 사라지는데,
    **다음 시험 모듈의 `UserGroup.objects.create()` 가 그 유령을 `created_by` 로 찍는다.**

    ⚠ 이 함정은 반대 방향으로 더 위험하다: 남은 요청이 `objects` 를 조용히 **비우면**
      404 를 기대한 시험이 **오염으로 초록**이 된다. 그래서 만들기 **전**과 끝난 **뒤**
      양쪽에서 지운다 — 저장소의 다른 시험들이 이미 같은 모양을 쓴다
      (`test_c2_camera_grid.py` · `test_dsm_app.py` 외 다수).
    """
    with contextlib.suppress(Exception):
        from core.middleware.refresh_token import thread_local

        thread_local.request = None


class _ThreadCleanMixin:
    """HTTP 를 때리는 시험은 **자기가 남긴 것을 자기가 치운다.**"""

    def setUp(self):
        _clear_thread_request()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        _clear_thread_request()


def _make_user(username: str):
    CoreUser = apps.get_model("user", "CoreUser")
    UserGroup = apps.get_model("user", "UserGroup")
    Role = apps.get_model("role", "Role")

    _clear_thread_request()          # 픽스처는 유령 앞에서 선다
    group = UserGroup.objects.create(name=f"ux24a-{username}")
    UserGroup.objects.filter(pk=group.pk).update(created_by=None)
    user = CoreUser.objects.create_user(
        username=username, password="test-only-not-a-secret",
        is_active=True, email=f"{username}@test.invalid",
    )
    link_field = CoreUser._meta.get_field("userprofilelink")
    link_field.related_model.objects.create(
        **{link_field.remote_field.name: user, "group": group}
    )
    role, _ = Role.objects.get_or_create(code="operator", defaults={"role_name": "operator"})
    user.roles.set([role])
    return user


def _bind_session(user, session_id: str) -> str:
    """로그인이 하는 일 그대로 — `user.token` 을 이 세션으로 덮어쓰고 접근 토큰을 준다."""
    refresh = RefreshToken.for_user(user)
    refresh["session_id"] = session_id
    access = str(refresh.access_token)
    decoded = pyjwt.decode(
        access, settings.NINJA_JWT["SIGNING_KEY"],
        algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")],
    )
    user.set_encrypted_session_token(session_id, decoded.get("jti"))
    user.save()
    return access


# ═══════════════════════════════════════════════════════════════════════════
# ① 판정 — **순수 함수**. 저장소가 무엇이든 이 답은 같아야 한다
# ═══════════════════════════════════════════════════════════════════════════

class WallTokenVerifyTest(TestCase):
    """서명·수명·회수. 캐시 처리: **비움** — 회수 목록이 캐시에 산다."""

    def setUp(self):
        cache.clear()

    def test_issued_token_verifies(self):
        token, claims = issue(7)
        got, reason = verify(token)
        self.assertEqual(reason, "")
        self.assertEqual(got["jti"], claims["jti"])
        self.assertEqual(got["sub"], 7)
        self.assertEqual(got["screen"], WALL_SCREEN_PATH)

    def test_ttl_is_twelve_hours_exactly(self):
        """12시간은 **판정**이다 (P-62). 발급기가 다른 값을 찍기 시작하면 여기가 빨개진다."""
        self.assertEqual(WALL_TOKEN_TTL_SECONDS, 12 * 60 * 60)
        _token, claims = issue(7)
        self.assertEqual(claims["exp"] - claims["iat"], WALL_TOKEN_TTL_SECONDS)

    def test_expired_token_is_refused(self):
        now = time.time()
        token, _ = issue(7, now=now - WALL_TOKEN_TTL_SECONDS - 1)
        self.assertEqual(verify(token, now=now)[1], "expired")

    def test_long_lived_token_is_refused_even_with_valid_signature(self):
        """★ 발급기를 **우회한** 장수명 토큰. 서명이 맞아도 규약보다 길면 거절한다.

        이 갈래가 없으면 「12시간」은 발급기의 관습일 뿐 판정이 아니다 —
        서명 열쇠를 가진 코드 한 줄이 30일짜리를 찍는 순간 조용히 뚫린다.
        """
        import base64 as _b64
        import hashlib
        import hmac
        import json as _json

        from common.wall_token import _signing_key

        claims = {"v": 1, "sub": 7, "jti": "deadbeef", "iat": int(time.time()),
                  "exp": int(time.time()) + 30 * 24 * 3600, "scope": "wall",
                  "screen": WALL_SCREEN_PATH}
        payload = _b64.urlsafe_b64encode(
            _json.dumps(claims, separators=(",", ":"), sort_keys=True).encode()
        ).decode().rstrip("=")
        body = f"{WALL_TOKEN_PREFIX}.{payload}"
        sig = hmac.new(_signing_key(), body.encode(), hashlib.sha256).digest()
        forged = f"{body}.{_b64.urlsafe_b64encode(sig).decode().rstrip('=')}"

        self.assertEqual(verify(forged)[1], "ttl_too_long")

    def test_tampered_signature_is_refused(self):
        token, _ = issue(7)
        self.assertEqual(verify(token[:-2] + "xy")[1], "bad_signature")

    def test_garbage_is_refused_without_raising(self):
        for junk in ("", "nope", "a.b.c", "gxwall1.@@@.###", WALL_TOKEN_PREFIX + "."):
            claims, reason = verify(junk)
            self.assertIsNone(claims, f"쓰레기가 통과했다: {junk!r}")
            self.assertNotEqual(reason, "")

    def test_revoked_token_stops_working(self):
        token, claims = issue(7)
        self.assertEqual(verify(token)[1], "")
        revoke(claims["jti"])
        self.assertEqual(verify(token)[1], "revoked")

    def test_epoch_kills_every_token_issued_before_it(self):
        """`--all` 회수. **캐시가 아니라 설정값**이라 재기동해도 산다."""
        token, _ = issue(7, now=time.time() - 60)
        with override_settings(WALL_TOKEN_EPOCH=int(time.time())):
            self.assertEqual(verify(token)[1], "epoch")

    def test_disabled_flag_closes_the_door(self):
        token, _ = issue(7)
        with override_settings(WALL_TOKEN_ENABLED=False):
            self.assertEqual(verify(token)[1], "disabled")

    def test_signing_key_is_not_the_jwt_signing_key(self):
        """★ 영역 분리. 두 열쇠가 같으면 한쪽에서 새는 순간 다른 쪽이 함께 열린다."""
        from common.wall_token import _signing_key

        jwt_key = (settings.NINJA_JWT.get("SIGNING_KEY") or "")
        self.assertNotEqual(_signing_key(), jwt_key.encode() if isinstance(jwt_key, str) else jwt_key)
        self.assertNotEqual(_signing_key(), (settings.SECRET_KEY or "").encode())


class WallTokenJudgeTest(_ThreadCleanMixin, TestCase):
    """미들웨어의 판정만 — **HTTP 없이**. 순수하므로 갈래를 전수로 돈다."""

    def setUp(self):
        cache.clear()
        self.mw = WallTokenMiddleware(lambda request: None)
        self.token, self.claims = issue(7)

    def _judge(self, method, path, *, token=None, authz=False):
        return self.mw.judge(method=method, path=path,
                             token=self.token if token is None else token,
                             has_authorization=authz)

    def test_read_on_listed_path_passes(self):
        for path in WALL_TOKEN_PATHS:
            self.assertIsNone(self._judge("GET", path), f"열려야 할 문이 막혔다: {path}")

    def test_every_write_method_is_403_read_only(self):
        """★ **쓰기 0.** 목록에 있는 경로라도 쓰기는 못 한다 — 그리고 사유가 `read_only` 다.

        사유가 `scope_path` 로 나오면 다음 사람이 「목록을 늘리면 쓰기도 열린다」로 읽는다.
        """
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            verdict = self._judge(method, WALL_TOKEN_PATHS[0])
            self.assertEqual(verdict, (403, "read_only"), f"{method} 가 막히지 않았다")

    def test_path_outside_the_list_is_403(self):
        for _m, path in READ_PROBES_OUTSIDE_SCOPE:
            self.assertEqual(self._judge("GET", path), (403, "scope_path"), path)

    def test_two_credentials_in_one_request_are_refused(self):
        """낮은 권한 토큰이 높은 권한 헤더에 얹혀 가는 모양(혼동된 대리인)을 닫는다."""
        self.assertEqual(self._judge("GET", WALL_TOKEN_PATHS[0], authz=True),
                         (401, "two_credentials"))

    def test_read_methods_are_exactly_three(self):
        """읽기 메서드 표가 늘면 그것은 판정이지 리팩터링이 아니다."""
        self.assertEqual(set(WALL_TOKEN_READ_METHODS), {"GET", "HEAD", "OPTIONS"})


# ═══════════════════════════════════════════════════════════════════════════
# ② HTTP — **단위 시험은 함수를 부르고 브라우저는 라우트를 때린다** (D-386)
# ═══════════════════════════════════════════════════════════════════════════

class WallTokenOverHttpTest(_ThreadCleanMixin, TestCase):
    """진짜 라우트를 때린다. 캐시 처리: **우회**(`X-No-Cache`) + **비움**."""

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user("ux24a_wall")

    def setUp(self):
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)
        self.token, self.claims = issue(self.user.id)
        self.headers = {WALL_HEADER_ENV: self.token}

    def test_wall_token_opens_the_two_read_doors(self):
        """월 토큰으로 `/wall` 의 두 문이 열린다 — **세션 없이.**"""
        for path in WALL_TOKEN_PATHS:
            res = self.client.get(path, **self.headers)
            self.assertNotIn(
                res.status_code, (401, 403),
                f"월 화면이 제 문을 못 연다: {path} → {res.status_code} "
                f"{getattr(res, 'content', b'')[:200]!r}",
            )

    def test_writes_are_all_refused(self):
        """★ **쓰기 0.** 몇 개 두드려 몇 개 거부되는지 — 이 시험이 그 수다."""
        refused, opened = 0, []
        for method, path in WRITE_PROBES:
            res = self.client.generic(method, path, data=b"{}",
                                      content_type="application/json", **self.headers)
            if res.status_code in (401, 403):
                refused += 1
            else:
                opened.append((method, path, res.status_code))
        self.assertEqual(
            refused, len(WRITE_PROBES),
            f"쓰기 {len(WRITE_PROBES)}개 중 {len(opened)}개가 열렸다: {opened}",
        )

    def test_reads_outside_the_screen_are_refused(self):
        refused, opened = 0, []
        for method, path in READ_PROBES_OUTSIDE_SCOPE:
            res = self.client.generic(method, path, **self.headers)
            if res.status_code in (401, 403):
                refused += 1
            else:
                opened.append((method, path, res.status_code))
        self.assertEqual(
            refused, len(READ_PROBES_OUTSIDE_SCOPE),
            f"목록 밖 읽기 {len(READ_PROBES_OUTSIDE_SCOPE)}개 중 {len(opened)}개가 열렸다: {opened}",
        )

    def test_wall_token_in_authorization_header_does_not_work(self):
        """④ 영역 분리 — 월 토큰을 `Authorization` 에 실으면 **아무 문도 안 열린다.**

        ⚠ 여기서 재는 것은 「열리지 않는다」이지 「401 이다」가 아니다. 실측해 보니
          이 자리는 **500** 을 낸다 — 그리고 그것은 우리 것이 아니다(아래 대조군).
        """
        res = self.client.get(WALL_TOKEN_PATHS[0],
                              HTTP_AUTHORIZATION=f"Bearer {self.token}", **NO_CACHE)
        self.assertGreaterEqual(res.status_code, 400, "월 토큰이 JWT 자리에서 통했다")
        self.assertNotIn(res.status_code, (200, 204))

    def test_djcore_500s_on_any_malformed_bearer(self):
        """모양이 안 맞는 `Bearer` 는 무엇이든 **500** 이다 — 그래서 위 시험이 401 을 못 쓴다.

            core/middleware/refresh_token.py:204   jwt.decode(...)  ← 감싸지 않았다
            → jwt.exceptions.DecodeError 가 그대로 올라가 500

        ★ **이것은 새 발견이 아니다.** 저장소가 이미 알고 있고 고정해 두었다:
          `tests/test_auth_surface.py::MalformedBearerTest::test_undecodable_token_yields_500_everywhere`
          (§0.4 dj-core · 우리가 못 고친다 · D-207). 여기 같은 갈래를 한 번 더 두는 이유는
          하나다 — **이 절의 영역 분리 시험이 왜 401 을 기대하지 않는지**를 이 파일 안에서
          읽을 수 있게 하기 위해서다. 저 시험이 빨개지는 날 이 시험도 함께 빨개지고,
          그날 위 `test_wall_token_in_authorization_header_does_not_work` 를 401 로 조인다.
        """
        for junk in ("abc", "aaa.bbb.ccc"):
            res = self.client.get(WALL_TOKEN_PATHS[0],
                                  HTTP_AUTHORIZATION=f"Bearer {junk}", **NO_CACHE)
            self.assertEqual(
                res.status_code, 500,
                f"dj-core 의 깨진 Bearer 갈래가 달라졌다({junk!r} → {res.status_code}) — "
                "고쳐졌다면 이 절의 영역 분리 시험도 401 로 조여라",
            )

    def test_jwt_in_wall_header_does_not_work(self):
        """④ 반대 방향 — JWT 를 월 헤더에 실어도 통하지 않는다."""
        access = _bind_session(self.user, uuid.uuid4().hex)
        res = self.client.get(WALL_TOKEN_PATHS[0], **{WALL_HEADER_ENV: access}, **NO_CACHE)
        self.assertEqual(res.status_code, 401)

    def test_revoked_token_is_refused_over_http(self):
        revoke(self.claims["jti"])
        res = self.client.get(WALL_TOKEN_PATHS[0], **self.headers)
        self.assertEqual(res.status_code, 401)

    @override_settings(WALL_TOKEN_ENABLED=False)
    def test_kill_switch_closes_it_over_http(self):
        res = self.client.get(WALL_TOKEN_PATHS[0], **self.headers)
        self.assertEqual(res.status_code, 401)

    def test_requests_without_the_header_are_untouched(self):
        """월 토큰이 없는 요청은 **한 자도 안 만진다** — 익명은 종전대로 401 이다."""
        res = self.client.get(WALL_TOKEN_PATHS[0])
        self.assertEqual(res.status_code, 401)
        self.assertNotIn(b"read_only", res.content)
        self.assertNotIn(b"scope_path", res.content)


# ═══════════════════════════════════════════════════════════════════════════
# ③ ★ 이 절이 존재하는 이유 — **데스크 세션이 산다**
# ═══════════════════════════════════════════════════════════════════════════

class DeskSessionSurvivesTest(_ThreadCleanMixin, TestCase):
    """자리 데스크톱이 켜져 있는 채로 월을 켠다. **둘 다 산다.**

    ★ 대조군이 함께 있다: 같은 순간에 **로그인으로** 월을 켜면 자리가 죽는다
      (`test_login_as_wall_still_kills_the_desk` — 턴 E 가 고정한 그 사실).
      두 시험이 나란히 있어야 「월 토큰이 그것을 고쳤다」가 **비교로** 읽힌다.
      한쪽만 재면 어느 쪽이든 그럴듯하다 (D-411 이 남긴 교훈).
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = _make_user("ux24a_desk")

    def setUp(self):
        cache.clear()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_wall_token_does_not_touch_user_token(self):
        """자리 세션 표식(`user.token`)이 **한 자도 안 바뀐다.**"""
        desk_session = uuid.uuid4().hex
        _bind_session(self.user, desk_session)
        self.user.refresh_from_db()
        before = self.user.token

        token, _ = issue(self.user.id)
        for path in WALL_TOKEN_PATHS:
            self.client.get(path, **{WALL_HEADER_ENV: token})

        self.user.refresh_from_db()
        self.assertEqual(
            before, self.user.token,
            "월이 세션 칸을 건드렸다 — 그러면 자리 화면이 죽는다. P-62 가 깨진 것이다.",
        )

    def test_desk_stays_alive_while_the_wall_reads(self):
        """★ **닫는 조건.** 자리 → 월 → 자리. 마지막 자리 요청이 여전히 산다."""
        desk_token = _bind_session(self.user, uuid.uuid4().hex)

        first = self.client.get("/api/dsm/events?limit=1",
                                HTTP_AUTHORIZATION=f"Bearer {desk_token}", **NO_CACHE)
        self.assertNotEqual(first.status_code, 401,
                            "자리 화면이 처음부터 못 들어갔다 — 재려던 것은 그 다음이다")

        wall, _ = issue(self.user.id)
        for path in WALL_TOKEN_PATHS:
            res = self.client.get(path, **{WALL_HEADER_ENV: wall}, **NO_CACHE)
            self.assertNotIn(res.status_code, (401, 403),
                             f"월이 제 문을 못 열었다: {path} → {res.status_code}")

        again = self.client.get("/api/dsm/events?limit=1",
                                HTTP_AUTHORIZATION=f"Bearer {desk_token}", **NO_CACHE)
        self.assertEqual(
            again.status_code, first.status_code,
            "월을 켰더니 자리 화면이 달라졌다 — 이 절이 실패한 것이다 "
            f"({first.status_code} → {again.status_code})",
        )

    def test_login_as_wall_still_kills_the_desk(self):
        """대조군 — **로그인으로** 월을 켜면 자리가 죽는다. 그 벽은 §0.4 안이고 그대로다.

        이 시험이 빨개지는 날 dj-core 의 세션 벽이 걷힌 것이고, **그날이 UX-24b 를 여는 날**이다.
        """
        desk_token = _bind_session(self.user, uuid.uuid4().hex)
        first = self.client.get("/api/dsm/events?limit=1",
                                HTTP_AUTHORIZATION=f"Bearer {desk_token}", **NO_CACHE)
        self.assertNotEqual(first.status_code, 401)

        _bind_session(self.user, uuid.uuid4().hex)          # 월이 로그인한다

        again = self.client.get("/api/dsm/events?limit=1",
                                HTTP_AUTHORIZATION=f"Bearer {desk_token}", **NO_CACHE)
        self.assertEqual(
            again.status_code, 401,
            "동시 2개가 살아 있다 — dj-core 의 벽이 걷혔다. UX-24b 를 다시 열어야 한다.",
        )


# ═══════════════════════════════════════════════════════════════════════════
# ④ 부작위 — **아무도 안 열었다**를 전수로 센다 (D-300)
# ═══════════════════════════════════════════════════════════════════════════

class WallTokenSurfaceTest(TestCase):
    """런타임 레지스트리에서 읽는다 — 정적 grep 이 아니다."""

    def _surface(self):
        from common.tenant_scope import _iter_ninja_apis, _join

        for mount, api in _iter_ninja_apis():
            for prefix, router in getattr(api, "_routers", []) or []:
                for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                    for op in getattr(path_view, "operations", []) or []:
                        path = _join(mount, prefix, op_path)
                        for method in (getattr(op, "methods", []) or []):
                            yield (str(method).upper(), path,
                                   getattr(op, "auth_callbacks", None) or [])

    def test_declared_surface_is_exactly_the_two_read_doors(self):
        """월 토큰을 받는 라우트가 **정확히 둘**이다. 늘면 그 손이 개방 선언이다."""
        declared = wall_token_routes(self._surface())
        self.assertEqual(
            declared, sorted(("GET", p) for p in WALL_TOKEN_PATHS),
            f"월 토큰 진입면이 대장과 다르다: {declared}",
        )

    def test_every_declared_route_is_read_only(self):
        for method, _path in wall_token_routes(self._surface()):
            self.assertIn(method, WALL_TOKEN_READ_METHODS,
                          "월 토큰을 받는 쓰기 라우트가 있다 — 이 절의 전제가 깨졌다")

    def test_declaring_without_a_reason_is_impossible(self):
        """사유 없는 개방은 다음 사람에게 「왜 열렸는지 모르는 문」이다."""
        with self.assertRaises(ValueError):
            JwtOrWallToken(wall_token=True)
