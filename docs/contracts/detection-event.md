# 계약 1 — DetectionEvent 스키마

**티켓**: W6-2 (계약 고정) · **구현**: W2-1 · **버전**: 1.1 · **고정일**: 2026-08-13 · **개정**: 2026-08-31 (D-293 · D-294)

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

    status         = CharField(max_length=16, default="new", db_index=True)   # 수명주기
    verdict        = CharField(max_length=16, null=True, db_index=True)       # 판정 (D-293)
    reviewed_by    = FK(CoreUser, null=True, on_delete=SET_NULL)
    reviewed_at    = DateTimeField(null=True)
    reject_reason  = CharField(max_length=255, null=True)

    mission        = FK("surveillance.SurveyMission", null=True, on_delete=SET_NULL)
```

### 열거값

| 필드 | 값 | 비고 |
|---|---|---|
| `event_type` | `person` `vehicle` `fire` `smoke` `intrusion` `sos` `flood` | 추가 시 이 문서와 W2-3 색 규칙을 함께 갱신. `flood` 는 **D-294 로 신설**(F-02 침수·수위) |
| `severity` | `info` `warning` `critical` | `critical` 만 빨강 (ISA-101). 다른 용도로 빨강 금지 |
| `status` | `new` `confirmed` `rejected` `closed` | 수명주기. 화면 정렬: `critical`+`new` 는 최상단 고정 |
| `verdict` | `null` `confirmed` `rejected` | **사람의 판정. 종료가 덮지 않는다** (D-293 신설). 오탐률의 분모·분자는 `status` 가 아니라 이 칸에서 나온다 |

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
6. **판정은 지워지지 않는다**(D-293). `close_event` 는 `status` 만 `closed` 로 옮기고
   `verdict` 를 건드리지 않는다. 종료 판정을 지우면 오탐률이 시간이 갈수록 **저절로
   좋아지고**, 그것은 개선이 아니라 나쁜 데이터가 사라진 것이다. 오탐률은 **발생 코호트
   기준**으로 센다 — 이번 달 발생분의 오탐률은 다음 달에도 같은 값이어야 한다.
   강제: `backend/tests/test_d293_cohort_regression.py`.
7. **오탐률·통계 집계는 `event_type` 별로 분리된다**(D-294). 한 타입의 판정이 다른 타입의
   분모에 들면 지표가 가리키는 대상과 실제 대상이 갈리고, 그 갈림은 숫자에 드러나지 않는다.
   강제: `backend/tests/test_d294_event_type_separation.py`.

## 하위 호환

- 필드 **추가**는 하위 호환이다. `null=True` 로 넣는다.
- 필드 **삭제·의미 변경**은 계약 변경이다. 이 문서의 버전을 올리고 W2·W3 를 함께 본다.
- 마이그레이션이 기존 컬럼을 삭제해야 하면 영향 행 수를 보고하고 멈춘다 (D-009).

## 개정 이력

| 버전 | 날짜 | 무엇이 · 왜 | 근거 |
|---|---|---|---|
| 1.0 | 2026-08-13 | 최초 고정 | W6-2 |
| 1.1 | 2026-08-31 | ① `event_type` 에 `flood` 추가 — F-02(침수·수위)는 계약 M 기능이고 전용 타입 부재는 설계 선택이 아니라 **누락**이었다. ② `verdict` 열 신설 — 종료가 판정을 덮어 오탐률이 **시간이 갈수록 저절로 좋아지던** 구조를 끊는다. 둘 다 **필드/열거 추가**이므로 하위 호환이다: 기존 열은 그대로이고 의미도 바뀌지 않았다 | D-294 · D-293 |

★ 1.1 이 **W2·W3·W1 에 미치는 영향** (위 경고문이 요구하는 평가):

- **W2 이벤트 센터** — 열거가 하나 늘었다. 타입별 필터·배지가 `flood` 를 모르면 목록에서
  라벨이 비어 보인다. 색 규칙은 `severity` 기준이므로 ISA-101 은 그대로다(빨강은 `critical` 전용).
- **W3 대시보드** — 같은 이유로 타입 범례에 한 칸이 는다. 위젯의 5상태 계약은 무관하다.
- **W1 리포트** — `verdict` 가 생겨 **종료된 이벤트도 판정을 말할 수 있다.** 보고서가 종료 후
  "이것은 오탐이었다"를 쓰지 못하던 것이 이번에 풀렸다. 기존 `status` 표기는 그대로 작동한다.
