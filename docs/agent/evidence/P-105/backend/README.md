# P-105 — 역할 없는 계정이 실자료를 읽던 자리 (2026-09-07 턴 M · 차선 Backend/DB)

> 이 문서의 수는 전부 **실측**이다. 잰 명령과 원문 파일을 같이 적었다.
> 잰 서버: `http://localhost:8000` (컨테이너 `gx-shell` · `runserver --noreload` · `config.settings`)
> 계약(앞단과 맞춘 것): `CONTRACT.md` — **코드보다 먼저 적었다.**

---

## 1. 반경 — 무엇을 어떻게 셌나

**정적 grep 이 아니다.** 런타임 열거다 — 등록된 API 객체를 타고 내려가 오퍼레이션을 센다.

| 세는 것 | 도구 | 전 | 후 |
|---|---|---|---|
| ninja 오퍼레이션 | `common.tenant_scope.enumerate_operations()` | **705** | **707** (+2 = 새 문 둘) |
| 서로 다른 경로 | 같은 열거의 `{path}` | **578** | **580** |
| `NinjaAPI` 인스턴스 | `common.tenant_scope._iter_ninja_apis()` | **22** | **23** |
| URL 패턴 전수 | `django.urls.get_resolver().url_patterns` 재귀 | **876** | **881** |

**전역 규칙 한 겹이 닿는 반경 = 707 오퍼레이션 전부** (`/api/` 밖 오퍼레이션은 **0개**다 —
열거해 보니 707 이 전부 `/api/` 접두다). 그중 실제로 「역할 0 도 통과」로 손으로 적은 것은
**13경로**(`role_gate.ROLE_ZERO_ALLOWED`)이고, 나머지가 403 이다.
(그 13 안에 역할 대기 문 하나가 있다. 관리 대장 문
`/api/v1/access/role-requests` 는 **목록에 없다** — 역할 0 은 그것도 403 이다.)

⚠ `access_gate.AUTHN_SURFACE`(로그인 면 넓은 규칙)는 **30 오퍼레이션**을 덮는다.
그 30 을 통째로 비켜 주지 **않았다** — 그 안에 `/api/v1/auth/profile` ·
`data-for-profile` · `groups` · `departments` · `teams` · `account` 처럼 실자료를 내는
자리가 있다. 넓은 면제 아래에 좁은 사고가 숨는 것을 `access_gate` 가 P-83 에서 이미
겪었다. 그래서 **이름을 손으로 적었다**(13경로).

재현:
```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
  python -c "import django;django.setup();
from common.tenant_scope import enumerate_operations,_iter_ninja_apis
ops=enumerate_operations(); print(len(ops), len({o.path for o in ops}), len(list(_iter_ninja_apis())))"'
```

---

## 2. 전 → 후 — **다섯 계정으로 같이 잰다. 한 계정은 측정이 아니다**

표본: **화면이 실제로 부르는 53자리** (`docs/agent/evidence/D-386/screen_routes.json` —
브라우저가 33화면을 그리며 부른 것 전부, 로그인 제외) + 새 문 1자리 = **54자리**.

| 계정 (역할) | 전 [11:30:55] | 그중 200+실자료 | 후 [11:58:03] | 그중 200+실자료 |
|---|---|---|---|---|
| `gxprobe_e2e` (**역할 0** · 대상) | 200:35 · 403:10 · 404:5 · 502:1 · 503:3 | **21** | **200:1 · 403:53** | **0** |
| `gxseed_u1_operator` (fire_user) | 200:35 · 403:10 · 404:5 · 502:1 · 503:3 | 22 | 200:36 · 403:10 · 404:4 · 502:1 · 503:3 | 23 |
| `gxseed_u2_manager` (fire_admin) | 200:35 · 403:10 · 404:5 · 502:1 · 503:3 | 22 | 200:36 · 403:10 · 404:4 · 502:1 · 503:3 | 23 |
| `gxseed_u4_official` (view_only_-_anyang) | 200:35 · 403:10 · 404:5 · 502:1 · 503:3 | 22 | 200:36 · 403:10 · 404:4 · 502:1 · 503:3 | 23 |
| `gxseed_u5_sysop` (admin) | 200:37 · 403:8 · 404:5 · 502:1 · 503:3 | 28 | 200:38 · 403:8 · 404:4 · 502:1 · 503:3 | 29 |

원문: `p105_before_final.json` · `p105_after_8000.json` · `p105_after_8000_nocache.json`

관리 대장 문(`/api/v1/access/role-requests`)을 더한 뒤 **55자리로 한 번 더** 잰 것:
`p105_after_final.json` [실측 · 캐시 우회]

    gxprobe_e2e          200:1 · 403:54                     200+실자료 **0**   ← 대장 문도 403
    gxseed_u1_operator   200:36 · 403:11 · 404:4 · 502:1 · 503:3   23
    gxseed_u2_manager    200:36 · 403:11 · 404:4 · 502:1 · 503:3   23
    gxseed_u4_official   200:36 · 403:11 · 404:4 · 502:1 · 503:3   23
    gxseed_u5_sysop      200:38 · 403:9  · 404:4 · 502:1 · 503:3   29

역할 보유 계정의 403 이 하나씩 는 것은 **대장 문이 관리자 전용**이어서다 —
네 계정 중 전역/테넌트 관리자로 판정되는 것은 없다(판정은 `common.tenant_roles`).

### 통제 4계정의 **자리별** 대조 — 회귀 0건

수만 같은 것이 아니라 **자리마다 같은지**를 봤다. 네 계정 전부 **차이 1건**이고,
그 1건은 매번 같다:

```
gxseed_u1_operator   차이 1건: 404 -> 200  GET /api/v1/access/role-pending
gxseed_u2_manager    차이 1건: 404 -> 200  GET /api/v1/access/role-pending
gxseed_u4_official   차이 1건: 404 -> 200  GET /api/v1/access/role-pending
gxseed_u5_sysop      차이 1건: 404 -> 200  GET /api/v1/access/role-pending
```

즉 **새로 생긴 문 하나뿐**이고, 그전에 읽던 것 중 못 읽게 된 것은 **없다.**
(`200+실자료`가 22→23, 28→29 로 는 것이 바로 그 문이다.)

### 전에 역할 0 에게 나가던 것 — 21자리 · 합계 **115,363바이트**

```
 24,999B  GET /api/advanced-table/grid-management/50/detail
 16,436B  GET /api/config-management/list-optimized
 11,270B  GET /api/print-format/.../fields/model?model_name=DeliveryOperation
  9,141B  GET /api/advanced-table/grid-management/9/detail
  8,963B  GET /api/dsm/events?limit=200                     ← 카메라명·시각·판정
  8,035B  GET /api/dsm/deliveries?limit=50
  5,489B  GET /api/advanced-table/grid-management/10/detail
  5,487B  GET /api/v1/user/get-user-detail/115              ← **남의 계정 전문**
  5,420B  GET /api/dsm/events?limit=50&mine=true
  4,146B  GET /api/dsm/events?limit=10
  3,945B  GET /api/dsm/events/queue?limit=200
  2,057B  GET /api/stream-monitors/stream-monitors
  2,031B  GET /api/user-groups/gen-schema?group_id=4&raw=false
  1,940B  GET /api/dsm/events?limit=50&response_state=occurred
  1,673B  GET /api/stream-monitors/stream-monitors/ai-models
  1,185B  GET /api/advanced-table/select-data?model_name=devicestatus…
    823B  GET /api/user-groups/?page_size=10000&current_page=1
    731B  GET /api/dsm/events?limit=50&event_type=camera_down,storage_high
    500B  GET /api/advanced-table/select-data?model_name=theme&distinct=true
    407B  GET /api/user-groups/gen-schema?group_id=4&raw=true
    260B  GET /api/dsm/dashboard/frame
```

**후: 이 21자리 전부 403 · 본문 399바이트 고정** (53자리의 403 본문 바이트가 전부 같은
399 다 — 요청에서 가져온 글자가 한 자도 없다는 뜻이다).

---

## 3. 캐시 처리 — **우회 + 대조** (D-341 착시 ⑦)

같은 순간에 헤더 없이 한 벌(`p105_after_8000.json`), `X-No-Cache: true` 로 한 벌
(`p105_after_8000_nocache.json`). **다섯 계정 × 54자리 = 270자리 전부 같은 수**였다 —
적중 본문이 답을 덮은 것이 아니다.

재기동도 확인했다:
```
python scripts/verify_live_freshness.py --api http://localhost:8000
  → 기동 2026-09-07 20:57:07 · 소스 최신 20:35:19 · 통과(초록)
python scripts/verify_live_freshness.py --api http://localhost:8010
  → 통과(초록)          ← 8010 도 같이 세웠다. 두 서버가 다른 코드로 서 있으면
                            다음 사람이 어느 쪽을 재는지에 따라 답이 갈린다
```
⚠ 전(前) 값이 **옛 코드에서 나온 것**이라는 증거: 재기동 전 8000 은
`GET /api/v1/access/role-pending` 에 **404** 를 냈다(그 라우트가 아직 없었다).

---

## 4. 옆자리 점검 — 표본 53자리 밖도 막히나 [실측]

53자리는 「화면이 부르는 것」이다. 규칙이 전역인지 확인하려고 표본 밖도 두드렸다:

| | 역할 0 | 익명(쿠키 없음) |
|---|---|---|
| `GET /api/delivery/processing/drones` (§0.4) | **403** | 401 |
| `GET /api/orders/banks` (§0.4) | **403** | 401 |
| `GET /api/terminals/terminals` (§0.4) | **403** | 401 |
| `POST /api/dsm/events/1/review` (쓰기) | **403** | — |
| `PUT /api/advanced-table/column-order` (쓰기) | **403** | — |
| `POST /api/v1/user/create-user` (쓰기) | **403** | — |
| `GET /api/v1/access/role-pending` | **200** | **401** |
| `GET /api/v1/auth/csrf-token` | **200** | 200 |

두 가지를 함께 못박는다:
- §0.4 금지구역(`delivery`·`orders`·`terminals`)도 **파일 한 줄 안 고치고** 덮인다 —
  D-348 이 만든 자리 그대로다.
- **익명의 답은 안 바뀌었다.** 401 은 여전히 401 이다. 「누구인지 모른다」와
  「누구인지는 아는데 안 된다」가 안 섞였다(D-290).

---

## 5. 관리자 알림 — **1건이 계약이고, 1건이었다** [실측]

```
GET /api/v1/access/role-pending  (역할 0 · 연속 두 번)
  1회차  notification: {"sent": ..., "already_sent": ..., "channel": "audit"}
  2회차  notification: {"sent": false, "already_sent": true}      ← 두 번째는 안 쓴다

common.role_request.pending_requests() 로 대장 조회:
  행수 1
  #188008  denied  role_request  actor=105  "역할 부여 요청 — 수신 admin (경로 global_admin)"
```

★ [실측 · 이 턴에 실제로 겪었다] 처음에는 `logger_name="gx.role_request"` 로 적었고
**알림이 통째로 실패했다**: `common/evidence_chain.py::CHAIN_PREFIX` 가 `guardianx.` 이고,
접두가 다른 행은 체인에 못 잇는다(LAW-08). 못 이으면 감사 쓰기 자체가 예외로 끝난다 —
즉 **알림이 남지 않는다.** 접두는 고를 수 있는 값이 아니다.

★ [실측 · 되돌린 것] 첫 판은 응답에 관리자 **주소**(`admin@guardianx.com`)를 실었다.
뺐다. 이 화면의 계약은 「관리자에게 **요청했습니다**」이지 「연락하세요」가 아니고,
쓸 일 없는 남의 연락처를 권한 0 계정에게 내주는 것은 이 절이 막으려는 그 부류다.
`tests/test_role_gate.py::test_administrator_contact_is_not_shipped` 가 못박는다.

---

## 6. 시험

`backend/tests/test_role_gate.py` — **28건 전부 초록** (무작위 순서에서도 초록).

| 무리 | 무엇을 못박나 |
|---|---|
| `RoleGateJudgeTest` (8) | 순수 술어. **양성**(역할 0 → 거절) · **음성**(역할 보유 → 안 건드림) · 로그인 면 개방 · **profile 면은 안 열림** · API 밖 안 건드림 · 되돌리기 · 본문에 자료 0자 · 앞단이 읽는 `message.ko` |
| `HasNoRoleTest` (5) | 역할 0 판정. 잠금 방지(`is_superuser`·`is_staff`) · 익명은 이 겹의 일이 아님 · **`getattr(u,"role")` 이 None 이라는 사실을 못박음**(그 필드가 생기는 날 빨개진다) |
| `RoleGateOverHttpTest` (6) | **호출로 확인한다**(D-210). Bearer 로 때린다 — 세션으로 재면 `JWTUserRestoreMiddleware` 를 건너뛴 판을 재게 된다. 캐시 우회(`X-No-Cache`) |
| `RoleRequestNotificationTest` (5) | 알림 1건 · 중복 억제 · 관리자를 못 찾으면 없다고 냄 · **주소를 안 실음** · **대장에 문이 있고 그 문은 관리자만 연다** |
| `MiddlewareOrderTest` (4) | 자리 — 캐시보다 바깥 · 접근 관문보다 안쪽 · 사용자 복원보다 아래 |

전 단위 시험: **1,227 passed · 0 failed · 3 skipped** (직전 기준선 1,199/0/3 + 새 28).

### ★ 이 시험이 **남의 시험을 죽였다** — 그리고 그것을 고쳤다

전수로 돌리자 `tests/test_s_evidence_chain.py` 가 **10건 빨개졌다**:

```
psycopg2.errors.ForeignKeyViolation: insert or update on table "logger_auditlogs"
  violates foreign key constraint "..._created_by_id_..._fk_user_coreuser_id"
  DETAIL:  Key (created_by_id)=(9) is not present in table "user_coreuser".
```

그 파일 단독으로는 **22건 전부 초록**이었다. 원인은 우리 쪽이다 — 이 파일의 HTTP
시험이 지나가면 **스레드 지역에 요청이 남고**, dj-core 의 `BaseModel` 이 저장할 때
그 요청의 사용자를 `created_by` 로 채운다. 그 사용자는 롤백으로 이미 없다.

**빨강은 남의 파일에 떴지만 더럽힌 것은 우리다.** 그래서 치우는 것도 우리 일이다:
`_CleanThreadLocal` 혼합으로 이 파일의 모든 `TestCase` 가 **앞뒤로** 비운다.
(시험을 약화시켜 초록을 만든 것이 아니다 — 상태를 치웠고, 그 파일의 22건은 그대로다.)

### 기존 시험이 한 번 빨개졌다 — **그 시험이 옳았다**

```
tests/test_route_tenant_scope.py::test_all_routes_are_tenant_scoped
  AssertionError: 649 not less than or equal to 648
  미분류 라우트가 늘었습니다 (648 → 649)
```
새 라우트를 스코프 선언 없이 올렸기 때문이다. 래칫이 제 일을 했다.
`@tenant_scoped(required=False, reason=…)` 를 달아 해소했고, **`required=False` 는
형식이 아니라 필요조건**이다: 역할 0 계정은 소속(group)이 없는 경우가 흔해서
(`gxprobe_e2e`.group is None) `required=True` 면 차단 모드에서 그 **유일한 문이
역할 0 에게만 잠긴다.**

---

## 7. 게이트가 잡은 것 — **셋 다 게이트가 옳았다**

### ㉠ `verify_dormant.py` — 「잠든 채 태어났다」 2건 (내 것)

```
· A backend/common/role_request.py::pending_requests
· C ROLE_REQUEST_ADMIN_NAME
```
- `pending_requests()` 는 **아무도 안 부르는 함수**였다. 알림을 대장에 쓰기만 하고
  읽을 자리를 안 만든 것이다 — **함수는 문이 아니다**(이 저장소가 `review_event` 로
  두 달을 겪은 그 모양). 문을 세웠다: `GET /api/v1/access/role-requests`(관리자만).
- `ROLE_REQUEST_ADMIN_NAME` 은 **뺐다.** 기본값이 비면 그 분기는 한 번도 안 도는
  코드이고, 값을 채우면 화면이 DB 가 아니라 설정 파일이 말하는 사람에게 연락하라고
  말한다. 못 찾으면 `source="none"` 으로 없다고 낸다.

⚠ 남은 dormant 1건 `backend/common/error_body.py::process_exception` 은 **턴 L(P-100)의
것**이고 이 차선이 만든 것이 아니다. 손대지 않았다 — 남의 턴 산출을 조용히 고치지 않는다.

### ㉡ `verify_route_alive.py` — 초록인데 **눈이 멀었다** [실측]

이 게이트는 `gxprobe_e2e`(= 역할 0)로 43라우트를 때리고, 판정 규칙이
`401/403 → 살아 있다` 다. 그래서 **우리 변경 뒤에도 exit 0** 이다:

```
[ALIVE] 토큰 대조 — 익명과 다른 응답 43/43건 · 토큰을 들고도 401/403 인 자리 43건
[ALIVE] 통과 — 43건 전부 살아 있다        ← 43건 **전부** 403 이다
```

같은 순간 **역할 보유 계정**으로 같은 게이트를 돌리면 실제로 잰다:

```
verify_route_alive.py --user gxseed_u4_official
  … 33건 200 「산다」 · 10건 401/403 · **죽은 라우트 2건** (503 media-data ×2 = MinIO 자리표시자)
  exit 1
```

즉 이 게이트의 보증이 **우리 때문에 비었다.** 그 게이트 자신의 머리말이 그 위험을
적어 두었다: *「401 을 「문지기가 섰다」로 읽는 규칙은 **우리가 들어갈 수 있을 때만**
옳다」*. 지금은 그 조건이 깨졌다.

★ **다음 사람이 할 일** — `scripts/verify_route_alive.py` 의 탐침 계정을 역할 보유
  계정으로 옮긴다(`GX_ROUTE_USER=gxseed_u4_official` + `GX_SEED_ROLE_PASSWORD`).
  `scripts/**` 는 이 차선의 소유가 아니라 손대지 않았다 — **적어서 넘긴다.**

### ㉢ `test_route_tenant_scope.py` — 미분류 라우트 래칫 (§6 참조)

---

## 8. 남긴 것 — **닫히지 않은 것**

- **표본은 53자리다. 707 전수가 아니다.** 이 53 은 「화면이 실제로 부르는 것」이고,
  전수 판정은 차선 Security 의 `scripts/verify_read_auth.py` 가 든다(그 파일은
  게이트 소유라 이 차선이 안 건드린다). §4 의 옆자리 점검이 「전역이다」의 근거이지
  전수 측정이 아니다 — 그렇게 적어 둔다(D-301).
- `/api/media-data`(503 ×3) · `/api/dsm/events/{id}/snapshot`(503) · `/api/proxy/notam`
  (502)은 **MinIO 자격증명이 자리표시자**여서 나는 수다. 전·후 양쪽에서 같고, 우리
  변경과 무관하다 — 전후 판정에서 뺐다.
- **앞단은 아직 이 계약을 안 그린다.** 서버는 403 + `code: "role_required"` 를 내고,
  기존 전역 거절 처리기가 `message.ko` 로 띠를 그린다. 「역할 대기 화면」 자체는
  차선 Frontend 가 같은 턴에 만들고 있다 — `CONTRACT.md` 가 그 접점이다.
