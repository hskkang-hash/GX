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
