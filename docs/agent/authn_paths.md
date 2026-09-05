# 인증 경로 대장 — 면마다 어느 문으로 들어가는가 (P-15)

**작성 2026-09-18 · 확정 2026-09-19** · 판정 `scripts/verify_authn_paths.py` · 근거는 전부 [실측]

> **2026-09-19 확정 (지시서 판정 2 · 판정 3):** `/api/token/pair` 를 **뺐다**(§2 · D-411).
> §3 의 405 넷은 **고쳤다**(§3 · D-410) — 넷 다 도달한다. 아래 표들은 그 뒤의 실측이다.

> 게이트는 다른 길로 들어갔다. **그러면 실제 클라이언트는 어느 길로 들어가나?**
> 모바일 M1~M3 는 로그인이 첫 화면이다. **죽은 인증 길 위에 화면을 세우지 않는다.**

---

## 0. 「토큰」이라 불리는 것이 셋이다 — 셋은 다른 것이다 (동음이의 · D-337)

| 이름 | 무엇인가 | 누가 주나 | 누가 받나 |
|---|---|---|---|
| ~~**JWT(pair)**~~ | 서명된 접근 토큰 | ~~`/api/token/pair`~~ **제거됨(404 · D-411)** | ★ 세션이 있을 때만이었다 — 스스로는 못 세웠다 |
| **user.token** | DB 에 심는 세션 표식 | `/api/v1/auth/login` | dj-core `CustomJWTAuth` 가 **이것을 본다** |
| **api_key** | 외부 App 이 들고 오는 비밀 | `POST /api/dsm/settings/api-keys` | 선언한 라우트만 (`X-API-Key`) |

한 이름으로 부르면 **「토큰을 받았다」가 「들어갈 수 있다」로 읽힌다.**
2026-09-17 에 게이트가 정확히 그 착각으로 초록을 냈다 — 26건 중 **24건이 401** 인 채로.

`core/auth.py:38` 이 그 갈림의 전부다:

```python
user = User.objects.filter(id=user_id).first()
if not user.token:                       # ← JWT 는 멀쩡한데 여기서 죽는다
    raise HttpError(401, "Token expired")
```

### ★ 그리고 이 대장의 첫 판이 틀렸다 — 판정기가 잡았다

처음엔 「pair 토큰은 어디서도 401」이라 적었다. 판정기를 돌리니 **200** 이었다.
한 갈래를 더 재고서야 규칙이 보였다:

| `user.token`(세션) | pair 토큰으로 `/api/dsm/events` |
|---|---|
| **없음** | **401** |
| **있음** | **200** |

즉 이 문은 **죽은 것이 아니라 남이 세운 세션에 기생한다.** 스스로는 못 세운다.
`tests/test_api_contract.py` 의 계약 시험이 참인 것도 그 setUp 이 로그인을 하지 않기
때문이다 — **시험은 옳았고, 문장이 너무 넓었다.**

> **한 갈래만 재면 어느 쪽이든 그럴듯하다.** 2026-09-17 의 401 도, 오늘의 200 도
> 각각은 사실이었다. 규칙은 **두 갈래를 함께 재야** 나온다.

★ 그리고 **이 자리는 이미 저장소에 적혀 있었다.**
`tests/test_api_contract.py::test_token_pair_issues_tokens_that_do_not_work` 가
「200 으로 토큰을 준다. 그리고 그 토큰은 쓸 수 없다」를 못박아 두고 있었다(W0-18).
그런데 **도구는 그 문으로 걸어 들어갔다.**
**저장소가 아는 것과 도구가 아는 것은 다른 것이다** — 그래서 이 대장이 있다.

---

## 1. 면별 대장 [실측 2026-09-18]

| 면 | 어느 인증으로 들어가나 | 실측 | 근거 경로 |
|---|---|---|---|
| **웹 UI (SPA)** | `POST /api/v1/auth/login` → `user.token` + JWT | **200** | 빌드 번들에 `/api/v1/auth/login`·`/api/v1/auth/refresh-token` 만 있고 `/api/token/pair` **0건** (`backend/_fe_dist/assets/*.js`) |
| **모바일 M1~M3** | 같은 문 — 화면은 이미 있고 같은 `loginAPI` 를 쓴다 | **미착수** | `frontend/src/features/LoginMobile/LoginMobile.tsx` (`loginAPI(username, password, end_previous_session)`) |
| **외부 API U6** | `X-API-Key` — 선언한 라우트에서만 | ★ **발급 문이 도달 불가** | `common/inbound_api_key.py:66` · `apps/dsm/api.py:135` (§3) |
| **게이트·판정기** | `POST /api/v1/auth/login` (`end_previous_session:true`) | **200** | `scripts/verify_route_alive.py::LOGIN_PATHS` |
| **시드** | HTTP 를 안 쓴다 — 서비스 함수를 직접 부른다 | 해당 없음 | `stream_monitors/management/commands/seed_dsm_events.py` |
| **화면 캡처 시험** | `/api/token/pair` → `/api/v1/auth/logout` (강제 로그아웃) | **200 · 실제로 지워진다** | `tests/test_screens_browser.py::_force_logout` (§4) |

### 로그인 한 번에 필요한 것 — `end_previous_session`

제품은 **동시 접속 1개**다. 이 칸이 없으면 앞선 세션 때문에
**HTTP 200 · `success:false`** 가 온다(토큰 없음) — 조용한 성공이다.

```json
{"username": "...", "password": "...", "end_previous_session": true}
```

---

## 2. `/api/token/pair` 처분 — **뺐다** [D-411 · 승인 세종 2026-09-19]

**㉰ 제거. 시행 완료 · [실측] `POST /api/token/pair` → 404.**

| 물음 | 실측 |
|---|---|
| 실제 클라이언트가 쓰는가 | **아니다.** 빌드 번들 21파일에 0건 |
| 쓰는데 거절되는가 | 세션이 없으면 401 · 있으면 200 — **스스로는 못 들어간다** |
| 우리가 등록했는가 | 아니다 — dj-core(ninja_jwt)가 들고 온다. §0.4 라 **그 파일은 못 고친다**(D-207) |

★ 위험의 모양이 「죽은 문」이 아니라 **「기생하는 문」**이었다는 것이 처분을 정했다:
누군가 로그인해 세션이 살아 있는 동안에는, 아이디·비밀번호를 아는 쪽이 이 문으로
**세션 관리 규약(동시 접속 1개)을 우회한 토큰을 더 찍어 낼 수 있다.**
쓸모없는 토큰을 내주는 문은 기능이 아니라 **공격 면**이다.

### 어떻게 뺐나 — **dj-core 는 한 줄도 안 고쳤다**

라우트는 `core.urls`(금지구역) 안에 그대로 살아 있다. 우리는 `config/urls.py` 에서
`include("core.urls")` **앞에** 같은 경로를 놓아 404 를 낸다 — Django 는 먼저 등록된
패턴에서 멈춘다.

```python
path("api/token/pair", _gone),          # ← core.urls 보다 먼저
path("api/", include("core.urls")),
```

> ⚠ **순서가 곧 판정이다.** 저 줄이 한 칸만 내려가면 문은 **소리 없이 다시 열린다.**
> 그래서 그 순간을 보는 것을 둘로 뒀다:
> `tests/test_api_contract.py::test_token_pair_is_gone` (404 부작위 · D-300) 과
> `scripts/verify_authn_paths.py` (익명 POST → 404 기대).

### 함께 옮긴 것 · 함께 뺀 것

- 저장소 안 유일한 사용처였던 `tests/test_screens_browser.py::_release_session` 을
  `/api/v1/auth/login`(`end_previous_session:true`)으로 옮겼다.
  **없어도 되는 우회였다** — 로그인 자신이 앞선 세션을 닫는다.
- ★ **`PUBLIC_ROUTES` 의 줄은 뺐다가 되돌렸다 — Code 오판 1건.**
  「없어진 문의 면제를 남기지 않는다」고 뺐더니 미분류 라우트가 **648 → 649** 로 늘었다
  (`test_route_tenant_scope` 가 잡았다). 라우트는 URLconf 에서 **사라지지 않았다** —
  `core.urls` 안에 그대로 있고 우리는 앞에 404 문을 세워 가리고 있을 뿐이다.
  등재를 지우면 그 자리는 「판정이 끝난 것」에서 **「아직 아무도 안 본 것」**이 된다.
  **빚을 갚은 것이 아니라 빚을 안 보이게 한 것**이었다. 사유를 바꿔 되돌렸다:
  「제거된 문 — 404 만 낸다. 아무것도 내주지 않으므로 인증이 필요 없다」.
- ⚠ `token/refresh` · `token/verify` 는 **건드리지 않았다.** 이번에 잰 것은 `pair`
  하나이고, 재지 않은 것을 함께 닫으면 그 순간 이 결정이 추측이 된다(D-301).

### 시험을 고쳐 초록을 만든 것이 아니다

앞판의 계약 시험(`test_token_pair_issues_tokens_that_do_not_work`)은 **그날의 사실이었고
옳았다.** 바뀐 것은 시험이 아니라 **계약**이다 — 세종이 제거를 승인했고, 사유와 함께
결정 대장(D-411)에 남았다. 계약이 바뀌면 시험도 바뀐다. 바뀌지 않는 것은
**계약을 시험이 정하지 않는다**는 것이다(D-327).

---

## 3. ★ 외부 API U6 — 키를 발급할 문이 도달 불가였다 → **고쳤다** [D-410]

`POST /api/dsm/settings/api-keys` 를 때리면 **405 · `Allow: GET`** 이다.

원인: 같은 컨트롤러의 `@route.get("/settings/{domain}")` 이 **먼저 선언되어**
`settings/<한 단>` 을 통째로 먹는다. Django 는 첫 일치에서 멈추고, 그 뷰는 GET 만 안다.

같은 이유로 넷이 함께 막혀 있다:

| 메서드 | 경로 | 계약 | 09-18 | **09-19 고친 뒤** |
|---|---|---|---|---|
| POST | `/api/dsm/settings/api-keys` | F-05 API Key 발급 | 405 | **422** (검증이 돌았다 · 도달) |
| POST | `/api/dsm/settings/thresholds` | F-12 임계값 | 405 | **422** |
| POST | `/api/dsm/settings/zones` | F-12 구역 | 405 | **422** |
| POST | `/api/dsm/settings/grade-rules` | F-12 등급규칙 | 405 | **422** |

GET 여섯 도메인은 **그대로다**: `thresholds`·`zones`·`recipients`·`widgets`·
`api_keys`·`grade_rules` 전부 403(문지기) · 없는 이름은 501. 한 갈래만 바뀌었다 —
`GET /settings/api-keys`·`grade-rules`(**하이픈**)가 501 → **405** 다. 그 둘은 애초에
설정 영역 이름이 아니었고(영역은 밑줄 `api_keys`·`grade_rules`), 이제 그 경로는
**POST 전용**이므로 405 가 더 정확한 대답이다.

두 단짜리 형제는 멀쩡하다 — `DELETE /settings/api-keys/{id}` **403**,
`POST /settings/api-keys/{id}/rotate` **403** (문지기가 선 것이지 죽은 것이 아니다).

### 왜 여태 안 보였나

**단위 시험은 서비스 함수를 직접 부른다.** `verify_contract_ac.py` 도 절마다 그 시험을
가리키므로 넷 다 초록이었다. D-386 이 이름 붙인 층이 정확히 여기다 —

> 단위 시험은 **함수를 부른다.** 브라우저는 **라우트를 때린다.**

그리고 `route-alive` 는 **화면이 실제로 부른 GET** 만 때린다. 이 넷은 쓰기 면이고,
화면이 아직 안 부른다. **양쪽 눈의 사각이 정확히 겹친 자리**다.

### 처분 — ㉮ 를 골랐다. 그러나 순서만으로는 반이었다

지시서 판정 3 이 「순서를 바꾸거나 `{domain}` 을 좁혀라」로 정했다. 재어 보니
**둘 다 단독으로는 안 됐다:**

```
㉮ 선언 순서만 바꾼다   → POST 는 살고 **GET /settings/thresholds·zones 가 405** 가 된다
㉯ {domain} 을 좁힌다   → thresholds·zones 는 **영역 이름이면서 동시에 쓰기 경로**다.
                          좁혀도 같은 경로 문자열이라 여전히 한쪽만 산다
```

한 경로 = 한 `PathView` 이므로, **GET 과 POST 를 같은 문에 함께 세우는 것**이
둘 다 사는 유일한 배선이다:

1. 리터럴 쓰기 경로 넷을 `{domain}` **앞으로** 옮겼다
2. 겹치는 둘(`thresholds`·`zones`)에는 **같은 리터럴 경로에 GET 을 붙였다** —
   같은 핸들러(`_setting_overview`) · 같은 문지기 · 같은 응답
3. `{domain}` 은 **맨 뒤**에 선다. 나머지 네 영역(`recipients`·`widgets`·`api_keys`·
   `grade_rules`)을 그대로 받는다

라우트 계약 문서는 **무변경**이다 — 문서가 옳았고 배선이 틀렸다.

★ `EVENT_ENTRY_SURFACE` 에 두 줄이 늘었지만 **진입면이 넓어진 것이 아니다.**
같은 문이 제 이름으로 다시 걸린 것이다. 그 사유를 등재부에 함께 적었다.

### 그리고 세 번째 눈을 세웠다 — `verify_contract_route_reach.py`

이 자리가 숨어 있던 이유는 도구 둘의 사각이 **정확히 겹쳤기** 때문이다. 그 사이를
보는 판정기를 만들었다: **선언된 계약 진입면의 (method, path) 마다 자격증명 있이
한 번씩 문을 두드린다.** 405 는 언제나 실패다.

돌리자마자 **아무도 안 보던 자리 둘**을 더 잡았다:

| 라우트 | 실측 | 원인 |
|---|---|---|
| `GET /api/dsm/reports/templates` | **500** | `TemplateView` 에 없는 칸 `renderer` 를 App 이 읽었다 |
| `POST /api/dsm/events/{id}/notify` | **500** | 「그런 이벤트가 없다」를 **서버 결함**으로 냈다 |

둘 다 고쳤다(200 · 404). 뒤엣것은 K2 에 좁은 갈래 `EventNotFound` 를 파서
404 / 409(수신자 0명) / 400(그 밖)으로 **갈라 냈다** — 셋을 뭉치면 U6 은 자기 잘못인지
우리 잘못인지 모른다.

**계약 진입면 20건 전부 도달 · 못 닿음 0 · 못 잼 0** [실측 2026-09-19].
래칫 기준선을 **4 → 0** 으로 조였다(D-311) — 갚은 빚은 기준선에서 내려야 하고,
안 내리면 그 자리가 다시 썩어도 초록이 난다.

---

## 4. `/api/v1/auth/logout` — 문 하나가 느슨하다 [실측]

`@router.post("/logout")` 에는 **`auth=` 가 없다.** 사용자는 미들웨어가 붙인 것으로 판정한다
(`get_authenticated_user_from_request`). 그래서:

| | 결과 |
|---|---|
| 익명(헤더 없음) | **401** — 안전하다 |
| ~~`/api/token/pair` 토큰~~ | 그랬다 — **그 문이 없어져 이 갈래도 없다**(D-411) |

즉 **다른 모든 라우트가 거절하는 토큰을 이 문만 받는다.** dj-core 자산이라 고치지 않는다.

★ 이것을 재기 전 가설은 「`_force_logout` 은 성공이라 말하고 아무 일도 안 할 것」이었다.
  **측정이 그 가설을 뒤집었다** — 실제로 지워진다. 적어 두는 이유는, 다음 사람이 같은
  의심을 할 때 **다시 재지 않아도 되게** 하기 위해서다(D-280 — 수는 원인을 말하지 않는다).

---

## 5. 모바일 M1~M3 이 설 자리 — 문은 하나다

- 로그인은 **`/api/v1/auth/login` 하나**로만 한다. `end_previous_session` 을 함께 보낸다.
- 화면은 이미 있다: `frontend/src/features/LoginMobile/LoginMobile.tsx` —
  **다시 만들지 않는다**(D-333 ④). 붙일 것은 M1~M3 의 나머지다.
- 무계정 링크 금지는 그대로.
- ⚠ 외부 API 키가 필요한 모바일 기능이 생기면 §3 이 먼저 풀려야 한다 —
  **지금은 키를 HTTP 로 발급할 수 없다.**

---

## 6. 강제 도구

```
python scripts/verify_authn_paths.py
```

- 웹 UI 면: 번들이 부르는 주소를 **읽어서** 판정한다 — 손으로 적지 않는다.
  화면이 `/api/token/pair` 를 부르기 시작하면 그 자리에서 빨개진다(**죽은 문 위의 화면**).
- 제품 로그인 면: 받은 토큰으로 실제 라우트를 때려 **들어가지는지**까지 본다.
- 제거한 문: `/api/token/pair` 를 **익명으로** 때려 404 인지 본다(D-411).
  401 이 아니라 404 여야 한다 — 401 이면 연동 담당자가 계정을 고치려 든다.
  다시 열리면 그 자리에서 빨개진다: `config/urls.py` 의 차단 줄이 내려간 것이다.
  ★ 「기생하는 문」을 두 갈래로 재던 갈래는 **문이 없어져 함께 없어졌다.**
  그 교훈(**한 갈래만 재면 어느 쪽이든 그럴듯하다**)은 주석으로 남겼다.
- 도달 불가 쓰기 면: 넷을 세고 **기준선 0 을 넘으면 빨개진다**(래칫 D-311).
- ★ 그리고 이제 **세 번째 눈**이 따로 선다: `scripts/verify_contract_route_reach.py` —
  선언된 계약 진입면 전수를 method+path 로 두드린다.

---

## 7. 동음이의 기준선 한 줄이 늘었다 — 사유 (D-337)

`verify_homonyms` 가 이 판정기의 수식어 없는 `api_key` 를 잡았다. 둘이었고 하나는 고쳤다:

- 판정기 머리말의 설명어 → **`inbound_api_key`** 로 바꿨다(방향을 이름에 붙인다).
- 남은 하나는 `("POST", "/api/dsm/settings/api-keys")` — **제품의 실제 URL** 이다.
  이름을 바꾸면 때릴 자리가 달라진다. 그래서 `--freeze` 로 기준선에 올렸다(+1).

기준선 파일은 손으로 고치지 않는다(도구가 만든다). **사유는 여기 남긴다** —
다음에 그 한 줄을 보는 사람이 「왜 예외인가」를 여기서 읽게.

### 2026-09-05 턴 F — 기준선 146 → 150 (+4) · 사유

`backend/tests/test_s_wall_token.py` 의 쓰기 탐침 목록이 수식어 없는 `api_key` 를 넷 썼다.
넷 다 **제품의 실제 URL 문자열**이다:

```
("POST",   "/api/dsm/settings/api-keys")          ("DELETE", "/api/dsm/settings/api-keys/1")
("POST",   "/api/dsm/settings/api-keys/1/rotate") ("GET",    "/api/dsm/settings/api_keys")
```

이름을 바꾸면 **두드릴 자리가 달라진다** — 그러면 이 시험은 있지도 않은 문을 두드리고
초록이 된다. §7 이 이미 같은 판정을 한 자리(하이픈 URL 과 밑줄 영역 이름이 다른 것,
그 다름이 §3 의 절반이다)와 정확히 같은 이유다. `--freeze` 로 올렸다.

★ 여기 남는 것은 「바꾸면 안 되는 자리라서 얼렸다」는 **판정**이지 「혼동이 없다」는
주장이 아니다.

### 2026-09-19 — 기준선 139 → 142 (+3) · 사유

새 판정기 `scripts/verify_contract_route_reach.py` 가 수식어 없는 `api_key` 를 셋 썼다.
셋 다 **제품의 실제 문자열**이라 이름을 바꾸면 **두드릴 자리가 달라진다**:

| 자리 | 무엇인가 |
|---|---|
| 머리말 인용 | `POST /api/dsm/settings/{api-keys,…}` — 이 도구가 태어난 그날의 405 넷 |
| 출생 표본 | `("POST", "/api/dsm/settings/api-keys", 405)` — 실제 URL |
| 자기시험 | `"api_keys"` — F-12 **설정 영역 이름**(밑줄). 하이픈 URL 과 다른 것이고, 그 다름이 §3 의 절반이다 |

★ 이름을 못 바꾸는 것과 이름이 옳은 것은 다르다. 여기 남는 것은 「바꾸면 안 되는
자리라서 얼렸다」는 **판정**이지 「혼동이 없다」는 주장이 아니다.

---

## 8. UX-24 동시 세션 상한 — **새 문이 아니다. 있는 문 위의 정책이다** (2026-09-05 턴 E · 차선 S)

★ **이 행을 먼저 쓰고 짓는다** (P-15 · 지시서 §4 함정 ③). 죽은 인증 길 위에 화면을
얹지 않기 위해서다. 아래는 전부 [실측]이고, **못 잰 것은 「판정 불가」라고 적었다.**

| 면 | 어느 인증으로 들어가나 | 실측 | 근거 경로 |
|---|---|---|---|
| **월 모드 대형 화면** | `POST /api/v1/auth/login` — **같은 문** | 문 200 · **동시성 판정 불가** | `frontend/src/features/dsm/pages/Wall.tsx` 는 앞단 라우트다. 서버 문은 하나다 |
| **자리 데스크톱** | 같은 문 | 같음 | — |
| **이동 중 휴대전화 M1~M3** | 같은 문 (`LoginMobile.tsx`) | 같음 | §1 표와 동일 |

**새 인증 경로는 0 개다.** 상한은 로그인 문 **뒤**에 붙는 정책이고, 우리 층 미들웨어
`common/session_limit.py` 가 그 자리다.

### 8-1. `end_previous_session` 이 어디서 도는가 — **dj-core 안이다 (§0.4)**

| 무엇 | 자리 | 하는 일 |
|---|---|---|
| 요청 칸 | `core/api/v1/schemas.py:20` | `end_previous_session: bool = False` |
| 거절 갈래 | `core/api/v1/auth.py:630` | 칸이 **거짓**이고 앞선 세션이 있으면 **200 · `success:false`** — 토큰을 안 준다 |
| 축출 갈래 | `core/api/v1/auth.py:693` | 칸이 **참**이면 그 사용자의 `OutstandingToken` 을 **전부** 블랙리스트 |
| 세션 심기 | `core/api/v1/auth.py:706·725` | `session_id = uuid4()` → `user.set_encrypted_session_token(session_id, access_jti)` |
| 세션 대조 | `core/auth.py:31·51·63` | 토큰의 `session_id` ≠ `user.token` 의 `session_id` → **401 `"Token from different session"`** |
| 저장 자리 | `core/user/models.py:577` | `user.token = enc("<session_id>:<access_jti>")` — **한 벌만 들어간다** |

★ **동시 접속 1개는 설정이 아니라 자료구조다.** `user.token` 은 CharField 한 칸이고
세션을 하나만 담는다. 로그인은 그 칸을 **덮어쓴다.** 그러므로 두 기기가 동시에 사는 길은
둘 중 하나뿐이고 **둘 다 §0.4 안이다**:
`core/auth.py` 의 대조를 고치거나, `user.token` 을 여러 벌로 바꾸거나.

### 8-2. 그래서 우리 층은 무엇을 얹었나 — **셋을 얹고 하나는 판정 불가**

| | 얹었나 | 자리 |
|---|---|---|
| 역할별 상한 표 (U1 3 · U2 3 · U4 2 · U5 2) | **얹었다** | `common/session_limit.py::cap_for_user` — 역할 코드는 `config/k3_roles` 한 곳이 답한다(D-369) |
| 월 모드 세션 12시간 | **얹었다** | 같은 파일 `WALL_MODE_SESSION_TTL` · **토큰 수명은 안 늘렸다**(§8-3) |
| 초과 시 **가장 오래된 세션**을 끊는다 | **얹었다** (순수 함수 `admit`) | 같은 파일 — 대장은 캐시, 시험은 순수 함수로 잰다 |
| 끊긴 화면에 안내 한 줄 | **얹었다** (서버가 말한다) | `SessionLimitMiddleware` 가 dj-core 의 401 `"Token from different session"` 을 사전 문구로 바꾼다 |
| **실제로 2대가 동시에 산다** | **판정 불가** | 위 8-1. 우리 층에서 얹을 수 있는 자리가 없다 — **지어내지 않는다** |

⚠ **조율자 배선 필요 1**: 서버는 이제 사전 문구를 401 본문(`detail`)에 싣는다. 그 글자가
사람에게 닿으려면 앞단이 `detail` 을 그려야 한다. `frontend/` 는 차선 S 의 것이 아니다.

### 8-3. 토큰 수명 — **한 값도 안 바꿨다** [실측]

`NINJA_JWT` 접근 200분 · 재발급 7일 · 회전 켜짐 그대로다. 월 모드 12시간이 그 값을
요구하는지부터 쟀다: **요구하지 않는다.** 12시간 > 200분이지만 재발급(7일)과 회전이
그 사이를 잇는다 — 앞단이 실제로 재발급을 부르는 것은 `UX-16/session_12h.md` 가
번들에서 확인해 두었다. 접근 토큰을 720분으로 올리면 월 모드 한 장을 위해
**제품 전체의 탈취 창**이 3.3시간에서 12시간으로 넓어진다. 그것은 이 절이 아니라 보안 결정이다.
`tests/test_s_session_limit.py::test_token_lifetime_unchanged` 가 이 세 값을 못박는다.

### 8-4. 강제 도구

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  DB_TEST_NAME=test_gx_sec python -m pytest tests/test_s_session_limit.py -q \
  --nomigrations -p no:randomly --tb=short 2>/dev/null'
```

`tests/test_s_session_limit.py::test_dj_core_admits_exactly_one_session` 은 **결함을 고정한다**
(characterization · `test_auth_surface.py` 와 같은 방식). dj-core 가 여러 세션을 받게 되는 날
그 시험이 빨개지고, **그날이 이 절을 다시 여는 날**이다.

---

## 9. UX-24a 월(wall) 표시 토큰 — **인증 경로가 하나 늘었다** (2026-09-05 턴 F · 차선 S)

★ **이 절을 먼저 쓰고 지었다** (P-15 · 지시서 §4 함정 ③). 아래 표의 실측은 지은 뒤에 채웠다.

세종 판정 **P-62**: 월 모드는 **세션이 필요 없다.** §8 이 못박은 대로 「2대가 동시에 산다」는
`user.token` 한 칸(§0.4) 때문에 우리 층에서 못 연다(UX-24b). 그래서 **문을 쪼갰다** —
월은 세션을 세우지 않는 **다른 문**으로 들어온다. 그러면 자리 데스크톱의 세션은
**건드려지지 않는다.**

### 9-1. 대장 행 — 인증 경로 **+1**

| 면 | 어느 인증으로 들어가나 | 실측 | 근거 경로 |
|---|---|---|---|
| **월 대형 화면 `/wall`** | `X-GX-Wall-Token: gxwall1.…` — **로그인 문을 안 부른다** | 아래 §9-5 | `backend/common/wall_token.py` |

이 문이 §0 의 「토큰이라 불리는 셋」에 **넷째**로 붙는다. 셋과 무엇이 다른지 먼저 적는다 —
이름이 겹치면 다음 사람이 같은 것으로 읽는다(동음이의 · D-337):

| 이름 | 어디에 실리나 | 누가 검증하나 | 세션을 세우나 | 쓰기 |
|---|---|---|---|---|
| **user.token**(세션) | `Authorization: Bearer <JWT>` | dj-core `CustomJWTAuth` | **세운다**(한 칸을 덮어쓴다) | 역할대로 |
| **inbound_api_key** | `X-API-Key` | dj-core + `JwtOrInboundKey` | 아니다 | 선언한 라우트만 |
| ~~JWT(pair)~~ | — | — | 제거됨(404 · D-411) | — |
| ★ **월 표시 토큰** | **`X-GX-Wall-Token`** | **우리 층 `common/wall_token.py`** | **아니다 — `user.token` 을 한 자도 안 만진다** | **0** |

★ **왜 JWT 로 만들지 않았나.** JWT 를 발급하면 그것은 `Authorization: Bearer` 자리에 실리고,
  그 자리는 dj-core 가 본다 — 즉 **제품 전체의 문**이 된다. 월 한 장을 위해 문 하나를
  통째로 여는 것이다. 그래서 **다른 헤더 · 다른 서명 열쇠 · 다른 검증기**로 갈랐다.
  서명 열쇠는 `HMAC(SECRET_KEY, "gx.ux24a.wall-display-token.v1")` 이라 JWT 열쇠와
  **같은 값이 될 수 없다**(영역 분리). 월 토큰을 `Authorization` 에 실어도 통하지 않고,
  JWT 를 `X-GX-Wall-Token` 에 실어도 통하지 않는다.

### 9-2. 이 토큰이 할 수 있는 것 — **읽기 둘뿐이다**

`/wall` 화면이 실제로 부르는 문만 열었다(손으로 고른 것이 아니라 화면에서 읽었다):

```
GET /api/dsm/events/queue     Wall.tsx:177  dsmGet(dsmEndpoint.eventsQueue)
GET /api/dsm/cameras/pulse    useCameraPulse.ts:CAMERA_PULSE_PATH
```

그 밖의 **모든 경로 · 모든 쓰기 메서드**는 이 토큰으로 열리지 않는다. 두 겹으로 막는다:

| 겹 | 자리 | 무엇을 막나 |
|---|---|---|
| ① 미들웨어 | `WallTokenMiddleware` (`AccessGateMiddleware` **위**) | 쓰기 메서드 → **403** · 목록 밖 경로 → **403**. §0.4 라우트까지 **전부** 덮는다 |
| ② 라우트 선언 | `JwtOrWallToken(wall_token=True, …)` — **두 라우트에만** | 선언 없는 라우트는 월 토큰을 **거절한다**(기본값 거절 · `JwtOrInboundKey` 와 같은 규약) |

★ 한 겹이면 충분한가 — **아니다.** ②만 있으면 §0.4 안에서 새 라우트가 나는 날 그 자리가
  선언 없이 열릴 수 있고, ①만 있으면 목록을 늘리는 손이 곧 개방이 된다. 둘을 함께 두면
  **어느 한쪽을 늘려도 다른 쪽이 남는다.**

### 9-3. 발급 주체와 회수 절차 — **HTTP 문이 아니다**

| 물음 | 답 |
|---|---|
| 누가 발급하나 | **U5 시스템 관리자**가 서버에서 관리 명령으로. `python manage.py wall_token issue --user <계정>` |
| 왜 HTTP 문이 아닌가 | 발급 문을 네트워크에 내면 그 문이 새 공격면이다. 월 토큰은 **한 달에 몇 번** 나가는 물건이고, 그런 것에 상시 열린 문을 주지 않는다(D-300 부작위) |
| 유효기간 | **12시간 고정.** 발급기가 그것만 찍고, 검증기도 `exp-iat > 12h` 면 서명이 맞아도 거절한다 |
| 어디에 남나 | 토큰 자체는 **어디에도 저장하지 않는다**(자체 완결 · 서명). 남는 것은 `jti`·발급 시각·대상 계정뿐 |
| 어떻게 끊나(한 장) | `python manage.py wall_token revoke --jti <jti>` — 회수 목록(캐시 · 12시간)이 곧 만료된다. 토큰 수명보다 오래 들고 있을 이유가 없다 |
| 어떻게 끊나(전부) | `python manage.py wall_token revoke --all` — 발급 시각 기준선(`WALL_TOKEN_EPOCH`)을 지금으로 올린다. **그 이전에 나간 것 전부**가 즉시 죽는다 |
| 되돌리기 한 줄 | `settings.WALL_TOKEN_ENABLED = False` — 그러면 이 문은 통째로 401 이다 |

⚠ **회수 목록은 캐시다.** 재기동하면 비고, 그러면 개별 회수는 사라진다 — 그 사실을 숨기지
않는다. 그래서 **전부 끊기**(`--all`)는 캐시가 아니라 설정값(`WALL_TOKEN_EPOCH`)에 둔다.
급한 회수는 `--all` 이 답이다.

### 9-4. 「쓰기 0」은 주장이 아니라 시험이다

`backend/tests/test_s_wall_token.py` 가 쓰기 문 여럿을 이 토큰으로 두드려 **전부 거부**되는지
잰다. 목록에는 이 절이 연 두 읽기 문의 **바로 옆 쓰기 문**들이 들어간다 — 판정(`/review`)·
접수(`/response`)·현장 회신(`/field-reply`)·설정 쓰기·§0.4 경로. 그리고 HTTP 로도 한 번
더 두드린다(§9-5) — **단위 시험은 함수를 부르고 브라우저는 라우트를 때린다**(D-386).

### 9-5. 실측 [2026-09-05 턴 F]

명령 그대로와 원 출력은 `docs/agent/evidence/UX-24a/wall_token_20260905_TF.md` 에 있다.

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings   python /docs/agent/evidence/UX-24a/probe_wall_token.py'

[UX-24a] 월 토큰 발급 jti=… 수명=43200초                      ← 12시간
[UX-24a] ① 자리 로그인 success=True
[UX-24a] ② 자리 화면 /api/dsm/events?limit=1 → 200
[UX-24a] ③ 월 토큰으로 /api/dsm/events/queue?limit=5 → 200
[UX-24a] ③ 월 토큰으로 /api/dsm/cameras/pulse      → 200
[UX-24a] ④ **월을 켠 뒤** 자리 화면 → 200  (①과 같다)        ← ★ 닫는 조건
[UX-24a] ⑤ user.token 이 바뀌었나 → **그대로다**              ← ★ 세션을 안 만졌다
[UX-24a] ⑥ 쓰기 문 20개 두드림 → **거부 20** · 열림 0          ← ★ 쓰기 0
[UX-24a] ⑦ 목록 밖 읽기 6개 → **거부 6** · 열림 0
```

회수도 **다른 프로세스에서** 재었다(발급은 관리 명령 · 검증은 runserver):

```
[REVOKE] 발급 직후            → 200
[REVOKE] 회수 뒤(다른 프로세스) → 401
```

시험: `tests/test_s_wall_token.py` **30건 초록**
(쓰기 탐침 20 · 목록 밖 읽기 8 · 영역 분리 · 부작위 전수 · 대조군 「로그인으로 월을 켜면
자리가 죽는다」 포함). 게이트: `scripts/verify_authn_paths.py` **exit 0**, 면 ⑤ 가 늘었다.

⚠ **못 잰 것**
- 브라우저로 실제 `/wall` 을 띄워 본 것은 **아니다.** 앞단은 아직 이 헤더를 안 싣는다
  (§9-6). 잰 것은 **서버 면**이다 — 문이 열리고, 자리가 살고, 쓰기가 0 이다.
- 월 토큰 요청의 **응답 캐시** 상호작용: 미들웨어가 `request.user` 를 세워 캐시 열쇠가
  그 사용자 것이 되게 했지만, 두 테넌트의 월 토큰으로 **교차 확인은 못 했다**(이 환경에
  월 계정이 하나다).

### 9-6. ⚠ 조율자 배선 필요 — 앞단이 이 헤더를 실어야 한다

서버 면은 섰다. 남은 것은 `/wall` 화면이 요청에 `X-GX-Wall-Token` 을 싣는 일이다.
지금은 안 싣는다 — **없는 배선을 있는 척하지 않는다.** 그때까지 `/wall` 은 종전대로
로그인 세션으로 뜨고, 그러면 자리 화면이 죽는다(P-62 이전 상태).
