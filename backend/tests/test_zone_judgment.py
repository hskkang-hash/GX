# -*- coding: utf-8 -*-
"""D-299 구역 판정 — **선 것과 그 이상을 안 만든 것을 함께 잰다** (D-300).

넷으로 나뉜다:

    ZoneJudgmentTest        섰는가       — 카메라 묶음 판정이 실제로 도는가
    PolygonContractTest     계약 절      — F-03 폴리곤 AC + 경계 사례 넷 (D-365)
    PolygonIsOpenTest       열렸는가     — 열림이 값싼 선언이 아닌가
    ReadyPolygonDataTest    데이터 대조  — 데이터와 상수가 앞서거니 하지 않는가

★ 2026-09-10 — **부작위 시험 둘이 답을 바꿨다** (D-365)
------------------------------------------------------
직전까지 이 파일에는 `NothingWasGuessedTest`(폴리곤을 **안 만들었는가**)와
`PolygonStillLockedTest`(**잠겨 있는가**)가 있었다. 폴리곤이 미확정인 동안 그 둘이
"추측이 계약이 되는 것"을 막았고, 실제로 막았다 — 그동안 아무도 좌표계를 몰래 고르지 못했다.

이번 턴에 좌표 표현·좌표계를 **정식으로 골랐으므로**(D-365) 그 둘은 답이 바뀌었다.
지운 것이 아니라 **교대한 것**이다: 「안 만들었는가」를 재던 자리를 「만든 것이 계약을
지키는가」가 이어받았고, 「잠겨 있는가」를 「열림이 값싼 선언이 아닌가」가 이어받았다.

★ 그러나 **부작위 시험 자체는 사라지지 않았다.** `test_no_gis_dependency_was_pulled_in`
  이 그것이다 — 여는 것과 무엇이든 끌어오는 것은 다른 일이고, 열렸다고 부작위를
  거두면 그 다음에 들어오는 의존은 아무도 안 본다 (D-300).
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


class PolygonContractTest(SimpleTestCase):
    """★ **계약 F-03 폴리곤 절** — 순수 함수로 잰다. DB 없이 경계를 판다 (D-365).

    이 클래스가 `NothingWasGuessedTest`(폴리곤을 **안 만들었는가**)를 대체한다.
    그 시험은 사라진 것이 아니라 **답이 바뀐 것**이다 — 만들지 않았음을 재던 자리가
    만든 것을 재는 자리가 됐다. 잠금 규약이 요구한 교대이고(D-299), 잠금을 올린
    커밋이 이 파일을 함께 고치지 않으면 `verify_zone_polygon.py` 가 exit 1 한다.
    """

    #: 서울 시청 앞 사각형 하나. 축에 나란해서 경계 사례를 손으로 셀 수 있다.
    SQUARE = {"type": "Polygon", "coordinates": [[
        [126.970, 37.560], [126.980, 37.560],
        [126.980, 37.570], [126.970, 37.570], [126.970, 37.560]]]}

    #: ㄷ자 — **오목**. 볼록만 맞는 알고리즘은 여기서 틀린다.
    CONCAVE = {"type": "Polygon", "coordinates": [[
        [0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [3.0, 4.0],
        [3.0, 1.0], [1.0, 1.0], [1.0, 4.0], [0.0, 4.0]]]}

    #: 나비넥타이 — **자기교차.** 「안」이 하나로 정해지지 않는다.
    BOWTIE = {"type": "Polygon", "coordinates": [[
        [0.0, 0.0], [2.0, 2.0], [2.0, 0.0], [0.0, 2.0]]]}

    def test_f03_polygon_contract_ac(self) -> None:
        """★ **계약 AC** — "지정 위험구역(폴리곤) 내 사람·차량 진입".

        `verify_zone_polygon.py` 가 이름으로 요구하는 시험이다. 상수를 올리는 순간
        의무가 되며, 이 이름이 사라지면 정적 게이트가 exit 1 한다.

        재는 것은 계약 문장 그대로 **안과 밖이 갈리는가** 하나다.
        경계·오목·자기교차는 아래에서 따로 판다 — 한 시험에 다 넣으면 무엇이
        깨졌는지가 실패 한 줄에 안 나온다.
        """
        ring = zones._ring(self.SQUARE)

        inside = (126.975, 37.565)      # 한가운데
        outside = (126.990, 37.565)     # 동쪽 바깥

        self.assertTrue(
            zones._point_in_polygon(inside[0], inside[1], ring),
            "구역 한가운데의 진입을 '밖'으로 판정했습니다 — F-03 이 성립하지 않습니다.")
        self.assertFalse(
            zones._point_in_polygon(outside[0], outside[1], ring),
            "★ 구역 밖을 '안'으로 판정했습니다 — 모든 진입이 위험구역 진입이 됩니다. "
            "이쪽이 더 나쁜 오류입니다(경보가 의미를 잃습니다).")

    def test_the_declared_lock_and_the_implementation_agree(self) -> None:
        """상수·구현·좌표계 선언이 **같은 말을 한다.** 하나만 올라간 상태를 막는다."""
        self.assertTrue(zones.ZONE_POLYGON_READY)
        self.assertTrue(zones.is_polygon_ready())
        self.assertTrue(callable(zones._point_in_polygon))
        self.assertEqual(zones.ZONE_CRS, "WGS84",
                         "좌표계 선언이 바뀌었습니다 — 바꾸려면 F-03 계약 해석부터 "
                         "다시 받으십시오. 이 문자열이 곧 계약입니다(D-365).")
        self.assertEqual((zones.LON, zones.LAT), (0, 1),
                         "GeoJSON 좌표 순서가 뒤집혔습니다 — [경도, 위도] 입니다.")

    # ── 경계 사례 넷 (지시 D-360 ②) ─────────────────────────────────────
    def test_a_point_on_a_vertex_is_inside(self) -> None:
        """① **꼭짓점 위.** 광선 투사가 가장 자주 틀리는 자리다."""
        ring = zones._ring(self.SQUARE)
        for lon, lat in ring:
            self.assertTrue(
                zones._point_in_polygon(lon, lat, ring),
                f"꼭짓점 ({lon}, {lat}) 을 '밖'으로 판정했습니다 — 경계에 선 사람을 "
                f"놓칩니다(BOUNDARY_IS_INSIDE={zones.BOUNDARY_IS_INSIDE}).")

    def test_a_point_on_an_edge_is_inside(self) -> None:
        """② **변 위.** 남·북·동·서 네 변을 모두 판다 — 한 변만 맞을 수 있다."""
        ring = zones._ring(self.SQUARE)
        on_edges = (
            (126.975, 37.560),   # 남
            (126.975, 37.570),   # 북
            (126.970, 37.565),   # 서
            (126.980, 37.565),   # 동
        )
        for lon, lat in on_edges:
            self.assertTrue(
                zones._point_in_polygon(lon, lat, ring),
                f"변 위의 점 ({lon}, {lat}) 을 '밖'으로 판정했습니다.")

    def test_a_concave_polygon_judges_the_notch_as_outside(self) -> None:
        """③ **오목 다각형.** ㄷ자의 **패인 곳**은 밖이다.

        볼록 껍질로 판정하는 구현은 여기서만 틀린다 — 사각형 시험은 통과한 채로.
        그래서 이 갈래가 없으면 잘못된 구현이 초록으로 들어온다.
        """
        ring = zones._ring(self.CONCAVE)
        self.assertFalse(
            zones._point_in_polygon(2.0, 3.0, ring),
            "★ ㄷ자의 패인 곳을 '안'으로 판정했습니다 — 볼록 껍질로 재고 있습니다.")
        self.assertTrue(zones._point_in_polygon(0.5, 2.0, ring), "왼쪽 기둥 안")
        self.assertTrue(zones._point_in_polygon(3.5, 2.0, ring), "오른쪽 기둥 안")
        self.assertTrue(zones._point_in_polygon(2.0, 0.5, ring), "아래 이음부 안")

    def test_a_self_intersecting_polygon_is_refused_not_guessed(self) -> None:
        """④ **자기교차는 거절한다.** 조용히 한쪽 규칙을 고르지 않는다.

        고르는 순간 화면이 그린 모양과 시스템이 판정하는 모양이 갈리고,
        **갈렸다는 사실이 아무 데도 안 남는다** (D-284).
        """
        points = zones._ring(self.BOWTIE)
        with self.assertRaises(zones.InvalidPolygon) as caught:
            zones._reject_self_intersection(points)
        self.assertIn("자기교차", str(caught.exception))

    def test_a_simple_polygon_is_not_called_self_intersecting(self) -> None:
        """★ **음성 대조** — 멀쩡한 도형을 거절하면 그 검사는 검사가 아니다 (D-289).

        이웃한 두 변은 언제나 꼭짓점을 공유한다. 그것을 교차로 세면
        **모든 폴리곤이 자기교차**가 되고, 구역 기능이 통째로 죽는다.
        """
        for name, geom in (("사각형", self.SQUARE), ("ㄷ자", self.CONCAVE)):
            zones._reject_self_intersection(zones._ring(geom))   # 안 터져야 한다

    # ── 잘못 그린 것은 잘못 그렸다고 말한다 ─────────────────────────────
    def test_a_flipped_coordinate_pair_is_caught(self) -> None:
        """★ 위경도가 뒤집혀 들어오면 **판정하지 않고 잡는다.**

        이 모듈에서 가장 흔한 사고다. 뒤집힌 채로 판정하면 서울의 구역이
        인도양 어딘가가 되고, 그러면 **모든 진입이 구역 밖**이 된다 — 조용히.
        """
        flipped = {"type": "Polygon", "coordinates": [[
            [37.560, 126.970], [37.560, 126.980], [37.570, 126.980]]]}
        with self.assertRaises(zones.InvalidPolygon) as caught:
            zones._ring(flipped)
        self.assertIn("위도", str(caught.exception))

    def test_a_polygon_with_a_hole_is_refused(self) -> None:
        """구멍은 받지 않는다 — **조용히 무시하지 않는다.**

        무시하면 구멍 안이 '구역 안'으로 판정되고, 그 오판은 화면에 안 보인다.
        """
        holed = {"type": "Polygon", "coordinates": [
            self.SQUARE["coordinates"][0],
            [[126.973, 37.563], [126.977, 37.563], [126.977, 37.567]]]}
        with self.assertRaises(zones.InvalidPolygon):
            zones._ring(holed)

    def test_a_degenerate_ring_is_refused(self) -> None:
        """꼭짓점 둘짜리에는 '안'이 없다 — 넓이 없는 도형을 판정하지 않는다."""
        line = {"type": "Polygon", "coordinates": [[[0.0, 0.0], [1.0, 1.0]]]}
        with self.assertRaises(zones.InvalidPolygon):
            zones._ring(line)

    def test_an_unclosed_ring_is_accepted(self) -> None:
        """닫는 점이 없어도 받는다 — 화면이 안 닫고 보내는 일이 흔하다.

        닫힌 것과 안 닫힌 것이 **같은 판정**을 내야 한다. 다르면 그리는 쪽의
        사소한 습관이 판정을 바꾼다.
        """
        closed = zones._ring(self.SQUARE)
        unclosed = zones._ring({"type": "Polygon",
                                "coordinates": [self.SQUARE["coordinates"][0][:-1]]})
        self.assertEqual(closed, unclosed)


class PolygonIsOpenTest(SimpleTestCase):
    """★ 열렸는가 — 그리고 **열림이 값싼 선언이 아닌가.**

    `PolygonStillLockedTest` 를 대체한다. 잠금 규약은 그대로이고 방향만 뒤집혔다:
    잠겨 있으면 사유를 요구했고, 열려 있으면 **구현과 시험**을 요구한다.
    """

    def test_the_reason_string_is_kept_for_the_way_back(self) -> None:
        """사유를 **지우지 않았다.** 되돌리는 날 사유 없이 되돌릴 수 있으면 안 된다."""
        reason = zones.ZONE_POLYGON_NOT_READY_REASON.strip()
        self.assertTrue(reason, "되돌림용 사유가 지워졌습니다 — 되돌림이 조용해집니다.")
        self.assertIn("F-03", reason)

    def test_an_undrawn_zone_still_refuses_to_judge(self) -> None:
        """★ 코드가 섰다고 **안 그린 구역이 판정되지는 않는다.**

        `geometry_status='not_implemented'` 는 여전히 `NotImplementedError` 다 —
        이것이 「안 그렸다」와 「밖이다」를 가르는 자리이고, 여기가 무너지면
        도형을 안 넣은 구역이 **영원히 아무도 안 걸리는 구역**이 된다.
        """
        Zone = apps.get_model("stream_monitors", "Zone")
        undrawn = Zone(name="아직 안 그린 구역", kind="polygon",
                       geometry_status="not_implemented")
        with self.assertRaises(NotImplementedError) as caught:
            zones.contains(undrawn, lat=37.565, lng=126.975)
        self.assertIn("F-03", str(caught.exception))

    def test_a_drawn_zone_judges(self) -> None:
        """음성 대조 — 그린 구역은 **실제로 판정한다.** 전부 멈추면 그건 구현이 아니다."""
        Zone = apps.get_model("stream_monitors", "Zone")
        drawn = Zone(name="그린 구역", kind="polygon", geometry_status="ready",
                     geometry=PolygonContractTest.SQUARE)
        self.assertTrue(zones.contains(drawn, lat=37.565, lng=126.975))
        self.assertFalse(zones.contains(drawn, lat=37.565, lng=126.990))
        self.assertTrue(zones.point_in_zone(drawn, lat=37.565, lng=126.975))

    def test_a_polygon_zone_asked_with_a_camera_id_says_so(self) -> None:
        """좌표 없이 물으면 **그 질문이 아니라고** 말한다 — False 를 돌려주지 않는다."""
        Zone = apps.get_model("stream_monitors", "Zone")
        drawn = Zone(name="그린 구역", kind="polygon", geometry_status="ready",
                     geometry=PolygonContractTest.SQUARE)
        with self.assertRaises(ValueError):
            zones.contains(drawn, camera_id=1)

    def test_zone_kernel_and_polygon_are_still_two_locks(self) -> None:
        """두 잠금이 **여전히 둘이다.** 둘 다 열렸다고 한 이름으로 합치지 않았다."""
        from pathlib import Path

        from tests.e2e.e2e_contract import kernel_present

        self.assertTrue(kernel_present("ZONE"), "E2E-2 3단계가 다시 잠겼습니다.")
        self.assertTrue(zones.ZONE_POLYGON_READY)
        src = Path(zones.__file__).read_text(encoding="utf-8")
        self.assertIn("ZONE_POLYGON_READY: bool =", src,
                      "폴리곤 잠금이 제 이름의 상수가 아니게 됐습니다 — "
                      "KERNEL_READY 와 한 칸이 되면 하나를 내릴 때 둘 다 내려갑니다.")
        self.assertIn("KERNEL_READY: bool =", src)

    def test_no_gis_dependency_was_pulled_in(self) -> None:
        """★ **부작위는 그대로 잰다** (D-300). 열었다고 GIS 를 끌어오지 않았다.

        계약에 GIS 요구가 없고, 의존 하나가 배포 하나를 어렵게 한다.
        이 시험이 사라지면 다음 사람이 `django.contrib.gis` 를 조용히 넣는다.
        """
        from pathlib import Path

        src = Path(zones.__file__).read_text(encoding="utf-8")
        body = "\n".join(line for line in src.split("\n")
                         if not line.lstrip().startswith("#"))
        for token in ("GEOSGeometry", "contrib.gis", "shapely", "pyproj"):
            self.assertNotIn(
                token, body,
                f"GIS 의존({token})이 들어왔습니다 — 판정은 순수 함수로 섭니다.")

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
    """★ **데이터와 상수가 앞서거니 하는 것**을 잡는다 — 정적 게이트가 못 보는 쪽.

    상수가 True 가 된 지금(D-365) 이 대조의 **방향이 둘**이 됐다:

        ① 되돌아가는 쪽 — 상수를 내렸는데 `ready` 행이 남아 있다
                          (화면은 폴리곤이 돈다고 믿고 코드는 미구현이다)
        ② 앞서가는 쪽   — `ready` 인데 **도형이 판정 불가**다
                          (「가동」이라 적혀 있는데 부르면 멈춘다 — 더 조용한 고장이다)

    ②는 상수가 False 이던 동안에는 존재할 수 없던 갈래다. 열면서 생긴 새 위험을
    열면서 함께 잰다 — 열고 나서 나중에 재면 그 사이가 빈다.
    """

    def test_no_ready_polygon_zone_without_the_flag(self) -> None:
        """① `geometry_status='ready'` 인 Zone 이 있는데 상수가 False 면 실패한다.

        정적 게이트는 DB 를 못 보므로 이 대조는 여기서만 가능하다 (D-299).
        지금은 상수가 True 라 이 갈래가 **안 돈다** — 되돌리는 날을 위해 남긴다.
        """
        Zone = apps.get_model("stream_monitors", "Zone")
        ready = Zone._base_manager.filter(geometry_status="ready")
        if not zones.ZONE_POLYGON_READY:
            self.assertEqual(
                [], list(ready.values_list("name", flat=True)),
                "폴리곤 판정이 잠겨 있는데 geometry_status='ready' 인 구역이 있습니다 — "
                "데이터가 코드를 앞질렀습니다. 상수를 올리거나 그 행을 되돌리십시오.")

    def test_positive_control_the_check_can_fail(self) -> None:
        """★ 위 시험이 **실패할 수 있는가.** 실패할 수 없는 시험은 시험이 아니다 (D-277).

        상수가 True 인 지금 ①의 몸통은 통째로 건너뛰어진다. 그대로 두면 이 대조는
        **언제나 통과하는 시험** — 즉 시험이 아닌 것 — 이 된다. 그래서 상수를 잠깐
        내려 그 갈래를 실제로 돌린다. 건너뛰는 시험을 통과로 세지 않는다 (D-301).
        """
        self._zone("폴리곤 앞지르기", self.group_a, [], kind="polygon",
                   geometry_status="ready")
        original = zones.ZONE_POLYGON_READY
        zones.ZONE_POLYGON_READY = False
        self.addCleanup(setattr, zones, "ZONE_POLYGON_READY", original)
        with self.assertRaises(AssertionError):
            self.test_no_ready_polygon_zone_without_the_flag()

    def test_every_ready_zone_can_actually_be_judged(self) -> None:
        """② **`ready` 라고 적힌 구역은 실제로 판정된다.**

        「가동」이라 적혀 있는데 부르면 `InvalidPolygon` 으로 멈추는 행은, 화면에서
        멀쩡해 보이고 판정에서만 사라진다 — **경보가 안 오는 위험구역**이다.
        그 상태는 아무도 신고하지 않으므로 여기서 전수로 판다.
        """
        Zone = apps.get_model("stream_monitors", "Zone")
        broken = []
        for zone in Zone._base_manager.filter(geometry_status="ready",
                                              kind="polygon"):
            try:
                zones.contains(zone, lat=37.565, lng=126.975)
            except zones.InvalidPolygon as exc:
                broken.append(f"{zone.name}: {exc}")
        self.assertEqual(
            broken, [],
            "geometry_status='ready' 인데 판정할 수 없는 구역이 있습니다 — "
            "화면에는 '가동'으로 보이고 판정에서만 사라집니다: "
            + " · ".join(broken))

    def test_positive_control_a_broken_ready_zone_is_caught(self) -> None:
        """★ 위 ②가 **실제로 잡는가.** 깨진 행을 하나 심어 본다 (D-277)."""
        self._zone("도형 없는 가동 구역", self.group_a, [], kind="polygon",
                   geometry_status="ready", geometry=None)
        with self.assertRaises(AssertionError):
            self.test_every_ready_zone_can_actually_be_judged()
