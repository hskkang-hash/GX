# -*- coding: utf-8 -*-
"""대응 진행 축 — **앞으로만 가고, 거절은 4xx 로 나간다** (D-399).

이 파일이 묻는 것
-----------------
지시서(세종 2026-09-14)는 「거절은 HTTP 4xx이어야 하며 **200 봉투 안 오류는 실패**」라
못박았다(착시 ⑧). 그래서 두 층을 따로 본다:

    ① 규칙층 — `response_flow.transition` 이 허용/금지를 **예외로** 가르는가
    ② 라우트층 — 그 예외가 **실제 HTTP 상태**로 번역되는가.
                 셋(409·400·403)이 **서로 다른 코드**인지까지 본다 — 하나로 묶이면
                 화면이 「무엇을 고쳐 다시 보낼지」를 모른다 (D-290)

★ 그리고 **축이 섞이지 않는지**를 본다. `response_state` 를 옮겨도 `status`·`verdict`
  는 그대로여야 한다 — 섞이는 순간 D-293 이 막아 둔 오탐률 착시가 되돌아온다.
  이 시험이 이 파일에서 가장 값있는 자리다. 나머지는 규칙을 보고, 이것은 **설계**를 본다.
"""
from __future__ import annotations

from tests.test_dsm_app import DsmFixture


class _FakeRequest:
    """`_scope(request)` 와 `@tenant_scoped` 가 읽는 최소한만 든 요청.

    HTTP 클라이언트를 세우지 않는 이유: 이 시험이 묻는 것은 **예외 → 상태코드 번역**
    이지 인증 경로가 아니다. 인증은 `test_access_gate.py` 가 따로 본다 —
    한 시험이 두 가지를 물으면 어느 쪽이 깨졌는지 모른다.
    """

    def __init__(self, user):
        self.user = user
        self.auth = user
        self.headers = {}
        self.META = {}
        self.GET = {}


class ResponseFlowFixture(DsmFixture):
    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        super().setUpTestData()
        from stream_monitors.models import DetectionEvent

        cls.S = DetectionEvent.ResponseState
        cls.Event = DetectionEvent

    def _row(self, event_id):
        return self.Event._base_manager.get(pk=event_id)


class ForwardOnlyTest(ResponseFlowFixture):
    """허용 전이 셋이 지나가고, 금지 전이가 거절된다."""

    def test_the_three_forward_steps_pass_in_order(self) -> None:
        """발생 → 접수 확인 → 조치중 → 종결. **한 칸씩만 간다.**"""
        from apps.dsm import services

        eid = self._event(self.stream_a)
        self.assertEqual(self._row(eid).response_state, self.S.OCCURRED,
                         "새 이벤트는 「발생」에서 시작해야 한다")

        for to in (self.S.ACKNOWLEDGED, self.S.IN_PROGRESS, self.S.CLOSED):
            out = services.advance_response(
                scope=self.scope_a, event_id=eid, to_state=to)
            self.assertEqual(out["to"], to)
            self.assertEqual(self._row(eid).response_state, to)
            self.assertTrue(out["audit_id"], "전이마다 감사 한 줄이 남아야 한다")

    def test_skipping_a_step_is_refused(self) -> None:
        """★ `occurred → closed` 직행을 막는다.

        막지 않으면 **접수한 사람이 없는 종결**이 생기고, 그때 「아무도 안 봤는데
        닫힌 이벤트」와 「보고 닫은 이벤트」가 같아진다 (D-290).
        """
        from apps.dsm import services
        from apps.dsm.services import ResponseTransitionForbidden

        eid = self._event(self.stream_a)
        with self.assertRaises(ResponseTransitionForbidden):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state=self.S.CLOSED)
        self.assertEqual(self._row(eid).response_state, self.S.OCCURRED,
                         "거절됐으면 값이 그대로여야 한다 — 반쯤 간 상태를 만들지 않는다")

    def test_going_backwards_is_refused_except_the_one_allowed_reversal(self) -> None:
        """되돌림은 「종결 → 조치중」 하나뿐이다."""
        from apps.dsm import services
        from apps.dsm.services import ResponseTransitionForbidden

        eid = self._event(self.stream_a)
        services.advance_response(scope=self.scope_a, event_id=eid,
                                  to_state=self.S.ACKNOWLEDGED)
        with self.assertRaises(ResponseTransitionForbidden):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state=self.S.OCCURRED)

    def test_the_reversal_needs_a_reason(self) -> None:
        """★ 무엇에서 무엇으로는 표가 알고 **왜** 는 여기서만 들어온다."""
        from apps.dsm import services
        from apps.dsm.services import ResponseTransitionNeedsReason

        eid = self._event(self.stream_a)
        for to in (self.S.ACKNOWLEDGED, self.S.IN_PROGRESS, self.S.CLOSED):
            services.advance_response(scope=self.scope_a, event_id=eid, to_state=to)
        with self.assertRaises(ResponseTransitionNeedsReason):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state=self.S.IN_PROGRESS, reason="   ")

    def test_an_unknown_value_is_refused_rather_than_stored(self) -> None:
        """모르는 값을 **그대로 저장하지 않는다.** 저장하면 나중에 상태처럼 읽힌다."""
        from apps.dsm import services
        from apps.dsm.services import ResponseTransitionForbidden

        eid = self._event(self.stream_a)
        with self.assertRaises(ResponseTransitionForbidden):
            services.advance_response(scope=self.scope_a, event_id=eid,
                                      to_state="done")
        self.assertEqual(self._row(eid).response_state, self.S.OCCURRED)


class AxesStayApartTest(ResponseFlowFixture):
    """★★ **두 축이 섞이지 않는다** — D-293 이 막아 둔 자리의 재발 방지."""

    def test_moving_response_state_does_not_touch_status_or_verdict(self) -> None:
        """대응이 「종결」로 가도 `status`·`verdict` 는 그대로다.

        섞이면 무슨 일이 생기나: 대응 종결이 판정 칸을 덮고, 그러면 종결이 쌓일수록
        오탐률이 **저절로 좋아진다** — 개선이 아니라 나쁜 데이터가 사라지는 것이다.
        정확히 D-293 이 `status` 와 `verdict` 를 가른 이유이고, 지시서가 「상태를
        4값으로 바꾸라」고 했을 때 그 값을 `status` 에 넣지 않은 이유다 (D-399).
        """
        from apps.dsm import services
        from kernels.k1_event import review_event

        eid = self._event(self.stream_a)
        #: ★ 2026-09-20 (P-16) — 판정값이 `rejected` 에서 **`confirmed` 로 바뀌었다.**
        #:   시험을 고쳐 초록을 만든 것이 아니다(D-327). 바뀐 것은 **계약**이다:
        #:   세종 판정으로 「오탐이면 대응 축도 자동 종결」이 붙었고, 그러면 이 시험이
        #:   재려던 「사람이 네 칸을 걸어간다」가 애초에 일어나지 않는다 — 첫 칸에서
        #:   이미 닫혀 있다. 그 빨강은 축이 섞인 증거가 아니라 **결합이 옳게 도는 증거**다.
        #:   이 시험이 재는 것(대응 진행이 판정 칸을 덮지 않는가)은 그대로이고,
        #:   결합 자체는 `tests/test_false_positive_coupling.py` 가 따로 잰다.
        review_event(eid, verdict="confirmed", reason="시험용 정탐 판정",
                     scope=self.scope_a)
        before = self._row(eid)
        self.assertEqual(before.verdict, "confirmed")

        for to in (self.S.ACKNOWLEDGED, self.S.IN_PROGRESS, self.S.CLOSED):
            services.advance_response(scope=self.scope_a, event_id=eid, to_state=to)

        after = self._row(eid)
        self.assertEqual(after.response_state, self.S.CLOSED)
        self.assertEqual(after.status, before.status,
                         "대응 진행이 탐지 판정 칸(status)을 덮었다 — 축이 섞였다")
        self.assertEqual(after.verdict, before.verdict,
                         "대응 진행이 판정(verdict)을 덮었다 — D-293 이 막은 자리다")


class RefusalIsFourXXTest(ResponseFlowFixture):
    """거절이 **실제 HTTP 4xx 로** 나가는가 — `200 + success:false` 금지 (착시 ⑧).

    ★ 라우트를 **실제로 부른다.** 라우트 본문을 시험에 옮겨 적으면 라우트가 바뀔 때
      시험이 안 깨지고, 안 깨지는 시험은 아무것도 지키지 않는다.
    """

    def _post(self, event_id, to_state, reason="", user=None):
        from apps.dsm.api import DsmAPI

        return DsmAPI.advance_response(
            DsmAPI, _FakeRequest(user or self.user_a),
            event_id=event_id, to_state=to_state, reason=reason)

    def _status_of(self, event_id, to_state, reason="", user=None):
        from ninja.errors import HttpError

        try:
            self._post(event_id, to_state, reason=reason, user=user)
        except HttpError as exc:
            return exc.status_code
        return 200

    def test_a_forbidden_transition_is_409_not_200(self) -> None:
        """그 전이 자체가 없다 — 다시 보내도 같으므로 **409(상태 충돌)** 다.
        400 이 아닌 이유: 요청이 틀린 게 아니라 **그 자리에서 갈 수 없는 것**이다."""
        eid = self._event(self.stream_a)
        self.assertEqual(self._status_of(eid, self.S.CLOSED), 409)

    def test_a_reversal_without_reason_is_400(self) -> None:
        """사유를 채워 다시 보내면 되므로 **400** 이다."""
        eid = self._event(self.stream_a)
        for to in (self.S.ACKNOWLEDGED, self.S.IN_PROGRESS, self.S.CLOSED):
            self._post(eid, to)
        self.assertEqual(self._status_of(eid, self.S.IN_PROGRESS, reason=""), 400)

    def test_the_happy_path_is_200_and_says_where_it_can_go_next(self) -> None:
        """★ 성공 응답이 `allowed_next` 를 낸다 — 화면이 자기 전이표를 따로 들면
        서버가 거절하는 버튼을 그리게 된다. 표는 서버에 하나만 둔다."""
        eid = self._event(self.stream_a)
        out = self._post(eid, self.S.ACKNOWLEDGED)
        self.assertEqual(out["from"], self.S.OCCURRED)
        self.assertEqual(out["to"], self.S.ACKNOWLEDGED)
        self.assertEqual(out["allowed_next"], [self.S.IN_PROGRESS])

    def test_someone_elses_event_is_404_not_403(self) -> None:
        """★ 남의 테넌트 이벤트는 **404** 다 — 존재 여부가 새는 것도 누출이다.
        쓰기 라우트에도 같은 문지기가 서는지 본다 (쓰기 IDOR)."""
        eid = self._event(self.stream_b)
        self.assertEqual(
            self._status_of(eid, self.S.ACKNOWLEDGED, user=self.user_a), 404)


class BackfillMappingTest(ResponseFlowFixture):
    """이관 규칙을 **실제로 돌려 본다** (D-399 · migration 0025).

    ★ 개발 DB 는 이벤트 0행이다 [실측 2026-09-14]. 거기서 마이그레이션을 돌리면
      「0행 이관」이 나오고, **0건은 검증이 아니다**(D-301). 그래서 네 상태를 직접
      심어 놓고 이관 함수를 부른다 — 규칙이 표대로 옮기는지를 여기서 본다.

    ★ 왜 기본값만으로 부족한가: 새 칸은 `occurred` 로 채워진다. 그러면 **이미 사람이
      판정하고 종료한 이벤트도 「아무도 안 봤다」로 보인다.** 그 상태로 화면을 열면
      당직자가 끝난 일을 다시 접수한다.
    """

    def test_the_mapping_moves_each_status_to_its_own_response_state(self) -> None:
        import importlib

        from django.apps import apps as django_apps

        #: 모듈 이름이 숫자로 시작해 `import` 문으로는 못 부른다 — `import_module` 은 된다.
        mod = importlib.import_module(
            "stream_monitors.migrations.0025_backfill_response_state")
        ids = {}
        for status in ("new", "confirmed", "rejected", "closed"):
            eid = self._event(self.stream_a)
            self.Event._base_manager.filter(pk=eid).update(
                status=status, response_state=self.S.OCCURRED)
            ids[status] = eid

        mod.forwards(django_apps, None)

        expected = mod.STATUS_TO_RESPONSE
        for status, eid in ids.items():
            with self.subTest(status=status):
                self.assertEqual(self._row(eid).response_state, expected[status],
                                 f"status={status} 의 이관 결과가 표와 다르다")
        #: ★ 그리고 **판정 칸을 건드리지 않았는지**를 본다. 이관이 status 를 덮으면
        #:   D-293 이 지킨 것이 마이그레이션 한 번에 무너진다.
        for status, eid in ids.items():
            self.assertEqual(self._row(eid).status, status,
                             "이관이 status 를 덮었다 — 새 칸만 채워야 한다")
