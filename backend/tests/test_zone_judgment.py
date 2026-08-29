# -*- coding: utf-8 -*-
"""D-299 구역 판정 — **선 것과 그 이상을 안 만든 것을 함께 잰다** (D-300).

셋으로 나뉜다:

    ZoneJudgmentTest        섰는가          — 카메라 묶음 판정이 실제로 도는가
    NothingWasGuessedTest   안 만들었는가    — 폴리곤을 추측으로 만들지 않았는가 (D-300)
    PolygonStillLockedTest  잠겨 있는가      — 잠금이 값싼 선언이 아닌가

★ 왜 "안 만들었는가"를 시험하나 (D-300)
---------------------------------------
금지된 산출물이 있는 작업에서 **"무엇을 만들었나"만 재면 금지선을 넘은 것이 초록 속에
숨는다.** 여기서 금지된 것은 폴리곤이다 — 좌표 표현·좌표계가 미확정인데 지금 고르면
그 선택이 곧 F-03 의 계약이 된다(D-280). 그래서 만들지 않았음을 시험이 잰다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.test import SimpleTestCase, TestCase

from common.tenant_scope import TenantScope
from stream_monitors.services import zones

#: 컨테이너에서는 backend 가 `/app` 이고 저장소는 `/repo` 에 따로 마운트된다
#: (docker-compose 의 `./scripts:/repo/scripts:ro`). 그래서 `__file__` 의 부모를
#: 세는 것만으로는 뿌리에 닿지 못한다 — `test_k1_event_kernel.py` 와 **같은 방식**으로
#: 찾는다. 두 곳이 다른 방식을 쓰면 한쪽만 고쳐지고 다른 쪽은 조용히 skip 이 된다.
REPO_ROOT_CANDIDATES = ("/repo",)


def _find_script(name: str):
    """저장소 게이트 스크립트의 실경로. 없으면 `None` — **추측하지 않는다.**"""
    from pathlib import Path

    here = Path(__file__).resolve()
    for root in (*(Path(c) for c in REPO_ROOT_CANDIDATES), *here.parents[1:4]):
        candidate = root / "scripts" / name
        if candidate.is_file():
            return candidate
    return None


class _ZoneFixture(TestCase):
    """테넌트 A/B · A 에 구역 둘(가까운 구역·먼 구역)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")

        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="zone-tenant-A")
        cls.group_b = UserGroup.objects.create(name="zone-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("zone_user_a", cls.group_a)
        cls.user_b = cls._user("zone_user_b", cls.group_b)

        cls.cam_gauge = cls._stream("zone-gauge", cls.group_a)
        cls.cam_people = cls._stream("zone-people", cls.group_a)
        cls.cam_far = cls._stream("zone-far", cls.group_a)
        cls.cam_theirs = cls._stream("zone-theirs", cls.group_b)

        cls.zone_near = cls._zone("보행교구간", cls.group_a,
                                  [cls.cam_gauge, cls.cam_people])
        cls.zone_far = cls._zone("상류구간", cls.group_a, [cls.cam_far])
        cls.zone_theirs = cls._zone("남의구역", cls.group_b, [cls.cam_theirs])

        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)
        cls.scope_pipe = TenantScope.system(
            reason="구역 판정 시험 — 파이프라인에는 요청자가 없다 (D-281)")

    # ── 도우미 ───────────────────────────────────────────────────────────
    @staticmethod
    def _own(obj, group):
        from kernels.k1_event.services import _owner_field

        if _owner_field(type(obj)) == "groups":
            obj.groups.set([group])
        else:
            obj.group = group
            obj.save(update_fields=["group"])
        return obj

    @classmethod
    def _user(cls, username, group):
        CoreUser = apps.get_model("user", "CoreUser")
        user = CoreUser.objects.create_user(
            username=username, password="test-only-not-a-secret", is_active=True,
            email=f"{username}@test.invalid")
        link_field = CoreUser._meta.get_field("userprofilelink")
        link_field.related_model.objects.create(
            **{link_field.remote_field.name: user, "group": group})
        return user

    @classmethod
    def _stream(cls, name, group):
        StreamMonitor = apps.get_model("stream_monitors", "StreamMonitor")
        return cls._own(StreamMonitor.objects.create(
            name=name, code=name, ip_source="rtsp://zone.invalid/x"), group)

    @classmethod
    def _zone(cls, name, group, streams, **kwargs):
        Zone = apps.get_model("stream_monitors", "Zone")
        zone = cls._own(Zone.objects.create(
            name=name, kind=kwargs.pop("kind", "camera_group"), **kwargs), group)
        zone.cameras.set(streams)
        return zone

    def _event(self, stream, *, event_type, severity="warning"):
        from kernels.k1_event import get_event, record_detection

        result = record_detection(
            scope=self.scope_pipe, stream_monitor_id=stream.pk,
            event_type=event_type, severity=severity,
            snapshot_path=f"minio://zone/{stream.pk}-{event_type}.jpg")
        return get_event(result.event_id, scope=self.scope_a)


class ZoneJudgmentTest(_ZoneFixture):
    """★ 섰는가 — 카메라 묶음 판정이 **실제로** 돈다."""

    def test_camera_in_zone_is_contained(self) -> None:
        self.assertTrue(zones.contains(self.zone_near, camera_id=self.cam_gauge.pk))
        # 음성 대조 — 언제나 참인 판정은 판정이 아니다 (D-289)
        self.assertFalse(zones.contains(self.zone_near, camera_id=self.cam_far.pk))

    def test_camera_group_judgment_needs_a_camera(self) -> None:
        """좌표만 주면 답하지 않는다 — camera_group 이 답할 수 있는 질문이 아니다."""
        with self.assertRaises(ValueError):
            zones.contains(self.zone_near, lat=37.4, lng=126.9)

    def test_two_cameras_in_one_zone_are_the_same_zone(self) -> None:
        zone = zones.same_zone(self.cam_gauge.pk, self.cam_people.pk, scope=self.scope_a)
        self.assertIsNotNone(zone)
        self.assertEqual(self.zone_near.pk, zone.pk)

    def test_cameras_in_different_zones_are_not(self) -> None:
        self.assertIsNone(
            zones.same_zone(self.cam_gauge.pk, self.cam_far.pk, scope=self.scope_a))

    def test_a_camera_is_not_its_own_pair(self) -> None:
        """자기 자신과의 결합은 F-03 이 묻는 질문이 아니다 — 언제나 참이 되면 시험이 죽는다."""
        self.assertIsNone(
            zones.same_zone(self.cam_gauge.pk, self.cam_gauge.pk, scope=self.scope_a))

    def test_inactive_zone_does_not_judge(self) -> None:
        """비활성 구역은 판정에 쓰이지 않는다 — 끈 것이 계속 돌면 끈 것이 아니다."""
        self.zone_near.is_active = False
        self.zone_near.save(update_fields=["is_active"])
        self.assertIsNone(
            zones.same_zone(self.cam_gauge.pk, self.cam_people.pk, scope=self.scope_a))

    def test_f03_combination_raises_the_severity(self) -> None:
        flood = self._event(self.cam_gauge, event_type="flood")
        person = self._event(self.cam_people, event_type="person")

        combined = zones.combine_in_zone(
            scope=self.scope_a, primary=flood, secondary=person)
        self.assertIsNotNone(combined)
        self.assertEqual("critical", combined.severity)
        self.assertNotEqual(flood.severity, combined.severity)
        self.assertIn(self.zone_near.name, combined.reason)

    def test_f03_combination_does_not_overwrite_the_stored_severity(self) -> None:
        """★ 결합은 **값**이다. 저장된 등급을 덮으면 '무엇이 실제로 났는가'가 사라진다.

        D-293 이 `status` 가 `verdict` 를 덮는 것을 금지한 것과 같은 계열이다.
        """
        from kernels.k1_event import get_event

        flood = self._event(self.cam_gauge, event_type="flood")
        person = self._event(self.cam_people, event_type="person")
        zones.combine_in_zone(scope=self.scope_a, primary=flood, secondary=person)

        self.assertEqual(
            "warning", get_event(flood.event_id, scope=self.scope_a).severity,
            "결합이 저장된 등급을 덮었습니다.")

    def test_isolation_another_tenant_cannot_see_our_zones(self) -> None:
        """규약 ② 계열 — 남의 구역이 우리 판정에 섞이지 않는다 (D-290)."""
        self.assertEqual(
            [], zones.zones_for_camera(self.cam_gauge.pk, scope=self.scope_b),
            "다른 테넌트가 우리 구역을 봤습니다.")
        self.assertIsNone(
            zones.same_zone(self.cam_gauge.pk, self.cam_people.pk, scope=self.scope_b),
            "다른 테넌트의 스코프로 우리 구역 결합이 성립했습니다.")
        # 양성 대조 — 우리 스코프로는 보인다. 안 보이면 위 초록은 뜻이 없다.
        self.assertTrue(zones.zones_for_camera(self.cam_gauge.pk, scope=self.scope_a))


class NothingWasGuessedTest(SimpleTestCase):
    """★ **그 이상을 만들지 않았는가** — 부작위 시험 (D-300).

    폴리곤은 좌표 표현·좌표계가 미확정이다. 지금 고르면 그 선택이 곧 F-03 의 계약이
    되고(D-280), 그 사실은 나중에 남지 않는다. 그래서 **안 만들었음**을 잰다.
    """

    def test_no_point_in_polygon_implementation_exists(self) -> None:
        from pathlib import Path

        src = Path(zones.__file__).read_text(encoding="utf-8")
        # 함수 정의가 없어야 한다. 주석·독스트링의 언급은 구현이 아니다.
        self.assertNotIn(
            "def _point_in_polygon", src,
            "폴리곤 판정 구현이 생겼습니다 — 그렇다면 ZONE_POLYGON_READY 를 올리고 "
            "F-03 AC 시험을 붙이십시오. 구현만 있고 잠금이 그대로인 상태가 가장 나쁩니다.")

    def test_no_coordinate_system_was_chosen(self) -> None:
        """좌표계를 코드가 고르지 않았다 — 고르는 자리는 F-03 설계이지 이 파일이 아니다."""
        from pathlib import Path

        src = Path(zones.__file__).read_text(encoding="utf-8")
        body = "\n".join(
            line for line in src.split("\n")
            if not line.lstrip().startswith("#"))
        for token in ("EPSG", "srid", "SRID", "GEOSGeometry", "gis"):
            self.assertNotIn(
                token, body,
                f"좌표계·GIS 의존({token})이 들어왔습니다 — 계약에 GIS 요구가 없고, "
                f"지금 고른 좌표계가 곧 F-03 의 계약이 됩니다 (D-280).")

    def test_zone_editing_surface_was_not_built(self) -> None:
        """구역을 **만드는** 면은 이번 범위가 아니다 — 만들면 쓰기 격리 시험이 함께 늘어야 한다."""
        self.assertFalse(
            [n for n in zones.__all__ if n.startswith(("create", "update", "delete"))],
            "구역 편집 함수가 공개 면에 생겼습니다 — 쓰기 면이 늘면 "
            "test_tenant_isolation.py 의 WRITE_PROBES 도 함께 늘어야 합니다 (D-290).")


class PolygonStillLockedTest(SimpleTestCase):
    """★ 잠겨 있는가 — 그리고 그 잠금이 **값싼 선언이 아닌가.**"""

    def test_polygon_is_locked(self) -> None:
        self.assertFalse(zones.ZONE_POLYGON_READY)
        self.assertFalse(zones.is_polygon_ready())

    def test_the_lock_carries_a_reason(self) -> None:
        """"안 됐다" 는 말은 사유를 요구한다 (D-264)."""
        reason = zones.ZONE_POLYGON_NOT_READY_REASON.strip()
        self.assertTrue(reason)
        self.assertGreater(
            len(reason), 60,
            "사유가 한 줄 변명입니다 — 무엇이 없어서 못 하는지를 적으십시오.")
        self.assertIn("F-03", reason, "어느 계약 조항이 걸린 일인지가 사유에 없습니다.")

    def test_polygon_zone_refuses_to_judge(self) -> None:
        """★ 조용히 False 를 돌려주지 않는다 — 미구현이 '구역 밖'으로 위장하지 않는다."""
        Zone = apps.get_model("stream_monitors", "Zone")
        unsaved = Zone(name="폴리곤 자리", kind="polygon")
        with self.assertRaises(NotImplementedError) as caught:
            zones.contains(unsaved, lat=37.4, lng=126.9)
        self.assertIn("F-03", str(caught.exception))

    def test_zone_kernel_is_present_but_polygon_is_not(self) -> None:
        """두 잠금이 **다른 것을 잠근다** — 하나가 다른 하나를 열지 않는다."""
        from tests.e2e.e2e_contract import kernel_present

        self.assertTrue(kernel_present("ZONE"), "E2E-2 3단계가 다시 잠겼습니다.")
        self.assertFalse(zones.ZONE_POLYGON_READY,
                         "구역이 열렸다고 폴리곤까지 열렸습니다 — 두 잠금이 붙었습니다.")

    def test_the_static_gate_agrees(self) -> None:
        """`scripts/verify_zone_polygon.py` 와 **같은 말을 하는가.**

        두 눈이 다른 말을 하면 어느 쪽도 못 믿는다 (D-227 이 만든 상태가 그것이었다).
        """
        import subprocess
        import sys

        script = _find_script("verify_zone_polygon.py")
        self.assertIsNotNone(
            script,
            "verify_zone_polygon.py 를 찾지 못했습니다. 컨테이너라면 docker-compose 의 "
            "`./scripts:/repo/scripts:ro` 마운트가 빠진 것입니다 (D-285 (4)). "
            "★ 이 시험은 skip 하지 않습니다 — 못 찾은 것은 '환경 미비'가 아니라 "
            "**되돌아간 것**입니다.")
        proc = subprocess.run([sys.executable, str(script)],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace")
        self.assertEqual(0, proc.returncode,
                         f"정적 게이트가 실패했습니다:\n{proc.stdout}\n{proc.stderr}")


class ReadyPolygonDataTest(_ZoneFixture):
    """★ **데이터가 상수를 앞지르는 것**을 잡는다 — 정적 게이트가 못 보는 쪽."""

    def test_no_ready_polygon_zone_without_the_flag(self) -> None:
        """`geometry_status='ready'` 인 Zone 이 있는데 상수가 False 면 실패한다.

        그 상태에서는 화면과 운영자는 폴리곤이 돈다고 믿는데 코드는 미구현이다.
        정적 게이트는 DB 를 못 보므로 이 대조는 여기서만 가능하다 (D-299).
        """
        Zone = apps.get_model("stream_monitors", "Zone")
        ready = Zone._base_manager.filter(geometry_status="ready")
        if not zones.ZONE_POLYGON_READY:
            self.assertEqual(
                [], list(ready.values_list("name", flat=True)),
                "폴리곤 판정이 잠겨 있는데 geometry_status='ready' 인 구역이 있습니다 — "
                "데이터가 코드를 앞질렀습니다. 상수를 올리거나 그 행을 되돌리십시오.")

    def test_positive_control_the_check_can_fail(self) -> None:
        """★ 위 시험이 **실패할 수 있는가.** 실패할 수 없는 시험은 시험이 아니다 (D-277)."""
        Zone = apps.get_model("stream_monitors", "Zone")
        self._zone("폴리곤 앞지르기", self.group_a, [], kind="polygon",
                   geometry_status="ready")
        with self.assertRaises(AssertionError):
            self.test_no_ready_polygon_zone_without_the_flag()
