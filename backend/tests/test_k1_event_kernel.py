# -*- coding: utf-8 -*-
"""K1 이벤트 커널 — **이중 AC 시험** (DA-04 §2 K1 · D-275 EXIT 승인 후 착수).

★ 이 파일은 구현보다 **먼저** 쓰였다.
--------------------------------------
지시(2026-08-28 §5⑥): "K1 이벤트 커널 착수 — **이중 AC 테스트 먼저**".
그래서 이 파일이 `backend/kernels/k1_event/` 보다 먼저 커밋 트리에 들어왔고,
첫 실행은 `ModuleNotFoundError` 로 빨간불이었다. 그 빨간불이 이 시험의 **양성 대조**다 —
구현이 없을 때 빨갛지 않은 시험은 구현이 있을 때도 초록의 뜻이 없다 (D-277).

이중 AC 란 (DA-04 §1-2)
-----------------------
커널 티켓은 `[F-xx 계약 AC]` + `[U-x 상품 AC]` 로 이중 태깅한다.
**충돌 시 계약 AC 가 우선**한다 — 계약 AC 는 검수 기준(7조3항)이고 상품 AC 는 우리 목표다.

  · **F-04** 동일 이벤트 5분 내 중복 **알림** 0건
  · **F-05** OpenAPI 제공 · p95 500ms
  · **U1**  증거 확보 클릭 수 ≤ 3 · 오탐률 수치화

★ 이 셋이 한 지점에서 충돌한다 — DA-04 가 그 해법을 이미 적었다
---------------------------------------------------------------
    중복 억제는 **기록 단계**(10초·이벤트)와 **알림 단계**(5분·K2)를 나눈다.
    이벤트를 접으면 U1 의 오탐률 분모가 거짓이 되므로 **이벤트는 남기고 알림만 접는다.**

그래서 아래 `DedupSplitTest` 가 **이벤트 수 ≠ 알림 수**를 단언한다.
둘이 같아지는 순간 F-04 를 지키려다 U1 의 분모를 깨뜨린 것이고, 그 반대도 마찬가지다.
이것이 이 파일에서 가장 중요한 시험이다.

무엇을 **아직 못 재나** — 지우지 않고 적는다 (D-262)
----------------------------------------------------
**F-05 의 p95 500ms 는 이 시험이 재지 못한다.** 부하도 데이터도 없다.
1건짜리 픽스처에서 잰 응답 시간은 500ms 를 통과하겠지만 그 초록은 아무 뜻이 없다 —
모수 2 위에서 "누락 1건"을 말하던 것과 같은 착시다 (D-271).
대신 지금 잴 수 있는 것을 잰다: **쿼리 수**(N+1 없음)와 **서버 필터 여부**.
p95 는 W2-3 화면이 서고 실데이터가 쌓인 뒤 별도로 잰다.
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.http import Http404
from django.test import TestCase
from django.utils import timezone


class K1Fixture(TestCase):
    """테넌트 A/B 와 각자의 스트림 하나씩. `test_tenant_isolation` 의 픽스처 규약을 따른다."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        CoreUser = apps.get_model("user", "CoreUser")
        UserGroup = apps.get_model("user", "UserGroup")
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")

        # 스레드 로컬에 남은 이전 시험의 요청을 지운다 (D-253 배선).
        # 남겨 두면 dj-core 가 created_by 를 롤백된 사용자 id 로 채우고 teardown 이 터진다.
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="k1-tenant-A")
        cls.group_b = UserGroup.objects.create(name="k1-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._make_user("k1_user_a", cls.group_a)
        cls.user_b = cls._make_user("k1_user_b", cls.group_b)

        cls.stream_a = cls._make_stream("k1-stream-A", cls.group_a)
        cls.stream_b = cls._make_stream("k1-stream-B", cls.group_b)

        # ── D-281 스코프 두 벌 ────────────────────────────────────────────
        # 커널 공개 함수는 `*, scope: TenantScope` 를 **필수**로 받는다. 시험도 예외가
        # 아니다 — 시험이 우회 경로를 쓰면 그 우회가 곧 다음 사람의 본보기가 된다.
        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        # 검출 파이프라인에는 요청자가 없다. 사유를 적어 등재한다(면제가 아니다).
        cls.scope_pipe = TenantScope.system(
            reason="검출 파이프라인 시험 — gRPC 콜백에는 요청자가 없다 (D-281)")

    @classmethod
    def _make_user(cls, username: str, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_model = link_field.related_model
        link_model.objects.create(**{link_field.remote_field.name: user, "group": group})
        return user

    @classmethod
    def _make_stream(cls, name: str, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        sm = StreamMonitor.objects.create(name=name, code=name, ip_source="rtsp://test.invalid/x")
        # 소유 필드는 환경에 따라 `groups`(M2M) 또는 `group`(FK) 이다 — 저장소 소스와
        # 실행 중인 dj-core 가 다르다(P-LOCAL-4 미결). 픽스처가 한쪽을 박으면 다른 환경에서
        # **시험이 조용히 판정 불가가 된다.** 커널이 쓰는 판단기를 그대로 쓴다.
        from kernels.k1_event.services import _owner_field

        if _owner_field(StreamMonitor) == "groups":
            sm.groups.set([group])
        else:
            sm.group = group
            sm.save(update_fields=["group"])
        return sm


# ═══════════════════════════════════════════════════════════════════════════
# [F-04 계약 AC] × [U1 상품 AC] — 기록 10초 / 알림 5분 을 **가른다**
# ═══════════════════════════════════════════════════════════════════════════
class DedupSplitTest(K1Fixture):
    """★ 이 파일에서 가장 중요한 시험.

    F-04 만 보면 "5분 내 같은 것은 하나로 접어라"가 되고, 그렇게 접으면
    U1 의 오탐률 분모(= 실제 검출 수)가 거짓이 된다.
    DA-04 의 해법은 **두 창을 나누는 것**이다 — 이벤트는 10초, 알림은 5분.
    """

    def test_folded_records_do_not_notify_again(self) -> None:
        """[F-04] ★ **접힌 관측은 알림을 다시 내지 않는다.**

        접혔다는 것은 **같은 이벤트**라는 뜻이고, F-04 는 "동일 이벤트 5분 내 중복 알림
        0건"이다. 그러니 접힘 → 알림 없음이어야 한다.

        ★ 이 시험은 결함을 **잡고 나서** 생겼다 (W2-2 배선 시험이 먼저 잡았다).
          같은 배치에 같은 검출 3연발 → 이벤트는 1건으로 접혔는데 `should_notify` 가
          **세 번 다 참**이었다. 원인은 알림 질의가 `.exclude(pk=event.pk)` 로 자기 자신을
          빼는데, 접히면 `event` 가 **기존 이벤트**여서 유일한 "이전 것"이 매번 제외된 것이다.

          `test_event_count_and_notify_count_differ` 는 30초 간격이라 매번 **새 이벤트**였고,
          그래서 이 갈래를 한 번도 지나가지 않았다. 시나리오가 초록이어도 갈래가 안 덮이면
          못 잡는다 — 착시 ②(D-262)의 작은 판이다.
        """
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        results = [
            k1.record_detection(
                scope=self.scope_pipe,
                stream_monitor_id=self.stream_a.id, event_type="smoke",
                severity="critical", occurred_at=t0 + timedelta(seconds=i * 3),
            )
            for i in range(3)                       # 3초 간격 — 전부 10초 창 안이다
        ]

        # 대상별 표를 낸다 — **실패는 뒤를 가리지 않는다** (D-274 승격 원칙).
        table = [(i, r.created, r.folded_into_existing, r.should_notify)
                 for i, r in enumerate(results)]
        detail = "\n".join(
            f"  #{i} created={c} folded={f} should_notify={n}" for i, c, f, n in table)

        self.assertEqual([r.created for r in results], [True, False, False],
                         f"10초 창이 안 먹었다\n{detail}")
        self.assertEqual(
            [r.should_notify for r in results], [True, False, False],
            f"접힌 관측이 알림을 다시 냈다 — 같은 이벤트인데 K2 가 여러 번 보낸다 "
            f"(F-04 위반)\n{detail}")

        # 이벤트는 **하나뿐**이다. 접힘이 이벤트를 늘리지 않는다 (U1 분모는 관측이 아니라 이벤트).
        self.assertEqual(len({r.event_id for r in results}), 1, detail)

    def test_records_within_10s_fold_into_one_event(self) -> None:
        """[F-04] 같은 stream+type 이 10초 안에 재발하면 **이벤트는 1건**이고 last_seen 만 는다."""
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        first = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical",
            occurred_at=t0, confidence=0.91, snapshot_path="minio://snap/1.jpg",
        )
        second = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical",
            occurred_at=t0 + timedelta(seconds=7), confidence=0.88,
            snapshot_path="minio://snap/2.jpg",
        )

        self.assertEqual(first.event_id, second.event_id,
                         "10초 안의 같은 stream+type 이 새 이벤트를 만들었습니다 (F-04 위반).")
        self.assertTrue(first.created, "첫 기록이 새 이벤트로 잡히지 않았습니다.")
        self.assertFalse(second.created, "두 번째 기록이 새 이벤트로 잡혔습니다.")

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event.objects.get(pk=first.event_id)
        self.assertIsNotNone(row.last_seen_at, "접힌 기록이 last_seen_at 을 갱신하지 않았습니다.")
        self.assertGreater(row.last_seen_at, row.occurred_at)

    def test_records_beyond_10s_make_a_new_event(self) -> None:
        """[U1] 10초를 넘기면 **새 이벤트**다 — 접으면 오탐률 분모가 거짓이 된다.

        ★ 이것이 음성 대조다. 위 시험만 있으면 "전부 접는" 구현도 통과한다.
        """
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        first = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_a.id, event_type="smoke", severity="warning",
            occurred_at=t0, snapshot_path="minio://snap/a.jpg",
        )
        later = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_a.id, event_type="smoke", severity="warning",
            occurred_at=t0 + timedelta(seconds=11), snapshot_path="minio://snap/b.jpg",
        )
        self.assertNotEqual(first.event_id, later.event_id,
                            "10초를 넘긴 검출이 접혔습니다 — 오탐률 분모가 거짓이 됩니다 (U1 위반).")
        self.assertTrue(later.created)

    def test_event_count_and_notify_count_differ_in_five_minutes(self) -> None:
        """★★ **이벤트 수 ≠ 알림 수** — 두 AC 를 한 구현으로 만족시키는 지점.

        5분 동안 30초 간격으로 5회 검출:
          · 이벤트(10초 창)  → **5건**  ← U1 오탐률 분모가 살아 있다
          · 알림(5분 창)     → **1건**  ← F-04 "5분 내 중복 알림 0건"
        """
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        results = [
            k1.record_detection(
            scope=self.scope_pipe,
                stream_monitor_id=self.stream_a.id, event_type="intrusion", severity="critical",
                occurred_at=t0 + timedelta(seconds=30 * i), snapshot_path=f"minio://s/{i}.jpg",
            )
            for i in range(5)
        ]

        event_ids = {r.event_id for r in results}
        notify_count = sum(1 for r in results if r.should_notify)

        self.assertEqual(
            len(event_ids), 5,
            f"이벤트가 {len(event_ids)}건으로 접혔습니다. 5분 창으로 이벤트를 접으면 "
            "U1 의 오탐률 분모가 거짓이 됩니다 — 이벤트는 남기고 알림만 접습니다 (DA-04 K1).",
        )
        self.assertEqual(
            notify_count, 1,
            f"알림이 {notify_count}건입니다. F-04 는 동일 이벤트 5분 내 중복 알림 **0건**을 요구합니다.",
        )

    def test_a_different_stream_is_never_folded(self) -> None:
        """다른 스트림의 같은 유형은 접히지 않는다 — 접히면 남의 테넌트 것과 합쳐진다."""
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        a = k1.record_detection(scope=self.scope_pipe, stream_monitor_id=self.stream_a.id, event_type="person",
                                severity="info", occurred_at=t0, snapshot_path="minio://a.jpg")
        b = k1.record_detection(scope=self.scope_pipe, stream_monitor_id=self.stream_b.id, event_type="person",
                                severity="info", occurred_at=t0 + timedelta(seconds=1),
                                snapshot_path="minio://b.jpg")
        self.assertNotEqual(a.event_id, b.event_id,
                            "다른 스트림의 검출이 접혔습니다 — 테넌트를 넘어 합쳐집니다.")


# ═══════════════════════════════════════════════════════════════════════════
# [F-05 계약 AC] × [U1 상품 AC] — 조회는 **서버에서** 거른다
# ═══════════════════════════════════════════════════════════════════════════
class ServerSideFilterTest(K1Fixture):
    """DA-04: "3클릭이 되려면 조회 API 가 **필터를 서버에서 처리**해야 한다
    (클라이언트 필터는 클릭을 늘린다)." 그 문장을 시험으로 바꾼다.
    """

    def setUp(self) -> None:
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        self.rows = []
        for i, (etype, sev) in enumerate(
            [("fire", "critical"), ("smoke", "warning"), ("person", "info"),
             ("fire", "warning"), ("vehicle", "info")]
        ):
            self.rows.append(k1.record_detection(
            scope=self.scope_pipe,
                stream_monitor_id=self.stream_a.id, event_type=etype, severity=sev,
                occurred_at=t0 - timedelta(minutes=i * 10), snapshot_path=f"minio://f/{i}.jpg",
            ))

    def test_query_filters_by_type_severity_and_period_on_the_server(self) -> None:
        """[F-05 · U1] 필터가 서버에서 적용된다 — 반환된 수가 곧 필터 결과여야 한다."""
        from kernels.k1_event import services as k1

        got = k1.query_events(scope=self.scope_a, event_type="fire")
        self.assertEqual(
            [e.event_type for e in got], ["fire", "fire"],
            "event_type 필터가 서버에서 적용되지 않았습니다 — 클라이언트가 다시 걸러야 하고, "
            "그만큼 클릭이 늡니다 (U1 3클릭 위반).",
        )

        got = k1.query_events(scope=self.scope_a, severity="critical")
        self.assertEqual(len(got), 1, "severity 필터가 서버에서 적용되지 않았습니다.")

        got = k1.query_events(scope=self.scope_a, since=timezone.now() - timedelta(minutes=15))
        self.assertEqual(len(got), 2, "기간 필터가 서버에서 적용되지 않았습니다.")

    def test_query_does_not_do_n_plus_one(self) -> None:
        """[F-05] p95 500ms 를 **직접 재지는 못한다.** 지금 잴 수 있는 것을 잰다.

        1건짜리 픽스처의 응답 시간으로 p95 를 말하는 것은 모수 없는 초록이다 (D-271).
        대신 N+1 이 없는지를 본다 — p95 를 깨는 가장 흔한 원인이고, 이것은 지금 잴 수 있다.

        ★ **고정된 쿼리 수를 단언하지 않는다.** 그러면 `get_user_group` 같은 고정 비용이
          하나 늘 때마다 시험이 깨지고, 깨진 시험은 숫자만 올려서 고쳐진다.
          여기서 묻는 것은 하나다 — **행이 늘 때 쿼리가 같이 느는가.**
        """
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        from kernels.k1_event import services as k1

        def count_queries(limit: int) -> int:
            with CaptureQueriesContext(connection) as ctx:
                rows = k1.query_events(scope=self.scope_a, limit=limit)
                _ = [(e.event_type, e.stream_monitor_name) for e in rows]  # 관련 필드까지 만진다
            return len(ctx.captured_queries)

        few, many = count_queries(1), count_queries(50)
        self.assertEqual(
            few, many,
            f"행 1건일 때 {few}쿼리, 여러 건일 때 {many}쿼리입니다 — 행 수에 따라 쿼리가 늡니다(N+1). "
            "p95 500ms(F-05)를 깨는 가장 흔한 원인입니다. select_related 를 확인하십시오.",
        )

    def test_paging_is_server_side(self) -> None:
        from kernels.k1_event import services as k1

        page1 = k1.query_events(scope=self.scope_a, limit=2, offset=0)
        page2 = k1.query_events(scope=self.scope_a, limit=2, offset=2)
        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 2)
        self.assertFalse({e.event_id for e in page1} & {e.event_id for e in page2},
                         "페이지가 겹칩니다 — 서버 페이징이 아닙니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 테넌트 격리 — WP-2 가 봉인한 것을 커널이 물려받는다
# ═══════════════════════════════════════════════════════════════════════════
class KernelTenantScopeTest(K1Fixture):
    """DA-04: `query_events` 는 **테넌트 스코프 강제**, `get_event` 는 남의 것이면 **404**.

    ★ 양성 대조를 먼저 둔다 (D-277). "남의 것이 안 보인다"만 시험하면
      **아무것도 안 보이는 구현**도 통과한다 — WP-2 EXIT §5-2 의 목록 5종이 그 상태였다.
    """

    def setUp(self) -> None:
        from kernels.k1_event import services as k1

        now = timezone.now()
        self.mine = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical",
            occurred_at=now, snapshot_path="minio://mine.jpg",
        )
        self.theirs = k1.record_detection(
            scope=self.scope_pipe,
            stream_monitor_id=self.stream_b.id, event_type="fire", severity="critical",
            occurred_at=now, snapshot_path="minio://theirs.jpg",
        )

    def test_positive_control_own_event_is_found(self) -> None:
        """★ 양성 대조 — 자기 테넌트의 이벤트는 **실제로 찾아진다.**

        이 시험이 빨간불이면 아래 격리 시험들은 '통과'가 아니라 **판정 불가**다.
        """
        from kernels.k1_event import services as k1

        ids = {e.event_id for e in k1.query_events(scope=self.scope_a)}
        self.assertIn(self.mine.event_id, ids,
                      "자기 테넌트의 이벤트조차 목록에서 찾지 못했습니다 — "
                      "아래 '남의 것이 안 보인다'는 통과가 아니라 판정 불가입니다 (D-277).")
        self.assertIsNotNone(k1.get_event(self.mine.event_id, scope=self.scope_a))

    def test_query_events_excludes_other_tenant(self) -> None:
        from kernels.k1_event import services as k1

        ids = {e.event_id for e in k1.query_events(scope=self.scope_a)}
        self.assertNotIn(self.theirs.event_id, ids,
                         "남의 테넌트 이벤트가 목록에 섞였습니다.")

    def test_get_event_of_other_tenant_is_404_not_empty_200(self) -> None:
        """남의 것은 **없는 것과 같아야** 한다 — 200+빈 응답을 새로 만들지 않는다 (W0-18)."""
        from kernels.k1_event import services as k1

        with self.assertRaises(Http404):
            k1.get_event(self.theirs.event_id, scope=self.scope_a)

    def test_review_and_close_of_other_tenant_are_404(self) -> None:
        """쓰기 경로도 같다 — 읽기만 막고 쓰기를 열어 두는 것이 W0-14c 가 잡은 결함이었다."""
        from kernels.k1_event import services as k1

        with self.assertRaises(Http404):
            k1.review_event(self.theirs.event_id, verdict="rejected",
                            reason="probe", scope=self.scope_a)
        with self.assertRaises(Http404):
            k1.close_event(self.theirs.event_id, scope=self.scope_a)

    def test_review_records_the_verdict_for_false_positive_rate(self) -> None:
        """[U1] 오탐률 수치화의 입력 — 판정과 판정자가 남아야 K6 가 셀 수 있다."""
        from kernels.k1_event import services as k1

        out = k1.review_event(self.mine.event_id, verdict="rejected",
                              reason="빛 반사", scope=self.scope_a)
        self.assertEqual(out.status, "rejected")

        Event = apps.get_model("stream_monitors", "DetectionEvent")
        row = Event.objects.get(pk=self.mine.event_id)
        self.assertEqual(row.reviewed_by_id, self.user_a.id,
                         "판정자가 안 남으면 오탐률을 누가 매겼는지 알 수 없습니다.")
        self.assertIsNotNone(row.reviewed_at)
        self.assertEqual(row.reject_reason, "빛 반사")

    def test_rejected_event_is_not_deleted(self) -> None:
        """기각은 **분모에서 빼는 것이 아니다.** 행이 사라지면 오탐률을 셀 수 없다."""
        from kernels.k1_event import services as k1

        k1.review_event(self.mine.event_id, verdict="rejected", reason="x", scope=self.scope_a)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertTrue(Event.objects.filter(pk=self.mine.event_id).exists(),
                        "기각된 이벤트가 사라졌습니다 — 오탐률 분자가 함께 사라집니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 계층 — 커널의 공개 면은 서비스 함수다 (DA-04 §1-4 · D-278)
# ═══════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════
# [D-281] 스코프는 **표식이 아니라 시그니처다**
# ═══════════════════════════════════════════════════════════════════════════
class KernelScopeSignatureTest(K1Fixture):
    """커널 공개 함수를 **스코프 없이 부를 수 있는가.**

    ★ 왜 게이트가 있는데 시험도 두나 — 같은 것을 두 번 세는 것이 아니다.
      `scripts/verify_tenant_scope.py` 는 **소스를 AST 로 읽어** 인자가 선언돼 있는지 본다.
      여기서는 **실제로 불러 본다.** 선언은 맞는데 런타임에 통과해 버리는 경우
      (기본값·`**kwargs` 흡수·데코레이터가 인자를 삼키는 경우)를 정적 눈은 못 본다.
      한 판정을 두 각도에서 먹인다 — 트립와이어가 정적 눈·런타임 눈 둘을 둔 것과 같은 계열.

    D-281: *"데코레이터는 '붙였는가'만 보지만, 필수 인자는 **부르는 쪽이 테넌트를
    알아야만** 호출된다. 표식이 아니라 구조다 — 우회할 자리가 없다."*
    """

    #: DA-04 §2 K1 공개 면 6개 전부. 하나라도 빠지면 그 함수가 뒷문이 된다.
    def _surface_calls(self):
        from kernels.k1_event import services as k1

        return [
            ("record_detection", lambda: k1.record_detection(
                stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical")),
            ("query_events", lambda: k1.query_events()),
            ("get_event", lambda: k1.get_event(1)),
            ("review_event", lambda: k1.review_event(1, verdict="rejected")),
            ("close_event", lambda: k1.close_event(1)),
            ("subscribe", lambda: k1.subscribe(webhook_url="https://test.invalid/hook")),
        ]

    def test_every_public_function_refuses_to_run_without_scope(self) -> None:
        """[D-281] 6개 전부 — `scope` 없이 부르면 **TypeError.**

        ★ **실패는 뒤를 가리지 않는다** (D-274 승격 원칙). 첫 함수에서 멈추면
          "1건 실패"가 실제로는 "1건 실패 + 5건 미측정"이 된다. 대상별 표를 낸다.
        """
        table = []
        for name, call in self._surface_calls():
            try:
                call()
            except TypeError as exc:
                ok = "scope" in str(exc)
                table.append((name, "TypeError" if ok else f"TypeError(다른 사유: {exc})", ok))
            except Exception as exc:  # noqa: BLE001 — 무엇이 왔는지 표에 적어야 한다
                table.append((name, f"{type(exc).__name__}: {exc}", False))
            else:
                table.append((name, "통과해 버렸다", False))

        failed = [(n, w) for n, w, ok in table if not ok]
        self.assertEqual(
            failed, [],
            "scope 없이 호출됐거나 다른 이유로 죽은 커널 공개 함수가 있습니다 (D-281).\n"
            + "\n".join(f"  {n:20s} {w}" for n, w, _ in table),
        )

    def test_subscribe_requires_scope_before_it_raises(self) -> None:
        """[D-281] 구현이 없어도 스코프는 먼저 걸린다.

        `subscribe` 는 부르면 `NotImplementedYet` 을 던진다. 그런데 **스코프 없이 불렀을
        때도** 그것이 나오면, 이 함수는 "구현이 없어서 안전한" 것이지 "스코프를 요구해서
        안전한" 것이 아니다. 구현이 들어오는 날 그 차이가 드러난다 — 지금 갈라 둔다.
        """
        from kernels.k1_event import services as k1
        from kernels.k1_event.exceptions import NotImplementedYet

        with self.assertRaises(TypeError):
            k1.subscribe(webhook_url="https://test.invalid/hook")

        # scope 를 주면 그때서야 "구현이 없다"가 나온다.
        with self.assertRaises(NotImplementedYet):
            k1.subscribe(scope=self.scope_a, webhook_url="https://test.invalid/hook")

    def test_system_scope_cannot_read(self) -> None:
        """[D-281] 파이프라인 스코프로는 **읽지 못한다.**

        쓰기 파이프라인에 요청자가 없다는 사실이 읽기까지 열어 주면, 그 경로는 영구히
        전역 조회가 된다. `record_detection` 만 시스템 스코프를 받고 나머지는 거절한다.
        """
        from common.tenant_scope import SystemScopeCannotRead
        from kernels.k1_event import services as k1

        mine = k1.record_detection(
            scope=self.scope_pipe, stream_monitor_id=self.stream_a.id,
            event_type="fire", severity="critical")

        table = []
        for name, call in [
            ("query_events", lambda: k1.query_events(scope=self.scope_pipe)),
            ("get_event", lambda: k1.get_event(mine.event_id, scope=self.scope_pipe)),
            ("review_event", lambda: k1.review_event(
                mine.event_id, verdict="rejected", scope=self.scope_pipe)),
            ("close_event", lambda: k1.close_event(mine.event_id, scope=self.scope_pipe)),
        ]:
            try:
                call()
            except SystemScopeCannotRead:
                table.append((name, "거절", True))
            except Exception as exc:  # noqa: BLE001
                table.append((name, f"{type(exc).__name__}: {exc}", False))
            else:
                table.append((name, "시스템 스코프로 통과해 버렸다", False))

        failed = [(n, w) for n, w, ok in table if not ok]
        self.assertEqual(
            failed, [],
            "시스템 스코프가 읽기·판정 경로를 통과했습니다 (D-281).\n"
            + "\n".join(f"  {n:16s} {w}" for n, w, _ in table),
        )

    def test_scope_of_none_is_refused_at_construction(self) -> None:
        """[D-281] 빈 스코프는 **만들어지지도 않는다** — 검사가 호출 전에 끝난다."""
        from common.tenant_scope import TenantScope

        with self.assertRaises(ValueError):
            TenantScope.of(None)
        with self.assertRaises(ValueError):
            TenantScope.system(reason="")          # 사유 없는 시스템 스코프 = 면제
        with self.assertRaises(ValueError):
            TenantScope.system(reason="   ")       # 공백도 사유가 아니다
        with self.assertRaises(ValueError):
            TenantScope()                          # 둘 다 없음

    def test_human_scope_cannot_write_into_another_tenants_stream(self) -> None:
        """[D-281] 사람이 부른 기록은 **남의 스트림에 심지 못한다** — 쓰기 쪽 IDOR.

        시그니처만으로는 이것을 못 막는다(스코프를 주기만 하면 되므로). 그래서 2차
        문지기가 있다 — `record_detection` 이 `assert_scoped(StreamMonitor, ...)` 를 부른다.
        **시그니처가 1차, 문지기가 2차** (D-281).
        """
        from kernels.k1_event import services as k1

        with self.assertRaises(Http404):
            k1.record_detection(
                scope=self.scope_a,                     # 테넌트 A 가
                stream_monitor_id=self.stream_b.id,     # 테넌트 B 의 스트림에
                event_type="fire", severity="critical")

        # 양성 대조 — 자기 스트림에는 들어간다. 위 거절이 "전부 막힌 것"이 아님을 보인다.
        ok = k1.record_detection(
            scope=self.scope_a, stream_monitor_id=self.stream_a.id,
            event_type="fire", severity="critical")
        self.assertTrue(ok.created)


class KernelPublicSurfaceTest(TestCase):
    """DA-04 §2 K1 표가 정한 공개 면 6개가 **실재하는가.**

    표와 코드가 갈리는 것은 시간 문제다. 갈리면 어느 쪽이 계약인지 아무도 모른다 —
    `verify_kernel_map.py` 가 티켓 매핑에 대해 하는 일을, 여기서는 함수 면에 대해 한다.
    """

    #: DA-04 §2 K1 의 "공개 면" 열 그대로.
    #: ★ 2026-09-14 — 둘이 늘었다 (D-399 대응 진행 축). DA-04 §2 K1 표와 `__init__` 과
    #:   이 줄을 **같은 커밋에서** 함께 고쳤다. 갈리면 어느 쪽이 계약인지 모른다.
    #: ★ 2026-09-20 — 하나가 더 늘었다 (P-16 오탐 결합). `__init__` 과 이 줄을
    #:   **같은 커밋에서** 고쳤다. 이 함수는 소비자 한 곳만 부르지만 공개 면에 둔다 —
    #:   격리 대장(`WRITE_PROBES`)이 커널 `__all__` 을 훑기 때문이고, 면에서 감추면
    #:   쓰기 면이 **대장 밖에서** 자란다(D-290 · D-301).
    SURFACE = ["record_detection", "query_events", "get_event",
               "review_event", "close_event", "subscribe",
               "advance_response", "response_state",
               "close_as_false_positive"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k1_event

        missing = [n for n in self.SURFACE if not hasattr(k1_event, n)]
        self.assertEqual(
            missing, [],
            f"DA-04 §2 K1 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.",
        )

    #: 저장소 뿌리 후보. 컨테이너에는 `backend/` 만 `/app` 으로 들어오므로 소스 트리에서
    #: 되짚는 경로가 통하지 않는다. `docker-compose` 가 `/repo` 로 뿌리 모양을 넣어 준다
    #: (D-285 (4) — skip 을 해소한 마운트). 후보를 **순서대로** 보고 첫 번째를 쓴다.
    REPO_ROOT_CANDIDATES = ("/repo",)

    @classmethod
    def _find_gate(cls, name: str):
        """저장소 게이트 스크립트의 실경로. 없으면 `None` — **추측하지 않는다.**"""
        from pathlib import Path

        here = Path(__file__).resolve()
        roots = [*(Path(c) for c in cls.REPO_ROOT_CANDIDATES), *here.parents[1:4]]
        for root in roots:
            candidate = root / "scripts" / name
            if candidate.is_file():
                return candidate
        return None

    def test_kernel_does_not_import_apps(self) -> None:
        """계층 역전 금지 (D-278). 게이트가 CI 에서 보지만, 커널 자신도 한 번 확인한다."""
        import subprocess
        import sys

        script = self._find_gate("verify_layers.py")
        self.assertIsNotNone(
            script,
            "verify_layers.py 를 찾지 못했습니다. 컨테이너라면 docker-compose 의 "
            "`./scripts:/repo/scripts:ro` 마운트가 빠진 것입니다 (D-285 (4)).\n"
            "★ 이 시험은 더 이상 skip 하지 않습니다 — 마운트를 넣어 skip 을 해소한 뒤이므로, "
            "다시 사라지면 그것은 '환경 미비'가 아니라 **되돌아간 것**입니다.",
        )
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_migration_state_matches_models_and_db(self) -> None:
        """[D-282] 착시 ⑤ — **재는 자리가 실물인가.**

        이 시험 파일 전체는 `--nomigrations` 로 돈다. 그러면 테스트 DB 는 마이그레이션이
        아니라 **모델 선언에서** 만들어지고, 그래서 `DetectionEvent` 표가 실물 DB 에 없는
        동안에도 초록이었다. 여기서 그 격차를 **같은 실행 안에서** 한 번 본다.

        ※ 게이트(`scripts/verify_migrations.py`)를 부르는 것이지 판정을 복제하는 것이 아니다.
          판정기는 한 벌이고 눈만 둘이다 — 트립와이어가 정적·런타임 눈을 둔 것과 같은 계열.
        """
        import subprocess
        import sys

        script = self._find_gate("verify_migrations.py")
        self.assertIsNotNone(script, "verify_migrations.py 를 찾지 못했습니다 (D-282 게이트)")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(
            out.returncode, 0,
            "모델 선언 · 마이그레이션 그래프 · DB 가 어긋납니다 (D-282 착시 ⑤).\n"
            + out.stdout + out.stderr,
        )
