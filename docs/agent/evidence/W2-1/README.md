# W2-1 증거 — DetectionEvent 모델

생성: 2026-08-13 · status: verify-pending (마이그레이션 적용만 대기)

## 한 일

- `backend/stream_monitors/models.py` 에 `DetectionEvent(BaseModelWithGroup)` 추가
  신규 앱을 만들지 않았다 (부록 A).
- `backend/tests/test_tenant_isolation.py` MODELS 레지스트리에 **같은 커밋으로** 등록
  (W0-3 에서 예약해 둔 주석 자리를 해제 — D-108)

## 계약 준수

`docs/contracts/detection-event.md` 와 필드 대조: **19/19 일치** (모델에만/계약에만 = 없음)

열거값도 계약대로다.
```
event_type : person vehicle fire smoke intrusion sos
severity   : info warning critical      # critical 만 빨강 (ISA-101)
status     : new confirmed rejected closed
```

## 인덱스 설계 (계약에 없던 부분 — 성능)

```
(stream_monitor, -occurred_at)              이벤트 센터 타임라인
(status, severity, -occurred_at)            미처리·위험 우선 표출
(stream_monitor, event_type, -occurred_at)  W2-2 중복 억제 조회
(mission, -occurred_at)                     W1-1 임무 리포트 집계
```

중복 억제(W2-2)는 "같은 stream+type 의 최근 이벤트"를 매 검출마다 조회한다.
인덱스 없이는 이벤트가 쌓일수록 검출 경로가 느려진다 — 그때 권한 필터를
우회하고 싶어지는 지점이다(D-103 이 금지). 미리 인덱스를 넣었다.

## verify-pending — 사내망에서 실행할 것

```bash
docker compose up -d backend
docker compose exec -T backend python manage.py makemigrations stream_monitors
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend python manage.py test tests.test_tenant_isolation -v 2
```

마이그레이션 생성 불가 사유: `core.base` 가 dj-core 사내 패키지에 있어
Django 앱 로드 자체가 안 된다 (D-007). 코드 문제가 아니다.

정적 검증은 통과했다.
```
python -m py_compile backend/stream_monitors/models.py   → OK
./docs/agent/verify_gates.sh --gate isolation            → PASS (10모델 등록)
```

## 남은 작업 (W2-1 범위 밖)

- W2-2 이벤트 수집: `grpc_dual_stream_service.py` 검출 수신 지점에서 생성 + 중복 억제
- W2-3 이벤트 센터 화면: AntD Table + virtual + expandedRowRender
- `reviewed_by` 는 `settings.AUTH_USER_MODEL` 로 참조했다. 계약 문서는 `CoreUser` 라고
  적었으나 같은 대상이며, 문자열 참조가 dj-core 버전 변화에 더 강하다.
