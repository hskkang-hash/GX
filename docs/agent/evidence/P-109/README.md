# P-109 — 표 셋: **공개 쓰기 7 · 회색 8 · 회전 목록**

발행: 2026-09-07 · 턴 M · 차선 S · [실측]

모두 실서버(`http://localhost:8000` · `gx-shell` 안)에 **익명으로 실제 호출**해서 쟀다.
부작용이 없도록 **빈 목록·없는 id·없는 사용자명**만 썼고, `delivery`·`orders` 36개 표의
행 합계를 전/후로 셌다 — **17,298 → 17,298 (변화 0)**.
★ 값은 어디에도 적지 않는다. 대조가 필요하면 `sha256[:12]` 와 길이만 적는다 (D-204).

기계가 읽는 벌: `write_public_and_greys.json`

---

## ① 공개 쓰기 7 — 속도 제한도 서명도 없으면 **회색이다**

| 자리 | 왜 공개인가 | 속도 제한 | 서명 / 일회용 토큰 | 판정 |
|---|---|---|---|:--:|
| `POST /api/v1/auth/login` | 토큰을 받으러 오는 자리 | `@ratelimit ip 5/m block` | 없음(자격증명 자체) | **초록** |
| `POST /api/v1/auth/forgot-password` | 로그인 못 하는 사람이 부른다 | `@ratelimit ip 3/h` + `@csrf_protect` | 없음 | **초록** |
| `POST /api/v1/auth/reset-password` | 메일 토큰으로 부른다 | `@ratelimit ip 15/h` + `@csrf_protect` | 메일로 받은 재설정 토큰 | **초록** |
| `POST /api/v1/auth/refresh-token` | 접근 토큰이 없는 상태가 정상 | 없음 | refresh 토큰 **서명 검증 + 블랙리스트 대조** | **초록** |
| `POST /api/v1/auth/logout` | 만료된 토큰으로도 불려야 한다 | 없음 | 첫 줄이 `get_authenticated_user_from_request()` → 없으면 401 | **초록** |
| `POST /api/v1/auth/otp/verify` | 로그인 절차 2단계 | **없음** | otp_code 6자리 — 그런데 그것이 **맞히려는 대상**이고 시도 계수기도 없다 | **회색** |
| `POST /api/v1/auth/otp/reset` | 로그인 절차 안 | **없음** | **없음** — 본문은 `{username}` 하나뿐 | **회색** |

### 회색 둘의 사유

**`otp/verify`** — 익명이 사용자명 하나만 알면 6자리 코드를 **무제한으로** 시도할 수 있다.
속도 제한도 잠금도 없다. 「공개여도 되는 면」인지 이 증거로는 말할 수 없다.
[실측 · 익명 · 없는 사용자명] HTTP **404** 「User not found」 — 관문 없이 핸들러까지 닿는다.

**`otp/reset`** — 일곱 중 가장 나쁘다. 핸들러가 하는 일
[소스 실측 · dj-core `core/api/v1/auth.py:2050-2055`]:

```
otp_secret = pyotp.random_base32()      # 새 OTP 비밀을 굽는다
user.otp_exempt      = False
user.opt_mandatory   = False
user.otp_is_verified = False            # 2단계 인증을 내린다
user.save()
profile.otp_secret = otp_secret; profile.is_temporary = True; profile.save()
```

곧 **익명이 남의 사용자명만 알면 그 계정의 2단계 인증을 되돌릴 수 있다.**
[실측 2026-09-07 · 익명 · 없는 사용자명 `gxnosuchuser_zzz_probe`] HTTP **404**
「User not found」 — 관문 없이 핸들러까지 닿았다.
★ **실재 사용자명으로는 두드리지 않았다** — 그것이 곧 사고다. 그래서 「닿는다」의 근거는
없는 사용자명의 404 이고, 「무엇을 하는가」의 근거는 소스다. 둘을 섞지 않는다.

---

## ② `write_auth` 의 회색 8 — **다섯을 해소했다**

| 자리 | 이전(턴 L) | 지금 [실측 턴 M] | 판정 |
|---|---|---|---|
| `POST /api/token/pair` | 500 | **404** (Django 기본 HTML) | 회색 **해소** → 그 주소가 없다. 선언에서 뺄 이름이다 |
| `POST /api/token/refresh` | 400 | 400 `{"refresh":"token is required"}` | 회색 **유지** — 관문이 본문 안(토큰 서명)에 있다 |
| `POST /api/token/verify` | 400 | 400 `{"token":"token is required"}` | 회색 **유지** — 같은 사유 |
| `POST /api/v1/auth/delete-session` | 422 | 422 `loc=["query","data"]` | 회색 **유지** — 필수 값이 **질의**에 있어 쓰기 탐침이 못 넘는다. 채워 두드리면 **남의 세션을 끊어서** 두드리지 않았다 |
| `POST /api/delivery/processing/assign-packages-to-drone` | 500 · 탐침 인공물 | **200 + `Permission denied` 봉투** | 회색 **해소** → 거부 |
| `POST /api/delivery/processing/assign-packages-to-drones` | 500 · 탐침 인공물 | **200 + `Permission denied` 봉투** | 회색 **해소** → 거부 |
| `POST /api/delivery/verification/verify-orders` | 500 · 탐침 인공물 | **200 + `Permission denied` 봉투** | 회색 **해소** → 거부 |
| `POST /api/orders/order/{id}/payment` | 500 · 탐침 인공물 | **200 + `Permission denied` 봉투** | 회색 **해소** → 거부 |

어떻게 해소했나 — 대체물(stub)을 **안 쓰고** 실서버에 **스키마를 통과하는 최소 본문**을
익명으로 보냈다. 부작용을 없애려고 **빈 목록**(`[]` · `{"operation_ids": []}`)과
**없는 id**(`999999999`)만 썼다. 본문이 `data` 단일 파라미터라 ninja 는 **값 자체**를 읽는다 —
`{"data": []}` 로 감싸면 422 가 나고 그 422 를 「막혔다」로 세면 또 거짓 초록이다.

★ **턴 J 의 추측이 맞았다.** 대체물이 함께 지우던 `@path_permission` 은 실제로 서 있다.
다만 그 거부가 **HTTP 200 봉투** 안에 있다 — D-349 착시 ⑧이고, 따로 등재된 결함이다.
「막혔다」와 「200 으로 막혔다」는 다른 칸이다.

**남은 회색 3자리는 지우지 않는다.** 이름과 사유로 잠갔다 (위 표 2~4행).

---

## ③ 회전 목록 — **이름만.** 값은 한 자도 적지 않는다

| 자리 | 왜 | 상태 |
|---|---|---|
| MinIO 루트 자격증명 (`MINIO_ROOT_USER`·`MINIO_ROOT_PASSWORD` · 호스트 `.env`) | 평문으로 있고 컨테이너가 그대로 쓴다 | 이미 알려진 자리 |
| `anyang / Admin@123` | 알려진 약한 자격증명 | 이미 알려진 자리 |
| ★★ **`Admin@123` 을 쓰는 계정 74개** (전체 113 중 · 활성 73) | [실측 · `check_password` 전수] `anyang` 한 자리가 아니라 **74자리**다. 그중에 이 저장소의 **유일한 superuser**(`phatlh`)가 있다. 한 사람이 그 한 낱말을 알면 74개 계정과 관리자 권한이 함께 열린다 | **새로 찾음** — 전수 회전 |
| ★ 앱의 MinIO 자격증명 (`MINIO_ACCESS_KEY`·`MINIO_SECRET_KEY`) | [지문 실측] 둘 다 `sha256[:12]=b5a2c9625061` · **길이 5** — 두 값이 **같고** 자리표시자다. `/api/media-data` 503 의 원인 | **새로 찾음** — 회전이 아니라 채워 넣기 |
| ★ `DJANGO_SECRET_KEY` 의 **저장소에 적힌 기본값** (`backend/config/settings.py:28`) | [지문 실측] 기본값 `55a2aa619c85` · 길이 20 / 지금 도는 키 `2bf9799b0713` · 길이 33 → **이 환경은 기본값을 안 쓴다.** 그러나 `NINJA_JWT["SIGNING_KEY"] = SECRET_KEY` 이므로 환경변수를 안 넣은 배포는 **저장소에 적힌 값으로 JWT 를 서명한다** — 저장소를 본 사람이 아무 토큰이나 만든다 | **새로 찾음** — 기본값 제거 + 회전 |
| ★ `WEBHOOK_SIGNING_KEYS` | [실측] 지금 **0개**. 웹훅이 서명 없이 오간다 — 회전이 아니라 **도입** 대상 | **새로 찾음** |
| ★ 탐침·씨앗 계정(`gxprobe_*`·`gxseed_*`)과 `.env.gates` 의 세 비밀번호 | 제품 DB 에 실재하는 계정이다 — 상용에서는 **회전이 아니라 삭제**. 그리고 이름이 어긋나 있다: `GX_PROBE_PASSWORD` 는 `gxprobe_e2e` 의 것이 **아니고**(그 계정 것은 `GX_ROUTE_PASSWORD`), 그것을 모르고 두드리면 잠금 계수기를 태운다 — 이번 턴에 「Attempts 3/5」를 봤다 | **새로 찾음** — 이름 정리 + 상용 전 삭제 |

★ 74개 계정을 어떻게 셌나: `check_password` 를 전수로 돌렸다. **비밀번호를 바꾸지 않았고
로그인도 하지 않았다** — 잠금 계수기를 태우지 않는 방법이다. 사용자명은 여기 적지 않는다
(`write_public_and_greys.json` 에도 수만 적었다).
