# 6 역할 x 전 라우트 — 화면 · API 두 칸 (P-293 · P-471)

생성: `python scripts/verify_role_routes.py --matrix` · 표 출처 `frontend/src/features/nav/roleScreens.json` (메뉴와 가드가 같은 출처) · 라우트 130자리(App.tsx 사이드바 밑 + /start).

읽는 법
- 화면 칸: `열림` = 그 역할이 표의 주인(가드 통과) · `안내` = 「이 화면은 ○○ 역할 화면입니다」로 통째 막힘.
- API 칸: 8500 에서 그 역할 계정 토큰으로 GET 한 실측 상태. `200→403` = 실측은 200 이었고 이번 턴 서버 규칙(`role_gate.py` 규칙 ③)이 배포되면 403 이 된다(**미배포 · 시험으로만 확인**). `-` = 이 화면은 읽는 API 가 없다 · `미측` = 이번에 못 쟀다.
- U3(현장 대원)·U6(외부 연계)는 사람 메뉴 버킷이 없다: U6 은 U5 계정으로, U3 은 뷰어 계정으로 열려서 가드는 U1·U2·U4·U5 에만 걸린다. 두 열의 화면 칸은 표의 선언이고 **API 는 계정이 없어 못 쟀다**(미측).
- 측정 시각 2026-10-01T01:32:30+0000 · 대상 http://gx-nginx-e:8500 · 서버는 **옛 코드**(이번 턴 수정 미배포).

| 화면 주소 | 표 줄 | U1 관제요원 화면 | U1 API | U2 관제팀장 화면 | U2 API | U3 현장 대원 화면 | U3 API | U4 재난안전과 화면 | U4 API | U5 기관 관리자 화면 | U5 API | U6 외부 연계 화면 | U6 API |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `/qr-code` | /qr-code | 열림 | - | 열림 | - | 안내 | - | 안내 | - | 열림 | - | 안내 | - |
| `/dsm/dashboard` | /dsm/dashboard | 열림 | 200 | 열림 | 200 | 안내 | 미측 | 안내 | 200 | 안내 | 200 | 안내 | 미측 |
| `/dsm/events` | /dsm/events | 열림 | 200 | 열림 | 200 | 열림 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/home` | /dsm/home | 안내 | 200 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/queue` | /dsm/queue | 열림 | 200 | 열림 | 200 | 안내 | 미측 | 안내 | 200 | 안내 | 200 | 안내 | 미측 |
| `/dsm/drill` | /dsm/drill | 안내 | 200 | 열림 | 200 | 안내 | 미측 | 안내 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/cameras/import` | /dsm/cameras/import | 안내 | 200→403 | 안내 | 200 | 안내 | 미측 | 안내 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/cameras/tuning` | /dsm/cameras/tuning | 안내 | 200 | 열림 | 200 | 안내 | 미측 | 안내 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/stats/false-positive` | /dsm/stats/false-positive | 안내 | 200 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/stats` | /dsm/stats | 안내 | 200 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/audit` | /dsm/audit | 안내 | 403 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/reports` | /dsm/reports | 안내 | 403 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/cameras/address` | /dsm/cameras/address | 안내 | 200→403 | 안내 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/cameras/grid` | /dsm/cameras/grid | 열림 | 200 | 열림 | 200 | 안내 | 미측 | 안내 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/privacy-requests` | /dsm/privacy-requests | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/metering` | /dsm/metering | 안내 | 200→403 | 안내 | 200 | 안내 | 미측 | 안내 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/system` | /dsm/system | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 열림 | 200 | 안내 | 미측 |
| `/dsm/settings/rules` | /dsm/settings/rules | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 열림 | 200 | 안내 | 미측 |
| `/dsm/team-status` | /dsm/team-status | 안내 | 200→403 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/dsm/people` | /dsm/people | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 열림 | - | 안내 | - |
| `/dsm/notify` | /dsm/notify | 안내 | 403 | 열림 | 200 | 안내 | 미측 | 안내 | 403 | 열림 | 200 | 안내 | 미측 |
| `/dsm/me` | /dsm/me | 열림 | 200 | 열림 | 200 | 열림 | 미측 | 열림 | 200 | 열림 | 200 | 열림 | 미측 |
| `/dsm/integrations` | /dsm/integrations | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 열림 | 200 | 열림 | 미측 |
| `/dsm/events/:id` | /dsm/events/:id | 열림 | 200 | 열림 | 200 | 열림 | 미측 | 열림 | 200 | 열림 | 200 | 안내 | 미측 |
| `/fws/home` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/field` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/drone` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/office` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/office/report` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/admin` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/fws/command` | /fws | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/ops` | /ops | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/m/inbox` | /m/inbox | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 안내 | - |
| `/m/events/:id` | /m/events/:id | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 안내 | - |
| `/m/settings` | /m/settings | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 안내 | - |
| `/users` | /users | 안내 | 200→403 | 안내 | 200→403 | 안내 | 미측 | 안내 | 200→403 | 열림 | 200 | 안내 | 미측 |
| `/users/add` | /users/add | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 열림 | - | 안내 | - |
| `/` | / | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - |
| `/menu` | /menu | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/menu/add` | /menu | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/profile` | /profile | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - | 열림 | - |
| `/roles` | /roles | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 열림 | 200 | 안내 | 미측 |
| `/configuration-management` | /configuration-management | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/configuration-management/edit/:configId` | /configuration-management | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/device` | /device | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/device/add-new-device` | /device | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/device/detail-device/:id` | /device | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/device/edit-device/:id` | /device | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/packaging` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/packaging/add-new-packaging` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/packaging/detail-packaging/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/etri-order/add-new-etri-order` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-inquiry` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/unverified-orders/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/verified-orders/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/arrived-orders/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/completed-orders/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-operation/cancelled-orders/order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-report` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-report/completed-order-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-profile` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-profile/add-new-survey-profile` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-profile/survey-profile-detail/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-inquiry/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-inquiry/add-new-order` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/operation-settings` | /operation-settings | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/terminals` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/terminals/add-new-terminals` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/terminals/edit-terminals/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/routes` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/routes/add-new-route` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/routes/detail-route/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/routes/edit-route/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/other-equipments` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/other-equipments/add-new-equipment` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/other-equipments/edit-equipment/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/partner` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/aim` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/notam` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-dashboard` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-dashboard-anyang` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/surveillance-dashboard` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/waybill-template` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/waybill-template/add-new-waybill-template` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/waybill-template/edit-waybill-template/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/library` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/library/add-new-library` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/library/edit-library/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/etri-tracking` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/etri-tracking/:id/:operation_id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/etri-order` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-hubs` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-hubs/register-delivery-hub` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-hubs/edit-delivery-hub/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/delivery-hubs/detail-delivery-hub/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/infrastructure` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/infrastructure/register` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/infrastructure/detail-infrastructure/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/docking-stations` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/docking-stations/register` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/docking-stations/detail-docking-station/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/report-template` | /report-template | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/report-template/add-new-report-template` | /report-template | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/report-template/edit-report-template/:id` | /report-template | 안내 | 403 | 안내 | 403 | 안내 | 미측 | 안내 | 403 | 안내 | 200 | 안내 | 미측 |
| `/operational-notice` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/multi-stream-monitor` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/checklist-setting` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/order-status` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/mapping-status` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/operational-data` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/operational-data/detail-operational-data/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/flight-log-analysis` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-mission` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-mission/add-new-survey-mission` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-mission/detail-survey-mission/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-mission/edit-survey-mission/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/data-analysis` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/data-analysis/detail-data-analysis/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/handover` | /handover | 열림 | - | 열림 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/handover/create-shift-log-handover/:id` | /handover | 열림 | - | 열림 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/handover/handover-duty-detail` | /handover | 열림 | - | 열림 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/handover/add-notice-management` | /handover | 열림 | - | 열림 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/media-data` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/media-data/video-analysis/:id` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/dji-url` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/gcs-mavlink` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/survey-profile/surveillance-gcs` | (없음 -> 플랫폼 운영자) | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - | 안내 | - |
| `/start` | /start | 열림 | 200 | 열림 | 200 | 안내 | 미측 | 열림 | 200 | 열림 | 200 | 열림 | 미측 |

## 출생 표본 — 관제요원(U1) 메뉴 밖 열 라우트

| 화면 | U1 화면 | U1 API (실측) | 서버 규칙 후 |
|---|---|---|---|
| `/dsm/reports` | 안내(관제팀장 · 재난안전과 · 기관 관리자) | 403 | 403 |
| `/dsm/system` | 안내(기관 관리자) | 403 | 403 |
| `/dsm/notify` | 안내(관제팀장 · 기관 관리자) | 403 | 403 |
| `/roles` | 안내(기관 관리자) | 403 | 403 |
| `/dsm/people` | 안내(기관 관리자) | - | - |
| `/users` | 안내(기관 관리자) | 200 | 403 |
| `/device` | 안내(플랫폼 운영자) | 403 | 403 |
| `/report-template` | 안내(플랫폼 운영자) | 403 | 403 |
| `/dsm/cameras/import` | 안내(기관 관리자) | 200 | 403 |
| `/dsm/team-status` | 안내(관제팀장 · 재난안전과 · 기관 관리자) | 200 | 403 |

