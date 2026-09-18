# -*- coding: utf-8 -*-
"""턴 U · 차선 U56 — 「끝내기」 다섯을 **문으로** 잰다 (WS-22·WS-23 · API-03·04).

무엇을 재는가 — 다섯 절, 전부 HTTP 왕복으로
-------------------------------------------
    ① `POST /api/dsm/cameras/{id}/address`   한 대 고치기 — 404/422/감사/재조회 -1
    ② `POST /api/dsm/system/restart-request` **기록만** — 컨테이너를 안 건드린다
    ③ `GET  /api/dsm/system/backup-receipts` 회수증 — 없으면 **회색**(0 을 초록으로 적지 않는다)
    ④ `GET  /api/dsm/system/storage`         상한 미선언 → UNKNOWN 문장 · 선언 → %
    ⑤ `POST /api/dsm/settings/api-keys`      범위 · 범위 밖 403 · 익명 401 · 없는 id 404 · 422

★ 서비스 함수를 직접 부르지 않는다 — U6 은 HTTP 로만 들어온다(D-410 이 잡은 그 사각).
★ 값은 출력하지 않는다. `secret` 은 **있다는 사실**과 길이만 본다.
"""
from __future__ import annotations

import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client, override_settings

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture


class TurnUAdminSurfaceTest(DsmFixture):
    """U5·U6 의 다섯 문. 자격은 `admin` 역할(U5 시드 계정이 실제로 갖는 그것)."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        """스레드에 남은 요청을 비운다 — 안 비우면 다음 시험이 유령 사용자로 죽는다
        (`test_u56_settings_api_keys.py` 와 같은 뿌리)."""
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    # ── 자격 ─────────────────────────────────────────────────────────────
    def _admin(self, user=None, group=None):
        """`admin` 역할을 **더한다**(대체하지 않는다). 소속은 그대로 둔다."""
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
    # ① 카메라 주소 — 한 대 고치기 (U5 #5 · WS-23)
    # ══════════════════════════════════════════════════════════════════════
    def test_one_camera_address_fills_and_gap_drops_by_one(self):
        """★ 닫는 조건 — 누른 뒤 `address-gap` 의 미입력이 **-1** 이다 (서버 기록)."""
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}

        before = self._body(self.client.get("/api/dsm/cameras/address-gap", **head))
        resp = self.client.post(
            "/api/dsm/cameras/%d/address?address=%s" % (self.stream_a.pk, "경기도 안양시 만안구 안양로 123"),
            **head)
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertEqual("manual", body["address_source"],
                         "출처가 사람이 아닙니다 — 팝업으로 채워도 출처는 사람이다(D-331).")
        self.assertTrue(body["was_blank"], "빈 칸을 채운 것이 아니라 덮어썼습니다.")
        self.assertIn("audit_id", body, "주소 쓰기가 감사에 남지 않았습니다 (AC-12).")

        after = self._body(self.client.get("/api/dsm/cameras/address-gap", **head))
        self.assertEqual(before["without_address"] - 1, after["without_address"],
                         "미입력 수가 1 줄지 않았습니다 — 쓰기가 실제로 닿지 않았습니다.")

    def test_one_camera_address_rejects_other_tenant_with_404(self):
        """★ 남의 테넌트 카메라는 **404** — 403 은 그 id 가 있다는 사실을 흘린다(D-269)."""
        admin = self._admin()
        resp = self.client.post(
            "/api/dsm/cameras/%d/address?address=%s" % (self.stream_b.pk, "남의동 1"),
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(404, resp.status_code, self._text(resp))
        self.stream_b.refresh_from_db()
        self.assertFalse(self.stream_b.install_address,
                         "남의 테넌트 카메라에 주소가 써졌습니다 (쓰기 IDOR).")

    def test_one_camera_address_rejects_blank_with_422(self):
        """★ 빈 주소는 **422** — 「비운다」가 아니라 「값이 틀렸다」다."""
        admin = self._admin()
        resp = self.client.post(
            "/api/dsm/cameras/%d/address?address=%s" % (self.stream_a.pk, "%20"),
            **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(422, resp.status_code, self._text(resp))

    def test_one_camera_address_rejects_non_admin_with_403(self):
        """★ 문지기를 느슨하게 만들지 않았다 — 역할 없는 계정은 여전히 403."""
        resp = self.client.post(
            "/api/dsm/cameras/%d/address?address=%s" % (self.stream_a.pk, "안양로 1"),
            **self._bearer(self.user_a), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(403, resp.status_code, self._text(resp))

    # ══════════════════════════════════════════════════════════════════════
    # ② 재시작 **요청** — 기록만 (WS-22)
    # ══════════════════════════════════════════════════════════════════════
    def test_restart_request_records_only_and_says_so(self):
        """★★ 닫는 조건 — 행 +1 · 감사 1 · `executed: false` · 문장이 「실행은 점검 창」."""
        from apps.dsm.api_u56 import RESTART_ACK

        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        resp = self.client.post(
            "/api/dsm/system/restart-request?reason=%s" % "앞단 기동 순서 확인",
            **head)
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertFalse(body["executed"],
                         "재시작 요청이 스스로 실행됐다고 말합니다 — 이 문은 기록만 합니다.")
        self.assertEqual("requested", body["status"])
        self.assertEqual(RESTART_ACK, body["message"])
        self.assertIn("audit_id", body)

        listed = self._body(self.client.get("/api/dsm/system/requests", **head))
        self.assertEqual(1, listed["total"])
        self.assertEqual(body["request_id"], listed["requests"][0]["request_id"])

    def test_restart_request_requires_reason_422(self):
        """★ 사유 없는 요청은 **422** — 「왜 내렸는지 모르는 정지」를 남기지 않는다."""
        admin = self._admin()
        resp = self.client.post("/api/dsm/system/restart-request?reason=%20",
                                **self._bearer(admin), **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(422, resp.status_code, self._text(resp))

    def test_restart_request_rejects_non_admin_403(self):
        resp = self.client.post("/api/dsm/system/restart-request?reason=x",
                                **self._bearer(self.user_a),
                                **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(403, resp.status_code, self._text(resp))

    def test_restart_request_is_tenant_scoped(self):
        """★ 남의 테넌트 요청은 내 목록에 **안 보인다**(격리)."""
        admin_a = self._admin()
        head_a = {**self._bearer(admin_a), "HTTP_X_NO_CACHE": "true"}
        self.client.post("/api/dsm/system/restart-request?reason=%s" % "A의 사유",
                         **head_a)

        admin_b = self._admin(self.user_b, self.group_b)
        head_b = {**self._bearer(admin_b), "HTTP_X_NO_CACHE": "true"}
        listed_b = self._body(self.client.get("/api/dsm/system/requests", **head_b))
        self.assertEqual(0, listed_b["total"],
                         "남의 테넌트 재시작 요청이 보입니다 (격리 결함).")

    # ══════════════════════════════════════════════════════════════════════
    # ③ 백업 회수증 — 실물로 재고, 없으면 회색
    # ══════════════════════════════════════════════════════════════════════
    def test_backup_receipts_reads_real_manifest(self):
        """★ 회수증이 **있으면** 시각·파일·검증 가능 여부가 나온다 (실물 파일로)."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            day = Path(tmp) / "20260918"
            day.mkdir()
            (day / "manifest.json").write_text(json.dumps({
                "created_at": "2026-09-18T03:24:37+00:00",
                "db_settings": {"host": "postgres", "user": "postgres"},
                "db": {"file": "db_x.dump", "bytes": 123,
                       "rows": {"stream_monitors_streammonitor": 39}},
            }, ensure_ascii=False), encoding="utf-8")

            admin = self._admin()
            with override_settings(OPS_BACKUP_DIR=tmp):
                import os

                os.environ["GX_BACKUP_ROOT"] = tmp
                try:
                    resp = self.client.get("/api/dsm/system/backup-receipts",
                                           **self._bearer(admin),
                                           **{"HTTP_X_NO_CACHE": "true"})
                finally:
                    os.environ.pop("GX_BACKUP_ROOT", None)
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertEqual("OK", body["verdict"])
        self.assertEqual(1, body["receipts_found"])
        self.assertEqual("db_x.dump", body["last"]["db_file"])
        self.assertTrue(body["last"]["verifiable"],
                        "증인 표 행 수가 있는데 검증 불가로 읽혔습니다.")
        # ★ 접속 정보는 **나가지 않는다** — 화면이 알 일이 아니다.
        self.assertNotIn("db_settings", json.dumps(body, ensure_ascii=False))

    def test_backup_receipts_is_grey_when_none_found(self):
        """★★ 회수증이 없으면 **UNKNOWN** 이다 — 0 을 초록으로 적지 않는다(D-301)."""
        import os
        import tempfile

        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        with tempfile.TemporaryDirectory() as empty:
            os.environ["GX_BACKUP_ROOT"] = empty
            try:
                # ★ 주기를 **꺼 놓고** 잰다 — 이 환경(`retention_seed`)은 켜져 있어서,
                #   켠 채로 재면 「예정 없음 — 꺼짐」 문장이 영영 안 밟힌다.
                with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=False):
                    off = self._body(self.client.get(
                        "/api/dsm/system/backup-receipts", **head))
                with override_settings(OPS_BACKUP_SCHEDULE_ENABLED=True):
                    on = self._body(self.client.get(
                        "/api/dsm/system/backup-receipts", **head))
            finally:
                os.environ.pop("GX_BACKUP_ROOT", None)
        self.assertEqual("UNKNOWN", off["verdict"])
        self.assertEqual(0, off["receipts_found"])
        self.assertIsNone(off["last"])
        self.assertIn("꺼짐", off["next_run"],
                      "백업 주기가 꺼져 있는데 「예정 없음 — 꺼짐」을 말로 안 합니다.")
        self.assertNotIn("꺼짐", on["next_run"],
                         "켜 놓았는데 꺼졌다고 말합니다 — 두 상태가 한 문장입니다.")

    # ══════════════════════════════════════════════════════════════════════
    # ④ 저장 상한 선언 → storage_used_pct
    # ══════════════════════════════════════════════════════════════════════
    def test_storage_says_undeclared_when_capacity_missing(self):
        """★ 상한 미선언 → `declared: false` · `used_pct: null` · **그 말을 문장으로**."""
        import os

        admin = self._admin()
        old = os.environ.pop("GX_STORAGE_CAPACITY_GB", None)
        try:
            resp = self.client.get("/api/dsm/system/storage",
                                   **self._bearer(admin),
                                   **{"HTTP_X_NO_CACHE": "true"})
        finally:
            if old is not None:
                os.environ["GX_STORAGE_CAPACITY_GB"] = old
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertFalse(body["declared"])
        self.assertIsNone(body["used_pct"])
        self.assertEqual("UNKNOWN", body["verdict"])
        self.assertIn("GX_STORAGE_CAPACITY_GB", body["reason"])

    def test_storage_gives_pct_when_capacity_declared(self):
        """★ 상한이 있고 사용량을 재면 **%가 나온다.** 사용량을 못 재면 여전히 UNKNOWN."""
        import os
        from unittest import mock

        admin = self._admin()
        os.environ["GX_STORAGE_CAPACITY_GB"] = "500"
        try:
            with mock.patch("common.ops_tasks.storage_used_gb",
                            return_value=(50.0, "시험 고정값")):
                resp = self.client.get("/api/dsm/system/storage",
                                       **self._bearer(admin),
                                       **{"HTTP_X_NO_CACHE": "true"})
        finally:
            os.environ.pop("GX_STORAGE_CAPACITY_GB", None)
        body = self._body(resp)
        self.assertTrue(body["declared"])
        self.assertEqual(500.0, body["capacity_gb"])
        self.assertEqual(10.0, body["used_pct"])
        self.assertEqual("OK", body["verdict"])

    # ══════════════════════════════════════════════════════════════════════
    # ⑤ API-03·04 키 범위
    # ══════════════════════════════════════════════════════════════════════
    def _issue_key(self, head, name, scopes=None):
        url = "/api/dsm/settings/api-keys?name=%s" % name
        if scopes is not None:
            url += "&scopes=%s" % scopes.replace(":", "%3A").replace(",", "%2C")
        return self.client.post(url, **head)

    def test_issue_defaults_to_the_narrowest_scope(self):
        """★ 기본은 `events:read` **하나**다 — 전부로 두면 D-335 가 돌아온다."""
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        resp = self._issue_key(head, "u56-turn-u-default")
        self.assertEqual(200, resp.status_code, self._text(resp))
        body = self._body(resp)
        self.assertEqual(["events:read"], body["scopes"])
        self.assertTrue(body.get("secret"))

        got = self._body(self.client.get(
            "/api/dsm/settings/api-keys/%d/scopes" % body["key_id"], **head))
        self.assertEqual("set", got["state"])
        self.assertEqual(["events:read"], got["scopes"])

    def test_issue_rejects_unknown_scope_name_with_422(self):
        """★ 모르는 이름은 **422** — 조용히 버리면 발급자는 준 줄 알고 상대는 못 쓴다.

        ★★ 그리고 **키가 남지 않는다.** 이름 검사는 이제 `set_key_scopes` 안에서만
          일어나므로(공개 면을 하나로 모았다 · D-281) 검사는 발급 **뒤**에 온다.
          그 순서가 위험하지 않다는 것을 여기서 잰다 — 라우트가 발급과 범위를 한
          트랜잭션으로 묶으므로 422 는 키까지 되돌린다. 세지 않으면 「범위 없는 키가
          아무도 모르는 채 살아 있다」가 조용히 돌아온다.
        """
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        resp = self._issue_key(head, "u56-turn-u-bad", scopes="events:read,everything")
        self.assertEqual(422, resp.status_code, self._text(resp))

        # 대조군 — 좋은 이름은 **실제로 행을 만든다.** 이것이 없으면 아래 0 은
        # 「안 만들어졌다」가 아니라 「세는 눈이 멀었다」일 수 있다 (분모 0 문제).
        good = self._issue_key(head, "u56-turn-u-good", scopes="events:read")
        self.assertEqual(200, good.status_code, self._text(good))

        issued = self._issued_names()
        self.assertIn("u56-turn-u-good", issued,
                      "세는 눈이 멀었습니다 — 분모 0 위의 초록은 초록이 아닙니다.")
        self.assertNotIn("u56-turn-u-bad", issued,
                         "422 인데 키가 남았습니다 — 범위 없는 키는 아무도 모르는 채 "
                         "살아 있습니다(발급과 범위는 한 트랜잭션이어야 합니다).")

    def _issued_names(self) -> list:
        """지금 살아 있는 **들어오는 키**의 이름들. 판정은 커널 한 곳이다(D-212) —
        표를 직접 뒤지면 격리 판정이 두 벌이 되고, 두 벌은 반드시 어긋난다."""
        from kernels.k5_trust import list_keys

        return [view.name for view in list_keys(scope=self.scope_a)]

    def test_scopes_of_unknown_key_id_is_404(self):
        """★ 없는(또는 남의) 키 id 는 **404** — 존재도 새지 않는다(D-269)."""
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        resp = self.client.get("/api/dsm/settings/api-keys/9999999/scopes", **head)
        self.assertEqual(404, resp.status_code, self._text(resp))

    def test_scopes_anonymous_is_401(self):
        """★ 익명은 **401** — 인증이 없다(403 이 아니다)."""
        resp = self.client.get("/api/dsm/settings/api-keys/1/scopes",
                               **{"HTTP_X_NO_CACHE": "true"})
        self.assertEqual(401, resp.status_code, self._text(resp))

    # ══════════════════════════════════════════════════════════════════════
    # ⑥ OpenAPI — `components.schemas` ≥ 1
    # ══════════════════════════════════════════════════════════════════════
    def test_openapi_has_at_least_one_component_schema(self):
        """★ 명세가 「200 이 온다」밖에 못 말하던 상태를 깬다 (U6 #14 계열)."""
        from apps.dsm.urls import dsm_api

        schema = dsm_api.get_openapi_schema()
        schemas = (schema.get("components") or {}).get("schemas") or {}
        self.assertGreaterEqual(
            len(schemas), 1,
            "OpenAPI components.schemas 가 0 입니다 — 모양 없는 명세는 명세가 아닙니다.")
        self.assertIn("StorageOut", schemas,
                      "저장 용량 응답 모양이 명세에 없습니다: %s" % sorted(schemas))

    def test_error_envelopes_are_recorded_for_the_spec(self):
        """★ 연계 명세가 인용하는 **실제 오류 봉투**를 여기서 찍는다(401/403/404/422).

        문서에 손으로 적은 봉투는 이틀 뒤 거짓말이 된다(D-286). 이 시험이 모양을
        고정하고, `docs/design/GX-API_연계명세_v0.1.md` 가 그 모양을 인용한다.
        """
        admin = self._admin()
        head = {**self._bearer(admin), "HTTP_X_NO_CACHE": "true"}
        seen = {}
        seen[401] = self.client.get("/api/dsm/system/storage",
                                    **{"HTTP_X_NO_CACHE": "true"})
        seen[403] = self.client.post(
            "/api/dsm/system/restart-request?reason=x",
            **self._bearer(self.user_b), **{"HTTP_X_NO_CACHE": "true"})
        seen[404] = self.client.get("/api/dsm/settings/api-keys/9999999/scopes", **head)
        seen[422] = self.client.post(
            "/api/dsm/system/restart-request?reason=%20", **head)
        shapes = {}
        for code, resp in seen.items():
            self.assertEqual(code, resp.status_code,
                             "%s 자리가 %s 를 냈습니다: %s"
                             % (code, resp.status_code, self._text(resp)))
            shapes[code] = sorted(self._body(resp).keys())
        print("GX_ERROR_SHAPES " + json.dumps(shapes, ensure_ascii=False))
        # ★ 넷 다 **같은 칸 이름**을 써야 한다 — 다르면 외부 App 이 갈래마다 파서를 둔다.
        self.assertEqual(1, len({tuple(v) for v in shapes.values()}),
                         "오류 봉투의 칸 이름이 갈래마다 다릅니다: %s" % shapes)


class TurnUKeyScopeDecisionTest(DsmFixture):
    """★★ **범위 판정 그 자체** — 커널 공개 면 하나(`assert_path_scope`)로 잰다.

    왜 HTTP 가 아니라 여기인가 [실측 · 턴 U]
    ----------------------------------------
        HTTP 로는 아직 이 403 이 안 보인다 — `stats/*` 와 `cameras/pulse` 는
        `inbound_key=True` 선언이 없어 **들어오는 키를 401 로** 먼저 끊는다
        (`common/inbound_api_key.py` 기본값 거절 · D-335 ③⑤). 그 한 줄이 서는 날
        이 판정이 그대로 403 을 낸다. 지금 잴 수 있는 것은 **판정식**이고,
        그것을 회색으로 두지 않고 여기서 잰다.

    ★ [턴 U 병합] 옛 `check_request_key_scope(request, *, granted)` 를 부르지 않는다.
      커널은 HTTP 를 모르고(그 함수는 `request` 를 받았다), `granted` 를 시험이 손으로
      넘기면 **DB 도 문지기도 안 타는 판정**을 재게 된다. 지금은 키의 범위를 실제로
      저장하고, 커널이 자기 문지기로 그것을 읽어 판정한다 — 그래서 아래 ③(남의
      테넌트)이 비로소 잴 수 있는 것이 됐다.
    """

    def setUp(self):
        super().setUp()
        # 스레드에 남은 요청을 비운다 — 남아 있으면 `objects` 가 그 요청의 group 으로
        # 조용히 좁혀지고, 아래 격리 판정이 **우리 문지기가 아니라 오염**으로 초록이 된다.
        import contextlib

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

    def _key_id(self, scope, name: str) -> int:
        from kernels.k5_trust import issue_key

        return issue_key(scope=scope, name=name).view.key_id

    def test_the_gate_allows_inside_and_denies_outside(self):
        """`events:read` 키는 `events` 를 지나가고 `stats`·`pulse` 에서 막힌다."""
        from kernels.k5_trust import (KeyScopeDenied, assert_path_scope,
                                      set_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-inside")
        view = set_key_scopes(scope=self.scope_a, key_id=key_id,
                              scopes="events:read")
        self.assertEqual(("events:read",), view.scopes)

        # 범위 안 — 지나간다(예외 없음)
        assert_path_scope(scope=self.scope_a, key_id=key_id, path="/api/dsm/events")
        assert_path_scope(scope=self.scope_a, key_id=key_id, path="/api/dsm/events/12")
        # 규칙 밖 경로 — 없는 규칙을 지어내지 않는다
        assert_path_scope(scope=self.scope_a, key_id=key_id, path="/api/dsm/health")
        # 범위 밖 — **403 의 뿌리**
        for path in ("/api/dsm/stats/summary", "/api/dsm/cameras/pulse",
                     "/api/dsm/webhook-subscriptions"):
            with self.assertRaises(KeyScopeDenied, msg=path):
                assert_path_scope(scope=self.scope_a, key_id=key_id, path=path)

    def test_unset_is_false_not_everything(self):
        """★ **미설정은 거짓이다** — 범위를 정한 적 없는 옛 키가 전부 열리지 않는다."""
        from kernels.k5_trust import (KeyScopeDenied, assert_path_scope,
                                      get_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-unset")
        self.assertIsNone(get_key_scopes(scope=self.scope_a, key_id=key_id).scopes,
                          "행이 없는데 범위가 보입니다 — UNSET 과 빈 목록을 뭉쳤습니다.")
        self.assertEqual("unset",
                         get_key_scopes(scope=self.scope_a, key_id=key_id).state)
        with self.assertRaises(KeyScopeDenied):
            assert_path_scope(scope=self.scope_a, key_id=key_id,
                              path="/api/dsm/events")

    def test_an_empty_list_is_a_refusal_not_a_default(self):
        """★ `scopes=[]` 는 「아무 데도 못 간다」다 — 기본값으로 메우지 않는다."""
        from kernels.k5_trust import (KeyScopeDenied, assert_path_scope,
                                      get_key_scopes, set_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-empty")
        set_key_scopes(scope=self.scope_a, key_id=key_id, scopes="")
        self.assertEqual((), get_key_scopes(scope=self.scope_a, key_id=key_id).scopes)
        self.assertEqual("set",
                         get_key_scopes(scope=self.scope_a, key_id=key_id).state)
        with self.assertRaises(KeyScopeDenied):
            assert_path_scope(scope=self.scope_a, key_id=key_id,
                              path="/api/dsm/events")

    def test_an_unknown_scope_name_stops_the_write(self):
        """★ 모르는 이름은 `InvalidScopeName` 이고, **그 행은 바뀌지 않는다.**"""
        from kernels.k5_trust import (InvalidScopeName, get_key_scopes,
                                      set_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-bad-name")
        set_key_scopes(scope=self.scope_a, key_id=key_id, scopes="events:read")
        with self.assertRaises(InvalidScopeName):
            set_key_scopes(scope=self.scope_a, key_id=key_id,
                           scopes="events:read,everything")
        self.assertEqual(("events:read",),
                         get_key_scopes(scope=self.scope_a, key_id=key_id).scopes)

    def test_another_tenants_key_scopes_are_not_read(self):
        """★★ ③ **남의 테넌트 키는 안 읽힌다** — 문지기가 실제로 부릴 때만 참인 말이다.

        A 가 키를 만들고 범위를 넓게 준다. B 가 그 키 id 로 물으면 「행이 없다」로
        보이고(존재도 새지 않는다 · D-269), 그 UNSET 은 **거부**다. 분모를 함께 둔다:
        같은 물음을 A 가 하면 넓은 범위가 그대로 보인다 — 그래야 이 초록이
        「격리됐다」이지 「아무것도 못 읽는다」가 아니다.
        """
        from kernels.k5_trust import (KeyScopeDenied, assert_path_scope,
                                      get_key_scopes, set_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-mine")
        set_key_scopes(scope=self.scope_a, key_id=key_id,
                       scopes="events:read,stats:read")

        # 분모 — A 는 보인다
        self.assertEqual(("events:read", "stats:read"),
                         get_key_scopes(scope=self.scope_a, key_id=key_id).scopes)
        assert_path_scope(scope=self.scope_a, key_id=key_id,
                          path="/api/dsm/stats/summary")

        # ★ B 는 못 본다 — 그리고 못 보는 것이 곧 거부다
        self.assertIsNone(get_key_scopes(scope=self.scope_b, key_id=key_id).scopes,
                          "남의 테넌트 키의 범위가 읽혔습니다.")
        with self.assertRaises(KeyScopeDenied):
            assert_path_scope(scope=self.scope_b, key_id=key_id,
                              path="/api/dsm/stats/summary")

    def test_another_tenant_cannot_widen_my_key(self):
        """★ **쓰기 IDOR** — B 가 A 의 키 범위를 덮어쓸 수 없고, 거부는 **거부로** 말한다.

        ⚠ [실측 · 턴 U 병합] 문지기를 붙이자마자 이 자리가 `IntegrityError` 로
          죽었다 — B 에게 A 의 행이 안 보이니 「없으니 만든다」로 이어졌고,
          유일 제약(`dsm_api_key_scope_one_live_per_key`)이 그것을 막았다. 범위는
          지켜졌지만 답이 **DB 오류**였고, DB 오류는 라우트에서 500 이 된다.
          그래서 커널이 먼저 `InboundKeyNotFound` 로 끊는다(없는 것과 같다 · D-269).
        """
        from kernels.k5_trust import (InboundKeyNotFound, get_key_scopes,
                                      set_key_scopes)

        key_id = self._key_id(self.scope_a, "u56-scope-widen")
        set_key_scopes(scope=self.scope_a, key_id=key_id, scopes="events:read")

        with self.assertRaises(InboundKeyNotFound):
            set_key_scopes(scope=self.scope_b, key_id=key_id,
                           scopes="events:read,stats:read,webhooks:manage")

        self.assertEqual(("events:read",),
                         get_key_scopes(scope=self.scope_a, key_id=key_id).scopes,
                         "남의 테넌트가 내 키의 범위를 넓혔습니다 (쓰기 IDOR).")

    def test_the_kernel_does_not_know_http(self):
        """★ 커널 공개 면에 `request` 를 받는 함수가 없다 — 요청을 아는 자리는
        `common/inbound_api_key.py` 하나다(D-335 · 턴 U 병합).

        이름으로만 재지 않고 **시그니처**로 잰다: 이름을 지워도 다음 사람이 같은
        모양을 다시 만들 수 있기 때문이다.
        """
        import inspect

        from kernels.k5_trust import key_scopes

        public = [(n, f) for n, f in vars(key_scopes).items()
                  if inspect.isfunction(f) and not n.startswith("_")
                  and f.__module__ == key_scopes.__name__]
        self.assertTrue(public, "공개 함수를 한 개도 못 셌습니다 — 분모 0 입니다.")
        for name, fn in public:
            params = inspect.signature(fn).parameters
            self.assertNotIn("request", params,
                             "%s 가 request 를 받습니다 — 커널은 HTTP 를 모릅니다." % name)
            self.assertIn("scope", params,
                          "%s 에 scope 가 없습니다 (D-281)." % name)
            self.assertEqual(inspect.Parameter.KEYWORD_ONLY,
                             params["scope"].kind,
                             "%s 의 scope 가 키워드 전용이 아닙니다 (D-281)." % name)
