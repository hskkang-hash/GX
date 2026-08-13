# W0-2 증거 — 멀티테넌트 권한 우회 제거

생성: 2026-08-13 · status: verify-pending (성능 측정만 대기)

## 한 일

### 1) 업무 데이터 모델 7종 제거 — 완료

`backend/common/base_model.py` `CustomManagerGroup.get_queryset()`

제거: `order, orderitem, orderhistory, payment, ordercomment, orderassignment, terminal`
남김: `coreuser, usergroup, role, userprofilelink, multilanguagecontent, userprofile, group`

```
./docs/agent/verify_gates.sh --gate bypass
  PASS  업무 데이터 모델 우회 0건
  SKIP  프레임워크 모델 잔존 (뷰 레벨 필터로 대응)
```

재발 방지: `tests/test_tenant_isolation.py::test_bypass_list_does_not_grow` 가
업무 모델의 재등록을 실패시킨다.

### 2) 프레임워크 모델 — 뷰 레벨 필터 헬퍼 신설

`backend/common/tenant_filters.py`

| 함수 | 용도 |
|---|---|
| `filter_users_by_group(qs, user)` | CoreUser 목록을 요청자 group 으로 좁힘 |
| `filter_by_group_field(qs, user)` | group FK 를 직접 가진 모델용 |
| `get_scoped_or_404(model, pk, user)` | 단건 조회 IDOR 차단. 없으면 404(존재 여부도 안 흘림) |

group 이 없으면 `.none()` 을 준다 — 여는 쪽이 아니라 닫는 쪽이 기본값이다.

## ⚠ 이 티켓의 전제가 부분적으로 틀렸다 (W0-3 에서 실측)

`BaseModelWithGroup` 이 두 개다.

| 구현 | 사용 |
|---|---|
| `core.base.BaseModelWithGroup` (dj-core, §0.4 금지구역) | orders · terminals · stream_monitors · surveillance · checklist_setting · delivery · partner · drone_communication (8개 앱) |
| `common.base_model.BaseModelWithGroup` (이 저장소) | `dashboard.Dashboard`, `dashboard.DashboardPanel` **2개뿐** |

`devices/models.py`, `operation_settings/models.py` 는 common 쪽을 import 만 하고
상속하는 클래스가 없다(죽은 import).

즉 **이번에 고친 목록은 Dashboard/DashboardPanel 에만 적용된다.**
목록이 나열했던 `order`·`terminal`·`coreuser` 는 전부 dj-core 쪽 매니저를 쓰므로
이 파일을 고쳐도 그 모델들의 필터링은 바뀌지 않는다.

이번 변경이 무의미하다는 뜻은 아니다 —
- 목록 자체가 잘못된 선례였고, 지웠으니 복제 확산이 멈춘다
- `test_bypass_list_does_not_grow` 로 재발이 막힌다
- 그러나 **실제 SaaS 격리 위험은 해소되지 않았다.** dj-core 쪽에 같은 목록이
  있다면 그것이 진짜 차단선이며, 그 파일은 §0.4 금지구역이다.

### 사람이 결정할 것

dj-core 의 `BaseModelWithGroup` / 매니저를 확인해야 한다. 선택지:

- **A안**: 사내망에서 dj-core 소스를 받아 동일한 우회 목록이 있는지 확인하고,
  있으면 dj-core 에 별도 PR 을 낸다. §0.4 예외 승인 필요.
- **B안**: 앱 쪽 모델을 `common.base_model.BaseModelWithGroup` 으로 옮긴다.
  8개 앱이 영향받는다 — R1 범위에서 회귀 위험이 크다.
- **C안**: 뷰·서비스 레벨 필터(`tenant_filters.py`)를 전 엔드포인트에 강제해
  매니저 계층을 신뢰하지 않는다. 작업량은 크지만 금지구역을 안 건드린다.

권장: **A안 확인 → 결과에 따라 C안 병행.** B안은 R1 에서 하지 않는다.

## 덤으로 발견한 교차 테넌트 버그 2건 (이 티켓 범위 밖)

```
handover/services/handover_document_service.py:608   group = UserGroup.objects.first()
handover/services/handover_notice_service.py:96      group = UserGroup.objects.first()
```

group 을 임의로(첫 번째로) 고른다. 테넌트가 둘 이상이면 남의 group 이 붙는다.
별도 티켓 필요.

또한 `CoreUser.objects.get(id=user_id)` 형태로 호출자가 준 id 를 그대로 믿는 곳이
저장소 안에 30곳 있다. `get_scoped_or_404` 로 치환해야 하나 W0-2 범위를 넘는다.

## verify-pending — 사내망에서 실행할 것

RESUME_NEXT §3 이 요구한 제거 전후 쿼리 수·응답시간 측정.

```bash
docker compose up -d backend redis
# 제거 전 기준선: git stash 후 측정, 또는 baseline 커밋 4afca2b 체크아웃
docker compose exec -T backend python manage.py test tests.test_tenant_isolation -v 2
docker compose exec -T backend python -c "
from django.test.utils import CaptureQueriesContext
from django.db import connection
# 대상: /api/orders/ 목록, /api/terminals/ 목록
"
```

측정 양식:
```
제거 전 : 쿼리 N회 / p95 XXXms
제거 후 : 쿼리 N회 / p95 XXXms
```

측정 불가 사유: dj-core 미설치로 Django 앱 로드 자체가 안 된다 (D-007).
