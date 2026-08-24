# W0-13 ③ — 소유자 백필 **dry-run 리포트** (한 행도 쓰지 않았다)

**실행** 2026-08-24 · **결정** D-254(652 확대 전 백필 선행) · D-209(dry-run 선행 강제)
**대상 DB** `database_guardianx` (운영 복제본 · **읽기 전용 질의만**. D-245 무변경 유지)
**도구** `scripts/backfill_owner_dryrun.py` · 원자료 `evidence/W0-13/backfill_dryrun.txt`

---

## 0. 판정 — **"전량 백필"은 불가능하고, 그렇게 해서도 안 된다**

> 테넌트성 모델 131종 · 45,277행 중 **소유 group 이 없는 행이 30,200 (66.7%)** 이다.
> 그런데 그 30,200 은 **성격이 셋으로 갈린다.**
>
> | 부류 | 행 수 | 어떻게 정하나 |
> |---|---:|---|
> | **A. 부모에게서 물려받을 수 있다** | **23,273** | 자동 (R3 — 부모 레코드의 group) |
> | **B. created_by 로 정할 수 있다** | 343 | 자동 (R2) |
> | **C. 근거가 없다** | **6,584** | **사람이 정해야 한다** — 그리고 그중 상당수는 애초에 테넌트 데이터가 아니다 |
>
> **C 를 기계적으로 어느 테넌트에 밀어넣으면 화면이 거짓을 말하게 된다.** 국가·시간대·통화·
> 메뉴는 특정 고객의 것이 아니다. C 를 가르는 것이 이 리포트가 대표께 묻는 것이다.

---

## 1. 합계 (operation_settings 제외 — §4)

```
total=45,277  created_by_null=29,902  group_null=30,200  both_null=29,857
R1(group 있음→created_by 채움)=45   R2(created_by 있음→group 채움)=343
R3(부모의 group 물려받기)=23,273
```

* `created_by IS NULL` 29,902 (66.0%) — W0-13 착수 시점 실측 65.9% 와 일치한다 (재확인).
* **두 구멍은 방향이 반대다.** `created_by NULL` 은 dj-core 매니저의 OR 때문에 **전 테넌트에
  노출**되고, `group NULL` 은 W0-14 의 명시적 필터에서 **아무에게도 안 보인다**.
  그래서 백필은 노출을 막는 동시에 손실을 되돌린다 — D-254 가 확대 전에 두라고 한 이유다.

## 2. A 부류 — 부모에게서 물려받는다 (자동 · 23,273행)

| 모델 | group NULL | R3 로 덮이는 행 | 부모 |
|---|---:|---:|---|
| `surveillance.MissionWaypoint` | 8,877 | **8,877** | `mission → SurveyMission` |
| `orders.OrderHistory` | 5,696 | **5,696** | `order → Order` |
| `delivery.DeliveryOperationApprovalChecklist` | 3,013 | **3,013** | `approval → DeliveryOperationApproval` |
| `orders.DeliveryEvent` | 3,033 | 2,995 | `terminal_stop → Terminal` |
| `terminals.RouteTerminal` | 1,807 | **1,807** | `route → Routes` |
| `delivery.DeliveryOperationHistory` | 280 | 280 | `delivery_operation → DeliveryOperation` |
| `orders.OrderAssignment` | 261 | 261 | `order_item → OrderItem` |
| `terminals.TerminalOperatingTime` | 98 | 98 | `terminal → Terminal` |
| `surveillance.SurveillanceProfileChecklistItem` | 72 | 72 | `checklist_setting → ChecklistSetting` |
| 그 외 11종 | — | 174 | (원자료 참조) |

이 부류는 **논리적으로 안전하다** — 자식 행의 소유 테넌트는 정의상 부모와 같다.
다만 부모가 group NULL 이면 물려줄 것이 없으므로 **부모부터 위로 올라가며 순서대로** 채워야 한다
(예: `RouteTerminal → Routes` 를 채우기 전에 `Routes` 가 정해져 있어야 한다).

## 3. C 부류 — 근거가 없는 6,584행. **여기가 판정이 필요한 곳이다**

부모도 없고 created_by 도 없는 모델 110종. 상위를 성격별로 갈랐다.

### 3-1. 실제 테넌트 데이터인데 근거가 없다 — **1건이 크다**

| 모델 | 총행 | group NULL | 왜 문제인가 |
|---|---:|---:|---|
| **`terminals.Terminal`** | 5,686 | **3,399 (60%)** | 배송·순찰의 기준 장소다. 직접 부모가 없어 자동 귀속 불가. 이 3,399가 W0-14 확대 시 **비전역 계정 화면에서 사라진다** |

> `Terminal` 은 `RouteTerminal`·`TerminalOperatingTime`·`DeliveryEvent` 의 **부모**다.
> 즉 이 3,399를 정하지 못하면 그 아래 4,900여 행도 연쇄로 정할 수 없다. **최우선 판정 대상.**

#### ★ 역추론 실측 — 데이터가 답을 갖고 있었다 (읽기 전용)

참조 8경로를 전수로 훑어 각 orphan Terminal 이 **어느 테넌트에서 쓰였는지** 셌다
(`RouteTerminal` · `Routes.terminal_from` · `Order.pickup_location` · `Order.delivery_terminal` ·
`Device.terminal` · `MissionWaypoint.terminal` · `FlightLog.start_point` · `FlightLog.end_point`).

| 판정 | 터미널 수 | 뜻 |
|---|---:|---|
| **단일 테넌트에서만 쓰였다** | **1,809** | 소유가 하나로 정해진다. **자동 귀속 가능** (R5 — 역추론) |
| **어디에도 쓰인 적이 없다** | **1,590** | 참조 0. 숨겨도 업무에 영향이 없다 |
| 여러 테넌트에서 쓰였다 | **0** | **공용 마스터가 아니다** — Terminal 은 실제로 테넌트별로 쓰인다 |

> 모호한 건이 **0건**이다. 그래서 이 3,399는 "판단이 어려운 덩어리"가 아니라
> **1,809(귀속) + 1,590(미사용)** 으로 깨끗하게 갈린다. 재현 SQL 은 §7.

### 3-2. 애초에 테넌트 데이터가 아니다 (공용 마스터) — 약 2,000행

`user.Timezone` 598 · `user.Country` 238 · `user.CurrencyFormat` 31 ·
`advanced_table.GridSetting` 763 · `GridSettingUser` 896 · `menu.UserMenu` 60 ·
`menu.Tab` 27 · `devices.FrameType` 24 · `Protocol` 17 · `FrameClass` 14 ·
`orders.OrderItemType` 15 · `delivery.DeliveryStatus` 14 · `configuration.AdminConfig` 11 …

> 이들은 `created_by`/`group` 열을 **베이스 모델에서 물려받았을 뿐**이고, 내용은 전 테넌트 공용이다.
> 여기에 소유자를 채우면 다른 테넌트의 화면에서 국가·시간대·상태값이 사라진다.
> **필요한 것은 백필이 아니라 "공용 마스터" 표기**다 (D-209 ② 의 `is_system` 이 정확히 이것).

### 3-3. 사용자·권한 테이블 — 별도로 봐야 한다

`user.CoreUser` 95 · `menu.RoleMenu`/`RoleTab`(일부) · `file_management.UserMediaFile` 224.
`CoreUser` 의 소유 테넌트는 `UserProfileLink.group` 이 이미 말하고 있다 —
`created_by` 를 채우는 것과 별개 문제다. W0-16 의 역할 분리와 함께 본다.

## 4. 제외 — 채우면 기능이 깨진다

`operation_settings` 계열은 `created_by IS NULL` 을 **"시스템 기본 설정"의 뜻으로 이미 쓴다**
(`operation_settings_service.py:32` · `tasks.py:27,100` — impact.md §3 실측).
여기에 소유자를 채우면 기본 설정 조회가 깨진다. 스크립트가 `SYSTEM_OWNED_APPS` 로 제외한다.

## 5. 셀 수 없었던 4건 — 저장소 모델과 운영 스키마가 어긋난다 (P-LOCAL-4 의 실례)

```
logger.AuditLogs                        column logger_auditlogs.deleted does not exist
stream_monitors.StreamMonitorAIModel    column …streammonitoraimodel.deleted does not exist
stream_monitors.DrawingSession          column …drawingsession.deleted does not exist
stream_monitors.DetectionEvent          relation "stream_monitors_detectionevent" does not exist
```

앞 셋은 `stream_monitors.0015`(저장소에 있으나 **운영 스키마에 미적용**) 가 추가하는 열이다.
넷째는 W2-1 의 마이그레이션이 아직 없다. **백필 적용 전에 스키마를 먼저 맞춰야 한다.**

## 6. 적용 계획 (승인 후에 만든다 — 지금은 만들지 않았다)

```
0단계  백업 — pg_dump. 저장소 밖(D-002). 복원 절차를 먼저 시연한다
1단계  공용 마스터 표기 (§3-2) — 백필이 아니라 "테넌트 없음이 정상"을 선언. 코드/설정 판단 필요
2단계  R2 (343행) — created_by 의 group 으로 채운다. 가장 안전
3단계  Terminal — 역추론으로 1,809행 귀속(단일 소유 확정) · 미사용 1,590행은 그대로 둔다.
       대표 판정(P-W0-13-1) 후에만 실행
4단계  R3 (23,273행) — **부모부터 위에서 아래로.** 3단계가 끝나야 Terminal 하위가 풀린다
5단계  재측정 — 이 스크립트를 다시 돌려 group NULL 이 줄었음을 숫자로 확인
6단계  그 다음에야 W0-14c(652 확대) · 운영 플래그 전환 (D-252 단서)
```

각 단계는 **되돌릴 수 있게** 한다: 변경 전 `(pk, created_by_id, group_id)` 를 별 테이블에 적재하고,
되돌리기 스크립트를 같은 커밋에 넣는다. 그것 없이는 4단계를 실행하지 않는다.

## 7. 재현

```bash
docker exec -i -w /app gx-shell python - < scripts/backfill_owner_dryrun.py          # 표
docker exec -i -w /app gx-shell python - < scripts/backfill_owner_dryrun.py --json   # 기계 판독
```
**읽기 전용이다.** `--apply` 같은 인자는 이 스크립트에 없다.

Terminal 역추론(§3-1)은 SQL 한 번이다:

```sql
WITH orphan AS (SELECT id FROM terminals_terminal WHERE deleted IS NULL AND group_id IS NULL),
usage AS (
  SELECT rt.terminal_id AS tid, r.group_id FROM terminals_routeterminal rt
    JOIN terminals_routes r ON r.id=rt.route_id WHERE r.group_id IS NOT NULL
  UNION ALL SELECT r.terminal_from_id, r.group_id FROM terminals_routes r WHERE r.group_id IS NOT NULL
  UNION ALL SELECT o.pickup_location_id, o.group_id FROM orders_order o WHERE o.group_id IS NOT NULL
  UNION ALL SELECT o.delivery_terminal_id, o.group_id FROM orders_order o WHERE o.group_id IS NOT NULL
  UNION ALL SELECT d.terminal_id, d.group_id FROM devices_device d WHERE d.group_id IS NOT NULL
  UNION ALL SELECT w.terminal_id, w.group_id FROM surveillance_missionwaypoint w WHERE w.group_id IS NOT NULL
  UNION ALL SELECT f.start_point_id, f.group_id FROM flight_log_flightlog f WHERE f.group_id IS NOT NULL
  UNION ALL SELECT f.end_point_id, f.group_id FROM flight_log_flightlog f WHERE f.group_id IS NOT NULL)
SELECT count(DISTINCT u.group_id) AS tenants, count(*) FROM orphan o
  LEFT JOIN usage u ON u.tid=o.id GROUP BY o.id;   -- 집계는 바깥에서 한 번 더 묶는다
```
