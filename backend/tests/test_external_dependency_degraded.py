# -*- coding: utf-8 -*-
"""외부 의존이 죽어도 화면이 서는가 — 저하 운전 시험 (W0-17).

무엇을 지키는 시험인가
    이 저장소는 외부 의존(스트리밍 서버·AI 분석·FlightBird)에 직접 붙는다.
    실측에서 **목록 API 는 스트리밍 서버가 없으면 통째로 HTTP 500** 이었다
    (evidence/W0-16/http_role_split_test.md §4-2 — 격리 시험을 하려면 매번 스텁이
    필요했다는 사실 자체가 저하 운전 부재의 증거였다).

    드론 목록은 스트리밍 서버와 무관하게 보여야 한다. 이 시험은 그 문장을 지킨다:
      ① 외부가 죽어도 예외가 올라오지 않는다 — 실패는 **값**으로 온다
      ② 타임아웃은 빠뜨릴 수 없다 — 호출부가 잊어도 설정값이 들어간다
      ③ 죽은 것을 **성공으로 위장하지 않는다** — 상태가 'unavailable' 로 표시된다

DB 를 쓰지 않는다. dj-core 1.1.6 은 마이그레이션을 0부터 쌓지 못하므로(P-LOCAL-1)
DB 의존 시험은 이 환경에서 돌지 않는다. 여기서 재는 것은 실패 처리 경로다.
"""
from __future__ import annotations

from unittest import mock

import requests
from django.test import SimpleTestCase, override_settings

from common.external_http import (
    AVAILABLE,
    UNAVAILABLE,
    default_timeout,
    fetch_json,
    long_timeout,
    request,
)

#: 외부 의존이 죽는 방식들. 하나라도 예외로 새면 화면이 500 이 된다.
OUTAGES = [
    ("연결 거부", requests.exceptions.ConnectionError("connection refused")),
    ("응답 없음", requests.exceptions.ReadTimeout("read timed out")),
    ("이름 해석 실패", requests.exceptions.ConnectionError("NameResolutionError")),
    ("HTTP 503", requests.exceptions.HTTPError("503 Server Error")),
    ("JSON 아님", ValueError("Expecting value: line 1 column 1")),
]


class FetchJsonDegradedTest(SimpleTestCase):
    """① 실패가 예외가 아니라 값으로 온다."""

    def test_every_outage_returns_fallback_instead_of_raising(self):
        for label, exc in OUTAGES:
            with self.subTest(outage=label):
                with mock.patch("common.external_http.requests.request", side_effect=exc):
                    data, ok = fetch_json("http://external.invalid/x", default={"items": []})
                self.assertFalse(ok, f"[{label}] 실패를 성공으로 보고했습니다.")
                self.assertEqual({"items": []}, data)

    def test_json_error_response_is_a_failure_not_a_payload(self):
        """HTTP 500 본문을 정상 데이터로 착각하지 않는다."""
        response = mock.Mock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
        with mock.patch("common.external_http.requests.request", return_value=response):
            data, ok = fetch_json("http://external.invalid/x", default=None)
        self.assertFalse(ok)
        self.assertIsNone(data)

    def test_success_returns_payload(self):
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"items": [{"name": "stream/A"}]}
        with mock.patch("common.external_http.requests.request", return_value=response):
            data, ok = fetch_json("http://external.invalid/x", default={})
        self.assertTrue(ok)
        self.assertEqual([{"name": "stream/A"}], data["items"])

    def test_unexpected_error_is_not_swallowed(self):
        """버그를 저하 운전으로 위장하지 않는다 — 알 수 없는 예외는 그대로 올린다."""
        with mock.patch("common.external_http.requests.request",
                        side_effect=KeyError("프로그래밍 오류")):
            with self.assertRaises(KeyError):
                fetch_json("http://external.invalid/x")


class TimeoutIsAlwaysAppliedTest(SimpleTestCase):
    """② 호출부가 잊어도 타임아웃이 들어간다."""

    @override_settings(EXTERNAL_HTTP_TIMEOUT=(1.5, 2.5))
    def test_fetch_json_injects_configured_timeout(self):
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        with mock.patch("common.external_http.requests.request", return_value=response) as m:
            fetch_json("http://external.invalid/x")
        self.assertEqual((1.5, 2.5), m.call_args.kwargs["timeout"])

    @override_settings(EXTERNAL_HTTP_TIMEOUT=(1.5, 2.5))
    def test_request_wrapper_injects_configured_timeout(self):
        with mock.patch("common.external_http.requests.request") as m:
            request("GET", "http://external.invalid/x")
        self.assertEqual((1.5, 2.5), m.call_args.kwargs["timeout"])

    @override_settings(EXTERNAL_HTTP_TIMEOUT=(1.5, 2.5))
    def test_explicit_timeout_wins(self):
        with mock.patch("common.external_http.requests.request") as m:
            request("GET", "http://external.invalid/x", timeout=(9, 9))
        self.assertEqual((9, 9), m.call_args.kwargs["timeout"])

    def test_timeout_values_come_from_settings_not_literals(self):
        """값은 설정 1곳에서 온다 (D-212). 무한(None)이 되는 경로는 없다."""
        for name, fn in (("기본", default_timeout), ("장기", long_timeout)):
            with self.subTest(kind=name):
                value = fn()
                self.assertIsNotNone(value)
                connect, read = value
                self.assertGreater(connect, 0)
                self.assertGreater(read, 0)


class StreamMonitorListDegradesTest(SimpleTestCase):
    """③ 목록 API 의 스트리밍 상태조회가 죽어도 200 이고, 죽었다고 말한다.

    스키마의 `from_queryset` 은 부모(DynamicSchema)와 DB 를 함께 쓰므로 여기서는
    **외부 호출 부분만** 격리해 잰다. 통합 확인은 재현 절차(evidence)가 맡는다.
    """

    def test_list_schema_reports_unavailable_instead_of_raising(self):
        from stream_monitors.schemas import schemas_djantic_out as out

        row = {"id": 1, "code": "A"}
        with mock.patch.object(out, "fetch_json", return_value=({}, False)) as m, \
                mock.patch.object(out.DynamicSchema, "from_queryset", return_value=row):
            # 외부가 죽은 상태에서 호출해도 예외가 나지 않아야 한다.
            try:
                result = out.StreamMonitorOutSchema.from_queryset(object(), many=False)
            except Exception as exc:  # pragma: no cover - 실패 시 메시지를 남긴다
                self.fail(f"외부 의존 실패가 예외로 새어 나왔습니다: {exc!r}")
        self.assertTrue(m.called, "저하 운전 경로(fetch_json)를 타지 않았습니다.")
        self.assertEqual(
            UNAVAILABLE, result.get("stream_status"),
            "외부가 죽었는데 정상으로 표시했습니다 — 사용자가 빈 화면을 정상으로 오해한다.",
        )

    def test_list_schema_reports_available_when_external_is_up(self):
        from stream_monitors.schemas import schemas_djantic_out as out

        row = {"id": 1, "code": "A"}
        with mock.patch.object(out, "fetch_json", return_value=({"items": []}, True)), \
                mock.patch.object(out.DynamicSchema, "from_queryset", return_value=row):
            result = out.StreamMonitorOutSchema.from_queryset(object(), many=False)
        self.assertEqual(AVAILABLE, result.get("stream_status"))

    def test_status_constants_are_distinct(self):
        self.assertNotEqual(AVAILABLE, UNAVAILABLE)

class MinioStorageDegradedTest(SimpleTestCase):
    """저장소(MinIO)도 외부 의존이다 — C-3.3.

    왜 뒤늦게 붙나: W0-17 게이트는 `requests` 만 셌고, **저장소는 그 밖에 있었다.**
    2026-08-27 백필 실행 로그가 그 대가를 보여줬다 — endpoint 가 닿지 않는데
    MinIO 초기화가 `minio.invalid` 를 향해 **5회 재시도**를 두 번 돌았다.
    타임아웃도 재시도 상한도 없어서, 저장소 하나가 안 뜨면 그 뒤 작업이 그만큼 매달린다.

    MinIO SDK 는 호출마다 `timeout=` 을 받지 않는다. **생성자에서 한 번** 정한다 —
    그래서 이 시험이 보는 곳도 호출부가 아니라 생성부다.
    """

    def _pool(self):
        from stream_monitors.utils.minio_client import MinioClient
        return MinioClient._http_client()

    def test_pool_has_connect_and_read_timeout(self):
        pool = self._pool()
        t = pool.connection_pool_kw.get("timeout")
        self.assertIsNotNone(t, "MinIO 연결 풀에 타임아웃이 없습니다 — 매달릴 수 있습니다.")
        self.assertIsNotNone(t.connect_timeout, "연결 타임아웃이 없습니다.")
        self.assertIsNotNone(t.read_timeout, "응답 타임아웃이 없습니다.")

    def test_retries_are_capped(self):
        """재시도 상한이 없으면 타임아웃이 있어도 그 배수만큼 매달린다."""
        pool = self._pool()
        retries = pool.connection_pool_kw.get("retries")
        self.assertIsNotNone(retries, "재시도 상한이 없습니다 — 오늘 5회를 돌았습니다.")
        self.assertLessEqual(
            retries.total, 2,
            "재시도가 많으면 타임아웃을 걸어도 그 배수만큼 매달립니다.",
        )

    @override_settings(MINIO_CONNECT_TIMEOUT=1.5, MINIO_READ_TIMEOUT=4.5,
                       MINIO_MAX_RETRIES=0)
    def test_values_come_from_settings_not_literals(self):
        """값이 코드에 박혀 있으면 운영에서 못 바꾼다 (C-3.4 계열)."""
        pool = self._pool()
        t = pool.connection_pool_kw["timeout"]
        self.assertEqual(1.5, t.connect_timeout)
        self.assertEqual(4.5, t.read_timeout)
        self.assertEqual(0, pool.connection_pool_kw["retries"].total)

    def test_construction_failure_does_not_raise(self):
        """저장소가 죽어도 예외가 올라오지 않는다 — 실패는 값으로 온다 (available=False)."""
        from stream_monitors.utils import minio_client as mc

        with mock.patch.object(mc, "Minio", side_effect=OSError("storage down")):
            try:
                client = mc.MinioClient()
            except Exception as exc:  # pragma: no cover - 실패 시 메시지를 남긴다
                self.fail(f"저장소 장애가 예외로 새어 나왔습니다: {exc!r}")
        self.assertFalse(
            client.available,
            "저장소가 죽었는데 available=True 입니다 — 죽은 것을 성공으로 위장했습니다.",
        )
