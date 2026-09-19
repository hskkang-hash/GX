# -*- coding: utf-8 -*-
"""전역 접근 관문 — **우리 층에서 길목을 막는다** (D-348 · D-343 ③).

왜 미들웨어인가 — §0.4 가 금지한 것은 「파일 수정」이지 「길목 차단」이 아니다
------------------------------------------------------------------------------
사고 ③에서 익명에게 데이터를 돌려주던 11자리 중 **2자리를 못 닫았다.**
`backend/delivery/views/api.py` 가 §0.4 금지구역이라 라우트 선언에 손을 댈 수 없었고,
forbidden-zone 게이트가 STOP 으로 잡았다. **게이트는 제 일을 했다** — 파일을 고치려 했으니까.

    [판정 D-348] D-207 이 금지한 것은 **그 파일을 수정하는 것**이다.
    그 경로로 가는 요청을 **우리 층에서 막는 것**은 금지된 적이 없다.
    바꿀 것은 게이트가 아니라 **막는 자리**다.

이 미들웨어는 우리 코드다. dj-core 도, `backend/delivery/` 도 **한 줄도 건드리지 않는다.**

무엇을 하나 — 규칙 둘
---------------------
  ① **들어오는 키 기본값 거절** (D-343 ③) — inbound 키를 들고 온 요청은
     `INBOUND_KEY_ALLOWED` 에 이름이 오른 자리에만 닿는다. 나머지는 401.
     ★ 라우트 선언의 `JwtOrInboundKey` 와 **같은 규칙을 한 겹 밖에서** 건다.
       선언은 우리가 고칠 수 있는 라우트만 덮고, 이 미들웨어는 **전부**를 덮는다 —
       §0.4 경로를 포함해서.
  ② **익명 거절** (D-348) — `AUTHN_REQUIRED_PATHS` 에 오른 경로는 자격증명 없는
     요청을 401 로 끊는다. 인증 관문이 라우트에 없어도 여기서 끊긴다.
     ★ [P-83 · 2026-09-06] 이 규칙이 `AUTHN_SURFACE` 면제보다 **앞**에 선다.
       넓은 면제(「인증 면은 비켜 준다」) 아래에 좁은 사고
       (`/api/v1/auth/reset-password-for-user` — 익명이 남의 비밀번호를 바꾼다)가
       숨어 있었다. **손으로 이름을 적은 것이 규칙보다 세다.**

★ 자리 — **캐시보다 바깥이어야 한다** (D-341 착시 ⑦)
----------------------------------------------------
`UniversalCacheMiddleware` 는 캐시 적중 시 뷰를 부르지 않고 저장된 본문을 200 으로 돌려준다.
이 관문을 캐시 **안쪽**에 두면, 열려 있던 동안 익명 키로 채워진 항목이 관문을 지나지 않고
그대로 나간다 — 2026-09-07 에 실제로 있었던 일이다(2자리가 고친 뒤에도 200).
그래서 `MIDDLEWARE` 에서 `UniversalCacheMiddleware` **위**에 둔다.
`common.api_contract.ApiContractStatusMiddleware` 가 같은 이유로 그 자리에 있다.

★ 응답은 **HTTP 상태로 말한다** (D-349 착시 ⑧)
----------------------------------------------
거절을 HTTP 200 봉투 안에 담지 않는다. 401 은 401 로 나간다.
「봉투는 200, 내용은 403」이 이 저장소가 방금 겪은 착시이고, 그 면을 우리가 새로 만들지 않는다.

되돌림
------
`settings.MIDDLEWARE` 에서 이 한 줄을 지우면 종전 동작이다. 데이터도 스키마도 건드리지 않는다.
"""
from __future__ import annotations

import logging
import re

from django.http import JsonResponse

from common.inbound_api_key import carries_inbound_key

logger = logging.getLogger(__name__)

#: ★ **들어오는 키가 닿아도 되는 자리 — 전부.** 이 집합이 곧 개방 선언이다(D-343 ②).
#: 늘리는 일은 손으로 이 줄을 더하는 일이고, 그 손이 「진입면을 넓힌다」는 선언이다.
#: `scripts/verify_route_inventory.py` 가 이 집합과 라우트 대장의
#: `inbound_key_allowed` 가 **같은지** 검사한다 — 갈리면 exit 1.
INBOUND_KEY_ALLOWED: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/dsm/events"),
    # ★ [턴 W · 차선 U3 · 조율자 요청] **이 한 줄이 「진입면을 넓힌다」는 선언이다.**
    #   손으로 더했고, 그래서 보고에 크게 적는다. 라우트 쪽 선언
    #   (`apps/dsm/api.py::camera_pulse` 의 `inbound_key=True`)과 **짝**이다 —
    #   한쪽만 고치면 `test_allowlist_matches_the_route_ledger` 가 빨개진다.
    #   그 두 손을 요구하는 설계가 옳다: 미들웨어만 열면 라우트가 막고,
    #   라우트만 열면 미들웨어가 막는다. 여는 사람이 **둘 다** 만져야 한다.
    #
    #   사유: `pulse:read` 범위가 `kernels/k5_trust/key_scopes.py` 에 이미 있고
    #   `PATH_SCOPES` 가 이 경로를 가리키는데, 선언이 없어 **범위 판정에 닿기도
    #   전에 401** 이었다 — 줄 수는 있는데 쓸 데가 없는 범위였다.
    #   ⚠ 여는 것이 넓히는 것이 아니다: `DEFAULT_SCOPES = ("events:read",)` 이므로
    #     **이미 나간 키는 그대로 403** 이다. 늘어나는 것은 운영자가 `pulse:read` 를
    #     일부러 준 키 하나뿐이고, `@tenant_scoped` 는 그대로다.
    ("GET", "/api/dsm/cameras/pulse"),
})

#: ★ **익명이 닿으면 안 되는 경로.** 라우트에 인증 관문이 없어도 여기서 끊는다.
#:
#: 지금 오른 넷은 §0.4(`backend/delivery/`)라 라우트 선언을 고칠 수 없는 자리다.
#: [실측 2026-09-08] 앞의 둘에서 익명에게 데이터가 나갔다:
#:     GET  /api/delivery/drone-monitoring/drone-status   17,416 B  드론 텔레메트리
#:     GET  /api/delivery/etri-mock/test-scenarios         1,976 B  시험 시나리오
#: 뒤의 둘은 같은 컨트롤러의 쓰기 면이다 — 한 자리를 막고 옆자리를 열면 사고는 그대로다.
#:
#: ★ 2026-09-10 넷이 더 올랐다 (D-364) — **측정기가 안 보여 주던 자리다.**
#: [실측] `probe_gap_route_settlement.py` 가 리다이렉트를 **따라가자** 드러났다:
#:     GET /api/orders/banks             200 · 87 B   익명 도달
#:     GET /api/orders/delivery-option   200 · 96 B   익명 도달
#:     GET /api/orders/payment-methods   200 · 97 B   익명 도달
#:     GET /api/orders/item-types        500          익명 도달(핸들러가 터졌다)
#: 직전 측정에서 이 넷은 **301** 로 찍혀 「본문 없음」 칸에 들어갔다. 301 은 관문의 답이
#: 아니라 `APPEND_SLASH` 의 답이었고, 따라가지 않았기 때문에 **관문이 있는 것처럼 보였다**
#: (D-350 — 측정기를 먼저 의심한다. 이번이 두 번째 적용이다).
#:
#: ★ 지금 `data: []` 가 나온다고 안전한 것이 아니다 — 그 표가 이 환경에서 비어 있을 뿐이다.
#:   행이 있는 환경에서는 같은 호출이 목록을 통째로 내놓는다 (D-301 「검사 못함 ≠ 0건」).
#: ★ `item-types` 는 터지므로 데이터가 안 나가지만 **함께 올린다.** 한 자리를 막고
#:   옆자리를 열면 사고는 그대로이고, 터지던 것이 고쳐지는 날 그 자리가 열린 채로 남는다.
#: `backend/orders/` 는 §0.4 다 — 라우트를 고치지 않고 **우리 층에서 막는다**(D-357).
#: ★ 2026-09-06 하나가 더 올랐다 (차선 V) — **터지는 바람에 안 보이던 자리다.**
#: [실측 2026-09-06] `probe_authn_gap_calls.py` 가 이 자리를 `reached_no_data`(422)로 냈다.
#: 422 는 **관문의 답이 아니라 스키마 검증의 답**이다 — 프로브가 필수 질의값을 안 줘서
#: 났을 뿐이고, 익명은 이미 라우팅과 검증을 지나 **핸들러까지 닿아 있었다.**
#: 값을 채워 다시 익명으로 불렀다:
#:     GET /api/delivery/processing/get-drones-by-package-and-route-optimized
#:         ?package_id=1&route_id=1   → **422** ·
#:         본문: "type object 'ProcessingRepository' has no attribute
#:                get_drones_by_operation_and_route_optimized"
#: 즉 **데이터가 안 나가는 이유가 관문이 아니라 저장소 메서드가 없는 것**이다.
#: 이 라우트는 `auth=` 도 `@path_permission` 도 없고(둘 다 없는 자리), 그 오타가
#: 고쳐지는 날 익명에게 드론 목록(unit_id · 배터리 · 적재량 · 터미널명 · ETA)이 나간다.
#: 위 `item-types` 와 **같은 사유로 같이 올린다** — 「터지니까 안전하다」는 관문이 아니다.
#: `backend/delivery/` 는 §0.4 라 라우트 선언을 못 고친다 — 우리 층에서 막는다(D-348 · D-357).
AUTHN_REQUIRED_PATHS: tuple[str, ...] = (
    "/api/delivery/drone-monitoring/drone-status",
    "/api/delivery/processing/get-drones-by-package-and-route-optimized",
    "/api/delivery/etri-mock/test-scenarios",
    "/api/delivery/etri-mock/receive-delivery",
    "/api/orders/banks",
    "/api/orders/delivery-option",
    "/api/orders/payment-methods",
    "/api/orders/item-types",
    # ★★ 2026-09-06 턴 I · 차선 S — **다섯이 더 올랐다. 이번엔 읽기가 아니라 쓰기다** (P-83)
    #
    # 어떻게 드러났나: `probe_write_surface.py` 가 턴 H 까지 **빈 본문 `{}`** 하나만
    # 던지고 「도달 못 하면 관문이 섰다」로 셌다. 그 17자리 중 13자리의 실제 답은
    # **422 — 스키마 검증 실패**였다. 422 는 「인증 없이도 여기까지 왔다」는 뜻이지
    # 관문이 아니다. 스키마를 통과하는 최소 본문을 만들어 다시 던지자 다섯 자리에서
    # 익명이 **핸들러까지 닿았다**(D-334 대체물 · 본체는 한 줄도 안 돌았다):
    #
    #   POST /api/v1/auth/reset-password-for-user  ★★ 본문 {id, new_password} 만으로
    #        **아무 사용자의 비밀번호를 바꾼다.** 핸들러에 권한 검사가 **한 줄도 없다**
    #        (dj-core `core/api/v1/auth.py:2286` — 데코레이터도 없다). 계정 탈취다
    #   POST /api/v1/user/create-user             ★ 문서엔 "Requires admin privileges",
    #        코드엔 그 검사가 없다. `@ratelimit`·`@csrf_protect` 뿐이다
    #   POST /api/v1/auth/register                ★ 익명이 계정을 만든다. 이 제품은
    #        관리자가 계정을 내주는 B2B 운영 도구다 — 자가 가입 면이 아니다
    #   POST /api/source/save-html                ★ 익명이 템플릿 디렉터리에 파일을 쓰고
    #        `os.remove()` 로 기존 파일을 지운다
    #   PUT  /api/advanced-table/column-order     핸들러 안에 `check_permission` 이
    #        있지만 그 판정은 **핸들러 안**이고, 결과를 200 봉투에 담는다(D-349 착시 ⑧).
    #        관문은 봉투 밖에 있어야 한다 — 닫힌 쪽을 택한다
    #
    # ★ 다섯 다 **dj-core**(`/usr/local/.../core/`) 안이다 — §0.4 금지구역이라
    #   라우트 선언을 못 고친다. D-348 그대로 **우리 층에서 길목을 막는다.**
    #   `@csrf_protect` 가 붙은 자리도 함께 올린다: CSRF 는 남의 사이트가 시키는
    #   요청을 막는 장치이지 **직접 때리는 익명**을 막는 장치가 아니다. 스크립트는
    #   쿠키를 먼저 받아 오면 그만이다 — 관문으로 세지 않는다.
    "/api/v1/auth/reset-password-for-user",
    "/api/v1/auth/register",
    "/api/v1/user/create-user",
    "/api/source/save-html",
    "/api/advanced-table/column-order",
    # ★★ 2026-09-07 턴 J · 차선 S — **하나가 더 올랐다. 이번엔 정적 판정이 틀렸다** (D-368 ③)
    #
    #   POST /api/delivery/etri-integration/receive-from-etri
    #
    # 이 자리는 세 턴 동안 `read_only_in_practice`(도달은 하되 **안 쓴다**) 칸에
    # 앉아 있었다. 그 판정의 근거는 `writes_by: "[정적] 핸들러 본문에 쓰기 호출 없음"`
    # 이었고, 그 술어는 **핸들러 본문 한 겹만** 본다. 한 겹 더 따라가면 이렇다:
    #
    #   delivery/views/api.py:1623   DeliverySystem.receive_status_from_etri(etri_data, request)
    #     → delivery/services/etri_service.py:368  EtriService.receive_status_from_etri
    #       → :417  _update_delivery_status(...)
    #           delivery_operation.order.status = OrderStatus.objects.get(code='cancelled')
    #           delivery_operation.order.save()          ← 남의 주문을 **취소한다**
    #           delivery_operation.save()
    #           OrderService.create_order_history(...)   ← 이력까지 쓴다
    #
    # **익명이 `RECEIPT_ID` 하나만 알면 남의 배송을 취소·완료 처리할 수 있다.**
    #
    # 전/후 [실측 2026-09-07 · 인증 없음 · 없는 id `999999999` · 행 53,411 · 모델 117]:
    #   전  HTTP **400** `{"message": "Delivery operation with ID 999999999 not found"}`
    #       ← 핸들러가 **실제로 돌았다**(조회까지 갔다). 행수·최신수정시각 변화 0
    #       ⚠ 「행이 안 늘었다」는 「안 쓴다」가 아니다 — **없는 id 라서** 못 쓴 것이다.
    #         실재 id 로는 두드리지 않는다(그것이 곧 사고다). 그래서 「쓴다」의 근거는
    #         호출 그래프이고, 「이 입력으로는 안 썼다」의 근거는 위 실측이다. 둘을 섞지 않는다
    #   후  HTTP **401** (자격증명 없음)
    #
    # 왜 이 목록인가: `backend/delivery/` 는 §0.4 라 `@route.post("/receive-from-etri")`
    # 에 `auth=` 를 붙일 수 없다. D-348 이 만든 자리가 정확히 이것이다.
    # 옆자리 점검 [실측 · 인벤토리 전수]: `/api/delivery/etri-*` 12자리 중 익명인 것은
    # 이것과 mock 둘뿐이고 **mock 둘은 이미 이 목록에 있다**. 즉 진짜 입구만 열려 있었다.
    #
    # ⚠ 되돌리기: 이 한 줄을 뺀다. 되돌릴 조건 — ETRI 가 **자격증명을 하나도 안 싣고**
    #   호출하는 것이 계약으로 확인되면. 그때도 완전 개방이 아니라 `INBOUND_KEY_ALLOWED`
    #   에 (POST, 이 경로)를 올리는 쪽이 옳다. 이 관문은 자격증명의 **있음**만 보므로
    #   (`_has_credentials`), ETRI 가 `Authorization` 이나 `X-API-Key` 를 아무거나 실으면
    #   지금도 그대로 지나간다 — 막히는 것은 **아무것도 안 싣고 오는 요청**뿐이다.
    # ★ 세종 미판정 · 기본값(닫힌 쪽·되돌릴 수 있는 쪽) 택함.
    "/api/delivery/etri-integration/receive-from-etri",
    # ★★ 2026-09-10 턴 O · 차선 S — **하나가 더 올랐다. 익명이 남의 2FA 를 끈다** (P-113)
    #
    #   POST /api/v1/auth/otp/reset   본문 {"username": "..."} 하나
    #
    # dj-core `core/api/v1/auth.py:1990 reset_otp` 에 권한 검사가 **한 줄도 없다.**
    # 핸들러는 `pyotp.random_base32()` 로 비밀키를 새로 심고
    # `opt_mandatory=False` · `otp_is_verified=False` 로 **2단계 인증을 꺼 버린다.**
    #
    # 전/후 [실측 2026-09-10 · TARGET=8500 · 인증 없음 · 없는 이름 `gx_nonexistent_probe_zzz`]:
    #   전  HTTP **404** {"success":false,...,"ko":"사용자를 찾을 수 없습니다"}
    #       <- 핸들러가 **실제로 돌았다**(조회까지 갔다). 404 는 관문의 답이 아니다(P-83).
    #       ⚠ 실재 사용자명으로는 **일부러 두드리지 않았다** — 그 한 번이 곧 사고다.
    #   후  HTTP **401** (자격증명 없음)
    #
    # ★ `AUTHN_SURFACE`(인증 면 면제)가 이 자리를 덮고 있었다 —
    #   `reset-password-for-user` 와 **정확히 같은 모양의 사고**다(P-83).
    #   그래서 **같은 자리에 이름을 적는다.** 이름이 규칙보다 세다.
    # ★ 익명 401 은 이 한 줄이 낸다. 「본인 재인증 · 관리자+감사」 규칙은
    #   `common/otp_reset_guard.py` 가 낸다 — 아래 `__call__` 에서 부른다.
    # ⚠ 되돌리기: 이 한 줄을 뺀다(익명 개방으로 되돌아간다).
    "/api/v1/auth/otp/reset",
    # ★★ 2026-09-11 턴 P · 차선 S — **다섯이 더 올랐다. 익명이 자료를 200 으로 받던 자리 전부**(P-133)
    #
    # 어떻게 재나: `scripts/probe_anon_read.py` (이번에 만든 익명 전용 탐침 —
    # 로그인하지 않는다). 라우터 전수 **읽기 331자리**를 자격증명 없이 불렀고,
    # 빨강 술어(`probe_read_surface.has_data`: 2xx · 거부 봉투 아님 · 봉투를 걷어내고도
    # 남는 것이 있음)로 센 결과 [실측 2026-09-11]:
    #
    #     GET /api/v1/auth/timezones                 200 · 109,309 B · 598덩이
    #     GET /api/config-management/list-optimized  200 ·  16,436 B ·  12덩이
    #     GET /api/v1/auth/groups                    200 ·   1,685 B ·  10덩이
    #     GET /api/v1/auth/languages                 200 ·     466 B ·   3덩이
    #     GET /api/register-settings                 200 ·     182 B ·   1덩이
    #
    # ★ 다섯 다 **dj-core**(`/usr/local/lib/python3.11/site-packages/core/`) 안이다 —
    #   `core.api.v1.auth.get_timezones` · `get_groups` · `get_languages` ·
    #   `core.configuration.api.list_configs_optimized` · `core.user.api.get_register_settings`.
    #   §0.4 금지구역(읽기전용)이라 라우트 선언에 `auth=` 를 못 붙인다.
    #   D-348 그대로 **길목을 우리 층에서 막는다.**
    #
    # ★ 앞의 셋이 `AUTHN_SURFACE`(인증 면 면제) 아래 숨어 있었다 —
    #   `reset-password-for-user`(P-83) · `otp/reset`(P-113) 과 **정확히 같은 모양**이다.
    #   이름을 적은 자리가 규칙보다 세다 — 그래서 같은 자리에 이름을 적는다.
    #
    # ★ 공개가 설계인가 — **아니다. 부르는 쪽이 없다** [실측 2026-09-11]
    #   `frontend/src` 전수 검색: 다섯 경로 중 어느 것도 **한 번도 불리지 않는다**
    #   (히트 0). 로그인 화면이 로그인 전에 부르는 자리는 `/api/v1/auth/login`
    #   하나다 (`frontend/src/features/login/loginRequest.ts:22` · `LOGIN_PATH`).
    #   언어 목록은 프런트 정적 자원(`src/i18n`)이 낸다 — 이 문이 아니다.
    #   그래서 **허용 목록으로 좁히지 않고 닫는다**(`PUBLIC_READ_BY_DESIGN` 판단 기준:
    #   「아직 로그인하지 못한 사람이 부르는 자리인가」 — 다섯 다 아니다).
    #   → 109KB 타임존 목록을 「우리 층 정적 목록(1KB)」으로 갈음하는 안은
    #     **필요 없다** — 갈음할 수요 자체가 없다. 수요가 생기는 날
    #     (예: 자가가입 화면이 생긴다) 그때 그 목록을 만들어 여는 쪽이 옳다.
    #   `/api/register-settings` 는 `{"is_allow_register": false}` 하나를 낸다 —
    #   자가가입이 꺼져 있다는 관리 설정이고, 그 설정이 가리키는
    #   `/api/v1/auth/register` 는 **이미 이 목록에 있다**(P-83). 한 자리를 막고
    #   그 자리를 설명하는 옆자리를 열어 두면 사고는 그대로다.
    #
    # ⚠ 되돌리기: 해당 줄을 뺀다. 인증된 사용자는 이 줄들과 무관하다 —
    #   이 관문은 `_has_credentials` 가 거짓일 때만 말한다(사용자 회귀 0의 근거).
    "/api/v1/auth/timezones",
    "/api/v1/auth/groups",
    "/api/v1/auth/languages",
    # "/api/config-management/list-optimized" — ★ D-461: 닫지 않고 **좁혔다**.
    #   로그인 화면(rj-core)이 로그인 전에 부른다. 아래 `ANON_PUBLIC_PROJECTIONS` 참조.
    "/api/register-settings",
    # ★ 같은 실측이 **옆자리 셋**을 함께 냈다 — 「비었으니 안전하다」가 아니다 (D-301)
    #
    # [실측 2026-09-11 · 익명 · 캐시 우회 없음]
    #     GET /api/v1/auth/departments  200 · 87 B · {"data": []}
    #     GET /api/v1/auth/positions    200 · 85 B · {"data": []}
    #     GET /api/v1/auth/teams        200 · 81 B · {"data": []}
    #
    # 빨강 술어는 이 셋을 **회색**으로 놓는다 — 봉투를 걷어내니 비었기 때문이다.
    # 그러나 비어 있는 이유는 관문이 아니라 **이 환경의 그 표에 행이 없어서**다.
    # 바로 옆의 `/api/v1/auth/groups` 가 증거다: 같은 컨트롤러 · 같은 모양인데
    # 행이 10개 있어서 **빨강**이었다. 행이 있는 환경에서는 이 셋도 똑같이 나간다
    # (부서·직위·팀 이름은 조직도다 — 테넌트 자료다).
    #
    # 「검사 못함 ≠ 0건 검사」(D-301) + 「한 자리를 막고 옆자리를 열면 사고는 그대로다」.
    # 모르는 쪽은 **닫힌 쪽**으로 기운다 (D-284).
    # 부르는 쪽 점검 [실측]: `frontend/src` 전수 검색 히트 **0**. 로그인 전에 부르는
    # 자리가 아니다. 인증 사용자는 그대로다 — 이 관문은 자격증명이 **없을 때만** 말한다.
    "/api/v1/auth/departments",
    "/api/v1/auth/positions",
    "/api/v1/auth/teams",
)

#: ★★ **경로 틀(`{id}`)로 선언된 자리는 이름으로 못 막는다** — 2026-09-06 턴 I · P-83
#:
#: 위 `AUTHN_REQUIRED_PATHS` 는 **정확히 같은 글자**만 막는다. 그런데 실측으로 드러난
#: 무관문 쓰기 자리 중 셋은 경로에 파라미터가 있다:
#:
#:     POST /api/apikey/keys/{api_key_id}/regenerate          익명이 남의 키를 재발급
#:     POST /api/apikey/keys/{user_id}                        익명이 **남의 이름으로 키를 만든다**
#:     POST /api/third-api/api-key-management/keys/{user_id}  같은 컨트롤러의 다른 입구
#:
#: [실측 2026-09-06 · `probe_write_surface.py`] 익명이 이 자리들의 핸들러에 닿았고
#: 그 핸들러는 `APIKey.create_key(...)` · `deactivate(...)` 를 부른다. **API 키를
#: 익명이 만들 수 있으면 그 뒤의 모든 관문은 의미가 없다** — 키가 곧 자격증명이다.
#:
#: 그래서 **접두**로 막는다. 이 두 접두 아래는 전부 API 키 관리 면이고, 아직 로그인하지
#: 못한 사람이 부를 자리가 하나도 없다 (`PUBLIC_BY_DESIGN` 판단 기준 그대로).
#: 한 자리를 막고 옆자리를 열면 사고는 그대로다 — 그래서 읽기 면까지 함께 덮는다.
AUTHN_REQUIRED_PREFIXES: tuple[str, ...] = (
    "/api/apikey/",                      # inbound 키 발급 면 — 남이 우리를 부를 때 쓸 키다
    "/api/third-api/api-key-management/",  # 같은 inbound 계열
)

#: 이 관문이 보는 면. API 밖(관리자·정적·문서)은 종전대로 둔다 — 넓히면 로그인 화면까지 막는다.
#: ★★ [D-461 · 2026-09-15 턴 P] **닫은 문 하나가 로그인 화면의 부제목을 지웠다 — 막지 않고 좁힌다.**
#:   P-133 이 익명에게 닫은 `/api/config-management/list-optimized`(16,436 B)를 로그인 화면이
#:   **로그인 전에** 부른다. 부르는 쪽은 `frontend/src` 가 아니라 §0.4 `rj-core` 다
#:   (`rj-core.umd.js` · `fetchDataDev` → `configManagementDev` · `?name=<묶음>`) — 그래서 P-133 의
#:   `frontend/src` 전수 검색에 안 잡혔다. 닫은 뒤 로그인 화면은 `System.subtitle`
#:   (「AI기반 드론.로봇 통합 운영 서비스」)을 잃었고, 콘솔에 401 + 「Token refresh failed」 두 줄을
#:   남겨 배치의 걷기 게이트가 **배치를 되돌렸다** [실측 2026-09-15 · walk_20260915_142614].
#:   원 응답의 `System` 묶음은 `cidr`·`security`·`otp`·`validation`·`domain` 을 함께 싣는다 —
#:   다시 여는 것은 답이 아니다. 로그인 컴포넌트가 로그인 전에 읽는 **두 칸만** 우리 층에서
#:   **새로 만들어** 낸다. 원 응답을 거르지 않는 이유: 거르면 거름망의 구멍이 곧 누출이다.
#:   만들면 여기 적지 않은 것은 나갈 수 없다(거부 기본값 · D-284).
#:   rj-core 는 `data` 를 `name → settings` 로 접는다(`bM`) — 그래서 칸은 이 둘로 충분하다.
#:   ⚠ 되돌리기: 이 항목을 지우고 경로를 `AUTHN_REQUIRED_PATHS` 로 되돌린다(로그인 부제목이 다시 빈다).
ANON_PUBLIC_PROJECTIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "/api/config-management/list-optimized": {
        "System": ("subtitle",),                       # 로그인 화면 부제목
        "system_register": ("is_allow_register",),     # 「회원가입」 링크를 그릴지
    },
}
#: 투영 응답의 크기 상한 — 넘으면 **닫는다**(투영이 자라는 것은 누출이 자라는 것이다).
ANON_PROJECTION_MAX_BYTES = 1024


API_PREFIX = "/api/"

#: 인증 면 자체. 여기까지 막으면 **아무도 키를 받을 수 없다** — 관문이 문을 잠그고 열쇠를 삼킨다.
AUTHN_SURFACE = re.compile(r"^/api/(v1/)?(auth|token|login|logout|refresh|register)(/|$)")


def _has_credentials(request) -> bool:
    """자격증명을 **들고 왔는가**. 유효한지는 보지 않는다 — 그건 인증의 일이다.

    ★ 여기서 유효성까지 보면 이 미들웨어가 **두 번째 인증기**가 된다.
      인증기가 둘이면 언젠가 갈리고, 갈리면 어느 쪽이 맞는지 아무도 모른다(D-337 계열).
      이 관문이 답하는 질문은 하나다: **아무것도 없이 들어왔는가.**
    """
    if request.headers.get("Authorization") or carries_inbound_key(request):
        return True
    user = getattr(request, "user", None)
    return bool(user is not None and getattr(user, "is_authenticated", False))


def _denied(reason: str) -> JsonResponse:
    """거절은 **401 로** 나간다 — 200 봉투에 담지 않는다 (D-349).

    사유에 키·토큰·경로 파라미터를 넣지 않는다(D-335 규약 ④).
    """
    return JsonResponse({"detail": "Unauthorized", "reason": reason}, status=401)


def _normalize(path: str) -> str:
    return path.rstrip("/") or "/"


class AccessGateMiddleware:
    """규칙 둘을 한 자리에서 건다. **기본값은 거절이다.**"""

    def __init__(self, get_response):
        self.get_response = get_response
        self._allowed = {(m.upper(), _normalize(p)) for m, p in INBOUND_KEY_ALLOWED}
        self._authn_required = tuple(_normalize(p) for p in AUTHN_REQUIRED_PATHS)
        #: 접두는 끝에 `/` 를 붙여 둔다 — 안 붙이면 `/api/apikeys-public` 처럼
        #: **이름이 겹치는 남의 자리**까지 함께 막힌다.
        self._authn_prefixes = tuple(
            p if p.endswith("/") else p + "/" for p in AUTHN_REQUIRED_PREFIXES)

    def __call__(self, request):
        # ★ D-461 — 자격증명이 없는 GET 이 공개 투영 자리를 부르면, 뒷단에 닿기 전에 여기서 답한다.
        if not _has_credentials(request):
            projected = self._anon_projection(request)
            if projected is not None:
                return projected

        verdict = self.judge(
            method=request.method,
            path=request.path,
            has_inbound_key=carries_inbound_key(request),
            has_credentials=_has_credentials(request),
        )
        if verdict is not None:
            return _denied(verdict)

        # ★★ [P-113 · 2026-09-10 턴 O] **2FA 초기화는 재인증을 요구한다.**
        #   위 규칙은 「아무것도 안 들고 왔는가」만 본다(이 관문의 본래 질문).
        #   그러나 이 한 자리는 그것으로 부족하다 — 로그인만 했으면 남의 2FA 를
        #   끌 수 있어서는 안 된다. 판정식은 `otp_reset_guard` 한 곳에 둔다(D-212).
        #   같은 길목에서 부르되 **이 파일에 판정을 복사하지 않는다.**
        rejection = self._otp_reset_rejection(request)
        if rejection is not None:
            return rejection

        return self.get_response(request)

    # ── D-461 — 공개 투영. 원 응답을 거르지 않고 **허용한 칸만 새로 만든다** ──────
    @staticmethod
    def _anon_projection(request):
        """익명 GET 이 `ANON_PUBLIC_PROJECTIONS` 의 자리를 부르면 공개 칸만 담은 응답. 아니면 `None`."""
        if request.method != "GET":
            return None
        spec = ANON_PUBLIC_PROJECTIONS.get(_normalize(request.path))
        if spec is None:
            return None
        from core.configuration.models import AdminConfig   # dj-core — 읽기만 (§0.4)

        wanted = (request.GET.get("name") or "").strip()
        names = [n for n in spec if not wanted or wanted == n]
        rows = []
        #: `is_sensitive` 로 표시된 묶음은 이름이 허용 목록에 있어도 **내지 않는다**(닫힌 쪽).
        #: `is_active` 로는 거르지 않는다 — 원 뷰가 거르지 않았다. 이 환경의 `system_register` 는
        #: `is_active=False` 인데 원 응답 16,436 B 의 `data[6]` 에 들어 있었고 로그인 화면은 그 값을
        #: 읽어 왔다 [실측 2026-09-15]. 여기서 거르면 운영자가 가입을 켜도 로그인 화면만 모른다.
        for cfg in AdminConfig.objects.filter(name__in=names, is_sensitive=False):
            src = cfg.settings or {}
            rows.append({"name": cfg.name,
                         "settings": {k: src[k] for k in spec.get(cfg.name, ()) if k in src}})
        resp = JsonResponse({"success": True, "status": 200, "count": len(rows), "data": rows})
        if len(resp.content) > ANON_PROJECTION_MAX_BYTES:
            logger.warning("[ACCESS-GATE] 공개 투영이 %d바이트 — 상한 %d 를 넘어 닫는다: %s",
                           len(resp.content), ANON_PROJECTION_MAX_BYTES, request.path)
            return _denied("authentication required")
        resp["X-GX-Public-Projection"] = "login-config"
        resp["Cache-Control"] = "no-store"
        return resp

    # ── P-113 — 한 자리짜리 재인증 규칙. 길목은 여기, 판정은 저기 ────────────
    @staticmethod
    def _otp_reset_rejection(request):
        """`POST /api/v1/auth/otp/reset` 에만 걸리는 규칙. 그 밖에는 `None`."""
        from common import otp_reset_guard as guard

        if not guard.enabled():
            return None
        if not guard.is_guarded(method=request.method, path=request.path):
            return None

        user = getattr(request, "user", None)
        body = guard.read_body(request)
        outcome = guard.judge(user=user, body=body)
        if outcome is None:
            return None

        status, reason, needs_audit = outcome
        target = str((body or {}).get("username") or "")

        if status is None and needs_audit:
            # 관리자가 **남의 계정**을 초기화한다 — 감사 한 줄이 조건이다(규칙 ④).
            try:
                guard.write_audit(actor=user, target=target, allowed=True,
                                  reason=reason, status=200)
            except Exception:                             # noqa: BLE001
                logger.exception("[P-113] 감사에 남기지 못했다 — 통과시키지 않는다")
                return JsonResponse(
                    {"detail": "Forbidden", "reason": guard.REASON_AUDIT_FAILED},
                    status=403)
            return None

        if status == 403:
            return JsonResponse({"detail": "Forbidden", "reason": reason}, status=403)
        return _denied(reason)

    # ── 술어 — 요청 객체 없이 시험할 수 있게 순수 함수로 둔다 ──────────────────
    def _is_authn_required(self, path: str) -> bool:
        """이 경로가 **익명 거절 자리**인가 — 이름으로든, 접두로든.

        ★ 두 목록을 여기 한 곳에서 합친다(D-212). `judge()` 안에 흩으면 한쪽만
          고쳐지는 날이 오고, 그날 「목록에는 있는데 안 막히는」 자리가 생긴다.
        """
        norm = _normalize(path)
        return norm in self._authn_required or (norm + "/").startswith(self._authn_prefixes)

    def judge(self, *, method: str, path: str, has_inbound_key: bool,
              has_credentials: bool) -> str | None:
        """거절 사유를 돌려준다. 통과면 None.

        ★ 순서가 규칙이다. 인증 면을 **먼저** 비켜 준다 — 그러지 않으면
          키를 발급받는 길까지 막혀 아무도 이 시스템에 들어올 수 없다.
        """
        if not path.startswith(API_PREFIX):
            return None

        # ★★ [P-83 · 2026-09-06 턴 I] **이름을 적은 자리는 규칙보다 세다.**
        #
        #   `AUTHN_SURFACE` 는 「로그인·토큰 면은 비켜 준다」는 **넓은 규칙**이고,
        #   그 규칙 아래에 `/api/v1/auth/reset-password-for-user` 가 숨어 있었다 —
        #   익명이 `{id, new_password}` 만 보내면 아무 계정의 비밀번호가 바뀐다.
        #   넓은 면제가 좁은 사고를 덮은 모양이다.
        #
        #   그래서 **손으로 이름을 적은 경로**는 인증 면 안에 있어도 막는다.
        #   순서가 곧 규칙이다: 이름이 먼저, 규칙이 나중.
        #   (규칙을 좁히지 않고 예외를 앞에 두는 이유 — `AUTHN_SURFACE` 를 손보면
        #    로그인 길이 함께 흔들린다. 흔들리면 아무도 못 들어온다.)
        if not has_credentials and self._is_authn_required(path):
            return "authentication required"

        if AUTHN_SURFACE.match(path):
            return None

        key = (method.upper(), _normalize(path))

        # ① 들어오는 키 기본값 거절 (D-343 ③) — 선언한 자리에만 닿는다.
        if has_inbound_key and key not in self._allowed:
            return "inbound key is not allowed on this route"

        # ② 익명 거절 (D-348) — 라우트에 관문이 없어도 여기서 끊는다.
        #   ★ 판정은 **위로 올라갔다**(P-83). 여기 한 벌 더 두면 판정식 복사본이
        #     둘이 되고, 갈린 복사본 하나가 D-212 였다. 그래서 부르지 않고 가리킨다.

        return None
