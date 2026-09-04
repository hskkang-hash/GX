# 순회 1바퀴 (2026-09-04 15:47:19)

**이 파일은 `scripts/ops_patrol.py` 가 실행하며 적었다.**
종료 코드는 각 판정기가 실제로 낸 값이다 — 회색(2)은 초록이 아니다.

순회 시작 2026-09-04 15:46:50

- 환경: `.env` 에서 MinIO 자격증명을 넘겼다 (값은 적지 않는다)

### 감시 3종 (liveness·lag·fill)

- 도는 자리: `container` · 명령: `/repo/scripts/ops_monitor.py --check`
- 종료 코드 **1** → **빨강** · 3.9초

```
[OPS-MONITOR] [입력] 신호 11개 · 2026-09-04T06:46:53+00:00
  OK      db_ping_ms             7.93       한계 500 · 
  OK      cache_alive            True       왕복 5.1ms
  OK      object_store_alive     True       저장소가 답했다 · 버킷 guardianx-dev 있음
  ALARM   latest_event_age_min   1052.4     한계 60 · 
  OK      unsent_deliveries      0          한계 10 · 
  OK      db_size_gb             0.087      한계 50 · 
  OK      cameras                40         등록 카메라 수 — 늘고 줄어드는 것이 보인다
  OK      cameras_silent_24h     0          한계 0 · 켜져 있고 **전에 울린 적 있는데** 24시간 조용한 것: 없음 — 「죽었다」가 아니라 **「가서 봐라」**다
  OK      cameras_never_seen     39         켜져 있는 39대 중 **한 번도 이벤트를 낸 적 없는** 것 — 설치 미완·외부 드론일 수 있다. 경보가 아니라 **세어 두는 수**다 (임계 없음)
  OK      storage_used_gb        0.0006     버킷 guardianx-dev 객체 합계 0.0006GB
  UNKNOWN storage_used_pct       None       한계 80 · 용량 상한이 선언되지 않았다(GX_STORAGE_CAPACITY_GB) — **분모 없이 「몇 % 찼나」에 답하지 않는다**(D-301)
[OPS-MONITOR] ★ 경보 — 1개 신호가 한계를 넘었다
```

### 시드 역할 사람 U2·U4

- 도는 자리: `container` · 명령: `python /repo/scripts/verify_seed_roles.py`
- 종료 코드 **0** → 초록 · 4.1초

```
[verify_seed_roles] 소속 4(ETRI-Group)
  OK   시드 사람        2명 · 표식 온전
  OK   역할·소속        각 1개 · 소속 일치
  OK   K3 프리셋       기대와 같다 · matched=True
  OK   K2 수신자       critical 수신자 14명 · {"operator": 12, "fire_admin": 1, "view_only_-_anyang": 1}
```

### 경보 발송처 표 (OPS-10)

- 도는 자리: `container` · 명령: `python /repo/scripts/ops_alert_routing.py`
- 종료 코드 **1** → **빨강** · 4.0초

```
  OK   ① 표를 세웠는가        규칙 4줄을 폈다
  FAIL ② 닿는 사람 0명       규칙은 있는데 **받을 사람이 0명**: 4(ETRI-Group)/critical/fire_user
  OK   ③ 미구현 채널         규칙이 가리키는 채널이 전부 등록돼 있다
  FAIL ④ 사람에게 도달        **모든 규칙이 `log` 다 — 사람에게 도달하는 경보가 0건이다.** 배선은 살아 있고 수신 채널만 미정이다(DA-04 D4-1)
판정 **실패**.
④가 빨간 것은 **배선의 결함이 아니라 대표 결정 대기**다(DA-04 D4-1). 그 결정이
```

### 로그 수집기·보존 (OPS-07)

- 도는 자리: `host` · 명령: `scripts/ops_log_collectors.py`
- 종료 코드 **1** → **빨강** · 16.8초

```
  OK   ① 수집기 전수       수집기 6개를 전수로 셌다
  FAIL ② 보존 기간        **보존 기간이 없다**(무한 적재): 컨테이너 stdout · gx-shell, 컨테이너 stdout · postgres, 컨테이너 stdout · redis, 컨테이너 stdout · guardianx-source-minio-1, 컨테이너 stdout · gx-fe-build
  OK   ③ 자라는 속도       6개의 한 시간 치를 쟀다
판정 **실패** — 통과가 목표가 아니다. **지금 어떤 수집기가 무한히 쌓이는지**를
```

## 한 바퀴의 결론

| 자리 | 색 | 종료 코드 |
|---|---|---|
| 감시 3종 (liveness·lag·fill) | **빨강** | 1 |
| 시드 역할 사람 U2·U4 | 초록 | 0 |
| 경보 발송처 표 (OPS-10) | **빨강** | 1 |
| 로그 수집기·보존 (OPS-07) | **빨강** | 1 |

한 바퀴의 색: **빨강** — 빨강 3 — 감시 3종 (liveness·lag·fill), 경보 발송처 표 (OPS-10), 로그 수집기·보존 (OPS-07)

걸린 시간 29초. 순회에 **넣지 않은 것**: 되돌리기 훈련(OPS-08 · 6분 · DB 를
만들었다 지운다) · 볼륨 백업(OPS-12 · 볼륨에 파일을 쌓는다). 아침마다 도는 순회가
그런 일을 하면 **순회 자체가 사고의 원인**이 된다 — 그 둘은 사람이 부른다.
