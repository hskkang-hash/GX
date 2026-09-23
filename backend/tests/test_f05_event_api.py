# -*- coding: utf-8 -*-
"""F-05 — **외부 App 이 이벤트 OpenAPI 하나로만 들어오는가** (D-309 미측정 해소).

계약 AC 원문: *"외부 App 이 이벤트 OpenAPI **하나로만** 들어온다 (API Key 발급·폐기 포함)"*

이 파일이 왜 생겼나 — **D-309 대장의 유일한 '미측정' 이었다**
--------------------------------------------------------------
F-05 는 구현 여부와 무관하게 **재는 시험이 없었다.** 대장은 그것을 '부분' 이 아니라
'미측정' 으로 적게 했고(증명 없는 칸은 '구현' 으로 못 적는다), 그 한 칸이 이번 관문이 됐다.

무엇을 재는가 — 셋
------------------
  ① **진입면이 하나인가**   L4 App 중 K1 커널을 소비하는 것은 `apps.dsm` **하나뿐**이고,
                            그 App 의 HTTP 진입면은 등재된 10개뿐이다.
  ② **그 진입면이 잠겨 있는가**  전건 인증 + 테넌트 스코프.
  ③ **모양이 안정적인가**   응답 키 집합을 이름으로 고정한다(D-285 ②).

  ★ ①이 **부작위 시험**이다(D-300) — "만든 것" 이 아니라 **"다른 데로 못 들어옴"** 을 잰다.
    AC 의 핵심 단어가 "하나로만" 이므로, 이 AC 는 부작위로만 정확히 잴 수 있다.

무엇을 **못** 재는가 — 정직하게 남긴다
--------------------------------------
**API Key 발급·폐기(FR-05-3)는 저장처가 없다.** 그래서 못 잰다. 다만 그 부재는 조용하지
않다 — `apps.dsm.services.SETTING_DOMAINS['api_keys']` 가 사유와 함께 501 로 나가고,
`test_dsm_app.py::test_unavailable_domains_raise_instead_of_returning_empty` 가 그 갈래를
잰다. 아래 `test_api_key_issuance_is_declared_not_silently_missing` 가 그 선언이 살아
있는지 확인한다 — **없는 것을 없다고 말하는 상태**를 지키는 것이 지금 할 수 있는 전부다.

★ 술어를 먼저 밝힌다 (D-271 ③) — 그리고 **첫 술어는 틀렸다**
------------------------------------------------------------
"이벤트에 닿는 라우트" 를 처음에는 **핸들러 모듈의 소스 + 그 모듈이 끌어들인 우리 모듈**
(2단계 import 폐포)로 셌다. 결과는 662 중 **98건** — `delivery.views.api` 와
`stream_monitors.views.*` 가 전부 잡혔다. 그것들은 이벤트를 만지지 않고, 다만
`stream_monitors.models` 를 끌어들일 뿐이다. **전이 import 근접성은 도달이 아니다.**

빨간불의 뜻이 둘이 되면 그 게이트는 곧 꺼진다(D-295 가 게이트 둘을 나눈 이유).
그래서 술어를 **직접 import** 로 좁혔다: `kernels.k1_event` 를 import 하는 모듈.
실측 결과 라우트를 가진 51개 모듈 중 **0개**이고, K1 소비자는 8개뿐이다(아래 등재).
"""
from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

from django.test import SimpleTestCase

BACKEND = Path(__file__).resolve().parents[1]
_SKIP_DIRS = {"__pycache__", "migrations", ".venv", "node_modules", "venv"}

# ═══════════════════════════════════════════════════════════════════════════
# 등재부 — **이름으로 잠근다** (D-285 ②). 수가 아니라 이름이다.
# ═══════════════════════════════════════════════════════════════════════════
#: F-05 가 말하는 **그 하나의 진입면.** 재난안전 App 의 HTTP 표면 전부다.
#: 여기 없는 라우트가 `/api/dsm/` 아래 생기면 이 시험이 멈춘다 — 진입면이 둘이 되는
#: 순간을 사람이 아니라 도구가 본다.
EVENT_ENTRY_SURFACE: frozenset[tuple[str, str]] = frozenset({
    ("GET", "/api/dsm/dashboard/frame"),
    ("GET", "/api/dsm/dashboard/link-state"),
    ("GET", "/api/dsm/deliveries"),
    ("GET", "/api/dsm/events"),
    ("GET", "/api/dsm/events/{int:event_id}/clip"),
    ("GET", "/api/dsm/events/{int:event_id}/clip/stream"),
    ("POST", "/api/dsm/events/{int:event_id}/notify"),
    # ★ 2026-09-04 **둘이 늘었다** — 현장 회신(U3 #9 · 차선 D 커널 + 조율자 배선).
    #   문지기: `@tenant_scoped`(쓰기·읽기 IDOR) + `JwtOrInboundKey`.
    #   ⚠ 회신은 **계정이 남긴다** — 무계정 링크 금지의 집행은 커널의 요청자 검사에도 있다.
    #   여는 이유: `dormant` 게이트가 「켜진 상태로 태어나야 한다」로 잡았기 때문이다.
    ("POST", "/api/dsm/events/{int:event_id}/field-reply"),
    ("GET", "/api/dsm/events/{int:event_id}/field-replies"),
    ("GET", "/api/dsm/reports/templates"),
    ("GET", "/api/dsm/reports/{int:template_id}.pdf"),
    # ★ 2026-09-05 **여덟이 늘었다** — 법·인증 면 (LAW-02a · LAW-06 · LAW-07 · 차선 L).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이다. 이 시험이
    #   그 선언을 강제했다 — 여덟이 조용히 늘 뻔했다.
    #
    #   ★ 이 여덟은 **다른 컨트롤러**(`apps/dsm/law_api.py`)에 산다. 같은 턴에 두 차선이
    #     한 라우트 파일을 고치면 충돌하고, 충돌한 라우트는 **라우팅 침묵**이 된다.
    #     컨트롤러가 둘이어도 **진입면은 하나다** — 같은 `NinjaExtraAPI` 에 등록되고
    #     같은 `/api/dsm/` 아래에 서며 여기 한 표에 함께 잠긴다.
    #
    #   문지기: 전건 @tenant_scoped + JwtOrInboundKey.
    #   ★ 청구 넷은 **관리자만**이다(403) — 응답에 청구인의 이름이 실린다.
    #   ★ `POST /law/retention/sweep` 은 **되돌릴 수 없는 쓰기**다:
    #     `dry_run` 기본값이 참이고, 거짓으로 부르는 것은 **전역 관리자**만 할 수 있으며
    #     사유가 없으면 422 다. 지금 이 집행은 테넌트별로 나뉘지 않기 때문이다.
    ("GET", "/api/dsm/law/ai-act/duties"),                          # LAW-06 자리표
    ("GET", "/api/dsm/law/retention"),                              # LAW-02a 보관 기간
    ("POST", "/api/dsm/law/retention/sweep"),                       # LAW-02a 집행
    ("GET", "/api/dsm/law/privacy-requests"),                       # LAW-07 목록
    ("POST", "/api/dsm/law/privacy-requests"),                      # LAW-07 접수
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}"),          # LAW-07 상세
    ("GET", "/api/dsm/law/privacy-requests/{receipt_no}/masked"),   # LAW-07 마스킹본
    ("POST", "/api/dsm/law/privacy-requests/{receipt_no}/reply"),   # LAW-07 회신 기록
    ("GET", "/api/dsm/settings/{domain}"),
    # ★ 2026-09-19 **둘이 늘었다 — 그런데 진입면은 넓어지지 않았다** (D-410).
    #   `GET /settings/{domain}` 이 `domain=thresholds` · `domain=zones` 로 이미
    #   서 주던 **바로 그 문**이다: 같은 핸들러(`_setting_overview`) · 같은 문지기
    #   (@tenant_scoped + JwtOrInboundKey + guard_setting) · 같은 응답.
    #   바뀐 것은 **어느 URL 패턴이 그 문을 여는가** 뿐이다.
    #
    #   왜 다시 걸었나: 이 둘은 **설정 영역 이름이면서 동시에 쓰기 경로**다.
    #   `settings/<str:domain>` 이 먼저 등록돼 있는 한 `POST /settings/thresholds`
    #   는 405 였다(Allow: GET). 리터럴을 앞으로 옮기면 이번엔 GET 이 405 가 된다 —
    #   한 경로 = 한 PathView 이므로, **GET 과 POST 를 같은 문에 함께 세우는 것**이
    #   둘 다 사는 유일한 배선이다.
    #
    #   ⚠ 이 두 줄을 지우면 시험이 멈춘다. 멈추면 지우지 말고 **왜 문이 사라졌는지**
    #     를 보라 — 십중팔구 `{domain}` 이 다시 위로 올라간 것이다.
    ("GET", "/api/dsm/settings/thresholds"),
    ("GET", "/api/dsm/settings/zones"),
    # ★ 2026-09-06 추가 (D-325 표 ① · F-02 「지점별 기준선 설정」 · F-12 「임계값」).
    #   진입면이 **하나 늘었다** — 그리고 그것이 이 시험의 값이다: 사람이 아니라 도구가
    #   그 사실을 여기서 멈춰 세웠다. 늘리는 판단은 손으로 이 줄을 더하는 일이고,
    #   그 손이 곧 "진입면을 늘린다"는 선언이다.
    #   문지기: @tenant_scoped + CustomJWTAuth + guard_setting(F-12 감사 전건).
    ("POST", "/api/dsm/settings/thresholds"),
    # ★ 2026-09-10 **다섯이 늘었다** — 계약 절 셋을 갚으면서 (D-365~368).
    #   손으로 이 줄들을 더하는 일이 곧 "진입면을 넓힌다" 는 선언이다.
    #   이 시험이 아니었으면 다섯이 조용히 늘었을 것이고, F-05 의
    #   「이벤트 OpenAPI 하나로만 들어온다」가 소리 없이 약해졌을 것이다.
    #
    #   문지기: 전건 @tenant_scoped + JwtOrInboundKey(키 거절 · 기본값) +
    #           guard_setting(F-12 감사 — 성공·실패 모두)
    #   ★ 다섯 다 **들어오는 키를 받지 않는다.** 특히 api-keys 셋이 그렇다 —
    #     키로 키를 발급받을 수 있으면 키 하나가 영원히 자기를 갱신하고,
    #     그러면 폐기가 폐기가 아니게 된다.
    ("POST", "/api/dsm/settings/zones"),          # F-12 「구역」 (D-366)
    ("POST", "/api/dsm/settings/grade-rules"),    # F-12 「등급규칙」 (D-368)
    ("POST", "/api/dsm/settings/api-keys"),       # F-05 「발급」 (D-367)
    ("DELETE", "/api/dsm/settings/api-keys/{int:key_id}"),         # F-05 「폐기」
    ("POST", "/api/dsm/settings/api-keys/{int:key_id}/rotate"),    # F-05 「회전」
    # ★ 2026-09-14 **하나가 늘었다** — 대응 진행 축(D-399). 손으로 이 줄을 더하는 일이
    #   곧 「진입면을 넓힌다」는 선언이다. 이 시험이 그 선언을 강제했다.
    #   문지기: @tenant_scoped(쓰기 IDOR) + JwtOrInboundKey.
    #   ★ 이 라우트는 **거절을 4xx 로 낸다** — 409(그 전이는 없다) · 400(사유를 채워라) ·
    #     403(팀장이 해야 한다). 셋을 한 코드로 묶지 않는다(D-290).
    ("POST", "/api/dsm/events/{int:event_id}/response"),
    # ★ 2026-09-11 **하나가 늘었다** — 이벤트 상세 화면(D-371 ①)이 부를 자리.
    #   이 시험이 먼저 멈춰 세웠다. 게이트가 지시보다 위다(D-327) — 손으로 이 줄을
    #   더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #
    #   왜 목록에서 골라내지 않고 라우트를 늘렸나: 화면이 목록 응답에서 한 줄을
    #   골라 상세로 쓰면 **문지기가 목록에만 서고 상세에는 안 선다.** 그 자리가
    #   IDOR 이 태어나는 자리다. 상세는 서버에 다시 묻는다.
    #   문지기: @tenant_scoped + JwtOrInboundKey(**키 거절** — 상세는 목록에 없는
    #           clip_path·address·reviewed_by_id 를 더 낸다. 계약이 F-05 로 연 것은
    #           이벤트 조회이지 그 셋이 아니다)
    ("GET", "/api/dsm/events/{int:event_id}"),    # F-09 이벤트 상세 (D-371)
    # ★ 2026-09-20 **하나가 늘었다** — 판정(오탐) 라우트 (P-16 · 오탐 ②).
    #   `review_event` 는 2026-08 부터 **서비스로는 있었고 문이 없었다.** 화면의 「오탐」
    #   버튼이 부를 자리가 없어 U1 의 오탐률은 시드로만 채워졌다 — 착시 ⑨(함수는 문이
    #   아니다)의 세 번째 실사례다. 손으로 이 줄을 더하는 일이 곧 「진입면을 넓힌다」는
    #   선언이고, 그 선언을 여기 남긴다.
    #   문지기: @tenant_scoped(쓰기 IDOR) + JwtOrInboundKey.
    #   ★ 거절을 4xx 로 **나눈다** (D-290): 422(판정값이 아니다) · 404(없는 이벤트 ·
    #     남의 이벤트) · 403(시스템 스코프 — 판정은 사람이 하는 일이다 · D-281).
    ("POST", "/api/dsm/events/{int:event_id}/review"),
    # ★ 2026-09-23 **하나가 늘었다** — W1 요약 한 줄 (차선 C · 온보딩 U2 #1
    #   「밤사이 요약 보기」). 손으로 이 줄을 더하는 일이 곧 「진입면을 넓힌다」는
    #   선언이고, 그 선언을 여기 남긴다. 이 시험이 먼저 멈춰 세웠다 —
    #   21 vs 22 로 빨개졌고, 게이트가 지시보다 위다(D-327).
    #
    #   왜 목록 라우트로 세지 않고 라우트를 늘렸나: 요약은 **집계**다. 화면이
    #   `/events` 를 받아 자기가 세면 상한 밖의 이벤트가 안 세어지고, 「미처리 3건」이
    #   실은 「상한 안의 3건」이 된다 — 그리고 그 사실이 화면에 안 나온다.
    #   오탐률은 K6 `false_positive_rate` 만 낸다(집계 경로 하나 · DA-04 K6).
    #
    #   문지기: @tenant_scoped(남의 테넌트 오탐률·미처리 수가 섞이면 격리 실패) +
    #           JwtOrInboundKey(**키 거절 — 기본값**).
    #   ⚠ **읽기 전용이다.** 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #   ⚠ 등록 자리가 `/events/{int:event_id}` **위**여야 한다. 지금은 `int` 변환기라
    #     삼키지 않지만, 변환기가 `{str:...}` 로 바뀌는 날 조용히 404 가 된다 —
    #     조용한 404 는 「기능이 없다」와 구별되지 않는다(D-410 이 남긴 자리).
    ("GET", "/api/dsm/events/summary"),
    # ★ 2026-09-24 **하나가 늘었다** — 스냅샷 바이트 (P-25 · 조율자).
    #   손으로 이 줄을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 시험이 먼저 멈춰 세웠다(22 vs 23) — 게이트가 지시보다 위다(D-327).
    #
    #   왜 라우트를 냈나: 화면은 스냅샷을 **이미 그리고 있었고** 바이트를 줄 문이 없었다.
    #   그 자리를 서명 URL(무계정 링크)로 메우지 않았다 — 계정 없이 열리는 링크는
    #   한 번 새면 회수할 수 없다(불변 제약). 문은 **하나**이고 인증 뒤에 선다.
    #
    #   ⚠ **읽기 전용이다.** 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #   문지기: @tenant_scoped(남의 이벤트 프레임이 나가면 격리 실패) +
    #           JwtOrInboundKey(**키 거절 — 기본값**. 계약이 F-05 로 연 것은 이벤트
    #           조회이지 프레임 바이트가 아니다).
    #   ★ 나가는 바이트에는 **소인**이 있다(테넌트명·열람 시각). 저장은 못 막지만
    #     출처는 남는다 — `backend/tests/test_snapshot_route.py` 규약 넷이 잰다.
    ("GET", "/api/dsm/events/{int:event_id}/snapshot"),
    # ★ 2026-09-16 **아홉이 늘었다** — 턴 S 파 2 「짓기」 (차선 U1·U24·U56).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 시험이 먼저 멈춰 세웠다(68 대 84) — **게이트가 지시보다 위다**(D-327).
    #
    #   ★ **수를 손으로 세지 않았다.** 차선 셋이 보고한 수가 서로 달랐고(16 · 4 · 선언 21줄),
    #     살아 있는 라우터와 이 명부를 대조하는 이 시험이 **이름으로 16건**을 뱉었다.
    #     그중 아홉이 여기 있다 — 나머지 일곱(웹푸시 구독 다섯 · 내 알림 설정 둘)은
    #     차선 U3 가 **아직 `api.py` 를 고치는 중**이라 등재하지 않았다. 안 굳은 주소를
    #     조율자가 먼저 박으면 그것은 등재가 아니라 추측이다(P-90 에서 배운 것과 같은 말:
    #     대상 없는 승인을 받은 쪽이 대상을 추정하면 그 순간 승인받지 않은 행위다).
    #
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey()` 기본값(**들어오는 키 거절**).
    ("GET",  "/api/dsm/queue/field-signals"),        # U1 · 큐 「지원 요청」 배지
    # ★ U24 넷 — 통계·시뮬. **쓰기는 하나뿐**이고 그것도 아무것도 저장하지 않는다:
    #   `thresholds/simulate` 는 「이 문턱이면 시간당 N건」을 세어 답할 뿐이다(POST 인 것은
    #   인자가 본문에 실리기 때문이지 쓰기여서가 아니다). 그래서 WRITE_PROBES 대상이 아니다.
    ("POST", "/api/dsm/stats/thresholds/simulate"),  # U24 · 임계 시뮬 (저장 0)
    ("GET",  "/api/dsm/stats/false-positive/by-camera"),  # U24 · 오탐률 상위 카메라
    ("GET",  "/api/dsm/stats/camera-thresholds"),    # U24 · 카메라별 문턱 목록
    ("GET",  "/api/dsm/stats/camera-threshold"),     # U24 · 한 대의 문턱
    # ★ U56 넷 — 알림 규칙(등급 × 역할 × 채널)과 「내 정보」.
    #   ⚠ `notify-rules/save` 는 **심각 등급에 받는 사람 0 을 거부한다**(409). 그 거부가
    #     이 면의 요점이다 — 저장은 됐는데 아무도 안 받는 규칙은 「설정했다」는 착각만 남긴다.
    #   ⚠ `notify-rules/test` 는 **훈련 채널로만** 나간다(채널 인자가 없다). 시험 발송이
    #     실제 수신함에 닿을 수 있으면 그것은 시험이 아니라 발송이다.
    ("GET",  "/api/dsm/settings/notify-rules/list"),  # U56 · S-16 규칙 목록
    ("POST", "/api/dsm/settings/notify-rules/save"),  # U56 · S-16 저장 ★쓰기 (409 · 수신자 0 거부)
    ("POST", "/api/dsm/settings/notify-rules/test"),  # U56 · S-16 시험 발송 (훈련 채널 전용)
    ("GET",  "/api/dsm/me"),                          # U56 · S-15 내 정보 (읽기 전용)
    # ★ 2026-09-16 **일곱이 더 늘었다** — 같은 턴 차선 U3(웹푸시 구독 · 내 알림 설정).
    #   위 아홉과 **커밋이 갈라지지 않도록** 같은 표에 함께 적는다. 앞서 아홉만 적은 것은
    #   그때 U3 가 아직 `api.py` 를 고치는 중이어서다 — **안 굳은 주소를 조율자가 먼저
    #   박으면 그것은 등재가 아니라 추측이다.** 차선이 자기 경로를 글자 그대로 보고한
    #   뒤에 적는다(그 목록과 이 줄들을 대조했다).
    #
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey()` 기본값(**들어오는 키 거절**).
    #   ⚠ `push-subscriptions` 는 **기기를 등록하는 면**이다. 키로 기기를 등록할 수 있으면
    #     키 하나가 「남의 휴대전화를 울리는 관」이 된다 — api-keys 셋에 키를 안 연 것과
    #     같은 이유다.
    #   ⚠ `me/notify-prefs` 는 **자기 것만** 만진다. 남의 것을 가리킬 인자가 시그니처에
    #     없다(D-281 「시그니처가 1차」).
    ("GET",    "/api/dsm/push-subscriptions/vapid-key"),                # U3 · 공개키 상태
    ("POST",   "/api/dsm/push-subscriptions/test-send"),                # U3 · 내 기기로 한 통 ★쓰기
    ("POST",   "/api/dsm/push-subscriptions"),                          # U3 · 기기 등록 ★쓰기
    ("GET",    "/api/dsm/push-subscriptions"),                          # U3 · 내 기기 목록
    ("DELETE", "/api/dsm/push-subscriptions/{int:subscription_id}"),    # U3 · 해지 ★쓰기
    ("GET",    "/api/dsm/me/notify-prefs"),                             # U3 · WS-02 내 알림 설정
    ("PUT",    "/api/dsm/me/notify-prefs"),                             # U3 · WS-02 저장 ★쓰기
    # ★ 2026-09-24 **여덟이 늘었다** — 차선 C 2파 (UX-13 · UX-14 · UX-17 · UX-18).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 시험이 먼저 멈춰 세웠다(25 vs 33) — 게이트가 지시보다 위다(D-327).
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey`(**키 거절 — 기본값**).
    #
    #   ⚠ 읽기 여섯은 쓰기 면이 아니라 WRITE_PROBES 대상이 아니다(P-8).
    #     **쓰기는 둘뿐**이다 — `POST /drill` · `POST /cameras/import`. 그 둘의 probe 는
    #     `tests/test_tenant_isolation.py` 에 함께 들어갔다(선등록에서 옮겨 온 자리다).
    #   ⚠ 등록 순서가 곧 라우팅이다(D-410): `/events/queue`·`/events/response-times` 는
    #     `/events/{int:event_id}` **위**에, drill·cameras 넷은 `/settings/{domain}` **아래**에
    #     선다. 이 순서가 바뀌면 조용히 404·405 가 되고, 조용한 404 는 「기능이 없다」와
    #     구별되지 않는다.
    ("GET",  "/api/dsm/events/queue"),                    # UX-13 초점 큐 + ×N 묶음
    ("GET",  "/api/dsm/events/response-times"),           # UX-14 월간 p50/p95
    ("GET",  "/api/dsm/events/{int:event_id}/timeline"),  # UX-14 네 시각
    ("GET",  "/api/dsm/drill"),                           # UX-17 훈련 모드 상태
    ("POST", "/api/dsm/drill"),                           # UX-17 스위치 ★쓰기
    ("GET",  "/api/dsm/drill/report"),                    # UX-17 종료 보고서
    ("GET",  "/api/dsm/cameras/address-gap"),             # UX-18 「주소 없는 카메라 N대」
    ("POST", "/api/dsm/cameras/import"),                  # UX-18 벌크 ★쓰기(dry_run 기본 True)
    # ★ 2026-09-05 TC **셋이 늘었다** — UX-19 외부 웹훅 구독 (차선 S).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #
    #   왜 F-05 진입면 위에 세우나 — **새 인증 경로를 만들지 않는다**(세종 §4-4 · P-37).
    #   웹훅은 「이 URL 을 아는 사람은 누구나」가 되기 가장 쉬운 자리다. 구독을 등록하는
    #   문을 따로 내면 그 문이 곧 새 계정 체계가 된다. 그래서 **이미 있는 문 옆에** 선다.
    #
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey`(**키 거절 — 기본값**).
    #   ★ 셋 다 들어오는 키를 받지 않는다. 특히 등록이 그렇다 — 키로 구독을 걸 수 있으면
    #     키 하나가 **자기에게 이벤트를 계속 흘려보내는 관**이 되고, 키를 폐기해도
    #     그 관은 남는다(api-keys 셋에 키를 안 연 것과 같은 이유).
    #   ⚠ 쓰기 둘(등록·해지)의 격리는 `tests/test_s_webhook_outbox.py` 가 잰다.
    #     등록은 **남의 것을 가리킬 인자가 없고**(주인은 서버가 정한다), 해지는
    #     `assert_scoped` 를 지난다 — 대장의 사유가 그 둘을 이름으로 적고 있다.
    ("POST",   "/api/dsm/webhook-subscriptions"),                        # ★쓰기 등록
    ("GET",    "/api/dsm/webhook-subscriptions"),                        # 목록
    ("DELETE", "/api/dsm/webhook-subscriptions/{int:subscription_id}"),  # ★쓰기 해지
    # ★ 2026-09-05 TC **둘이 늘었다** — 법 고지 배선 (LAW-02 · LAW-03 · 차선 E).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 시험이 먼저 멈춰 세웠다(36 vs 38) — **게이트가 지시보다 위다**(D-327).
    #   차선 둘이 각자 라우트를 얹었고 둘 다 자기 것만 등재했다. 두 차선에 걸친 자리는
    #   조율자가 병합에서 맞춘다 — 그것이 이 시험이 병합 때 빨개지는 이유이자 값이다.
    #
    #   왜 F-05 진입면 위에 세우나 — 세종 초안(`docs/design/GX-LAW-02·03`)의 「제품 자동」
    #   칸을 채우는 **읽기 전용** 문이다. 안내판·처리방침을 사람이 손으로 옮겨 적으면
    #   칸이 하나 늘 때마다 그 문서가 조용히 낡는다. 그래서 **제품에서 생성한다.**
    #
    #   문지기: `@tenant_scoped` + `JwtOrInboundKey`(**키 거절 — 기본값**).
    #   ★ 둘 다 들어오는 키를 받지 않는다. 고지문 초안은 **아직 법률 검토 전**이고
    #     (대장 LAW-02·03 은 「미측정」이다), 검토 안 된 문안이 외부 연계로 새어 나가면
    #     그것이 곧 대외 문서가 된다. **초안이 있다는 것과 게시해도 된다는 것은 다르다.**
    #   ⚠ **읽기 전용이다** — 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #   ⚠ 등록 자리가 `settings/{domain}` **위**여야 한다. 아래로 내려가는 순간 둘 다
    #     `{domain}` 에 삼켜져 조용히 405/404 가 된다 — D-410 이 남긴 자리다.
    ("GET", "/api/dsm/settings/notice-draft"),          # LAW-02 영상정보처리기기 고지
    ("GET", "/api/dsm/settings/privacy-collection"),    # LAW-03 수집 항목(모델에서 생성)
    # ★ 2026-09-05 TD **하나가 늘었다** — UX-23 카메라 격자의 맥박 (차선 C2).
    #   손으로 이 줄을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 턴에도 차선 넷이 각자 자기 것만 등재한다 — 두 차선에 걸친 자리는 조율자가
    #   병합에서 맞춘다(위 LAW-02·03 줄이 그 규약을 이미 적었다).
    #
    #   왜 라우트를 냈나: OPS-15 의 맥박 판정은 **시스템 이벤트로만** 나가고 있었다
    #   (`camera_cluster_down`). 화면에서 「어느 카메라가 응답이 없는가」를 볼 문이
    #   없었고, 문이 없으면 화면은 카메라 목록을 받아 **자기 문턱으로** 생사를 정하게
    #   된다 — 그러면 화면의 「응답 없음」과 시스템 이벤트의 두절 판정이 갈린다.
    #   판정은 한 곳(`camera_pulse.py`)이고, 이 문은 그것을 **인용해서 낸다.**
    #
    #   문지기: `@tenant_scoped`(남의 테넌트 카메라의 생사 · 구역 두절은 재난 정보다) +
    #           `JwtOrInboundKey`(**키 거절 — 기본값**).
    #   ⚠ **읽기 전용이다** — `scan_clusters(create_events=False)` 로 부른다.
    #     쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #   ⚠ `/cameras/address-gap`·`/cameras/import` 와 형제다. 변수 조각이 없으므로
    #     서로 삼키지 않는다.
    ("GET", "/api/dsm/cameras/pulse"),                  # UX-23 카메라 맥박 + 군집 두절
    # ★ 2026-09-05 턴 E — **여섯이 늘었다** (차선 E · P-57 파기 셋 · OPS-16 계량 셋).
    #   손으로 이 줄들을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기
    #   남긴다. 이 시험이 47 != 53 으로 멈춰 세운 것이 **그 시험의 값이다** —
    #   턴 D 의 차선 L 이 여덟을 등재한 것과 같은 자리다(evidence/LAW-02a/README §부록).
    #
    #   ── P-57 파기 (「보관 기간이 지난 영상 지우기」) ──────────────────────
    #   왜 라우트를 냈나: 「지운다」가 이 저장소에서 **지우지 않았다**(dj-core 소프트
    #   삭제). 파기는 하드 삭제 + 객체 삭제 + 파기 기록이고, 그것을 사람이 누르는 자리와
    #   그 대상을 **미리 보는 자리**가 필요하다 — 파기는 일어난 뒤에 알면 늦다.
    #
    #   왜 `/law/retention/sweep` 옆에 다른 문인가: **좁히는 축이 다르다.** sweep 은
    #   전역이고 전역 관리자만 부른다. purge 는 테넌트 하나다. 한 문에 두 뜻을 담으면
    #   「내 것만 지우려던 손」이 전역을 지운다.
    #
    #   문지기: `@tenant_scoped` + `JwtOrInboundKey`(**키 거절 — 기본값**) + 관리자.
    #   ⚠ `POST /law/purge` 는 **쓰기 면이다.** 되돌릴 수 없다 — 그래서 `dry_run`
    #     기본값이 **참**이고, `dry_run=false` 에는 사유가 없으면 422 다.
    #   ⚠ `/law/purge/tenants`·`/law/purge/history` 는 **리터럴**이고 `{}` 조각이
    #     없다. `/law/privacy-requests/{receipt_no}` 와 접두가 달라 서로 안 삼킨다.
    ("GET", "/api/dsm/law/purge/tenants"),              # P-57 파기 대상(선언한 테넌트)
    ("POST", "/api/dsm/law/purge"),                     # P-57 파기 (dry-run 기본값)
    ("GET", "/api/dsm/law/purge/history"),              # P-57 「지운 기록」
    #
    #   ── OPS-16 계량 (「이번 달 사용량」) ────────────────────────────────
    #   왜 라우트를 냈나: 계량 자리가 **0건**이었다 [실측]. 가격표를 쓸 수는 있어도
    #   청구할 수는 없었다. 다섯 수(카메라 대수·쓰는 사람 수·이벤트 수·보낸 알림 수·
    #   저장 용량)를 **읽기 전용**으로 센다.
    #
    #   ⚠ **셋 다 읽기 전용이다** — 계량이 행을 하나라도 만들면 **그 수로 청구하게
    #     된다.** 쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #     `tests/test_be_metering.py::test_reading_usage_creates_no_rows` 가 지킨다.
    #   ⚠ `/metering/csv` 는 CSV 본문을 그대로 낸다(봉투가 아니다). `<a href>` 로
    #     붙이면 인증 헤더가 안 실려 401 이므로 화면은 axios 로 받는다.
    ("GET", "/api/dsm/metering"),                       # OPS-16 이번 달 사용량 다섯 칸
    ("GET", "/api/dsm/metering/series"),                # OPS-16 달별 사용량
    ("GET", "/api/dsm/metering/csv"),                   # OPS-16 표 내려받기
    # ★ 2026-09-10 턴 O — **하나가 늘었다** (UX-30 · P-125 · 차선 B).
    #   손으로 이 줄을 더하는 일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   이 시험이 먼저 멈춰 세웠다(56 vs 57) — **게이트가 지시보다 위다**(D-327).
    #
    #   왜 라우트를 냈나 — **경로의 숫자가 다른 것을 가리키고 있었다** [실측 2026-09-10].
    #   재난안전과 공무원이 상황 보고서를 받으려고 `GET /api/dsm/reports/7.pdf` 를 불렀고,
    #   나온 것은 **「배송 완료 보고서」**(Sender Name · Delivery Fee · ETRI Receipt ID)였다.
    #   `?event_id=4802` 를 붙여도 본문이 그대로였다 — `reports/{template_id}.pdf` 의 숫자는
    #   **템플릿 표의 행 번호**이고, 그 표의 19행이 전부 택배 운송장이며, K4 의 치환은
    #   `{{ events }}` 등 일곱 이름만 바꾸는데 그 서식에는 그 일곱이 하나도 없었기 때문이다.
    #   → 요청이 서식을 고르는 한 이 사고는 되풀이된다. 이 문은 **사건 id 를 경로로 받고
    #     서식은 코드가 정한다**(`apps/dsm/incident_report.py` · 1쪽 · 택배 칸 0).
    #
    #   문지기: `@tenant_scoped`(남의 사건이 종이로 나가면 IDOR) +
    #           `JwtOrInboundKey`(**키 거절 — 기본값**. 종이는 사람이 받는 것이고,
    #           들어오는 키에 보고서를 열어 주면 키 하나가 사건 전건의 사본을 뜬다).
    #   ⚠ **읽기 전용이다** — 행을 하나도 만들지 않는다(`usage_count` 도 안 올린다).
    #     쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다(P-8).
    #   ⚠ `/events/{int:event_id}/snapshot`·`/timeline` 과 형제다. 끝 조각이 달라
    #     서로 삼키지 않는다(D-410).
    ("GET", "/api/dsm/events/{int:event_id}/report.pdf"),   # UX-30 사건 보고서 1쪽
    # ★ [턴 Q · WO-01 §4.2] **다섯이 늘었다** — 차선 라우터 모듈(`api_u1/u3/u24.py`)에서
    #   태어났다. 넷 다 `JwtOrInboundKey()` 기본값(들어오는 키 거절) + `@tenant_scoped`.
    #   새 인증 경로는 없다 — 차선 파일의 `_scope()` 는 `api.py::_scope` 와 같은 세 줄이다.
    ("POST", "/api/dsm/events/{int:event_id}/review-and-acknowledge"),  # U1 · AC-2 판정+접수 한 트랜잭션
    ("POST", "/api/dsm/events/{int:event_id}/field-photo"),             # U3 · UX-45 현장 사진 올리기
    ("GET", "/api/dsm/stats/summary"),                                  # U24 · UX-39 통계 요약
    ("GET", "/api/dsm/stats/by-reviewer"),                              # U24 · UX-35 요원별
    ("GET", "/api/dsm/stats/false-positive"),                           # U24 · UX-36 오탐률
    # ★ [턴 R · WO-01 §5 · 차선 U1] **다섯이 늘었다** — UX-34 인계 자동 초안 ·
    #   사건 메모(부속서A #15). 전부 `api_u1.py`(같은 차선 파일)에서 태어났다.
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey()` 기본값(들어오는 키 거절).
    #   새 인증 경로는 없다 — 이 파일의 `_scope()` 는 `api.py::_scope` 와 같은 세 줄이다.
    #
    #   왜 라우트를 냈나 — 서버가 초안을 쓰고 사람이 고친다(UX-34). 셈은
    #   `apps.dsm.services.recent_events`(K1)를 그대로 옮길 뿐이고, 저장은
    #   `stream_monitors.models.DsmHandover`(턴 Q 가 세운 표)에 한다.
    #   `/handover/latest` 는 다음 근무자 홈 카드가 읽을 자리(그리는 것은 F 차선 몫).
    #   메모는 새 표를 두지 않고 `common/audit_writer.py`(F-12 감사와 같은 표)를
    #   재사용한다 — 사건별 이름(`event_note:{id}`)으로 가른다.
    ("GET", "/api/dsm/handover/draft"),                                 # U1 · UX-34 초안 미리보기(저장 안 함)
    ("POST", "/api/dsm/handover/draft"),                                # U1 · UX-34 초안 저장
    ("GET", "/api/dsm/handover/latest"),                                # U1 · UX-32-U2 다음 근무자 카드 자리
    ("POST", "/api/dsm/events/{int:event_id}/note"),                    # U1 · 부속서A #15 사건 메모 남기기
    ("GET", "/api/dsm/events/{int:event_id}/note"),                     # U1 · 부속서A #15 사건 메모 조회
    # ★ [턴 R · 병합] **넷이 늘었다** — 차선 F 하나 · 차선 U56 셋. 손으로 이 줄들을 더하는
    #   일이 곧 「진입면을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #
    #   ★ 이 넷은 **조율자가 병합에서 등재했다.** 차선 셋(U1·U3·U56)이 각자 「내 것은
    #     등재했고 남은 빨강은 내 결함이 아니다」로 보고했고, 셋 다 옳았다 — 229줄이
    #     이미 적어 둔 그 자리다: **두 차선에 걸친 자리는 조율자가 병합에서 맞춘다.**
    #     그것이 이 시험이 병합 때 빨개지는 이유이자 값이다. U56 은 자기 셋만 채워도
    #     F 의 한 줄이 비어 여전히 빨갛다는 것을 보고 **손대지 않았다** — 옳은 판단이다.
    #
    #   문지기: 전건 `@tenant_scoped` + `JwtOrInboundKey()` 기본값(들어오는 키 거절).
    #   새 인증 경로는 없다 — 차선 파일의 `_scope()` 는 `api.py::_scope` 와 같은 세 줄이다.
    #
    #   ⚠ 진행률은 **읽기 전용이다**(쓰기 면이 아니므로 WRITE_PROBES 대상이 아니다 · P-8).
    #     다만 그 읽기가 **자동 완료 훅을 태운다** — 카드를 닫는 것은 사람의 체크가 아니라
    #     서버 기록이다(WO-01 §12). 그래서 읽는 것만으로 온보딩 행이 늘 수 있다.
    #   ⚠ 사람 셋은 **관리자만**이다. `people/{int:user_id}/deactivate` 는 남의 계정을
    #     끄는 문이라 문지기가 둘(테넌트 + 역할)이다.
    #   ⚠ `webhook-subscriptions/issue` 는 **기존 `POST /webhook-subscriptions` 옆의 다른
    #     문이다**(226줄). 등록은 구독만 만들고, 이 문은 구독 + 서명키를 한 동작으로 낸다 —
    #     키 값은 **이 응답에 한 번만** 실리고 그 뒤로는 해시만 남는다(D-335 ④).
    #     한 문에 두 뜻을 담지 않은 이유는 `/law/purge` 와 `/law/retention/sweep` 을
    #     가른 것과 같다(276줄): 되돌릴 수 없는 것이 섞이면 손이 미끄러진다.
    ("GET", "/api/dsm/onboarding/progress"),                            # F · UX-46 온보딩 진행률
    ("POST", "/api/dsm/settings/people/create"),                        # U56 · S-14 사람 만들기 ★쓰기
    ("POST", "/api/dsm/settings/people/{int:user_id}/deactivate"),      # U56 · S-14 사람 비활성화 ★쓰기
    ("POST", "/api/dsm/settings/webhook-subscriptions/issue"),          # U56 · P-145 구독+서명키 발급 ★쓰기
    # ★ 2026-09-17 **열하나가 늘었다** — 턴 T 파 2 「닿기」 (차선 U1 1 · U3 1 · U24 6 · U56 3).
    #   이 목록은 손이 아니라 이 시험이 뱉은 「새로 생긴 것」이다(병합 · 조율자).
    #   선등록(write_surfaces_v11.yaml 턴 T 블록)이 미리 적은 「표 밖 자리」 셋이 전부 났다:
    #   ① U24 CSV 반출 ② U1 종결 닫기 ③ U3 M1 처리함(목록 필터로 못 열어 라우트가 됐다).
    #   ⚠ `GET /health` 는 **인증 없는 유일한 진입면**이다 — 아래 PUBLIC_ENTRY_BY_DESIGN 에 사유.
    ("POST", "/api/dsm/queue/field-signals/{int:event_id}/confirm-done"),   # U1 · 종결 확인 = 서버 기록이 닫는다 ★쓰기
    ("GET", "/api/dsm/me/handled-events"),                                  # U3 · M1 처리함(내 회신 낸 사건)
    ("GET", "/api/dsm/stats/axes"),                                         # U24 · 통계 축 5
    ("GET", "/api/dsm/stats/export.csv"),                                   # U24 · CSV 반출(UTF-8 BOM · no-store)
    ("GET", "/api/dsm/events/upper-report/flags"),                          # U24 · 상급 보고 표시 조회
    ("POST", "/api/dsm/events/{int:event_id}/upper-report"),                # U24 · 상급 보고 표시 ★쓰기
    ("DELETE", "/api/dsm/events/{int:event_id}/upper-report"),              # U24 · 상급 보고 해제(소프트) ★쓰기
    # ★ 2026-09-21 (턴 AB · WO-04 §4-3) **하나 늘었다** — 별지 제1호 「재난 상황보고」.
    #   ★★ **이 줄을 손으로 더하는 일이 곷 「진입면을 넓힌다」는 선언이다.**
    #   이번에도 사람이 아니라 도구가 멈춰 세웠다 — 병합 전량 시험에서
    #   `109 != 110` 으로 나왔고, 그랬지 않았으면 문 하나가 **조용히** 늘었다.
    #
    #   문지기: `auth=JwtOrInboundKey()` · 보는 사람은 **보고서와 같다**
    #   (`_report_reader_denial` — 판정식을 새로 안 썼다).
    #   ⚠ 이 문은 임시 자리다: 넷째 서식을 `monthly_report.KINDS` 에 끼우려면
    #     남의 파일을 고쳐야 해서, 사건 하나를 지금 그려 내려주는 문으로 냈다.
    #     실행 기록에 넷째 종류가 서는 날 `monthly_report` 쪽으로 옮겨 붙고
    #     **그때 이 줄도 같은 커밋에서 옮긴다.**
    ("GET", "/api/dsm/events/{int:event_id}/situation-report.docx"),        # U24 · 별지 1호 DOCX
    ("GET", "/api/dsm/audit"),                                              # U24 · 감사 읽기(U2·U4·U5 · 필터 3)
    ("GET", "/api/dsm/health"),                                             # U56 · 생존 확인 · 인증 없음(아래 사유)
    ("GET", "/api/dsm/settings/webhook-subscriptions/{int:subscription_id}/filters"),   # U56 · WS-17
    ("POST", "/api/dsm/settings/webhook-subscriptions/{int:subscription_id}/filters"),  # U56 · WS-17 ★쓰기
    # ── 턴 U (2026-09-18 · 파 3 턴 1 「끝내기」 · 조율자 병합) ────────────────
    #   ★ 열둘이 한 번에 늘었다. 이 표는 **먼저 늘지 않는다** — 문이 선 커밋에서 같이 는다.
    #     늘린 근거는 차선 보고가 아니라 **시험이 뱉은 실제 라우트 목록**이다(아래 판정이 대조한다).
    ("GET", "/api/dsm/reports/runs"),                                       # U24 · 보고서 실행 기록 목록
    ("POST", "/api/dsm/reports/runs"),                                      # U24 · 보고서 만들기 ★쓰기(WS-21)
    ("GET", "/api/dsm/reports/runs/{int:run_id}.docx"),                     # U24 · DOCX 정본 반출(결정 ⑤)
    ("GET", "/api/dsm/reports/runs/{int:run_id}.pdf"),                      # U24 · PDF 병행 반출
    ("GET", "/api/dsm/audit/export.csv"),                                   # U24 · 감사 표 반출
    ("POST", "/api/dsm/cameras/{int:camera_id}/address"),                   # U56 · 한 대 고치기 ★쓰기(WS-23)
    ("POST", "/api/dsm/system/restart-request"),                            # U56 · 요청만 기록 ★쓰기(WS-22 · 실행은 창)
    ("GET", "/api/dsm/system/requests"),                                    # U56 · 요청 목록(테넌트 격리)
    # ★ [턴 V · 차선 F] **하나가 늘었다** — 점검 창에서 한 일을 적는 문(WS-24 · 선등록 적중).
    #   D-492 가 `DsmSystemRequest.handled_note` 를 「쓰는 문이 없다」로 등재한 자리이고,
    #   이 문이 그 사유를 끝냈다(등재 해제와 배선은 같은 변경 · scripts/verify_dead_fields.py).
    #   문지기: `@tenant_scoped` + `JwtOrInboundKey` + `guard_setting`(관리자만 · 감사 1행).
    #   ⚠ 이 문도 **컨테이너를 건드리지 않는다** — 사람이 한 일을 적는 칸이지 실행하는
    #     문이 아니다(응답 `executed_by_app: false` · tests/test_f_system_request_handled.py).
    ("POST", "/api/dsm/system/requests/{int:request_id}/handled"),          # F · 점검 창 기록 ★쓰기(WS-24)
    ("GET", "/api/dsm/system/backup-receipts"),                             # U56 · 회수증(없으면 UNKNOWN · 0 이 아니다)
    ("GET", "/api/dsm/system/storage"),                                     # U56 · 상한·사용률(미선언이면 null + 문장)
    ("GET", "/api/dsm/settings/api-keys/{int:key_id}/scopes"),              # U56 · API-03 범위 조회
    ("POST", "/api/dsm/settings/api-keys/{int:key_id}/scopes"),             # U56 · API-03 범위 저장 ★쓰기
    # ── 턴 W (2026-09-19 · 차선 U56) ─────────────────────────────────────────
    # ★ **하나가 늘었다.** 이 줄을 손으로 더하는 일이 곧 「진입면을 넓힌다」는 선언이다 —
    #   그리고 이 시험은 **제 값을 했다**: U56 자기 시험 94/0 은 이 문을 못 봤고, 옆 차선의
    #   넓은 회귀가 여기서 멈춰 세웠다. **자기 문만 돌리면 자기 문만 보인다.**
    #
    #   무엇인가: `/dsm/system` 화면이 **넉 달 동안 404 를 받아 온 바로 그 경로**다
    #   (U5-BACKUP-404). 화면은 그 404 를 빨강이 아니라 회색(「백엔드 신호 대기」)으로
    #   그렸고, 그래서 아무도 안 고쳤다. 이 문이 그 회색을 없앴다.
    #   증거: docs/agent/evidence/U5-BACKUP-404/ (눌러서 잰 판 · 분모 11건 · 404 0건).
    #
    #   문지기: `@tenant_scoped(required=False)` + `JwtOrInboundKey()`(**기본값 = 키 거절**)
    #           + `guard_setting`(관리자만 · 감사 1행). 익명 401 · 역할 없음 403.
    #   ★★ **이 문은 들어오는 키를 받지 않는다.** 그래서 `test_f05_inbound_api_key.py` 의
    #      `INBOUND_KEY_ALLOWED` 는 **한 칸도 안 건드렸다** — 그 목록이 이 턴에 바뀐 것은
    #      차선 U3 의 `cameras/pulse` 때문이지 이 줄 때문이 아니다.
    #   ★ **읽기 전용이다.** 같은 경로의 POST 는 405 [실측 · nginx:8500]이고, 그 사실을
    #     지키는 시험이 따로 있다(tests/test_u56_backup_declaration.py
    #     ::test_post_is_not_opened_on_this_path). 여기에 POST 줄이 생기면 그때는
    #     **쓰기 면이 난 것**이고 선등록 표에 표 밖 1건으로 적어야 한다.
    ("GET", "/api/dsm/ops/backup/declaration"),                             # U56 · 백업 선언 읽기(U5-BACKUP-404 닫음)
    # ★ 2026-09-23 (턴 AE · 차선 U온) **하나 늘었다** — 온보딩 48행 U2#3
    #   「이벤트 등급 재판정」. 이 시험이 그것을 잡았다: 병합 전량에서 `110 != 111` 로
    #   났고, 그러지 않았으면 문 하나가 **조용히** 늘었다. 아래는 손으로 적은 판단이
    #   아니라 이 문을 **실제로 두드려** 잰 것이다(추측으로 등재하지 않는다).
    #
    #   왜 이 문이 있어도 되는가 — 이미 잰 넷
    #   --------------------------------------
    #   ① 누가 부를 수 있나 — 새 인증 경로는 없다(`api_u24.py::_scope` 는
    #      `api.py::_scope` 와 같은 세 줄) + `@tenant_scoped`. **읽기 전용(U4
    #      `view_only_-_anyang`)은 403 이다** — 다만 이 문 자신의 로직이 막는 것이
    #      아니라 **저장소 전역의 `RoleGateMiddleware`(P-119 · `common/role_gate.py`)**
    #      가 「쓰기 메서드 + 읽기 전용 역할」을 이 문에 이르기도 전에 끊는다(허용
    #      목록 `READONLY_WRITE_ALLOWED_PATTERNS` 에 이 경로를 안 넣었다 — 그래서 막힌다).
    #      [실측 2026-09-23 · `gxseed_u4_official` 로 `POST …/4802/severity` 를
    #      직접 두드림] → `403 {"code": "read_only_role", ...}`, 그 뒤 DB 재조회로
    #      `severity` 가 안 바뀐 것도 확인했다(막힌 요청이 조용히 반쪽만 쓰지 않는다).
    #   ② 남의 테넌트 사건 — **404**. `services.event_detail`(기존 함수 그대로
    #      재사용 — 새 문지기를 안 짰다)이 커널의 `assert_scoped` 를 태우고, 없는
    #      사건·남의 사건은 여기서 끊긴다. [실측] `event_id=999999999` → `HttpError(404,
    #      "그런 사건이 없습니다.")`.
    #   ③ 나쁜 값 — **400**. `DetectionEvent.Severity.values`(계약 그대로 ·
    #      `info`/`warning`/`critical`) 밖의 값은 여기서 거절한다. [실측]
    #      `severity="bogus"` → `HttpError(400, "severity='bogus' 은 계약에 없다. ...")`.
    #   ④ 감사 · 되돌림 — 성공은 `audit.record_event_action` 으로 한 행 남는다
    #      (실패도 남긴다 — ①②의 403·404 도 각자 감사 행이 있다). [실측] 사건
    #      4802(그룹 ETRI-Group)를 `critical → warning`(감사 #340014) →
    #      `warning → critical`(감사 #340015)로 되돌렸고, DB 재조회로 원복을
    #      확인했다 — 시험용 상태 변경은 남기지 않았다.
    ("POST", "/api/dsm/events/{int:event_id}/severity"),                    # U2#3 · 이벤트 등급 재판정 ★쓰기
})

#: 인증 없이 열리는 진입면 — **이름과 사유로** 잠근다. 늘면 여기 사유가 먼저 늘어야 한다.
#:   `GET /health` (턴 T · U56): 생존 확인은 정의상 로그인 전에 부른다. 응답은 검사 이름과
#:   상태 이름(ok/fail) 뿐 — 테넌트 자료·호스트명·값 없음(tests/test_u56_health.py 가 못박음).
#:   같은 이름을 `scripts/probe_read_surface.py::PUBLIC_READ_BY_DESIGN` 에도 올렸다(P-133 계열).
PUBLIC_ENTRY_BY_DESIGN: dict[tuple[str, str], str] = {
    ("GET", "/api/dsm/health"): "생존 확인 — 로그인 전에 부른다 · 검사 이름과 상태 이름뿐",
}

#: K1 커널을 소비하는 모듈 전수 → **왜 소비하는가.**
#:
#: 사유를 함께 두는 이유: 새 소비자가 생겼을 때 "늘었다" 만으로는 그것이 옳은지 모른다.
#: 커널끼리의 재사용(K2·K3·K4·K6)은 **진입면이 아니고**, 파이프라인(bridge)도 HTTP 가
#: 아니다. F-05 가 금지하는 것은 **App 이 여럿이 되는 것**이다.
K1_CONSUMERS: dict[str, str] = {
    "backend/kernels/k1_event/__init__.py":
        "커널 자신의 공개 면 — 소비자가 아니라 **소비되는 쪽**이다",
    "backend/kernels/k1_event/services.py":
        "커널 자신의 구현 — 공개 면이 여기를 다시 import 한다",
    "backend/kernels/k1_event/response_flow.py":
        "★ 커널 자신의 구현 — 대응 진행 축(D-399). 1차판은 이 파일이 `apps/dsm/` 에 "
        "있었고 `AppStaysThinTest` 가 즉시 빨개졌다. `DetectionEvent` 의 수명주기는 "
        "K1 의 것이고 review_event·close_event 가 이미 여기 산다 — 흩어 두면 같은 "
        "표의 규칙이 두 층에 나뉜다. 소비자가 아니라 **소비되는 쪽**이다",
    "backend/apps/dsm/services.py":
        "★ **유일한 App 소비자.** F-05 가 말하는 그 하나의 진입면이 여기서 시작한다",
    "backend/stream_monitors/management/commands/seed_dsm_events.py":
        "★ 검수용 시드 (P-9). **이 소비자가 K1 을 부르는 것이 요점이다** — 지시서가 정한 "
        "「실제 이벤트」는 K1 생성 경로를 통과한 행이고, DB 직접 INSERT 는 모형이다. "
        "HTTP 진입면이 아니라 운영자가 손으로 부르는 커맨드다",
    "backend/kernels/k2_notify/services.py":
        "커널 간 재사용 — 알림이 이벤트를 읽는다. HTTP 진입면이 아니다",
    "backend/kernels/k2_notify/renotify.py":
        "★ 커널 간 재사용 — **재알림 N분**(차선 D · U3 · 2026-09-04). 이벤트를 읽어 "
        "「아직 아무도 손대지 않았는가」를 묻는다(K1 `response_state`). 전이표를 "
        "여기 다시 적지 않으려고 소비자가 됐다 — 두 벌이면 갈리고, 갈리면 재알림이 "
        "영원히 울리거나 영원히 안 울린다(D-212). HTTP 진입면이 아니다: 이 이름을 "
        "여는 라우트는 아직 없고, 여는 커밋이 `EVENT_ENTRY_SURFACE` 를 함께 늘린다",
    "backend/kernels/k1_event/field_reply.py":
        "★ 커널 자신의 구현 — **현장 회신**(차선 D · U3 #9 · M3 · 2026-09-04). "
        "쓰기 앞에 K1 의 읽기 문지기(`get_event`)를 그대로 세우려고 이 모듈이 "
        "K1 을 부른다 — `advance_response` 가 한 것과 같은 규약이고, 문지기를 새로 "
        "만들면 두 벌이 갈린다(D-212). 회신은 `DeliveryRecord` 도 새 표도 만들지 "
        "않고 전용 `logger_name`(`guardianx.dsm.field_reply`)의 감사 한 줄로 남는다. "
        "소비자가 아니라 **소비되는 쪽**이다 — HTTP 진입면이 아니다",
    "backend/kernels/k3_dashboard/services.py":
        "커널 간 재사용 — 대시보드가 이벤트를 읽는다",
    "backend/kernels/k4_report/services.py":
        "커널 간 재사용 — 보고서가 이벤트를 읽는다",
    "backend/kernels/k6_feedback/services.py":
        "커널 간 재사용 — 오탐률이 이벤트를 센다",
    "backend/stream_monitors/services/false_positive_closer.py":
        "★ **오탐 결합이 사는 단 한 곳** (P-16 · 2026-09-20). 판정 축의 신호를 받아 "
        "대응 축을 닫는다. HTTP 진입면이 아니다 — 밖에서 부를 주소가 없고, "
        "`verdict_changed` 를 받는 자리다. 이 모듈이 **소비자인 것이 요점**이다: "
        "`review_event` 가 `response_state` 를 직접 쓰면 D-399 가 가른 두 축이 코드에서 "
        "다시 맞물린다. 결합은 한 곳에만 두고, 그 한 곳을 여기 이름으로 적는다",
    "backend/stream_monitors/services/detection_event_bridge.py":
        "AI 검출 파이프라인 배선. gRPC 콜백이라 **요청자가 없고**(D-281 시스템 스코프) "
        "HTTP 진입면이 아니다 — 밖에서 부를 수 있는 주소가 없다",
    "backend/stream_monitors/services/camera_pulse.py":
        "★ **OPS-15 카메라 맥박 군집 두절** (차선 Q · 2026-09-24). 구역 N중 M 두절을 "
        "`camera_cluster_down` 이벤트로 낸다 — **K1 경로 하나로만** 만든다. 여기서 "
        "`DetectionEvent` 를 직접 만들면 등급 검증·소유 상속·중복 억제가 한 번도 안 "
        "돌고, 그 행은 화면에는 이벤트로 보이면서 아무 규칙도 안 탄다(D-401). "
        "HTTP 진입면이 아니다 — 밖에서 부를 주소가 없고 맥박 검사가 부르는 자리다",
}

#: `/api/dsm/events` 응답의 키 집합. **모양이 계약이다** — 조용히 늘거나 줄면 멈춘다.
EVENT_RESPONSE_KEYS: frozenset[str] = frozenset({
    "event_id", "event_type", "severity", "status", "verdict",
    "occurred_at", "last_seen_at", "stream_monitor_id", "stream_monitor_name",
    "lat", "lng", "snapshot_path",
    # ★ 2026-09-21 **하나가 늘었다** — 대응 진행(D-399). 손으로 이 줄을 더하는 일이
    #   곧 「목록의 모양을 넓힌다」는 선언이고, 그 선언을 여기 남긴다.
    #   왜 넓혔나: 그전까지 대응 축은 **상세에만** 있었고, 그래서 관제팀장의
    #   「미처리 이벤트 확인」을 서버가 걸러 줄 수 없었다(온보딩 48행 U2 #2).
    #   ⚠ 넓힌 것은 **읽기 면**이다 — 이 값을 쓰는 문은 여전히 `/events/{id}/response`
    #     하나뿐이고, 목록은 아무것도 바꾸지 않는다.
    "response_state",
})


def _py_files():
    for p in BACKEND.rglob("*.py"):
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if "/tests/" in str(p).replace("\\", "/"):
            continue                       # 시험은 진입면이 아니다
        yield p


def _rel(p: Path) -> str:
    return "backend/" + str(p.relative_to(BACKEND)).replace("\\", "/")


def _imports(tree: ast.Module) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out.add(node.module)
            out |= {f"{node.module}.{a.name}" for a in node.names}
    return out


def _scan() -> tuple[list[str], list[str]]:
    """(K1 을 import 하는 모듈, 라우트를 가진 모듈) — **직접 import 로만** 센다."""
    consumers: list[str] = []
    route_modules: list[str] = []
    for path in _py_files():
        src = path.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        if any(i.startswith("kernels.k1_event") for i in _imports(tree)):
            consumers.append(_rel(path))
        if "@route." in src or "@api_controller" in src:
            route_modules.append(_rel(path))
    return sorted(consumers), sorted(route_modules)


class EntrySurfaceIsOneTest(SimpleTestCase):
    """★ ① **하나로만 들어오는가** — 부작위 시험 (D-300)."""

    def test_the_event_kernel_has_exactly_one_app_consumer(self) -> None:
        """★ AC 의 핵심 단어는 "하나로만" 이다. 그것은 **App 이 하나**라는 뜻이다."""
        consumers, _ = _scan()
        apps_consuming = [m for m in consumers if m.startswith("backend/apps/")]
        self.assertEqual(
            ["backend/apps/dsm/services.py"], apps_consuming,
            "K1 커널을 소비하는 App 이 하나가 아닙니다 — 진입면이 둘이 되면 "
            "F-05 의 '하나로만' 이 깨집니다. 새 App 이 이벤트를 쓰려면 "
            "그 판정을 먼저 받으십시오.")

    def test_no_route_module_imports_the_event_kernel_directly(self) -> None:
        """★ 라우트가 커널을 **직접** 부르면 App 계층이 비어 버린다 (DA-04 §1-1).

        실측: 라우트를 가진 모듈 51개 중 0개. 0 이 아니라 **51 을 함께 출력**하는 것이
        요점이다 — 모수 없는 초록은 보고가 아니다(D-271).
        """
        consumers, route_modules = _scan()
        self.assertGreater(len(route_modules), 30,
                           f"라우트를 가진 모듈을 {len(route_modules)}개밖에 못 셌습니다 — "
                           f"열거기가 눈이 멀었습니다 (D-301).")
        offenders = sorted(set(consumers) & set(route_modules))
        self.assertEqual(
            [], offenders,
            f"라우트를 가진 모듈이 K1 을 직접 import 합니다: {offenders}. "
            f"(모수: 라우트 모듈 {len(route_modules)} · K1 소비자 {len(consumers)})")

    def test_every_k1_consumer_is_registered_with_a_reason(self) -> None:
        """★ 소비자가 늘면 **사유와 함께** 늘어야 한다 — 이름으로 잠근다 (D-285 ②).

        개수로 잠그면 하나가 지워질 때 새 소비자가 들어올 자리가 생긴다.
        """
        consumers, _ = _scan()
        self.assertTrue(consumers, "K1 소비자를 한 건도 못 찾았습니다 — 열거기 고장입니다.")
        unlisted = [m for m in consumers if m not in K1_CONSUMERS]
        self.assertEqual(
            [], unlisted,
            f"등재되지 않은 K1 소비자: {unlisted}. 등재는 면제가 아니라 **선언**입니다 — "
            f"왜 이 모듈이 이벤트를 쓰는지 K1_CONSUMERS 에 적으십시오.")
        gone = [m for m in K1_CONSUMERS if m not in consumers]
        self.assertEqual(
            [], gone,
            f"등재돼 있는데 이제 K1 을 안 씁니다: {gone}. 낡은 등재가 남으면 "
            f"다음에 늘어나는 소비자를 그 이름이 가립니다.")
        for module, why in K1_CONSUMERS.items():
            self.assertGreater(len(why.strip()), 10, f"{module} 의 사유가 비었습니다.")


class EntrySurfaceIsLockedTest(SimpleTestCase):
    """★ ② 그 하나의 진입면이 **잠겨 있는가.**"""

    def _dsm_routes(self):
        from common.tenant_scope import enumerate_operations

        return [r for r in enumerate_operations() if r.path.startswith("/api/dsm/")]

    def test_the_entry_surface_is_pinned_by_name(self) -> None:
        """등재된 10개가 전부다. 늘거나 줄면 멈춘다 — 진입면은 계약이다."""
        rows = self._dsm_routes()
        actual = {(r.method, r.path) for r in rows}
        self.assertEqual(
            set(EVENT_ENTRY_SURFACE), actual,
            f"진입면이 달라졌습니다.\n"
            f"  새로 생긴 것: {sorted(actual - set(EVENT_ENTRY_SURFACE))}\n"
            f"  사라진 것:   {sorted(set(EVENT_ENTRY_SURFACE) - actual)}")

    def test_every_entry_route_is_authenticated(self) -> None:
        naked = [(r.method, r.path) for r in self._dsm_routes() if not r.has_auth]
        for key in naked:
            self.assertGreater(len(PUBLIC_ENTRY_BY_DESIGN.get(key, "").strip()), 10,
                               f"인증 없는 진입면인데 사유가 없습니다: {key}")
        self.assertEqual(sorted(PUBLIC_ENTRY_BY_DESIGN), sorted(naked),
                         f"인증 없는 진입면: {naked} · 사유 등재: {sorted(PUBLIC_ENTRY_BY_DESIGN)}")

    def test_every_entry_route_is_tenant_scoped(self) -> None:
        """문지기 없는 경로가 하나 생기면 그 순간 다시 샌다 (D-275 §5-1)."""
        loose = [(r.method, r.path) for r in self._dsm_routes() if r.scope is None]
        self.assertEqual([], loose, f"테넌트 문지기가 없는 진입면: {loose}")

    def test_the_count_is_not_zero(self) -> None:
        """★ 0건은 통과가 아니라 **판정 불가**다 (D-301). 라우트를 못 세면 위 셋이 전부 초록이다."""
        self.assertEqual(
            len(EVENT_ENTRY_SURFACE), len(self._dsm_routes()),
            "런타임에서 진입면을 세지 못했습니다 — 등록이 바뀌었거나 열거기가 멀었습니다.")


class EntryShapeIsStableTest(SimpleTestCase):
    """★ ③ **모양이 계약이다** — 응답 키가 조용히 늘거나 줄면 외부 App 이 깨진다."""

    def test_the_event_response_keys_are_pinned(self) -> None:
        """라우트 소스에서 응답 딕셔너리의 키를 **읽어** 대조한다.

        HTTP 를 태우지 않는 이유: 이 시험이 재는 것은 값이 아니라 **모양**이고,
        모양은 소스에 있다. 값까지 재는 것은 E2E-1 의 일이다(두 벌로 재지 않는다).
        """
        from apps.dsm.api import DsmAPI

        src = inspect.getsource(DsmAPI.events)
        keys = set(re.findall(r'"(\w+)":\s*e\.', src))
        self.assertEqual(
            set(EVENT_RESPONSE_KEYS), keys,
            f"이벤트 응답의 모양이 달라졌습니다.\n"
            f"  새로 생긴 키: {sorted(keys - set(EVENT_RESPONSE_KEYS))}\n"
            f"  사라진 키:   {sorted(set(EVENT_RESPONSE_KEYS) - keys)}\n"
            f"외부 App 이 이 키를 읽습니다 — 바꾸려면 그 판정을 먼저 받으십시오.")

    def test_the_shape_comes_from_the_kernel_view_not_the_model(self) -> None:
        """★ 응답 키가 **커널 값(EventView)에 실재하는가.** 모델을 타고 들어가지 않는다.

        App 이 모델 속성을 직접 읽으면 커널을 바꿀 때 App 이 깨지고, "한 번 개발" 이
        거짓이 된다(DA-04 §1-4).
        """
        from dataclasses import fields

        from kernels.k1_event import EventView

        view_fields = {f.name for f in fields(EventView)}
        missing = sorted(EVENT_RESPONSE_KEYS - view_fields)
        self.assertEqual(
            [], missing,
            f"응답 키가 EventView 에 없습니다: {missing} — App 이 모델을 타고 "
            f"들어가고 있다는 뜻입니다.")


class ApiKeyStoreExistsTest(SimpleTestCase):
    """★ FR-05-3 — **저장처가 생겼다** (2026-09-06 · D-325 표 ② · D-328).

    이 시험의 앞선 판은 정반대를 쟀다: *"저장처가 없다는 사실이 사유와 함께 선언돼
    있어야 한다."* 그 시험은 이렇게 끝맺고 있었다 — **"저장처가 생겼다면 F-05 대장의
    not_measured 도 함께 고치십시오."** 그날이 왔으므로 함께 고친다.

    ★ 이름을 바꾸는 것이 요점이다. `...IsDeclaredMissing` 인 채로 내용만 뒤집으면
      다음 사람이 이름을 믿고 코드를 안 읽는다.
    """

    def test_the_api_key_domain_is_no_longer_blocked(self) -> None:
        from apps.dsm.services import SETTING_DOMAINS

        self.assertIn("api_keys", SETTING_DOMAINS,
                      "API Key 영역이 설정 대장에서 사라졌습니다 — 빠진 줄은 보이지 않습니다.")
        self.assertEqual("", (SETTING_DOMAINS["api_keys"] or "").strip(),
                         "표 ②가 섰는데 사유가 남아 있습니다 — 사유는 막힌 것의 표시입니다.")

    def test_the_store_holds_facts_not_values(self) -> None:
        """★ D-204 · D-319 — 저장처가 생겼다는 것이 **값을 담는다**는 뜻은 아니다."""
        from kernels.k5_trust.credentials import CredentialDef

        self.assertNotIn("value", CredentialDef.__dataclass_fields__,
                         "표 ②가 값을 담기 시작하면 그것은 저장처가 아니라 유출면입니다.")

    def test_every_key_says_what_kind_of_api_it_is(self) -> None:
        """★ D-328 — 「있는가」가 아니라 **「무엇인가」**. 그 칸이 없어서 하루를 잃었다."""
        from kernels.k5_trust.credentials import CREDENTIALS

        self.assertTrue(CREDENTIALS)
        self.assertTrue(all(s.api_type.strip() for s in CREDENTIALS.values()))
