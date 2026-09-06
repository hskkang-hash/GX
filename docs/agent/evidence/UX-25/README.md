# UX-25 제품 화면이 사이드바에 있다 — 증거 (차선 C · 2026-09-05 턴 F)

세종 **P-61** 집행. 메뉴 정본은 dj-core DB 이므로 **코드가 아니라 시드(데이터)** 로 넣었다.
`core.menu.models.Menu` 도 `rj-core` 의 `CustomSidebar` 도 **한 줄도 고치지 않았다**(§0.4).

---

## 1. 착수 전 — 무엇이 없었나 [실측]

명령 그대로:

```bash
# 컨테이너 안에서 실제 로그인 → 사이드바를 받는다
#   (gx-shell 은 8000 을 게시하지 않는다. 호스트에서는 안 보인다)
docker exec -i gx-shell python -  <<'PY'
  POST /api/v1/auth/login   {"username": …, "password": …, "end_previous_session": true}
  GET  /api/menu/menus?page_size=200   (Bearer)
PY
```

| 계정 (역할) | 사이드바 | **제품 화면** |
|---|---|---|
| `gxseed_u1_operator` (U1 `fire_user`) | 12줄 | **0장** |
| `gxseed_u2_manager` (U2 `fire_admin`) | 14줄 | **0장** |
| `gxseed_u4_official` (U4 `view_only_-_anyang`) | 24줄 | **0장** |

12줄의 정체: 정찰 임무 · GaionGCS · 정찰거점 · 적재함 · 장치 구성 템플릿 · 항로 및 경로 ·
체크리스트 설정 · 관리자 설정 + 묶음 마디 넷. **한 줄도 관제요원의 화면이 아니다.**
`/dsm/*` · `/wall` · `/start` 로 시작하는 행은 `Menu` 표 131행 중 **0행**이었다.

---

## 2. 무엇을 만들었나

| 자리 | 파일 | 무엇 |
|---|---|---|
| **표(정본)** | `backend/common/product_menus.py` | 제품 메뉴 10줄 · 역할 묶음 · 순서 · 안 건 자리의 **선언** (**새 파일**) |
| **손(시드)** | `backend/stream_monitors/management/commands/seed_product_menus.py` | 표를 DB 로 옮긴다. 멱등 · `--dry-run` · `--show` · `--unlink` (**새 파일**) |
| **테넌트 배선** | `backend/common/product_menu_signals.py` | `UserGroup`·`Role` 이 생기면 표를 다시 세운다 (**새 파일**) |
| 배선을 잇는 곳 | `backend/stream_monitors/apps.py` | `ready()` 에 import 한 줄 (수신자는 import 될 때 등록된다) |
| **U1 상한** | `backend/common/menu_exposure.py` | `CUT_BUNDLES` 에 `P-61-U1` 묶음을 더했다(기존 두 묶음 무수정) |
| **판정기** | `scripts/verify_sidebar.py` | 다섯 수를 잰다 · `--self-test` 양성·음성 표본 9종 (**새 파일**) |
| 자격증명 한 자리 | `scripts/verify_route_alive.py` | `GX_SEED_ROLE_PASSWORD` 를 읽는 이름 목록에 더했다(두 벌을 안 둔다) |
| **시험** | `backend/tests/test_c_product_menus.py` | 14건 — 행·멱등·**테넌트 생성**·새 역할·소속 없음·남의 행 (**새 파일**) |
| 하단 한 줄 | `frontend/src/features/dsm/components/BuildVersion.tsx` 외 2 | 버전 옆에 **지원 창구** 한 줄 |

### 표 — 제품 메뉴 10줄 (순서는 「하루에 누르는 횟수」)

| 자리 | 이름 | 경로 | 보는 사람 |
|---:|---|---|---|
| -1000 | 지금 처리할 것 | `/dsm/queue` | U1 · U2 |
| -990 | 무슨 일 있었나 | `/dsm/events` | U1 · U2 · U4 |
| -980 | 카메라 격자 | `/dsm/cameras/grid` | U1 · U2 |
| -970 | 인계 메모 | `/handover` | U1 · U2 |
| -960 | 처음이세요 | `/start` | U1 · U2 |
| -950 | 관제 현황 | `/dsm/dashboard` | U2 |
| -940 | 훈련 모드 | `/dsm/drill` | U2 · U5 |
| -930 | 열람·삭제 청구 | `/dsm/privacy-requests` | U4 |
| -920 | 카메라 일괄 등록 | `/dsm/cameras/import` | U5 |
| -910 | 이번 달 사용량 | `/dsm/metering` | U5 |

`ordering` 이 음수인 이유: 인수받은 뿌리 행은 0 이상이고(`Dashboard` 0 · `Admin` 100)
정렬은 `order_by('ordering')` 하나다. **남의 행을 안 옮기고** 위에 서려면 음수 자리가 필요하다.

---

## 3. ★ 소속(`group`)을 안 붙였다 — 붙일 수가 없었다 [실측]

처음 설계는 「테넌트마다 한 벌」이었다. 두 실측이 그것을 막았다:

1. `RoleMenu` 는 `unique_together = ('menu','role')` 이다 — 같은 (메뉴,역할) 쌍의 행은
   **온 DB 에 하나뿐**이고, 테넌트마다 연결을 따로 둘 수 없다.
2. dj-core `list_menus` 는 메뉴를 **소속으로 가리지 않는다.** 소속 4(ETRI-Group)의 U1 계정이
   소속 6·7 의 메뉴(#128 · #130 · #101 · #104 · #96)를 그대로 봤다.

→ 테넌트마다 심으면 **모든 테넌트의 사본이 모두에게 보인다.** 테넌트 열이면
「지금 처리할 것」이 열 줄 뜬다. 그래서 정본은 **소속 없는 한 벌**(기존 53행과 같은 자리)이고,
그 결과 **새 테넌트는 만들어지는 순간 이미 본다**(구조로 닫힌다).

신호(`product_menu_signals.py`)가 여전히 필요한 자리는 둘이다:
① 표가 늘었는데 시드를 다시 안 돌린 채 테넌트가 생기는 날 ·
② **새 테넌트가 자기 역할을 새로 만드는 날**(이 DB 의 `role_role` 은 소속을 갖는다 —
`fire_user` 는 소속 6, `surveillance_order` 는 소속 5).
둘 다 `backend/tests/test_c_product_menus.py` 가 **실제로 만들어서** 잰다.

---

## 4. 실행한 명령 그대로

```bash
# ① 무엇을 할지 먼저 본다
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python manage.py seed_product_menus --dry-run'

# ② 심는다  → 행: 새로 10 · 고침 0 · 그대로 0   연결: 새로 34
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python manage.py seed_product_menus'

# ③ 두 번째 실행(멱등 확인) → 행: 새로 0 · 고침 0 · 그대로 10   연결: 새로 0 · 그대로 34
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python manage.py seed_product_menus'

# ④ U1 9장 상한 — **연결만 되끈다. 행은 한 줄도 안 지운다**
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python manage.py unlink_control_role_menus --bundle P-61-U1 --all-tenants --dry-run'
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings \
    python manage.py unlink_control_role_menus --bundle P-61-U1 --all-tenants'
#   1차 18개 · 2차 14개 = 32개 연결을 껐다 (장부: ../UX-21/menu_unlink_ledger.json)
#   되돌리기: python manage.py relink_control_role_menus --bundle P-61-U1 --all-tenants

# ⑤ 판정
python scripts/verify_sidebar.py --self-test     # 통과 · exit 0
python scripts/verify_sidebar.py                 # exit 0 (컨테이너로 자동 위임)

# ⑥ 시험
docker exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS test_gx_c;"
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_c gx-shell \
    python -m pytest tests/test_c_product_menus.py tests/test_c_menu_exposure.py \
    -q --nomigrations -p no:randomly        # 40 passed

# ⑦ 전 단위 시험 — 새 신호가 **남의 시험을 깨지 않는가**
#    (`Role`·`UserGroup` 이 생길 때마다 신호가 돈다 — 시험 픽스처 대부분이 그 둘을 만든다)
docker exec -e DJANGO_SETTINGS_MODULE=config.settings -e DB_TEST_NAME=test_gx_c gx-shell     python -m pytest tests -q --nomigrations -p no:randomly --ignore=tests/e2e
#   → **1138 passed · 2 skipped · 0 failed** (8분 8초) [실측 2026-09-05]

# ⑧ 게이트
./docs/agent/verify_gates.sh --gate forbidden-zone   # PASS · 금지구역 변경 0건
python scripts/verify_ui_copy.py                     # 통과 · 새 대장 언어 0건
```

---

## 5. 닫은 뒤 — 역할별 실측

`verify_sidebar_after.txt` (판정기 출력 그대로) · `sidebar_after_login.txt` (실제 로그인 전문).

| 역할 | 사이드바 (역할 코드별 최대) | **제품 화면** | 잰 방법 |
|---|---|---|---|
| **U1 관제요원** | **5줄** (`fire_user` 5 · `operator` 5 · `surveillance_operation` 5) | **5장** | 링크 표 + **실제 로그인** |
| **U2 관제팀장** | 21줄 (`fire_admin` 21 · `surveillance_order` 7) | **7장** | 링크 표 + **실제 로그인** |
| **U4 재난안전과** | 26줄 (`view_only_-_anyang` 26) | **2장** | 링크 표 + **실제 로그인** |
| **U5 관리자** | 70줄 (`admin` 70) | **3장** | **링크 표만** — 시드 계정이 없다 |

U1 은 이제 **다섯 줄 전부가 우리 제품**이고 전부 한국어다. 12 → 5, 제품 0 → 5.

### ★ 두 눈 대조가 잡은 것 — 계정 하나로 재면 못 보는 자리

처음 `P-61-U1` 묶음은 `gxseed_u1_operator`(역할 `fire_user`)의 화면만 담았다.
판정기의 **두 눈 대조**가 그것을 잡았다:

```
FAIL 두 눈 대조   U1 링크표 19줄(제품 5) ≠ 로그인 5줄(제품 5)
```

역할 코드별로 다시 재니 `fire_user` 5줄 · `surveillance_operation` 5줄 · **`operator` 19줄**.
`operator` 역할을 가진 사람(이 DB 에 열둘)은 배송 대시보드·협력사 관리·도킹 스테이션을
그대로 보고 있었고, **아무 계정으로도 재 본 적이 없었다.**
계정 하나로 재고 「닫았다」고 적었으면 그것이 거짓 초록이다.

---

## 6. 안 건 자리 — **선언이다** (면제가 아니다)

P-61 의 표 스물한 자리 중 **여덟은 화면이 없다.** 없는 화면에 메뉴를 걸면 사이드바에
「눌러도 아무 데도 안 가는 줄」이 남는다 — `menu_exposure.py` 가 「Media Viewer」에서
이미 만난 고장이다. 그래서 안 걸고 이름을 적는다
(`common/product_menus.py::P61_NO_SCREEN_YET`):

| P-61 이 적은 자리 | 왜 안 걸었나 |
|---|---|
| 요원별 현황 (U2) | 화면 없음. `/dsm/dashboard`(**관제 현황**)로 근사해 걸었다 — 「요원별」이라 적으면 없는 것을 있다고 말하는 것이다 |
| 설정(임계값·알림 규칙·시험) (U2) | 임계값·알림 규칙을 여는 우리 층 화면이 없다 |
| 보고서(월간 1쪽·HWPX) (U2·U4) | 월간 1쪽은 서버가 낸다. 그리는 화면이 없다 |
| 이벤트 검색 (U4) | 목록의 거르개는 있으나 검색 화면이 따로 없다 |
| 감사 기록 (U4) | 화면 없음 |
| 시스템(맥박·용량·생존) (U5) | 운영 도구는 있으나 화면이 없다 |
| 알림 규칙·채널 (U5) | 화면 없음 |
| 백업·보존 (U5) | 화면 없음(`scripts/ops_backup.py` 는 도구이지 화면이 아니다) |

**화면은 있으나 일부러 안 건 자리**: `/wall`(월 모드 — 대형 화면에는 마우스가 없다) ·
`/dsm/cameras/address`(P-61 표에 없다) · `/m/inbox`(U3 · 사이드바 없는 화면).

**이미 있어서 새로 안 만든 자리**: `/users`(『User Management』 #3) · `/roles`(『역할 관리』 #5) —
P-61 U5 의 「사용자·역할」·「기존 화면(래핑)」이 이것이다.

---

## 7. 하단 한 줄 — **사이드바가 아니라 화면 하단이다**

P-61 은 「전 역할 **사이드바 하단**」이라 적었다. 그 자리에는 **못 붙였다**:
사이드바는 인수 부품 `rj-core` 의 `CustomSidebar` 가 통째로 그리고 그 파일은 §0.4 금지구역이다.
`SidebarProps` 에 `children` 이 선언돼 있으나 `App.tsx` 의 호출은 그것을 쓰지 않고,
부품이 그 자리를 어디에 그리는지도 우리가 못 본다.

그래서 **화면 하단 오른쪽**(기존 `BuildVersion`)에 지원 창구 한 줄을 더했다:

```
버전 3d40cf6 · 장애 신고 창구 미등록
```

P-61 이 이 줄로 얻으려던 것(「전 역할이 늘 볼 수 있는 자리」)은 그대로다. 오히려 넓다 —
사이드바가 없는 화면(월 모드·로그인·온보딩·모바일)에서도 보인다.
**「사이드바 하단」이라 적으면 거짓이므로 「화면 하단」이라 적는다.**

지원 창구 값은 배포가 준다(`GX_SUPPORT` / `VITE_GX_SUPPORT`). 저장소에 기본 전화번호를
두지 않는 이유: 기관마다 다른 그 번호는 반드시 늙고, 늙은 번호로 건 전화는 **막다른 골목**이다.
빈 값이면 화면은 「지원 창구 미등록」이라 적는다 — 「버전 알 수 없음」과 같은 규약이다.

⚠ **못 쟀다**: 이 한 줄을 **번들로 찍어 눈으로 보지 못했다**(프런트 빌드·캡처는 이 턴에
안 돌렸다). 소스는 들어갔고, 화면에 뜨는 것은 다음 캡처가 확인한다.

---

## 8. 되돌리는 법

```bash
# 메뉴를 사이드바에서 내린다(행은 그대로 · 칸만 꺼진다)
python manage.py seed_product_menus --unlink
# U1 에서 끊은 인수 자산을 되살린다(장부대로 · 끊기 전에 꺼져 있던 것은 안 켠다)
python manage.py relink_control_role_menus --bundle P-61-U1 --all-tenants
```

**행은 한 줄도 지우지 않았다.** 지우면 되돌릴 때 id 가 바뀌고, 그 id 를 적어 둔 자리가
조용히 끊긴다.

---

## 9. 턴 G 이어붙임 — **역할 넷을 실제 로그인으로 찍었다** (2026-09-06 · 차선 C)

턴 F 의 이 문서 §5 는 U5 를 **「링크 표만 — 시드 계정이 없다」**로 적었다. 그 자리를 메웠다.

| 역할 | 사이드바(역할 코드별 최대) | 제품 화면 | 잰 방법 | 화면 |
|---|---|---|---|---|
| U1 관제요원 | 5줄 | 5장 | 링크 표 + **실제 로그인** | `shots/sidebar_U1_gxseed_u1_operator.png` |
| U2 관제팀장 | 21줄 | 7장 | 링크 표 + **실제 로그인** | `shots/sidebar_U2_gxseed_u2_manager.png` |
| U4 재난안전과 | 26줄 | 2장 | 링크 표 + **실제 로그인** | `shots/sidebar_U4_gxseed_u4_official.png` |
| **U5 관리자** | **71줄** | **4장** | 링크 표 + **실제 로그인** ← 처음이다 | `shots/sidebar_U5_gxseed_u5_sysop.png` |

- U5 시드 사람 `gxseed_u5_sysop`(역할 `admin`)이 **실제 HTTP 경로**로 생겼다
  (`POST /api/v1/user/create-user` → 200). `is_superuser=False · is_staff=False`.
- 「두 눈 대조」가 **3 → 4 역할**로 늘었다. U5 의 70줄은 그전까지 아무도 로그인해서
  본 적 없는 재현이었다 — 이제 71줄(제품 4)로 **눈으로 재진다.**
- U5 제품 줄이 3 → 4 가 된 이유: P-61 의 「백업·보존」 자리에 화면이 생겨
  (`/dsm/system` 「보존·백업 설정」) `P61_NO_SCREEN_YET` 에서 표로 **옮겼다**(§6 갱신).
- 자세한 것과 촬영 명령: `../P-74/README.md`.
