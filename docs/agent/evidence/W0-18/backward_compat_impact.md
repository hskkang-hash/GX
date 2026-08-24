# W0-18 ① 하위호환 영향조사 — 200-body-403 승격의 파급

**티켓** W0-18 · **결정** D-248(첫 작업은 영향조사) · D-212(플래그 뒤에) · **작성** 2026-08-24
**실측 환경** `docker gx-shell` (`/app` ← `backend/` 바인드마운트) · 테스트DB `--keepdb`
**측정 하네스** `tests/test_api_contract.py` (이 조사가 그대로 계약 시험이 된다) · `scripts/scan_frontend_success_contract.py`

> D-248 이 요구한 순서를 지켰다. **먼저 쟀고, 그 다음에 고친다.**

---

## 0. 한 줄 결론

**"200-body-403" 은 하나가 아니라 셋이었다.** 그리고 셋 중 가장 나쁜 것은
D-248 도 티켓도 예상하지 못한 **거부 사실이 아예 사라지는** 경우다.

| | 라우트 성격 | 권한거부 시 실제 응답 | 건수 | 응답계층에서 |
|---|---|---|---|---|
| **A** | `response=` 없음 | `200` + `{"success":false, …, "status_code":403}` | **281** | 승격 가능 |
| **B** | `response=List[…]` | pydantic 이 dict 를 거부 → **`500`** | **7** | 예외에서 복원 가능 |
| **C** | `response=<단일 스키마>` | **`200` + `{}`** — 거부 사실 **소멸** | **8** | **복원 불가** |

C 가 왜 최악인가: A 는 최소한 `success:false` 를 실어 보내고 B 는 요란하게 실패한다.
**C 는 조용히 성공처럼 보인다.** 클라이언트도 감사 로그도 "권한이 거부됐다"는 사실을 알 수 없다.
`report_template` 4건 · `checklist_setting` 4건 — **둘 다 §0.4 밖 저장소 앱이라 고칠 수 있다.**

---

## 1. 실측 — 무엇을 어떻게 쟀나

권한이 없는 사용자를 만든다: 역할은 주되 `RoleMenu`/`RoleTab` 은 주지 않는다.
`core/role/permission.py:_check_path_permission` 이 그 조합에서 `False` 를 낸다(실측 확인).
그 사용자의 유효한 Bearer 로 각 성격의 라우트를 부른다.

```
A 무스키마     GET  /api/devices/devices-management   -> 200
   {"success": false, "message": {"en":"Permission denied.", "ko":"권한이 거부되었습니다.", …},
    "status_code": 403}

B typed List[] GET  /api/report-template/             -> ValidationError → (DEBUG=False 에서) 500
   1 validation error for NinjaResponseSchema
   response  Input should be a valid list
     [type=list_type, input_value={'success': False, …, 'status_code': 403}, input_type=dict]

C typed 단일   GET  /api/report-template/1            -> 200
   {}
```

**C 의 기전**: 거부 dict 를 단일 출력 스키마로 검증하는데 그 스키마의 필드가 전부 선택적이라
pydantic 이 오류 없이 **빈 객체**를 만든다. 거부 메시지도 `status_code` 도 남지 않는다.

### 1-1. 성격별 분포 (런타임 레지스트리 실측 · grep 아님)

`common.tenant_scope._iter_ninja_apis()` 로 등록된 전 라우트를 열고
`view._path_override`(= `@path_permission` 이 남기는 표식) 가 있는 것만 센다.

```
전체 라우트                652
@path_permission 부착      296
  ├ A 응답스키마 없음      281   (95.0%)
  ├ B List[…]                7   ( 2.4%)  delivery 5 · report_template 1 · checklist_setting 1
  └ C 단일 스키마            8   ( 2.7%)  report_template 4 · checklist_setting 4
```

B 의 5건이 `delivery` 라 **§0.4 안**이다 → 소스 수정 불가 → 예외 경로로 처리해야 한다.
C 의 8건은 **전부 §0.4 밖**이다 → 선택지가 있다(§4).

---

## 2. 프론트 영향 — 승격하면 무엇이 깨지나

승격하면 axios 가 4xx 에서 reject 한다. `then` 분기에서 `res.success` 를 읽던 코드는
그 분기에 **도달하지 못한다**. 그래서 두 가지를 센다: 호출이 보호받는가, 계약에 의존하는가.

`python scripts/scan_frontend_success_contract.py` (읽기 전용 · 원자료 `frontend_success_sites.json`)

```
API 호출 지점                    369
  try/catch · .catch 로 보호      311   (84.3%)
  보호 없음                        58
res.success 를 읽는 지점          191
★ 보호없음 × 계약의존             21   ← 승격 시 무증상 실패 후보 (15개 파일)
```

**폭발반경은 21곳이다.** 369 중 311 이 이미 예외를 잡고 있어서다.

### 2-1. 21곳이 어떻게 실패하는가

이 앱에는 react-query 가 없고(`useQuery`/`useMutation` 0건) `ErrorBoundary` 는
**전 앱에 단 하나**뿐이다(`ReadyToShipTabOptimized` 한 화면). 그래서 잡히지 않은 reject 는
빨간 오류 화면이 아니라 **스피너 고착 — 아무 일도 일어나지 않는 화면**이 된다.
D-248 이 걱정한 "흰 화면"의 실제 모습은 이쪽이다.

전형은 `features/Dashboard/hooks/useDashboard.ts:49` 다:

```ts
const response = await API.get(fullUrl);   // ← try 없음. 403 이면 여기서 함수가 끝난다
if (response.success) { … } else { … }     // ← else 분기가 있는데도 도달하지 못한다
```

`else` 를 이미 써 뒀다는 것이 중요하다 — **거부를 다룰 의사는 있었고 경로만 바뀐다.**

### 2-2. 21곳 (파일별)

| 건 | 파일 |
|---|---|
| 3 | `features/delivery/DeliveryOperation/MainTabs/ReturnedTab/components/ReturnedOrderDetail.tsx` |
| 3 | `features/delivery/DeliveryOperation/MainTabs/ReturnedTab/index.tsx` |
| 2 | `features/Dashboard/hooks/useDashboard.ts` |
| 2 | `features/delivery/DeliveryOperation/MainTabs/VerificationTab/components/VerificationOrderDetail.tsx` |
| 1 | `features/checklistSetting/pages/CheckListSetting.tsx` |
| 1 | `features/Dashboard/DeliveryDashboard/componentsV2/PopoverDevice.tsx` |
| 1 | `features/delivery/DeliveryOperation/hooks/useOperationOrder.ts` |
| 1 | `features/delivery/DeliveryOperation/MainTabs/CompletedTab/components/CompletedOrderDetail.tsx` |
| 1 | `features/delivery/DeliveryOperation/MainTabs/CompletedTab/index.tsx` |
| 1 | `features/delivery/DeliveryOperation/MainTabs/VerificationTab/index.tsx` |
| 1 | `features/delivery/DeliveryReport/components/CompletedOrderDetail.tsx` |
| 1 | `features/delivery/DeliveryReport/index.tsx` |
| 1 | `features/entriOder/AddNewOrder.tsx` |
| 1 | `features/MultiStreamMonitor/components/DroneCameraView/index.tsx` |
| 1 | `features/surveillanceProfile/hooks/useSurveillanceProfile.ts` |

(경로는 `frontend/src/` 기준. 원자료 JSON 에 전체 경로·행번호가 있다.)

⚠️ 15개 중 **10개가 `features/delivery/`** 다. 프론트 delivery 화면은 §0.4 의 "delivery 앱"
(백엔드 3개 앱 269파일)과 별개지만, 배송 라인이라는 점은 같다 — 승격 롤아웃 시 이 화면들을
**마지막 순서**로 두는 근거가 된다.

### 2-3. `status_code` 를 HTTP 뜻으로 읽는 곳은 사실상 없다

프론트 `status_code` 122건 중 **118건이 주문 상태코드**(`mapped_status_code` 등 도메인 값)다.
HTTP 뜻으로 읽는 곳은 `features/surveillanceProfile/hooks/useSurveillanceProfile.ts:243-245`
**하나뿐**이고, 그마저 이미 `errorResponse.response?.data?.status_code` 로 **4xx 경로를 먼저 본다**.
즉 그 화면은 승격 후에 오히려 정상 동작한다.

> **판정**: 승격의 위험은 "status_code 를 읽는 코드가 깨진다"가 아니다.
> **"거부를 200 으로 받아 else 로 처리하던 21곳이 아무 반응도 하지 않게 된다"** 이다.

---

## 3. 부수 실측 — 티켓 ③(문서 정정)의 전제 검증

### 3-1. `/api/token/pair` — "미작동"이 아니라 **더 나쁘다**

티켓 spec ③ 은 "미작동"이라고 적었다. 실측은 다르다.

```
POST /api/token/pair   -> 200   keys = ['access', 'refresh', 'username']   ← 정상처럼 보인다
  그 access 로 auth=CustomJWTAuth() 라우트 호출 -> 401 {"detail": "Unauthorized"}
  DB 확인:  user.token = None
```

기전은 `core/auth.py:37` 의 `if not user.token: raise HttpError(401, "Token expired")` 다.
`token/pair`(ninja_jwt 기본 엔드포인트)는 `user.token` 을 채우지 않는다. 채우는 것은
`/api/v1/auth/login` 뿐이다.

**연동자 입장에서 이것이 왜 중요한가**: 발급은 200 으로 성공하고 **그 다음 호출이** 401 로
죽는다. 그리고 그 401 의 문구가 `"Token expired"`(내부) / `"Unauthorized"`(외부)라
**"방금 받은 토큰이 만료됐다"**는 불가능한 이야기를 한다. 연동 담당자는 시계·TTL 을 의심하며
시간을 버린다. WP-2 ENTRY §86 의 기재가 정확했고, 티켓 spec 의 "미작동"이 느슨했다.

### 3-2. `/api/v1/auth/delete-session` — 쿼리 파라미터로도 **부를 수 없다**

티켓 spec ③ 은 "`data: dict` 라 ninja 가 쿼리 파라미터로 잡으니 호출 예시를 body 가 아닌
실제 동작대로 고치라"고 적었다. 실측은 **네 가지 호출 형태가 전부 422** 다.

| 호출 형태 | 결과 |
|---|---|
| body `{"data":"x"}` | `422 missing · loc:["query","data"]` |
| `?data=x` | `422 dict_type · "Input should be a valid dictionary"` |
| `?data=%7B%22session_id%22%3A%22x%22%7D` (URL 인코딩 JSON) | `422 dict_type` |
| `?session_id=x` | `422 missing · loc:["query","data"]` |

ninja 는 쿼리 문자열에서 `dict` 를 만들지 못한다. **이 엔드포인트는 어떤 방법으로도
호출할 수 없다.** 그러므로 문서 정정의 내용은 "호출 예시를 쿼리로 바꾼다"가 아니라
**"현재 호출 불가임을 명시한다"** 여야 한다. 핸들러는 §0.4 안이라 고칠 수 없다.

### 3-3. 예정에 없던 발견 — `@path_permission` 은 있는데 `auth=` 가 없는 라우트 24건

같은 레지스트리 훑기에서 나왔다.

```
652 라우트 중 auth 콜백 없음     143
  그중 @path_permission 부착      24
     terminals 9 · devices 6 · flight_log 4 · delivery 3 · operational_data 1 · orders 1
```

이 24건은 `CustomJWTAuth` 를 거치지 않고 미들웨어가 복원한 사용자로 권한만 본다.
실측 증거: `token/pair` 가 준(= `CustomJWTAuth` 가 401 로 거부하는) 토큰으로
`/api/devices/devices-management` 를 부르면 **401 이 아니라 권한판정까지 도달한다.**

**W0-18 의 범위가 아니다.** 인증 표면 문제이므로 **P-W0-18-2 로 적재**하고 W0-14/W0-16 으로 넘긴다.
지금 이 티켓에서 손대면 계약 작업과 인증 작업이 한 커밋에 섞인다.

---

## 4. 그래서 어떻게 고치는가 (§2 로 넘기는 설계 입력)

| | 대상 | 방법 | §0.4 |
|---|---|---|---|
| **A** 281 | 응답 본문이 `{"success":false, "status_code":4xx}` 인 200 | **미들웨어 응답단계**에서 실제 상태로 승격 | 무관 |
| **B** 7 | pydantic 이 거부 dict 를 거절해 터진 예외 | **`process_exception`** 에서 `ValidationError.errors()[i]["input"]` 을 읽어 복원 | delivery 5건이 §0.4 안이라 **이 경로가 유일** |
| **C** 8 | 거부가 `{}` 로 소멸 | 응답계층에서 **복원 불가** → §4-1 | 전부 §0.4 **밖** |

B 가 예외 경로로 풀리는 근거: `ninja/errors.py:_default_exception` 이
`if not settings.DEBUG: raise exc` 로 **Django 에 도로 넘긴다** → `process_exception` 이 호출된다.
그리고 pydantic `ValidationError` 는 거부 dict 를 `input` 에 그대로 담고 있다(§1 실측 출력 참조).

### 4-1. C 8건 — 판정이 필요하다 (P-W0-18-1)

C 의 8개 라우트는 `response=<단일 스키마>` 를 선언해 놓고 **성공 시에는 그 스키마를 쓰지 않는다.**
핸들러가 `BaseResponse`(= `JsonResponse` 서브클래스)를 돌려주고 ninja 는 `HttpResponse` 를
검증 없이 통과시키기 때문이다. 즉 **그 `response=` 선언은 이미 실제 응답과 다르다** —
OpenAPI 문서가 지금도 거짓을 말하고 있다.

- **A안(권고)** 8건의 `response=` 선언을 **뗀다.** 성공 응답은 한 글자도 바뀌지 않고
  (어차피 통과였다), 거부는 A 부류가 되어 미들웨어가 승격한다. OpenAPI 는 **거짓 스키마를
  잃는 대신 참을 말하게 된다.**
- **B안** 선언을 유지하고 8개 핸들러 앞에 저장소 쪽 권한 가드를 따로 건다. 중복 판정이 생긴다.
- **C안** 그대로 둔다. 8개 라우트에서 **권한거부가 계속 조용히 사라진다.**

---

## 5. 롤아웃 (D-248 ③ · D-212)

플래그 `API_CONTRACT_PROMOTE_ERROR_STATUS` **기본 False**. 설정 한 곳(`config/settings.py`)에서만 켠다.

```
1단계  플래그 OFF 로 배포          — 기존 동작 그대로. 미들웨어는 경로에 있으나 아무것도 바꾸지 않는다
2단계  스테이징 ON                 — 계약 시험 green + §2-2 의 21곳 수동 확인
3단계  §2-2 의 21곳에 catch 보강    — delivery 화면 10개는 마지막
4단계  운영 ON                     — 되돌리기는 플래그 한 줄
```

**되돌림 기준**: 승격 후 4xx 를 받고도 화면이 반응하지 않는 지점이 하나라도 보고되면 OFF.

---

## 6. 이 조사가 답하지 못한 것

- **운영 프론트 빌드는 이 저장소 소스가 아닐 수 있다** (P-LOCAL-4 — 백엔드 78파일 불일치 실측).
  §2 의 21곳은 **저장소 소스 기준**이다. 운영 번들 기준 재확인은 P-LOCAL-4 판정 뒤에 가능하다.
- `frontend/node_modules` 가 없어(사내 git 소멸) `rj-core` 의 `createApiClient` 내부를 읽지 못했다.
  "axios 가 4xx 에서 reject 한다"는 axios 기본 동작에 근거한 것이고, 이 저장소에는
  `interceptors` 사용처가 0건이라 그 기본을 바꾸는 코드가 저장소 쪽에는 없다.
  rj-core 가 내부에서 `validateStatus` 를 완화했을 가능성은 **남아 있다** → 3단계에서 실측한다.

---

## 7. 구현 중 발견 — 캐시가 승격을 **되돌린다** (배치가 곧 기능이다)

미들웨어를 처음에 `MIDDLEWARE` 목록 **맨 끝**에 뒀다. 시험 하나가 `200 != 403` 으로 실패했고
원인은 이랬다.

`UniversalCacheMiddleware` 는 캐시가 적중하면 저장해 둔 **본문으로 응답을 새로 만든다**:

```python
# common/universal_optimization.py:872
response = JsonResponse(cache_data['data'], safe=False)   # ← 상태코드는 저장하지도, 복원하지도 않는다
```

즉 **캐시에서 나온 응답은 언제나 HTTP 200** 이다. 승격 미들웨어가 캐시보다 안쪽에 있으면
적중한 요청에서는 **호출조차 되지 않는다.** 그리고 그때 시험은 전부 초록이다 —
시험DB 의 캐시가 비어 있어 늘 미스이기 때문이다. **운영에서만 틀린다.**

**해결**: `GZipMiddleware` 보다 안쪽, `UniversalCacheMiddleware` 보다 **바깥**에 둔다.
두 조건은 한 지점에서 만난다(캐시 바로 위). 그 자리를 `MiddlewareOrderTest` 가 못박는다 —
순서를 바꾸면 시험이 먼저 빨개진다.

> 이 자리에서는 캐시가 만든 200 도 다시 승격된다. 부수 효과로 **플래그를 켜는 순간
> 이미 캐시된 거부 응답까지 즉시 4xx 가 된다** — TTL 만료를 기다리는 창이 없다.

**부수 확인 (좋은 소식)**: 캐시 키에는 `g{userprofilelink.group.id}` 가 들어간다
(`_get_user_permission_signature`). **테넌트가 키에 있으므로 캐시가 W0-14 의 격리를
가로질러 새게 하지는 않는다.** 다만 `is_superuser` 는 전원이 `"super"` 한 키를 공유한다.

---

## 8. ★ P-W0-14-4 의 전제를 정정한다 — 남은 3건은 이 계층으로 닫히지 **않는다**

P-W0-14-4 는 W0-14c 의 남은 격리 실패 3건에 대해 "A안 권고 — W0-18 후처리 계층에서
소스 무수정" 이라고 적었다. **실측은 다르다.**

```
플래그 OFF:  python manage.py test tests.test_tenant_isolation  →  4 failures / 1 error
플래그 ON :  같은 명령 · API_CONTRACT_PROMOTE_ERROR_STATUS=true →  4 failures / 1 error
```

**한 건도 움직이지 않는다.** 이유는 셋 다 권한거부가 아니기 때문이다.

| 남은 실패 | 실제 성격 | 후처리로 되는가 |
|---|---|---|
| Order 상세 `500` | `DoesNotExist` 가 핸들러를 빠져나간다. 본문에 거부 dict 가 없다 | **아니다** — 예외의 종류가 다르다 |
| Terminal 수정 `400` + `success:true` | 상태는 4xx 인데 본문이 성공이라고 말한다 (승격의 **반대** 방향) | **아니다** |
| Terminal 삭제 `200` "Deleted successfully" · 행 그대로 | 상태·본문이 아니라 **본문이 거짓**이다 | **아니다** — 어떤 응답 계층도 안 한 일을 한 일로 만들 수 없다 |

D-248 이 지시한 것은 **"권한거부의 상태코드"** 였고 이 계층은 그것을 한다.
P-W0-14-4 는 그것을 **"§0.4 안의 응답 계약 위반 일반"** 으로 넓혀 읽었다.
넓힌 부분은 이 티켓이 못 닫는다 → **P-W0-18-3 으로 적재**한다.

**W0-14 dod 와 WP-2 EXIT 에 미치는 영향**: EXIT 기준 1(누출 0건)은 이 3건과 무관하다 —
정정된 실측에서 **누출은 이미 0** 이고 이 3건은 계약 위반이다(68ac7ef). 다만 EXIT 기준 4
("계약 테스트 green")는 **이 티켓의 계약 시험 19건으로 충족**된다. 3건의 처리 방침은
별도 판정이 필요하다.
