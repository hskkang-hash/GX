# -*- coding: utf-8 -*-
"""턴 W · 차선 U56 — **화면이 부르던 404 를 닫았는가** (`/dsm/system` · U5-BACKUP-404).

무엇을 재는가
-------------
    ① `GET /api/dsm/ops/backup/declaration` 이 **404 가 아니다** — 이것이 이 시험의 전부다.
       [실측 2026-09-19] 그 전까지 이 경로는 404 였고, 화면은 그 404 를 「백엔드 신호
       대기」 회색으로 그렸다(`CR-USER/U5U6/evidence_index.json` U5-BACKUP-404 ·
       `P-74/README.md:199` · `UX-WALK/runs/walk_20260919T062846.json`).
    ② **경로 글자가 화면이 부르는 그것과 같은가** — 한 글자라도 다르면 화면은
       여전히 404 를 받고, 그 404 는 빨강이 아니라 조용한 회색으로 그려진다.
       그래서 경로를 **frontend 의 상수와 같은 글자**로 여기에 못 박는다.
    ③ 선언이 없으면 **「미선언」이라고 말한다** — `/backup` 같은 기본값을 지어내지
       않는다(P-67: 보존 일수·백업 목적지·일정에 코드 기본값 없음).
    ④ 문지기는 그대로다 — 익명 **401** · 역할 없는 계정 **403**.
    ⑤ **읽기 문이다.** 같은 경로의 POST 는 열리지 않았다.

★ 이 문은 쓰기 면이 아니다. 선언하는 자리는 여전히 환경(`OPS_BACKUP_*`)이고,
  이 문은 그 선언을 **보여 줄 뿐** 한 칸도 바꾸지 않는다.
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client, override_settings

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture

#: ★ 화면(`frontend/src/features/dsm/api.ts :: dsmSystemEndpoint.backupDeclaration`)이
#:   부르는 **그 글자 그대로**. 여기를 고치려거든 화면도 같은 변경에서 고쳐야 한다 —
#:   둘이 갈리면 화면은 404 를 받고 그것을 회색으로 그린다(사람은 아무 빨강도 못 본다).
BACKUP_DECLARATION_PATH = "/api/dsm/ops/backup/declaration"


class TurnWBackupDeclarationDoorTest(DsmFixture):
    """`/dsm/system` 이 부르던 404 하나. 자격은 `admin` 역할이다."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        """스레드에 남은 요청을 비운다 — 안 비우면 다음 시험이 유령 사용자로 죽는다
        (메모리 「스레드에 남은 요청이 거짓 초록을 만든다」)."""
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    # ── 자격 ─────────────────────────────────────────────────────────────
    def _admin(self, user=None, group=None):
        """`admin` 역할을 **더한다**(대체하지 않는다)."""
        user = user or self.user_a
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin",
                                             defaults={"role_name": "admin"})
        role = self._own(role, group or self.group_a)
        user.roles.add(role)
        user.refresh_from_db()
        return user

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    @staticmethod
    def _body(resp):
        return json.loads((resp.content or b"{}").decode("utf-8"))

    @staticmethod
    def _text(resp):
        return (resp.content or b"")[:400].decode("utf-8", "replace")

    # ══════════════════════════════════════════════════════════════════════
    # ① · ② 문이 섰는가 — **404 가 아니다**
    # ══════════════════════════════════════════════════════════════════════
    def test_screen_path_is_no_longer_404(self):
        """★★ 닫는 조건 — 화면이 부르는 **그 경로**가 200 을 낸다."""
        admin = self._admin()
        resp = self.client.get(BACKUP_DECLARATION_PATH, **self._bearer(admin),
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertNotEqual(
            404, resp.status_code,
            "화면이 부르는 경로가 아직 404 입니다 — 경로 글자가 갈렸습니다: %s"
            % BACKUP_DECLARATION_PATH)
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        for key in ("declared", "destination", "schedule", "retention_days",
                    "restore_drill", "source", "env_names"):
            self.assertIn(key, body,
                          "화면이 읽는 칸 %r 이 응답에 없습니다." % key)

    def test_declaration_names_where_to_declare(self):
        """★ **이름을 감추지 않는다** — 고칠 자리가 응답에 이름으로 실린다.

        「설정은 기본값이 아니라 선언이다」. 「미선언」 배지만 보여 주면 관리자는
        어디를 고쳐야 하는지 코드를 읽어야 한다.
        """
        admin = self._admin()
        body = self._body(self.client.get(
            BACKUP_DECLARATION_PATH, **self._bearer(admin),
            **{"HTTP_X_NO_CACHE": "true"}))
        self.assertIn("OPS_BACKUP_DIR", body["env_names"])
        self.assertIn("OPS_BACKUP_SCHEDULE_ENABLED", body["env_names"])

    # ══════════════════════════════════════════════════════════════════════
    # ③ 선언이 없으면 **지어내지 않는다** (P-67)
    # ══════════════════════════════════════════════════════════════════════
    #: ★ [턴 X · U56 정정] 여기가 `OPS_BACKUP_RETENTION_DAYS=0` 이었다. 그때는
    #:   코드가 `0 or None` 으로 읽어 **0 과 미선언이 같은 칸**이었고, 이 시험은
    #:   그 뒤섞임을 「맞다」고 못 박고 있었다 — 시험이 결함을 지키고 있었던 것이다.
    #:   이 시험의 **이름은 「undeclared」**다. 그러니 진짜 미선언(`None`)을 준다.
    #:   0 을 선언한 갈래는 `RetentionHasNoCodeDefaultTest` ② 가 따로 잰다.
    @override_settings(OPS_BACKUP_DIR="", OPS_BACKUP_SCHEDULE_ENABLED=False,
                       OPS_BACKUP_RETENTION_DAYS=None)
    def test_undeclared_says_so_and_invents_nothing(self):
        """★ 목적지가 비면 **빈 문자열**이다 — `/backup` 을 지어내지 않는다."""
        admin = self._admin()
        resp = self.client.get(BACKUP_DECLARATION_PATH, **self._bearer(admin),
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertFalse(body["declared"])
        self.assertEqual("", body["destination"],
                         "목적지를 지어냈습니다 — P-67 뒤로 코드 기본값은 없습니다.")
        self.assertEqual("", body["schedule"])
        self.assertIsNone(body["retention_days"],
                          "선언이 없는데 수가 나왔습니다. ⚠ 예전 이 줄은 「0 은 "
                          "「모른다」입니다」라고 적혀 있었는데 그것이 틀렸다 — "
                          "0 은 **「보존하지 않는다」는 선언**이고 미선언은 `None` "
                          "이다. 둘을 한 칸에 두면 되돌릴 수 없는 삭제가 아무도 "
                          "정하지 않은 수로 돈다 (P-67).")
        self.assertEqual("UNDECLARED", body["verdict"])
        self.assertIn("OPS_BACKUP_DIR", body["reason"],
                      "무엇이 비었는지 이름으로 말하지 않았습니다.")

    @override_settings(OPS_BACKUP_DIR="/backup", OPS_BACKUP_SCHEDULE_ENABLED=True,
                       OPS_BACKUP_RETENTION_DAYS=14)
    def test_declared_reads_the_beat_table_not_a_hand_written_time(self):
        """★ 일정은 **beat 표에서** 온다 — 문서의 「매일 03:00」을 손으로 옮기지 않는다.

        beat 를 옮긴 날 화면만 옛 시각을 말하는 것을 막는다(「분모는 손으로 적지
        않는다」와 같은 결).
        """
        admin = self._admin()
        body = self._body(self.client.get(
            BACKUP_DECLARATION_PATH, **self._bearer(admin),
            **{"HTTP_X_NO_CACHE": "true"}))
        self.assertTrue(body["declared"])
        self.assertEqual("/backup", body["destination"])
        self.assertEqual(14, body["retention_days"])
        self.assertIn("common.ops_backup_beat", body["schedule"],
                      "일정이 beat 표에서 온 것이 아닙니다.")

    # ══════════════════════════════════════════════════════════════════════
    # ④ 문지기는 그대로다
    # ══════════════════════════════════════════════════════════════════════
    def test_anonymous_gets_401(self):
        """★ 이 문은 **열린 문이 아니다** — 운영 기반의 사실이 실린다."""
        resp = self.client.get(BACKUP_DECLARATION_PATH,
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(401, resp.status_code, self._text(resp))

    def test_non_admin_gets_403(self):
        """★ 역할 없는 계정은 403 — 문지기를 느슨하게 만들지 않았다."""
        resp = self.client.get(BACKUP_DECLARATION_PATH,
                               **self._bearer(self.user_a),
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(403, resp.status_code, self._text(resp))

    # ══════════════════════════════════════════════════════════════════════
    # ⑤ **읽기 문이다** — 쓰기 면이 아니다
    # ══════════════════════════════════════════════════════════════════════
    def test_post_is_not_opened_on_this_path(self):
        """★★ 이 턴에 **쓰기 면을 만들지 않았다.** 같은 경로의 POST 는 안 연다.

        선등록 표(`write_surfaces_v11.yaml` ㉡)가 「쓰기 문이 나면 적중」으로 적어
        두었다 — 안 났다는 사실을 **시험으로** 남긴다. 다음 사람이 여기에 POST 를
        더하면 이 시험이 먼저 빨개진다.
        """
        admin = self._admin()
        resp = self.client.post(BACKUP_DECLARATION_PATH, **self._bearer(admin),
                                **{"HTTP_X_NO_CACHE": "true"})
        self.assertIn(resp.status_code, (404, 405),
                      "이 경로에 쓰기 문이 생겼습니다 — 표 밖 1건으로 보고해야 합니다.")


class TurnWStorageDeclarationSourceTest(DsmFixture):
    """WS-26 — 저장 상한이 **선언인지 기본값인지** 응답이 말하는가 (P-177).

    ⚠ 값은 이 턴에 **바꾸지 않았다.** 실측 50 그대로다(세종 이의 #2 ·
      `docs/agent/evidence/P-177/저장상한_200_이의_20260918.md`). 이 시험은
      **수를 재지 않는다** — 수를 시험에 적으면 그 순간 분모를 손으로 적는 것이 된다.
    """

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _admin(self):
        user = self.user_a
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin",
                                             defaults={"role_name": "admin"})
        role = self._own(role, self.group_a)
        user.roles.add(role)
        user.refresh_from_db()
        return user

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    def test_storage_says_where_the_number_came_from(self):
        """★★ 닫는 조건 — 응답이 **이름**과 **출처**를 함께 낸다.

        이름만으로는 그 수가 누가 적은 선언인지 코드가 지어낸 기본값인지 갈리지
        않는다. 「설정은 기본값이 아니라 선언이다」.
        """
        import os

        admin = self._admin()
        os.environ.setdefault("GX_STORAGE_CAPACITY_GB", "50")
        body = json.loads(self.client.get(
            "/api/dsm/system/storage", **self._bearer(admin),
            **{"HTTP_X_NO_CACHE": "true"}).content.decode("utf-8"))
        self.assertEqual("GX_STORAGE_CAPACITY_GB", body["env_name"])
        self.assertTrue(body["capacity_source"],
                        "상한의 출처가 응답에 없습니다 — 화면이 「누가 정했나」에 "
                        "답하지 못합니다.")
        self.assertIn("GX_STORAGE_CAPACITY_GB", body["capacity_source"])

    def test_storage_source_says_undeclared_when_nobody_wrote_a_number(self):
        """★ 아무도 안 적었으면 **「선언 없음」**이라고 말한다 — 0 을 값으로 적지 않는다."""
        import os

        admin = self._admin()
        old = os.environ.pop("GX_STORAGE_CAPACITY_GB", None)
        try:
            body = json.loads(self.client.get(
                "/api/dsm/system/storage", **self._bearer(admin),
                **{"HTTP_X_NO_CACHE": "true"}).content.decode("utf-8"))
        finally:
            if old is not None:
                os.environ["GX_STORAGE_CAPACITY_GB"] = old
        self.assertFalse(body["declared"])
        self.assertIn("선언 없음", body["capacity_source"])


class TurnWRestartRequestEmptyStateTest(DsmFixture):
    """조율자 요청 2 — 「재시작 요청」 표의 **0건**이 무엇을 말해야 하는가 (차선 U24 문안).

    화면은 0건일 때 이렇게 적는다:
        「아직 올린 재시작 요청이 없습니다.」
        「위 칸에 사유를 적고 「재시작 요청」을 누르면 여기에 한 줄이 생깁니다. …」

    ★ 그 둘째 줄은 **주장**이다 — 「가만히 두면 안 생기고, 눌러야 생긴다」는 주장.
      이 시험은 그 주장을 지킨다. 사전 기본 문구(「새 자료가 생기면 이 자리에
      나타납니다」)가 이 자리에서 **거짓말**인 이유가 그것이다(차선 U24 가
      「보고서 0건」에서 잡은 것과 같은 뿌리).
    """

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _admin(self):
        user = self.user_a
        Role = apps.get_model("role", "Role")
        role, _ = Role.objects.get_or_create(code="admin",
                                             defaults={"role_name": "admin"})
        role = self._own(role, self.group_a)
        user.roles.add(role)
        user.refresh_from_db()
        return user

    def _bearer(self, user) -> dict:
        import jwt as pyjwt
        from ninja_jwt.tokens import RefreshToken

        session_id = str(uuid.uuid4())
        refresh = RefreshToken.for_user(user)
        refresh["session_id"] = session_id
        access = str(refresh.access_token)
        decoded = pyjwt.decode(
            access, settings.NINJA_JWT["SIGNING_KEY"],
            algorithms=[settings.NINJA_JWT.get("ALGORITHM", "HS256")])
        setter = getattr(user, "set_encrypted_session_token", None)
        if setter is not None:
            setter(session_id, decoded.get("jti"))
            user.save()
        return {"HTTP_AUTHORIZATION": "Bearer %s" % access}

    def test_a_tenant_with_no_requests_gets_an_empty_list_not_an_error(self):
        """★★ 화면의 `isEmpty` 가 무엇을 보고 갈라지는가 — **`requests: []`** 다.

        0건이 200 + 빈 목록으로 와야 화면이 「빈 상태」로 간다. 404 나 500 으로 오면
        화면은 「못 읽었다」를 그리고, 그 둘은 **다른 사실**이다.
        """
        admin = self._admin()
        resp = self.client.get("/api/dsm/system/requests", **self._bearer(admin),
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))
        body = json.loads(resp.content.decode("utf-8"))
        self.assertEqual([], body["requests"],
                         "요청이 없는 테넌트인데 목록이 비어 있지 않습니다.")
        self.assertEqual(0, body["total"],
                         "0건인데 total 이 0 이 아닙니다 — 분모가 거짓말합니다.")

    def test_the_row_appears_only_when_a_person_presses(self):
        """★★ 「눌러야 생긴다」가 **참인가.** 0 → (누름) → 1 을 한 판에서 본다."""
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}

        before = json.loads(
            self.client.get("/api/dsm/system/requests", **head).content.decode("utf-8"))
        self.assertEqual(0, before["total"])

        resp = self.client.post(
            "/api/dsm/system/restart-request?reason=%s" % "앞단 기동 순서 확인", **head)
        self.assertEqual(200, resp.status_code,
                         (resp.content or b"")[:300].decode("utf-8", "replace"))

        after = json.loads(
            self.client.get("/api/dsm/system/requests", **head).content.decode("utf-8"))
        self.assertEqual(1, after["total"],
                         "눌렀는데 표가 그대로입니다 — 화면 문구가 거짓이 됩니다.")
        self.assertEqual(1, len(after["requests"]))

    def test_nothing_but_that_button_creates_a_row(self):
        """★★★ **이 시험이 화면 문구를 지킨다.**

        화면은 「누르면 생깁니다」라고 적는다. 그 말이 참이려면 **행을 만드는 자리가
        그 문 하나**여야 한다. 배치·크론·시드가 이 표에 행을 만들기 시작하면
        「가만히 두면 안 생긴다」가 거짓이 되고, 그때는 **문구를 먼저 고쳐야 한다.**

        ⚠ 그래서 이 시험은 조용히 고치지 말고 **문구와 함께** 고쳐라.
        """
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent
        pattern = re.compile(r"DsmSystemRequest\s*(?:\.\w+)*\.create\(")
        makers = []
        for path in root.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel.startswith("tests/") or "/migrations/" in ("/" + rel):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if pattern.search(text):
                makers.append(rel)
        self.assertEqual(
            ["apps/dsm/api_u56.py"], sorted(makers),
            "이 표에 행을 만드는 자리가 「재시작 요청」 문 하나가 아닙니다. "
            "화면은 「누르면 생깁니다」라고 적고 있습니다 — 만드는 자리가 늘었다면 "
            "그 문구가 거짓이 된 것이므로 문구를 먼저 고쳐야 합니다: %s" % makers)


# ─────────────────────────────────────────────────────────────────────────────
# 턴 X · U56 — **내가 턴 W 에 넣은 기본값 `0` 을 뽑고, 다시 들어오지 못하게 한다**
# ─────────────────────────────────────────────────────────────────────────────
class RetentionHasNoCodeDefaultTest(DsmFixture):
    """P-67 ⑤ — **보존 일수에 코드 기본값이 없다.**

    캐시 처리: `NO_CACHE` 헤더로 응답 캐시를 우회한다(D-341). 아래 ①②③ 은 HTTP 를
      타지 않고 `backup_declaration()` 을 곧바로 부르므로 캐시가 낄 자리 자체가 없고,
      ④ 는 파일을 AST 로 읽는 정적 검사라 역시 캐시가 없다. 그래도 같은 파일의 다른
      시험과 **같은 규약**을 쓰라는 §규약에 따라 한 줄로 적는다.

    왜 이 시험이 있는가 — **턴 W 에 이 차선이 결함을 만들었다.**
        `ops_tasks.backup_declaration()` 이 `getattr(settings,
        "OPS_BACKUP_RETENTION_DAYS", 0) or 0` 으로 읽었다. 그러면 **아무도 정하지
        않았다는 사실이 화면에서 사라진다** — 「미선언」과 「0일로 선언」이 같은 칸이
        된다. 보존 일수는 **되돌릴 수 없는 삭제**를 모는 수라 그 둘이 갈려야 한다.
        `scripts/verify_retention_declared.py` ⑤ 가 그것을 잡았고, 그 판정이 옳다.

    ★ 그런데 그 판정기는 **커밋을 막지 못했다.** `.pre-commit-config.yaml` 의
      `gx-ga-readiness` 훅이 그것을 부르지만 `files:` 가
      `^docs/agent/evidence/(D-346|D-309|DA-05)/.*$` 라, 코드만 고친 커밋에는
      **한 번도 안 뜬다**[실측 2026-09-20 · 최근 다섯 커밋 391 파일 중 걸린 커밋 1].
      그래서 **같은 규칙을 시험으로도 세운다** — 시험은 차선이 실제로 돌린다.
    """

    def test_undeclared_reads_as_none_not_zero(self):
        """① 선언이 없으면 `None` 이다. `0` 이 아니다."""
        from common import ops_tasks

        with override_settings(OPS_BACKUP_RETENTION_DAYS=None,
                               OPS_BACKUP_DIR="/backup"):
            out = ops_tasks.backup_declaration()
        self.assertIsNone(
            out["retention_days"],
            "선언이 없는데 수가 나왔습니다 — 「아무도 안 정했다」가 화면에서 "
            "사라집니다 (P-67).")
        self.assertFalse(out["declared"])
        self.assertEqual("UNDECLARED", out["verdict"])
        self.assertIn("선언 없음", out["reason"],
                      "사유가 **어느 칸이 비었는지**를 말해야 합니다.")

    def test_zero_is_a_declaration_and_is_not_none(self):
        """② **`0` 과 `None` 은 다른 사실이다.**

        누군가 `0` 을 적었으면 그것은 「보존하지 않는다」는 **선언**이다.
        선언으로 치지는 않지만(`declared=False`), 화면에 `null` 로 내보내
        「아무도 안 정했다」로 보이게 하면 **거짓말**이다.
        """
        from common import ops_tasks

        with override_settings(OPS_BACKUP_RETENTION_DAYS=0,
                               OPS_BACKUP_DIR="/backup"):
            out = ops_tasks.backup_declaration()
        self.assertEqual(
            0, out["retention_days"],
            "0 으로 선언한 것이 `null` 로 나갔습니다 — 미선언과 구별이 안 됩니다.")
        self.assertFalse(out["declared"],
                         "0 일 보존을 「선언 완료」로 읽으면 안 됩니다.")
        self.assertIn("0 일로 선언됨", out["reason"])

    def test_garbage_is_undeclared_not_zero(self):
        """③ 수가 아닌 값도 **미선언**이지 0 이 아니다."""
        from common import ops_tasks

        with override_settings(OPS_BACKUP_RETENTION_DAYS="영원히",
                               OPS_BACKUP_DIR="/backup"):
            out = ops_tasks.backup_declaration()
        self.assertIsNone(out["retention_days"])
        self.assertFalse(out["declared"])

    def test_declared_days_survive(self):
        """③′ 양성 대조 — 제대로 선언하면 **그 수가 그대로** 나오고 초록이다.

        음성만 재면 「언제나 None 을 내는 함수」도 통과한다.
        """
        from common import ops_tasks

        with override_settings(OPS_BACKUP_RETENTION_DAYS=30,
                               OPS_BACKUP_DIR="/backup",
                               OPS_BACKUP_SCHEDULE_ENABLED=True):
            out = ops_tasks.backup_declaration()
        self.assertEqual(30, out["retention_days"])

    def test_no_numeric_default_in_enforcement_files(self):
        """④ ★★★ **정적 검사 — 판정기와 같은 규칙을 시험으로 세운다.**

        `scripts/verify_retention_declared.py::scan_defaults` 를 **다시 구현하지
        않고 그대로 부른다**(두 벌은 반드시 어긋난다 · D-369). 그 판정기가 훑는
        「집행하는 자리」 셋에 보존·일수 이름의 수 기본값이 하나라도 생기면 여기서
        먼저 빨개진다.

        ⚠ 판정기를 못 찾으면 **초록이 아니라 회색**(skip)이다 — 「없어서 통과」는
          이 저장소에서 가장 나쁜 초록이다.
        """
        import importlib.util
        import pathlib

        #: 컨테이너는 `/repo/scripts`, 호스트는 `<repo>/scripts` 다. 한 자리로 못
        #: 박으면 한쪽에서 조용히 건너뛰고, 건너뛴 시험은 아무것도 안 지킨다
        #: (`test_evidence_guard.py:318` 과 같은 규약).
        here = pathlib.Path(__file__).resolve()
        cands = [pathlib.Path("/repo/scripts")]
        cands += [parent / "scripts" for parent in here.parents]
        judge = None
        for cand in cands:
            if (cand / "verify_retention_declared.py").is_file():
                judge = cand / "verify_retention_declared.py"
                break
        if judge is None:
            self.skipTest(
                "scripts/verify_retention_declared.py 를 못 찾았다 — 컨테이너에 "
                "/repo/scripts 가 안 붙은 판이다. **회색이지 초록이 아니다.**")
        root = judge.parent.parent
        spec = importlib.util.spec_from_file_location("_vrd", judge)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        hits, read = mod.scan_defaults(root)
        self.assertEqual(
            3, read,
            "판정기가 훑기로 한 파일 셋 중 %d 개만 읽혔습니다 — 못 읽은 파일은 "
            "검사되지 않았고, 그것을 초록으로 세면 안 됩니다." % read)
        self.assertEqual(
            [], hits or [],
            "보존·백업 일수에 **코드 기본값**이 생겼습니다. 아무도 정하지 않은 "
            "수가 되돌릴 수 없는 삭제를 몹니다 (P-67 ⑤). 미선언은 `None` 으로 "
            "내보내고, 기본값을 `settings` 로 옮겨 숨기지 마십시오 — 같은 "
            "판정기가 그 자리에서 다시 빨개집니다: %s" % (hits,))
