# `/users`·`/roles` 0행 · `create-user` 프리플라이트 401 — 원인과 넘길 자리

- 잰 사람: 차선 B (Backend/DB) · 턴 O · 2026-09-10
- **TARGET** = `http://localhost:8500` (`gx-nginx-e` → `gx-gunicorn-e`) ·
  대조군은 `http://localhost:8000` (gx-shell 안 runserver · nginx 없음)
- **AS** = `gxprobe_s` (role=`user`) · 자격 sha256 앞 12자 `b6ae237c2c7b`
- **SOURCE** = 살아 있는 서버 응답 + 개발 DB 읽기 + 저장소 원문

---

## A. `OPTIONS /api/v1/user/create-user` → 401 — **우리 층이다 (nginx 앞단)**

### 실측

| 요청(TARGET=8500) | 상태 | CORS 헤더 |
|---|---|---|
| `OPTIONS /api/v1/user/create-user` | **401** | **하나도 없음** |
| `OPTIONS /api/v1/user/update-user` | 200 | `access-control-allow-origin: http://localhost:3002` 외 |
| `OPTIONS /api/v1/auth/login` | 200 | 같은 헤더 |
| `OPTIONS /api/v1/user/create-user` **+ `Authorization` 헤더** | **200** | 있음 |

401 본문:

```json
{"detail":"Unauthorized","reason":"authentication required (front line)"}
```

`reason` 이 스스로 자리를 말한다 — **앞단(front line)** 이다. Django 는 관여하지 않는다:
nginx 를 뺀 대조군(8000)에서 같은 프리플라이트는 **200** 이다.

### 원인 (한 문장)

앞단이 `location = /api/v1/user/create-user` 에서 **자격증명 없는 요청을 401 로 끊는데**,
CORS 프리플라이트는 규격상 `Authorization` 도 쿠키도 **싣지 않는다** — 그래서 브라우저의
프리플라이트가 문 앞에서 잘리고 「사용자 추가」는 요청을 한 번도 못 보낸다.

### 자리 (파일 · 줄)

| 파일 | 줄 | 무엇 |
|---|---|---|
| `backend/common/front_line.py` | **81** | `CREDENTIAL_FOLD` — 자격증명 접기(`$http_authorization$http_x_api_key$cookie_sessionid`) |
| `backend/common/front_line.py` | 120–126 | 그 접기를 `location` 블록으로 찍는 자리 |
| `backend/common/access_gate.py` | **140** | `AUTHN_REQUIRED_PATHS` 에 `"/api/v1/user/create-user"` |
| `nginx/generated/gx-gate.conf` | 140·145 | **생성물** — 손으로 고치지 않는다 |
| `backend/common/access_gate.py` | 287 | 같은 구멍의 쌍둥이(미들웨어). 지금은 `CorsMiddleware`(MIDDLEWARE 1번)가 먼저 답해 안 닿지만, 순서가 바뀌면 **같은 401 이 Django 에서 다시 난다** |

### 고칠 한 줄 — ⚠ **차선 B 가 손대지 않았다**

이 자리는 인증 급소이고 이번 턴 **보안 차선이 잡고 있다**(지시서 제약). 그래서 코드를
고치지 않고 **넘긴다.** 고칠 모양은 하나다 — `front_line.py:81`:

```python
CREDENTIAL_FOLD = ('set $gx_cred "$http_authorization$http_x_api_key$cookie_sessionid"; '
                   'if ($request_method = OPTIONS) { set $gx_cred "preflight"; }')
```

그리고 `python scripts/ops_front_line.py --render` 로 다시 찍는다(생성물이라 손편집 금지).

- **왜 안전한가**: 앞단의 자기검사는 문자열 `"authentication required"` 와
  `gx_key_denied` 로 블록을 가른다(`front_line.py:235-253`) — `$request_method` 검사가
  하나 더 붙어도 그 판정은 흔들리지 않는다.
- **왜 구멍이 아닌가**: 프리플라이트에는 **본문이 없고 서버 상태를 못 바꾼다.**
  뒤따르는 실제 `POST` 는 자격증명을 싣고 오므로 앞단이 그대로 막는다.
- **함께 볼 것**: `access_gate.py:287` 의 쌍둥이에도 같은 면제를 두면 두 방어선이
  **같은 자리**를 덮는다(지금은 한쪽만 덮고 있고, 그 사실이 보이지 않는다).

---

## B. `/users`·`/roles` 0행 — **시간이 아니라 「누구로 들어갔나」였다**

세 가설(로그인 뒤 지연 · `?tab=list` · `/profile` 먼저 방문)이 기각된 이유가 여기 있다.
**셋 다 시간·경로 가설**이었고, 실제 변수는 **계정의 역할**이다.

### 실측 ① — 역할이 메뉴를 가른다 (개발 DB · 읽기)

`menu.Menu`: `/users`=3 · `/roles`=5. `menu.RoleMenu.permit_read`:

| 역할 | `/users` | `/roles` |
|---|---|---|
| `admin` (gxseed_u5_sysop) | **True** | **True** |
| `superuser` | True | True |
| `fire_admin` (gxseed_u2_manager) | True | (행 없음) |
| `view_only_-_anyang` (gxseed_u4_official) | **False** | **False** |
| `user` (gxprobe_*) | **False** | (행 없음) |
| `fire_user` (gxseed_u1_operator) | False | (행 없음) |

→ **29 users / 15 roles 가 보인 그 한 번은 `admin` 이었다.** 0행이 나온 나머지는
`view_only`·`user`·`fire_user` 다. 「간헐적」이 아니라 **계정별로 결정적**이다.
그리고 이 저장소는 **동시 접속 1개**라, 다른 차선이 같은 계정으로 로그인하면 내 창의
세션이 밀린다(`401 · reason_code=session_evicted`) — 사람이 보기에 「같은 조건인데 이번엔
0행」이 되는 이유가 이것이다. 이 문서를 쓰는 동안에도 두 번 밀렸다.

### 실측 ② — 거부가 **HTTP 200** 으로 나온다 (착시 ⑧ · dj-core)

TARGET=8500 · AS=gxprobe_s:

```
GET /api/roles/?page_size=25&current_page=1        → HTTP 200
{"success": false, "message": {"ko": "권한이 거부되었습니다."}, "status_code": 403}

GET /api/v1/user/list/?page_size=25&current_page=1 → HTTP 200 · count=30 · rows=25
```

`/api/roles/` 는 **막혔는데 200 이다.** 화면은 200 을 받고 목록 칸이 비었으니
**빈 상태도 오류도 못 그린다** — 「요청은 성공했고 0건」과 「권한이 없다」가 같은 응답이다.
이것이 W0-18 이 우리 층에서 8건 뗀 그 모양이고, 지금 남은 것은 **dj-core 쪽**이다.

- **자리**: dj-core `core/role/permission.py` **514** (`_check_path_permission` 실패 시
  `{"success": False, …, "status_code": 403}` 을 **200 본문으로** 돌려준다).
  설치본 경로: `/usr/local/lib/python3.11/site-packages/core/role/permission.py`.
- **§0.4 금지구역이라 고치지 않았다.** 고칠 한 줄은
  `return {"success": False, …}` → `raise HttpError(403, CommonMessage.COMMON_PERMISSION_DENIED)`
  (또는 `ninja` 응답 상태를 403 으로 세우는 것). 그러면 화면이 **「권한 없음」 문장**을
  그릴 수 있다(UX-31 의 넷 중 하나).

### 실측 ③ — 화면이 아예 요청을 안 낸다

nginx 접근 로그(`docker logs gx-nginx-e`, 브라우저 출처만)에서 SPA 가 `user/list` ·
`/api/roles` 를 부른 것은 **보존 구간 전체에서 한 번뿐**이다(`08/Sep 04:20:43`, 200).
나머지 방문에는 **그 줄 자체가 없다.** 메뉴 응답(`/api/menu/menus`)에 `/users`·`/roles`
가 없으면 화면이 `menu_id` 를 못 얻고, 그리드는 **조회를 시작하지 않는다** —
우리 층의 `frontend/src/features/Dashboard/utils/getPath.tsx:77-99` 가 `null` 을 내고,
그 뒤 그리드는 벤더(`rj-core`) 안이라 이 저장소에 없다.

### 그래서 무엇을 고치나 (차선 B 는 **아무 데이터도 안 바꿨다**)

1. **역할 설정**(우리 것): 이 화면들을 볼 사람의 역할에 `RoleMenu.permit_read=True` 를
   준다. ⚠ 그러나 **UX-28 이 「역할별 메뉴 허용 목록」을 일부러 좁혔다** — U4(view_only)가
   `/users`·`/roles` 를 못 보는 것은 **결함이 아니라 설계**일 수 있다.
   그러므로 이 한 줄은 **제품 결정**이고, 데이터 쓰기라서 차선 B 가 임의로 켜지 않았다.
   「사용자 추가」를 해야 하는 사람은 `admin`·`fire_admin` 계열이다.
2. **빈 상태 문장**(프런트 차선 · UX-31): 200+`success:false` 를 **권한 없음**으로 읽어
   문장을 그린다. 지금은 「0건」과 구별이 안 된다.
3. **dj-core**: `core/role/permission.py:514` 를 403 으로 — 위에 적었다.

---

## C. `GET /api/v1/user-groups/gen-schema?raw=false` → 422 — **dj-core**

```
GET /api/user-groups/gen-schema?raw=false             → 422
   {"detail":[{"type":"missing","loc":["query","group_id"],"msg":"Field required"}]}
GET /api/user-groups/gen-schema?group_id=4&raw=false  → 200
```

- **원인**: 핸들러가 `group_id: int` 를 **기본값 없이** 선언해 필수 질의 인자가 됐다.
  ninja 가 본문에 들어가기 전에 422 로 끊는다. FK 스키마 생성과는 무관하다.
- **자리**: dj-core `core/user/api.py` **503** (`def gen_schema(self, request, group_id: int, raw: bool = False)`).
  설치본 `/usr/local/lib/python3.11/site-packages/core/user/api.py`.
- **고칠 한 줄**: `group_id: int = None` + 본문 첫 줄에서 없을 때의 4xx 를 그 API 의
  봉투로 낸다. 그러면 「고르지 않았다」가 **422 원문**이 아니라 사람이 읽는 문장이 된다.
- **우리 쪽 자리**: 부르는 코드가 그룹을 고르기 전에 이 주소를 때린다. URL 상수는
  `frontend/src/services/API.ts:617`(`genGroupConfig`)이고, 실제 호출은 벤더 `rj-core`
  안이라 이 저장소에 없다 — 우리 층에서 막으려면 그룹 선택 전에는 부르지 않게 해야 한다.
