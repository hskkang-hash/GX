# 라우트 인벤토리 — 전수 685건 [실측 2026-09-05T09:26:14+07:00]

> D-343 ①②. `docker exec gx-shell python /repo/scripts/probe_route_inventory.py` 가 낸다.
> 런타임 ninja 레지스트리 전수 — 정적 grep 이 아니다.

> **이 표는 세 번 쓴다** (D-343 ▣): F-05 연동 규격서 부록 · 상용 API 문서 초안 ·
> 파트너 기술 검토 자료.

## 1. 들어오는 키 (inbound key) — 지금 어디까지 닿나

| 상태 | 건수 | 뜻 |
|---|---:|---|
| `accepts` | 547 | **지금 키가 닿는다.** dj-core `CustomJWTAuth` 가 받는다 — 좁혀지지 않은 자리 |
| `open_anonymous` | 72 | **인증 콜백이 없다.** 키를 검사하지도 않는다 — 「거절」이 아니다 |
| `refuses` | 56 | 우리 문지기 `JwtOrInboundKey` 가 기본값 거절로 막는다 |
| `unknown` | 9 | 우리가 모르는 인증 클래스. 모른다고 적는다 (D-301) |
| `declared` | 1 | 우리가 `inbound_key=True` 로 **선언해서** 연 자리 (사유 기재) |

## 2. 3갈래 분류 — 기본값은 좁은 쪽 (D-343 ②)

| 갈래 | 건수 |
|---|---:|
| `inbound_key_allowed` | 1 |
| `session_only` | 684 |
| `internal_only` | 0 |

대장: `route_classes.yaml` · 래칫 기준선: `route_baseline.txt`

## 3. 테넌트 범위 검사

| 상태 | 건수 |
|---|---:|
| `none` | 651 |
| `required` | 33 |
| `exempt` | 1 |

## 4. 앱별 (상위 20)

| 앱 | 라우트 | 키가 닿음 | 관문 없음 | 테넌트 범위 |
|---|---:|---:|---:|---:|
| `devices` | 66 | 54 | 0 | 0 |
| `delivery` | 60 | 51 | 9 | 0 |
| `surveillance` | 60 | 58 | 0 | 0 |
| `terminals` | 55 | 46 | 9 | 0 |
| `v1` | 45 | 24 | 21 | 0 |
| `dsm` | 33 | 0 | 0 | 32 |
| `orders` | 31 | 26 | 5 | 0 |
| `advanced-table` | 29 | 28 | 1 | 0 |
| `stream-monitors` | 28 | 19 | 0 | 1 |
| `handover` | 25 | 25 | 0 | 0 |
| `third-api` | 24 | 23 | 1 | 0 |
| `operation-settings` | 20 | 20 | 0 | 0 |
| `operational-data` | 17 | 17 | 0 | 0 |
| `partner` | 16 | 16 | 0 | 0 |
| `menu` | 15 | 15 | 0 | 0 |
| `apikey` | 12 | 0 | 12 | 0 |
| `user-groups` | 12 | 12 | 0 | 0 |
| `optimization` | 10 | 10 | 0 | 0 |
| `print-format` | 9 | 1 | 0 | 0 |
| `roles` | 9 | 9 | 0 | 0 |

## 5. 지금 키를 받겠다고 **선언한** 자리

| 메서드 | 경로 | 사유 |
|---|---|---|
| GET | `/api/dsm/events` | F-05 「외부 App 이 이벤트 OpenAPI 하나로만 들어온다」 — 읽기 전용 조회 |

## 6. 인증 콜백이 없는 자리 (관문 없음)

전수 72건. 그중 `@path_permission` 이 **활성**인 것 13건 —
그 자리는 `probe_authn_gap_calls.py` 가 **호출로** 재고 결과를 `authn_gap_calls.json` 에 남긴다 (D-210 · D-342).

| 메서드 | 경로 | authz |
|---|---|---|
| PUT | `/api/advanced-table/column-order` | 없음 |
| GET | `/api/apikey/analytics` | 없음 |
| POST | `/api/apikey/bulk-deactivate` | 없음 |
| GET | `/api/apikey/check` | 없음 |
| GET | `/api/apikey/keys` | 없음 |
| POST | `/api/apikey/keys` | 없음 |
| DELETE | `/api/apikey/keys/{api_key_id}` | 없음 |
| GET | `/api/apikey/keys/{api_key_id}` | 없음 |
| PATCH | `/api/apikey/keys/{api_key_id}` | 없음 |
| POST | `/api/apikey/keys/{api_key_id}/regenerate` | 없음 |
| GET | `/api/apikey/keys/{api_key_id}/usage-logs` | 없음 |
| POST | `/api/apikey/keys/{user_id}` | 없음 |
| GET | `/api/apikey/stats` | 없음 |
| GET | `/api/comment` | 없음 |
| GET | `/api/config-management/list-optimized` | 없음 |
| GET | `/api/delivery/drone-monitoring/drone-status` | 없음 |
| POST | `/api/delivery/drone-monitoring/drone-status` | 없음 |
| POST | `/api/delivery/etri-integration/receive-from-etri` | 없음 |
| POST | `/api/delivery/etri-mock/receive-delivery` | 없음 |
| GET | `/api/delivery/etri-mock/test-scenarios` | 없음 |
| POST | `/api/delivery/processing/assign-packages-to-drone` | 활성 |
| POST | `/api/delivery/processing/assign-packages-to-drones` | 활성 |
| GET | `/api/delivery/processing/get-drones-by-package-and-route-optimized` | 없음 |
| POST | `/api/delivery/verification/verify-orders` | 활성 |
| GET | `/api/orders/banks` | 없음 |
| GET | `/api/orders/delivery-option` | 없음 |
| GET | `/api/orders/item-types` | 없음 |
| POST | `/api/orders/order/{id}/payment` | 활성 |
| GET | `/api/orders/payment-methods` | 없음 |
| GET | `/api/rating` | 없음 |
| GET | `/api/rating/featured` | 없음 |
| GET | `/api/register-settings` | 없음 |
| GET | `/api/source/get-html` | 없음 |
| GET | `/api/source/get-url` | 없음 |
| POST | `/api/source/save-html` | 없음 |
| GET | `/api/terminals/delivery-hubs` | 활성 |
| GET | `/api/terminals/delivery-hubs/{id}` | 활성 |
| GET | `/api/terminals/docking-stations` | 활성 |
| GET | `/api/terminals/docking-stations/{id}` | 활성 |
| GET | `/api/terminals/infrastructures` | 활성 |
| GET | `/api/terminals/infrastructures/{id}` | 활성 |
| GET | `/api/terminals/terminals` | 활성 |
| GET | `/api/terminals/terminals/{id}` | 활성 |
| GET | `/api/terminals/terminals/{id}/operating-times` | 활성 |
| POST | `/api/third-api/api-key-management/keys/{user_id}` | 없음 |
| POST | `/api/token/pair` | 없음 |
| POST | `/api/token/refresh` | 없음 |
| POST | `/api/token/verify` | 없음 |
| GET | `/api/topic` | 없음 |
| GET | `/api/topic/slug/{topic_slug}` | 없음 |
| GET | `/api/topic/{topic_id}` | 없음 |
| GET | `/api/v1/auth/csrf-token` | 없음 |
| GET | `/api/v1/auth/data-for-profile` | 없음 |
| POST | `/api/v1/auth/delete-session` | 없음 |
| GET | `/api/v1/auth/departments` | 없음 |
| POST | `/api/v1/auth/forgot-password` | 없음 |
| GET | `/api/v1/auth/groups` | 없음 |
| GET | `/api/v1/auth/languages` | 없음 |
| POST | `/api/v1/auth/login` | 없음 |
| POST | `/api/v1/auth/logout` | 없음 |
| GET | `/api/v1/auth/otp/generate-qr` | 없음 |
| POST | `/api/v1/auth/otp/reset` | 없음 |
| POST | `/api/v1/auth/otp/verify` | 없음 |
| GET | `/api/v1/auth/positions` | 없음 |
| POST | `/api/v1/auth/refresh-token` | 없음 |
| POST | `/api/v1/auth/register` | 없음 |
| POST | `/api/v1/auth/reset-password` | 없음 |
| POST | `/api/v1/auth/reset-password-for-user` | 없음 |
| GET | `/api/v1/auth/teams` | 없음 |
| GET | `/api/v1/auth/timezones` | 없음 |
| GET | `/api/v1/health` | 없음 |
| POST | `/api/v1/user/create-user` | 없음 |
