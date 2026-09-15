# P-141 — 로그인 뒤 첫 화면 = 역할의 홈 (구현 증거 · 차선 F · 턴 Q · 2026-09-15)

- 정본 사양: `docs/agent/evidence/P-131/역할_홈_사양.md` (재검토하지 않음 · WO-01 §2)
- **AS** = 로그인 안 함(차선 규칙 6 — HTTP 로그인 도구 금지). 역할 실림은 **DB 읽기 전용 탐침**으로 쟀다(아래 §2).
- 「첫 URL 4/4 · U1#1 초록」은 **아직 안 닫혔다** — 조율자 한 줄(`verify_click_completes`)이 누른 뒤를 봐야 초록이다.

## 1. 규칙 한 곳 — `frontend/src/features/nav/roleHome.ts::resolveHome()`

| 순서 | 규칙 | 결과 |
|---|---|---|
| ① | 사람이 고른 홈 `settings.home_screen_setting__path` + `home_screen_setting_id` (`'/'` 제외) | `{path}?menuId={id}` — 종전 규칙 그대로 |
| ② | 역할의 홈 — `roleNav.ts` 의 `bucketOf(roleCodesOf(…))` 재사용(새 표 없음) | 아래 표 |
| ③ | 역할을 못 읽음(모르는 역할 · 역할 0 · 역할 칸 없음) | 부르는 쪽 기본값 = 지금 가던 곳 |

| 사람 | 역할 코드 (`roleNav.ts:52-57`) | 데스크톱 | 휴대전화 | 라우트 등록 |
|---|---|---|---|---|
| U1 | `fire_user` · `surveillance_operation` · `operator` | `/dsm/queue` (`dsm2Routes.focusQueue`) | `/m/inbox` (`mobileRoutes.inbox`) | `App.tsx:681` · `:709` |
| U2 | `fire_admin` · `surveillance_order` | `/dsm/events` (`CustomRoutes.dsm.events`) | QR(지금 가던 곳) | `App.tsx:676` |
| U4 | `view_only_-_anyang` | `/dsm/events?period=d7` | QR | 같은 화면 · `EventList.tsx:221` |
| U5 | `admin` | `/dsm/dashboard` (`CustomRoutes.dsm.dashboard`) | QR | `App.tsx:673` |
| 모름 | — | `/profile` | QR(로그인) · `/profile`(RootRedirect) | — |

부르는 자리 셋 — 셋 다 이 함수만 부른다:

| 자리 | 넘기는 후보(앞이 먼저) | 옵션 |
|---|---|---|
| `features/login/LoginDesktop.tsx` (종전 124-130) | `[info(프로필 응답), user(로그인 응답)]` | desktop · fallback `/profile` |
| `App.tsx` `RootRedirect` | `userInfo`(저장소) | `isMobile` 따라 · fallback `/profile` |
| `features/LoginMobile/LoginMobile.tsx` (종전 100-110) | `[profile.data, userData]` | mobile · fallback QR · `honorSetting:false`(종전에 ①을 안 봤다) |

`dataQRCode` 가 붙은 로그인은 종전대로 QR 이 먼저다(두 로그인 화면 모두 규칙 앞에서 갈린다).

## 2. 「로그인 직후 역할이 실려 있는가」 — 가장 흔한 실패를 먼저 쟀다

| 자리 | `roles` 가 있는가 | 근거 |
|---|---|---|
| 로그인 응답 `body.user` (`POST /api/v1/auth/login`) | **없다** | dj-core `core/api/v1/auth.py` 의 `login_data` = 토큰·user_id·username·email·theme·timezone·language. `roles` 는 보안 기록용 `success_payload`(792-797)에만 |
| 프로필 응답 `getProfileAPI` = `GET /api/v1/user/get-user-detail/{id}` → rj-core `{success, data: body.user}` | **있다** | dj-core `core/api/v1/user.py:800-875` · `UserDetailSchema(fields="__all__", depth=2)` + `permissions=ArrayAgg('roles__code')` · rj-core 번들 `V1.profile` · `u = async (M) => { … data: L.user }` |
| 저장소 `userInfo` (데스크톱) | **있다** | `LoginDesktop` 이 `updateUserInfo(info)` — rj-core 리듀서는 **교체**(`a.userInfo = e.payload`) → 프로필 응답이 저장소가 된다 |
| 저장소 `userInfo` (휴대전화) | **없다** | `LoginMobile` 은 프로필을 받고도 저장소에 안 올린다 → 그래서 받은 `profile.data` 를 **직접** 넘긴다 |

[실측 2026-09-15 · 읽기 전용 Django 탐침 · gx-shell · 같은 스키마로 직렬화 · 값 출력은 역할 코드·키 이름뿐]

```
gxseed_u1_operator  roles: list ['fire_user']          permissions ['fire_user']          settings.home_screen_setting__path=None · _id=None
gxseed_u2_manager   roles: list ['fire_admin']         permissions ['fire_admin']         settings.home_screen_setting__path=None · _id=None
gxseed_u4_official  roles: list ['view_only_-_anyang'] permissions ['view_only_-_anyang'] settings.home_screen_setting__path=None · _id=None
gxseed_u5_sysop     roles: list ['admin']              permissions ['admin']              settings.home_screen_setting__path=None · _id=None
gxseed_u5_newop     roles: list ['fire_user']          permissions ['fire_user']          (U1 로 판정된다 — 이름과 역할이 다르다)
```

→ 넷 다 ①이 안 걸리고(고른 홈 없음) ②로 간다: U1 `/dsm/queue` · U2 `/dsm/events` · U4 `/dsm/events?period=d7` · U5 `/dsm/dashboard`.
종전 U1#1 이 `/profile` 이던 이유도 같은 표가 말한다 — ①이 비었고 ②가 없었다(사양 §1 「설정 누락의 부산물」).

## 3. 규칙 시험 — 42 passed · 0 failed

vitest/jest 가 `frontend/package.json` 에 없다(grep 0). 그래서 `gx-fe-build` 안에서 esbuild 로 `roleHome.ts`·`adapter.ts` 를 묶어 node 로 돌렸다.
`@/services/API` 는 rj-core 를 끌고 오므로 라우트 상수 대역으로 바꾸고, **대역 값은 원문(`services/API.ts:23-24`)과 문자열 대조 후** 쓴다.
스크립트는 저장소 밖(작업 임시 폴더)이고 컨테이너 임시 파일은 지웠다.

```
docker cp frontend/src/. gx-fe-build:/app/src
docker exec gx-fe-build node /tmp/ffe_rule_run.mjs
== 42 passed · 0 failed ==
```

덮은 것: 역할 홈 4(+U1·U2 대체 코드 3) · 여러 역할 → 넓은 쪽 · 대소문자 · ① 우선/무효 두 갈래 · ③ 다섯 갈래(로그인 응답만 · 역할 0 `[null]` · 모르는 역할 · null · `permissions` 만) · 휴대전화 여섯 · 어댑터 19(모양 셋 · 승격 전/후 · `{ko,en}` · 422 · 204 · AxiosResponse).

타입 검사: `npx tsc --noEmit -p tsconfig.app.json` — 바뀐 줄(`adapter.ts` · `api.ts` · `roleHome.ts` · `RootRedirect` 블록 · 두 로그인의 새 줄)에 오류 0. 세 파일에 남은 오류는 `rj-core` 선언에 없는 이름(`useAPILogin` · `CustomRouters` 등)의 **가져오기 줄**과 단추 속성 — 이번 변경 전부터 있던 것이다.

## 4. 안 정한 것 (사양 §5 — 표대로 두었다 · 선언)

- U2 「밤사이」 창 12h(`EventList.tsx:54`) ↔ 24h(`ShiftHandoverPanel.tsx:42`) — 홈은 `/dsm/events` 만 건다.
- U4 에 `?preset=` 도 걸 것인가 — 기간(`period=d7`)만 건다.
- U5 홈이 관제 대시보드가 맞는가 — CPO 사이드바 표 첫 줄(`/dsm/queue`)과 어긋난 채 사양대로 `/dsm/dashboard`.
- 휴대전화의 U2·U4·U5 는 지금 가던 곳(QR)으로 둔다 — 사양은 휴대전화 U1 만 정했다.

## 5. 게이트 기대식 (고치지 않았다 — 요청)

`scripts/verify_click_completes.py:140-142` U1#1 기대 문구 `["관제", "대시보드", "이벤트", "GuardianX"]` 는 `/profile` 시절의 추정이다.
`/dsm/queue` 로 떨어지면 정본 화면 문구는 `frontend/src/features/dsm/pages/FocusQueue.tsx:98` `HEADLINE = '지금 처리할 것 — 가장 급한 하나'` 다
(P-132 — 기대식은 정본 화면 문구에서 뽑는다).
