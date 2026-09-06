# P-74 — `/wall` 배선 실측 · 사이드바 U2·U4·U5 · 미선언 배지 · 빈/오류 문구 대조

- 집행: 차선 C(Frontend) · **2026-09-06 턴 G** · 근거: 세종 판정 **P-74 · P-67**
- 차선 이름: `DB_TEST_NAME=test_gx_c` · 포트 **8400**(+ 8401 · 아래 §6) · 탐침 `gxprobe_c`
- 만든 것: `frontend/src/features/dsm/wallToken.ts`(새) ·
  `frontend/src/features/dsm/pages/SystemSettings.tsx`(새) ·
  `docs/agent/evidence/P-74/capture_p74.py`(새 · 이 문서의 화면을 만든 탐침)
- 고친 것: `frontend/src/App.tsx` · `Wall.tsx` · `routes.ts` · `api.ts` · `useCameraPulse.ts` ·
  `backend/config/settings.py`(CORS 한 줄 · §1-㉠) · `backend/common/product_menus.py` ·
  `backend/stream_monitors/management/commands/seed_role_users.py` ·
  `scripts/verify_sidebar.py` · `scripts/verify_seed_roles.py` · `docs/design/GX-COPY_v1.md`

---

## 1. `/wall` — **브라우저가 처음으로 그 문을 열었다** [실측]

직전 턴(UX-24a)이 세운 것은 **서버 면**이었다. 그 문서 §8 이 스스로 적어 두었다:
「브라우저로 `/wall` 을 띄워 본 것이 아니다 — 앞단이 아직 `X-GX-Wall-Token` 을 안 싣는다.」
이번 턴이 그 한 줄을 실었고, **싣자마자 아무것도 안 나갔다.**

### ★ ㉠ 막힌 것은 서버도 화면도 아니라 **프리플라이트**였다 [실측 · 1차 촬영]

```
[P-74] OK   토큰으로 /wall — 화면 — 「월 표시 토큰으로 열림」 있다
[P-74] FAIL 토큰으로 /wall — 요청 — 머리글자를 실은 200 이 **0건**이다.
            우리 API 기록 1건: [('/api/config-management/list-optimized', 200, False)]
```

화면은 떴고, 「월 표시 토큰으로 열림」도 떴고, 화면 오류도 0건이었다. **그런데 우리 API 로
나간 요청이 한 건도 없었다.** 커스텀 머리글자가 실린 다른 출처 요청은 브라우저가 먼저
**예비 요청(OPTIONS)** 을 보내고, 허용 목록에 그 이름이 없으면 진짜 요청은 **아예 나가지
않는다.** 서버 탐침은 서버에서 서버로 불렀으므로 이 겹을 한 번도 안 지났다.

- 뿌리: `settings.CORS_ALLOW_HEADERS` 에 `x-gx-wall-token` 이 없었다.
- ⚠ **같은 자리에 두 번째로 걸렸다.** 바로 위 `x-no-cache` 가 D-341 때 똑같이 걸렸고,
  그 주석이 「세 자리가 다 옳아 보여서 아무도 안 봤다」고 적어 두었다.
- 고침: 이름을 손으로 적지 않고 `common.wall_token.WALL_TOKEN_HEADER` **한 곳에서 읽는다.**
  두 벌로 적으면 이름이 바뀌는 날 증상이 **똑같이 「요청 0건」**이고 원인은 안 보인다.

### 닫는 조건 — 넷을 **함께** 잰다 [실측 · 2차 촬영 · exit 0]

월 화면은 로그인 세션으로도 **겉이 똑같이** 뜬다. 그래서 글자 하나로 단언하지 않는다.

```
[P-74] OK 토큰 없이 /wall      — 도착 …/login · 월 화면 글자 없다      ← 관문이 그대로 산다
[P-74] OK 토큰으로 /wall 화면   — 「월 표시 토큰으로 열림」 있다
[P-74] OK 토큰으로 /wall 요청   — 머리글자를 실은 문 2건 · 200 2건
                                 (/api/dsm/cameras/pulse · /api/dsm/events/queue)
[P-74] OK 토큰으로 /wall 세션   — 로그인 문을 **한 번도 안 불렀다**
[P-74] OK 토큰으로 /wall 자격증명 — 머리글자와 로그인 자리를 함께 실은 요청 0건
```

기록 전문: `capture_p74_report.json` 의 `wall_calls`.

| 화면 | 파일 |
|---|---|
| 토큰이 **없는** 브라우저 (로그인으로 튕긴다) | `shots/wall_without_token.png` |
| 토큰을 **든** 브라우저 (1920×1080 · 실제 사건이 그려진다) | `shots/wall_with_token.png` |

### 무계정 링크 금지를 깨지 않았다

월 표시 토큰은 서버가 서명해 발급하고 **12시간**에 죽고 **읽기 문 둘**만 여는 자격증명이다.
토큰이 없는 브라우저에는 아무것도 안 열린다 — 위 첫 줄이 그 사실이다.
주소로 받은 토큰은 **받은 즉시 주소창에서 지운다**(`adoptWallToken`): 관제실 화면은 사진에
자주 찍히고, 주소창에 남은 토큰은 사진 한 장이 곧 토큰이 되는 자리다.

---

## 2. ★ 월 화면이 **못 가져온 밤에 「평온합니다」라고 적고 있었다** — 고쳤다

`Wall.tsx` 머리말이 처음부터 못박은 문장이 있다: 「멈춘 화면은 「사건이 없다」와 구별되지
않는다 — 이 화면에서 가장 위험한 고장이다.」 그런데 **정작 이 화면의 두 칸이 그 고장을
하고 있었다.**

```tsx
// 종전 — 첫 호출이 실패하면 cards 는 0장이고, 그래서 이 줄이 뜬다
{queue.state !== 'loading' && cards.length === 0 ? (
  <div>지금 열려 있는 이벤트가 없습니다 — 평온합니다.</div>
) : null}
```

머리 위 빨간 상자는 「불러오지 못했습니다」라고 말하는데, **본문 세 칸은 평온하다고 말한다.**
3m 밖에서 읽히는 것은 큰 글자 쪽이다. 지도 칸도 같은 모양이었다(「지도에 표시할 위치가
없습니다」). 이제 「0건」은 **가져왔을 때만** 말한다:

| 상태 | 큐 칸 | 지도 칸 |
|---|---|---|
| 가져왔고 0건 | 지금 열려 있는 이벤트가 없습니다 — 평온합니다. | 지도에 표시할 위치가 없습니다. |
| **못 가져왔다** | **지금 처리할 것을 불러오지 못했습니다.** | **지도에 표시할 위치를 불러오지 못했습니다.** |

---

## 3. 사이드바 — **역할 넷 전부를 실제 로그인으로 찍었다**

### ㉠ U5 시드 사람이 이번 턴에 처음 생겼다 (실제 HTTP 경로)

`seed_role_users` 에 U5(`admin` · K3 `MANAGER` 프리셋)를 더했다. 심는 문은 종전 그대로
**하나**다 — `POST /api/v1/user/create-user`. ORM 우회로는 없다.

```
[SEED] POST http://127.0.0.1:8400/api/v1/user/create-user → 200
[SEED]   U5  gxseed_u5_sysop   역할=admin   프리셋=MANAGER   OK
[SEED] 새로 만든 사람 1명 · 이미 있던 사람 3명
```

★ 왜 필요했나: 그전까지 **U5 만 시드 계정이 없어서** `verify_sidebar` 의 「두 눈 대조」가
U1·U2·U4 셋에서만 돌았다. 즉 **U5 의 70줄은 아무도 로그인해서 본 적 없는 재현**이었다.
`admin` 은 테넌트 역할이지 전역 관리자가 아니다 — 이 사람도 `is_superuser=False ·
is_staff=False` 다. 전역 관리자를 시드로 만들면 그 계정은 격리를 지나가고, 그때부터
이 저장소의 테넌트 시험은 전부 뜻을 잃는다.

### ㉡ ★ **심자마자 판정기가 빨개졌고, 그 빨강이 옳은 물음이 아니었다** [실측]

```
FAIL K2 수신자  규칙은 있는데 **닿는 사람이 0명**인 역할: admin
```

`verify_seed_roles` ④는 시드 역할 **전부**에 critical 수신자가 1명 이상 있기를 요구했다.
U1·U2·U4 에는 옳다 — 경보를 받아 움직이는 사람들이다. 그런데 K2 규칙 어디도 `admin` 을
가리키지 않는다. 빨강을 지우는 가장 빠른 길은 `admin` 에게 critical 규칙을 만드는 것이고,
**그러면 판정기가 알림 정책을 발명한다** — 재난 경보를 누가 받는가는 세종의 판정이지
시드의 것이 아니다(D-264 와 같은 모양).

그래서 규칙을 만들지 않고 **선언 칸**을 뒀다: `SEED_PEOPLE[…]["alarm_destination"]`.
⚠ 면제가 아니다 — **칸을 안 적으면 종전대로 「경보가 갈 자리」로 본다**(엄한 쪽이 기본값).
자기시험이 양성·음성 양쪽을 먹는다(선언하면 초록 · 안 하면 여전히 빨강).

### ㉢ U5 사이드바에 **우리 화면 한 줄이 더 섰다**

P-61 이 적은 U5 자리 「백업·보존」은 턴 F 에 **화면이 없어서** `P61_NO_SCREEN_YET` 에
선언으로 남아 있었다. 이번 턴에 화면(`/dsm/system`)이 생겨서 **표로 옮겼다.**
지운 것이 아니라 **옮긴 것**이고, 옮겨 간 자리를 `P61_SCREEN_ARRIVED` 가 적는다 —
지우기만 하면 「P-61 이 적은 스물한 자리」의 셈이 조용히 하나 줄어든다.

```
행: 새로 1 · 고침 0 · 그대로 10   연결: 새로 1 · 켬 0 · 그대로 34
새 행 #142 보존·백업 설정 → /dsm/system
```

### 닫는 수 [실측 · `verify_sidebar.py` exit 0]

```
  OK   제품 메뉴 행      U1 5줄 · U2 7줄 · U4 2줄 · U5 4줄
  OK   라우트 실재       우리가 심은 줄 전부가 실재 라우트에 닿는다
  OK   우리 대장의 말     금지 낱말 0건 · 영문 메뉴명 0건
  OK   U1 상한          관제요원 사이드바 5줄 (상한 9)
  OK   두 눈 대조        **역할 4개**에서 링크 표와 실제 로그인이 같다   ← 3 → 4
  [실측] U5 사이드바 최대 71줄 (제품 최소 4줄) · admin 로 로그인하면 71줄(제품 4)
```

| 역할 | 화면 |
|---|---|
| U1 관제요원 (`fire_user`) | `../UX-25/shots/sidebar_U1_gxseed_u1_operator.png` |
| U2 관제팀장 (`fire_admin`) | `../UX-25/shots/sidebar_U2_gxseed_u2_manager.png` |
| U4 재난안전과 (`view_only_-_anyang`) | `../UX-25/shots/sidebar_U4_gxseed_u4_official.png` |
| U5 관리자 (`admin`) | `../UX-25/shots/sidebar_U5_gxseed_u5_sysop.png` |

⚠ U5 의 71줄 중 67줄은 **인수 자산**이고 상당수가 영문이다. UX-21 은 U1·U2·U4 에서만
끊었다 — U5 를 끊을지는 이 차선이 정할 일이 아니다(관리자가 그 화면들을 실제로 쓴다).

### ㉣ 촬영 중에 만난 것 — **세션 칸 하나가 화면 결함으로 보인다** [실측]

첫 촬영에서 역할 넷이 전부 「로그인 뒤에도 로그인 화면이다」로 기록됐다. 원인은 화면이
아니라 **바로 앞에서 `verify_sidebar` 가 같은 계정으로 로그인해 두었기 때문**이다:

```
POST /api/v1/auth/login  (end_previous_session 없이)
→ 200 {"success": false,
       "message": "You have an active session in another location...",
       "auth_status": {"existing_session": true}}
```

화면은 로그인 화면에 머무르며 **확인 창**을 띄운다. 촬영기는 그것을 「화면이 안 떴다」로
기록했고, 그 기록은 거짓이다 — 없던 것은 화면이 아니라 **빈 세션 칸**이었다.
찍기 전에 `end_previous_session` → `logout` 으로 칸을 비우고, **그래도 확인 창이 뜨면
확인을 누르는 길**을 함께 뒀다(다른 차선이 그 사이에 들어올 수 있다).

---

## 4. P-67 미선언 배지 — **세 상태를 뭉치지 않았다**

`/dsm/system` 「보존·백업 설정」(U5). 판정문 그대로: 「미선언 테넌트 = 「미선언」 상태로
화면(U5 시스템)에 빨강 배지 · 파기·백업 돌지 않음.」

| 상태 | 화면 | 뜻 |
|---|---|---|
| 선언됨 | 값 + **누가 정했나** | 값만 보이면 다음 사람이 출처를 못 되짚는다 |
| **미선언** | 빨강 배지 + **무엇이 안 도는지** 한 줄 | 아무도 정하지 않았다 |
| **서버 신호 대기** | 회색 배지 + 「선언되지 않았다는 뜻이 아닙니다」 | **우리가 못 읽는다** |

★ 셋째 칸이 이 화면의 요점이다. 셋을 둘로 접으면 신호가 끊긴 날 화면이 「미선언」이라
적고, 관리자는 **이미 정해 둔 값을 다시 정하러 간다.** 그러고도 화면은 여전히 빨갛다.

### 무엇이 실재하고 무엇이 없나 [실측 2026-09-06]

| 칸 | 문 | 지금 |
|---|---|---|
| 영상 보관 기간 | `GET /api/dsm/law/retention` — **실재한다** | 이 환경은 **선언돼 있다**(개발·스테이징 선언 · 차선 E 의 `config/retention_seed.py`). 그래서 빨강이 **안 뜬다** — 그것이 옳다 |
| 백업 목적지 · 일정 · 보관 기간 · 복구 시험 | `GET /api/dsm/ops/backup/declaration` — **없다** | **백엔드 신호 대기.** 설정에는 서 있으나(개발·스테이징) 화면에 내주는 문이 없다 |

★ **없는 문을 있는 척하지 않았다.** 404 를 「미선언」으로 그리지 않고 회색으로 그린다.
화면 쪽 낱말은 「서버 신호 대기」다 — 「백엔드」는 우리가 우리 서랍을 부르는 이름이라
사용자 본문에 쓰지 않는다(사전 §4). 이 문서의 낱말과 화면의 낱말이 다른 이유가 그것이다.

★ **입력칸을 만들지 않았다.** 선언을 받는 문이 없는데 입력칸을 그리면, 그것은 눌러도
아무 일도 안 일어나는 단추이고 「선언했다」는 착각을 만든다.

### 화면 둘 — **두 장은 다른 사실이다**

| 파일 | 무엇의 증거인가 |
|---|---|
| `shots/u5_system_undeclared.png` | **이 환경의 지금 상태.** 보관 기간은 선언돼 있고, 백업 넷은 「서버 신호 대기」다 |
| `shots/u5_system_undeclared_injected.png` | **빨강 배지가 실제로 그려진다**는 사실. 미선언 응답을 **주입해서** 찍었다. ⚠ 이 환경이 미선언이라는 뜻이 **아니다** |

주입이 필요했던 이유: 선언된 환경에서는 빨강이 안 뜨고, 그러면 「코드에 있다」와
「화면에 뜬다」가 구별되지 않는다. 그리고 1차 주입은 **아무 일도 안 일어났다** —
예비 요청(OPTIONS)까지 답해 주지 않았기 때문이다. §1-㉠ 과 **정확히 같은 자리**다.

---

## 5. 오류·빈 문구 사전 대조 — **문자열이 같은 화면은 0건. 그러나 한 화면이 같은 그림을 그렸다**

사전: `docs/design/GX-COPY_v1.md`(정본) · 강제: `scripts/verify_ui_copy.py`.
대상: `features/dsm/pages/*` · `features/mobile/pages/*` 15장(주석 걷어낸 뒤).

### ★ 빨강 — 「빈」과 「오류」가 **같은 그림**이던 화면 : **1장** (이번 턴에 고쳤다)

| 화면 | 무엇이 같았나 |
|---|---|
| `Wall.tsx` | 문자열은 달랐지만 **못 가져온 상태에서 빈 상태 문구가 떴다**(§2). 이 화면만 `StateBoundary` 를 안 쓰고 칸을 손으로 짰고, 손으로 짠 조건이 「로딩이 아니고 0장」이었다 |

**지금 남은 빨강(문자열이 동일한 화면): 0건.** 나머지 열넷은 공용 `StateBoundary` 가
상태로 갈라 그린다 — 빈은 `Empty`, 오류는 빨간 `Alert` + 「다시 시도」이고, 오류에는
반드시 사유가 실린다.

### 주황 — 빈 상태가 **기본 문구**로 떨어지는 자리 (사전 규칙 3 미달)

사전은 「없는 것은 없다고 적는다 — 없는 것이 **무엇**인지 적는다」이고, 공용 기본값
「표시할 항목이 없습니다.」는 무엇이 없는지 안 말한다.

| 화면 | 빈 상태에 닿는가 | 지금 문구 |
|---|---|---|
| `Metering.tsx` 달별 사용량 표 | 닿는다(0행 가능) | 표 부품의 기본 빈 그림 — **우리 사전 밖이다** |
| `CameraAddress` · `CameraImport` · `DrillMode` · `SystemSettings` | **안 닿는다** (`isEmpty` 를 안 주므로 빈 상태 자체가 없다 — 한 덩이 자료라 「0건」에 뜻이 없다) | 기본값이 서 있으나 그려지지 않는다 |

→ **손댈 곳은 `Metering` 하나**다. 이번 턴에 안 고쳤다: 그 파일은 차선 E 의 것이고
같은 턴에 같은 파일을 두 차선이 만지면 충돌한다. **다음 턴 한 줄.**

### 빈 상태 문구가 제 이름을 말하는 화면 (초록 · 8장)

`CameraGrid`(등록된 카메라가 없습니다) · `ControlDashboard`(최근 이벤트가 없습니다) ·
`EventDetail`(발송 기록이 없습니다) · `EventList`(조건에 맞는 이벤트가 없습니다) ·
`FocusQueue`(지금 열려 있는 이벤트가 없습니다 — 평온합니다) ·
`PrivacyRequests`(접수된 청구가 없습니다) ·
`MobileEventDetail`(이 사건에는 영상 구간 참조가 없습니다 — 서버가 404 로 답했습니다) ·
`MobileInbox`(이 테넌트에 남은 발송 기록이 0건입니다)

★ 여덟 중 넷이 괄호로 **「요청은 성공했고 0건입니다」**를 함께 적는다. 그 괄호가
이 절이 재려는 것을 화면 안에서 이미 말하고 있다.

⚠ 이 대조는 **소스를 읽어서** 했다. 화면에 오류를 **주입해서** 재는 것은 차선 Q 의
`walk_states.py`(P-69)가 이번 턴에 만든다 — 두 벌을 두지 않는다.

---

## 6. 어떻게 돌렸나 · 못 한 것

```bash
# ① 번들 (기본 힙으로는 조용히 죽는다)
docker cp frontend/src gx-fe-build:/app/
docker exec -e GX_COMMIT=$(git rev-parse HEAD) gx-fe-build sh -lc \
  'cd /app && NODE_OPTIONS=--max-old-space-size=6144 \
     npx vite build --outDir dist_c --emptyOutDir'      # ✓ 1m 28s · 산출물 **221 파일**
#    ⚠ 1차 빌드는 `GX_COMMIT` 없이 돌렸고, 그 번들은 하단에 **「버전 알 수 없음」**이
#      뜨고 게이트가 찾는 `GX_COMMIT:<40자리>` 리터럴이 **없었다**. 다시 구웠다.
#      번들 도장: GX_COMMIT:c86b678dfda96ebcdc764da212e54fc9a7a42a59 (= HEAD · commit_sha)
#      ⚠ 이 번들은 **HEAD + 이 차선의 미커밋 변경**이다. HEAD 를 다시 구운 것과
#        바이트가 같지 않다 — 병합 뒤 조율자가 한 번 더 굽는다.
docker cp gx-fe-build:/app/dist_c <tmp>; docker cp <tmp>/. gx-shell:/app/_fe_dist_c
#    저장소 쪽 backend/_fe_dist_c/ 221 파일 · **gitignore 확인함**(git status 0건)

# ② 차선 서버
runserver 8400 (시드용 HTTP) · SPA **3404**(/app/_fe_dist_c — 배치용 번들)
runserver 8401 · SPA 3403(/app/_fe_dist_c_probe)          ← 아래 ⚠
#  ⚠ 3402 는 **죽어 있다.** 도장 찍은 번들로 다시 굽느라  를
#    했고, 그 자리를 작업 디렉터리로 들고 있던 정적 서버가 함께 죽었다.
#    과정을 죽이지 않는 규칙이 있어 **그 자리를 치우지 않고 3404 로 새로 띄웠다** —
#    조율자가 3402 를 거두어 주기 바란다. 숨기지 않는다.

# ③ 시드 · 판정
python manage.py seed_role_users --peer gxprobe_e2e --base-url http://127.0.0.1:8400
python manage.py seed_product_menus --dry-run && python manage.py seed_product_menus
python scripts/verify_sidebar.py            # exit 0
python scripts/verify_seed_roles.py         # exit 0  (컨테이너에서)

# ④ 발급 · 촬영
python manage.py wall_token issue --user gxseed_u1_operator --note "…"
GX_WALL_TOKEN=… GX_SEED_ROLE_PASSWORD=… python /docs/agent/evidence/P-74/capture_p74.py \
    --web http://127.0.0.1:3403 --api http://localhost:8401     # exit 0 · 11장
```

### ⚠ 왜 포트가 둘인가 — **숨기지 않는다**

CORS 한 줄(§1-㉠)은 `settings.py` 에 있고, 이미 떠 있는 `runserver --noreload` 는 그것을
안 읽는다. 공용 8000 과 이 차선의 8400 을 **죽이지 않기로** 했으므로(과정 금지 규칙)
**새 프로세스 8401** 을 띄웠다. 번들은 부르는 주소를 빌드 시각에 굽기 때문에
촬영용 번들 한 벌을 `VITE_API_URL=http://localhost:8401` 로 따로 만들었다.

- 저장소에 심는 번들 `backend/_fe_dist_c` 는 **기본(8000) 그대로**다 — 배치용은 이쪽이다.
- 촬영용 `_fe_dist_c_probe` 는 **컨테이너 안에만** 있고 저장소에 없다.
- 두 번들의 차이는 **API 기준 주소 문자열 하나**다. 이 절이 재는 것(머리글자가 실리는가 ·
  월이 열리는가 · 배지가 뜨는가)은 그 문자열과 무관하다.
- ⚠ 그래도 **같은 번들로 찍은 것이 아니다.** 8000 을 재기동할 수 있는 사람이 한 번 더
  찍으면 이 각주가 없어진다.

### 못 잰 것

1. **단위 시험을 못 돌렸다 — 환경이다.** `test_gx_c` 에서 **모든** 시험 모듈이 같은 자리에서 죽는다:
   `django.core.management.base.CommandError: App 'user' does not have migrations.`
   내 파일과 무관한 `tests/test_auth_surface.py` 도 똑같이 8건 오류다.
   작업복사본의 `backend/conftest.py` 가 **지금 다른 차선이 고치는 중**(+100줄 · P-71 시험 DB
   우회층 · `tests/test_s_conftest_bootstrap.py` 새로 생김)이고, 그 손이 끝나기 전에 잰 수다.
   **초록으로 세지 않는다** — 회색이다. 병합 뒤 `test_c_product_menus.py` ·
   `test_c_menu_exposure.py` · `test_s_wall_token.py` 를 다시 돌려야 한다.
2. **월 토큰 두 테넌트 교차 확인**은 여전히 못 했다(이 환경에 월 계정이 하나다 · UX-24a §8 그대로).
3. **`Metering` 빈 표 문구**(§5 주황)는 안 고쳤다 — 남의 차선 파일이라 다음 턴 한 줄.
4. **U5 사이드바 67줄의 인수 자산**은 안 끊었다. 끊을지는 이 차선의 판정이 아니다.
5. 월 토큰 계정으로 `gxseed_u1_operator` 를 썼다. **좁은 전용 계정**을 쓰는 것이 옳고,
   그 판정은 UX-24a §8 이 적어 둔 대로 아직 안 내려졌다.

### 되돌리는 법

```bash
# 앞판 배선만 끄기 — 서버는 그대로
settings.WALL_TOKEN_ENABLED = False        # 토큰 자체를 끈다(종전 규약)
# 사이드바 한 줄 내리기(행은 남는다)
python manage.py seed_product_menus --unlink
# U5 시드 사람 지우기(표식 셋을 다 갖춘 행만)
python manage.py seed_role_users --peer gxprobe_e2e --purge
```
