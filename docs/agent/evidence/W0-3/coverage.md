# W0-3 격리 커버리지 대장 — 수집 모델 · EXEMPT 사유 · 예상 실패 등록부

**작성** 에이전트 · 2026-08-15 · WP-0 §11-2·3 (ENTRY 승인분)
**상태** 정적 실측 완료 / **실행 수치는 사내망 방문 후 §4 에 기입**
**근거 결정** D-105 · D-209 · D-210 · D-214

> 이 파일은 두 가지를 한다.
> ① 격리 대상 모델을 **전수 세고**(§1~2), ② 어느 테스트가 **실패할 것으로 등록되어 있는지**를 남긴다(§3).
> ②가 필요한 이유는 §3 첫 문단에 적었다 — **표기를 코드가 아니라 문서로 하는 이유**다.

---

## 0. 측정 방법 (DB·컨테이너 없이 재현 가능)

```bash
cd backend
# 격리 가능 모델 = groups M2M 을 갖는 베이스를 상속한 것
grep -rn "class .*(BaseModelWithGroup):"       --include=models.py .
grep -rn "class .*(MeasurableModelWithGroup):" --include=models.py .
# 등록된 대상
grep -n 'Target("' tests/test_tenant_isolation.py
```

`apps.get_models()` 는 Django 기동이 필요해 오프라인에서 돌지 않는다.
위 grep 은 **이 저장소 안의** 모델만 센다. dj-core·rj-core 패키지 안의 모델은
사내망에서 `npm/pip` 로 받은 뒤에야 보이며, **그래서 아래 수는 하한이다.**

---

## 1. 수집 결과 — 저장소 내 격리 가능 모델 **17종**

| # | 모델 | 베이스 | MODELS 등록 | 비고 |
|---|---|---|---|---|
| 1 | `checklist_setting.ChecklistSetting` | BaseModelWithGroup | ✅ | |
| 2 | `dashboard.Dashboard` | BaseModelWithGroup | ✅ | `common` 베이스 — 우회목록이 실제로 관여하는 2종 중 1 |
| 3 | `dashboard.DashboardPanel` | BaseModelWithGroup | ❌ | `common` 베이스 — 우회목록 관여 2종 중 2 |
| 4 | `orders.ExternalOrderStatus` | BaseModelWithGroup | ❌ | |
| 5 | `orders.OrderStatusMapping` | BaseModelWithGroup | ❌ | |
| 6 | `partner.Partner` | BaseModelWithGroup | ❌ | **W4(라이선스) 가 이 위에 얹힌다** |
| 7 | `stream_monitors.StreamMonitor` | BaseModelWithGroup | ✅ | |
| 8 | `stream_monitors.DetectionEvent` | BaseModelWithGroup | ✅ | W2-1 신설 |
| 9 | `surveillance.SurveillanceProfileChecklist` | BaseModelWithGroup | ❌ | |
| 10 | `surveillance.VideoAnalysis` | BaseModelWithGroup | ❌ | |
| 11 | `terminals.TerminalType` | BaseModelWithGroup | ❌ | |
| 12 | `terminals.Function` | BaseModelWithGroup | ❌ | |
| 13 | `terminals.TerminalPurpose` | BaseModelWithGroup | ❌ | |
| 14 | `flight_log.FlightLog` | MeasurableModelWithGroup | ❌ | **W1-1 임무리포트의 데이터 소스** |
| 15 | `surveillance.SurveyMission` | MeasurableModelWithGroup | ❌ | **W1-1·W2-1 이 참조하는 임무 본체** |
| 16 | `surveillance.SurveillanceProfile` | MeasurableModelWithGroup | ✅ | |
| 17 | `terminals.Terminal` | MeasurableModelWithGroup | ✅ | |

**등록 6 / 17 = 35.3 %.** 미등록 **11종**.

> 미등록 중 **`SurveyMission`·`FlightLog`·`Partner` 셋은 뒤 WP 가 그 위에 기능을 얹는다**
> (WP-4 임무리포트 · WP-6 라이선스). 격리가 확인되지 않은 모델 위에 화면을 얹으면
> 그 화면이 유출 경로가 된다. **W0-14 를 WP-1 에서 먼저 닫아야 하는 실질 이유가 이것이다.**

---

## 2. EXEMPT — 의도적 제외와 사유

| 대상 | 사유 | 해소 조건 |
|---|---|---|
| `user.*` · `core.*` 앱의 전 모델 | dj-core/rj-core 프레임워크. §0.4 금지구역이라 상속을 바꿀 수 없다 | 뷰 레벨 필터(`common/tenant_filters.py`)로 대체 통제. `exceptions.md` 참조 |
| `orders.Order` · `devices.Device` · `report_template.ReportTemplate` · `handover.HandoverDocument` | `core.base.BaseModel` 상속 — **`groups` M2M 자체가 없다.** 격리 메커니즘 부재 | `KNOWN_UNISOLATED` 4종으로 고정. 증가 금지 테스트가 지킨다 |
| grid 계열 12종 (`menu`,`tab`,`role`,`rolemenu`,`roletab`,`roleuser`,`gridsetting*`,`searchconditionsuser`,`usergridmanagement`) | 화면 설정·권한 마스터. 테넌트 데이터가 아니다 | 해당 없음 (설계상 전역) |

**EXEMPT 집합은 늘리지 않는다.** 늘려야 하면 사유를 여기 적고 `decisions_pending` 에 적재한다.

---

## 3. ★ 예상 실패 등록부 — **코드가 아니라 여기에 적는다**

ENTRY §11-2 는 예상 실패 3건을 `@expectedFailure` 로 **코드에** 등록하라고 했다.
**그렇게 하지 않았다.** 이유는 셋이고, 전부 정본에 있다.

1. `test_tenant_isolation.py` 파일 머리말이 *"이 파일의 테스트를 skip·xfail·비활성화하지 말 것"* 이라고 적고 있다.
2. AGENT_LOOP 절대금지 #5 — 격리 테스트 **수정 금지**.
3. **D-209 가 "이 테스트는 실패하는 것이 정상이고, 실패가 산출물이다"라고 결정했다.**
   `@expectedFailure` 는 그 산출물을 스위트에서 **지운다.** 실패 건수가 0으로 보이는 순간
   금지 #5 가 막으려던 상태가 된다 — 테스트를 고쳐 통과시킨 것과 결과가 같다.

따라서 **표기는 문서로 한다.** 실패는 실패로 남고, 그것이 무엇을 뜻하는지는 이 표가 답한다.

| 테스트 | 오프라인 판정 | 근거 | 실패 시 처리 |
|---|---|---|---|
| `test_registry_covers_all_isolatable_models` | **실패 확정** | §1 — 미등록 11종을 정적으로 열거함 | **W0-14 (WP-1)**. 11종 등록으로 해소 |
| `test_null_created_by_is_not_globally_visible` | **판정 불가** | 대상이 `MODELS` 첫 격리가능 모델 = `terminals.Terminal` 로 해석되는데, 그 매니저는 dj-core 안이라 오프라인에서 읽을 수 없다. `common` 쪽 `CustomManagerGroup` 은 세 분기 전부 `Q(created_by__isnull=True)` 를 OR 한다(실측) | **W0-13 (WP-1)** · D-209 의 4단계 순서 준수 |
| `test_unisolated_set_has_not_grown` | **통과 예상** | `MODELS` 내 비격리 모델 = `Order`·`Device`·`ReportTemplate`·`HandoverDocument` **4종이 `KNOWN_UNISOLATED` 와 정확히 일치** | 실패하면 새 비격리 모델이 들어온 것 → 원인 조사 후 WP-1 |
| `test_bypass_list_does_not_grow` | **통과 예상** | `common/base_model.py` 잔여 목록 7종이 전부 프레임워크 모델. 업무 7종 교집합 = ∅ (실측) | 실패하면 W0-2 회귀 |
| `TenantIsolationAPITest` 5시나리오 | **판정 불가** | `Target.api_base` 경로가 실제 라우트와 맞는지 미확인. 404 면 테스트가 자진 `fail` 하도록 되어 있다 | 경로 문제는 **테스트가 아니라 `api_base` 를 실측 라우트로** 고친다 |

> **한 줄로.** 이 스위트가 사내망에서 처음 돌 때 **초록이 아닌 것이 정상이다.**
> WP-0 의 goal 은 "격리 완결"이 아니라 "verify-pending 종결"이고, 실패를 **분류해서**
> WP-1 입력으로 넘기면 WP-0 의 임무는 끝난다 (ENTRY §9).

---

## 4. 실행 수치 (사내망 방문 후 기입)

| 항목 | 값 | 출처 |
|---|---|---|
| 실행한 테스트 수 | _(미기입)_ | `manage.py test tests.test_tenant_isolation -v 2` |
| ok | _(미기입)_ | |
| fail | _(미기입)_ | |
| error | _(미기입)_ | |
| 런타임 수집 격리 모델 수 (dj-core 포함) | _(미기입)_ | `test_registry_covers_all_isolatable_models` 실패 메시지의 missing 목록 |
| §1 하한(17) 대비 증가분 | _(미기입)_ | 위에서 뺀 값 = **dj-core 안에 있던 격리 대상** |

마지막 칸이 이 방문의 진짜 산출물이다 — **저장소 밖에 격리 대상이 몇 개 더 있었는지**를
이 프로젝트가 처음으로 숫자로 알게 된다.

---

## 5. D-210 이행 점검 — 자동 수집으로 바꿨는가

D-210 은 *"손으로 적는 방식 자체를 폐기하고 `apps.get_models()` 자동 수집으로 바꾼다"* 고 결정했다.
구현은 **하이브리드**다 — `MODELS` 하드코딩 레지스트리 + 자동 스캔 테스트.

**의도는 충족된다.** ENTRY §3-3 이 세운 판정 기준은 *"자동 스캔이 실제로 미등록 모델을 잡는가"* 였고,
§1 이 **11종을 잡는 것을 정적으로 증명**했다. 누락은 구조적으로 불가능하다.
→ **현 구조 유지.** 수집 방식으로의 전환은 하지 않는다 (ENTRY §3-3 의 두 갈래 중 앞쪽).
