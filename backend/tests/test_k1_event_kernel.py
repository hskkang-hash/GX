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

    def test_records_within_10s_fold_into_one_event(self) -> None:
        """[F-04] 같은 stream+type 이 10초 안에 재발하면 **이벤트는 1건**이고 last_seen 만 는다."""
        from kernels.k1_event import services as k1

        t0 = timezone.now()
        first = k1.record_detection(
            stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical",
            occurred_at=t0, confidence=0.91, snapshot_path="minio://snap/1.jpg",
        )
        second = k1.record_detection(
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
            stream_monitor_id=self.stream_a.id, event_type="smoke", severity="warning",
            occurred_at=t0, snapshot_path="minio://snap/a.jpg",
        )
        later = k1.record_detection(
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
        a = k1.record_detection(stream_monitor_id=self.stream_a.id, event_type="person",
                                severity="info", occurred_at=t0, snapshot_path="minio://a.jpg")
        b = k1.record_detection(stream_monitor_id=self.stream_b.id, event_type="person",
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
                stream_monitor_id=self.stream_a.id, event_type=etype, severity=sev,
                occurred_at=t0 - timedelta(minutes=i * 10), snapshot_path=f"minio://f/{i}.jpg",
            ))

    def test_query_filters_by_type_severity_and_period_on_the_server(self) -> None:
        """[F-05 · U1] 필터가 서버에서 적용된다 — 반환된 수가 곧 필터 결과여야 한다."""
        from kernels.k1_event import services as k1

        got = k1.query_events(actor=self.user_a, event_type="fire")
        self.assertEqual(
            [e.event_type for e in got], ["fire", "fire"],
            "event_type 필터가 서버에서 적용되지 않았습니다 — 클라이언트가 다시 걸러야 하고, "
            "그만큼 클릭이 늡니다 (U1 3클릭 위반).",
        )

        got = k1.query_events(actor=self.user_a, severity="critical")
        self.assertEqual(len(got), 1, "severity 필터가 서버에서 적용되지 않았습니다.")

        got = k1.query_events(actor=self.user_a, since=timezone.now() - timedelta(minutes=15))
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
                rows = k1.query_events(actor=self.user_a, limit=limit)
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

        page1 = k1.query_events(actor=self.user_a, limit=2, offset=0)
        page2 = k1.query_events(actor=self.user_a, limit=2, offset=2)
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
            stream_monitor_id=self.stream_a.id, event_type="fire", severity="critical",
            occurred_at=now, snapshot_path="minio://mine.jpg",
        )
        self.theirs = k1.record_detection(
            stream_monitor_id=self.stream_b.id, event_type="fire", severity="critical",
            occurred_at=now, snapshot_path="minio://theirs.jpg",
        )

    def test_positive_control_own_event_is_found(self) -> None:
        """★ 양성 대조 — 자기 테넌트의 이벤트는 **실제로 찾아진다.**

        이 시험이 빨간불이면 아래 격리 시험들은 '통과'가 아니라 **판정 불가**다.
        """
        from kernels.k1_event import services as k1

        ids = {e.event_id for e in k1.query_events(actor=self.user_a)}
        self.assertIn(self.mine.event_id, ids,
                      "자기 테넌트의 이벤트조차 목록에서 찾지 못했습니다 — "
                      "아래 '남의 것이 안 보인다'는 통과가 아니라 판정 불가입니다 (D-277).")
        self.assertIsNotNone(k1.get_event(self.mine.event_id, actor=self.user_a))

    def test_query_events_excludes_other_tenant(self) -> None:
        from kernels.k1_event import services as k1

        ids = {e.event_id for e in k1.query_events(actor=self.user_a)}
        self.assertNotIn(self.theirs.event_id, ids,
                         "남의 테넌트 이벤트가 목록에 섞였습니다.")

    def test_get_event_of_other_tenant_is_404_not_empty_200(self) -> None:
        """남의 것은 **없는 것과 같아야** 한다 — 200+빈 응답을 새로 만들지 않는다 (W0-18)."""
        from kernels.k1_event import services as k1

        with self.assertRaises(Http404):
            k1.get_event(self.theirs.event_id, actor=self.user_a)

    def test_review_and_close_of_other_tenant_are_404(self) -> None:
        """쓰기 경로도 같다 — 읽기만 막고 쓰기를 열어 두는 것이 W0-14c 가 잡은 결함이었다."""
        from kernels.k1_event import services as k1

        with self.assertRaises(Http404):
            k1.review_event(self.theirs.event_id, verdict="rejected",
                            reason="probe", actor=self.user_a)
        with self.assertRaises(Http404):
            k1.close_event(self.theirs.event_id, actor=self.user_a)

    def test_review_records_the_verdict_for_false_positive_rate(self) -> None:
        """[U1] 오탐률 수치화의 입력 — 판정과 판정자가 남아야 K6 가 셀 수 있다."""
        from kernels.k1_event import services as k1

        out = k1.review_event(self.mine.event_id, verdict="rejected",
                              reason="빛 반사", actor=self.user_a)
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

        k1.review_event(self.mine.event_id, verdict="rejected", reason="x", actor=self.user_a)
        Event = apps.get_model("stream_monitors", "DetectionEvent")
        self.assertTrue(Event.objects.filter(pk=self.mine.event_id).exists(),
                        "기각된 이벤트가 사라졌습니다 — 오탐률 분자가 함께 사라집니다.")


# ═══════════════════════════════════════════════════════════════════════════
# 계층 — 커널의 공개 면은 서비스 함수다 (DA-04 §1-4 · D-278)
# ═══════════════════════════════════════════════════════════════════════════
class KernelPublicSurfaceTest(TestCase):
    """DA-04 §2 K1 표가 정한 공개 면 6개가 **실재하는가.**

    표와 코드가 갈리는 것은 시간 문제다. 갈리면 어느 쪽이 계약인지 아무도 모른다 —
    `verify_kernel_map.py` 가 티켓 매핑에 대해 하는 일을, 여기서는 함수 면에 대해 한다.
    """

    #: DA-04 §2 K1 의 "공개 면" 열 그대로.
    SURFACE = ["record_detection", "query_events", "get_event",
               "review_event", "close_event", "subscribe"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k1_event

        missing = [n for n in self.SURFACE if not hasattr(k1_event, n)]
        self.assertEqual(
            missing, [],
            f"DA-04 §2 K1 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.",
        )

    def test_kernel_does_not_import_apps(self) -> None:
        """계층 역전 금지 (D-278). 게이트가 CI 에서 보지만, 커널 자신도 한 번 확인한다."""
        import subprocess
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        script = root / "scripts" / "verify_layers.py"
        if not script.is_file():
            self.skipTest("verify_layers.py 없음 — 컨테이너에는 scripts/ 가 마운트되지 않는다")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
