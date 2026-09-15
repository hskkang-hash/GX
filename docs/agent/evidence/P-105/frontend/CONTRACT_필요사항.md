# P-105 · 앞단이 **뒷단에 필요한 것** — 역할 0개 계정의 한 화면

발행: 2026-09-07 턴 M · 차선 C(앞단) · 수신: 차선 백엔드/DB

> **이 파일이 왜 여기 있나.** 지시는 「뒷단이 `docs/agent/evidence/P-105/backend/` 에
> 계약을 먼저 적는다. 그것을 읽고 맞춰라」였다. **그 자리는 이 턴이 끝날 때까지 없었다**
> [실측 — `ls docs/agent/evidence/P-105/` → 디렉터리 없음]. 그래서 지시의 나머지 절반을
> 한다: **앞단이 필요한 것을 적고, 그 사실을 보고에 그대로 말한다.**
> 아래는 요구가 아니라 **제안**이다. 뒷단이 다른 모양으로 지으면 앞단이 맞춘다 —
> 고쳐야 할 자리는 `frontend/src/features/session/rolePending.ts` **한 곳**이다.

---

## 0. 지금 상태 — **막는 일은 아직 아무것도 되어 있지 않다** [실측 2026-09-07]

역할이 0개인 계정(`gxprobe_e2e` · `user.roles` = `[]`)으로 로그인해, 33장이 부른 API 를
화면별로 그대로 다시 두드렸다. 원본: `before_roleless_api.json` (같은 폴더).

| | |
|---|---|
| 두드린 경로 | 28개 화면이 부른 API 전부 |
| **403 이 난 화면** | **3개뿐** — `surveillance-dashboard`(7건) · `configuration-management`(1건) · `flight-log-analysis`(1건) |
| 나머지 | **전부 200** |

그리고 그 200 안에 **실제 자료**가 들어 있다:

```
GET /api/dsm/events?limit=200            → 200 · "total": 22
     event_id · event_type(fire/flood/intrusion) · severity · occurred_at
     stream_monitor_name "시드 카메라 (검수용)" · snapshot_path
GET /api/stream-monitors/stream-monitors → 200 · 카메라 대장
     name "GD-150Q" · ip_source "rtsp://…" · group__name "ETRI-Group" · drone_id
```

★ 즉 **「전역 거절 처리기가 그 15장을 받는가」는 아직 물을 수 없다.** 거절이 나오지
않으므로 받을 것이 없다. 앞단의 처리기는 서 있고(`PermissionDeniedNotice` · P-88),
403 이 오면 뜬다 — 실제로 `surveillance-dashboard` 에서는 **뜬다**. 나머지는
**서버가 200 을 주는 동안 뜰 수 없다.**

★★ 그리고 앞단이 이번에 세운 화면(아래 1절)은 **자물쇠가 아니다.** 화면을 안 그려도
문은 열려 있고, 개발자도구의 `fetch` 한 줄이면 위 22건이 그대로 나온다.
**닫는 것은 뒷단의 일이고, 그 일은 아직 안 되어 있다.**

---

## 1. 앞단이 이번 턴에 세운 것

| 무엇 | 자리 |
|---|---|
| 판정 한 줄 (`roles` 가 **배열이면서 길이 0**일 때만 참) | `frontend/src/features/session/rolePending.ts :: hasNoRoles` |
| 그 하나뿐인 화면 | `frontend/src/features/session/RolePendingScreen.tsx` |
| 관문 안 **모든** 화면의 부모에서 갈라친다 | `frontend/src/App.tsx :: PrivateLayout` |

[실측 2026-09-07 · 번들 `6cf2c19` · 3002] 역할 0개 계정으로 종전에 **자료를 그리던**
여섯 경로(`/dsm/events` · `/dsm/dashboard` · `/profile` · `/notam` ·
`/multi-stream-monitor` · `/m/inbox`)를 밟아 **일곱 장 모두** 이 화면이 떴다
(`shots/role0_run.json` · 못 찍은 자리 0 · JS 오류 0건).
역할 있는 계정 둘(`admin` · `fire_user`)은 **영향이 없다** — 제 화면을 그대로 본다 [실측].

---

## 2. 앞단이 **모르는 것 둘** — 그래서 서버가 말해야 하는 것

CPO 가 정한 문장은 이것이다:

> 「역할이 아직 없습니다 · **관리자(이름)**에게 역할 부여를 **요청했습니다**」

이 한 줄이 앞단이 모르는 사실을 **둘** 주장한다:

1. **내 관리자가 누구인가** (이름) — 앞단은 모른다.
2. **그에게 요청이 갔는가** (「요청했습니다」는 완료된 과거다) — 앞단은 모른다.

그래서 **지금 화면은 그 문장을 쓰지 않는다.** 머리줄만 쓰고 둘째 줄은 내려 적는다:

> 「아직 역할 부여를 요청하지 못했습니다. 관리자에게 직접 알려 주세요.」

이것이 지금 찍힌 화면이다(`shots/role0_dsm_events_desktop.png`).
**이름을 지어내거나 「요청했습니다」를 조건 없이 적으면 그것은 안내가 아니라 거짓말이고**,
안 간 알림을 갔다고 적으면 사람은 기다리기만 하고 아무도 부르지 않는다.

---

## 3. 제안하는 계약

### `GET /api/v1/auth/role-pending`

```jsonc
// 200 — 역할이 0개인 계정
{
  "success": true,
  "status": 200,
  "role_pending": true,
  "administrator": {            // 정할 수 없으면 null. 그러면 앞단은 이름을 안 쓴다
    "name": "홍길동",
    "email": "admin@example.org",   // 선택 — 있으면 화면에 mailto 로 붙인다
    "department": "재난안전과"        // 선택
  },
  "notified": true,             // ★ 알림이 **실제로 나갔을 때만** true
  "notified_at": "2026-09-07T11:30:00Z"
}
```

- `role_pending: false` — 이 계정에 역할이 있다. 앞단은 이 화면을 띄우지 않는다.
- `administrator: null` — 관리자를 못 정했다. **이름 없는 문장을 만들지 않는다.**
- `notified: false` — 아직 안 갔다. 앞단은 「요청했습니다」를 **쓰지 않는다.**

앞단이 읽는 자리: `rolePending.ts :: readRolePending()`.
**모르면 안전한 쪽으로 떨어진다** — `notified` 는 `true` 라고 **명시**될 때만 참이고,
관리자 이름이 없으면 `notified` 도 강제로 거짓이 된다.

### ★ 반드시 지켜야 할 것 하나 — **이 문은 403 의 예외다**

「나머지는 전부 403」 규칙에 이 문이 걸리면, **역할 0개 계정이 볼 수 있는 유일한 화면이
자기 내용을 못 받는다.** 이 문 하나는 **역할 0개 계정에게 200 이어야 한다.**
(같은 이유로 로그인·로그아웃·`/api/v1/user/me` 도 열려 있어야 한다 — `me` 의 `roles`
칸이 이 화면을 띄우는 판정의 입력이다.)

### 알림 — **한 번**

CPO: 「관리자가 알림을 **한 번** 받는다」. 이 문이 화면이 뜰 때마다 불리므로,
발송은 **계정당 한 번**으로 눌러 주기를 바란다(새로고침 때마다 관리자에게 메일이
가면 그 알림은 곧 무시된다). 앞단은 이 문을 **화면이 뜰 때 1회** 부른다.

---

## 4. 뒷단이 다른 모양으로 지었다면

고칠 자리는 **`rolePending.ts` 한 파일**이다 — `ROLE_PENDING_PATH` 와
`readRolePending()` 둘뿐이고, 화면(`RolePendingScreen.tsx`)과 갈라치는 자리
(`App.tsx`)는 손대지 않아도 된다. 그러라고 세 파일로 나눴다.
