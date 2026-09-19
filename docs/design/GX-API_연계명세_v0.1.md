# GX-API 연계 명세 v0.1 — 외부 시스템(U6)이 읽는 한 장

- 발행: 2026-09-18 · WO-GX-20260915-01 파 3 턴 1 · 차선 **U56**
- 대상 독자: **기계**(외부 연계 App). 사람 화면의 문구는 여기 없다.
- 이 문서의 모든 코드·봉투는 **실측**이다 — Django 시험 클라이언트로 찍어 인용했다
  (`backend/tests/test_u56_turn_u_admin_surfaces.py`). 손으로 적은 봉투는 이틀 뒤
  거짓말이 된다(D-286). 봉투가 바뀌면 그 시험이 먼저 빨개진다.

---

## 0. 한 문장

우리 문은 **JWT(사람)** 또는 **들어오는 API 키(기계)** 로 열리고, 키는 **선언한
라우트에서만** 통과하며, 키가 무엇을 할 수 있는지는 **범위(scope)** 가 정한다.
선언하지 않은 것은 닫혀 있다 — **기본값이 거절이다.**

---

## 1. U6 여덟 행 — 순서대로

| # | 하는 일 | 문 | 지금 |
|---|---|---|---|
| 1 | API 키로 인증 | `POST /api/dsm/settings/api-keys`(발급 · 사람 자격) → 그 키로 `GET /api/dsm/events` | ● 발급·폐기·회전 · **범위(scope) 칸이 이번 턴에 섰다** |
| 2 | 이벤트 목록 조회 | `GET /api/dsm/events` | ● 키 200 · 익명 401 |
| 3 | 이벤트 상세 조회 | `GET /api/dsm/events/{id}` | ◐ **키는 거절 · JWT 만**(D-371 「의도된 절반」 — 상세는 `clip_path`·`address` 를 더 낸다) |
| 4 | 이벤트 발생 웹훅 수신 | `POST /api/dsm/settings/webhook-subscriptions/issue`(서명키 동시 발급) · 필터 `…/{id}/filters` | ● 구독 → 발송 → 서명 → 재시도 |
| 9 | 이벤트 상태 갱신 | `POST /api/dsm/events/{id}/response` · `…/review` | ◐ 외부 App 의 인증 경로(키/JWT)가 `authn_paths` 대장에 아직 없다 |
| 12 | 인증 실패 처리 | 아래 §4 오류 규약 | ◐ F-05 면은 진짜 4xx · 나머지 접두는 A2 작업 |
| 14 | 스키마 버전 확인 | 응답 헤더 `X-GX-Schema: 1.1` · `GET /api/dsm/health` 의 `schema` 칸 | ● |
| 15 | 연계 헬스체크 | `GET /api/dsm/health` — **인증 없음** · 200/503 | ● |

---

## 2. 인증 — 두 갈래, 하나의 기본값

```
Authorization: Bearer <JWT>        사람
X-API-Key: <키>                    기계 (또는 Authorization: apikey <키>)
```

- **키는 선언한 라우트에서만 통과한다.** 라우트가 `inbound_key=True` 를 선언하지
  않았으면 키를 들고 온 요청은 **401** 이다(200 도 403 도 아니다 — 그 문은 키에게
  존재하지 않는다). `backend/common/inbound_api_key.py` 가 그 한 겹이다.
- **쓰기 메서드에는 키를 열지 않는다**(읽기 전용부터 · D-335 ③).
- **HTTPS 가 아니면 키를 거절한다**(운영 기본값 · `INBOUND_API_KEY_REQUIRE_HTTPS`).
- 키 값은 **발급 응답에 한 번만** 나온다. 저장소는 sha256 해시만 갖는다 —
  잃어버리면 되찾기가 없고 **회전**만 있다.

---

## 3. 키의 범위(scope) — API-03·04 [이번 턴 신설]

이름은 **넷뿐이다.** 정본은 `backend/kernels/k5_trust/key_scopes.py` 하나다.

| 이름 | 무엇을 여는가 | 경로 접두 |
|---|---|---|
| `events:read` | 사건 목록·상세 | `/api/dsm/events` |
| `pulse:read` | 카메라 맥박 | `/api/dsm/cameras/pulse` |
| `stats:read` | 통계·반출 | `/api/dsm/stats` |
| `webhooks:manage` | 구독·필터 | `/api/dsm/webhook-subscriptions` · `/api/dsm/settings/webhook-subscriptions` |

발급:

```
POST /api/dsm/settings/api-keys?name=<이름>&scopes=events%3Aread%2Cstats%3Aread
→ 200 {"key_id": 12, "name": "...", "prefix": "...", "secret": "<한 번만>",
       "scopes": ["events:read", "stats:read"], "audit_id": 991}
```

- `scopes` 를 **안 주면 기본은 `["events:read"]` 하나**다. 기본을 전부로 두면
  D-335 가 잡은 「범위 없이 이미 열어 두었다」가 그대로 돌아온다.
- 모르는 이름은 **422** 다 — 조용히 버리면 발급자는 준 줄 알고 상대는 못 쓴다.
- 조회·변경: `GET|POST /api/dsm/settings/api-keys/{key_id}/scopes`
  (`state: "unset"` 은 「아직 정한 적 없다」이고 `scopes: []` 는 「아무 데도 못
  간다」다 — **둘은 다른 사실이다**).
- 범위 밖 호출은 **403** 이다(401 이 아니다 — 인증은 성했고 권한이 없다).

### 3.1 범위 밖 = 403 — **HTTP 로 잰 수** [실측 2026-09-18 · 턴 V]

같은 문(`GET /api/dsm/events`)을 세 가지 키로 눌렀다. **분모를 함께 둔다** — 범위를
가진 키가 200 을 받지 못하면 아래 403 은 「막았다」가 아니라 「문이 죽었다」이다.

| 키의 범위 | `GET /api/dsm/events` | 본문 |
|---|---|---|
| `events:read` (범위 안) | **200** | 목록 |
| `stats:read` (범위 밖) | **403** | `{"detail": "이 키에는 범위 events:read 가 없습니다 — 지금 가진 범위: stats:read"}` |
| 정한 적 없음(옛 키 · `state: "unset"`) | **403** | `{"detail": "이 키에는 범위 events:read 가 없습니다 — 지금 가진 범위: 없음"}` |

`nginx:8500` 과 `gunicorn:8000` **두 출처에서 같은 수**가 나왔다(캐시가 덮지 않았다).
재현: `scripts/probe_key_scope_http.py` · 시험
`backend/tests/test_u56_turn_u_admin_surfaces.py::TurnVKeyScopeOverHttpTest`.

> ⚠ **턴 U 의 기록을 정정한다.** 턴 U 는 「`stats`·`pulse` 가 `inbound_key=True` 를
> 선언하지 않아서 403 이 안 보인다」고 적었다. 맞는 말이지만 **원인이 하나 더 있었고
> 그쪽이 먼저였다**: `assert_path_scope` 를 부르는 **HTTP 자리가 저장소에 0곳**이었다.
> 판정식은 서 있었고 **아무도 부르지 않았다.** 그 자리를 이번 턴에 세웠다
> (`backend/common/inbound_api_key.py` — `key_scopes.py` 머리말이 지정한 그 자리).

> ⚠ **남은 한계 [실측 2026-09-18]** — `/api/dsm/stats/*` 와 `/api/dsm/cameras/pulse` 는
> 아직 `inbound_key=True` 를 선언하지 않았다. 그래서 **키로 부르면 403 이 아니라 401**
> 이다(문 자체가 키에게 안 열려 있다). 「범위가 없다」가 아니라 **「그 문이 아직 키에게
> 없다」**이다 — 둘을 뭉치지 않는다. 그 두 문은 U24·U3 소유라 이 차선이 안 고친다
> (등록 요청 · 파 3 턴 2 보고 ③).

---

## 4. 오류 규약 — 401 / 403 / 404 / 422

**봉투는 넷 다 같다** [실측 · `test_error_envelopes_are_recorded_for_the_spec`]:

```json
{"detail": "한국어 한 줄"}
```

칸 이름이 갈래마다 다르면 외부 App 이 갈래마다 파서를 둔다. 그래서 같게 두고,
시험이 그 동일성을 잰다.

| 코드 | 뜻 | 예 |
|---|---|---|
| **401** | 자격이 **없다** | 익명 호출 · 선언 안 한 라우트에 키를 들고 옴 · 만료·폐기된 키 |
| **403** | 자격은 있고 **권한이 없다** | 관리자가 아닌 사람이 설정 문을 부름 · 키가 **범위 밖**을 부름 |
| **404** | **없다**(남의 것도 없는 것이다) | 남의 테넌트 카메라 id · 남의 키 id — 403 을 내면 「있다」가 샌다(D-269) |
| **422** | 값이 **틀렸다** | 빈 주소 · 빈 사유 · 모르는 범위 이름 · 질의 인자 누락(`loc: ["query", …]`) |

추가로 쓰는 코드:

- **400** 요청이 틀렸다(JSON 이 아님 · 모르는 필터 키)
- **409** 지금 상태에서 할 수 없다(심각 수신자 0명 저장 · `NoRecipients`)
- **501** 그 기능을 **아직 구현하지 않았다**(`GET /settings/{domain}` 의 모르는 영역)
- **503** 살아 있지 않다(`/health` 의 검사 하나라도 실패)

---

## 5. 스키마 버전 — `X-GX-Schema`

- 모든 응답에 헤더 `X-GX-Schema: 1.1` 이 실린다. 외부 App 은 **이 헤더로** 계약
  세대를 가른다 — 본문의 칸 유무로 추측하지 않는다.
- `GET /api/dsm/health` 의 본문에도 `schema` 칸이 같은 값으로 있다(헤더를 못 읽는
  중계기 뒤에서도 읽히도록).

---

## 6. 헬스체크 — `GET /api/dsm/health`

**자격증명 없이 200.** 로드밸런서·감시기가 부른다.

```
200 {"status": "ok",  "schema": "1.1",
     "checks": {"db": "ok", "cache": "ok", "queue": "ok"}, "failed": []}
503 {"status": "fail", "schema": "1.1",
     "checks": {"db": "fail", ...}, "failed": ["db"]}
```

- 나가는 것은 **상태 이름뿐**이다 — 예외 문장·호스트명·포트·버전이 없다. 열린
  문으로 나가는 글자는 전부 정찰 자료다.
- 검사 하나라도 죽으면 **503** 이다. 200 으로 삼키면 감시기가 못 본다.
- `Cache-Control: no-store` — 캐시된 초록이 죽은 서버를 덮지 않는다.

---

## 7. OpenAPI

- `GET /api/dsm/openapi.json`(ninja 기본 경로 규약).
- `components.schemas` **11** [실측 2026-09-18 · 턴 V · 턴 U 에는 3, 그 전에는 0]. 이 저장소의 dsm
  라우트는 인자를 원시 타입으로 받고 응답을 `dict` 로 내므로 모양이 하나도 없었다.
  모양이 없으면 외부 App 은 「200 이 온다」밖에 못 읽고, 그 상태의 명세는 명세가
  아니다. `StorageOut`(저장 용량 응답)이 그 0 을 깼다 —
  `backend/tests/test_u56_turn_u_admin_surfaces.py::test_openapi_has_at_least_one_component_schema`
  가 그 수를 지킨다.
- **응답까지 선언된 문 7 / 108** [실측 2026-09-18]. 턴 V 에 U5·U6 문 여섯이 더해졌다:
  `POST /cameras/{id}/address` · `POST /system/restart-request` · `GET /system/requests` ·
  `GET /system/backup-receipts` · `GET|POST /settings/api-keys/{id}/scopes`.
  **101 은 아직 「200 이 온다」밖에 못 읽는다** — 그 수를 줄이지 않고 적어 둔다.

---

## 8. 이번 턴에 태어난 관리자 면(U5) — 기계도 읽을 수 있다

| 문 | 내는 것 | 비고 |
|---|---|---|
| `POST /api/dsm/cameras/{id}/address` | 한 대의 설치 주소 | 관리자만 · 남의 것 404 · 빈 주소 422 · 감사 1행 |
| `POST /api/dsm/system/restart-request` | **요청 기록** | ⚠ **서버를 내리지 않는다.** `executed` 는 언제나 거짓 |
| `GET /api/dsm/system/requests` | 요청 목록 | 테넌트 격리 |
| `GET /api/dsm/system/backup-receipts` | 마지막 회수증·검증 가능 여부·다음 예정 | 못 찾으면 `verdict: "UNKNOWN"` — **0 을 초록으로 적지 않는다** |
| `GET /api/dsm/system/storage` | 상한·사용량·% | 상한 미선언이면 `used_pct: null` 과 **그 이유 한 문장** |

---

## 9. 바뀌면 빨개지는 자리 (P-171)

이 문서의 규약을 바꾸는 차선은 **같은 커밋에** 아래를 갱신한다.

- `backend/tests/test_u56_turn_u_admin_surfaces.py` — 오류 봉투 · 범위 · OpenAPI 수
- `backend/tests/test_u56_schema_header.py` — `X-GX-Schema`
- `backend/tests/test_u56_health.py` — `/health` 200/503
- `backend/tests/test_tenant_isolation.py` · `backend/tests/tenant_census.py` — 새 표
- `backend/tests/test_f05_event_api.py::EVENT_ENTRY_SURFACE` — 새 진입면(차선 F 소유)
- `scripts/verify_write_auth.py` — 새 쓰기 면의 자격
