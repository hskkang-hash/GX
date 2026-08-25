# 계약 2 — 오류 응답과 인증 엔드포인트

**티켓**: W0-18 · **결정**: D-248 · D-212 · P-W0-18-1 · **버전**: 1.1 · **고정일**: 2026-08-25
**시험**: `backend/tests/test_api_contract.py` — 이 문서의 모든 표는 그 시험이 지킨다.
**실측 근거**: `docs/agent/evidence/W0-18/backward_compat_impact.md`

> **이 문서는 "이렇게 되어야 한다"가 아니라 "지금 실제로 이렇다"를 적는다.**
> 기재와 동작이 갈라지면 계약 시험이 먼저 빨개진다. 그때 **둘 다** 고친다.
> GS인증은 매뉴얼 기재와 실동작의 불일치를 결함으로 처리한다(지시서 §0.1-5).

---

## 1. 권한거부의 상태코드

### 1-1. 지금 (플래그 OFF · 기본값)

권한이 없는 사용자가 보호된 엔드포인트를 부르면 **HTTP 200 이 나간다.** 거부 사실은
본문에만 있다.

```http
GET /api/devices/devices-management
Authorization: Bearer <권한 없는 사용자>

HTTP/1.1 200 OK
Content-Type: application/json

{"success": false,
 "message": {"en": "Permission denied.", "ko": "권한이 거부되었습니다.", "vi": …, "th": …},
 "status_code": 403}
```

원인은 `core/role/permission.py` 의 `@path_permission` 이 거부를 **평범한 dict** 로
돌려주는 것이고, 그 파일은 §0.4 금지구역이라 고칠 수 없다(D-207 · D-248).

**⚠️ 그리고 그 200 은 라우트마다 모양이 다르다.** 세 가지다.

| 라우트 선언 | 권한거부 시 실제 응답 | 건수 (2026-08-24) | 건수 (지금) |
|---|---|---|---|
| `response=` 없음 | `200` + 위 본문 | 281 | **289** |
| `response=List[…]` | **`500`** (pydantic 이 dict 를 거절) | 7 | 7 |
| `response=<단일 스키마>` | **`200` + `{}`** — 거부 사실이 **사라진다** | 8 | **0** |

세 번째가 가장 위험했다 — 클라이언트도 감사 로그도 **거부됐다는 것을 알 수 없다.**
**2026-08-25 · P-W0-18-1 A 안 적용으로 0 이 됐다.** 8건(`report_template` 4 ·
`checklist_setting` 4)의 `response=<단일 스키마>` 선언을 뗐다. 그 선언은 성공 경로에
한 번도 적용된 적이 없었고(핸들러가 `BaseResponse` 를 돌려주므로 ninja 가 검증 없이
통과시킨다), 실제로 그 스키마를 통과한 것은 거부 dict 뿐이었다.
**OpenAPI 문서는 이 제거로 바뀌지 않았다** — 제거 전후 대조 실측
(`evidence/W0-18/response_decl_before_after.md`).

### 1-2. 플래그 ON — 실제 HTTP 상태로 승격

```
API_CONTRACT_PROMOTE_ERROR_STATUS = true   (환경변수 또는 config/settings.py)
```

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{"success": false, "message": {…}, "status_code": 403}
```

- **본문은 바뀌지 않는다.** 상태줄만 고친다 — 기존 클라이언트가 읽던
  `success`·`message`·`status_code` 가 그대로 남는다.
- `response=List[…]` 라우트의 **500 도 403 이 된다.**
- `response=<단일 스키마>` 부류는 **0 건이다**(P-W0-18-1). 그 부류가 남아 있는 동안에는
  응답 계층으로 복원할 수 없었다 — 거부 정보가 응답이 만들어지기 전에 소멸하기 때문이다.
  다시 생기면 `tests/test_api_contract.py::test_swallowed_routes_have_not_grown` 이 잡는다.

### 1-3. 승격되지 않는 것

`success` 가 **정확히 `false`** 이고 `status_code` 가 **400~599 정수**일 때만 승격한다.
아래는 승격하지 않는다 — 도메인 값이지 HTTP 상태가 아니기 때문이다.

| 본문 | 이유 |
|---|---|
| `{"success": false, "status_code": 3}` | 배송 진행단계(0~5) |
| `{"success": false, "status_code": "error"}` | 도메인 상태문자열 |
| `{"success": false, "status_code": 200}` | 4xx/5xx 가 아니다 |
| `{"status": "error", "status_code": 400}` | `success` 키가 없다 (`orders/views/order_views.py:1394`) |
| `{"success": true, "status_code": 403}` | 성공이라고 말하고 있다 |

### 1-4. 클라이언트가 지금 해야 할 일

**두 형태를 모두 다뤄라.** 플래그는 언제든 켜지고 꺼진다.

```ts
try {
  const res = await API.get(url);
  if (res?.success === false) { /* 200 으로 온 거부 — 플래그 OFF */ }
} catch (e) {
  if (e?.response?.status === 403) { /* 실제 403 — 플래그 ON */ }
}
```

`catch` 가 없으면 승격 후 **아무 일도 일어나지 않는 화면**이 된다(스피너 고착).
저장소 프론트에서 그런 지점 21곳을 실측했다 — 목록은 영향조사 §2-2.

---

## 2. 인증 엔드포인트

### 2-1. 자격증명 → 토큰: `/api/v1/auth/login` **을 쓴다**

```http
POST /api/v1/auth/login
Content-Type: application/json

{"username": "...", "password": "..."}
```

이미 다른 곳에서 로그인 중이면 `200` 에 `success:false` 와
`auth_status.existing_session:true` 가 실려 온다. 오류가 아니라 **선택 요구**다.

### 2-2. `/api/token/pair` — **쓰지 말 것.** 200 을 주지만 그 토큰은 동작하지 않는다

```http
POST /api/token/pair          →  200 {"username": …, "refresh": …, "access": …}
GET  <보호된 엔드포인트>
Authorization: Bearer <위 access>
                              →  401 {"detail": "Unauthorized"}
```

**기전**: `core/auth.py` 가 `if not user.token: raise HttpError(401, "Token expired")` 로
막는다. `user.token` 을 채우는 것은 `/api/v1/auth/login` 뿐이고 `token/pair`
(ninja_jwt 기본 엔드포인트)는 채우지 않는다.

> **연동 담당자에게**: 발급은 **성공**하고 **그 다음 호출이** 죽는다. 그리고 그 오류가
> `"Token expired"` 라 "방금 받은 토큰이 만료됐다"는 불가능한 이야기를 한다.
> 시계·TTL·서명키를 의심하지 말 것. **엔드포인트를 바꾸면 된다.**

핸들러는 §0.4 안이라 고칠 수 없다. 이 문서와 계약 시험이 유일한 방어다.

### 2-3. `/api/v1/auth/delete-session` — **현재 호출할 수 없다**

핸들러 인자가 `data: dict` 인데 ninja 는 그것을 **쿼리 파라미터**로 잡는다.
쿼리 문자열에서는 `dict` 를 만들 수 없으므로 어떤 형태로도 통과하지 못한다.

| 호출 형태 | 결과 |
|---|---|
| body `{"data": …}` | `422 missing · loc:["query","data"]` |
| `?data=x` | `422 dict_type` |
| `?data=<URL 인코딩 JSON>` | `422 dict_type` |
| `?session_id=x` | `422 missing` |

**대안**: 다른 위치의 세션을 끝내려면 `/api/v1/auth/login` 응답의
`auth_status.existing_session` 흐름을 쓴다. 핸들러는 §0.4 안이라 수정 불가.

---

## 3. 이 계약을 바꾸려면

1. `backend/tests/test_api_contract.py` 를 먼저 고친다 (시험이 정본이다).
2. 이 문서의 해당 표를 같은 커밋에서 고친다.
3. 라우트가 늘어 §1-1 의 분포가 바뀌면 `test_distribution_matches_evidence` 가
   먼저 빨개진다 — 영향조사 §1-1 도 같이 갱신한다.
