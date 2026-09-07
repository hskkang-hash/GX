# P-83 쓰기 관문 재정의 · 무관문 쓰기 라우트 수리 — 2026-09-06 · 턴 I · 차선 S

기계 시각 2026-09-06 (UTC 13:2x~13:4x) · 대상 서버: **컨테이너 안 `django.test.Client`**
(런타임 레지스트리를 때려야 나오는 분류라 게이트가 아니라 탐침이 잰다 — 8000 은 안 때렸다)

## 0. 한 줄

**「관문 17」은 거짓이었다. 진짜 관문은 2였다. 그리고 그 자리에서 P0 쓰기 구멍 10개가 나왔다 —
전부 닫았고, 다시 재서 401 을 확인했다.**

## 1. 무엇이 거짓 초록이었나

턴 H 까지 `probe_write_surface.py` 는 **빈 본문 `{}`** 하나를 던지고
「도달하지 못하면 = 관문이 섰다(`rejected_elsewhere`)」로 셌다. 재보니:

| 그때의 `rejected_elsewhere` 17자리 | 실제 상태 |
|---|---|
| 13자리 | **422** — 스키마 검증 실패. 인증 없이 **거기까지 갔다** |
| 2자리 | 405 — 그 자리에 그 메서드가 없다(도달 실패) |
| **2자리** | **401 — 이것만 관문이었다** |

422 는 「본문 형식이 안 맞아 떨어졌다」이고, **본문만 맞추면 그대로 들어간다.**
읽기 탐침이 이미 배운 ⑪ 문지기형 교훈(「막은 것의 이름을 대지 못하면 막은 것이 아니다」)이
쓰기 탐침에는 안 들어가 있었다.

## 2. 고친 것 — 탐침이 **스키마를 통과하는 본문**을 만든다

값의 출처는 사람이 읽은 serializer 가 아니라 **그 요청의 422 응답**이다(추정 금지 D-280):

    detail[].loc  → 어느 칸이 빈지        detail[].type → 어떤 형이어야 하는지

빠진 칸을 채워 다시 던지기를 최대 16바퀴 되풀이한다. 채운 자취는 행마다 `rounds_log` 에 남는다.
본체는 여전히 **한 줄도 안 돈다** — 등록된 `view_func` 를 도달 표시만 남기는 대체물로 바꾸고
때린다(D-334). 부작용 0.

판정표(`classify`) — **세 칸을 갈랐다**:

| 상태 | 칸 | 뜻 |
|---|---|---|
| 401 · 403 | `gated` **관문** | 막았다 |
| 422 · 400 | `schema_rejected` **도달·검증** | 막지 않았다. 그리고 그 뒤에 관문이 있는지 **못 쟀다**(회색) |
| 404 · 405 | `unreachable` **도달 실패** | 그 자리에 그 메서드가 없다 |
| 도달 + 쓴다 | `writes` ★ | **P0.** 래칫 없음 · 0건 절대선 |
| 도달 + 안 씀 | `read_only_in_practice` | 래칫 |
| 그 밖(500 등) | `blocked_other` | 따로 센다 |

게이트 첫 줄은 이제 언제나 **`관문 N · 도달·검증 N · 도달 실패 N`** 으로 시작한다.

## 3. 두 번째로 잡은 거짓 — 정적 쓰기 판정이 한 겹만 봤다

첫 재측에서 `/api/apikey/keys` POST 가 `read_only_in_practice`(안 쓴다) 칸에 앉아 있었다.
그 핸들러는 `APIKey.create_key(user=…)` 를 부른다 — `create_key` 가 `WRITE_CALLS` 목록에
없어서 **「안 쓴다」로 셌다.** 목록을 늘리는 대신 **접두**로 보게 고쳤다
(`create*`·`delete*`·`update*`·`save*`·`bulk_*`·`set_*`·`revoke*`·`regenerate*`·`deactivate*` …).
그러자 API 키 발급 면 다섯 자리가 `writes` 로 올라왔다.

## 4. 드러난 P0 — **무관문 쓰기 10자리** (전부 dj-core = §0.4 금지구역 안)

| 메서드 · 경로 | 익명이 할 수 있던 일 | 핸들러의 자체 검사 |
|---|---|---|
| POST `/api/v1/auth/reset-password-for-user` | ★★ **아무 사용자의 비밀번호를 바꾼다**(`{id, new_password}`) | **없음. 데코레이터조차 없다** |
| POST `/api/v1/user/create-user` | 계정 생성 | 문서엔 "Requires admin privileges", 코드엔 그 검사가 없음 |
| POST `/api/v1/auth/register` | 계정 생성 | `@csrf_protect` 뿐 |
| POST `/api/source/save-html` | 템플릿 디렉터리에 파일 쓰기 · `os.remove()` | 없음 |
| PUT `/api/advanced-table/column-order` | 남의 그리드 설정 변경 | 핸들러 **안**의 `check_permission`(200 봉투) |
| POST `/api/apikey/keys` | ★ **API 키 발급** | 컨트롤러 밖에서 도달 |
| POST `/api/apikey/keys/{user_id}` | ★ **남의 이름으로 API 키 발급** | 없음 |
| POST `/api/apikey/keys/{api_key_id}/regenerate` | 남의 키 재발급 | 없음 |
| POST `/api/apikey/bulk-deactivate` | 남의 키 일괄 비활성 | 없음 |
| POST `/api/third-api/api-key-management/keys/{user_id}` | 같은 컨트롤러의 다른 입구 | 없음 |

**API 키를 익명이 만들 수 있으면 그 뒤의 모든 관문은 의미가 없다** — 키가 곧 자격증명이다.

`@csrf_protect` 가 붙은 자리도 관문으로 세지 않았다: CSRF 는 **남의 사이트가 시키는 요청**을
막는 장치이지 직접 때리는 익명을 막는 장치가 아니다(스크립트는 쿠키를 먼저 받아 오면 그만이다).

## 5. 수리 — 라우트가 아니라 **길목**을 막았다 (D-348 그대로)

열 자리 전부 dj-core(`site-packages/core/`) 안이라 라우트 선언을 못 고친다.
`backend/common/access_gate.py`(우리 코드)에서 막았다. dj-core 는 한 줄도 안 바뀌었다.

* `AUTHN_REQUIRED_PATHS` 에 이름 다섯을 더했다.
* **`AUTHN_REQUIRED_PREFIXES` 를 새로 만들었다** — 경로 틀(`{user_id}`)은 이름으로 못 막는다:
  `/api/apikey/` · `/api/third-api/api-key-management/`.
* `judge()` 의 순서를 바꿨다: **이름을 적은 자리는 `AUTHN_SURFACE` 면제보다 앞이다.**
  넓은 규칙(「인증 면은 비켜 준다」) 아래에 좁은 사고(`reset-password-for-user`)가 숨어 있었다.
* 앞단(nginx) 생성기(`common/front_line.py`)에 `location ^~` 접두 블록을 더했다 —
  두 방어선이 **같은 자리**를 덮게. `nginx/generated/gx-gate.conf` 다시 만들었다(익명 401 26자리).

## 6. 재측 — 붙인 뒤 다시 쟀다

    [WRITEAUTH] 관문 14 · 도달·검증 0 · 도달 실패 0 · ★관문없이 도달·쓰기 0 · 도달·안씀 5 · 선언 11
        writes                     0자리
        read_only_in_practice      5자리
        gated                     14자리
        schema_rejected            0자리
        unreachable                0자리
        blocked_other              0자리
        public_by_design          11자리
    [WRITEAUTH] 통과 · rc=0

수리한 **10자리 전부 401**(`gated`). 관문 2 → 14.
`backend/tests/test_access_gate.py` 30건 통과(새 시험 7건 포함 — 스키마를 통과하는 본문으로
호출해서 401 을 확인하고, 로그인 길이 안 막혔다는 **음성 대조**까지 둔다).

## 7. 아직 못 닫은 것 — **회색으로 남긴다, 초록으로 만들지 않는다**

`read_only_in_practice` **5자리**는 익명이 **핸들러까지 닿는다.** 「안 쓴다」는 판정은
**정적이고 한 겹만** 본다 — 서비스 층으로 넘기는 자리는 못 본다:

    POST /api/orders/order/{id}/payment    →  OrderService.payment_order(id) 를 부른다.
                                              `payment_order` 는 접두에도 안 걸린다 → **쓴다**
    POST /api/delivery/etri-integration/receive-from-etri
    POST /api/delivery/processing/assign-packages-to-drone(-s)
    POST /api/delivery/verification/verify-orders

닫지 않은 이유(우회가 아니라 **사유**):

1. `payment` 는 경로 틀이라 접두(`/api/orders/order/`)로만 막을 수 있고, 그 접두는
   주문 면 전체를 덮는다 — 이번 턴 실측 범위 밖의 판단이다.
2. `receive-from-etri` 는 **외부 기관(ETRI) 연동 입구**다. 막으면 연동이 끊긴다.
   옳은 답은 「막고 `INBOUND_KEY_ALLOWED` 에 키로 다시 여는 것」이고 그건 상대와의 약속이다.
3. 정적 판정을 두 겹으로 넓히는 것은 측정기 변경이고, 그 변경으로 나올 새 빨강을
   같은 턴에 닫을 수 없다 — 「못 잰 것을 0 으로 내지 않는다」.

→ **다음 턴 첫 일**. 게이트는 이 다섯을 래칫으로 붙들고 있다(늘면 exit 1).

## 8. 게이트가 새로 보는 것 둘

* **⑥ 탐침 방식** — 증거에 `probe_mode: "schema-passing-body"` 가 없으면 빨강.
  빈 본문으로 잰 옛 증거(=422 를 관문으로 세던 증거)로는 **초록을 못 낸다.**
  판정 규칙이 바뀌면 증거도 다시 떠야 한다.
* **⑦ 못 잰 자리** — 스키마를 맞춰 주고도 422 인 자리는 「막혔다」가 아니라 **「모른다」**다.
  빨강이 없고 이것만 있으면 **exit 2(회색)**. 0 으로 내지 않는다.

## 9. 손댄 파일

    scripts/probe_write_surface.py           스키마 통과 본문 · 여섯 갈래 · 쓰기 접두 판정
    scripts/verify_write_auth.py             세 수 첫 줄 · 관문 래칫 제외 · ⑥⑦ 추가
    backend/common/access_gate.py            이름 5 · 접두 2 · 판정 순서
    backend/common/front_line.py             앞단 접두 블록 · parse_gated_prefixes
    backend/tests/test_access_gate.py        세 번째 출생 표본 + 시험 7
    nginx/generated/gx-gate.conf             다시 만든 생성물(익명 401 26자리)
    docs/agent/evidence/D-368/write_surface.json         재측 증거
    docs/agent/evidence/D-368/writeauth_20260906_TI.json 이번 턴 첫 재측(수리 전) 원본
    docs/agent/evidence/D-368/write_auth_baseline.json   갈래가 바뀌어 다시 잠금
