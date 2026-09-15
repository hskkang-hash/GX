# P-100 짝 게이트 `verify_error_body` — 전/후 (2026-09-07 · 턴 L · 차선 Q)

> 판정기: `scripts/verify_error_body.py` (차선 Q 신설) · 수치는 `error_body_전후_20260907_TL.json`
> 술어: **무인증 표본에서 5xx 본문에 `Traceback` · `pydantic` · `File "` · 내부 파일 경로가 0회**
> 모수: **살아 있는 라우터 705 라우트**(`_iter_ninja_apis()` · 손 목록 아님 · P-99) × 무인증 결 2 = **표본 1,410**

## 0. 이 게이트가 P-100 보다 넓게 문 것 — 표본을 뜨자마자 나왔다

P-100 은 「`GET /api/report-template` 권한 거절 → 500 + pydantic 역추적」 **한 건**으로 열렸다.
그런데 익명 결에 **망가진 토큰 한 줄**(`Authorization: Bearer zzz`)을 붙이자:

```
GET /api/v1/health   머리글자 없음        → 200        38 바이트
GET /api/v1/health   Bearer zzz          → 500   165,721 바이트   ← 장고 디버그 페이지 전문
GET /api/cameras     Bearer zzz          → 500   166,132 바이트   ← **없는 경로인데도** 받는다
```

165KB 안에 `Traceback` 6 · `File "` 17 · `site-packages` 36 · `/app/stream_monitors/media/images` ·
`INSTALLED_APPS` 전문 · 설정 표 전체 · `Exception Location: /usr/local/lib/python3.11/site-packages/jwt…`.

**라우트가 없어도 받는다 → 한 라우트의 결함이 아니라 URL 해석 앞단의 결함**이고,
그래서 「그 라우트를 고쳤다」로는 닫히지 않는다.

## 1. 전 (2026-09-07 ~19:05 · 재기동 전)

| | |
|---|---|
| 표본 | 1,410 (응답 못 받음 0) |
| 5xx | **709** |
| 그중 유출 | **709 — 100%** |
| 결별 | `bad_token` **705/705 전부 500 + 유출** · `anon` 4건(`GET /api/topic` · `/api/topic/{id}` · `/api/topic/slug/{slug}` · `/api/v1/auth/data-for-profile`) |
| 표지 | `Traceback` · `File "` · 내부경로 — 709건 모두 셋 다 |
| 색 | **빨강 (exit 1)** |

`anon` 넷은 머리글자조차 없이 받는 500 이고, 본문이 **평문 역추적**이었다
(`django/db/models/sql/query.py` `FieldError` / `setup_joins` — 2.3KB · 13.6KB).

## 2. 후 (2026-09-07 19:11:35 재기동 뒤 · 차선 Backend/DB 수정 반영)

| | |
|---|---|
| 표본 | 1,410 (응답 못 받음 0) |
| 5xx | **709** — 수는 그대로다 |
| 그중 유출 | **0** |
| 색 | **초록 (exit 0)** |

    GET /api/v1/health   Bearer zzz  → 500  170 바이트
    {"success": false, "status_code": 500,
     "message": "서버가 요청을 처리하지 못했습니다. 관리자에게 문의하세요.", "detail": "Internal serv…"}

**닫힌 것은 「본문이 내부를 싣고 나가는 것」이다.** 165,721 → 170 바이트.

## 3. 닫히지 **않은** 것 — 이 게이트의 술어 밖이므로 여기서 판정하지 않는다

- **망가진 토큰에 705/705 가 여전히 500 이다.** 형식이 깨진 `Authorization` 은
  **401 이어야 하고 500 이면 안 된다** — 지금은 「자격 없는 사람이 아무 라우트나 500 으로
  만들 수 있다」가 남아 있다(가용성 · 로그 오염). 그 자리는 이 게이트가 아니라
  인증 관문(`verify_authn_paths` · `verify_write_auth`)의 술어다. **넘긴다.**
- **404 본문 77KB**(익명 · 재기동 전)도 같은 가족이었다. 지금은 재확인하지 않았다 —
  이 게이트의 술어는 5xx 다. 5xx 아닌 본문의 유출은 「참고」 칸으로만 세고 색을 만들지 않는다.

## 4. 이 게이트가 스스로 지키는 것

- **면제 칸이 없다**(D-327). 「이 라우트는 원래 그렇다」를 적는 자리를 만들지 않았다.
- **5xx 를 한 번도 못 보면 회색**이다 — 공백 참을 초록으로 내지 않는다(D-301).
  실제로 19:05 재기동 창에 서버가 안 떴을 때 이 갈래가 걸려 회색(exit 2)이 나왔다.
- **모수를 사진에서 뽑으면 회색**이다(P-99). 라이브 라우터에서 못 뽑으면 커밋된
  `route_inventory.json` 으로 물러서되 그 사실을 적고 회색을 낸다.
- **쓰기 라우트에 쓰기를 보내지 않는다.** 754자리는 `OPTIONS` 대체이고 「그 메서드는
  못 잰 것」으로 표시된다. 경로 매개변수는 없는 id(`999999999`)로 채운다.
- 자기시험 17건(출생 표본 6 · 음성 6 포함) — `python scripts/verify_error_body.py --self-test`
