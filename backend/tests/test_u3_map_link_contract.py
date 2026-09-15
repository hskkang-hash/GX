# -*- coding: utf-8 -*-
"""M2 지도 링크가 딛는 자리 — **F-09 상세가 좌표·주소를 계속 내는가** (UX-45 · 턴 Q).

왜 이 시험이 있나
-----------------
모바일 M2(`features/mobile/pages/MobileEventDetail.tsx::mapLinkUrl`)는 서버가 주는
`lat`·`lng`·`address` 세 칸만 보고 지도 링크를 그린다 — 새 칸을 열지 않았다(P-141
「없는 칸은 지어내지 않는다」). 그 말은 **이 세 칸이 조용히 빠지면 화면도 조용히
빠진다**는 뜻이다 — 버튼이 안 그려질 뿐 콘솔에도, 서버 로그에도 아무것도 안 남는다.

`GET /api/dsm/events/{event_id}` 는 이 저장소 안의 다른 차선(F-05 진입면 대장)도
같이 쓰는 라우트라 U3 가 코드를 고치지 않는다 — 대신 **이 시험으로 계약을 잠근다**
(D-285 ② 「이름으로 잠근다」와 같은 자리): 좌표가 있는 사건 · 주소만 있는 사건 ·
둘 다 없는 사건 셋을 만들어 두고, 세 칸이 서비스 계층과 라우트 계층 양쪽에서
그대로 나오는지 본다. 남의 테넌트 사건은 여전히 404 인지도 함께 잰다 — 지도
링크가 **남의 사건 좌표**를 새는 문이 되지 않게.

★ `test_snapshot_route.py` 와 같은 형이다 — `RequestFactory` + 라우트 핸들러 직접
  호출(HTTP 왕복 없음). 스레드에 요청이 남으면 그다음 시험의 조회가 비는 함정
  (`guardianx-threadlocal-request-false-green`)을 피하려고 `tearDown` 에서 지운다.
"""
from __future__ import annotations

import contextlib

from django.apps import apps
from django.http import Http404
from django.test import Client, RequestFactory, TestCase

from common.tenant_scope import TenantScope

LAT, LNG = 37.3943, 126.9568  # 안양시 근방 — 임의의 유효 좌표(P-20 시드와 같은 자릿수)
ADDRESS_ONLY = "경기도 안양시 만안구 (좌표 없음 · 주소만)"


class _MapLinkFixture(TestCase):
    """테넌트 A/B · A 아래 사건 셋(좌표+주소 · 주소만 · 둘 다 없음)."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="maplink-tenant-A")
        cls.group_b = UserGroup.objects.create(name="maplink-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("maplink_user_a", cls.group_a)
        cls.user_b = cls._user("maplink_user_b", cls.group_b)
        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)

        # ★ 표본마다 **다른 스트림**에 세운다. 같은 스트림·같은 유형으로 10초 창
        #   안에 두 번 부르면 K1 의 중복 억제(DA-04)가 뒤의 것을 앞의 것으로 접는다
        #   — 접힌 표본은 lat/lng/address 가 갱신되지 않고 **첫 표본 그대로** 남는다
        #   (`test_snapshot_route.py` 가 같은 이유로 프레임 없음 표본을 다른 스트림에
        #   세운 것과 같은 함정). 접힌 채로 시험하면 「세 칸이 정확히 난다」를 잰다고
        #   믿으면서 실은 **같은 행을 세 번** 재는 것이 된다.
        cls.stream_geo = cls._stream("maplink-cam-A-geo", cls.group_a)
        cls.stream_addr = cls._stream("maplink-cam-A-addr", cls.group_a)
        cls.stream_none = cls._stream("maplink-cam-A-none", cls.group_a)
        cls.event_with_geo = cls._event(cls.stream_geo, lat=LAT, lng=LNG, address=None)
        cls.event_address_only = cls._event(
            cls.stream_addr, lat=None, lng=None, address=ADDRESS_ONLY)
        cls.event_no_location = cls._event(cls.stream_none, lat=None, lng=None, address=None)
        assert len({cls.event_with_geo, cls.event_address_only,
                    cls.event_no_location}) == 3, "세 표본이 같은 행으로 접혔다"

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
            name=name, code=name, ip_source="rtsp://maplink.invalid/x"), group)

    @classmethod
    def _event(cls, stream, *, lat, lng, address) -> int:
        from kernels.k1_event import record_detection

        return record_detection(
            scope=TenantScope.system(reason="지도 링크 계약 시험 — 파이프라인에 요청자 없음"),
            stream_monitor_id=stream.pk, event_type="fire", severity="critical",
            lat=lat, lng=lng, address=address).event_id

    def tearDown(self) -> None:
        """HTTP 를 때린 시험 뒤 스레드에 요청이 남으면 그다음 조회가 빈다
        (memory: `guardianx-threadlocal-request-false-green`) — 매번 지운다."""
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _request(self, user, event_id):
        request = RequestFactory().get(f"/api/dsm/events/{event_id}")
        request.user = user
        return request

    def _call(self, user, event_id):
        from apps.dsm.api import DsmAPI

        return DsmAPI.event_detail(DsmAPI(), self._request(user, event_id), event_id)


class MapLinkContractTest(_MapLinkFixture):

    # ── 서비스 계층 — 세 표본이 세 칸을 정확히 낸다 ────────────────────────
    def test_service_returns_lat_lng_for_geo_event(self) -> None:
        from apps.dsm import services

        view = services.event_detail(scope=self.scope_a, event_id=self.event_with_geo)
        self.assertEqual(view.lat, LAT)
        self.assertEqual(view.lng, LNG)

    def test_service_returns_address_without_coords(self) -> None:
        from apps.dsm import services

        view = services.event_detail(scope=self.scope_a, event_id=self.event_address_only)
        self.assertIsNone(view.lat)
        self.assertIsNone(view.lng)
        self.assertEqual(view.address, ADDRESS_ONLY)

    def test_service_leaves_both_empty_when_neither_exists(self) -> None:
        """지어내지 않는다 — 좌표도 주소도 없으면 셋 다 비어 있어야 한다.
        (화면의 `mapLinkUrl()` 은 이 상태에서 `null` 을 돌려주고 버튼을 안 그린다.)"""
        from apps.dsm import services

        view = services.event_detail(scope=self.scope_a, event_id=self.event_no_location)
        self.assertIsNone(view.lat)
        self.assertIsNone(view.lng)
        self.assertFalse(view.address)

    # ── 라우트 계층 — 서비스만 맞고 라우트가 새면 계약이 아니다 ────────────
    def test_route_carries_the_same_three_fields(self) -> None:
        body = self._call(self.user_a, self.event_with_geo)
        self.assertEqual(body["lat"], LAT)
        self.assertEqual(body["lng"], LNG)
        self.assertIn("address", body)
        self.assertIn("address_status", body)

    # ── 격리 — 지도 링크가 남의 좌표를 새는 문이 되지 않는다 ────────────────
    def test_another_tenant_gets_404_not_someone_elses_coordinates(self) -> None:
        """서비스도, 라우트도 같은 답(404)이어야 한다 — 서비스만 막고 라우트가
        새면 막은 것이 아니다.

        ★ `event_detail` 라우트(`apps/dsm/api.py`)는 스냅샷 라우트와 달리
          `Http404` 를 `HttpError` 로 번역하지 **않는다** — Django 의 URL 디스패처가
          `Http404` 를 404 응답으로 바꿔 주므로 실제 HTTP 왕복에서는 404 가 난다.
          여기서는 핸들러를 직접 부르므로(디스패처를 안 거친다) 그 번역이 없고,
          `Http404` 가 그대로 올라온다 — **그것이 맞는 동작**이다(익명 401 시험은
          아래에서 실제 HTTP 로 재확인한다)."""
        from apps.dsm import services

        with self.assertRaises(Http404):
            services.event_detail(scope=self.scope_b, event_id=self.event_with_geo)

        with self.assertRaises(Http404):
            self._call(self.user_b, self.event_with_geo)

    # ── 익명 — 좌표 한 칸도 인증 없이는 안 나간다 ───────────────────────────
    def test_anonymous_gets_401(self) -> None:
        # 캐시 처리: 우회 — `X-No-Cache`(`tests.no_cache.NO_CACHE` · D-341 착시 ⑦). 이 파일에서
        #   스택을 타는 갈래는 이 관문 하나다(좌표·주소 대조는 RequestFactory 로 핸들러를 직접
        #   부른다). GET 이라 캐시가 앞에서 옛 200 을 내면 관문이 아니라 캐시를 재게 된다.
        from tests.no_cache import NO_CACHE

        client = Client(raise_request_exception=False)
        resp = client.get(f"/api/dsm/events/{self.event_with_geo}", **NO_CACHE)
        self.assertEqual(resp.status_code, 401)
        self.assertNotIn(b"lat", resp.content)
