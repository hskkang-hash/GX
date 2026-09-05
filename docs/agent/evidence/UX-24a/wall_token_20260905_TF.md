# UX-24a — 월(wall) 표시 토큰 · **세션을 쪼갰다**

- 집행: 차선 S(Security Agent) · **2026-09-05 턴 F** · 근거: 세종 판정 **P-62**
- 대장 행은 **먼저 썼다** — `docs/agent/authn_paths.md` §9 (P-15 · 지시서 §4 함정 ③)
- 파일: `backend/common/wall_token.py`(새) · `backend/common/management/commands/wall_token.py`(새) ·
  `backend/tests/test_s_wall_token.py`(새 · **30건 초록**) · `backend/config/settings.py` ·
  `backend/apps/dsm/api.py`(두 줄) · `scripts/verify_authn_paths.py`(면 ⑤) ·
  `docs/agent/evidence/UX-24a/probe_wall_token.py`(새 · 이 문서의 수를 만든 탐침)

---

## 1. 무엇을 쪼갰나 — **물음을 바꾼 것이 P-62 다**

턴 E 가 잰 벽은 그대로다 [실측 · `authn_paths.md` §8]:

```
core/user/models.py:577   user.token = enc("<session_id>:<access_jti>")   ← 칸 하나. 한 벌
core/api/v1/auth.py:706   로그인이 그 칸을 **덮어쓴다**
```

동시 접속 1개는 설정이 아니라 **자료구조**이고 §0.4 다. 그래서 턴 E 는 「2대가 동시에
산다」를 **판정 불가**로 적었다. 세종은 그 자리에서 물음을 바꿨다 —

> **월이 로그인해야 하는가? 아니다. 월 모드는 세션이 필요 없다.**

월 화면은 읽기만 한다. 읽기만 하는 화면에 세션을 주는 것은 **필요 이상으로 문을 여는
것**이고, 그 여분이 정확히 자리 데스크톱을 죽이고 있었다.

## 2. 그래서 무엇을 지었나 — **넷째 문. 세션이 아니다**

| | 값 | 어디서 강제되나 |
|---|---|---|
| 실리는 자리 | `X-GX-Wall-Token` (**`Authorization` 이 아니다**) | `wall_token.py::token_of` |
| 서명 | `HMAC(SECRET_KEY, "gx.ux24a.wall-display-token.v1")` | `_signing_key()` — JWT 열쇠와 **같은 값이 될 수 없다** |
| 수명 | **12시간** · 발급기와 **검증기 양쪽**이 본다 | `exp-iat > 12h` 면 서명이 맞아도 `ttl_too_long` |
| 화면 | `/wall` 하나 | `WALL_SCREEN_PATH` |
| 열리는 문 | `GET /api/dsm/events/queue` · `GET /api/dsm/cameras/pulse` **둘** | `WALL_TOKEN_PATHS` |
| 쓰기 | **0** | 아래 §3 |
| 세션 | **안 세운다** — `user.token` 을 한 자도 안 만진다 | 로그인 문을 부르지 않는다 |

### 왜 JWT 로 만들지 않았나 — 영역을 갈랐다

JWT 를 발급하면 그것은 `Authorization: Bearer` 자리에 실리고, 그 자리는 dj-core 가 본다.
즉 **제품 전체의 문**이 된다 — 월 한 장을 위해 문 하나를 통째로 여는 것이다.
`/api/token/pair` 를 뺀 이유(D-411)가 정확히 그것이었다: **쓸모없는 토큰을 내주는 문은
기능이 아니라 공격 면이다.** 같은 모양을 새로 만들지 않았다.

시험이 양방향을 못박는다: 월 토큰을 `Authorization` 에 실어도, JWT 를 `X-GX-Wall-Token`
에 실어도 **아무 문도 안 열린다.**

## 3. 「쓰기 0」을 두 겹으로 막았다

| 겹 | 자리 | 무엇을 막나 |
|---|---|---|
| ① 미들웨어 | `WallTokenMiddleware` — `AccessGateMiddleware` **위** | 쓰기 메서드 → 403 `read_only` · 목록 밖 경로 → 403 `scope_path`. **§0.4 라우트까지 전부** 덮는다 |
| ② 라우트 선언 | `JwtOrWallToken(wall_token=True, …)` — **두 라우트만** | 선언 없는 라우트는 거절이 기본값(`JwtOrInboundKey` 와 같은 규약 · D-335 ③⑤) |

★ **순서가 곧 판정이다.** 미들웨어는 메서드를 **경로보다 먼저** 본다. 목록에 있는 경로로
쓰기를 때리면 사유가 `scope_path` 가 아니라 **`read_only`** 로 나온다 — 그래야 다음 사람이
「목록을 늘리면 쓰기도 열린다」로 읽지 않는다.

★ 한 겹이면 충분한가 — 아니다. ②만 있으면 §0.4 안에 새 라우트가 나는 날 그 자리가 선언
없이 열릴 수 있고, ①만 있으면 목록을 늘리는 손이 곧 개방이 된다.

## 4. ★ 닫는 조건 — **자리 데스크톱이 산다** [실측]

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  python /docs/agent/evidence/UX-24a/probe_wall_token.py'
```

```
[UX-24a] 대상 계정 id=105
[UX-24a] 월 토큰 발급 jti=… 수명=43200초
[UX-24a] ① 자리 로그인 success=True 토큰=있다
[UX-24a] ② 자리 화면 /api/dsm/events?limit=1 → 200
[UX-24a] ③ 월 토큰으로 /api/dsm/events/queue?limit=5 → 200  {"now": …, "total_events": 5, …}
[UX-24a] ③ 월 토큰으로 /api/dsm/cameras/pulse      → 200  {"now": …, "rules": …}
[UX-24a] ④ **월을 켠 뒤** 자리 화면 → 200  (①과 같아야 한다: 200)
[UX-24a] ⑤ user.token 이 바뀌었나 → **그대로다**
[UX-24a] ⑥ 쓰기 문 20개 두드림 → **거부 20** · 열림 0
[UX-24a] ⑦ 목록 밖 읽기 6개 → **거부 6** · 열림 0
[UX-24a] 통과 — 월이 열리고 자리가 살아 있고 쓰기가 0 이다
```

두드린 쓰기 문 20개(원 목록은 탐침 파일에 있다): 판정 `/review` · 접수 `/response` ·
알림 `/notify` · 현장 회신 `/field-reply` · 설정 쓰기 여섯 · 훈련 모드 · 벌크 등록 ·
웹훅 구독 · **§0.4 셋**(delivery · orders · terminals) · **로그인/로그아웃** ·
그리고 **목록에 있는 두 경로의 쓰기 메서드**.

목록 밖 읽기 6개에는 **원본 영상 `clip/stream`**(계약 11조 · D-306)과 **나가는 키 표**
(`/settings/api_keys` · 표 ② · D-337)가 들어간다 — 「읽기니까 괜찮다」가 아니다.

### 대조군 — 로그인으로 월을 켜면 **여전히 자리가 죽는다**

`tests/test_s_wall_token.py::DeskSessionSurvivesTest::test_login_as_wall_still_kills_the_desk`
가 그 사실을 그대로 고정한다. 두 시험이 나란히 있어야 「월 토큰이 그것을 고쳤다」가
**비교로** 읽힌다 — 한쪽만 재면 어느 쪽이든 그럴듯하다(D-411 이 남긴 교훈).

## 5. 발급 주체와 회수 절차 — **HTTP 문이 아니다**

```
python manage.py wall_token issue  --user <계정> [--note "관제실 A 대형화면"]
python manage.py wall_token revoke --jti <jti>
python manage.py wall_token revoke --all        # WALL_TOKEN_EPOCH 를 알려 준다
python manage.py wall_token show   --token <토큰>
```

[실측 · 발급] (토큰 본문은 **가렸다** — 증거 문서에 비밀을 적지 않는다)

```
  X-GX-Wall-Token: gxwall1.<가렸다>
  대상 계정  gxprobe_e2e (id=105)
  jti        653acfda3175bd02   ← 회수할 때 이 값을 쓴다
  만료       2026-09-06 09:21:13  (12시간)
  화면       /wall  (하나뿐이다)
  열리는 문  /api/dsm/events/queue, /api/dsm/cameras/pulse  ← **읽기만**
```

[실측 · 회수] 발급은 관리 명령(별도 프로세스) · 검증은 runserver — **프로세스를 건너** 듣는다:

```
[REVOKE] 발급 직후            → 200
[REVOKE] 회수 뒤(다른 프로세스) → 401
```

| 물음 | 답 |
|---|---|
| 누가 | **U5 시스템 관리자**가 서버에서 |
| 왜 HTTP 문이 아닌가 | 발급 문 자체가 새 공격면이다. 한 달에 몇 번 나가는 물건에 상시 열린 문을 주지 않는다(D-300 부작위) |
| 어디에 저장되나 | **어디에도.** 자체 완결(서명)이고, 잃어버리면 새로 발급한다 — 저장하지 않는 비밀은 새지 않는다 |
| 급한 회수 | `--all` → `WALL_TOKEN_EPOCH` 를 올린다. 그 이전에 나간 것 **전부**가 죽는다 |
| 되돌리기 | `WALL_TOKEN_ENABLED = False` 한 줄 |

⚠ **개별 회수는 캐시다.** 재기동하면 빈다 — 숨기지 않는다. 그래서 최종 수단을 캐시가
아니라 설정값(`--all`)에 뒀다.

## 6. 게이트 — 인증 경로가 **+1** 되고 그 자리를 게이트가 본다

`scripts/verify_authn_paths.py` 에 **면 ⑤** 를 더했다. 재는 것 둘:

```
[AUTHN] [입력] 1건 — 위조 월 토큰으로 /api/dsm/events/queue → 401 (기대 401)
[AUTHN] [입력] 1건 — 월 토큰 자리로 POST /api/dsm/events/1/review → 401 (**쓰기 0** · 2xx 면 실패)
[AUTHN] 통과 — … 월 표시 토큰(UX-24a)은 **읽기만** 연다
                                                          → exit 0
[AUTHN] 자기시험 통과 — … · **월 토큰 행 실재**            → --self-test exit 0
```

★ 게이트에 **진짜 토큰을 심지 않았다** — 심으면 그것이 곧 유출이다. 게이트가 재는 것은
「그 겹이 살아 있는가」이고, 유효한 토큰으로 여는 전체 실측은 위 §4 의 탐침이 한다.
★ 자기시험이 **대장에 `X-GX-Wall-Token` 행이 있는지**까지 본다 — 인증 경로는 먼저 적고
짓는다는 규약(P-15)을 게이트가 지키게 했다.

## 7. 일하다 만난 것 둘 — **둘 다 이미 저장소가 알고 있었다**

### ㉠ 모양이 안 맞는 `Bearer` 는 무엇이든 **500**

```
Authorization: Bearer abc          → 500
Authorization: Bearer aaa.bbb.ccc  → 500
```

뿌리는 `core/middleware/refresh_token.py:204` 의 감싸지 않은 `jwt.decode` 다(§0.4).
**새 발견이 아니다** — `tests/test_auth_surface.py::MalformedBearerTest` 가 이미 고정해
두었다. 그래서 이 절의 영역 분리 시험은 401 을 기대하지 않고 「**열리지 않는다**」를 잰다.
그 사유를 시험 안에 적어 두었다 — 저 시험이 고쳐지는 날 이 시험도 함께 빨개지고, 그날
401 로 조인다.

### ㉡ ★ **내 시험이 남의 시험을 죽였다** — 스레드에 남은 요청 [실측]

이 파일을 `tests/test_s_session_limit.py` 와 **함께** 돌리자 저쪽 5건이 픽스처에서 죽었다:

```
psycopg2.errors.ForeignKeyViolation:
  insert or update on table "user_usergroup" violates foreign key constraint …
  DETAIL: Key (created_by_id)=(3) is not present in table "user_coreuser".
```

뿌리는 **이 파일**이다. 월 토큰 미들웨어가 `request.user` 를 세우고 그 요청이
`thread_local.request` 에 남는다. 시험이 끝나 그 사용자는 롤백으로 사라지는데, **다음 시험
모듈의 `UserGroup.objects.create()` 가 그 유령을 `created_by` 로 찍는다.**

⚠ 이 함정은 **반대 방향으로 더 위험하다**: 남은 요청이 `objects` 를 조용히 비우면
**404 를 기대한 시험이 오염으로 초록**이 된다. 저장소의 다른 시험들이 이미 같은 모양을
쓰고 있었고(`test_c2_camera_grid.py` 외 다수), 이 파일도 같게 고쳤다 — 픽스처 만들기
**전**과 끝난 **뒤** 양쪽에서 지운다(`_clear_thread_request` · `_ThreadCleanMixin`).

```
tests/test_s_wall_token.py + tests/test_s_session_limit.py        → 56 passed
+ test_access_gate · test_api_contract · test_f05_inbound_api_key
  · test_auth_surface · test_tenant_isolation                     → **163 passed**
```

## 8. 못 잰 것 · 남은 위험

- **브라우저로 `/wall` 을 띄워 본 것이 아니다.** 앞단이 아직 `X-GX-Wall-Token` 을 안 싣는다
  (조율자 배선 필요 · `authn_paths.md` §9-6). 잰 것은 **서버 면**이다.
  그때까지 `/wall` 은 종전대로 로그인 세션으로 뜨고, 그러면 자리 화면이 죽는다.
- **응답 캐시와의 교차 확인을 못 했다.** 미들웨어가 `request.user` 를 세워 캐시 열쇠가 그
  사용자 것이 되게 했지만(안 세우면 익명 칸에 담긴다), **두 테넌트의 월 토큰으로 교차
  확인은 못 했다** — 이 환경에 월 계정이 하나다.
- **토큰이 종이에 적혀 관제실에 붙는 물건**이라는 위험은 그대로다. 12시간 · 읽기 둘 ·
  회수 절차가 그것을 좁히지만 없애지는 못한다. 그 화면이 보는 것은 **이벤트 큐와 카메라
  생사**이고, 둘 다 재난 정보다.
- 월 계정의 **역할**은 이 절이 정하지 않았다. 토큰은 `--user` 가 준 계정의 자격으로 읽는다 —
  그 계정에 넓은 역할을 주면 두 문이 내주는 **범위**가 넓어진다. 좁은 전용 계정을 쓰는 것이
  운영의 몫이고, 그 판정은 아직 **안 내려졌다**.
