# W0-14c 선행 — 격리 시험이 **보지 않고 있는 것**을 셌다

> ## ▲ 2026-08-27 **2차 재측정 (D-263)** — 아래 1차 수치는 대체됐다
>
> D-263 이 **앱 단위 매칭 금지 · 모델별 실경로 매칭**을 지시했다. 이름 매칭을 폐기하고
> **핸들러가 실제로 만지는 모델을 AST 로 추적**하는 방식으로 다시 쟀다.
> 결론이 바뀌었다 — **§7 을 정본으로 읽을 것.** 1차(§0~§6)는 방법과 그 한계의 기록으로 남긴다.
>
> | | 1차 (이름 매칭) | 2차 (실경로 추적) | **3차 (단건 정의 시정)** |
> |---|---:|---:|---:|
> | P0 — EXIT 필수 | 6종 | 19종 | **15종** |
> | P1 — 계획 등재 | 17종 | 46종 | **50종** |
> | 미검토 | 99종 | 57종 | **57종** |
>
> **3차(같은 날) 정정**: 2차는 **pk 가 없는 쓰기**(`POST /approve-flight` 처럼 요청 **본문**으로
> 대상을 고르는 라우트)를 "단건 경로"로 셌다. 그것은 IDOR 경로가 아니라 배선이 다른 별개 위험이다.
> 섞으면 "단건 경로"가 부풀고 그러면 P0 가 부푼다 — **또 하나의 "구별하지 못하는 수"**다.
> 분리했더니 4종이 P0→P1 로 내려갔다. 그 4종은 사라진 것이 아니라 **P1 에서 사유와 함께 센다.**
> **§7 을 정본으로 읽되 수치는 이 표를 따른다.**

**실행** 2026-08-27 · **결정** D-260 · **티켓** W0-14 · W0-3 (WP-2)
**도구** `scripts/build_leak_targets.py` · **원자료** `evidence/W0-14/leak_targets.json`
**앞 문서** `w0_14c_write_guards_and_correction.md` (2026-08-24 · 정정본이 정본이다)

---

## 0. 판정 — **EXIT 조건 1 은 지금 판정 불가다. 모수가 밝혀져 있지 않기 때문이다**

> WP-2 EXIT 조건 1 은 **"재현 누출 0건(전 계정) · 격리 시나리오 5/5"** 다.
> 그런데 그 "5 시나리오"가 도는 대상은 **9종**이고, 테넌트성 모델은 **131종**이다.
>
> | | 수 | 뜻 |
> |---|---:|---|
> | 테넌트성 모델 (W0-13 실측) | **131** | `created_by` + (`group`\|`groups`) 를 가진 모델 |
> | 격리 시험 `MODELS` 가 보는 것 | **9** | 나머지는 시험이 존재를 모른다 |
> | **보지 않는 것** | **122** | 여기에 대해 우리가 말할 수 있는 것은 "누출 없음"이 아니라 **"모른다"** |
>
> 122종에 대해 "누출 0건"이라고 쓰면 그것은 측정이 아니라 **가정**이다.
> `tickets.sha256`(WP-0 EXIT §6-1)이 게이트로 기능한 적이 없던 것과 같은 모양이다 —
> 초록불이 실제 커버리지보다 커 보인다.

**그러므로 W0-14c 의 남은 일은 "648 라우트 부착"이 아니라 판정 도구의 커버리지다.**
(부착률은 EXIT 기준이 아니다 — D-249 · `coverage.md` §3.)

---

## 1. 전제 확인 — 격리 자체는 버티고 있다

이 문서는 **정정본**(`w0_14c_write_guards_and_correction.md` §1) 위에 선다:

- **list 8/8 통과** — 목록은 이미 좁혀져 있다.
- 남은 실패 3건은 **누출이 아니라 응답 계약 위반**(Order 상세 500 · Terminal 수정 400 ·
  Terminal 삭제가 "성공"이라 거짓말)이고 셋 다 §0.4 금지구역 → W0-18 / `P-W0-14-4`.
- 직전 보고의 "detail 5 · update 3 · delete 5 누출"은 **시험 픽스처 오염**이었다.

즉 **고칠 것을 못 찾은 게 아니라, 볼 것을 덜 보고 있었다.** 이 문서가 그 크기를 잰다.

---

## 2. 어떻게 셌나 — **새로 정의하지 않고 이미 잰 것을 대조했다**

테넌트성 모델의 정의를 여기서 다시 만들면 그 수는 W0-13 의 수와 갈리고, **어느 쪽이
진실인지 아무도 모르게 된다**(D-227 manifest 유실과 같은 실패 모양). 그래서 입력이 전부 기존 실측본이다:

| 입력 | 무엇 | 어디서 잰 것 |
|---|---|---|
| (a) `evidence/W0-13/backfill_dryrun.txt` | 테넌트성 모델 **131종** + 행 수 + group NULL | Django 실측 (W0-13 dry-run) |
| (b) `evidence/W0-14/openapi_routes.json` | 등록 오퍼레이션 **531건** | 런타임 실측 (W0-14) |
| (c) `backend/tests/test_tenant_isolation.py` | 현재 `MODELS` 레지스트리 | **AST** — import 하지 않는다 |

(c)를 AST 로 읽는 이유: 이 파일은 Django 설정과 dj-core 를 요구한다. AST 면 **어느 머신에서나
돌고, 읽기만 한다.** 그래서 이 스크립트는 로컬 기동본 없이도 판정을 낸다.

### 2-1. 만든 도구의 결함 2건을 먼저 적는다 (둘 다 이번에 잡았다)

| # | 결함 | 어떻게 드러났나 | 고침 |
|---|---|---|---|
| ① | `MODELS` 를 **0종**으로 읽었다 | `MODELS: tuple[Target, ...] = (...)` 는 `ast.Assign` 이 아니라 **`AnnAssign`** 이다. "시험이 아무것도 보지 않는다"는 결과가 나와서야 드러났다 | `AnnAssign` 처리 추가 |
| ② | 후보가 부풀었다 (`delivery` 12모델이 똑같이 "단건 23건") | 슬러그에 `app_label` 을 넣어 **그 앱의 라우트 전부가 그 앱의 모델 전부에** 붙었다. 수가 커서 진척처럼 보이지만 **아무것도 구별하지 못하는 수**였다 | 모델명 슬러그만 사용. 앱 단위 수는 `app_single_routes` 로 **따로** 센다 |

②는 남길 가치가 있다 — 정적 수를 진짜 수인 척 쓰는 것이 이 저장소가 반복해서 만난 실패다.

---

## 3. 결과

```
[TARGETS] 테넌트성 모델 131종 (W0-13 실측)
[TARGETS] 격리 시험이 보는 것 9종 · 보지 않는 것 122종
[TARGETS] 우선순위  P0=6  P1=17  P2=99 (모델명 매칭 0건)
[TARGETS] ⚠ P2 중 93종은 같은 앱에 단건 경로가 있다 — 자동으로 면제하지 않는다
[TARGETS] ⚠ 시험에는 있으나 인구조사에 없다: ['stream_monitors.DetectionEvent']
```

### 3-1. P0 — 시험 밖 · 단건 경로 있음 · 행 50+ (여기부터 `Target` 에 올린다)

| 모델 | 행 | group NULL | 단건 경로 | 대표 경로 |
|---|---:|---:|---:|---|
| `menu.Menu` | 107 | 52.3% | 12 | `GET /api/menu/menu-base-role/{role_ids}` |
| `orders.OrderStatusMapping` | 84 | 0.0% | 5 | `GET /api/orders/order-status-mappings/available-statuses/{group_id}` |
| `flight_log.FlightLog` | 308 | 0.0% | 3 | `GET /api/flight-log/flight-log/detail/{id}` |
| `surveillance.VideoAnalysis` | 117 | 16.2% | 2 | `GET /api/surveillance/video-analysis/{video_analysis_id}` |
| `task_status.TaskStatus` | 84 | 0.0% | 2 | `GET /api/optimization/optimization/task-status/{task_id}` |
| `orders.Payment` | 64 | 0.0% | 1 | `POST /api/orders/order/{id}/payment` |

**단건 경로(IDOR)를 우선으로 둔 근거**는 정정본 §1 이다 — 목록은 8/8 통과했고,
뚫릴 수 있는 면은 단건 경로다. "화면에 안 보이니 안전하다"가 거짓이라는 것을 그 표가 보여 준다.

`flight_log.FlightLog`(308행)와 `surveillance.VideoAnalysis`(117행)는 **재난안전 App(F-13 정찰 ·
F-01~03 탐지)이 직접 쓸 데이터**다. 에스비 채널은 고객사별 분리가 전제이므로(계약 §2.2-4)
이 둘이 시험 밖에 있는 것은 WP-DA2 착수 전에 닫아야 한다.

### 3-2. ★ P2=99 를 "라우트가 없다"로 읽으면 안 된다

**P2 중 93종은 같은 앱에 단건 경로가 있다.** 모델명이 경로 세그먼트와 안 맞았을 뿐일 수 있다
(이 저장소는 동사형 경로가 흔하다 — `POST /{id}/change-status` · `POST /{id}/cancel-order`).

자동 분류를 면제로 쓰면 `PUBLIC_ROUTES` 도피로(`coverage.md` §2)와 같은 착시가 된다:
**미분류가 면제로 위장하면 시험은 초록이 되고 노출은 그대로 남는다.**
그래서 이 93종은 면제가 아니라 **사람이 봐야 하는 몫**으로 남긴다.

### 3-3. 대조가 잡아낸 불일치 1건

`stream_monitors.DetectionEvent` 는 **시험에는 있고 인구조사에는 없다.**
W2-1 의 마이그레이션이 운영 스키마에 적용되지 않아 W0-13 이 셀 때 테이블이 없었기 때문이다
(정정본 §3 "DetectionEvent 테이블 생성 — W2-1 미적용"과 같은 사실).
**불일치를 지우지 않고 출력에 띄운다** — 두 실측본이 갈렸다는 것 자체가 정보다.

---

## 4. 이것이 W0-14c 를 얼마나 줄이나

| 읽는 방식 | 작업량 | 판정 |
|---|---|---|
| "648 라우트에 데코레이터 부착" | O(648) | 부착률은 **EXIT 기준이 아니다** (D-249) |
| **"시험 대상을 9 → 131 로"** | P0 **6종** 먼저 → P1 17종 → P2 93종 검토 | 각 종이 5시나리오를 얻고, **누출 0건의 모수가 밝혀진다** |

P0 6종을 `Target` 에 올리는 것이 다음 작업이다. `NO_ROUTE` 등재부와 증가금지 래칫은 그대로 쓴다.

---

## 5. 하지 않은 것

| 항목 | 왜 |
|---|---|
| `Target` 레지스트리에 실제로 추가 | 이 커밋은 **세는 것**까지다 (D-260). 추가는 실경로 확인이 선행 — W0-14b 가 배선 결함 4종을 만난 이유다 |
| 누출 자체의 수정 | W0-14c 본체. 그리고 남은 실패 3건은 §0.4 안이다 (`P-W0-14-4`) |
| 시험 실행 | 이 머신에 dj-core 가 없다. 실행은 로컬 기동본에서 — `RUNBOOK_로컬기동.md` |
| P2 93종의 자동 면제 | **면제하지 않는다.** §3-2 |
| `is_group_isolatable()` 확장 | `P-LOCAL-3` 미결. 판정 함수라 손대지 않는다 (D-105) |

## 6. 재현

```bash
python scripts/build_leak_targets.py          # 요약 + 커버리지 델타
python scripts/build_leak_targets.py --json   # evidence/W0-14/leak_targets.json 갱신
python scripts/build_leak_targets.py --md     # P0·P1 표를 마크다운으로
```
※ Django·dj-core 불필요. 입력이 전부 커밋된 실측본이다.


---

# 7. ★ 2차 재측정 (2026-08-27 · D-263) — **이것이 정본이다**

## 7-0. 무엇을 바꿨나

1차는 **모델 이름과 경로 세그먼트**를 맞췄다. 그 방식은 두 방향으로 다 틀린다:

| 설정 | 증상 |
|---|---|
| 앱 슬러그 **포함** | `delivery` 12모델이 **똑같이** "단건 23건" — 수는 크지만 **구별력 0** |
| 앱 슬러그 **제외** | 동사형 경로(`POST /{id}/cancel-order`)를 놓쳐 미검토가 99종으로 부풀었다 |

**둘 다 이름을 보고 있었다는 것이 문제다.** 2차는 이름 대신 **코드**를 본다 —
`scripts/map_routes_to_models.py` 가 `라우트 → 핸들러 → (호출 함수) → 모델 클래스` 를
AST 로 추적한다. 호출 해석은 **그 모듈이 실제로 import 한 모듈 안에서만** 한다.
결과는 후보가 아니라 **근거(파일:행)를 가진 매핑**이다. Django·dj-core 불필요.

## 7-1. 만드는 과정에서 잡은 결함 2건 — 둘 다 실측이 드러냈다

| # | 결함 | 어떻게 드러났나 | 왜 위험했나 |
|---|---|---|---|
| ① | 호출 그래프 **폭주** | `ChecklistSetting` 이 "단건 313건"으로 나왔다. 이름만으로 함수를 찾아 앱을 넘나든 결과 | 1차의 앱 단위 매칭과 **같은 결함**이다 — 수가 커서 진척처럼 보이는 수 |
| ② | **거짓 음성** | `flight_log.FlightLog` 에 `/detail/{id}`·`/delete/{ids}` 가 실재하는데 매퍼가 "목록뿐"이라 했다 | 핸들러 `get_flight_log_detail` 이 **자기와 같은 이름의** 서비스 메서드를 가려, 해석이 자기 자신에서 끝났다. 그대로 갔으면 FlightLog 가 **조용히 면제**된다 — D-263 이 금지한 그 상태 |

②가 더 무섭다. ①은 수가 이상해서 보이지만, ②는 **아무 경고 없이 커버리지를 줄인다.**
그리고 그 모델은 하필 **D-266 이 WP-DA2 착수 전 필수로 지정한 2종 중 하나**였다.

## 7-2. ★ 결과 — P0 가 6종에서 **15종**으로 늘었다 (EXIT 필수 범위가 2.5배)

```
테넌트성 모델 131종 · 시험이 보는 것 9종 · 보지 않는 것 122종
P0 = 15 (EXIT 필수 · D-262 ②)   P1 = 50 (계획 등재 · ③)   UNREVIEWED = 57 (사유 첨부 · ④)
```

> **이 절이 처음에 적은 수는 19/46 이었다.** 같은 날 3차로 정정했다 —
> pk 없는 쓰기를 단건에서 뺐다(위 배너). 아래 P0 표는 15종판이다.

> **D-262 는 "P0 6종"으로 쓰였다. 그 수는 1차 측정의 것이다.**
> D-263 이 지시한 재측정 결과 **19종**이므로, EXIT 조건 ②의 실제 범위는 세 배다.
> 이 사실을 숨기고 6종만 닫으면 EXIT 는 초록이 되고 13종은 모수 밖에 남는다 —
> **D-262 가 고치려던 바로 그 실패의 재발**이다. 그래서 수를 갱신해 올린다.

### P0 15종 (EXIT 필수 · **pk 를 지목하는** 경로가 닿고 행 50+)

착수 순서대로 적는다 — D-266 선결 2종 먼저, 그 다음 **필수 FK 가 적은 순**(배선이 싼 순).
필수 FK 는 `scripts/draft_isolation_targets.py` 가 모델 선언에서 정적으로 뽑은 것이다
(W0-14b 를 죽인 것이 바로 그 필수 FK 24건이었다).

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

★ **D-266 선결 2종이 마침 필수 FK 0 이다** — 우선순위와 배선 비용이 같은 방향이다.
  필수 FK 가 없는 4종(1~4)이 첫 묶음이고, 여기서 패턴을 굳힌 뒤 FK 가 있는 것으로 간다.
  전문·Target 초안: `evidence/W0-14/p0_target_draft.md`

**★ 2종은 D-266 의 WP-DA2 선결 대상**이고 **최우선**이다.

★ 주목: `group NULL 100%` 가 넷이다(MissionWaypoint 8,877 · DeliveryOperationApprovalChecklist
3,013 · OrderAssignment 261 · TerminalOperatingTime 98). 이들은 **W0-13 백필(a) 의 대상**이기도
하다 — 백필이 끝나야 격리 시험의 기대값이 의미를 갖는다. 순서는 D-261 대로 백필이 먼저다.

## 7-3. UNREVIEWED 57종 — **면제가 아니다**

합계 **15,210행**. 자동 면제하지 않는 이유는 분류 사유 그 자체다:

> "핸들러 AST 추적에서 이 모델을 만지는 라우트를 **찾지 못했다.**
>  '라우트 없음'이 아니라 '못 찾았다'로 읽어야 한다 — 동적 디스패치·시그널·
>  Celery 태스크 경로는 이 추적이 보지 못한다."

행이 많은 순 상위:

| 모델 | 행 | group NULL | 성격(1차 판단 — 확정 아님) |
|---|---:|---:|---|
| `advanced_table.GridSettingUser` | 3,230 | 28.0% | 화면 설정 — 공용 마스터 후보 (D-261 c) |
| `orders.DeliveryEvent` | 3,033 | 100.0% | **업무 데이터** — 부모(Terminal) 상속 대상 (D-261 a) |
| `delivery.Address` | 1,353 | 0.0% | 업무 데이터 |
| `file_management.UserMediaFile` | 1,077 | 20.8% | 업무 데이터 |
| `advanced_table.GridSetting` | 928 | 82.2% | 화면 설정 — 공용 마스터 후보 |
| `menu.RoleMenu` | 923 | 4.4% | 메뉴 마스터 — 공용 후보 |
| `user.Timezone` | 598 | 100.0% | **공용 마스터 확정** (D-261 c) |

이 표의 "성격"은 **판단이 아니라 다음 작업의 입력**이다. D-262 조건 ④ 는 57종 **각각**의
사유를 요구하므로, 기계 사유는 `leak_targets.json` 의 `reason` 에 전건 들어 있고,
사람 판단(공용/업무/미사용)은 W0-13 백필 (b)(c) 분류와 **같은 표에서** 결정한다 — 두 번 판단하지 않는다.

## 7-4. 재현

```bash
python scripts/map_routes_to_models.py --json        # 라우트↔모델 실경로 매핑
python scripts/build_leak_targets.py --json          # 분류 (P0 / P1 / UNREVIEWED)
python scripts/map_routes_to_models.py --model flight_log.FlightLog   # 한 모델의 근거 전문
```
