# P-105 계약 — **역할 없는 계정은 아무것도 보지 않는다** (차선 B · 2026-09-07 턴 M)

> ★ 이 문서를 **코드보다 먼저** 적었다. 앞단(차선 F)이 화면을 같은 턴에 만들고 있고,
>   계약을 말로 주고받으면 갈린다. 갈린 계약은 「붙였는데 안 붙는」 화면이 된다.

## 0. 제품 결정 (CPO)

- 새 계정의 기본 상태는 **역할 0 = 로그인만 된다.**
- 역할 0 계정이 닿는 화면/문은 **정확히 하나** — 「역할이 아직 없습니다 —
  관리자(이름)에게 역할 부여를 요청했습니다」 그리고 **관리자에게 알림 1건.**
- 나머지 전부 **403**, 기존 전역 거절 처리기를 그대로 탄다.

## 1. 역할 0 의 정의 — **판정은 한 곳에서만 난다**

`backend/common/role_gate.py::has_no_role(user)`

    참이 되는 조건 (넷을 모두 만족)
      ① 인증된 사용자다 (`is_authenticated`)
      ② `user.roles` 가 **비어 있다** (M2M · 이 제품에는 단수 `role` 필드가 없다)
      ③ `is_superuser` 가 아니다        ← DB 플래그 관리자를 잠그지 않는다
      ④ `is_staff` 가 아니다            ← 관리자 화면 운영자를 잠그지 않는다

⚠ `getattr(u, "role", None)` 은 **이 제품에서 언제나 None 이다.** 그 None 을 측정으로
  읽은 것이 이 사고를 세 턴 동안 덮었다. 판정은 `roles`(M2M)로만 낸다.

## 2. 유일하게 열린 문 — 역할 대기 화면의 문

```
GET /api/v1/access/role-pending
```

- 인증 필요(익명 → 401). 역할이 **있는** 사람이 불러도 200 이고 `state: "has_roles"` 다.
- 200 응답:

```json
{
  "state": "pending",
  "message": "역할이 아직 없습니다 — 관리자(홍길동)에게 역할 부여를 요청했습니다.",
  "user":   { "username": "gxprobe_e2e", "display_name": "gxprobe_e2e" },
  "roles":  [],
  "administrator": {
    "name": "홍길동",
    "username": "gxseed_u5_sysop",
    "source": "tenant_admin | global_admin | none"
  },
  "notification": {
    "sent": true,
    "already_sent": false,
    "channel": "audit",
    "requested_at": "2026-09-07T20:11:03+00:00"
  }
}
```

- ⚠ **관리자의 주소(email)는 싣지 않는다.** [실측 2026-09-07 · 처음 만들 때는 실었고
  `admin@guardianx.com` 이 역할 0 계정에게 그대로 나갔다.] 이 화면의 계약은
  「관리자에게 **요청했습니다**」이지 「연락하세요」가 아니다 — 알림은 서버가 보냈다.
  쓸 일 없는 남의 연락처를 권한 0 계정에게 내주는 것은 이 절이 막으려는 그 부류다.
- `administrator.name` 이 **화면의 「관리자(이름)」 자리에 그대로 들어간다.**
  이름을 앞단에서 짓지 않는다(GX-COPY 규칙 1). 관리자를 못 찾으면
  `source: "none"` · `name: ""` 이고, 그때 `message` 는 이름 없는 문장으로 나간다.
- `message` 는 **서버가 짓는다.** 앞단은 그대로 그린다.
- ⚠ **이 화면은 다른 문을 부르면 안 된다.** `/api/menu/menus` ·
  `/api/config-management/list-optimized` · `/api/user-groups/gen-schema` 등
  SPA 가 평소 부팅에 부르는 문은 역할 0 에게 **전부 403** 이다. 역할 대기 화면은
  이 응답 하나로 자족해야 한다.

## 2-b. 관리자가 읽는 문 (앞단이 관리 화면을 만들 때 쓴다)

```
GET /api/v1/access/role-requests      ← 전역/테넌트 **관리자만**. 아니면 403
```
```json
{ "count": 3,
  "requests": [ {"audit_id": 188008, "user_id": 105,
                 "reason": "역할 부여 요청 — 수신 admin (경로 global_admin)"} ] }
```
★ 이 문이 없으면 알림을 **쓰기만 하고 읽을 자리가 없다** — `verify_dormant.py` 가
실제로 그렇게 잡았다(「잠든 채 태어났다」 · D-377). **함수는 문이 아니다.**

## 3. 관리자 알림 — **1건 · 중복 없음**

- 자리: `backend/common/role_request.py::notify_admin(user)`
- ⚠ `logger_name` 접두는 **`guardianx.` 여야 한다** — `common/evidence_chain.py::CHAIN_PREFIX`.
  다르면 체인에 못 잇고, 못 이으면 감사 쓰기가 예외로 끝나 **알림이 남지 않는다**
  [실측 2026-09-07 · `gx.role_request` 로 적었다가 통째로 실패했다].
- 채널: **감사 대장 한 줄** (`common.audit_writer.write`,
  `logger_name="gx.role_request"`, `action="role_request"`, `outcome=DENIED`).
  관리자는 `common.role_request.pending_requests()` 로 전건을 읽는다.
- 중복 억제: 같은 계정에 대해 **이미 남아 있으면 다시 쓰지 않는다**
  (`already_sent: true`). 「알림 1건」이 계약이고, 새로고침마다 1건은 계약 위반이다.
- 실패는 삼키지 않되 화면을 죽이지 않는다: 알림 쓰기가 실패하면
  `notification.sent=false` + `notification.error` 로 **응답에 보인다.**

## 4. 나머지 전부 — 403 의 모양

```
HTTP 403
{
  "success": false,
  "status_code": 403,
  "code": "role_required",
  "detail": "Forbidden",
  "message": { "ko": "역할이 아직 없습니다 — 관리자에게 역할 부여를 요청했습니다.",
               "en": "This account has no role yet. An administrator has been notified." },
  "role_pending_url": "/api/v1/access/role-pending"
}
```

- **본문에 테넌트 자료가 한 자도 없다.** 카메라 이름도 사건 id 도 사용자 목록도 없다.
- `message` 를 **다국어 객체**로 보낸다 — 앞단의 기존 전역 거절 처리기
  (`frontend/src/features/session/permissionDenied.ts::messageOfDenial`)가
  `message.ko` 를 그대로 읽는다. **앞단을 한 줄도 안 고쳐도 띠가 뜬다.**
- `code: "role_required"` 가 「이 403 은 역할 0 이다」의 표지다. 앞단은 이 값을 보고
  역할 대기 화면으로 보낸다. 다른 403(권한 부족)과 갈리는 자리가 이 한 값이다.

## 5. 역할 0 에게도 열려 있는 것 — **손으로 적은 목록** (`ROLE_ZERO_ALLOWED`)

로그인 절차 자체를 막으면 아무도 못 들어온다. 그래서 이 목록만 비켜 준다:

    /api/v1/auth/login            /api/v1/auth/logout
    /api/v1/auth/csrf-token       /api/v1/auth/refresh-token
    /api/v1/auth/end-session      /api/v1/auth/delete-session
    /api/v1/auth/change-password  /api/v1/auth/otp/verify
    /api/v1/auth/otp/generate-qr  /api/v1/auth/otp/reset
    /api/token/refresh            /api/token/verify
    /api/v1/access/role-pending   ← 그 하나의 문

목록에 **없는 것**을 적어 둔다 — 지금 자료가 나가는 자리들이다:
`/api/v1/auth/profile` · `/api/v1/auth/data-for-profile` · `/api/v1/auth/account` ·
`/api/v1/auth/groups` · `/api/v1/auth/departments` · `/api/v1/auth/teams`.
넓은 규칙(`AUTHN_SURFACE`)이 이것들을 덮고 있었고, 그 아래에 사고가 숨어 있었다 —
`access_gate` 가 P-83 에서 같은 것을 겪었다. **손으로 적은 이름이 규칙보다 세다.**

## 6. 되돌리기 (D-212)

    settings.ROLE_GATE_ENABLED = False    # 또는 환경변수 ROLE_GATE_ENABLED=false

False 면 미들웨어가 경로에 있어도 **한 요청도 안 막는다.** 역할 대기 문은 남는다
(문이 남는 것은 사고가 아니다 — 막는 것만 되돌린다).
