# UX-08 관제 화면 실시간 탐지 알림 — 증거 (차선 C2 · 2026-09-05 턴 D)

## 직전 턴이 남긴 미지와, 재고 나온 답

> 「잠자던 시그널은 `VideoAnalysis` 에 붙어 있고 화면은 `DetectionEvent` 를 읽는다 —
>  **꺼진 스위치가 그 전등의 스위치인지는 따로 확인해야 한다.**」 (턴 C 인계)

재 봤다. **그 스위치는 그 전등의 스위치가 아니었다.** 그리고 두드림은 이미 켜져 있었는데
**한 갈래에서만** 나가고 있었다.

```
grep -rn "ping_detection" backend/            [실측 2026-09-05]
  ./common/live_ping.py:52                                   def ping_detection(...)   (정의)
  ./stream_monitors/services/detection_event_bridge.py:327   from common.live_ping import ping_detection
  ./stream_monitors/services/detection_event_bridge.py:329   ping_detection(tenant_code=..., reason="detection")
  ./surveillance/signals.py:67                               from common.live_ping import PING_COALESCE_SECONDS  (상수만)
```

즉 **부르는 곳이 단 하나**였고 그것은 AI gRPC 파이프라인이다. `record_detection` 을 부르는
다른 경로로 태어난 이벤트는 화면을 **한 번도 두드리지 않았다**:

```
grep -rn "record_detection" backend/ (시험 제외 · 커널 자신 제외)
  stream_monitors/services/detection_event_bridge.py   ← 두드린다
  stream_monitors/services/camera_pulse.py:341         ← 안 두드렸다 (OPS-15 군집 두절)
  stream_monitors/management/commands/seed_dsm_events.py:264,306  ← 안 두드렸다 (검수 시드)
```

**군집 두절은 재난 징후인데 관제 화면이 조용했다.** 이 절의 실제 결함이 그것이다 —
「코드는 있고 꺼져 있다」가 아니라 **「켜져 있는데 다른 전등이다」**.

## 무엇을 고쳤나

`backend/surveillance/signals.py` 에 **수신기 하나**를 더했다:

```
@receiver(post_save, sender=DetectionEvent)
def detection_event_post_save(sender, instance, created, **kwargs)
```

- 두드림을 **행이 태어나는 사실**에 매단다. 갈래마다 손으로 부르면 갈래가 하나 늘 때마다
  조용히 빠지고, 그것이 지금까지의 상태였다.
- **새 탐지에만** 두드린다: `created=True` 이거나 `update_fields` 에 `last_seen_at` 이
  있을 때(= 접힌 관측 · 카드의 배지가 오른다). 판정(오탐)·대응 진행·종결 저장은
  두드리지 **않는다** — 안 바뀌는 목록을 밤새 다시 읽게 하지 않는다.
- **`transaction.on_commit` 뒤에** 두드린다. `record_detection` 은 `@transaction.atomic`
  이므로 시그널은 아직 커밋 안 된 트랜잭션 안에서 온다. 거기서 두드리면 화면이 목록을
  다시 읽는 순간 **그 행이 아직 없다.** 롤백된 이벤트로 두드리지 않는 것도 같은 한 줄이
  함께 지킨다.
- 실패를 위로 안 던진다(기록이 두드림 때문에 죽지 않는다). 조용히 삼키지도 않는다.
- **훈련 모드·중복 억제·알림 억제·소유 상속을 다시 하지 않는다.** 커널이 이미 했다.

여기서 **아무것도 켜지 않았다**: 받는 쪽(`consumers.py::detection_message`)은 턴 C 가
이미 세웠고, `apps.py::ready()` 의 import 도 서 있다. 이번에 더한 것은 **두드릴 자리**뿐이다.

## 어느 채널 레이어를 쟀나 — **두 사실을 따로 적는다**

조율자 지시대로 명시한다. **`InMemoryChannelLayer` 로 갈아 끼운 적이 없다.**

**(가) 운영 설정의 레이어가 실제로 도는가** — 시험 밖에서, 설정 그대로:

```
docker exec gx-shell sh -c 'cd /app && python probe_layer.py'   (임시 스크립트 · 잰 뒤 지웠다)
  layer = channels_redis.core.RedisChannelLayer
  received = {"type": "detection_message", "timestamp": "probe", "message": {"reason": "probe"}}
```
→ `settings.CHANNEL_LAYERS` 가 가리키는 **redis 레이어가 이 환경에서 실제로 돈다.**
   그룹으로 보낸 것이 그룹에 붙은 채널로 돌아왔다.

**(나) 시험 안에서 잰 것** — `tests/test_c2_realtime_ping.py` 는 `get_channel_layer()` 를
그대로 쓴다(위와 같은 RedisChannelLayer · 실행 로그에 그 객체가 찍힌다:
`<channels_redis.core.RedisChannelLayer object at 0x…>`). 방 이름도 시험이 따로 계산하지
않고 **보내는 쪽의 판단**(`live_ping._room_for(bridge._tenant_code_of(...))`)을 그대로 쓴다.

**시험이 손으로 민 것은 「커밋 한 걸음」뿐이다.** `TestCase` 는 커밋을 안 하므로
`captureOnCommitCallbacks(execute=True)` 로 커밋 콜백을 돌린다. **레이어는 진짜이고
커밋만 시험이 민다** — 이 둘을 섞어 적지 않는다.

**아직 못 잰 것**: 브라우저가 실제로 `wss://…/ws/surveillance/profiles/` 에 붙어 이 두드림을
받고 목록을 다시 읽는 것. WebSocket 을 태우는 것은 ASGI 경로이고(`gx-gunicorn-e`),
브라우저는 이 턴에 조율자의 것이다. **재지 않은 것을 초록으로 적지 않는다.**

## 실행한 명령과 출력 원문

### ① 고치기 **전**의 빨강 — 이것이 산출이다

수신기 데코레이터 한 줄을 임시로 주석 처리하고 잰 뒤 되돌렸다:

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings DB_TEST_NAME=test_gx_c2red python -m pytest tests/test_c2_realtime_ping.py -q --nomigrations -p no:randomly --tb=line 2>/dev/null'

FAILED tests/test_c2_realtime_ping.py::TheKnockGoesOutWhenTheRowIsBornTest::test_a_folded_observation_also_knocks
FAILED tests/test_c2_realtime_ping.py::TheKnockGoesOutWhenTheRowIsBornTest::test_recording_a_detection_knocks_the_room
FAILED tests/test_c2_realtime_ping.py::TheKnockDoesNotCareWhichPipelineTest::test_a_cluster_outage_event_also_knocks
FAILED tests/test_c2_realtime_ping.py::TheReceivingSideStandsFirstTest::test_the_signal_is_actually_connected
4 failed, 5 passed, 1 skipped, 5 warnings in 22.48s
```

★ 빨간 넷이 **전부 양성 쪽**이고, 부작위 넷(핸들러 실재 · 롤백 무두드림 · 상태 저장
무두드림 · 화면 낱말)은 **초록으로 남았다.** 「아무것도 안 하는 배선」이 부작위만으로는
통과한다는 것을 이 대조가 보여 준다.

### ② 고친 **뒤**의 초록

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings DB_TEST_NAME=test_gx_c2 python -m pytest tests/test_c2_camera_grid.py tests/test_c2_realtime_ping.py -q --nomigrations -p no:randomly --tb=short 2>/dev/null'
→ 24 passed, 1 skipped, 35 warnings in 22.94s
```

회귀(이벤트 경로를 지나는 이웃 시험):

```
... tests/test_dsm_app.py tests/test_q_camera_pulse.py …           → 76 passed, 1 skipped
... tests/test_k2_notify_kernel.py … tests/test_tenant_isolation.py → 142 passed
... tests/test_event_no_drop.py tests/test_k1_event_kernel.py …     → 초록 (기록 경로에 상한 없음 그대로)
```

## 시험이 무엇을 잠갔나

| 잠근 것 | 자리 |
|---|---|
| 받는 쪽이 먼저 선다 — 보내는 `type` 이 **전부** 핸들러를 갖는다 | `TheReceivingSideStandsFirstTest` |
| 화면이 기다리는 낱말과 서버가 보내는 낱말이 같다 (`detection_message`) | 같은 클래스 · **컨테이너에 `frontend/` 가 없어 SKIP** (아래) |
| 시그널이 실제로 붙어 있다 (「잠자는 기능」 방지) | `test_the_signal_is_actually_connected` |
| 행이 태어나면 **진짜 레이어의 그 방에** 두드림이 온다 | `test_recording_a_detection_knocks_the_room` |
| 접힌 관측도 두드린다 (배지가 오른다) | `test_a_folded_observation_also_knocks` |
| **갈래를 안 가린다** — 군집 두절도 두드린다 | `TheKnockDoesNotCareWhichPipelineTest` |
| 부작위 — 롤백된 이벤트는 두드리지 않는다 | `test_a_rolled_back_event_does_not_knock` |
| 부작위 — 새 탐지가 아닌 저장은 두드리지 않는다 | `OnlyANewDetectionKnocksTest` |
| 두드림에 **카드가 안 실린다** (목록이 두 벌이 되지 않는다) | `test_recording_a_detection_knocks_the_room` |

## 못 잰 것 — **판정 불가**

1. **브라우저 ↔ WebSocket 왕복.** 위 (나)에 적었다. 브라우저 금지 · 동시접속 1개.
2. **화면 낱말 대조가 시험 컨테이너에서 SKIP 된다.** `gx-shell` 의 `/repo` 에는
   `backend·docs·scripts` 뿐이고 `frontend/` 가 없다 [실측]. 그래서 그 한 건은
   **판정 불가**이고, 호스트에서 눈으로 대조했다:
   `frontend/src/features/dsm/hooks/useDetectionPing.ts` 는
   `if (payload.type === 'detection_message') cb.current();` 이고
   `backend/surveillance/consumers.py` 는 `"type": "detection_message"` 를 보낸다 — 같다.
   조율자의 통합 환경에 `frontend/` 가 함께 마운트되면 이 시험이 저절로 켜진다.
3. **두드림이 실제 부하에서 합쳐지는가**(3초 창)는 안 쟀다. 코드에는 있고
   (`live_ping.PING_COALESCE_SECONDS`) 폭주 상황을 만들지 않았다.

## 다음 사람이 브라우저에서 확인할 것 (3줄)

1. `/dsm/queue`(또는 `/dsm/events`)를 열어 둔 채 개발자 도구 Network → WS 에서
   `/ws/surveillance/profiles/` 가 **101 로 붙는지**. 안 붙으면 화면은 15초 주기 갱신으로
   계속 살아 있고, 그 사실 자체가 이 절의 다음 측정거리다.
2. 붙은 상태에서 다른 창으로 `python manage.py seed_dsm_events` 를 한 번 돌리고,
   **새로고침 없이** 목록이 늘어나는지. WS 프레임에 `{"type":"detection_message"}` 가
   보여야 한다(카드 내용은 안 실린다 — 신호만이다).
3. 카메라 맥박을 끊어 군집 두절을 낸 뒤에도 같은 두드림이 오는지. **이것이 이번에
   고친 갈래다** — 예전에는 여기서 화면이 조용했다.
