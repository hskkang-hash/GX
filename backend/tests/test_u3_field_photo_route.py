# -*- coding: utf-8 -*-
"""UX-45 M3 — 현장 사진 업로드 라우트 (`POST /events/{id}/field-photo`).

넷을 잰다(스냅샷 라우트 시험과 같은 형 — D-285 ② 「이름으로 잠근다」):

    ① 익명은 401
    ② 남의 테넌트 사건은 404 — 존재 여부도 새지 않는다
    ③ 크기·형식 위반은 422 — 저장소까지 안 간다(`_upload_bytes` 호출 여부로 잰다)
    ④ 정상 업로드는 `DsmFieldPhoto` 행 하나를 남기고, 그 행의 테넌트가 업로더의
       테넌트와 같다

MinIO 는 이 개발 컨테이너에서 닿지 않는다(`minio.invalid` — 실측). 그래서 `_upload_bytes`
를 patch 한다 — `test_snapshot_route.py` 가 `detection_snapshot.fetch_snapshot` 를
patch 하는 것과 같은 이유다: **저장소 가용성이 아니라 우리 코드의 판단**을 잰다.
"""
from __future__ import annotations

import contextlib
import io
from unittest import mock

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import Client, RequestFactory, TestCase

from common.tenant_scope import TenantScope

UPLOAD_BYTES = "apps.dsm.field._upload_bytes"


class _FieldPhotoFixture(TestCase):
    """테넌트 A/B · A 의 스트림에 사건 하나."""

    @classmethod
    def setUpTestData(cls) -> None:  # noqa: N802
        UserGroup = apps.get_model("user", "UserGroup")
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None

        cls.group_a = UserGroup.objects.create(name="fieldphoto-tenant-A")
        cls.group_b = UserGroup.objects.create(name="fieldphoto-tenant-B")
        UserGroup.objects.filter(
            pk__in=[cls.group_a.pk, cls.group_b.pk]).update(created_by=None)

        cls.user_a = cls._user("fieldphoto_user_a", cls.group_a)
        cls.user_b = cls._user("fieldphoto_user_b", cls.group_b)
        cls.scope_a = TenantScope.of(cls.user_a)
        cls.scope_b = TenantScope.of(cls.user_b)

        cls.stream = cls._stream("fieldphoto-cam-A", cls.group_a)
        cls.event_id = cls._event(cls.stream)

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
            name=name, code=name, ip_source="rtsp://fieldphoto.invalid/x"), group)

    @classmethod
    def _event(cls, stream) -> int:
        from kernels.k1_event import record_detection

        return record_detection(
            scope=TenantScope.system(reason="현장 사진 시험 — 파이프라인에 요청자 없음"),
            stream_monitor_id=stream.pk, event_type="fire", severity="critical").event_id

    def tearDown(self) -> None:
        with contextlib.suppress(Exception):
            from core.middleware.refresh_token import thread_local

            thread_local.request = None
        super().tearDown()

    def _request(self, user, event_id, photo):
        request = RequestFactory().post(f"/api/dsm/events/{event_id}/field-photo")
        request.user = user
        return request

    def _call(self, user, event_id, *, content=b"\xff\xd8\xff\xe0fake", content_type="image/jpeg"):
        from apps.dsm.api_u3 import DsmU3API

        photo = SimpleUploadedFile("scene.jpg", content, content_type=content_type)
        request = self._request(user, event_id, photo)
        return DsmU3API.upload_field_photo(DsmU3API(), request, event_id, photo)


class FieldPhotoRouteTest(_FieldPhotoFixture):

    # ── ① 익명 401 ───────────────────────────────────────────────────────
    def test_rule1_anonymous_gets_401(self) -> None:
        # 캐시 처리: 우회 — `X-No-Cache`(`tests.no_cache.NO_CACHE` · D-341 착시 ⑦). 이 파일에서
        #   스택을 타는 갈래는 이 관문 하나다(나머지 셋은 RequestFactory 로 핸들러를 직접 부른다).
        #   관문을 재는 시험이 캐시를 재면 안 된다.
        from tests.no_cache import NO_CACHE

        client = Client(raise_request_exception=False)
        photo = SimpleUploadedFile("scene.jpg", b"\xff\xd8\xff\xe0fake", content_type="image/jpeg")
        resp = client.post(f"/api/dsm/events/{self.event_id}/field-photo", {"photo": photo},
                           **NO_CACHE)
        self.assertEqual(resp.status_code, 401)

    # ── ② 남의 테넌트 404 ────────────────────────────────────────────────
    def test_rule2_another_tenant_gets_404(self) -> None:
        from ninja.errors import HttpError

        with mock.patch(UPLOAD_BYTES, return_value="bucket/field-photos/1/x.jpg"):
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_b, self.event_id)
        self.assertEqual(caught.exception.status_code, 404)

    # ── ③ 크기·형식 위반은 저장소까지 안 간다 ───────────────────────────────
    def test_rule3_oversized_photo_is_422_and_never_uploaded(self) -> None:
        from ninja.errors import HttpError

        from apps.dsm.field import MAX_BYTES

        with mock.patch(UPLOAD_BYTES) as uploader:
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_a, self.event_id, content=b"x" * (MAX_BYTES + 1))
        self.assertEqual(caught.exception.status_code, 422)
        uploader.assert_not_called()

    def test_rule3_disallowed_format_is_422_and_never_uploaded(self) -> None:
        from ninja.errors import HttpError

        with mock.patch(UPLOAD_BYTES) as uploader:
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_a, self.event_id, content=b"not a real video",
                           content_type="video/mp4")
        self.assertEqual(caught.exception.status_code, 422)
        uploader.assert_not_called()

    # ── 저장소가 죽으면 503 ─────────────────────────────────────────────
    def test_a_dead_store_is_503_not_500(self) -> None:
        from ninja.errors import HttpError

        from apps.dsm.field import FieldPhotoStorageDown

        with mock.patch(UPLOAD_BYTES, side_effect=FieldPhotoStorageDown("저장소 연결 안 됨")):
            with self.assertRaises(HttpError) as caught:
                self._call(self.user_a, self.event_id)
        self.assertEqual(caught.exception.status_code, 503)

    # ── ④ 정상 업로드 — 행이 남고, 테넌트가 업로더의 것과 같다 ───────────────
    def test_rule4_success_creates_a_row_owned_by_the_uploader_tenant(self) -> None:
        DsmFieldPhoto = apps.get_model("stream_monitors", "DsmFieldPhoto")
        self.assertEqual(DsmFieldPhoto.objects.filter(event_id=self.event_id).count(), 0)

        with mock.patch(UPLOAD_BYTES,
                        return_value=f"bucket/field-photos/{self.event_id}/x.jpg") as uploader:
            result = self._call(self.user_a, self.event_id)

        uploader.assert_called_once()
        self.assertEqual(result["event_id"], self.event_id)
        self.assertIn("photo_id", result)
        self.assertEqual(result["content_type"], "image/jpeg")

        row = DsmFieldPhoto.objects.get(pk=result["photo_id"])
        self.assertEqual(row.event_id, self.event_id)
        self.assertEqual(row.group_id, self.group_a.pk)
        self.assertEqual(row.purpose_code, "dsm.field_photo")
        self.assertTrue(row.object_key)

    def test_the_four_rules_are_all_present(self) -> None:
        required = {
            "①": "test_rule1_anonymous_gets_401",
            "②": "test_rule2_another_tenant_gets_404",
            "③": "test_rule3_oversized_photo_is_422_and_never_uploaded",
            "④": "test_rule4_success_creates_a_row_owned_by_the_uploader_tenant",
        }
        for no, name in required.items():
            self.assertTrue(
                hasattr(type(self), name),
                f"규약 {no} 의 시험 `{name}` 이 없습니다.")
