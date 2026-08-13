# 계약 1 — DetectionEvent 스키마

**티켓**: W6-2 (계약 고정) · **구현**: W2-1 · **버전**: 1.0 · **고정일**: 2026-08-13

> 이 스키마는 **AI 파이프라인 구현체와 무관하게 동일**하다.
> R2 의 W6-1 이 현재 gRPC 파이프라인을 DeepStream/Triton 으로 갈아끼워도
> 이 계약이 같으면 W2(이벤트 센터)·W3(대시보드)·W1(리포트)는 손대지 않는다.
> **이 계약을 바꾸려면 W2·W3·W1 의 영향을 먼저 평가한다.**

## 저장 모델

`backend/stream_monitors/models.py` — 신규 앱을 만들지 않는다.

```python
class DetectionEvent(BaseModelWithGroup):   # group 격리 필수
    stream_monitor = FK(StreamMonitor, on_delete=CASCADE, related_name="detection_events")
    ai_model       = FK(AIModel, null=True, on_delete=SET_NULL)

    event_type     = CharField(max_length=32, db_index=True)   # 아래 열거
    severity       = CharField(max_length=16, db_index=True)   # info | warning | critical
    occurred_at    = DateTimeField(db_index=True)
    last_seen_at   = DateTimeField(null=True)   # 중복 억제 시 갱신 (W2-2)

    lat            = FloatField(null=True)
    lng            = FloatField(null=True)
    alt            = FloatField(null=True)

    confidence     = FloatField(null=True)      # 0.0 ~ 1.0
    bbox           = JSONField(null=True)       # 아래 형식
    track_id       = CharField(max_length=64, null=True, db_index=True)

    snapshot_path  = CharField(max_length=512)  # MinIO object path
    clip_path      = CharField(max_length=512, null=True)

    status         = CharField(max_length=16, default="new", db_index=True)
    reviewed_by    = FK(CoreUser, null=True, on_delete=SET_NULL)
    reviewed_at    = DateTimeField(null=True)
    reject_reason  = CharField(max_length=255, null=True)

    mission        = FK("surveillance.SurveyMission", null=True, on_delete=SET_NULL)
```

### 열거값

| 필드 | 값 | 비고 |
|---|---|---|
| `event_type` | `person` `vehicle` `fire` `smoke` `intrusion` `sos` | 추가 시 이 문서와 W2-3 색 규칙을 함께 갱신 |
| `severity` | `info` `warning` `critical` | `critical` 만 빨강 (ISA-101). 다른 용도로 빨강 금지 |
| `status` | `new` `confirmed` `rejected` `closed` | 화면 정렬: `critical`+`new` 는 최상단 고정 |

### `bbox` 형식

정규화 좌표(0.0~1.0)를 쓴다. 해상도가 바뀌어도 값이 유효하다.

```json
{ "x": 0.42, "y": 0.31, "w": 0.08, "h": 0.15 }
```

원본 픽셀 좌표를 쓰지 않는다 — 파이프라인 교체 시 입력 해상도가 달라진다.

## 불변 규칙

1. **`BaseModelWithGroup` 상속 필수.** 신규 모델은 group 격리를 받아야 한다 (부록 A / D-108).
2. **`tests/test_tenant_isolation.py` 의 `MODELS` 레지스트리에 같은 커밋으로 등록한다.**
   자리는 이미 주석으로 예약되어 있다 — 주석만 풀면 된다.
3. **중복 억제**(W2-2): 동일 `stream_monitor` + `event_type` 이 N초(기본 10) 안에
   재발생하면 새 레코드를 만들지 않고 `last_seen_at` 만 갱신한다.
   알림 폭주는 Value 설계서가 지목한 페인포인트다.
4. **스냅샷은 MinIO 에 1장.** 원본 프레임을 DB 에 넣지 않는다.
5. 좌표는 `occurred_at` 시점의 기체 위치다. 보간하지 않는다.

## 하위 호환

- 필드 **추가**는 하위 호환이다. `null=True` 로 넣는다.
- 필드 **삭제·의미 변경**은 계약 변경이다. 이 문서의 버전을 올리고 W2·W3 를 함께 본다.
- 마이그레이션이 기존 컬럼을 삭제해야 하면 영향 행 수를 보고하고 멈춘다 (D-009).
