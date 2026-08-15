# WP-5 사전 메모 — 대시보드 라우트 6개 중 3개는 목업이었다

**출처** W0-4(데모·목업 분리) 구현 중 실측 · 2026-08-14 · 근거 커밋 `9998b93`
**용도** WP-5(3계층 대시보드·성과보고) ENTRY 의 **전제 검증 출발점**. 지금은 고치지 않는다 (D-219).

---

## 1. 무엇을 발견했나

W3-1 은 "대시보드가 6개 라우트로 분화되어 있으니 `/dashboard/:presetCode` 1개로 통합한다"를 전제한다.
그런데 **그 6개는 같은 급이 아니다. 3개는 실구현이고 3개는 정적 목업이다.**

| 라우트 | 컴포넌트 | 실체 | 규모 | API 호출 | W0-4 이후 상태 |
|---|---|---|---|---|---|
| `/surveillance-dashboard` | `features/Dashboard/SurveillanceDashboard` | **실구현** | 29파일 5,859줄 | 있음 (`useSurveillanceDashboard.ts` 등) | 그대로 |
| `/delivery-dashboard` | `features/Dashboard/DeliveryDashboard/indexV2` | **실구현** | 50파일 10,096줄 | 있음 | 그대로 |
| `/delivery-dashboard-anyang` | `DeliveryDashboardAnYang` | **실구현** (고객사명 하드코딩) | 위 50파일에 포함 | 있음 | 그대로 |
| `/intergrated-dashboard` | `mockupDemoUi/Dashboard` | **목업** | 7파일 876줄 | **0건** | 데모 플래그 뒤로 이동 |
| `/monitoring-dashboard` | `mockupDemoUi/MonitoringDashboard` | **목업** | 7파일 1,040줄 | **0건** | 데모 플래그 뒤로 이동 |
| `/disabillity-dashboard` | `mockupDemoUi/DisabillityDashborad` | **목업** | 8파일 1,619줄 | **0건** | 데모 플래그 뒤로 이동 |

**목업 3종은 `mockupDemoUi` 디렉터리 전체에서 `API.`/`endpoint.`/`useQuery` 호출이 0건이다.**
`Dashboard/index.tsx` 는 `getRandomInt()` · `generateRandomData()` 로 화면을 채우고,
도시 좌표(천안·공주·보령…)가 소스에 하드코딩되어 있다. 즉 **데이터 연결이 아니라 그림이다.**

또한 `services/API.ts` 의 해당 경로 선언 블록에는 원저자가 붙인 주석이 그대로 남아 있다 — `/* Mockup UI */`.

라우트가 없는 목업 2개도 있다(참조 0, 번들 미포함): `mockupDemoUi/SurveillanceDashboard`(1파일 602줄),
`mockupDemoUi/DeliveryDashboard`(11파일 1,029줄).

---

## 2. W3-1 의 전제에 무엇을 의미하나

| W3-1 이 가정한 것 | 실제 | WP-5 에서 다시 판단할 것 |
|---|---|---|
| 6개 라우트를 1개로 **통합**한다 | 통합 대상 실구현은 **3개**뿐 | 목업 3개는 통합이 아니라 **폐기**다. "6→1"이 아니라 **"3 통합 + 3 폐기 + 프리셋 3 신설"** |
| 기존 URL 은 **301 리다이렉트**로 유지 | 목업 3개는 W0-4 로 이미 프로덕션에서 사라짐 | 목업 3개 URL 은 리다이렉트 대상인가, 아니면 폐기 그대로 둘 것인가. **운영 DB 메뉴(`menu_menu`)가 이 경로를 가리키는지 확인이 선행** |
| 프리셋 3종(W3-2)은 신규 데이터 정의 | 목업 3종이 사실상 프리셋의 **시안**이다 | 목업의 패널 구성(위젯 배치·지표 선택)은 EXECUTIVE 뷰 설계 입력으로 재사용 가치가 있다. **코드가 아니라 화면 구성만** |

**가장 실질적인 함의**: W3-2 의 `EXECUTIVE` 프리셋("숫자 4~6개 + 지도 1장, 스크롤 없이 1화면")은
`mockupDemoUi/MonitoringDashboard`(한국지도 + 상태 카드)와 목적이 겹친다.
**새로 그리기 전에 그 목업을 열어 보고, 무엇을 남기고 무엇을 버릴지 판정하는 것이 WP-5 ENTRY 의 1번 항목이다.**

---

## 3. WP-5 ENTRY 착수 시 먼저 확인할 것 (체크리스트)

- [ ] 운영 DB `menu_menu` 에 `/intergrated-dashboard` · `/monitoring-dashboard` · `/disabillity-dashboard`
      경로를 가진 행이 있는가 (있으면 그 메뉴는 현재 프로덕션에서 홈으로 폴백된다 — D-218 허용 동작)
- [ ] `/delivery-dashboard-anyang` 의 고객사 하드코딩을 프리셋 파라미터로 흡수할 수 있는가
      (§0.4 는 `delivery` **앱**을 금지구역으로 두지만, 이 라우트는 `features/Dashboard` 쪽이다 — 경계 확인 필요)
- [ ] `backend/dashboard/` 의 패널·그룹·가중치 모델이 프리셋 3종을 데이터로 표현할 수 있는가
      (W3-2 는 "신규 엔진 금지, 프리셋만 정의"가 전제다)
- [ ] 목업 3종을 **삭제**할지 데모 플래그 뒤에 남길지 — 남기면 영업 시연 자산, 삭제하면 코드 3,535줄 감소

---

## 4. 지금 하지 않는 이유

D-219: 검증되지 않은 코드가 4건 떠 있는 상태에서 파급 큰 라우트 통합을 쌓으면
사내망 검증에서 무엇이 깨졌는지 원인 분리가 안 된다. **WP-0 → WP-1 → … 순서를 지킨다.**
이 파일은 그때까지 사실만 보존하는 용도다.
