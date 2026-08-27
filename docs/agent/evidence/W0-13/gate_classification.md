# D-270 ③ 게이트 신설 — `verify_classification.py`

**작성** 2026-08-27 · **결정** D-270 ③ (세종 위임) · **티켓** W0-13 · W0-14 (WP-2)
**규약** 초효율 코드구현 규약 §2 (게이트 3종) · C-3.2 ③
**실행본** `python scripts/verify_classification.py` · 원자료 `verify_classification_run.txt`

---

## 0. 왜 이것이 코드 구현보다 먼저인가

오늘 두 번, **판정을 지킨 것은 게이트가 아니라 사람의 눈**이었다.

1. 적용본이 분류 등록부를 참조하지 않아 `advanced_table.GridSetting`(479행) · `menu.Tab` 을
   채우려 했다 — **시뮬레이션이 잡았다.**
2. 저널이 개행 없이 한 줄로 쓰이는 결함 — **적용 전 코드 검토가 잡았다.**

둘 다 "잡혔으니 다행"이 아니라 **"안 잡혔으면 그대로 나갔다"**는 뜻이다.
D-270 ③ 이 게이트를 요구한 것이 이 때문이고, 규약 §3 이 이것을 코드 구현보다 앞에 둔 것도
같은 이유다 — **게이트가 없으면 이후 작업이 또 샌다.**

---

## 1. 무엇을 막나

데이터를 쓰는 스크립트가 **분류 등록부**(`backend/tests/tenant_classification.py`)를
참조하지 않으면 실패한다. 참조하지 않는 쓰기는 **공용 마스터와 미배정을 구별하지 못하는 쓰기**다.

대상: `scripts/*.py` · `backend/*/management/commands/*.py` — **사람이 손으로 돌리는 일회성 쓰기**.
앱 코드(views/models)는 대상이 아니다. 그쪽은 테넌트 스코프 게이트(C-3.1)가 본다.

### 1-1. 이름으로 세지 않는다 (D-263)

`.update(` 라는 이름으로 세면 `dict.update()` 가 DB 쓰기로 잡힌다. 그러면 게이트가 시끄러워지고,
**시끄러운 게이트는 결국 꺼진다.** 그래서 AST 로 **수신자 사슬**을 뿌리까지 따라가
매니저·쿼리셋(`objects` · `_base_manager` · `filter` …)·커서에 닿는지 본다.

`cursor.execute()` 는 SQL 을 읽어 쓰기 동사(INSERT/UPDATE/DELETE/TRUNCATE/DROP/ALTER…)를 찾는다.
`sql = f"..."` 처럼 변수에 담은 것도 **대입을 따라가** 읽는다 — 그렇게 하지 않으면
백필 적용본 자신이 "판정 불가"로 떨어진다.

### 1-2. 모르는 것을 만나면 멈춘다 (D-264 계열)

| 상황 | 처분 |
|---|---|
| 파싱 실패 | **실패.** 못 읽는 파일은 "판정하지 않은 파일"이고 그것이 사각지대다 |
| `obj.save()` — 수신자가 모델인지 확정 불가 | **쓰기로 센다.** 모호할 때 안전한 쪽은 "아마 읽기겠지"가 아니다 |
| 읽기임을 사람이 아는 경우 | `WRITE_AUDIT` 에 `경로:줄번호` + **사유**로 등재. 사유 없으면 거부 |
| 등재한 줄이 밀리거나 사라짐 | **실패.** 낡은 면제가 남으면 다음 사람이 그것을 근거로 읽는다 |

현재 `WRITE_AUDIT` 은 2줄뿐이다 — `clear_cache.py` 의 `redis_client.delete()`
(Redis 키 삭제이지 DB 행이 아니다).

---

## 2. ★ 첫 실행이 드러낸 것 — 빚 113건

```
대상 83개 · 쓰기 36개 (등록부 참조 **1개**) · 남은 빚 35개 파일 113건
```

**데이터를 쓰는 36개 중 등록부를 참조하는 것은 백필 적용본 하나뿐이다.**
나머지는 공용 마스터인지 아닌지 **모르는 채로** 쓴다.

그중 실제로 사고를 낼 수 있는 것 — **공용 마스터를 통째로 지우는 관리 명령**:

| 파일 | 무엇을 하나 |
|---|---|
| `terminals/…/init_days_of_week.py` | `DayOfWeek.objects.all().delete()` |
| `orders/…/init_anyang_data.py` | `OrderItemType.objects.all().delete()` — **`OrderItemType` 은 SHARED_MASTERS 등재분이다** |
| `orders/…/init_status_mapping_data.py` · `_anyang.py` | `ExternalOrderStatus` · `OrderStatusMapping` 전량 삭제 |
| `operation_settings/…/init_operation_settings.py` | `OperationSettings._base_manager.all().delete()` |
| `operation_settings/…/load_operation_settings_sample.py` | `OperationSettings.objects.all().delete()` |
| `handover/…/init_shifts.py` | `HandoverShift.objects.all().delete()` |

> D-261 (c) 가 "채우면 다른 테넌트 화면에서 국가·시간대가 사라진다"고 막은 그 사고를,
> 이 명령들은 **채우는 것이 아니라 지우는 방향**으로 낼 수 있다. 같은 사고의 다른 얼굴이다.

---

## 3. 왜 전부 실패시키지 않았나 — 증가금지 래칫

갈래가 둘 있었고 **둘 다 틀렸다**:

- **(가) 전부 실패** → 오늘부터 모든 커밋이 막힌다 → 게이트가 꺼진다 → **장식이 된다**
- **(나) 조용히 통과** → 빚이 안 보인다 → **"봐서 괜찮았다"와 "안 봤다"가 구별되지 않는다**

그래서 `KNOWN_DEBT` **증가금지 래칫**을 썼다 —
`tenant_classification.UNASSIGNED_BASELINE` 과 같은 장치이고, 이 저장소가 이미 쓰는 관용구다.

| 상황 | 판정 |
|---|---|
| 래칫에 **없는** 파일이 참조 없이 쓴다 | **실패** — 새 빚은 오늘부터 못 진다 |
| 래칫에 있는 파일이 빚을 **늘린다** | **실패** — 래칫은 갚을 목록이지 늘릴 목록이 아니다 |
| 빚이 **줄었다** | 통과 + "래칫을 낮춰라" 출력 (줄어드는 것은 환영이다) |
| 빚을 다 갚았다 | 통과 + "KNOWN_DEBT 에서 지워라" 출력 |
| 래칫에 적힌 파일이 사라졌다 | **실패** — 지운 파일의 빚은 지운다 |

**래칫은 면제 목록이 아니라 갚을 목록이다.** 갚는 순서는 우리가 정할 것이 아니라서
**P-W0-13-5** 로 적재했다 (권고 A: 공용 마스터를 지우는 7개를 EXIT 전에 먼저).

---

## 4. 주입 시험 — 게이트가 실제로 멈추는가

D-264 가 `verify_kernel_map.py` 에 요구한 것과 같은 시험을 했다.
**게이트를 만들었다는 말은 증거가 아니다. 깨뜨려 봐야 증거다.**

| 주입 | 기대 | 결과 |
|---|---|---|
| 래칫에 없는 새 쓰기 스크립트(`Thing.objects.filter().update()`) | exit 1 | **exit 1** · "래칫에 없는 새 빚" 검출 |
| 래칫에 있는 파일에 `DELETE FROM devices_protocol` 추가 | exit 1 | **exit 1** · "빚 6 → 7 증가" 검출 |
| 둘 다 되돌림 | exit 0 | **exit 0** · 빚 113 == 래칫 상한 113 |

주입본은 전부 제거했다 (`git status` 깨끗).

---

## 5. 배선

`.pre-commit-config.yaml` 에 `gx-classification` 훅으로 등록했다.
발동 대상: `scripts/*.py` · `backend/*/management/commands/*.py` ·
`backend/tests/tenant_classification.py`(등록부 자체가 바뀔 때도 자기검사를 돌린다).

### 5-1. 등록부 자기검사도 함께 돈다

참조를 강제해도 **등록부가 엉망이면 소용없다.** 그래서 같은 게이트가 등록부 자체를 본다:

- `SHARED_MASTERS` · `TENANT_UNASSIGNED` · `DEFERRED` 전건에 **근거 한 줄**이 있는가
- 같은 모델이 두 곳에 선언되지 않았는가 (공용이면서 주인 없음일 수는 없다)
- `TENANT_UNASSIGNED` 전건에 **증가금지 래칫**(`UNASSIGNED_BASELINE`)이 있는가
- 라벨이 `app.Model` 꼴인가

---

## 6. 하지 않은 것 · 남은 것

| 항목 | 왜 |
|---|---|
| 빚 113건 상환 | 갚는 순서가 일정에 걸린다 — **P-W0-13-5** 판정 청구 (권고 A) |
| 저널 왕복 자가검사 | **P-W0-13-4** 판정 청구. 등록부 참조만으로는 오늘 두 사고 중 **한 건만** 막힌다 |
| `verify_timeout.py` 신설 | 규약 §2 의 셋째. `scan_request_timeouts.py` 가 **이미 AST 실측**으로 돌고 있어 신설이 아니라 **확장**이 맞는지 확인 후 진행 (원칙 1: 중복 0) |
| `verify_tenant_scope.py` 확장 | 규약 §2 의 둘째. 다음 단계 |
