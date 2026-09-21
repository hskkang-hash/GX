# -*- coding: utf-8 -*-
"""K2 알림 커널 — **이중 AC 시험** (DA-04 §2 K2).

    [F-10 계약] 심각 등급 발생 후 **30초 내 발송 기록**
    [U2 상품]  보고 자동화의 입력 (K4 가 이 레코드를 조치 이력으로 읽는다)
    [U1 상품]  오탐 흐름의 시작점

★ 이 파일에서 가장 중요한 시험은 **실패가 성공처럼 보이지 않는가**이다.
  알림은 안 가도 화면이 조용하다. 발송 실패가 행으로 남지 않으면 아무도 모르고,
  아무도 모르는 채로 재난이 지나간다. 그래서 여기서는 초록보다 **빨강이 보이는가**를 잰다.

시험 갈래 (착시 5형 · D-282 를 따라간다)
  ② 시나리오 — 성공 · 실패 · 채널 미구현 · 수신자 0명 · 억제, 다섯 갈래를 각각 지나간다
  ③ 모수와 술어 — 30초 판정을 **레코드에서** 읽는다. "빨랐다"는 보고가 아니다
  ④ 탐지기 — 양성 대조. 발송을 막으면 이 시험이 실패하는가
  ⑤ 환경 — 표가 DB 에 실재하는가 (D-288 ②눈)
"""
from __future__ import annotations

import contextlib
from datetime import timedelta

from django.apps import apps
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone


#: ★ P-41 (2026-09-05) — **실발송 허용 도메인이 채널보다 앞에 선다.**
#:   `EmailChannel` 은 목록 밖 도메인을 `send_mail` 앞에서 **로그 어댑터로**
#:   떨어뜨린다. 그래서 「메일이 실제로 나갔다」를 재는 시험은 **어느 도메인을
#:   허용했는지 스스로 밝혀야** 한다. 밝히지 않고 초록이 서면 그 초록은
#:   운영에서 재현되지 않는다 — 운영의 목록은 비어 있기 때문이다.
#:   강제: `scripts/verify_send_allowlist.py`
@override_settings(K2_SEND_ALLOWED_DOMAINS=["test.invalid"])
class K2Fixture(TestCase):
    """테넌트 A/B · 각자의 스트림 · 역할 하나 · 수신 규칙 하나."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802 (Django 규약)
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="k2-tenant-A")
        cls.group_b = UserGroup.objects.create(name="k2-tenant-B")
        UserGroup.objects.filter(pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.role_a = cls._make_role("k2_watch_a", cls.group_a)
        cls.role_b = cls._make_role("k2_watch_b", cls.group_b)

        cls.user_a = cls._make_user("k2_user_a", cls.group_a, cls.role_a)
        cls.user_b = cls._make_user("k2_user_b", cls.group_b, cls.role_b)
        cls.stream_a = cls._make_stream("k2-stream-A", cls.group_a)
        cls.stream_b = cls._make_stream("k2-stream-B", cls.group_b)

        cls.rule_a = cls._make_rule(cls.group_a, cls.role_a, "critical", ["email"])
        cls.rule_b = cls._make_rule(cls.group_b, cls.role_b, "critical", ["email"])

        from common.tenant_scope import TenantScope

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="K2 시험 픽스처 — 발송 파이프라인에는 요청자가 없다 (D-281)")

    # ── 픽스처 도우미 ────────────────────────────────────────────────────
    @staticmethod
    def _own(obj, group):
        """소유 필드 이름은 커널의 판단기를 그대로 쓴다 (P-LOCAL-4 미결 · D-212)."""
        from kernels.k1_event.services import _owner_field

        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    @classmethod
    def _make_role(cls, code: str, group):
        Role = apps.get_model("role", "Role")
        role = Role.objects.create(role_name=code, code=code)
        return cls._own(role, group)

    @classmethod
    def _make_user(cls, username: str, group, role):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid",
        )
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        user.roles.add(role)
        return user

    @classmethod
    def _make_stream(cls, name: str, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        sm = StreamMonitor.objects.create(name=name, code=name,
                                          ip_source="rtsp://test.invalid/x")
        return cls._own(sm, group)

    @classmethod
    def _make_rule(cls, group, role, severity, channels, zone=None):
        Rule = apps.get_model("stream_monitors", "NotificationRule")
        rule = Rule.objects.create(severity=severity, role=role, zone=zone,
                                   channels=channels, is_active=True)
        return cls._own(rule, group)

    def _event(self, stream, *, when=None, severity="critical", event_type="fire"):
        from kernels.k1_event import record_detection

        self._nth = getattr(self, "_nth", 0) + 1
        when = when or (timezone.now() - timedelta(seconds=600 * self._nth))
        return record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type=event_type, severity=severity, occurred_at=when,
            snapshot_path=f"minio://k2/{self._nth}.jpg",
        ).event_id


# ═══════════════════════════════════════════════════════════════════════════
# [F-10 계약 AC] — 30초 내 **발송 기록**
# ═══════════════════════════════════════════════════════════════════════════
class F10DeliveryRecordTest(K2Fixture):
    """★ 재는 것은 "빨랐다"가 아니라 **레코드의 두 점**이다 (DA-04 K2)."""

    def test_delivery_record_carries_both_points_of_f10(self) -> None:
        from kernels.k2_notify import send

        event_id = self._event(self.stream_a, when=timezone.now())
        records = send(scope=self.scope_a, event_id=event_id)

        self.assertEqual(1, len(records), "수신자 1명인데 이력이 1건이 아닙니다.")
        record = records[0]
        self.assertTrue(record.succeeded, f"발송이 실패했습니다: {record.failure_reason}")
        self.assertIsNotNone(record.sent_at, "성공인데 sent_at 이 비었습니다.")
        self.assertIsNotNone(record.latency_seconds,
                             "occurred_at → sent_at 을 한 행에서 못 읽습니다 — "
                             "AC 측정에 조인이 필요하면 그 측정은 안 하게 됩니다.")
        self.assertTrue(record.meets_f10,
                        f"F-10 30초를 넘겼습니다: {record.latency_seconds}초")
        self.assertEqual(1, len(mail.outbox), "실제로 메일이 나가지 않았습니다.")

    def test_late_delivery_does_not_meet_f10(self) -> None:
        """★ **양성 대조** — 판정기가 위반을 잡는가 (D-277).

        전부 통과하는 판정기는 아무것도 판정하지 않는다. 30초를 넘긴 발송을
        만들어 넣어 `meets_f10` 이 거짓이 되는지 본다.
        """
        from kernels.k2_notify import send

        old = timezone.now() - timedelta(minutes=5)
        event_id = self._event(self.stream_a, when=old)
        record = send(scope=self.scope_a, event_id=event_id)[0]

        self.assertTrue(record.succeeded)
        self.assertGreater(record.latency_seconds, 30,
                           "픽스처가 의도한 지연을 만들지 못했습니다.")
        self.assertFalse(record.meets_f10,
                         "30초를 넘긴 발송을 F-10 충족으로 판정했습니다 — "
                         "판정기가 눈이 멀었습니다.")

    def test_failed_delivery_never_meets_f10(self) -> None:
        """실패한 발송은 **아무리 빨라도** F-10 을 충족하지 않는다.

        F-10 이 요구하는 것은 "빨리 시도했다"가 아니라 **"보냈다"** 이다.
        """
        from kernels.k2_notify import channels, send

        undo = channels.register(_BrokenChannel())
        self.addCleanup(undo)

        event_id = self._event(self.stream_a, when=timezone.now())
        record = send(scope=self.scope_a, event_id=event_id)[0]

        self.assertFalse(record.succeeded)
        self.assertIsNone(record.sent_at,
                          "실패에 sent_at 이 찍혔습니다 — 30초 AC 가 실패한 발송으로도 "
                          "달성됩니다.")
        self.assertIsNone(record.latency_seconds,
                          "실패를 0초로 셌습니다 — 못 보낸 것은 빠른 것이 아닙니다.")
        self.assertFalse(record.meets_f10)


class FailureIsVisibleTest(K2Fixture):
    """★ **실패가 성공처럼 보이지 않는가** (D-284 · D-290)."""

    def test_failure_leaves_a_row_not_silence(self) -> None:
        """"보낸 적 없음"(행 없음)과 "보내려다 실패"(행 있음)를 가른다."""
        from kernels.k2_notify import channels, list_deliveries, send

        undo = channels.register(_BrokenChannel())
        self.addCleanup(undo)

        event_id = self._event(self.stream_a, when=timezone.now())
        send(scope=self.scope_a, event_id=event_id)

        rows = list_deliveries(scope=self.scope_a, event_id=event_id)
        self.assertEqual(1, len(rows), "실패가 행으로 남지 않았습니다 — 조용한 유실입니다.")
        self.assertFalse(rows[0].succeeded)
        self.assertTrue(rows[0].failure_reason,
                        "실패 사유가 비었습니다 — 왜 못 갔는지 아무도 모릅니다.")

    def test_broken_channel_does_not_stop_the_pipeline(self) -> None:
        """저하 운전 — 발송 업체가 죽어도 **예외가 올라오지 않는다** (DA2-21 (4))."""
        from kernels.k2_notify import channels, send

        undo = channels.register(_ExplodingChannel())
        self.addCleanup(undo)

        event_id = self._event(self.stream_a, when=timezone.now())
        records = send(scope=self.scope_a, event_id=event_id)  # 예외가 나면 시험 실패
        self.assertEqual(1, len(records))
        self.assertFalse(records[0].succeeded)

    def test_unconfigured_channel_is_recorded_with_the_reason(self) -> None:
        """업체 미정(D4-1) 채널은 **조용히 성공하지 않는다.** 사유가 행에 남는다."""
        from kernels.k2_notify import send

        rule = self._make_rule(self.group_a, self.role_a, "warning", ["sms"])
        self.assertIsNotNone(rule.pk)
        event_id = self._event(self.stream_a, when=timezone.now(), severity="warning")
        records = send(scope=self.scope_a, event_id=event_id)

        self.assertEqual(1, len(records))
        self.assertFalse(records[0].succeeded)
        self.assertIn("미구현", records[0].failure_reason or "",
                      "미구현 채널의 실패 사유가 '왜'를 말하지 않습니다.")

    def test_zero_recipients_raises_instead_of_returning_empty(self) -> None:
        """★ 수신자 0명 = **알림 체계가 꺼진 상태.** 빈 성공으로 넘기지 않는다.

        DA-03 §3-2 (조용한 무력화 금지) · D-290.
        """
        from kernels.k2_notify import NoRecipients, send

        # info 등급에는 규칙이 없다 — 보낼 곳이 없다.
        event_id = self._event(self.stream_a, when=timezone.now(), severity="info")
        with self.assertRaises(NoRecipients):
            send(scope=self.scope_a, event_id=event_id)


class SuppressionTest(K2Fixture):
    """[F-04] 5분 억제 — **K2 는 발송 이력을 본다** (K1 은 이벤트 행을 본다)."""

    def test_second_alert_within_five_minutes_is_suppressed(self) -> None:
        """종전 그대로 — 같은 카메라·같은 유형의 둘째 알림은 접힌다.

        ★ [턴 Y · F-04] **묶는 키는 안 바뀜었다.** 바뀜 것은 창의 **기준**이다
          (사건 발생 시각 → 직전 발송 시각). 이 시험이 그대로 서 있어야
          「기준을 고쳐도 저장소가 들고 있던 계약은 안 깨졌다」가 증명된다.
        """
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=4))
        send(scope=self.scope_a, event_id=first)

        second = self._event(self.stream_a, when=now)
        self.assertTrue(suppress(scope=self.scope_a, event_id=second),
                        "5분 안의 두 번째 알림이 억제되지 않았습니다 (F-04).")
        self.assertEqual((), send(scope=self.scope_a, event_id=second),
                         "억제됐는데 발송 이력이 생겼습니다.")

    def test_pressing_notify_twice_on_the_same_event_is_suppressed(self) -> None:
        """★★ [턴 Y · F-04 · 2026-09-20] **새로 선 자리 — 문안이 말하는 바로 그것.**

        GX-COPY: 「5분 안에 **같은 사건** 재발송 억제」. 그런데 종전 질의는
        `occurred_at__lt = event.occurred_at` 로 **자기 발송만 잘라 냈다** — 발송
        행의 `occurred_at` 은 제 사건의 발생 시각 복사본이라 `<` 가 아니다.
        즉 **옆 사건은 접으면서 자기 자신은 못 접는**, 문안과 정반대인 상태였다.

        그 자리가 수로 남았다 [실측 2026-09-20 · 개발 DB]: 씨앗 사건 `#295402`
        하나에 발송 12건이 무리 셋(4+4+4)으로 달려 있었다 — 측정이 「알림 보내기」를
        세 번 눌렀고, 세 번 다 수신자 수만큼 행을 낳았다.
        """
        from kernels.k2_notify import send, suppress

        event_id = self._event(self.stream_a, when=timezone.now())
        sent = send(scope=self.scope_a, event_id=event_id)
        self.assertTrue(sent and sent[0].succeeded, "첫 발송이 실패했습니다(표본 고장).")

        self.assertTrue(
            suppress(scope=self.scope_a, event_id=event_id),
            "방금 보낸 사건을 다시 눌렀는데 안 접힙니다 — 그러면 사람이 「알림 "
            "보내기」를 두 번 누를 때마다 수신자 수만큼 행이 더 쌓입니다(F-04 문안).")
        self.assertEqual((), send(scope=self.scope_a, event_id=event_id),
                         "억제됐는데 발송 이력이 다시 생겼습니다.")

    def test_beyond_five_minutes_is_not_suppressed(self) -> None:
        """★ 양성 대조 — 억제기가 **모든 것을 접지는 않는가**."""
        from kernels.k2_notify import send, suppress

        now = timezone.now()
        first = self._event(self.stream_a, when=now - timedelta(minutes=9))
        send(scope=self.scope_a, event_id=first)
        #: ★★ [턴 Y · F-04] **보낸 시각을 옮겨 놓는다.**
        #:   종전엔 `occurred_at` 을 9분 전으로 두는 것만으로 「9분 전」이 됐다 —
        #:   질의가 발생 시각을 봤기 때문이고, 그것이 고친 결함이다. 이제 기준은
        #:   **보낸 시각**이므로 「9분 전에 보냈다」를 시험이 직접 만들어야 한다.
        #:   시계를 기다리지 않는다 — 기다리는 시험은 느린 것이 아니라 **재현되지 않는다.**
        apps.get_model("stream_monitors", "DeliveryRecord")._base_manager.filter(
            event_id=first, succeeded=True).update(sent_at=now - timedelta(minutes=9))

        second = self._event(self.stream_a, when=now)
        self.assertFalse(suppress(scope=self.scope_a, event_id=second),
                         "5분을 지난 알림까지 접었습니다 — 억제기가 과합니다.")

    def test_failed_delivery_does_not_suppress_the_next_one(self) -> None:
        """★ **못 보낸 알림은 '이미 알렸다'가 아니다.**

        여기가 K1 의 판정과 갈리는 자리다. 실패를 억제로 세면 장애 5분 동안의
        재난 알림이 통째로 사라진다 — 그 5분이 정확히 알림이 가장 필요한 5분이다.
        """
        from kernels.k2_notify import channels, send, suppress

        now = timezone.now()
        undo = channels.register(_BrokenChannel())
        first = self._event(self.stream_a, when=now - timedelta(minutes=2))
        send(scope=self.scope_a, event_id=first)
        undo()   # 메일 서버가 살아났다

        second = self._event(self.stream_a, when=now)
        self.assertFalse(
            suppress(scope=self.scope_a, event_id=second),
            "실패한 발송이 억제로 세어졌습니다 — 장애 구간의 알림이 사라집니다.")
        records = send(scope=self.scope_a, event_id=second)
        self.assertTrue(records[0].succeeded)


class RecipientResolutionTest(K2Fixture):
    """[F-10] 등급별 수신 그룹 — **등급이 다르면 받는 사람이 다르다**."""

    def test_recipients_differ_by_severity(self) -> None:
        from kernels.k2_notify import resolve_recipients

        critical = resolve_recipients(scope=self.scope_a, severity="critical")
        info = resolve_recipients(scope=self.scope_a, severity="info")

        self.assertEqual(1, len(critical))
        self.assertEqual(self.user_a.pk, critical[0].user_id)
        self.assertEqual((), info, "규칙이 없는 등급에서 수신자가 나왔습니다.")

    def test_rule_points_at_a_role_not_a_person(self) -> None:
        """역할이 바뀌면 수신자가 따라 바뀐다 — 규칙을 안 고쳐도 된다.

        사람을 직접 넣는 설계였다면 이 시험은 통과하지 못한다. 그리고 그 설계는
        **퇴사자에게 재난 알림을 보내는 상태**로 남는다.
        """
        from kernels.k2_notify import resolve_recipients

        newcomer = self._make_user("k2_user_a2", self.group_a, self.role_a)
        got = {r.user_id for r in resolve_recipients(scope=self.scope_a, severity="critical")}
        self.assertIn(newcomer.pk, got,
                      "역할에 사람을 넣었는데 수신자에 들어오지 않았습니다.")

    def test_zone_rule_wins_over_the_global_one(self) -> None:
        """구역 규칙이 있으면 그것만 쓴다 — 둘 다 쓰면 같은 사람에게 두 번 간다."""
        from kernels.k2_notify import resolve_recipients

        zone_role = self._make_role("k2_zone_role", self.group_a)
        zone_user = self._make_user("k2_zone_user", self.group_a, zone_role)
        self._make_rule(self.group_a, zone_role, "critical", ["email"], zone="anyang-1")

        got = {r.user_id for r in
               resolve_recipients(scope=self.scope_a, severity="critical", zone="anyang-1")}
        self.assertEqual({zone_user.pk}, got,
                         "구역 규칙과 전역 규칙이 함께 적용됐습니다 — 중복 발송이 됩니다.")

    def test_same_person_is_not_notified_twice_by_two_rules(self) -> None:
        from kernels.k2_notify import resolve_recipients

        self._make_rule(self.group_a, self.role_a, "critical", ["email"])  # 같은 역할 두 번째
        got = [r for r in resolve_recipients(scope=self.scope_a, severity="critical")
               if r.user_id == self.user_a.pk]
        self.assertEqual(1, len(got),
                         "규칙 둘이 같은 역할을 가리켜 같은 사람에게 두 번 갑니다.")


class SendPassesTheEventsZoneTest(K2Fixture):
    """[턴 U · P-173 §2 ④ · 턴 T 넘김] `send()` 가 사건의 구역을 `resolve_recipients`
    로 넘기는가 — **바로 위 클래스**의 시험은 `resolve_recipients` 함수 자체가 구역을
    받으면 옳게 좁힌다는 것만 잰다. 발송 문 `send()` 가 그 인자를 **부르지 않고** 있었다
    (턴 U 실측 · 개발 DB 에는 `Zone` 행이 0건이라 지금까지는 드러나지 않았다).
    """

    def test_a_camera_in_a_zone_notifies_only_that_zones_rule(self) -> None:
        """카메라를 구역에 묶고 그 구역 전용 규칙을 만들면, **전역 규칙이 아니라
        구역 규칙**의 사람에게 간다 — `send()` 가 `event.stream_monitor.zones` 를
        읽어 `resolve_recipients(zone=...)` 로 넘길 때만 참이다."""
        from kernels.k2_notify import send

        Zone = apps.get_model("stream_monitors", "Zone")
        zone = Zone.objects.create(name="k2-zone-anyang-1")
        zone.cameras.add(self.stream_a)

        zone_role = self._make_role("k2_zone_role", self.group_a)
        zone_user = self._make_user("k2_zone_user", self.group_a, zone_role)
        self._make_rule(self.group_a, zone_role, "critical", ["email"],
                        zone="k2-zone-anyang-1")

        event_id = self._event(self.stream_a, when=timezone.now())
        records = send(scope=self.scope_a, event_id=event_id)

        recipients = {r.recipient_id for r in records}
        self.assertEqual(
            {zone_user.pk}, recipients,
            "카메라가 속한 구역의 규칙이 아니라 전역 규칙(`rule_a`)으로 갔습니다 — "
            "`send()` 가 사건의 구역을 `resolve_recipients` 에 넘기지 않고 있습니다.")

    def test_a_camera_in_two_zones_merges_recipients_without_duplicates(self) -> None:
        """카메라 하나가 구역 둘에 걸치면(`Zone.cameras` M2M · 모델 머리말 「하천 합류부·
        교차로」) 두 구역의 수신자를 **합치되**, 같은 사람·같은 채널이 두 구역 모두에
        걸려도 두 통 가지 않는다."""
        from kernels.k2_notify import send

        Zone = apps.get_model("stream_monitors", "Zone")
        zone1 = Zone.objects.create(name="k2-zone-1")
        zone2 = Zone.objects.create(name="k2-zone-2")
        zone1.cameras.add(self.stream_a)
        zone2.cameras.add(self.stream_a)

        role1 = self._make_role("k2_zone_role_1", self.group_a)
        user1 = self._make_user("k2_zone_user_1", self.group_a, role1)
        self._make_rule(self.group_a, role1, "critical", ["email"], zone="k2-zone-1")

        role2 = self._make_role("k2_zone_role_2", self.group_a)
        user2 = self._make_user("k2_zone_user_2", self.group_a, role2)
        self._make_rule(self.group_a, role2, "critical", ["email"], zone="k2-zone-2")
        # 구역 2 규칙이 구역 1 의 사람도 가리키게 해 **중복 제거**를 함께 잰다.
        user1.roles.add(role2)

        event_id = self._event(self.stream_a, when=timezone.now())
        records = send(scope=self.scope_a, event_id=event_id)

        recipients = {r.recipient_id for r in records}
        self.assertEqual({user1.pk, user2.pk}, recipients)
        self.assertEqual(
            2, len(records),
            "구역 둘에 걸린 사람에게 두 통이 갔습니다 — 합치면서 중복을 제거해야 합니다.")

    def test_no_zone_on_the_camera_keeps_todays_behavior(self) -> None:
        """[뒤로 호환] 카메라가 어느 구역에도 없으면 — 지금 모든 실측 데이터가 그렇듯 —
        전역 규칙이 그대로 쓰인다. 이 시험이 깨지면 이번 배선이 기존 발송을 바꾼 것이다."""
        from kernels.k2_notify import send

        event_id = self._event(self.stream_a, when=timezone.now())
        records = send(scope=self.scope_a, event_id=event_id)

        self.assertEqual({self.user_a.pk}, {r.recipient_id for r in records})


class KernelTenantScopeTest(K2Fixture):
    """알림 격리 — **남의 재난 알림이 우리에게 오지 않는다**."""

    def test_positive_control_own_rules_are_found(self) -> None:
        """★ 양성 대조 — 자기 규칙은 찾아지는가 (D-277)."""
        from kernels.k2_notify import resolve_recipients

        self.assertEqual(
            1, len(resolve_recipients(scope=self.scope_a, severity="critical")),
            "자기 테넌트 규칙을 못 찾았습니다 — 판정기가 눈이 멀었습니다.")

    def test_other_tenant_rules_never_resolve(self) -> None:
        from kernels.k2_notify import resolve_recipients

        got = {r.user_id for r in resolve_recipients(scope=self.scope_a, severity="critical")}
        self.assertNotIn(self.user_b.pk, got,
                         "남의 테넌트 수신자가 우리 알림 대상에 들어왔습니다.")

    def test_send_into_another_tenant_event_is_404(self) -> None:
        """쓰기 쪽 IDOR — 남의 이벤트로 발송을 일으킬 수 없다 (D-290)."""
        from django.http import Http404

        from kernels.k2_notify import send

        victim = self._event(self.stream_b, when=timezone.now())
        with self.assertRaises(Http404):
            send(scope=self.scope_a, event_id=victim)

    def test_list_deliveries_excludes_other_tenant(self) -> None:
        from kernels.k2_notify import list_deliveries, send

        mine = self._event(self.stream_a, when=timezone.now())
        theirs = self._event(self.stream_b, when=timezone.now())
        send(scope=self.scope_a, event_id=mine)
        send(scope=self.scope_b, event_id=theirs)

        ids = {r.event_id for r in list_deliveries(scope=self.scope_a)}
        self.assertIn(mine, ids, "자기 이력을 못 봅니다 — 조회가 죽었습니다.")
        self.assertNotIn(theirs, ids, "남의 발송 이력이 보입니다 — 수신자 주소가 샙니다.")

    def test_system_scope_cannot_list(self) -> None:
        from common.tenant_scope import SystemScopeCannotRead

        from kernels.k2_notify import list_deliveries

        with self.assertRaises(SystemScopeCannotRead):
            list_deliveries(scope=self.scope_pipe)

    def test_delivery_row_is_never_orphaned(self) -> None:
        """주인 없는 이력은 §0.4 OR 절을 타고 **모두에게 보인다**."""
        from kernels.k1_event.services import _owner_field
        from kernels.k2_notify import send

        Delivery = apps.get_model("stream_monitors", "DeliveryRecord")
        event_id = self._event(self.stream_a, when=timezone.now())
        record = send(scope=self.scope_a, event_id=event_id)[0]
        row = Delivery._base_manager.get(pk=record.delivery_id)

        if _owner_field(Delivery) == "groups":
            self.assertTrue(row.groups.exists(), "발송 이력에 소유 group 이 없습니다.")
        else:
            self.assertIsNotNone(row.group_id, "발송 이력에 group 이 없습니다.")


class SingleLedgerTest(K2Fixture):
    """[U2] **발송 이력이 곧 K4 의 조치 이력이다** — 두 벌로 적재하지 않는다."""

    def test_report_reads_the_same_rows_as_the_alert(self) -> None:
        from kernels.k2_notify import list_deliveries, send

        event_id = self._event(self.stream_a, when=timezone.now())
        sent = send(scope=self.scope_a, event_id=event_id)
        listed = list_deliveries(scope=self.scope_a, event_id=event_id)

        self.assertEqual([r.delivery_id for r in sent], [r.delivery_id for r in listed],
                         "발송이 만든 행과 조회가 내는 행이 다릅니다 — 두 벌로 적재했습니다.")

    def test_no_separate_report_ledger_model(self) -> None:
        """보고서용 표를 따로 만들면 여기서 멈춘다."""
        candidates = [m.__name__ for m in apps.get_app_config("stream_monitors").get_models()
                      if "action" in m.__name__.lower() or "actionlog" in m.__name__.lower()]
        self.assertEqual([], candidates,
                         f"조치 이력용 별도 표가 생겼습니다: {candidates}. "
                         "DeliveryRecord 하나가 알림 이력이자 조치 이력입니다 (DA-04 K2).")


class KernelScopeSignatureTest(TestCase):
    """[D-281] 커널 공개 함수는 **스코프 없이는 호출 자체가 불가능**해야 한다."""

    def test_every_public_function_refuses_to_run_without_scope(self) -> None:
        import inspect

        from kernels import k2_notify

        problems = []
        for name in ("resolve_recipients", "send", "suppress", "list_deliveries"):
            sig = inspect.signature(getattr(k2_notify, name))
            scope = sig.parameters.get("scope")
            if scope is None:
                problems.append(f"{name}: scope 인자가 없다")
                continue
            if scope.kind is not inspect.Parameter.KEYWORD_ONLY:
                problems.append(f"{name}: scope 가 키워드 전용이 아니다")
            if scope.default is not inspect.Parameter.empty:
                problems.append(f"{name}: scope 에 기본값이 있다 — 필수가 아니다")
        self.assertEqual([], problems, f"D-281 위반: {problems}")


class ChannelTimeoutTest(TestCase):
    """[W0-17 · C-3.3] 외부 발송 호출에 **타임아웃이 빠질 수 없다**."""

    def test_email_channel_always_has_a_timeout(self) -> None:
        from kernels.k2_notify.channels import FALLBACK_EMAIL_TIMEOUT, EmailChannel

        self.assertGreater(EmailChannel.timeout(), 0,
                           "타임아웃이 0 이하입니다 — '없음'과 같습니다.")
        with self.settings(EMAIL_TIMEOUT=None):
            self.assertEqual(FALLBACK_EMAIL_TIMEOUT, EmailChannel.timeout(),
                             "설정이 비었을 때 바닥값으로 떨어지지 않습니다 — "
                             "그 경로가 '타임아웃 없음'이 됩니다 (W0-17).")

    def test_unavailable_channels_say_why(self) -> None:
        """미구현 채널은 **사유를 갖는다** — 빈 자리는 잊힌 자리다 (D-264)."""
        from kernels.k2_notify.channels import UNAVAILABLE, why_unavailable

        self.assertTrue(UNAVAILABLE, "미구현 채널 대장이 비었습니다.")
        for name, reason in UNAVAILABLE.items():
            self.assertTrue(reason.strip(), f"{name}: 사유가 비었습니다.")
            self.assertIn("미구현", why_unavailable(name))
        self.assertIn("알 수 없는 채널", why_unavailable("carrier-pigeon"))


class KernelPublicSurfaceTest(TestCase):
    """DA-04 §2 K2 표가 정한 공개 면 4개가 **실재하는가.**"""

    #: DA-04 §2 K2 의 "공개 면" 열 그대로.
    #: ★ 2026-09-20 — `notice_false_positive` 가 늘었다 (P-16 오탐 ③).
    SURFACE = ["resolve_recipients", "send", "suppress", "list_deliveries",
               "notice_false_positive",
               # ★ P-20 ① (2026-09-22) — 알림 규칙 쓰기 면. 개발 DB 의 규칙이 **0건**
               #   이어서 `send` 가 언제나 `NoRecipients` 를 던지던 자리를 연다.
               #   DA-04 §2 K2 표와 `kernels/k2_notify/__init__.py` 를 같은 커밋에서 고쳤다.
               "save_notification_rule",
               # ★ 차선 D (2026-09-04) — 재알림 N분. `WRITE_NO_PROBE` 에
               #   선등재된 이름을 그대로 쓴다. DA-04 §2 K2 표와
               #   `kernels/k2_notify/__init__.py` 를 같은 커밋에서 고쳤다.
               "renotify",
               # ★ 턴 S · 차선 U56 (WS-14 · UX-43) — S-16 「알림 받는 사람·채널」.
               #   읽기(`notify_rule_overview`) · 저장(`save_rule` — 심각 0명 금지) ·
               #   시험 발송(`send_test_notification` — 훈련 채널로만).
               #   DA-04 §2 K2 표와 `kernels/k2_notify/__init__.py` 를 같은 커밋에서 고쳤다.
               "notify_rule_overview",
               "save_rule",
               "send_test_notification",
               # ★ S-15 「내 정보」의 읽기 면. 쓰기(`me/notify-prefs`)는 U3 의 WS-02 다.
               "my_notify_reach",
               # ★ 턴 T · U3 (P-160 ③) — 웹푸시 발송 문. 부르는 쪽(`notify_prefs.
               #   send_test_push`)과 같은 커밋에서 열렸다.
               "send_webpush", "webpush_missing_env", "WebPushNotConfigured",
               "QUIET_HOURS_REASON", "CHANNEL_NOT_CHOSEN_REASON"]

    def test_public_surface_matches_da04(self) -> None:
        from kernels import k2_notify

        missing = [n for n in self.SURFACE if not hasattr(k2_notify, n)]
        self.assertEqual(
            [], missing,
            f"DA-04 §2 K2 표의 공개 면이 커널에 없습니다: {missing}\n"
            "표를 바꾸려면 DA-04 와 이 목록을 **같은 커밋에서** 함께 고치십시오.")

    def test_kernel_does_not_import_apps(self) -> None:
        """계층 역전 금지 (D-278)."""
        import subprocess
        import sys
        from pathlib import Path

        here = Path(__file__).resolve()
        script = next(
            (c for c in (Path("/repo") / "scripts" / "verify_layers.py",
                         *(p / "scripts" / "verify_layers.py" for p in here.parents[1:4]))
             if c.is_file()), None)
        self.assertIsNotNone(script, "verify_layers.py 를 찾지 못했습니다 (D-285 (4)).")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        self.assertEqual(0, out.returncode, out.stdout + out.stderr)


# ═══════════════════════════════════════════════════════════════════════════
# 시험용 채널 어댑터 — **저하 운전을 만드는 도구**
# ═══════════════════════════════════════════════════════════════════════════
class _BrokenChannel:
    """값으로 실패를 돌려주는 어댑터 (업체가 4xx 를 준 경우)."""

    name = "email"

    def send(self, *, address, subject, body):
        from kernels.k2_notify.channels import SendOutcome

        return SendOutcome(False, "시험용 — 발송 업체가 거부했다")


class _ExplodingChannel:
    """예외를 던지는 어댑터 (업체 서버가 죽은 경우).

    ★ 이 둘을 나눈 이유: 어댑터가 **값으로 실패**하는 경로와 **예외로 죽는** 경로는
      다른 코드가 처리한다. 하나만 시험하면 다른 하나가 프로세스를 세운다.
    """

    name = "email"

    def send(self, *, address, subject, body):
        raise ConnectionError("시험용 — 발송 업체가 응답하지 않는다")
