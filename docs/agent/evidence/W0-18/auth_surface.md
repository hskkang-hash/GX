# W0-18 · P-W0-18-2 C 안 실행 — 인증 관문 없는 라우트 24건 전수 조사

**티켓** W0-14 · W0-18 · **판정** P-W0-18-2 `chosen_default: "C"` (선조사) · **일자** 2026-08-25
**환경** `gx-shell` 컨테이너 · dj-core 1.1.6 · **읽기 전용** (GET 만 · 운영 DB 무접촉)
**도구** `scripts/scan_auth_surface.py` · 원자료 `auth_surface.json`
**시험** `backend/tests/test_auth_surface.py` (5건 green)

> **한 줄**: 24건 중 **공개 라우트로 볼 만한 것은 0건**이다. C 안이 걱정한
> "조사 없이 auth 를 붙이면 외부 연동이 조용히 끊긴다"의 근거가 실측에서 나오지 않았다.
> **한 줄 더**: 조사하다 별건이 나왔다 — **해독 불가 Bearer 토큰은 전 라우트에서 500 이다**(§4).
> 서명키를 교체하면(D-251) 구 토큰을 든 모든 클라이언트가 401 이 아니라 500 을 받는다.

---

## 1. 무엇을 셌나

정적 grep 이 아니라 **런타임 ninja 레지스트리**를 훑었다 (동적 등록을 놓치지 않기 위해서 —
`classify_permission_routes` 와 같은 이유). 라우트마다 `auth_callbacks` 유무와
`view_func._path_override`(=`@path_permission`) 유무를 함께 기록했다.

```bash
docker cp scripts/scan_auth_surface.py gx-shell:/tmp/
docker exec gx-shell python /tmp/scan_auth_surface.py /docs/agent/evidence/W0-18/auth_surface.json
# → [AUTH] routes=652 no_auth=143 gap=24
```

| | 건수 |
|---|---|
| 전체 라우트 | 652 |
| `auth=` 콜백 없음 | 143 |
| 그중 `@path_permission` **있음** ← 이 조사의 대상 | **24** |
| 그중 `@path_permission` 없음 | 119 |

P-W0-18-2 가 적재한 수(652 / 143 / 24)와 **정확히 같다.** 그 실측은 옳았다.

---

## 2. 24건 전부 — 공개 라우트 후보 0건

앱별: `terminals` 9 · `devices` 6 · `flight_log` 4 · `delivery` 3 · `operational_data` 1 · `orders` 1.

| # | 라우트 | 권한 경로 | 성격 |
|---|---|---|---|
| 1 | `GET /api/terminals/terminals` | `/terminals` | 업무 데이터 목록 |
| 2 | `GET /api/terminals/terminals/{id}` | `/terminals` | 업무 데이터 상세 |
| 3 | `GET /api/terminals/terminals/{id}/operating-times` | 4종 | 업무 데이터 상세 |
| 4 | `GET /api/terminals/delivery-hubs` | `/delivery-hubs` | 업무 데이터 목록 |
| 5 | `GET /api/terminals/delivery-hubs/{id}` | `/delivery-hubs` | 업무 데이터 상세 |
| 6 | `GET /api/terminals/docking-stations` | `/docking-stations` | 업무 데이터 목록 |
| 7 | `GET /api/terminals/docking-stations/{id}` | `/docking-stations` | 업무 데이터 상세 |
| 8 | `GET /api/terminals/infrastructures` | `/infrastructure` | 업무 데이터 목록 |
| 9 | `GET /api/terminals/infrastructures/{id}` | `/infrastructure` | 업무 데이터 상세 |
| 10 | `GET /api/devices/devices-management` | `/device` | 장비 목록 |
| 11 | `GET /api/devices/devices-management/{id}` | `/device` | 장비 상세 |
| 12 | `GET /api/devices/libraries-management` | `/library` | 장비 라이브러리 |
| 13 | `GET /api/devices/libraries-management/{id}` | `/library` | 〃 상세 |
| 14 | `GET /api/devices/packaging-specifications` | `/packaging` | 포장 규격 |
| 15 | `GET /api/devices/packaging-specifications/{id}` | `/packaging` | 〃 상세 |
| 16 | `GET /api/flight-log/flight-log` | `/flight-log-analysis` | 비행 이력 |
| 17 | `GET /api/flight-log/flight-log/detail/{id}` | 〃 | 비행 이력 상세 |
| 18 | `GET /api/flight-log/flight-log/download-log/{id}` | 〃 | **로그 파일 다운로드** |
| 19 | `DELETE /api/flight-log/flight-log/delete/{ids}` | 〃 | **삭제(쓰기)** |
| 20 | `GET /api/operational-data/operational-data/{order_item_id}` | `/operational-data` | 운영 데이터 |
| 21 | `POST /api/delivery/processing/assign-packages-to-drone` | `/delivery-operation/processing` | **드론 배정(쓰기)** |
| 22 | `POST /api/delivery/processing/assign-packages-to-drones` | 〃 | **드론 배정(쓰기)** |
| 23 | `POST /api/delivery/verification/verify-orders` | `/delivery-operation/verification` | **주문 검증(쓰기)** |
| 24 | `POST /api/orders/order/{id}/payment` | 3종 | **결제(쓰기)** |

**공개 라우트 관용어(health·ping·webhook·callback·login·token·public·docs·csrf·version)에
걸리는 것은 0건이다.** 전부 로그인한 사용자의 업무 화면이 부르는 경로이고,
**5건은 쓰기**(삭제 1 · 배정 2 · 검증 1 · 결제 1)다.

> ⚠️ **이름이 공개가 아니라는 것이 "공개가 아니다"의 증명은 아니다.** 스크립트의
> `public_hints` 는 사람이 볼 목록을 좁히는 힌트일 뿐 판정이 아니다. 다만 24건 중
> 단 하나도 힌트에 걸리지 않았고 절반이 업무 쓰기 경로라는 점은, C 안이 상정한
> "의도된 공개 엔드포인트가 섞여 있다"는 그림과 다르다.

---

## 3. HTTP 재현 — 관문이 없다는 것이 무슨 뜻인가

`Authorization` 헤더를 **아예 보내지 않고** 같은 요청을 둘에 보낸다.

| 라우트 | `auth=` | 헤더 없음 → |
|---|---|---|
| `GET /api/report-template/` (대조군) | 있음 | **401** `{"detail":"Unauthorized"}` |
| `GET /api/devices/devices-management` | **없음** | **200** `{"success":false,…"Permission denied"}` |
| `GET /api/terminals/terminals` | **없음** | **200** 〃 |
| `GET /api/operational-data/operational-data/1` | **없음** | **200** 〃 |

**인증을 한 번도 묻지 않고 권한 판정까지 간다.** 지금은 익명이라 권한이 없어 막히지만,
막는 주체가 인증 관문이 아니라 권한 판정이다 — 관문이 라우트마다 있거나 없다.
`tests/test_auth_surface.py::test_no_auth_callback_route_reaches_permission_check` 가 고정한다.

(P-W0-18-2 가 적은 "`token/pair` 가 준 토큰으로 권한 판정까지 도달한다"도 같은 사실의 다른 얼굴이다.
그쪽은 `tests/test_api_contract.py` 가 이미 고정하고 있다.)

---

## 4. ★ 조사 중 나온 별건 — 해독 불가 토큰은 **전 라우트에서 500**

`auth=` 유무와 **무관하다.** 라우트가 아니라 미들웨어의 문제다.

| Authorization | `auth=` 없는 라우트 | `auth=` 있는 라우트 |
|---|---|---|
| 헤더 없음 | 200 (권한 판정) | 401 |
| `Bearer ` (빈값) | **500** | **500** |
| `Bearer not-a-token` | **500** | **500** |
| `Bearer aaa.bbb.ccc` | **500** | **500** |
| **다른 키로 서명** (형식 정상) | **500** | **500** |
| 실키 서명 · **만료** | 200 (권한 판정) | 401 |
| `Bearer` 접두어 없음 | 200 | 401 |

**만료는 정상 처리된다. 500 의 원인은 "만료"가 아니라 "해독 실패"다.**

원인 — dj-core `core/middleware/refresh_token.py:204` (`TokenRefreshMiddleware`):

```python
try:
    ...                      # 정상 경로
except Exception as e:
    payload = jwt.decode(    # ← 복구를 시도하며 다시 해독한다. 감싸지 않았다
        token, settings.NINJA_JWT['SIGNING_KEY'], ...
    )
```

첫 실패가 "해독 불가"면 복구도 같은 자리에서 터지고, 그 예외가 미들웨어 밖으로 나가
Django 가 500 을 만든다. **`jwt.exceptions.DecodeError: Not enough segments`** (실측 traceback).

**§0.4 금지구역(dj-core)이라 그 파일은 고칠 수 없다** (D-207). 저장소 쪽에서 감싸는 것은 가능하다.

### 왜 지금 중요한가 — 자격증명 회전과 정면으로 만난다

D-251(긴급 병행: 자격증명 회전)로 **서명키를 교체하면 구 토큰은 "다른 키로 서명" 상태가 된다.**
표의 그 줄이 **500** 이다. 프론트의 재인증 경로는 **401** 을 본다.
즉 키 교체 직후 로그인 세션 전체가 재인증으로 흐르지 못하고 500 으로 멈출 수 있다.

또 하나: 같은 `except` 블록은 복구에 성공하면 **그 사용자의 유효 토큰을 전부 블랙리스트에**
넣는다. 해독이 되는 토큰(=실키 서명)에서만 도달하는 경로라 익명 공격자가 남의 세션을
끊을 수는 없다. 다만 **자기 세션이 예기치 않게 전부 끊기는** 경로가 있다는 사실은 남긴다.

→ 적재: **P-W0-18-6** (별건 · 저장소 쪽 감싸기 여부와 회전 순서)

---

## 5. 프론트 영향 — 확인할 수 있는 데까지

24건 중 프론트가 부르는 것은 확인된다(`services/API.ts` · 배송 대시보드 · 장비 ·
FlightLogAnalysis · LibraryDrone — 경로 문자열 80회 출현). 전부 **로그인 후 화면**이다.

**토큰을 붙이는 곳은 `rj-core` 안이라 이 저장소에서 확인할 수 없다** (사설 패키지 ·
`package.json` 의 git+ssh 의존 · 이 PC 에 `node_modules` 없음). 저장소 소스에서
`Authorization` 을 직접 붙이는 곳은 카카오 지도 API 3곳뿐이다.

→ **"auth 를 붙이면 프론트가 깨지는가"는 여기서 답할 수 없다.** 다만 24건이 전부
로그인 후 화면이라면 rj-core 가 토큰을 붙이고 있을 개연성이 높다 —
`auth=` 가 붙은 나머지 628 라우트가 그 클라이언트로 정상 동작하고 있기 때문이다.
확정하려면 rj-core 사본 확보나 브라우저 네트워크 탭 1회 확인이 필요하다 (사람 작업).

---

## 6. 그래서 P-W0-18-2 는 어떻게 되나

C(선조사)를 실행했고 결과가 나왔다. **A 와 B 중 무엇으로 갈지 판정이 필요하다** → **P-W0-18-5**.

- 조사가 걷어낸 걱정: "의도된 공개 엔드포인트가 섞여 있다" — **후보 0건**
- 남는 걱정: "rj-core 가 토큰을 붙이는가" — 저장소에서 확인 불가 (§5)
- 새로 생긴 것: 키 교체 시 500 (§4) — **auth 를 붙이든 안 붙이든 별도로 처리해야 한다**

---

## 7. 이 조사가 바꾼 것 / 바꾸지 않은 것

| | |
|---|---|
| 코드 변경 | **0줄** (신규 시험 파일 1개 · 조사 스크립트 1개뿐) |
| 라우트 동작 | **무변경** — `auth=` 를 붙이지 않았다 |
| 데이터·스키마 | **무접촉** (GET 만 · 테스트 DB) |
| 새 회귀 게이트 | `tests/test_auth_surface.py` 5건 — 24건이 늘면 빨개진다 |
