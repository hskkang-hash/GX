# W0-12 ② 전역 `.objects.first()` 스캔 — 19건 성격 분류

**작성** 에이전트 · 2026-08-15 · WP-1 (ENTRY 승인분)
**티켓** W0-12 spec ③ — *"저장소 전체에서 동일 패턴을 훑는다: `\.objects\.first\(\)` 중 Group/Tenant 성격 모델에 걸린 것 전부"*

## 0. 측정 방법 (재현 가능)

```bash
cd backend
grep -REn '\.objects\.first\(\)' --include=*.py . | grep -v '/migrations/'
```

**결과 19건.** 마이그레이션 디렉터리는 제외했다 — 그곳의 `first()` 는 스키마 시점의
데이터 조작이고 요청 컨텍스트가 없어 테넌트 개념 자체가 없다.

> **분류 기준은 하나다: 이 호출이 고른 행이 "누구의 것"이 되는가.**
> 소유자가 정해지는 자리(쓰기)면 **결함**, 표본만 보는 자리(읽기)면 **위험**,
> 테넌트 개념이 없는 마스터 코드면 **무해**다.

---

## 1. 결함 — 소유자를 임의로 정한다 (**수정 완료 2건**)

| # | 위치 | 무엇을 골랐나 | 조치 |
|---|---|---|---|
| 1 | `handover/services/handover_document_service.py:608` | 인수인계 **문서의 소유 group** | ✅ `require_user_group(user)` 로 교체. group 없으면 `ValidationError` |
| 2 | `handover/services/handover_notice_service.py:96` | 인수인계 **공지의 소유 group** | ✅ 동일 |

**정본 지목 2건과 정확히 일치한다.** 저장소 전체에 소유자 결정용 임의 선택은 이 둘뿐이었다.

```bash
$ git grep -n 'UserGroup\.objects\.first()' -- backend/
(출력 없음)                      ← W0-12 verify #1 통과
```

---

## 2. ★ 위험 — 남의 테넌트 행이 표본으로 뽑힐 수 있다 (**수정하지 않음 · 판단 요청**)

| # | 위치 | 하는 일 | 왜 위험한가 |
|---|---|---|---|
| 3 | `print_format/models.py:98` | 출력 서식 **미리보기**용 표본 인스턴스를 `apps.get_model(self.model_name)` 로 동적 조회해 렌더 | **모델이 테넌트 소유일 수 있다.** 모델 메서드라 `request` 가 없어 `CustomManagerGroup` 의 group 필터가 걸리지 않는다. 미리보기 화면에 **남의 테넌트 레코드가 렌더될 수 있다** |

**고치지 않은 이유.** 고치려면 `request`(또는 actor)를 모델 메서드까지 내려야 하고, 그것은
`print_format` 의 호출 규약 변경이다. W0-12 의 spec ③ 은 *"발견분은 같은 방식으로 고치고"* 라고
했으나 **"같은 방식"(시그니처에 group 명시 주입)이 여기서는 모델 계층 구조 변경**이 된다.
절대금지 #3(티켓에 없는 리팩터링) 에 닿으므로 **적재하고 남긴다** → `P-W0-12-1`.

> 이것이 이 스캔의 실제 수확이다. 정본이 지목한 2건은 **오배정**(쓰는 쪽)이었고,
> 이 1건은 **오열람**(읽는 쪽)이다. 결이 다르고, 후자는 티켓이 예상하지 못했다.

---

## 3. 무해 — 테넌트 개념이 없는 마스터 코드 (3건)

| # | 위치 | 대상 모델 | 판정 근거 |
|---|---|---|---|
| 4 | `surveillance/services/surveillance_profile_service.py:3355` | `SurveillanceStatus` | 상태 코드 마스터. `filter(code="pending_approval")` 우선, 없을 때만 폴백 |
| 5 | `surveillance/services/surveillance_profile_service.py:3408` | `SurveillanceProfileRepeatType` | 반복 유형 마스터 |
| 6 | `surveillance/services/surveillance_profile_service.py:3416` | `SurveillanceProfileRepeatUntilType` | 반복 종료 유형 마스터 |

셋 다 `BaseModelWithGroup` 을 상속하지 않는 **전역 코드표**이며 `coverage.md` §2 의
grid/마스터 계열과 같은 성격이다. **소유자가 없는 데이터라 오배정이 성립하지 않는다.**

---

## 4. 무해 — 진단·최적화 도구의 표본 조회 (4건)

| # | 위치 | 판정 근거 |
|---|---|---|
| 7 | `common/selective_cache_optimization.py:1303` | 캐시 최적화 **자가진단** 경로. 결과를 사용자에게 돌려주지 않고 성능 측정에만 쓴다 |
| 8 | `common/universal_optimization.py:3506` | 동일 — `[SELECTIVE_TEST]` 경로 |
| 9 | `common/universal_optimization.py:3640` | 동일 — 인스턴스가 없으면 `MockInstance` 로 대체 |
| 10 | `common/universal_optimization.py:3713` | 동일 |

> ⚠ **무해 판정에 조건이 붙는다.** 넷 다 "결과가 응답으로 나가지 않는다"는 전제에서 무해다.
> `optimization/urls.py` 가 `api/optimization/` 으로 노출돼 있으므로, **이 진단 API 가
> 인증된 일반 사용자에게 열려 있으면 표본 값이 새어 나갈 수 있다.** 라우트 노출 여부는
> W0-14 의 466건 현황표에서 함께 판정한다 → `coverage.md` 의 `optimization` 행.

---

## 5. 무해 — 관리 커맨드·테스트·주석 (10건)

| # | 위치 | 판정 근거 |
|---|---|---|
| 11 | `operation_settings/management/commands/load_operation_settings_sample.py:54` | 샘플 적재 커맨드. 운영자가 콘솔에서 직접 실행 |
| 12 | `orders/management/commands/generate_delivery_process.py:66` | 배송 프로세스 생성 커맨드 (§0.4 금지구역 · 미수정) |
| 13 | `report_template/management/commands/test_report.py:15` | 리포트 렌더 시험 커맨드 |
| 14 | `report_template/management/commands/test_report.py:17` | 동일 |
| 15 | `stream_monitors/management/commands/create_test_session.py:40` | 시험 세션 생성 커맨드 |
| 16 | `stream_monitors/management/commands/create_test_session.py:58` | 동일 |
| 17 | `stream_monitors/management/commands/create_test_session.py:62` | 동일 |
| 18 | `stream_monitors/services/stream_monitor_services.py:278` | **주석 처리된 코드** |
| 19 | `stream_monitors/services/stream_monitor_services.py:279` | **주석 처리된 코드** |

관리 커맨드는 HTTP 요청 경로가 아니고 실행 주체가 운영자다. **테넌트 경계를 넘는 것이
사고가 아니라 의도인 자리**이므로 고치지 않는다.

> 다만 11~17 은 **운영 DB 에서 실행하면 임의 테넌트에 샘플 데이터를 만든다.**
> 커맨드 이름에 `sample` / `test` 가 붙어 있어 의도는 분명하나, 운영 환경 실행을 막는 장치는 없다.
> W0-14 범위 밖이고 R1 DoD 밖이라 **기록만 한다.**

---

## 6. 요약

| 갈래 | 건수 | 조치 |
|---|---|---|
| **결함**(소유자 오배정) | **2** | **수정 완료** |
| **위험**(표본 오열람) | **1** | 적재 → `P-W0-12-1` · W0-14 현황표와 함께 판정 |
| 무해(마스터 코드) | 3 | 없음 |
| 무해(진단 도구) | 4 | 조건부 — W0-14 노출 판정에 연동 |
| 무해(커맨드·주석) | 10 | 없음(기록만) |
| **합계** | **19** | |

**정본이 지목한 2건은 전수와 일치했고, 스캔은 정본이 몰랐던 1건(`print_format`)을 더 찾았다.**
spec ③ 을 넣은 판단이 옳았다는 것이 이 표의 결론이다.
