# UX-24 — 역할별 동시 세션 상한 · **판정 불가 하나를 이름으로 적는다**

- 집행: 차선 S(Security Agent) · **2026-09-05 턴 E** · 근거: 세종 판정 UX-24
- 대장 행은 **먼저 썼다** — `docs/agent/authn_paths.md` §8 (P-15 · 지시서 §4 함정 ③)
- 파일: `backend/common/session_limit.py`(새) · `backend/config/settings.py` ·
  `backend/tests/test_s_session_limit.py`(새 · **25건 초록**)

---

## 1. 먼저 잰 것 — `end_previous_session` 은 **dj-core 안에서 돈다** (§0.4)

| 무엇 | 자리 | 하는 일 |
|---|---|---|
| 요청 칸 | `core/api/v1/schemas.py:20` | `end_previous_session: bool = False` |
| 거절 갈래 | `core/api/v1/auth.py:630` | 거짓 + 앞선 세션 있음 → **200 · `success:false`** (토큰 안 줌) |
| 축출 갈래 | `core/api/v1/auth.py:693` | 참 → 그 사용자 `OutstandingToken` **전부** 블랙리스트 |
| 세션 심기 | `core/api/v1/auth.py:706·725` | `uuid4()` → `set_encrypted_session_token(session_id, jti)` |
| 세션 대조 | `core/auth.py:31·51·63` | 토큰 `session_id` ≠ `user.token` → 401 |
| 저장 자리 | `core/user/models.py:577` | `user.token` = **CharField 한 칸 · 한 벌** |

★ **동시 1개는 설정이 아니라 자료구조다.** 여러 벌로 만들려면 `core/auth.py` 의 대조를
고치거나 `user.token` 을 바꿔야 하고 **둘 다 §0.4** 다.

## 2. 그래서 우리 층에 무엇을 얹었고 무엇을 못 얹었나

| 세종이 정한 것 | 결과 |
|---|---|
| 상한 U1 3 · U2 3 · U4 2 · U5 2 | **얹었다** — `ROLE_SESSION_CAPS` (역할 코드는 `config/k3_roles` 한 곳이 답한다) |
| 월 모드 세션 12시간 | **얹었다** — `WALL_MODE_SESSION_TTL_SECONDS` |
| 초과 시 가장 오래된 세션 종료 | **얹었다** — 순수 함수 `admit(existing, incoming, cap, now)` |
| 그 화면에 안내 한 줄 | **얹었다(서버 쪽)** — 401 본문에 사전 문구 |
| **2대가 실제로 동시에 산다** | **판정 불가** — 위 §1. 우리 층에 얹을 자리가 없다 |

**「판정 불가」를 초록으로 적지 않았다.** `test_dj_core_admits_exactly_one_session` 이
「지금은 1개다」를 **고정**한다 — dj-core 가 바뀌면 그 시험이 빨개지고 그날 절을 다시 연다.

## 3. 일하다 찾은 것 — **지시서에 없던 것 둘** [실측]

### ㉠ dj-core 의 사유는 화면에 **한 글자도 닿지 않는다**

```
core/auth.py:63          raise HttpError(401, "Token from different session")
core/auth.py:119         바깥 except 가 그것을 잡아 "Token invalid" 로 바꾼다
core/api/v1/auth.py:197  CustomJWTAuth.authenticate 의 `except Exception: pass` 가 삼킨다
→ 화면이 받는 것:        401 {"detail": "Unauthorized"}
```

즉 **밀려난 화면과 토큰이 깨진 화면이 글자 하나까지 같다.** 그래서 우리 층은 응답이
아니라 **요청이 들고 온 토큰**으로 둘을 가른다(`_eviction_of` — 서명 검증 후
토큰의 `session_id` 와 `user.token` 의 `session_id` 를 대조). 응답 본문으로 가르려던
첫 판은 **시험이 잡았다**(초록을 만들려고 술어를 넓히지 않았다).

### ㉡ ★ 밀려난 화면의 **요청 한 번**이 살아 있는 세션의 재발급 토큰을 **전부** 끊는다

`core/auth.py` 의 바깥 `except` 는 사유를 바꾸기 전에 그 사용자의 만료 안 된
`OutstandingToken` 을 전부 블랙리스트한다. 월 모드는 20초마다 서버를 두드리는 화면이다 —
**밀려난 월 모드 한 장이 지금 앉아 있는 사람의 세션 갱신까지 끊는다.**
「가끔 로그아웃된다」의 유력한 뿌리이고, §0.4 라 우리가 못 고친다.
`test_stale_token_blacklists_the_live_session` 이 그 사실을 고정한다(지금 초록 = 부작용 있음).

## 4. 토큰 수명 — **한 값도 안 바꿨다**

접근 **200분** · 재발급 **7일** · 회전 **켜짐** 그대로다. 월 모드 12시간이 그 값을
요구하는지부터 쟀고(UX-16 `session_12h.md`), **요구하지 않는다** — 재발급 7일과 회전이
그 사이를 잇는다. 720분으로 올리면 대형 화면 한 장을 위해 제품 전체의 탈취 창이
3.3시간 → 12시간이 된다. `test_token_lifetime_unchanged` 가 세 값을 못박는다.

## 5. 조율자 배선 필요 · 다음 사람이 할 일

1. **앞단이 401 본문의 `detail` 을 그려야** 사람이 「다른 기기에서 로그인되었습니다」를
   읽는다. 서버는 이미 말하고 있다. `frontend/` 는 차선 S 의 것이 아니다.
2. **월 모드 표식** — 월 모드 화면이 로그인에 `X-GX-Surface: wall` 을 실으면 12시간
   수명이 그 세션에 붙는다. 안 실으면 자리 화면과 같은 수명이다(지금은 그렇다).
3. dj-core 의 세션 벽을 여는 것은 **판정**이지 코드가 아니다 — `/api/token/pair` 를
   `config/urls.py` 앞줄로 막았던 것처럼, 우리 층에서 여는 길이 있다면 그것은
   `core/auth.py` 를 대신하는 인증 콜백을 **699 라우트 전부에** 갈아 끼우는 일이고
   그 라우트의 절반은 §0.4 다.

## 6. 명령과 수

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  DB_TEST_NAME=test_gx_sec python -m pytest tests/test_s_session_limit.py -q \
  --nomigrations -p no:randomly --tb=short 2>/dev/null'
→ 25 passed
```
