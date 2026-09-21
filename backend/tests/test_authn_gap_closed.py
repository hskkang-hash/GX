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

class OurLayerHasNoGatelessRouteTest(TestCase):
    """④ SEC-04 — **우리 층 전체**에 인증 관문 없는 라우트가 0건인가 (2026-09-26 · 차선 S).

    ③(고친 컨트롤러 잠금)과 다른 시험이다. ③은 **이름을 적은 컨트롤러**만 본다 —
    이름을 안 적은 새 컨트롤러가 관문 없이 태어나면 ③은 초록이다.
    이 시험은 **레지스트리 전수**를 훑고 관할로 가른다.

    ★ 「데이터가 안 나왔다」는 「안전하다」가 아니다(지시서 §4-2). 그래서 응답 본문이
      아니라 **관문이 붙어 있는가**를 본다 — 핸들러가 돌았는지 여부가 판정 대상이다.

    ★ 관할 술어는 계측기(`scripts/probe_authn_gap_ownership.py`)와 **같은 한 벌**을
      쓴다(`common.route_ownership`). 두 벌이면 계측기는 0을 내고 시험은 통과하는데
      실제로는 열려 있는 상태가 만들어진다.

    ★ [실측 2026-09-26] 28 → **0**. 저장소 밖 49 · §0.4 금지구역 23 은 우리가 못 고치는
      자리이고 이 시험의 대상이 아니다 — 그 둘을 한 수에 섞은 것이 09-09 의 「55」였다.
    """

    #: ★ 관할 술어는 **재는 층**에 산다(`scripts/route_ownership.py`). 제품 코드가
    #:   부르지 않는 함수를 `backend/` 에 두었더니 잠자는 기능 게이트가 잡았고,
    #:   그 빨강이 옳았다 — 이것은 제품이 하는 일이 아니라 재는 일이다.
    #:   마운트가 여럿이라 경로 후보를 둘 둔다: 컨테이너(`/repo/scripts`)와 체크아웃.
    @staticmethod
    def _load_predicate():
        import sys
        from pathlib import Path

        here = Path(__file__).resolve()
        for cand in ("/repo/scripts", str(here.parent.parent.parent / "scripts")):
            if cand not in sys.path and Path(cand).is_dir():
                sys.path.insert(0, cand)
        import route_ownership          # noqa: PLC0415

        return route_ownership

    #: ★★ **선언된 공개 면.** 관문이 없는 것이 **결정**인 자리는 여기 **이름으로** 적는다
    #:   (D-249 · D-421 이 기존 461건을 잠근 것과 같은 방식 — 수가 아니라 이름이다).
    #:   비어 있지 않은지, 그리고 **아직 실재하는지**를 아래 시험이 따로 누른다 —
    #:   이름만 적고 라우트가 사라지면 그 줄은 **다음 라우트를 덮는 담요**가 된다.
    PUBLIC_BY_DESIGN = {
        ("GET", "/api/dsm/health"):
            "생존 확인 — 로드밸런서·감시기가 자격 없이 부른다. 나가는 것은 검사 이름과 "
            "상태 이름뿐이고(ok/fail) 비밀·호스트명·버전·오류 본문이 없다. "
            "`auth=None` 이 소스에 **명시**돼 있다(apps/dsm/api_u56.py · 턴 T · 차선 U56) — "
            "「안 적었다」와 「공개다」는 다르고, 이 자리는 적은 쪽이다",
    }

    def _gateless_by_owner(self):
        """관문 없는 라우트를 관할로 가른다.

        ★★ [실측 2026-09-21 · 턴 AB · 차선 S] **이 함수가 눈이 멀어 있었다.**

          `inspect.getfile(op.view_func)` 는 **감싼 쪽의 파일**을 준다. ninja-extra 는
          컨트롤러 메서드를 `route_functions.py` 로 감싸고, dj-core 는 `django_ratelimit`
          으로 감싼다 — 둘 다 site-packages 다. 그래서 **관문 없는 73건이 한 건도
          빠짐없이 「저장소 밖」으로 떨어졌고**, 「우리 층 0건」은 잰 0 이 아니라
          **구조적으로 나올 수밖에 없는 0** 이었다. 실측:

              GET /api/dsm/health
                view_func.__module__ = apps.dsm.api_u56      ← 모듈 이름은 맞다
                inspect.getfile      = …/ninja_extra/controllers/route/route_functions.py
                classify_path        = 저장소 밖              ← 여기서 사라졌다
                inspect.unwrap 뒤    = /app/apps/dsm/api_u56.py
                classify_path        = 우리 층                ← 진짜 자리

          `functools.wraps` 는 `__module__` 을 옮겨 주지만 `__code__` 는 안 옮긴다.
          `getfile` 은 `__code__` 를 따라가므로 **이름은 맞고 자리는 틀린** 상태가 된다.
          같은 절을 인벤토리로 센 계측기(`probe_authn_gap_ownership.py`)는 기록된
          `view`·`app` **문자열**을 읽어 처음부터 **1건을 옳게 셌다** — 두 벌이 갈린 자리다.
          그리고 갈린 동안 **시험 쪽이 초록이었다.**

        ⚠ 그래서 `inspect.unwrap` 을 **먼저** 거친다. 그리고 아래 시험이
          「우리 층이 실제로 보이는가」를 **분모로** 따로 누른다 — 안 누르면 이 눈이
          다시 머는 날 아무도 모른다.
        """
        import inspect

        mod = self._load_predicate()
        UNRESOLVED, classify_path = mod.UNRESOLVED, mod.classify_path

        buckets = {}
        seen = 0
        for (method, path), op in _registry_rows().items():
            seen += 1
            if getattr(op, "auth_callbacks", None) or []:
                continue
            view = getattr(op, "view_func", None)
            try:
                #: ★ 감싼 껍질을 벗기고 **진짜 함수의 파일**을 본다.
                where = classify_path(
                    inspect.getfile(inspect.unwrap(view))) if view else UNRESOLVED
            except (TypeError, OSError):
                where = UNRESOLVED
            buckets.setdefault(where, []).append("%s %s" % (method, path))
        return seen, buckets

    def test_the_owner_predicate_can_actually_see_our_layer(self):
        """★★ **분모.** 우리 층이 한 건도 안 보이면 「우리 층 0건」은 잰 0 이 아니다.

        이 시험이 없어서 SEC-04 가 **거짓 초록**이었다. 관문 **있는** 것까지 세어,
        우리 층 라우트가 실제로 관할에 잡히는지를 누른다 — 아래 「0건」의 바닥이다.
        """
        import inspect

        mod = self._load_predicate()
        rows = _registry_rows()
        self.assertGreater(
            len(rows), 100,
            "레지스트리에서 라우트를 %d건밖에 못 봤다 — 열거기 고장이다" % len(rows))
        ours = 0
        for op in rows.values():
            view = getattr(op, "view_func", None)
            if view is None:
                continue
            try:
                where = mod.classify_path(inspect.getfile(inspect.unwrap(view)))
            except (TypeError, OSError):
                continue
            if where == mod.OURS:
                ours += 1
        self.assertGreater(
            ours, 50,
            "관할 술어가 우리 층 라우트를 %d건밖에 못 봤다 — 술어가 눈이 멀었다. "
            "이 수가 낮으면 아래 「우리 층 0건」은 **구조적으로 나오는 0** 이다 "
            "(2026-09-21 실측: unwrap 을 안 거쳐 73건 **전부**가 저장소 밖으로 떨어졌다)"
            % ours)

    def test_the_public_by_design_list_has_not_rotted(self):
        """★ 이름으로 잠근 줄이 **아직 실재하는가.**

        사라진 라우트의 이름이 목록에 남아 있으면, 같은 이름의 **다음 라우트**가
        태어날 때 그 줄이 담요가 된다. 잠근 이름은 실재해야 잠금이다.
        """
        rows = {(m, _normalize(p)) for (m, p) in _registry_rows()}
        self.assertTrue(self.PUBLIC_BY_DESIGN, "선언 목록이 비었다 — 비우려면 사유를 적는다")
        for (method, path), why in self.PUBLIC_BY_DESIGN.items():
            self.assertIn(
                (method, _normalize(path)), rows,
                "선언된 공개 면 «%s %s» 가 레지스트리에 없다 — 사라진 이름은 지운다"
                % (method, path))
            self.assertTrue(why.strip(),
                            "«%s %s» 을 사유 없이 열어 두었다" % (method, path))

    def test_our_layer_is_zero(self):
        """④ SEC-04 — 우리 층에 **선언되지 않은** 관문 없는 라우트가 0건인가.

        ⚠ [실측 2026-09-21 · 턴 AB] 이 수는 **0 이 아니었다.** 눈을 고치자 **1건**이
          드러났고, 그 1건이 `GET /api/dsm/health` 다 — 관문이 없는 것이 **결정**인
          자리(`auth=None` 명시)여서 위 `PUBLIC_BY_DESIGN` 에 **이름으로** 옮겨 적었다.
          「관문을 붙였다」가 아니라 **「선언되지 않은 채 열려 있던 것을 선언했다」**이다.
          두 문장은 다르고, 섞으면 그것이 거짓 초록이다.
        """
        OURS = self._load_predicate().OURS

        seen, buckets = self._gateless_by_owner()
        # 0건 검사와 검사 못함을 가른다 (D-301).
        self.assertGreater(seen, 100,
                           "레지스트리에서 라우트를 %d건밖에 못 봤다 — 열거기 고장이다" % seen)
        declared = {"%s %s" % (m, p) for (m, p) in self.PUBLIC_BY_DESIGN}
        ours = sorted(x for x in buckets.get(OURS, []) if x not in declared)
        self.assertEqual(
            ours, [],
            "★ 우리 층에 **선언되지 않은** 관문 없는 라우트가 %d건 있다 — SEC-04 의 표적이다.\n"
            "  관문을 붙이거나, 공개가 결정이면 `PUBLIC_BY_DESIGN` 에 **사유와 함께** 적는다:\n  %s"
            % (len(ours), "\n  ".join(ours)))

    def test_the_unresolved_bucket_is_not_silently_counted_as_safe(self):
        """★ **못 본 것을 0으로 세지 않는다** (D-301).

        모듈을 못 여는 라우트가 생기면 그것은 「안전하다」가 아니라 「모른다」다.
        모르는 자리가 늘면 이 시험이 그 수를 말한다 — 조용히 우리 층에서 빠지지 않게.
        """
        UNRESOLVED = self._load_predicate().UNRESOLVED

        _seen, buckets = self._gateless_by_owner()
        unresolved = sorted(buckets.get(UNRESOLVED, []))
        self.assertEqual(
            unresolved, [],
            "★ 관할을 못 가른 관문 없는 라우트가 %d건이다 — 0건이 아니라 **못 본 것**이다:\n  %s"
            % (len(unresolved), "\n  ".join(unresolved)))
