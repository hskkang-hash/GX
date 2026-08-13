# W6-2 증거 — 파이프라인 인터페이스 계약 고정

생성: 2026-08-13 · status: done · 오프라인 100% 수행

## 산출물 3종 (docs/contracts/)

| 파일 | 계약 | 검증 |
|---|---|---|
| `detection-event.md` | DetectionEvent 스키마 (W2-1 과 1:1) | 모델 필드 19/19 일치 |
| `stream-ws.asyncapi.yaml` | `{stream_id, ts, detections:[{type,bbox,conf,track_id}]}` | AsyncAPI 3.0.0, YAML 파싱 OK |
| `stream-control.openapi.yaml` | 스트림 시작/중지/상태/목록 | OpenAPI 3.0.3, YAML 파싱 OK |

## DoD 검증

```
① 3개 계약이 문서로 고정됨 — docs/contracts/ 3파일
② FE 코드에 gRPC 직접 호출 0건
   grep -rn 'grpc' frontend/src/ --include=*.ts --include=*.tsx  →  0건
③ 모델-계약 대조: DetectionEvent 필드 19개 전부 일치 (모델에만/계약에만 = 없음)
```

## 설계 판단 3가지

**1. bbox 는 정규화 좌표(0.0~1.0)로 고정했다.**
현재 구현은 `cv2.imencode` 후 픽셀 좌표를 다루지만, W6-1 의 DeepStream 전환에서
입력 해상도와 디코드 경로가 바뀐다. 픽셀 좌표를 계약에 넣으면 그때 FE 가 깨진다.

**2. WebSocket 은 좌표·메타만 보낸다. 렌더링된 프레임을 보내지 않는다.**
현재 구현(gRPC 왕복으로 렌더된 프레임 수신 → 재전송)은 계약 위반이 아니라
**계약 이전 단계**다. W6-1 이 이 계약대로 바꾸면 FE 는 그대로 둔다.

**3. `pipeline` 필드는 진단용이며 FE 가 분기하면 안 된다고 못박았다.**
분기하는 순간 "구현체 교체 가능"이라는 이 계약의 목적이 사라진다.

## 기존 구현과의 관계

기존 경로는 구현 상세이며 이 계약이 그 위의 안정 계층이다. R2 에서 제거될 수 있다.

```
POST /api/stream-monitors/start-ai-dual-stream   → /api/v1/streams/{id}/start
POST /api/stream-monitors/stop-ai-dual-stream    → /api/v1/streams/{id}/stop
ws  /ws/drawing/session/{id}                     (별개 채널 — 드로잉 협업, 계약 대상 아님)
```

기존 consumer 들이 최상위 `type` 으로 메시지를 분기하는 관례를 계약에도 반영했다.
