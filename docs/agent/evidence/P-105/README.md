# P-105 — **역할 없는 계정은 아무것도 보지 않는다.** 지금은 95자리를 본다

발행: 2026-09-07 · 턴 M · 차선 S · [실측]

---

## 한 줄

`gxprobe_e2e`(인증됨 · `user.roles` = `[]`)로 **살아 있는 라우터의 읽기 전수 329자리**를
실제로 불렀다. **95자리가 200 과 함께 자료를 돌려줬다** (합계 622,127 B).
익명으로도 **5자리**가 자료를 낸다.

| 칸 | 역할 0개 계정 | 익명 |
|---|---:|---:|
| **빨강** — 200 + 본문에 자료 | **95** | **5** |
| 초록 — 403/401, 또는 비었거나 거부인 봉투 | 130 | 308 |
| 공개 설계 — 선언 + 사유 | 2 | 2 |
| 회색 — 못 쟀다 | 102 | 14 |
| **분모 [실측]** | **329** | 329 |

분모를 낸 명령 (손으로 고른 목록이 아니다 · P-99):

```
docker exec -e DJANGO_SETTINGS_MODULE=config.settings \
  -e GX_READ_SUBJECT_PW=… -e GX_READ_CONTROL_PW=… gx-shell \
  python /repo/scripts/probe_read_surface.py /docs/agent/evidence/P-105/read_surface.json
# → 읽기 면 전수 329자리 (라우터 706행 중 · 분모=살아 있는 라우터)
```

`_iter_ninja_apis()` → `_routers` → `path_operations` → `operations` 전수에서 **읽기
메서드가 아닌 것 하나만** 걸렀다. 706행 = 읽기 329 + 쓰기 377.

---

## 빨강 술어 — 정확히 이것이다

셋이 **모두** 참일 때만 빨강이다:

1. HTTP 상태가 **2xx**
2. 본문이 JSON 이고 **거부 봉투가 아니다**
   (이 제품에는 「봉투는 200, 내용은 403」인 자리가 **53자리** 있다 — D-349 착시 ⑧.
   그것을 자료로 세면 없는 빨강이 무더기로 생긴다)
3. 봉투(`success`·`status`·`message`·쪽 나누기 칸)를 **걷어내고 남은 것이 비어 있지 않다**
   — 리스트면 원소 ≥ 1, 딕트면 열쇠 ≥ 1. `{"items": [], "total": 0}` 은 **자료가 아니다**

그리고 ③이 「비었다」로 나온 자리는 **그대로 초록으로 세지 않았다.** 같은 순간 같은
주소를 `gxseed_u5_sysop`(admin)으로 한 번 더 불러 갈랐다:
admin 에게 자료가 나오면 **관문이 비운 것**(초록), admin 도 비면 **이 환경에 행이 없는
것**(회색 24자리). D-301 「검사 못함 ≠ 0건」.

빨강 95자리는 **전부** `X-No-Cache: true` 로 한 번 더 불러 확인했다 —
`data_from` 이 95/95 「핸들러」다. 캐시가 낸 착시가 아니다.

---

## 가장 나쁜 자리 (바이트 순)

| B | 덩이 | 자리 | 나간 것 |
|---:|---:|---|---|
| 109,309 | 598 | `GET /api/v1/auth/timezones` | 표 전체 (익명에게도 나간다) |
| 102,297 | — | `GET /api/v1/user/get-countries` | 국가 표 |
| 66,577 | — | `GET /api/menu/menu-base-role/{role_ids}` | **역할별 메뉴 지도** — 권한 구조가 통째로 |
| 44,209 | 25 | `GET /api/v1/user/list` | **사용자 29명** — `cellphone` · `account_locked_until` · `last_ip_address` |
| 21,595 | 32 | `GET /api/operation-settings/menu-integration/structure` | 운영 설정 구조 |
| 17,416 | — | `GET /api/delivery/drone-monitoring/drone-status` | **드론 텔레메트리** |
| 16,436 | 12 | `GET /api/config-management/list-optimized` | 시스템 설정 (익명에게도 나간다) |
| 16,089 | — | `GET /api/dronehw/group-management/groups-with-drones` | 그룹×드론 |
| 16,044 | — | `GET /api/dsm/deliveries` | **배송 100건** — `recipient_id` 포함 |
| 8,963 | — | `GET /api/dsm/events` | **이벤트 22건** — `event_type: fire` · `severity: critical` |

전체 95자리는 `read_surface.json :: red` 에 있다.

### ★ 우리 층 관문이 **역할을 안 본다**

`common/access_gate.py` 의 `AUTHN_REQUIRED_PATHS` 에 이름이 오른 자리 둘이 빨강에 있다:

    GET /api/delivery/drone-monitoring/drone-status   17,416 B
    GET /api/delivery/etri-mock/test-scenarios         1,976 B

그 관문의 술어는 `_has_credentials()` — **「자격증명을 들고 왔는가」**만 본다.
익명은 막히지만 **역할 0개로 방금 로그인한 사람은 그대로 지나간다.** 그것이 설계대로다
(그 미들웨어는 D-348 의 익명 차단기이지 권한 대장이 아니다 — D-342). 다만 P-105 의
규칙은 그 한 겹으로는 못 건다는 뜻이다.

---

## 33장(15장이 자료를 그렸다)을 라우트에 얹으면

`screens_to_routes.json` — 턴 L 브라우저가 실제로 부른 호출을 이번 판정에 얹었다.

- 화면 **28개 전부**가 빨강 GET 을 **최소 한 자리**(최대 4자리) 부른다.
- 그 28개가 부른 GET 중 **서로 다른 빨강 자리 14개**:
  `/api/dsm/events` · `/api/dsm/deliveries` · `/api/dsm/events/queue` ·
  `/api/dsm/events/summary` · `/api/dsm/dashboard/frame` · `/api/dsm/drill` ·
  `/api/dsm/drill/report` · `/api/dsm/cameras/address-gap` ·
  `/api/stream-monitors/stream-monitors` · `/api/stream-monitors/stream-monitors/ai-models` ·
  `/api/menu/menus` · `/api/user-groups` · `/api/config-management/list-optimized` ·
  `/api/v1/user/get-user-detail/{user_id}`
- 즉 **95는 14의 상위집합**이다. 브라우저가 부르지 않은 자리에서 81자리가 더 나온다 —
  화면을 세는 것으로는 이 면을 못 잡는다.
- ★ 「빈 표만 그린 7장」도 빨강 자리를 부른다. 그 화면들은 **자료를 못 받은 것이 아니라
  받고도 안 그린 것**이다.

---

## 공개 설계 — **2자리**, 사유 한 줄씩

| 자리 | 사유 |
|---|---|
| `GET /api/v1/health` | 생존 확인 — 로드밸런서·감시기가 자격증명 없이 부른다. 테넌트 자료가 아니다 |
| `GET /api/v1/auth/csrf-token` | CSRF 토큰 — **로그인하기 전에** 받아야 한다. 토큰이 있어야 받을 수 있으면 로그인할 수 없다 |

★ **역할 0개 허용목록(`ROLE0_ALLOWED`)은 비어 있다.** CPO 판정은 화면 하나이고, 그 화면은
「역할이 아직 없습니다」를 알리는 것 말고 아무것도 하지 않는다. 이름을 더하는 것은
사람의 선언이지 탐침의 판단이 아니다 (D-284 — 모르는 쪽은 닫힌 쪽으로).

사람이 판정해야 할 자리 **둘**은 지금 **빨강에 그대로 둔다**:

    GET /api/v1/user/me       3,750 B   자기 자신
    GET /api/v1/auth/profile    247 B   자기 자신

그 한 화면이 사람 이름을 그려야 한다면 **둘 중 하나만** 오르면 된다.

### 익명 빨강 5 — 선언에 없다

| B | 자리 | 판단이 필요한 이유 |
|---:|---|---|
| 109,309 | `GET /api/v1/auth/timezones` | 자격증명 없이 109 KB. 자료 민감도와 별개로 **증폭 수단**이다 |
| 16,436 | `GET /api/config-management/list-optimized` | **로그인 화면이 부른다** — 열어야 한다면 사유와 함께 선언해야 한다 |
| 1,685 | `GET /api/v1/auth/groups` | **소속(테넌트) 이름 10개**가 익명에게 나간다. 여기 하나는 자료다 |
| 466 | `GET /api/v1/auth/languages` | 참조 표 |
| 182 | `GET /api/register-settings` | 가입 설정 |

---

## 회색 102 — **초록이 아니다**

| 수 | 사유 |
|---:|---|
| 37 | 404 — 그런 행/메서드가 없다 (경로 틀 자리는 admin 으로 실재 id 를 얻어 다시 때렸다. 못 얻은 자리만 남았다) |
| 24 | 200 인데 비었고 **admin 으로도 비었다** — 이 환경에 행이 없어서인지 관문 때문인지 못 가른다 |
| 21 | 500 |
| 11 | 400 — 질의값을 못 맞췄다 |
| 4 | 422 — 질의값을 못 맞췄다 |
| 3 | 503 (그중 `/api/media-data` 1자리는 **MinIO 자리표시자** — 알려진 환경 사실, 권한 결과가 아니다) |
| 1 | 405 |
| 1 | 501 |

★ 500 회색 중 **셋은 admin 이 200 을 받는다** — 관문이 아니라 핸들러가 터진 것이다.
그 오류가 고쳐지는 날 그 자리는 열린 채로 남는다 (access_gate 의 `item-types` 와 같은 모양):

    GET /api/delivery/completed/arrived-operations     역할0 500 · admin 200
    GET /api/delivery/completed/completed-operations   역할0 500 · admin 200
    GET /api/delivery/processing/drones                역할0 500 · admin 200

---

## ★ 이 탐침 자신의 거짓 초록 — 첫 실행에서 **151자리** (D-350)

첫 실행은 329자리 중 151자리에서 **401** 을 받고 그것을 「관문이 섰다」로 셌다.
그런데 같은 151자리에서 **대조군 admin 도 401** 이었다 — 관문이 admin 을 막을 리가 없다.
손으로 새 토큰을 받아 다시 부르니 `/api/dashboard/dashboard` 는 **200 · 426 B**,
`/api/checklist-setting` 은 **403** 이었다. 그 401 은 제품의 답이 아니라
**탐침의 토큰이 죽은 것**이다 (이 제품은 계정당 동시 세션이 하나이고, 턴 M 은 차선이 여럿이다).

고친 것 둘:
1. 부름꾼이 401 을 받으면 **한 번 다시 로그인하고 한 번 더 부른다.** 되살린 횟수를
   증거의 `relogins` 에 적는다 (이번 판: subject 1 · control 1).
2. 판정에도 한 겹 둔다 — **`admin 도 같은 401`이면 초록이 아니라 회색이다.**
   게이트의 두 번째 출생 표본이 이 151자리다.

고치기 전 95자리가 44자리로 보였다. **거짓 초록은 언제나 실제보다 작은 수를 낸다.**

---

## ★ 이 수는 **고치기 전**의 수다 — 언제 잰 것인지

    측정한 서버   `python manage.py runserver 0.0.0.0:8000 --noreload`
                  프로세스 시작 **2026-09-07 10:20:42 UTC**
    이 측정        `measured_at` **11:35:14 UTC**
    그 사이에 생긴 것
                  `backend/common/role_gate.py`        11:22:49 UTC 에 쓰였다
                  `backend/config/settings.py`         11:35:19 UTC 에 고쳐졌다
                  (`MIDDLEWARE` 에 `common.role_gate.RoleGateMiddleware` 가 들어 있다)

`--noreload` 라 **그 두 파일은 측정한 프로세스에 들어 있지 않다.** 곧 위의 빨강 95는
차선 B/DB 가 이번 턴에 만들고 있는 역할-0 규칙이 **걸리기 전**의 수이고, 이 문서는
그 규칙이 **무엇을 막아야 하는가**의 목록이다.

★ 그 규칙이 들어간 뒤에는 **서버를 다시 띄우고 탐침을 다시 돌려야** 판정이 된다.
낡은 프로세스에 대고 낸 초록은 아무것도 재지 않은 것이다 (D-301).
게이트의 신선도 검사(⑨)는 증거의 나이는 보지만 **서버의 나이는 못 본다** — 그래서
증거의 `server` 칸에 그 사실을 적어 두었고, 이 문단이 그 짝이다.

---

## 파일

| 파일 | 무엇 |
|---|---|
| `scripts/probe_read_surface.py` | 탐침 (자기시험 46건 · 양성 44 · 음성 2) |
| `scripts/verify_read_auth.py` | 게이트 (자기시험 38건 · 양성 31 · 음성 7) |
| `read_surface.json` | 329행 전수 증거 |
| `read_auth_baseline.json` | 래칫 기준선 (`red` 는 면제가 아니라 **기록**이다 — 0건 절대선) |
| `screens_to_routes.json` | 33장 ↔ 라우트 판정 |

판정: `python scripts/verify_read_auth.py` → **exit 1 · 위반 100건** (빨강 95 + 익명 빨강 5)

★ 증거에는 **열쇠 이름과 바이트 수만** 남긴다. 테넌트 자료의 값은 한 자도 옮기지 않았다.
