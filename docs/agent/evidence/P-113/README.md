# P-113 — 익명이 **남의 2단계 인증을 껐다** [차선 S · 2026-09-10 턴 O]

- TARGET = `http://localhost:8500` (nginx `gx-nginx-e` → gunicorn `gx-gunicorn-e`)
  ⚠ 그 서버는 **운영 프로필이 아니다** (`profile=dev` · `DEBUG=True` · `ALLOWED_HOSTS=['*']`).
  운영 *프로세스 모양*일 뿐이다 — 그래서 모든 수 옆에 `TARGET=` 을 적는다 (P-111 미해소).
- AS = 익명 · `gxseed_u4_official` · `gxseed_u5_sysop`(역할 `admin`)
- SOURCE = 오늘 내가 직접 두드린 응답. 남이 적어 준 줄은 이 표에 없다.

## ① 무엇이 있었나

```
POST /api/v1/auth/otp/reset
Content-Type: application/json

{"username": "..."}          ← 본문이 이것 하나뿐이다
```

dj-core `core/api/v1/auth.py:1990 reset_otp` 에 **권한 검사가 한 줄도 없다**:

```python
otp_secret = pyotp.random_base32()
user.otp_exempt = False
user.opt_mandatory = False       # ← 2단계 인증 의무 해제
user.otp_is_verified = False     # ← 검증 상태 취소
user.save()
profile.otp_secret = otp_secret  # ← 비밀키를 새로 심는다
profile.is_temporary = True
```

**익명이 아무 계정의 2FA 를 끌 수 있다.** P-112(74계정이 한 낱말을 공유)와 겹치면
두 번째 벽이 사라진 채 첫 번째 벽도 얇다.

## ② 전 → 후 [실측 · TARGET=8500]

| 부르는 사람 | 본문 | 전 | 후 |
|---|---|---|---|
| **익명** | `{"username":"gx_nonexistent_probe_zzz"}` | **404** `{"success":false,…,"ko":"사용자를 찾을 수 없습니다"}` | **401** `{"detail":"Unauthorized","reason":"authentication required"}` |
| 로그인만 한 본인 (`gxseed_u4_official`) | `{"username":"gxseed_u4_official"}` | (도달) | **401** `{"detail":"Unauthorized","reason":"re-authentication required"}` |
| 비관리자가 **남의 계정** | `{"username":"gx_nonexistent_probe_zzz"}` | (도달) | **403** `{"detail":"Forbidden","reason":"administrator required to reset another account's OTP"}` |
| 관리자(`gxseed_u5_sysop` · 역할 `admin`)가 남의 계정 | 같음 | (도달) | **통과** — 핸들러 404 · **감사 #199283** 남음 |

> ★ **404 는 관문의 답이 아니다.** 핸들러가 실제로 돌아 조회까지 갔다는 뜻이다
> (P-83 눈금: 401/403 만 관문 · 400/422 는 도달·검증 실패 · 404/405 는 도달 실패).
> ⚠ **실재 사용자명으로는 일부러 두드리지 않았다** — 그 한 번이 곧 사고다.
> 「쓴다」의 근거는 위 호출 그래프이고, 「이 입력으로는 안 썼다」의 근거는 없는 이름으로
> 잰 404 다. 둘을 섞지 않는다 (D-322).
> ★ 덤 — 옛 404 는 **익명이 사용자명의 존재 여부를 캐낼 수 있는 자리**이기도 했다.
> 401 이 그것도 함께 닫는다.

## ③ 규칙 (CPO 판정 그대로)

| 상황 | 답 |
|---|---|
| 익명 | **401** |
| 본인 + 재인증 증거 없음/틀림 | **401** (`current_password` 또는 `otp_code` 중 하나가 맞아야 한다) |
| 본인 + 증거 맞음 | 통과 |
| 남의 계정 + 비관리자 | **403** |
| 남의 계정 + 관리자 | 통과 **+ 감사 한 줄** (남기지 못하면 403 — 조용히 통과하지 않는다) |

- 관리자 판정 셋: `is_superuser` · `is_staff` · 역할 코드 ∈ {`admin`, `superuser`}.
- 대상 이름이 비면 **본인 요청**으로 읽는다 (가장 좁은 해석).
- 401 과 403 을 가르는 이유: 「누구인지 모른다」와 「누구인지는 아는데 안 된다」는
  다른 문장이다 (D-290).

## ④ 어디서 막았나 — **우리 층**

`core/api/v1/auth.py` 는 §0.4 금지구역이다. 라우트도 핸들러도 한 줄 안 고쳤다.

- `backend/common/access_gate.py` — `AUTHN_REQUIRED_PATHS` 에 이름 한 줄
  (`/api/v1/auth/reset-password-for-user` 와 **같은 목록**). 익명 401 은 여기서 나온다.
  `AUTHN_SURFACE`(인증 면 면제)가 이 자리를 덮고 있었다 — P-83 과 **정확히 같은 모양**이다.
- `backend/common/otp_reset_guard.py` — 재인증·관리자·감사 판정. 순수 함수라 요청 객체
  없이 시험된다.

되돌리기 두 줄 (D-212):
- 재인증 규칙: `settings.OTP_RESET_GUARD_ENABLED = False`
- 익명 401: `AUTHN_REQUIRED_PATHS` 에서 `/api/v1/auth/otp/reset` 한 줄을 뺀다

## ⑤ 시험 — `backend/tests/test_p113_otp_reset_guard.py` (**18건 통과**)

`OtpResetGuardPredicateTest` · `OtpResetGuardJudgeWithUsersTest` · `OtpResetOverHttpTest`.
못박은 것: 익명 401 · 증거 없는 본인 401 · **증거가 맞으면 통과(음성 대조 · D-277)** ·
현재 OTP 코드로도 통과 · 비관리자의 타계정 403 · 관리자 통과는 감사가 조건 ·
감사 `logger_name` 이 `guardianx.` 접두여야 함(LAW-08) · 플래그 OFF 되돌림.

## ⑥ 이 턴에 내가 만든 흠 하나 — **감사 접두를 틀렸다**

첫 판에서 `logger_name="security.otp_reset"` 로 썼다. `evidence_chain.CHAIN_PREFIX`
(= `"guardianx."`)로 시작하지 않아 **체인 잇기가 예외로 터졌고**, 규약대로 감사 쓰기가
통째로 실패했으며 **관문은 403 으로 끊었다**(조용히 통과하지 않았다 — 설계대로다).
그 시도가 남긴 감사 행 **#199137**(`logger_name=security.otp_reset`)은 **지우지 않았다.**
감사 행은 지우지 않는다. `guardianx.sec.otp_reset` 으로 고쳤고 시험에 못박았다.

## ⑦ 운영에 남는 결과 — 숨기지 않는다

「인증기를 잃어버렸다」는 이제 **관리자 일**이다. 종전에는 누구든(익명 포함) 이 자리를
불러 OTP 를 초기화할 수 있었다. 자가 복구 창구가 필요하면 그것은 **별도 흐름**이고,
이 자리를 다시 여는 것으로 대신하지 않는다.
