# UX-23 카메라 격자 — 증거 (차선 C2 · 2026-09-05 턴 D)

## 무엇을 만들었나

| 자리 | 파일 | 무엇 |
|---|---|---|
| 화면 | `frontend/src/features/dsm/pages/CameraGrid.tsx` | 자리표(빈 화면)를 채웠다. 타일 격자 · 자동 순회 · 「응답 없음」 표시 |
| 화면 훅 | `frontend/src/features/dsm/hooks/useCameraGrid.ts` | 값 부르기 + 순회 시계 (**새 파일**) |
| 화면 상수 | `frontend/src/features/dsm/api.ts` | `cameraPulse` 한 줄을 **끝에 더했다** (기존 줄은 안 건드렸다) |
| 서버 문 | `backend/apps/dsm/api.py` | `GET /api/dsm/cameras/pulse` (**새 라우트 1건**) |
| 서버 조립 | `backend/apps/dsm/services.py` | `camera_pulse()` — 판정을 안 하고 **옮기기만** 한다 |
| L3 판정 | `backend/stream_monitors/services/camera_pulse.py` | `pulse_rows()` · `CameraPulseRow` 를 **더했다** (⚠ 아래 「경계를 넘은 자리」) |
| 시험 | `backend/tests/test_c2_camera_grid.py` | 문지기 · 격리 · 조용함≠죽음 · 부작위 · 판정 한 벌 |
| 진입면 대장 | `backend/tests/test_f05_event_api.py` | `EVENT_ENTRY_SURFACE` 에 새 문 한 줄 등재 (그 파일의 규약) |

## 새 문의 응답 모양 — **C1 이 읽는다**

`GET /api/dsm/cameras/pulse` · 인증 필수(`JwtOrInboundKey` · 들어오는 키는 기본 거절) ·
`@tenant_scoped` · **읽기 전용**(이벤트를 만들지 않는다 · `create_events=False`).

현장 자료로 실제로 찍은 것 [실측 2026-09-05 · gx-shell · 사용자 `operator_user_4` ·
`cameras` 는 앞 3건만 잘랐다]:

```json
{
  "now": "2026-09-05 06:44:39.861992+00:00",
  "rules": {
    "pulse_timeout_seconds": 300,
    "cluster_window_seconds": 300,
    "cluster_min_cameras": 3,
    "cluster_min_down": 2
  },
  "counts": { "alive": 0, "total": 3, "never_seen": 3 },
  "cameras": [
    { "id": 14, "name": "GD-150Q", "alive": false, "last_seen_at": null, "silent_seconds": null },
    { "id": 15, "name": "H40",     "alive": false, "last_seen_at": null, "silent_seconds": null },
    { "id": 17, "name": "NBP-DR-P2","alive": false, "last_seen_at": null, "silent_seconds": null }
  ],
  "cluster": { "zones_seen": 0, "cameras_seen": 0, "outage_count": 0, "zones": [] }
}
```

`cluster.zones` 한 줄의 모양(위 자료에는 구역이 0개라 안 나왔다. 시험이 이 모양을 잰다):

```json
{
  "zone_id": 5, "zone_name": "하천변",
  "judged": true, "total": 3, "never_seen": 0,
  "silent_camera_ids": [11, 12], "cluster_camera_ids": [11, 12], "fires": true
}
```

### 읽는 쪽이 알아야 할 규약 넷

1. **세 사실이 세 값이다.** 「살아 있음」 · 「응답 없음」 · 「한 번도 안 옴」을 접지 않는다.

   | 사실 | `alive` | `last_seen_at` | `silent_seconds` |
   |---|---|---|---|
   | 살아 있음(사건이 없어도 프레임은 온다) | `true` | 시각 | 초 |
   | 응답 없음(프레임이 문턱을 넘게 끊겼다) | `false` | 시각 | 초 |
   | 한 번도 안 옴 | `false` | `null` | `null` |

   `silent_seconds` 의 `null` 은 **0이 아니다.** 0으로 읽으면 방금 등록한 카메라가
   방금 끊긴 카메라가 된다.

2. **문턱을 스스로 만들지 마라.** 「응답 없음」인지는 `alive` 가 답한다. `rules` 는
   **표시용**으로 주는 것이지 다시 판정하라고 주는 것이 아니다. 판정은
   `stream_monitors/services/camera_pulse.py` 한 곳이 한다.

3. **0건의 뜻이 둘이다.** `outage_count == 0` 일 때 `zones_seen == 0` 이면 「구역을
   하나도 안 봤다」이고, `zones_seen > 0` 이면 「봤는데 안 걸렸다」이다. 구역 한 줄의
   `judged` 가 그 구역을 실제로 판정했는지 말한다(카메라 3대 미만이면 `false`).

4. **사유 문장은 안 나간다** (P-27). `ClusterVerdict.reason` 은 우리 말이라 응답에
   싣지 않았다. 사유가 하던 일(「안 봤다」와 「안 걸렸다」 가르기)은 `judged`/`fires`
   두 값이 한다. 사람이 읽을 문장이 필요하면 **사전**에서 가져다 쓰라.

## 실행한 명령과 출력 원문

시험 (조율자가 정정한 명령 그대로):

```
docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings DB_TEST_NAME=test_gx_c2 python -m pytest tests/test_c2_camera_grid.py tests/test_c2_realtime_ping.py -q --nomigrations -p no:randomly --tb=short 2>/dev/null'
→ 24 passed, 1 skipped, 35 warnings in 22.94s
```

이웃 시험 회귀 (새 문·새 함수가 남의 초록을 깨지 않는가):

```
... -m pytest tests/test_c2_camera_grid.py tests/test_c2_realtime_ping.py tests/test_dsm_app.py tests/test_q_camera_pulse.py -q --nomigrations -p no:randomly
→ 76 passed, 1 skipped, 34 warnings in 23.27s

... -m pytest tests/test_k2_notify_kernel.py tests/test_k6_feedback_kernel.py tests/test_snapshot_route.py tests/test_clip_playback.py tests/test_c_w1_presets.py tests/test_zone_judgment.py tests/test_tenant_isolation.py -q --nomigrations -p no:randomly
→ 142 passed, 34 warnings in 51.00s
```

게이트:

```
python scripts/verify_layers.py             → 통과 — 계층 위반 0건 (대상 57개 파일)
python scripts/verify_post_arg_style.py     → 통과 — 라우트 39건 중 POST 12건 · 어긋난 자리 0건
python scripts/verify_route_scope_declared.py → 통과 — 선언 없이 태어난 새 라우트 0건
python scripts/verify_ui_copy.py            → 통과 — 잔여 0건 · 새로 생긴 대장 언어 0건 (35개 화면 파일)
python scripts/verify_lane_isolation.py     → 통과

docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings python /repo/scripts/verify_camera_pulse.py'
→ 통과 — 3중 2는 1건이고 1대는 0건이다
  (OPS-15 판정이 내 추가로 안 바뀐다는 확인. 이 게이트는 호스트에서 「판정 불가」다 —
   `ModuleNotFoundError: No module named 'config'` · 컨테이너 안에서 돌려야 한다)
```

화면 타입 검사 (호스트에 `node_modules` 가 없어 `gx-fe-build` 안에서 쟀다. 잰 뒤
그 컨테이너의 스냅샷은 원래대로 되돌렸다 — 다른 차선의 빌드를 건드리지 않는다):

```
docker exec gx-fe-build sh -c 'cd /app && node --max-old-space-size=4096 node_modules/typescript/bin/tsc --noEmit -p tsconfig.app.json'
→ features/dsm 아래 오류 0줄 (저장소 전체의 기존 오류는 3229줄 · 그중 우리 것 0)
```

## 못 잰 것 — **판정 불가**

1. **브라우저에서 이 화면이 어떻게 보이는지 안 쟀다.** 이 턴에 화면 동시접속은 1개이고
   브라우저는 조율자의 것이다. 화면 코드는 타입 검사와 문구 판정기까지만 지났다.
2. **영상 바이트가 이 화면에 없다.** 우리 카메라의 원본은 `rtsp://…` 이고 브라우저가
   바로 못 연다. 인수 자산(`MultiStreamMonitor`)에는 HLS/WebRTC 로 여는 조각이 있지만
   그것이 우리 카메라에도 서는지는 **재지 못했다**(닿는 AI/스트림 주소가 이 PC 에서
   `*.invalid` 다). 없는 것을 있는 척 그리지 않았다 — 타일은 카메라의 **상태**만 말한다.
3. **현장 자료로는 「살아 있는 카메라」를 한 대도 못 봤다** [실측]: 그 테넌트의 카메라
   3대가 **전부** `last_seen_at = null` 이고, 활성 카메라묶음 구역은 **0개**다. 이
   환경에서 `last_frame_at` 을 채우는 것이 아무것도 안 돌기 때문이다. OPS-15 게이트도
   같은 사실을 만나 합성 구역을 세워 잰다. 그래서 **정상 타일과 군집 두절 줄은 시험
   자료로만 봤다** — 현장 자료로는 못 봤다.

## 다음 사람이 브라우저에서 확인할 것 (3줄)

1. `/dsm/cameras/grid` 에 「카메라 격자」 제목과 타일들이 뜨고, 머리 한 줄이
   「응답 없음 N대 (전체 M대)」로 **분모와 함께** 나오는가.
2. 카메라가 13대 이상일 때(한 쪽 12타일) 「자동 순회」 단추가 **눌리고**, 누르면 글자가
   「순회 멈춤」으로 바뀌며 10초마다 쪽이 넘어가는가. 12대 이하면 그 단추는 **회색이고
   이유가 말풍선에 있다**(감춘 것이 아니다).
3. 응답 없는 타일에 「응답 없음」과 「마지막 응답 N분 전」이 함께 있고, **한 번도 응답이
   없던 카메라에는 그 「N분 전」 줄이 없는가**(대신 「응답을 받은 적이 없습니다.」).
   ※ 지금 현장 자료로는 3대 다 뒤엣것이다. 앞엣것을 보려면 `record_frame` 으로 맥박을
   심어야 한다.

## ⚠ 경계를 넘은 자리 — **조율자가 알아야 한다**

`backend/stream_monitors/services/camera_pulse.py` 에 `pulse_rows()` · `CameraPulseRow`
**두 이름을 더했다.** 이 파일은 이번 턴 내 소유 목록 밖이다. 왜 넘었나:

- `tests/test_dsm_app.py::AppStaysThinTest` 가 `apps/dsm/services.py` 안의
  `apps.get_model(` · `_base_manager` · `.objects.filter(` 를 **금지**한다. 즉 App 층은
  카메라 표를 직접 못 읽는다. 1차판이 그렇게 짰다가 그 시험이 즉시 빨개졌다.
- 소유 목록 안에는 카메라 전수를 낼 수 있는 L3 자리가 없다. 그리고 판정(`alive`)을 App
  으로 올리면 **문턱이 두 벌**이 된다 — 이 절이 막으려는 바로 그 상태다.
- 그래서 「카메라별 맥박 전수」를 맥박이 사는 그 파일에 뒀다. **추가만 했고 기존 줄은
  한 줄도 안 고쳤다.** `__all__` 에 두 이름을 더했고, OPS-15 게이트는 그대로 통과한다.

병합에서 이 파일을 다른 차선이 함께 고쳤다면 이 두 이름이 충돌 지점이다.
