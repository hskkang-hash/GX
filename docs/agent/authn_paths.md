# 인증 경로 대장 — 면마다 어느 문으로 들어가는가 (P-15)

**작성 2026-09-18** · 판정 `scripts/verify_authn_paths.py` · 근거는 전부 [실측]

> 게이트는 다른 길로 들어갔다. **그러면 실제 클라이언트는 어느 길로 들어가나?**
> 모바일 M1~M3 는 로그인이 첫 화면이다. **죽은 인증 길 위에 화면을 세우지 않는다.**

---

## 0. 「토큰」이라 불리는 것이 셋이다 — 셋은 다른 것이다 (동음이의 · D-337)

| 이름 | 무엇인가 | 누가 주나 | 누가 받나 |
|---|---|---|---|
| **JWT(pair)** | 서명된 접근 토큰 | `/api/token/pair` | ★ **세션이 있을 때만** — 스스로 세우지는 못한다 |
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

## 2. `/api/token/pair` 처분 [판정]

**㉰ — 제거 후보. 다만 이번 턴에 빼지 않는다.**

| 물음 | 실측 |
|---|---|
| 실제 클라이언트가 쓰는가 | **아니다.** 빌드 번들에 0건 |
| 쓰는데 거절되는가 | 세션이 없으면 401 · 있으면 200 — **스스로는 못 들어간다** |
| 우리가 등록했는가 | 아니다 — dj-core(ninja_jwt)가 들고 온다. **§0.4 라 우리가 못 뺀다**(D-207) |

★ 위험의 모양이 「죽은 문」이 아니라 **「기생하는 문」**이라는 것이 처분에 영향을 준다:
누군가 로그인해 세션이 살아 있는 동안에는, 아이디·비밀번호를 아는 쪽이 이 문으로
**세션 관리 규약(동시 접속 1개)을 우회한 토큰을 더 찍어 낼 수 있다.**
로그아웃하면 `user.token` 이 지워져 그 토큰들도 함께 죽는다 — 그래서 지금 등급은
「즉시 위험」이 아니라 **「연동 담당자가 먼저 발견하면 안 되는 문」**이다.

- 그러므로 처분은 「우리 코드에서 부르지 않기」이고, 그것은 **이미 그렇다.**
  남은 위험은 **연동 담당자가 그 문을 먼저 발견하는 것**이다 — OpenAPI 에 보이니까.
- 밖에서 막는 길은 있다(D-335/D-348: 바깥 차단). 그러나 **막기 전에 재야 한다** —
  지금 이 문을 쓰는 시험이 저장소 안에 하나 있다(§4). 먼저 그것을 옮기고, 그 다음에 막는다.
- ⚠ `tests/test_api_contract.py` 의 계약 시험은 **그대로 둔다.** 그 시험이 빨개지는 날은
  이 문이 살아난 날이고, 그때는 연동 문서를 고쳐야 한다. 판정기가 같은 것을 본다.

---

## 3. ★ 외부 API U6 — 키를 **발급할 문이 도달 불가**다 [실측]

`POST /api/dsm/settings/api-keys` 를 때리면 **405 · `Allow: GET`** 이다.

원인: 같은 컨트롤러의 `@route.get("/settings/{domain}")` 이 **먼저 선언되어**
`settings/<한 단>` 을 통째로 먹는다. Django 는 첫 일치에서 멈추고, 그 뷰는 GET 만 안다.

같은 이유로 넷이 함께 막혀 있다:

| 메서드 | 경로 | 계약 | 실측 |
|---|---|---|---|
| POST | `/api/dsm/settings/api-keys` | F-05 API Key 발급 | **405** |
| POST | `/api/dsm/settings/thresholds` | F-12 임계값 | **405** |
| POST | `/api/dsm/settings/zones` | F-12 구역 | **405** |
| POST | `/api/dsm/settings/grade-rules` | F-12 등급규칙 | **405** |

두 단짜리 형제는 멀쩡하다 — `DELETE /settings/api-keys/{id}` **403**,
`POST /settings/api-keys/{id}/rotate` **403** (문지기가 선 것이지 죽은 것이 아니다).

### 왜 여태 안 보였나

**단위 시험은 서비스 함수를 직접 부른다.** `verify_contract_ac.py` 도 절마다 그 시험을
가리키므로 넷 다 초록이었다. D-386 이 이름 붙인 층이 정확히 여기다 —

> 단위 시험은 **함수를 부른다.** 브라우저는 **라우트를 때린다.**

그리고 `route-alive` 는 **화면이 실제로 부른 GET** 만 때린다. 이 넷은 쓰기 면이고,
화면이 아직 안 부른다. **양쪽 눈의 사각이 정확히 겹친 자리**다.

### 처분 — 고르는 자리가 세종이다 (D-280)

지금 고치지 않는다. 셋 다 **경로 계약**을 건드리기 때문이다:

```
㉮ 선언 순서를 바꾼다        → 그러면 GET /settings/thresholds 가 405 가 된다. **살아 있는 것을 깬다**
㉯ 일반 조회 경로를 옮긴다    → 예: GET /settings/view/{domain}. 읽는 쪽 계약이 바뀐다
㉰ 쓰기 경로를 옮긴다        → 예: POST /settings/api-keys/issue. DA-04 스펙과 대조가 필요하다
```

지금 상태는 래칫으로 잠갔다(`SHADOWED_WRITE_ROUTES` · D-311) — **넷에서 늘면 빨개진다.**
대장: `DA-05/blockers.yaml :: DSM_SETTINGS_WRITE_ROUTES_SHADOWED`.

---

## 4. `/api/v1/auth/logout` — 문 하나가 느슨하다 [실측]

`@router.post("/logout")` 에는 **`auth=` 가 없다.** 사용자는 미들웨어가 붙인 것으로 판정한다
(`get_authenticated_user_from_request`). 그래서:

| | 결과 |
|---|---|
| 익명(헤더 없음) | **401** — 안전하다 |
| `/api/token/pair` 토큰 | **200 · 세션이 실제로 지워진다** (`user.token` True → False) |

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
- 기생하는 문: `/api/token/pair` 토큰을 **두 갈래로** 때린다 —
  세션 없이 401 · 세션 있이 200. 한 갈래만 재면 어느 쪽이든 그럴듯하다.
  세션 없이도 통하게 되면 **그 문이 스스로 세션을 세우게 된 것**이므로 빨개진다.
- 도달 불가 쓰기 면: 넷을 세고 **늘면 빨개진다**(래칫 D-311).

---

## 7. 동음이의 기준선 한 줄이 늘었다 — 사유 (D-337)

`verify_homonyms` 가 이 판정기의 수식어 없는 `api_key` 를 잡았다. 둘이었고 하나는 고쳤다:

- 판정기 머리말의 설명어 → **`inbound_api_key`** 로 바꿨다(방향을 이름에 붙인다).
- 남은 하나는 `("POST", "/api/dsm/settings/api-keys")` — **제품의 실제 URL** 이다.
  이름을 바꾸면 때릴 자리가 달라진다. 그래서 `--freeze` 로 기준선에 올렸다(+1).

기준선 파일은 손으로 고치지 않는다(도구가 만든다). **사유는 여기 남긴다** —
다음에 그 한 줄을 보는 사람이 「왜 예외인가」를 여기서 읽게.
