# W0-4 증거 — 데모·목업 코드 프로덕션 분리

생성: 2026-08-14 · status: **verify-pending** (실제 `npm run build` 만 미실행 — 사유 아래)

DoD: *"프로덕션 빌드 산출물에 mockupDemoUi 청크 없음. 해당 URL 직접 접근 시 404."*

---

## 1. REVIEW 결과 (STEP 2)

### 2-1 reuse_targets 실독

| 파일 | 규모 | 확인한 것 |
|---|---|---|
| `frontend/src/features/mockupDemoUi/` | 34파일 / 5디렉터리 | `Dashboard/index.tsx` 가 `getRandomInt()`·`generateRandomData()` 로 **난수 목업 데이터**를 그린다. MUI 사용(신규 화면 아님) |
| `frontend/src/features/setupData/` | 7파일 | 데모는 `DemoPage`(menu_id 로 HTML 조회)·`DemoUrlPage`(iframe) **2개뿐**. 나머지 5개는 데모가 아니다 |
| `frontend/src/services/API.ts` | 988줄 | `/* Mockup UI */` 주석 블록에 목업 라우트 경로가 모여 있다. `setupDemo`·`setupDemoUrl`·`djiUrl` 정의 확인 |
| `drone-monitoring.html` | 34KB | CDN chart.js + 하드코딩 값의 단독 데모 페이지. 빌드·서빙 경로 어디에도 연결 없음 |
| `frontend/App.tsx` · `vite.config.ts` · `Dockerfile` · `nginx.conf` | — | 라우트 등록 지점 · 빌드 설정 · 배포 경로 확인 |

### 2-2 티켓 가정 ↔ 실제 코드

| 티켓의 가정 | 실제 | 판정 |
|---|---|---|
| mockupDemoUi 44파일 | **34파일** | 수치만 차이. 영향 없음 |
| setupData = `/setup-demo-file`, `/setup-demo-url` 라우트 | 맞다. 단 같은 디렉터리에 **데모가 아닌 화면 5개**가 함께 있다 | 부분 일치 → 데모 2개만 격리 |
| `djiUrl` 임시 라우트 여부 확인 | **임시 아님.** `DJIPage` 는 메뉴별로 설정된 외부 URL(`endpoint.getMenuUrl`)을 새 창으로 여는 실기능 | 격리 대상 제외 |
| `drone-monitoring.html` 데모 파일 | 맞다. 백엔드의 `/api/delivery/drone-monitoring/*` 와는 **이름만 같고 참조 관계 없음** | `docs/demo/` 로 이동 |

**티켓이 적지 않은 사실 1건** — `mockupDemoUi` 는 데모 전용 URL 만 쓰는 게 아니라
**대시보드 라우트 3개를 실제로 점유**하고 있었다.

```
/intergrated-dashboard  → mockupDemoUi/Dashboard
/monitoring-dashboard   → mockupDemoUi/MonitoringDashboard
/disabillity-dashboard  → mockupDemoUi/DisabillityDashborad
```

즉 **W3-1 이 "정리 대상"으로 지목한 6개 대시보드 라우트 중 3개가 목업이었다.**
`/delivery-dashboard`·`/delivery-dashboard-anyang`·`/surveillance-dashboard` 는
`features/Dashboard/` 의 실구현이므로 건드리지 않았다.

### 2-3 금지구역 저촉

없음. 변경 파일 중 `delivery`/`orders`/`terminals`·`rj-core`/`dj-core`·지도 3종·`FormRoute.tsx`
해당 없음. MUI 를 쓰는 목업 화면은 **개종하지 않고 격리만** 했다(§0.4 UI 통일 금지 준수).

### 2-4 DoD 재현 정보

`404` 판정 기준이 코드 현실과 어긋난다 → **§4 로 분리해 기재.**

### 2-5 위험

| # | 위험 | 대응 |
|---|---|---|
| 1 | 운영 DB 의 메뉴(`menu_menu`)가 `/intergrated-dashboard` 등을 가리키면, 프로덕션에서 그 메뉴는 홈으로 리다이렉트된다 | 의도된 결과(미완성 기능 비노출). **W3-2 프리셋 3종이 그 자리를 대체**한다. 메뉴 시드 정리는 W3-1 범위 |
| 2 | 영업 시연이 목업 화면에 의존 중이면 데모 빌드가 필요해진다 | `VITE_ENABLE_DEMO=true npm run build` 로 그대로 살아난다. 삭제가 아니라 플래그다 |
| 3 | `mockupDemoUi/DeliveryDashboard`·`SurveillanceDashboard` 는 라우트가 없는 사문 코드 | 이번 변경 전에도 번들에 없었다(참조 0). 제거는 별건 |

---

## 2. 구현 (STEP 4)

| 파일 | 구분 | 내용 |
|---|---|---|
| `frontend/vite.config.ts` | 수정 | `define: { __DEMO_ENABLED__: JSON.stringify(process.env.VITE_ENABLE_DEMO === 'true') }` |
| `frontend/src/types/vite-env.d.ts` | 수정 | `declare const __DEMO_ENABLED__: boolean` |
| `frontend/src/App.tsx` | 수정 | 정적 import 3개 제거 → `demoRoutes` 배열(플래그 분기 안의 dynamic import 5개)로 통합, 라우트 5건을 `...demoRoutes` 하나로 대체 |
| `frontend/.env.example` | 수정 | `VITE_ENABLE_DEMO=false` + 경고 주석 |
| `drone-monitoring.html` → `docs/demo/` | 이동 | `git mv`. `docs/demo/README.md` 에 사유 기재 |
| `scripts/check_demo_isolation.py` | 신규 | 정적 격리 검사 4종 |
| `.pre-commit-config.yaml` | 수정 | `gx-demo-isolation` 훅 추가 |
| `.github/workflows/demo-isolation.yml` | 신규 | `static-gate`(항상) + `build-guard`(사내망 러너에서만) |

**핵심은 플래그를 런타임 조건이 아니라 컴파일 상수로 만든 것이다.**
`import.meta.env.X` 런타임 조회였다면 라우트는 막히지만 청크는 남는다 —
DoD 는 "라우트가 안 뜬다"가 아니라 **"청크가 없다"** 를 요구한다.

---

## 3. 검증 (STEP 5)

### 3-1. 정적 격리 검사 — PASS

```
$ python scripts/check_demo_isolation.py
PASS: 데모·목업 모듈이 프로덕션 빌드 경로에서 격리되어 있다 (W0-4)     exit=0
```

**음성 대조(검사가 실제로 잡는지):** 변경 전 트리(`git stash`)에서 같은 스크립트 실행

```
FAIL: 데모·목업 격리 위반 (W0-4)                                        exit=1
  - frontend/src/App.tsx : 데모 모듈을 정적 import 한다 → './features/mockupDemoUi/Dashboard'
  - frontend/src/App.tsx : 데모 모듈을 정적 import 한다 → './features/mockupDemoUi/DisabillityDashborad'
  - frontend/src/App.tsx : 데모 모듈을 정적 import 한다 → './features/mockupDemoUi/MonitoringDashboard'
  - frontend/src/App.tsx : 데모 경로가 플래그 분기 밖에서 참조된다 → /intergrated-dashboard, /monitoring-dashboard, /disabillity-dashboard
  - frontend/vite.config.ts : __DEMO_ENABLED__ define 이 없다
  - drone-monitoring.html : 데모 HTML 이 배포 경로에 있다 → docs/demo/ 로 옮긴다
  - __DEMO_ENABLED__ 를 사용하는 소스가 하나도 없다 — 게이트가 미적용 상태다
```

### 3-2. 청크 제거 메커니즘 실증 — PASS (동일 Vite 메이저)

이 저장소의 빌드는 사내 private 패키지 때문에 돌지 않는다(§3-3).
그래서 **같은 Vite 5.4 로 같은 코드 형태**(define + 삼항 분기 안의 dynamic import)를
최소 재현 프로젝트로 만들어 청크 생성 여부를 직접 측정했다.

```
vite/5.4.21  (프로젝트 선언: ^5.4.17)

[A] VITE_ENABLE_DEMO 미설정 (프로덕션 기본값)
    dist/assets/  →  index-BSYjKaqt.js                       (1개)
    'mockupDemoUi' 문자열 포함 파일: 0

[B] VITE_ENABLE_DEMO=true
    dist/assets/  →  index-CabPkzFl.js
                     mockupDemoUi-BPhPmQhk.js                (2개 — 별도 청크 생성)
    'mockupDemoUi' 문자열 포함 파일: 2
```

→ 플래그가 꺼지면 **dynamic import 자체가 dead code 로 접혀 청크가 생성되지 않는다**는 것이
동일 번들러에서 확인되었다. 산출물 경로: `scratchpad/dce-probe/`(임시, 저장소 밖).

### 3-3. 실제 `npm run build` — env-unavailable (D-007 동류)

```
$ npm install --dry-run          (frontend/)
  → 150초 타임아웃 (exit 124)

원인: package.json 의 private 의존 2건이 사내 git 서버를 가리킨다
  rj-core       git+ssh://git@192.168.0.22/HuyPhat/rj-core.git#rj-core-v2
  @gaion/gcs-fe git+ssh://git@192.168.0.22/HuyNgK/gcs-fe.git#develop

$ Test-NetConnection 192.168.0.22 -Port 22   →  TcpTestSucceeded=False
  (public npm registry 는 정상: npm view vite version → 8.2.1)
```

**환경 문제이지 코드 실패가 아니다(D-007).** 사내망에서 아래 한 줄이면 판정이 끝난다.

```bash
cd frontend && npm install && npm run build && ! grep -rlE 'mockupDemoUi|setup-demo-(file|url)' dist/assets
```

같은 명령이 `.github/workflows/demo-isolation.yml` 의 `build-guard` 잡에 들어 있다
(사내 러너 준비 시 `vars.GX_PRIVATE_REGISTRY_AVAILABLE=true` 로 활성).

### 3-4. pre-commit 훅 — 설정 완료, 실행은 env-unavailable

`pre-commit` 명령이 이 환경에 설치되어 있지 않다(`command not found`).
훅이 호출하는 스크립트 자체는 §3-1 에서 양성·음성 모두 확인했다.

---

## 4. ★ DoD 후반부에 대한 판정 요청 (Cowork/사람)

> DoD: "…해당 URL **직접 접근 시 404**."

현재 앱은 미등록 경로를 404 로 응답하지 않는다. **의도된 기존 정책**이다.

```
nginx  try_files $uri $uri/ /index.html     → SPA 라 항상 200 + index.html
App.tsx  { path: '*', element: <Navigate to={home} replace /> }   → 홈으로 이동
```

즉 이번 변경으로 데모 경로는 **"라우트 미등록 → 홈 리다이렉트"** 가 된다.
화면·번들 어디에도 데모는 없지만, HTTP 상태코드는 200 이다.

### D-203 초안 (제안)

| 안 | 내용 | 영향 |
|---|---|---|
| **A안 (권고)** | **라우트 미등록 + 홈 리다이렉트를 DoD 충족으로 인정**하고 DoD 문구를 "데모 경로가 라우트 테이블·번들에 없고 접근 시 홈으로 반환된다"로 정정 | 코드 변경 0. SPA 표준 동작 |
| B안 | `frontend/nginx.conf` 에 데모 경로 `return 404` 추가 | 문구 그대로 충족. 단 데모 빌드(`VITE_ENABLE_DEMO=true`)를 같은 nginx 이미지로 서빙하면 데모가 404 로 막힌다 → 이미지 이원화 필요 |
| C안 | SPA catch-all 을 홈 리다이렉트 대신 404 페이지로 교체 | **전 앱 미등록 경로의 동작이 바뀐다.** R1 범위 밖, 회귀 위험 |

**권고: A안.** GS 심사가 보는 것은 "미완성 기능이 UI 에 노출되는가"이고,
그 판정은 라우트·번들에서 사라졌는지로 이미 끝난다. 상태코드는 심사 항목이 아니다.

---

## 5. 남은 부채

- `mockupDemoUi/DeliveryDashboard`·`SurveillanceDashboard` (라우트 없는 사문 코드 2디렉터리) — 삭제는 별건
- 운영 DB 메뉴가 목업 대시보드 3개를 가리키는 경우의 시드 정리 → **W3-1**
- `frontend/nginx.conf` 와 `Dockerfile`(`npm run preview`)의 배포 경로 이원화 — R1 범위 밖
