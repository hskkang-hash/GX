# P-133 — **익명이 자료를 받던 5자리를 닫았다. 지금은 0자리다**

발행: 2026-09-11 · 턴 P · 차선 S · [실측]

---

## 한 줄

살아 있는 라우터의 **읽기 전수 331자리**를 **자격증명 없이** 불렀다.
착수 전 **5자리가 200 과 함께 자료를 돌려줬다** (합계 128,078 B).
우리 층 미들웨어 한 겹(`backend/common/access_gate.py`)으로 막은 뒤 **0자리**다.

| 칸 | 착수 전 | 착수 후 |
|---|---:|---:|
| **빨강** — 200 + 본문에 자료 | **5** | **0** |
| 초록 — 401/403 | 310 | 319 |
| 공개 설계 — 선언 + 사유 | 2 | 2 |
| 회색 — 못 쟀다 | 14 | 10 |
| **분모 [실측]** | **331** | **331** |

## 분모를 낸 명령 — 손으로 고른 목록이 아니다 (P-99)

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e GX_READ_BASE=http://localhost:8012 \
  -w /app gx-shell python /repo/scripts/probe_anon_read.py /app/_p133_anon_final.json
# → 익명 읽기 전수 331자리
```

`scripts/probe_anon_read.py` 는 이번에 만든 **익명 전용** 탐침이다.
`_iter_ninja_apis()` → `_routers` → `path_operations` → `operations` 전수를 돌고
거르는 것은 **읽기 메서드가 아닌 것 하나뿐**이다.

### 왜 `probe_read_surface.py` 를 그대로 안 썼나

그 탐침은 계정 **둘**(역할0 주인공 · admin 대조군)로 로그인한다. 이 제품은 계정당
동시 세션이 **하나**이고 턴 P 는 차선이 여럿이다 — 그 탐침을 돌리면 옆 차선의 토큰을
빼앗고, 빼앗긴 쪽이 받는 401 이 「관문이 섰다」로 세어져 **거짓 초록**이 된다
(D-350 · 턴 M 이 그렇게 거짓 초록 151자리를 냈다).

P-133 이 답해야 하는 질문은 하나다: **「자격증명 없이 부르면 자료가 나오는가.」**
그 질문에는 로그인이 필요 없다.

### 판정식은 베끼지 않았다 (D-212)

빨강 술어(`has_data`) · 칸 나누기(`classify`) · 공개 선언(`PUBLIC_READ_BY_DESIGN`) 은
`probe_read_surface` 에서 **import 한다**. 복사하면 언젠가 갈리고, 갈린 날 어느 쪽이
제품의 답인지 아무도 모른다.

### 대조군이 없어서 **못 가르는 것** — 정직하게 회색

「200 인데 비었다」가 **관문이 비운 것**인지 **이 환경에 행이 없는 것**인지는 admin
대조 없이 못 가른다 → 회색이다. 빨강(자료가 나갔다)은 대조군 없이도 확정된다.

---

## 착수 전 빨강 5자리 [실측 2026-09-11]

| 메서드 · 경로 | 상태 | 바이트 | 덩이 | 뷰 |
|---|---:|---:|---:|---|
| GET `/api/v1/auth/timezones` | 200 | 109,309 | 598 | `core.api.v1.auth.get_timezones` |
| GET `/api/config-management/list-optimized` | 200 | 16,436 | 12 | `core.configuration.api.list_configs_optimized` |
| GET `/api/v1/auth/groups` | 200 | 1,685 | 10 | `core.api.v1.auth.get_groups` |
| GET `/api/v1/auth/languages` | 200 | 466 | 3 | `core.api.v1.auth.get_languages` |
| GET `/api/register-settings` | 200 | 182 | 1 | `core.user.api.get_register_settings` |

**다섯 다 dj-core 안이다** — `/usr/local/lib/python3.11/site-packages/core/`.
§0.4 금지구역(읽기 전용)이라 라우트 선언에 `auth=` 를 못 붙인다.

### 어느 층에서 샜나

- `/api/v1/auth/{timezones,groups,languages}` — `AUTHN_SURFACE`(「인증 면은 비켜 준다」)
  라는 **넓은 규칙** 아래 숨어 있었다. `reset-password-for-user`(P-83) ·
  `otp/reset`(P-113) 과 **정확히 같은 모양의 사고**다.
- `/api/config-management/list-optimized` · `/api/register-settings` — 관문이
  **거부 목록(deny-list)** 이라, 이름이 오르지 않은 자리는 그대로 지나간다.

## 무엇을 했나 — **파일이 아니라 길목을 막았다** (D-348)

`backend/common/access_gate.py::AUTHN_REQUIRED_PATHS` 에 이름을 올렸다.
dj-core 도 `backend/delivery/` 도 **한 줄 안 바뀌었다.**
그 목록을 `backend/common/front_line.py` 가 읽어 앞단(nginx) 설정을 만든다 —
`nginx/generated/gx-gate.conf` 를 다시 생성했다(익명 401 **46자리**).

## 함께 닫은 **옆자리 셋** — 「비었으니 안전하다」가 아니다 (D-301)

| 경로 | 착수 전 | 왜 회색이었나 |
|---|---|---|
| GET `/api/v1/auth/departments` | 200 · 87 B `{"data": []}` | 이 환경의 그 표에 행이 없다 |
| GET `/api/v1/auth/positions` | 200 · 85 B `{"data": []}` | 〃 |
| GET `/api/v1/auth/teams` | 200 · 81 B `{"data": []}` | 〃 |

바로 옆 `/api/v1/auth/groups` 가 증거다 — 같은 컨트롤러 · 같은 모양인데 행이 10개라
**빨강**이었다. 부서·직위·팀 이름은 조직도이고, 조직도는 테넌트 자료다.
한 자리를 막고 옆자리를 열면 사고는 그대로다.

## 공개가 설계인 문은 **열어 두었다** — 음성 대조

```
GET /api/v1/health        200 ·  38 B   로드밸런서·감시기가 자격증명 없이 부른다
GET /api/v1/auth/csrf-token 200 · 144 B  토큰이 있어야 토큰을 받을 수 있으면 로그인할 수 없다
POST /api/v1/auth/login   (막지 않음)    이 문이 막히면 아무도 들어올 수 없다
```

전부 401 을 내는 관문은 방어선이 아니라 **벽**이고, 벽은 첫날 치워진다.

### 109KB 타임존을 「우리 층 정적 목록(1KB)」으로 갈음하지 않은 이유

**갈음할 수요가 없다.** `frontend/src` 전수 검색에서 다섯 경로 중 어느 것도
**한 번도 불리지 않는다**(히트 0). 로그인 화면이 로그인 전에 부르는 자리는
`/api/v1/auth/login` 하나다(`frontend/src/features/login/loginRequest.ts:22`).
언어 목록은 프런트 정적 자원(`src/i18n`)이 낸다.
수요가 생기는 날(예: 자가가입 화면이 생긴다) 그때 그 목록을 만들어 여는 쪽이 옳다.

---

## 남은 회색 10 — **닫지 않았다. 왜 남았는지 적는다**

| 경로 | 상태 | 무엇이 회색을 만드나 |
|---|---:|---|
| `/api/comment` · `/api/rating` | 400 | 질의값을 못 맞췄다. 그 뒤에 관문이 있는지 못 쟀다 |
| `/api/rating/featured` | 400 | ★ 아래 참조 — 10,727 B 짜리 오류 본문 |
| `/api/source/get-html` · `/api/source/get-url` | 404 | 그런 행이 없다. 관문은 못 쟀다 |
| `/api/topic` · `/api/topic/{topic_id}` · `/api/topic/slug/{topic_slug}` | 500 | 핸들러가 터진다 — 「터지니까 안전하다」는 관문이 아니다 |
| `/api/v1/auth/data-for-profile` | 500 | 〃 |
| `/api/v1/auth/otp/generate-qr` | 404 | 그런 행이 없다 |

열 자리 모두 **익명이 핸들러까지 닿는다.** 자료가 안 나가는 이유가 관문이 아니라
검증 실패·핸들러 오류다 — 그 오류가 고쳐지는 날 그 자리는 **열린 채로** 남는다
(`item-types`(D-364) · `get-drones-by-package-and-route-optimized`(P-83) 와 같은 모양).

### ★ 따로 등재할 것 — `/api/rating/featured` 가 **스키마를 통째로 뱉는다**

```
GET /api/rating/featured?featured=1   (익명)  → 400 · 10,727 B
{"error": "An unexpected error occurred: Cannot resolve keyword 'user_profile'
 into field. Choices are: accepted_handover_documents, account_locked_until,
 address_createdby, … "}
```

빨강 술어로는 **자료가 아니다**(2xx 가 아니다). 그러나 익명에게 사용자 모델의
**관계·필드 이름 전량**이 나간다 — 자료 반출이 아니라 **스키마 반출**이다.
P-133 의 범위(익명 자료 200)가 아니므로 **닫지 않았다.** 조율자 판단을 청한다.

---

## 되돌림

`common/access_gate.py::AUTHN_REQUIRED_PATHS` 에서 해당 줄을 뺀다(익명 개방으로
되돌아간다). 데이터도 스키마도 건드리지 않았다.

## 인증 사용자 회귀 0 의 근거

이 관문은 `_has_credentials(request)` 가 **거짓일 때만** 말한다(`Authorization` 헤더 ·
inbound 키 · 인증된 세션 중 하나라도 있으면 그대로 지나간다). 그러므로 이 여덟 줄이
인증 사용자의 200 을 건드릴 수 없다. `tests/test_p133_anon_read_closed.py::
GateIsSilentForCredentialBearingRequestsTest` 가 그것을 호출로 못박는다.

⚠ **인증된 전수 재측정은 이 턴에 하지 않았다** — 차선 S 는 이 턴에 로그인하지 않는다
(동시 세션 1개 · 옆 차선의 토큰을 빼앗지 않는다). 그 칸은 **회색이지 초록이 아니다.**

## 파일

- `anon_read_before.json` — 착수 전 전수 331자리 (빨강 5)
- `anon_read_after.json` — 착수 후 전수 331자리 (빨강 0)
