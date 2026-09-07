# D-368 턴 J — `read_only_in_practice` 5자리를 **실제로 재서** 갈랐다. 하나는 P0 이었다

- 집행: 차선 S · **2026-09-07 턴 J** · 서버 `http://localhost:8000`(gx-shell) · 커밋 없음
- 술어를 바꿨다: 「[정적] 핸들러 본문에 쓰기 호출 없음」 → **행수·최신수정시각을 앞뒤로 재고, 호출 그래프를 한 겹 더 따라간다**
- 결과: **쓴다 1 (닫았다) · 안 쓴다 4 (관문이 이미 섰다 — 판정이 틀렸던 것)** · 잔여 `read_only_in_practice` 5 → 4

---

## 0. 왜 정적 판정이 틀렸나 — **술어가 한 겹만 본다**

`probe_write_surface.py` 는 `writes_by: "[정적] 핸들러 본문에 쓰기 호출 없음"` 으로 적었다.
그 술어는 **핸들러 함수 본문**만 본다. 핸들러가 서비스를 부르고 그 서비스가 쓰면 안 보인다.
그리고 그 탐침은 `view_func` 를 **대체물로 바꾸고** 때리므로, 뷰 안에 있는
`@path_permission` 도 함께 사라진다 — 그래서 「도달했다」가 실제보다 넓게 나온다.

## 1. 잰 법 — 두 술어를 같이 (익명 · 없는 id `999999999`)

```
모델 117개 · 행 합계 53,411 · 술어 = (행수, 최신수정시각) 둘 다
  시각칸이 있는 모델 114 / 없는 3  (없는 쪽은 UPDATE 를 못 본다 — 그렇게 적는다)
```

각 자리마다 **앞 스냅샷 → 익명 요청 1회 → 뒤 스냅샷**. 실재 id 는 한 번도 안 썼다.

## 2. 결과 [실측 2026-09-07 · 인증 헤더 없음]

| 경로 | HTTP | 응답 | 행·시각 변화 | 판정 |
|---|---|---|---|---|
| `POST /api/delivery/etri-integration/receive-from-etri` | **400** | `Delivery operation with ID 999999999 not found` | 없음 | ★ **핸들러가 실제로 돌았다** |
| `POST /api/delivery/processing/assign-packages-to-drone` | 200 | `success:false · status_code:403 · Permission denied.` | 없음 | 관문이 섰다 |
| `POST /api/delivery/processing/assign-packages-to-drones` | 200 | 같음 | 없음 | 관문이 섰다 |
| `POST /api/delivery/verification/verify-orders` | 200 | 같음 | 없음 | 관문이 섰다 |
| `POST /api/orders/order/999999999/payment` | 200 | 같음 | 없음 | 관문이 섰다 |
| **전체 앞뒤** | | | **행수·최신수정시각 둘 다 안 움직였다** | |

**넷은 `read_only_in_practice` 가 아니라 `gated` 였다.** 그 넷을 「도달했다」로 읽게 만든 것이
바로 SEC-11a 가 고치고 있는 **200 봉투**다 — 거절이 200 으로 나가니 탐침이 성공으로 셌다.
판정기의 병과 제품의 병이 **같은 병**이다.

## 3. 남은 하나 — `receive-from-etri` 는 **쓴다.** P0 이고 닫았다

호출 그래프를 한 겹 더 따라갔다:

```
delivery/views/api.py:1600   @route.post("/receive-from-etri")      ← auth= 없음 · @path_permission 없음
delivery/views/api.py:1623   DeliverySystem.receive_status_from_etri(etri_data, request)
  → delivery/services/etri_service.py:368  EtriService.receive_status_from_etri
    → :417  _update_delivery_status(...)
        delivery_operation.order.status = OrderStatus.objects.get(code='cancelled')
        delivery_operation.order.save()            ← 남의 주문을 **취소한다**
        delivery_operation.save()
        OrderService.create_order_history(...)     ← 이력까지 쓴다
```

**익명이 `RECEIPT_ID` 하나만 알면 남의 배송을 취소·완료 처리할 수 있다.**

⚠ 두 사실을 섞지 않는다:
- 「쓴다」의 근거는 **호출 그래프**다(실재 id 로 두드리지 않았으므로 실측이 아니다).
- 「이 입력으로는 안 썼다」의 근거는 **위 표의 행·시각 0 변화**다(없는 id 라서 못 쓴 것이다).

### 옆자리 점검 — 진짜 입구만 열려 있었다

인벤토리 전수에서 `etri` 를 가리키는 라우트 12자리 중 익명(`authn=''`)은 셋뿐이고,
그중 **mock 둘은 이미 `AUTHN_REQUIRED_PATHS` 에 있었다**:

```
POST /api/delivery/etri-mock/receive-delivery        (이미 막힘)
GET  /api/delivery/etri-mock/test-scenarios          (이미 막힘)
POST /api/delivery/etri-integration/receive-from-etri  ← 이것만 열려 있었다
나머지 9자리는 전부 auth=CustomJWTAuth
```

**모의를 막고 진짜를 열어 둔 모양**이다.

### 닫은 법 — `backend/delivery/` 는 §0.4 라 우리 층에서 막는다 (D-348)

`common/access_gate.py` 의 `AUTHN_REQUIRED_PATHS` 에 한 줄. 전/후 [실측]:

```
전  POST … (인증 없음) → HTTP 400  "Delivery operation with ID 999999999 not found"
후  POST … (인증 없음) → HTTP 401  {"detail":"Unauthorized","reason":"authentication required"}
```

⚠ 되돌리기: 그 한 줄을 뺀다. 되돌릴 조건 — ETRI 가 **자격증명을 하나도 안 싣고** 호출하는
것이 계약으로 확인되면. 이 관문은 자격증명의 **있음**만 본다(`_has_credentials`) —
ETRI 가 `Authorization` 이나 `X-API-Key` 를 아무거나 실으면 지금도 그대로 지나간다.
막히는 것은 **아무것도 안 싣고 오는 요청**뿐이다.
★ 세종 미판정 · 기본값(닫힌 쪽 · 되돌릴 수 있는 쪽) 택함.

## 4. 게이트

```
전  관문 14 · 도달·안씀 5 · 선언 11
후  관문 15 · 도달·안씀 4 · 선언 11    ← verify_write_auth.py 초록 (writes 0)
```

## 5. 못 쟀다 (회색)

- 남은 4자리가 **권한 있는 계정**에서 쓰는지는 안 쟀다. 이 문서가 재는 것은 「익명이 쓰는가」다.
- `receive-from-etri` 가 **유효한 id 로** 실제로 주문을 바꾸는지는 안 쟀다 —
  그것을 재는 유일한 방법이 사고를 내는 것이기 때문이다. 근거는 호출 그래프로 남긴다.
- 행수·시각 술어는 **시각칸이 없는 모델 3종의 UPDATE 를 못 본다.**
