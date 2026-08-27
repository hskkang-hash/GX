# W0-14c ④ 준비 — P0 15종 `Target` 초안 (실경로 + 필수 필드)

**작성** 2026-08-27 · **결정** D-262 ② · D-266 · **티켓** W0-14 · W0-3 (WP-2)
**생성** `python scripts/draft_isolation_targets.py --md` · 입력은 전부 커밋된 실측본

---

## 0. 왜 초안을 미리 만드나

W0-14b 를 죽인 것은 격리 로직이 아니라 **배선**이었다. 실측 결함 4종 중 가장 큰 것이
**필수 FK 24건** — 값이 없어 시험이 **판정에 도달하기 전에 죽었다.**

이제 P0 **15종**을 올려야 한다(D-262 ②). 같은 일을 15번 되풀이하면 기동본 세션이
배선 디버깅으로 끝난다. 그래서 **정적으로 미리 뽑는다** — 어떤 라우트가 이 모델을 만지고,
레코드 하나를 만들려면 무엇이 필요한가.

⚠ **초안이지 정답이 아니다.** 그대로 `MODELS` 에 붙여넣지 않는다:
  · dj-core 의 부모(`BaseModel` 등) 필수 필드는 **저장소 밖이라 보이지 않는다** (표에 표시)
  · 수정/삭제의 메서드 모양은 기동본에서 확인한다 (PATCH 는 저장소 전체에 1건이었다)
  · 추정한 경로 위에 배선을 쌓으면 전부 다시 해야 한다 — W0-14b 의 교훈이 그것이다

## 1. ★ 착수 순서 — D-266 선결 2종이 마침 **가장 싸다**

`flight_log.FlightLog` · `surveillance.VideoAnalysis` 는 **필수 FK 가 0**이다.
즉 WP-DA2 착수를 막고 있는 2종이 배선 비용도 가장 낮다 — 우선순위와 비용이 같은 방향이다.
여기서 먼저 초록을 만들고 패턴을 굳힌 뒤 FK 가 있는 것으로 간다.

**필수 FK 가 없는 4종**(1·2·3·4)이 첫 묶음이다.

## 2. P0 15종 (★ = D-266 WP-DA2 선결)

| # | 모델 | 행 | group NULL | 필수 FK | 단건 경로 | 외부 부모 |
|---:|---|---:|---:|---:|---|---|
| 1 | `flight_log.FlightLog` ★ | 308 | 0.0% | 없음 | `GET /api/flight-log/flight-log/detail/{id}` | MeasurableModelWithGroup |
| 2 | `surveillance.VideoAnalysis` ★ | 117 | 16.2% | 없음 | `GET /api/surveillance/surveillance-profiles/{profile_id}` | BaseModelWithGroup |
| 3 | `terminals.RouteTerminal` | 2,062 | 87.6% | 없음 | `GET /api/terminals/qground-control/export-single-plan/{route_id}` | BaseModel |
| 4 | `task_status.TaskStatus` | 84 | 0.0% | 없음 | `GET /api/optimization/optimization/task-status/{task_id}` | BaseModel |
| 5 | `surveillance.MissionWaypoint` | 8,877 | 100.0% | `mission`→SurveyMission | `GET /api/surveillance/survey-missions/{survey_mission_id}` | BaseModel |
| 6 | `orders.OrderHistory` | 5,882 | 96.8% | `order`→Order | `GET /api/orders/order/{id}` | BaseModel |
| 7 | `orders.OrderItem` | 304 | 0.0% | `order`→Order | `GET /api/operational-data/operational-data/{order_item_id}` | BaseModel |
| 8 | `delivery.DeliveryOperationItem` | 285 | 0.0% | `delivery_operation`→DeliveryOperation | `GET /api/operational-data/operational-data/{order_item_id}` | BaseModel |
| 9 | `surveillance.SurveillanceProfileChecklistItem` | 231 | 31.2% | `checklist`→SurveillanceProfileChecklist | `POST /api/surveillance/surveillance-profiles/{profile_id}/check-complete` | BaseModel |
| 10 | `surveillance.SurveillanceProfileDrone` | 127 | 18.1% | `profile`→SurveillanceProfile | `GET /api/surveillance/surveillance-profiles/{profile_id}` | BaseModel |
| 11 | `orders.OrderStatusMapping` | 84 | 0.0% | `delivery_status`→delivery.DeliveryStatus | `GET /api/orders/order-status-mappings/{mapping_id}` | BaseModelWithGroup |
| 12 | `delivery.DeliveryOperation` | 304 | 0.0% | `order`→orders.Order, `current_status`→DeliveryStatus | `GET /api/third-api/delivery/confirmation/{operation_id}/photo/` | BaseModel |
| 13 | `terminals.TerminalOperatingTime` | 98 | 100.0% | `terminal`→Terminal, `day_of_week`→DayOfWeek | `GET /api/terminals/terminals/{id}` | BaseModel |
| 14 | `surveillance.SurveillanceProfileChecklist` | 83 | 12.0% | `profile`→SurveillanceProfile, `profile_drone`→SurveillanceProfileDrone | `GET /api/surveillance/surveillance-profiles/{profile_id}` | BaseModelWithGroup |
| 15 | `orders.Payment` | 64 | 0.0% | `order`→Order, `payment_type`→PaymentType | `GET /api/orders/external-order-statuses/{external_status_id}` | BaseModel |

> **`group NULL 100%` 가 셋**(MissionWaypoint 8,877 · TerminalOperatingTime 98 ·
> RouteTerminal 87.6% 2,062). 이들은 **W0-13 백필 (a) 의 대상이기도 하다** —
> 백필 전에는 "안 보이는 것"이 격리 때문인지 소유가 비어서인지 구별되지 않는다.
> **순서는 D-261 대로 백필이 먼저다.**

## 3. Target 초안 코드

`python scripts/draft_isolation_targets.py --py` 가 아래를 생성한다. 기동본에서 **하나씩** 확인하며 올린다.

```python
# ⚠ 초안이다. 기동본에서 하나씩 확인하며 MODELS 에 올린다 (W0-14b 교훈).
# 필수 FK 는 Deps 헬퍼로 만든다. 외부 부모(dj-core)의 필수 필드는 여기 없다.

    # flight_log.FlightLog — 행 308 · 필수FK 0  ★ D-266 선결
    Target(
        "FlightLog", "flight_log", "FlightLog",
        list_path='/api/flight-log/flight-log/',
        detail=Route('GET', '/api/flight-log/flight-log/detail/{id}'),
        # 쓰기 후보: DELETE /api/flight-log/flight-log/delete/{ids}  ← 수정/삭제 구분은 기동본에서 확인
        factory=lambda d, n: {},   # 필수 FK 없음(정적 판정)
    ),

    # surveillance.VideoAnalysis — 행 117 · 필수FK 0  ★ D-266 선결
    Target(
        "VideoAnalysis", "surveillance", "VideoAnalysis",
        list_path='/api/surveillance/surveillance-dashboard/abnormal-signs-overview',
        detail=Route('GET', '/api/surveillance/surveillance-profiles/{profile_id}'),
        factory=lambda d, n: {},   # 필수 FK 없음(정적 판정)
    ),

    # terminals.RouteTerminal — 행 2,062 · 필수FK 0
    Target(
        "RouteTerminal", "terminals", "RouteTerminal",
        list_path='/api/delivery/processing/routes',
        detail=Route('GET', '/api/terminals/qground-control/export-single-plan/{route_id}'),
        # 쓰기 후보: PUT /api/terminals/routes/{id}  ← 수정/삭제 구분은 기동본에서 확인
        factory=lambda d, n: {},   # 필수 FK 없음(정적 판정)
    ),

    # task_status.TaskStatus — 행 84 · 필수FK 0
    Target(
        "TaskStatus", "task_status", "TaskStatus",
        # list_path: NO_ROUTE 사유 필요
        detail=Route('GET', '/api/optimization/optimization/task-status/{task_id}'),
        # 쓰기 후보: POST /api/surveillance/surveillance-profiles/{profile_id}/download-analysis-for-profile  ← 수정/삭제 구분은 기동본에서 확인
        factory=lambda d, n: {},   # 필수 FK 없음(정적 판정)
    ),

    # surveillance.MissionWaypoint — 행 8,877 · 필수FK 1
    Target(
```

## 4. 기동본에서 할 확인 3가지

1. **수정/삭제 경로의 실제 모양** — 이 저장소는 `PATCH` 가 전체에 1건뿐이고, 수정은 PUT(devices 는 POST),
   삭제는 대개 `delete/{ids}` 대량 경로다. 초안의 "쓰기 후보"는 그 구분이 안 돼 있다.
2. **dj-core 부모의 필수 필드** — `BaseModel` · `BaseModelWithGroup` · `MeasurableModelWithGroup`
   은 저장소 밖이다. `manage.py` 가 있는 곳에서 `model._meta.get_fields()` 로 확인한다.
3. **라우트가 없는 시나리오는 `NO_ROUTE` 에 사유와 함께** 등재한다. 조용히 건너뛰면
   "5/5 초록"이 실제 커버리지보다 커 보인다 — 증가금지 래칫은 그대로 쓴다.

## 5. 하지 않은 것

| 항목 | 왜 |
|---|---|
| `MODELS` 에 실제 등재 | 시험을 돌릴 수 없는 곳에서 시험 파일을 고치지 않는다 (금지 #5 취지) |
| factory 본문 완성 | dj-core 부모 필드를 못 본다. 반쯤 맞는 factory 는 없느니만 못하다 |
| P1 50종 초안 | EXIT 필수가 아니다(D-262 ③). 계획만 등재 — `exit_coverage_appendix.md` |

