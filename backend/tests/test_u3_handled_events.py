# -*- coding: utf-8 -*-
"""M1 「처리함」 · M2 「이 카메라 7일」 — 서버 면 (2026-09-17 · 턴 T · 차선 U3).

    ① `GET /api/dsm/me/handled-events` — 내가 현장 회신을 낸 사건만, 최근 회신 순.
       동료의 회신은 내 처리함에 없다. 모수(`total`)와 함께 낸다.
    ② `GET /api/dsm/events?stream_monitor_id=<id>&since=<7일 전>` — 같은 카메라로 좁힌다.
    ③ App 의 회신 감사 행 이름이 커널과 같다(두 벌이 갈리면 처리함이 빈다).

캐시 처리: 우회 — 라우트 함수를 직접 부른다(D-341).
"""
from __future__ import annotations

from datetime import timedelta

from django.test import RequestFactory
from django.utils import timezone

from common.tenant_scope import TenantScope
from tests.test_snapshot_route import _SnapshotFixture


class HandledEventsTest(_SnapshotFixture):

    def _req(self, user, path="/api/dsm/me/handled-events"):
        request = RequestFactory().get(path)
        request.user = user
        return request

    def _reply(self, user, event_id, text="도착했습니다"):
        from kernels.k1_event import reply_from_field

        return reply_from_field(scope=TenantScope.of(user), event_id=event_id, text=text)

    def test_only_events_i_replied_to_are_in_my_inbox(self) -> None:
        from apps.dsm.api_u3 import DsmU3API

        colleague = self._user("snap_user_a2", self.group_a)
        self._reply(self.user_a, self.event_id)
        self._reply(colleague, self.event_no_frame)

        mine = DsmU3API.my_handled_events(DsmU3API(), self._req(self.user_a))
        self.assertEqual(1, mine["total"])
        self.assertEqual([self.event_id], [e["event_id"] for e in mine["events"]])
        self.assertIn("last_reply_kind", mine["events"][0])

        theirs = DsmU3API.my_handled_events(DsmU3API(), self._req(colleague))
        self.assertEqual([self.event_no_frame], [e["event_id"] for e in theirs["events"]])

    def test_an_empty_inbox_is_total_zero_not_missing(self) -> None:
        from apps.dsm.api_u3 import DsmU3API

        got = DsmU3API.my_handled_events(DsmU3API(), self._req(self.user_a))
        self.assertEqual({"total": 0, "events": []}, got)

    def test_events_can_be_narrowed_to_one_camera_and_seven_days(self) -> None:
        from apps.dsm.api import DsmAPI

        since = timezone.now() - timedelta(days=7)
        got = DsmAPI.events(DsmAPI(), self._req(self.user_a, "/api/dsm/events"),
                            since=since, stream_monitor_id=self.stream.pk, limit=50)
        ids = [e["event_id"] for e in got["events"]]
        self.assertIn(self.event_id, ids)
        self.assertNotIn(self.event_no_frame, ids, "다른 카메라의 사건이 섞였습니다.")

    def test_audit_row_names_match_the_kernel(self) -> None:
        from apps.dsm import field
        from kernels.k1_event import field_reply

        self.assertEqual(field_reply.LOGGER_NAME, field.FIELD_REPLY_LOGGER)
        self.assertEqual(field_reply.ACTION, field.FIELD_REPLY_ACTION)
