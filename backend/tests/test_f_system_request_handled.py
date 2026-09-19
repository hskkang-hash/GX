# -*- coding: utf-8 -*-
"""WS-22 — **점검 창에서 한 일을 적는 문** (턴 V · 차선 F · D-492 등재 해제).

무엇을 재는가
-------------
    `POST /api/dsm/system/requests/{id}/handled` 를 **HTTP 로** 왕복한다:
    익명 401 · 비관리자 403 · 빈 메모 422 · 모르는 결말 422 · 없는 id 404 ·
    남의 테넌트 404 · 관리자 200 + **재조회에 그 값이 보인다** · 두 번째 쓰기 409.

캐시 처리: 해당 없음 — 이 문은 쓰기(`POST`)이고 응답에 캐시 머리글을 달지 않는다.
재조회는 같은 시험 안에서 **다른 요청**으로 다시 받아 본다(적중 본문을 다시 읽는 것이
아니다 · D-378 계열). 그래서 우회할 캐시도 비울 캐시도 없다.

왜 이 시험이 있어야 하는가 — **죽은 칸 하나가 살아난 자리다**
------------------------------------------------------------
`DsmSystemRequest.handled_note` 는 턴 U 에 `verify_dead_fields.DECLARED_UNWIRED` 에
「쓰는 문이 이 저장소에 없다」는 사유로 등재됐다(D-492). 이 문이 그 사유를 끝냈고,
등재는 **같은 변경에서** 지워졌다. 그러면 남는 위험은 하나다: 다음 사람이 이 문을
지우면 그 칸은 다시 죽는데, 등재가 없으니 판정기는 「새로 죽은 필드」로 그것을 잡는다.
이 시험은 그 전에 **먼저** 빨개진다.

★ 이 문은 **서버를 내리지도 올리지도 않는다.** 요청 문(`/system/restart-request`)이
  「눌렀다」와 「일어났다」를 가르려고 태어났고, 이 문은 그 둘 사이에 사람이 한 일을
  적는 칸이다. 응답의 `executed_by_app: false` 가 그 사실을 말하고, 이 시험이 그것을 잰다.

★ 요청 행을 ORM 으로 찍지 않는다 — **U56 이 세운 진짜 요청 문으로** 만든다.
  손으로 찍은 행은 제품이 만드는 행과 다를 수 있고, 다르면 이 시험은 제 손을 잰다.
"""
from __future__ import annotations

import contextlib
import json
import uuid

from django.apps import apps
from django.conf import settings
from django.test import Client

from tests.no_cache import NO_CACHE
from tests.test_dsm_app import DsmFixture

RESTART_PATH = "/api/dsm/system/restart-request"
LIST_PATH = "/api/dsm/system/requests"


def handled_path(request_id) -> str:
    return "/api/dsm/system/requests/%s/handled" % request_id


class SystemRequestHandledTest(DsmFixture):
    """점검 창 기록 문 하나. 자격은 `admin` 역할(U5 시드 계정이 실제로 갖는 그것)."""

    def setUp(self):
        super().setUp()
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def tearDown(self):
        """스레드에 남은 요청을 비운다 — 안 비우면 다음 시험의 `objects` 가 빈다."""
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    # ── 자격 ─────────────────────────────────────────────────────────────
    def _admin(self, user=None, group=None):
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

    def _a_request(self, head) -> int:
        """**진짜 요청 문으로** 요청 하나를 만든다. 돌아온 것은 그 행의 번호다."""
        resp = self.client.post(
            "%s?reason=%s" % (RESTART_PATH, "앞단 기동 순서 확인"), **head)
        self.assertEqual(200, resp.status_code, self._body(resp))
        return self._body(resp)["request_id"]

    # ── 문지기 ────────────────────────────────────────────────────────────
    def test_anonymous_cannot_write_what_happened(self) -> None:
        resp = self.client.post(handled_path(1) + "?note=x")
        self.assertEqual(401, resp.status_code)

    def test_a_non_admin_gets_403(self) -> None:
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        resp = self.client.post(handled_path(request_id) + "?note=%s" % "했다",
                                **self._bearer(self.user_b))
        self.assertEqual(403, resp.status_code)

    def test_a_missing_request_is_404(self) -> None:
        head = self._bearer(self._admin())
        resp = self.client.post(handled_path(999999) + "?note=%s" % "했다", **head)
        self.assertEqual(404, resp.status_code)

    def test_another_tenants_request_is_404_not_403(self) -> None:
        """403 은 「있는데 못 만진다」를 알려 준다 — 그것만으로 존재가 샌다(D-269)."""
        model = apps.get_model("stream_monitors", "DsmSystemRequest")
        theirs = model._base_manager.create(
            purpose_code="dsm.ops", kind="restart", reason="남의 테넌트 사유",
            status="requested", group=self.group_b)
        head = self._bearer(self._admin())
        resp = self.client.post(handled_path(theirs.pk) + "?note=%s" % "했다", **head)
        self.assertEqual(404, resp.status_code)
        theirs.refresh_from_db()
        self.assertEqual("", theirs.handled_note)

    # ── 값 ────────────────────────────────────────────────────────────────
    def test_an_empty_note_is_422(self) -> None:
        """내용 없는 「완료」는 다음 사람이 되짚을 수 없다 — 그 표가 태어난 이유다."""
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        resp = self.client.post(handled_path(request_id) + "?note=%20", **head)
        self.assertEqual(422, resp.status_code)

    def test_an_unknown_ending_is_422(self) -> None:
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        resp = self.client.post(
            handled_path(request_id) + "?note=%s&status=finished" % "했다", **head)
        self.assertEqual(422, resp.status_code)

    def test_it_cannot_be_pushed_back_to_requested(self) -> None:
        """되돌리는 문이 아니다 — 「요청됨」으로 되돌리면 한 일이 사라진다."""
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        resp = self.client.post(
            handled_path(request_id) + "?note=%s&status=requested" % "했다", **head)
        self.assertEqual(422, resp.status_code)

    # ── 쓰기 ──────────────────────────────────────────────────────────────
    def test_the_note_is_written_and_comes_back_on_re_read(self) -> None:
        """**누른 뒤를 본다** — 목록 문이 그 값을 그대로 돌려준다."""
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        note = "점검 창에서 gx-gunicorn-e 재기동 · 무중단 아님 · 2분"
        resp = self.client.post(
            "%s?note=%s&status=done" % (handled_path(request_id), note), **head)
        self.assertEqual(200, resp.status_code, self._body(resp))
        body = self._body(resp)
        self.assertEqual(note, body["handled_note"])
        self.assertEqual("done", body["status"])
        self.assertEqual("requested", body["previous_status"])
        self.assertTrue(body["was_blank"])

        listed = self._body(self.client.get(LIST_PATH, **head))
        row = next(r for r in listed["requests"] if r["request_id"] == request_id)
        self.assertEqual(note, row["handled_note"])
        self.assertEqual("done", row["status"])

    def test_the_app_still_does_not_restart_anything(self) -> None:
        """이 문도 컨테이너를 안 건드린다 — 응답이 **말로** 그것을 말한다."""
        from apps.dsm.api_f_ops import HANDLED_ACK

        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        body = self._body(self.client.post(
            handled_path(request_id) + "?note=%s" % "했다", **head))
        self.assertIs(False, body["executed_by_app"])
        self.assertEqual(HANDLED_ACK, body["message"])

    def test_scheduling_first_then_finishing_is_allowed(self) -> None:
        """「점검 창에 잡았다」 → 「했다」 — 중간 상태에도 무엇을 했는지는 적는다."""
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        first = self.client.post(
            "%s?note=%s&status=scheduled" % (handled_path(request_id), "오늘 23시 창에 잡음"),
            **head)
        self.assertEqual(200, first.status_code)
        second = self.client.post(
            "%s?note=%s&status=done" % (handled_path(request_id), "재기동 완료"), **head)
        self.assertEqual(200, second.status_code)
        body = self._body(second)
        self.assertEqual("scheduled", body["previous_status"])
        self.assertFalse(body["was_blank"])

    def test_a_finished_request_cannot_be_overwritten(self) -> None:
        """이미 끝난 요청을 덮으면 앞사람이 적은 사실이 조용히 사라진다 — **409**."""
        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        self.client.post("%s?note=%s&status=done" % (handled_path(request_id), "처음"),
                         **head)
        resp = self.client.post(
            "%s?note=%s&status=done" % (handled_path(request_id), "덮어쓰기"), **head)
        self.assertEqual(409, resp.status_code)

        listed = self._body(self.client.get(LIST_PATH, **head))
        row = next(r for r in listed["requests"] if r["request_id"] == request_id)
        self.assertEqual("처음", row["handled_note"])

    # ── 감사 ──────────────────────────────────────────────────────────────
    def test_it_leaves_one_audit_row_with_the_request_id_in_the_action(self) -> None:
        """막든 통과시키든 감사에 남는다(AC-12). 행위 이름에 **무엇을** 이 들어 있다."""
        from common import audit_writer

        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        action = "write:system:request-handled:%s" % request_id
        before = audit_writer._model()._base_manager.filter(api_name=action).count()
        body = self._body(self.client.post(
            handled_path(request_id) + "?note=%s" % "했다", **head))
        after = audit_writer._model()._base_manager.filter(api_name=action)
        self.assertEqual(before + 1, after.count())
        self.assertTrue(body["audit_id"])

    def test_a_denied_write_is_also_audited(self) -> None:
        """403 도 남는다 — 막힌 시도가 감사에 없으면 그 감사는 절반이다."""
        from common import audit_writer

        head = self._bearer(self._admin())
        request_id = self._a_request(head)
        action = "write:system:request-handled:%s" % request_id
        before = audit_writer._model()._base_manager.filter(api_name=action).count()
        resp = self.client.post(handled_path(request_id) + "?note=%s" % "했다",
                                **self._bearer(self.user_b))
        self.assertEqual(403, resp.status_code)
        self.assertEqual(
            before + 1,
            audit_writer._model()._base_manager.filter(api_name=action).count())

    # ── 죽은 칸이 아니라는 사실 ───────────────────────────────────────────
    def test_the_field_is_no_longer_declared_unwired(self) -> None:
        """등재 해제와 배선은 **같은 변경**이다 — 둘이 갈리면 판정기가 빨개진다.

        ★ 이 시험이 `scripts/` 를 읽는 이유: 문과 등재가 **다른 파일**에 살아서,
          한쪽만 되돌리는 변경이 조용히 지나갈 수 있다. 여기서 둘을 묶는다.
        """
        from pathlib import Path

        root = Path(settings.BASE_DIR).resolve().parent
        judge = root / "scripts" / "verify_dead_fields.py"
        if not judge.is_file():  # pragma: no cover - 컨테이너 마운트가 다른 경우
            self.skipTest("판정기 파일이 이 실행 환경에 마운트되지 않았다")
        text = judge.read_text(encoding="utf-8")
        head, _, _ = text.partition("BASELINE = ")
        self.assertNotIn('"stream_monitors.DsmSystemRequest.handled_note":', head)
