# -*- coding: utf-8 -*-
"""사고 ③ — **인증 관문이 아예 없던 자리**를 못박는다 (D-342 · D-343 ①).

캐시 처리: 우회 — `X-No-Cache` (D-341 착시 ⑦). 관문을 재는 시험이 캐시를 재면 안 된다.

무엇이 있었나 [실측 2026-09-08]
-------------------------------
라우트 인벤토리 전수(663건)에서 **우리 층의 인증 콜백 없는 자리 79건**이 나왔다.
D-334 가 잡은 15자리는 「주석 처리된 권한 + `auth=` 없음」이었고, 이 79건은 그보다 넓다 —
**권한 데코레이터가 애초에 없던 자리**까지 포함한다. 읽어서는 위험을 알 수 없어 때렸다(D-210).

GET 51자리를 익명으로, 캐시를 우회해 호출한 결과:

    authz_blocked      20   `@path_permission` 이 익명을 떨어뜨렸다 (인증은 없었다 — D-342)
    reached_no_data    20   핸들러에 닿았고 404·422·500·301 로 끝났다 (막힌 것이 아니다)
    REACHED_WITH_DATA  11   ★ **익명에게 데이터가 나갔다**

그중 둘이 컸다:

    /api/delivery/drone-monitoring/drone-status        17,416 B  드론 텔레메트리 전량
    /api/dronehw/group-management/groups-with-drones   16,089 B  그룹·드론 일련번호

★ 그리고 **11 중 2 는 이 파일에 없다.** `backend/delivery/` 는 §0.4 금지구역이다(D-207).
  한 번 붙였다가 forbidden-zone 게이트가 STOP 으로 잡아 되돌렸다 — **게이트가 옳다**(D-327).
  그 2자리는 잠금 대장에 있다: DA-05/blockers.yaml :: DELIVERY_ZONE_ANON_LEAK

★ 측정기가 먼저 틀렸다 (D-284 · D-341 의 사촌)
    첫 판정에서 18건을 「데이터 반출」로 셌다. 그 18건의 HTTP 상태는 200 이었지만 본문이
    `{"success": false, "status_code": 403}` 였다 — **봉투는 200, 내용은 403.**
    판정기가 봉투만 읽었다. 내용을 읽게 고친 뒤에야 진짜 11건이 드러났다.

무엇을 했나
-----------
**익명에게 데이터를 돌려준 것이 확인된 컨트롤러** 중 **우리가 고칠 수 있는 9개**의,
인증 콜백 없는 라우트 **24자리 전부**에 `JwtOrInboundKey()` 를 붙였다. 목록만 막지 않고 컨트롤러 단위로 닫은 이유는
D-342 다 — `{id}` 자리가 404 를 낸 것은 **막힌 것이 아니라 그 id 가 없었을 뿐**이다.

`JwtOrInboundKey()` 를 쓴 이유(기본값 거절 · D-335 · D-343): 익명을 막으면서 **들어오는 키도
함께 좁힌다.** `CustomJWTAuth()` 를 붙였으면 익명은 막히고 발급된 아무 키나 닿았을 것이다.

이 파일이 못박는 것 셋
----------------------
  1) 24자리에 **인증 관문이 붙어 있다** — 레지스트리에서 확인한다
  2) 그 자리의 GET 이 익명에게 **401** 이다 — 호출로 확인한다
  3) 익명에게 데이터를 내던 9자리가 **본문까지** 막혔다 — 봉투가 아니라 내용을 본다

절대 금지 (AGENT_LOOP 절대금지 #4·#5 · D-105 · D-224)
    skip·xfail·비활성화하지 말 것.
"""
from __future__ import annotations

import json

from django.test import Client, TestCase

from tests.no_cache import NO_CACHE

#: ★ **출생 표본** — 2026-09-08 익명에게 데이터가 나간 11자리 중 **우리가 닫은 9자리.**
#: 나머지 2자리는 §0.4 금지구역이라 못 닫았다 — DELIVERY_ZONE_ANON_LEAK 로 등재돼 있다.
LEAKED_TO_ANONYMOUS = [
    "/api/devices/battery-types",
    "/api/devices/gnss-systems",
    "/api/devices/image-stabilizations",
    "/api/devices/imus",
    "/api/devices/motor-types",
    "/api/devices/protocols",
    "/api/dronehw/group-management/groups-with-drones",
    "/api/print-format/print-formats/print-formats",
    "/api/surveillance/video-analysis",
]

#: 그 9자리가 속한 컨트롤러의 **관문 없던 라우트 전부** — 24자리. `(메서드, 경로)`.
#: 쓰기 메서드가 여기 있다는 것이 이 사고의 다른 얼굴이다: 익명 POST·PUT·DELETE 가 열려 있었다.
FORMERLY_GATELESS = [
    ("GET", "/api/devices/battery-types"),
    ("GET", "/api/devices/battery-types/{id}"),
    ("GET", "/api/devices/gnss-systems"),
    ("GET", "/api/devices/gnss-systems/{id}"),
    ("GET", "/api/devices/image-stabilizations"),
    ("GET", "/api/devices/image-stabilizations/{id}"),
    ("GET", "/api/devices/imus"),
    ("GET", "/api/devices/imus/{id}"),
    ("GET", "/api/devices/motor-types"),
    ("GET", "/api/devices/motor-types/{id}"),
    ("GET", "/api/devices/protocols"),
    ("GET", "/api/devices/protocols/{id}"),
    ("GET", "/api/dronehw/group-management/groups-with-drones"),
    ("GET", "/api/dronehw/group-management/group/{group_id}/drones"),
    ("GET", "/api/print-format/print-formats/print-formats"),
    ("GET", "/api/print-format/print-formats/print-formats/fields/model"),
    ("GET", "/api/print-format/print-formats/print-formats/{print_format_id}/preview"),
    ("POST", "/api/print-format/print-formats/print-formats/{print_format_id}/print"),
    ("GET", "/api/print-format/print-formats/{print_format_id}"),
    ("POST", "/api/print-format/print-formats"),
    ("PUT", "/api/print-format/print-formats/{print_format_id}"),
    ("DELETE", "/api/print-format/print-formats/{print_format_id}"),
    ("GET", "/api/surveillance/video-analysis"),
    ("GET", "/api/surveillance/video-analysis/{video_analysis_id}/download-detail"),
]

#: ★ **음성 대조** (D-289). 전부 401 이면 그것은 「막았다」일 수도 「이 환경에서 아무것도
#: 안 뜬다」일 수도 있다. 둘을 가르려면 **열려 있어야 정상인 자리**가 401 이 아니어야 한다.
CONTROL_OPEN = "/api/v1/health"


def _concrete(path: str) -> str:
    out = []
    for part in path.split("/"):
        out.append("1" if part.startswith("{") and part.endswith("}") else part)
    return "/".join(out)


def _registry_rows():
    """ninja 레지스트리를 읽는다 — 정적 grep 이 아니다(동적 등록을 놓치지 않기 위해)."""
    from common.tenant_scope import _iter_ninja_apis, _join

    rows = {}
    for mount, api in _iter_ninja_apis():
        for prefix, router in getattr(api, "_routers", []) or []:
            for op_path, path_view in (getattr(router, "path_operations", {}) or {}).items():
                for op in getattr(path_view, "operations", []) or []:
                    path = _join(mount, prefix, op_path)
                    for method in [str(m).upper() for m in (getattr(op, "methods", []) or [])]:
                        rows[(method, path)] = op
    return rows


def _normalize(path: str) -> str:
    """`{int:event_id}` 와 `{event_id}` 를 같은 것으로 본다 — 표기는 문제가 아니다."""
    out = []
    for part in path.split("/"):
        if part.startswith("{") and part.endswith("}"):
            out.append("{}")
        else:
            out.append(part)
    return "/".join(out)


class FormerlyGatelessRoutesHaveAuthTest(TestCase):
    """① 24자리에 인증 관문이 실제로 붙어 있는가 — 레지스트리에서 확인한다."""

    def test_all_have_auth_callback(self):
        rows = {(m, _normalize(p)): op for (m, p), op in _registry_rows().items()}
        unfound, missing = [], []
        for method, path in FORMERLY_GATELESS:
            op = rows.get((method, _normalize(path)))
            if op is None:
                unfound.append("%s %s" % (method, path))
                continue
            if not (getattr(op, "auth_callbacks", None) or []):
                missing.append("%s %s" % (method, path))

        self.assertEqual(
            unfound, [],
            "라우트가 사라졌거나 경로가 바뀌었다 — 목록을 실측으로 갱신하라:\n  "
            + "\n  ".join(unfound),
        )
        self.assertEqual(
            missing, [],
            "★ 인증 관문이 다시 없어졌다. 익명이 핸들러에 닿는다:\n  " + "\n  ".join(missing),
        )

    def test_inbound_key_is_refused_by_default(self):
        """붙인 것이 `JwtOrInboundKey` 인가 — 들어오는 키까지 좁혔는가 (D-343).

        `CustomJWTAuth` 를 붙였다면 익명은 막히고 **발급된 아무 키나 닿는다.**
        「막았다」와 「좁혔다」는 다른 일이다.
        """
        from common.inbound_api_key import JwtOrInboundKey

        rows = {(m, _normalize(p)): op for (m, p), op in _registry_rows().items()}
        wrong = []
        for method, path in FORMERLY_GATELESS:
            op = rows.get((method, _normalize(path)))
            callbacks = getattr(op, "auth_callbacks", None) or [] if op else []
            gate = next((c for c in callbacks if isinstance(c, JwtOrInboundKey)), None)
            if gate is None:
                wrong.append("%s %s — JwtOrInboundKey 가 아니다" % (method, path))
            elif gate.inbound_key:
                wrong.append("%s %s — 들어오는 키를 받겠다고 선언했다 (사유 없이 넓힌 것이다)"
                             % (method, path))
        self.assertEqual(wrong, [], "\n  ".join([""] + wrong))


class FormerlyGatelessRoutesRejectAnonymousTest(TestCase):
    """② 익명 요청이 401 을 받는가 — **호출로** 확인한다 (D-210).

    GET 만 때린다. 쓰기 메서드는 부작용이 있어 부르지 않고, ①의 레지스트리 단언이 지킨다.
    """

    def setUp(self):
        # 캐시 처리: 우회 — 관문을 재는 시험이 캐시를 재면 안 된다 (D-341).
        self.client = Client(raise_request_exception=False, **NO_CACHE)

    def test_anonymous_get_is_rejected(self):
        wrong = []
        for method, path in FORMERLY_GATELESS:
            if method != "GET":
                continue
            resp = self.client.get(_concrete(path))
            if resp.status_code != 401:
                wrong.append("%s -> %s (401 이어야 한다)" % (path, resp.status_code))
        self.assertEqual(
            wrong, [], "★ 익명 요청이 인증 관문을 지났다:\n  " + "\n  ".join(wrong))

    def test_leaked_routes_no_longer_return_data(self):
        """★ 데이터를 내던 9자리 — **봉투가 아니라 내용을 본다** (D-284).

        이 저장소의 200 은 200 이 아닐 수 있다. 처음 측정에서 판정기가 바로 그것에 속았다.
        """
        self.assertEqual(len(LEAKED_TO_ANONYMOUS), 9, "사고 규모를 바꾸려면 사유와 함께 바꿔라")
        wrong = []
        for path in LEAKED_TO_ANONYMOUS:
            resp = self.client.get(_concrete(path))
            if resp.status_code != 401:
                wrong.append("%s -> HTTP %s" % (path, resp.status_code))
                continue
            body = resp.content or b""
            if not body:
                continue
            try:
                data = json.loads(body.decode("utf-8", "replace"))
            except ValueError:
                continue
            if isinstance(data, dict) and data.get("success") is True:
                wrong.append("%s -> 401 인데 본문이 success=true 다" % path)
        self.assertEqual(
            wrong, [], "★ 익명에게 다시 데이터가 나간다:\n  " + "\n  ".join(wrong))


class NoNewGatelessRouteInFixedControllersTest(TestCase):
    """③ 부작위 (D-300) — 고친 컨트롤러에 **관문 없는 라우트가 다시 생기지 않는다.**

    한 자리를 막고 옆자리를 열면 사고는 그대로다. 컨트롤러 단위로 잠근다.
    """

    #: ①에서 닫은 라우트가 사는 컨트롤러들 (§0.4 의 delivery 둘은 여기 없다).
    FIXED_CONTROLLERS = (
        "devices.views.battery_type_views.BatteryTypeAPI",
        "devices.views.gnss_system_views.GNSSSystemAPI",
        "devices.views.image_stabilization_views.ImageStabilizationAPI",
        "devices.views.imu_views.IMUAPI",
        "devices.views.motor_type_views.MotorTypeAPI",
        "devices.views.protocol_views.ProtocolAPI",
        "drone_communication.views.group_views.GroupAPI",
        "print_format.views.PrintFormatController",
        "surveillance.views.surveillance_profile_view.VideoAnalysisController",
    )

    def test_no_route_without_auth_in_fixed_controllers(self):
        naked = []
        seen = 0
        for (method, path), op in _registry_rows().items():
            view = getattr(op, "view_func", None)
            name = "%s.%s" % (getattr(view, "__module__", "?"),
                              getattr(view, "__qualname__", "?"))
            controller = name.rsplit(".", 1)[0]
            if controller not in self.FIXED_CONTROLLERS:
                continue
            seen += 1
            if not (getattr(op, "auth_callbacks", None) or []):
                naked.append("%s %s" % (method, path))
        # 0건 검사와 검사 못함을 가른다 (D-301).
        self.assertGreater(seen, 0, "고친 컨트롤러를 하나도 못 찾았다 — 열거기 고장이다")
        self.assertEqual(
            naked, [],
            "★ 고친 컨트롤러에 관문 없는 라우트가 다시 생겼다:\n  " + "\n  ".join(naked))
