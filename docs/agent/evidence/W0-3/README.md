# W0-3 증거 — 테넌트 격리 회귀 테스트

생성: 2026-08-13 · status: verify-pending (D-202)

## 작성물

- `backend/tests/test_tenant_isolation.py` — 9모델 등록, 5시나리오, skip/xfail 0건
- `backend/tests/__init__.py`
- `.github/PULL_REQUEST_TEMPLATE.md` — 격리 테스트 등록 체크박스 포함

## 정적 검증 (오프라인에서 가능한 것)

```
python -m py_compile backend/tests/test_tenant_isolation.py   → OK
./docs/agent/verify_gates.sh --gate isolation
  PASS  필수 9모델 전부 등록
  PASS  5시나리오 전부 존재
```

## 사내망에서 실행할 명령 (verify-pending 해소)

```bash
docker compose up -d backend redis
docker compose exec -T backend python manage.py test tests.test_tenant_isolation -v 2
```

실행 불가 사유: `core.base` / `core.user.models` 가 dj-core 사내 패키지에 있고
`git+ssh://git@192.168.0.22` 에서만 받을 수 있다. 저장소의 `core/` 에는
`advanced_table`, `data` 만 있다. 코드 문제가 아니라 망 접근 문제다 (D-007).

## 실행 시 예상 결과 — 전부 green 이 **아니다**

이 테스트는 통과를 전제로 쓰지 않았다. 아래를 실증하도록 썼다.

| 테스트 | 예상 | 의미 |
|---|---|---|
| `test_registry_covers_all_isolatable_models` | PASS | 레지스트리가 코드베이스를 덮는다 |
| `test_unisolated_set_has_not_grown` | PASS | 격리 없는 모델이 4종에서 늘지 않았다 |
| `test_bypass_list_does_not_grow` | **FAIL** | W0-2 미완 — 업무 모델 7종이 우회 목록에 남아 있다 |
| `test_list_excludes_other_tenant` | 일부 FAIL 가능 | 아래 참조 |
| `test_null_created_by_is_not_globally_visible` | **FAIL 예상** | 아래 참조 |
| `test_*_api` (5종) | 경로 확인 필요 | `Target.api_base` 는 config/urls.py 의 앱 접두사에서 유도했다. ninja_extra 컨트롤러의 실제 하위 경로는 컨테이너에서 확인해야 한다 |

## 이 테스트가 드러내는 구조적 문제 2건

### 1. BaseModelWithGroup 이 두 개다

| | 사용 앱 |
|---|---|
| `core.base.BaseModelWithGroup` (dj-core, §0.4 금지구역) | orders, terminals, stream_monitors, surveillance, checklist_setting, delivery, partner, drone_communication — 8개 |
| `common.base_model.BaseModelWithGroup` (이 저장소) | `dashboard.Dashboard`, `dashboard.DashboardPanel` — 2개뿐 |

`devices/models.py`, `operation_settings/models.py` 는 common 쪽을 import 만 하고
실제로 상속하는 클래스가 없다 (죽은 import).

W0-2 가 지목한 `performance_bypass_models` 는 common 쪽 파일 안에 있는데,
그 목록이 나열한 `order`·`terminal`·`coreuser` 등은 전부 dj-core 쪽을 쓴다.
→ **common 쪽 목록을 고쳐도 그 모델들의 필터링은 바뀌지 않는다.**
자세한 내용과 선택지는 tickets.yaml W0-2 blocker 참조.

### 2. 지시서의 9모델 중 4종은 격리 메커니즘 자체가 없다

`groups` M2M 이 없으므로 group 필터링 대상이 아니다.

```
orders.Order                    core.base.BaseModel
devices.Device                  core.base.BaseModel
report_template.ReportTemplate  core.base.BaseModel
handover.HandoverDocument       core.base.BaseModel
```

또한 지시서가 지정한 `Handover` 라는 이름의 모델은 존재하지 않는다.
handover 앱의 실제 모델은 HandoverShift / HandoverDocument / HandoverContent /
HandoverNotice / HandoverNoticeComment 다. 최상위인 HandoverDocument 로 등록했다.

### 3. created_by 가 NULL 인 레코드는 전 테넌트에 보인다

`CustomManagerGroup.get_queryset()` 의 필터가 `Q(created_by__isnull=True)` 를
OR 로 포함한다. 데이터 마이그레이션·관리 커맨드로 만든 레코드가 여기 해당하며
group 과 무관하게 모든 테넌트에 노출된다. `test_null_created_by_is_not_globally_visible`
가 이것을 잡는다. 수정하려면 dj-core 쪽 동작도 함께 봐야 한다.
