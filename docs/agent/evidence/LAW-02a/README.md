# LAW-02a — 영상 보존 일수를 제품이 선언한다 (그리고 그대로 지운다)

- 차선 L (법·영역 ⑧) · 2026-09-05 (기계) · 턴 D
- 판정: **닫힘 후보 — 조율자 확인 필요** (아래 「못 잰 것」과 「조율자 배선」을 함께 읽어라)

## 1. 무엇을 만들었나

| 자리 | 파일 | 하는 일 |
|---|---|---|
| 선언 | `backend/apps/dsm/retention.py` | 보존 일수 하나 · 그 수의 **출처** · 「도는가」 |
| 집행 | 같은 파일 `sweep()` | 지난 것을 **진짜로** 지운다 (dry-run 이 기본값) |
| 주기 | `backend/common/ops_tasks.py::video_retention_sweep_beat` | 매일 도는 자리 |
| 주기 등재 | `backend/config/celery.py` `law02a-video-retention-sweep` 03:20 | 감사 정리(03:10) 뒤 · 백업(03:30) 앞 |
| HTTP | `backend/apps/dsm/law_api.py` `GET /api/dsm/law/retention` · `POST /api/dsm/law/retention/sweep` | 미리보기와 집행을 **다른 문**으로 |
| 화면 | `frontend/src/features/dsm/components/RetentionNotice.tsx` | 「영상 보관 기간」 N일 · 「보관 기간이 지난 영상은 자동으로 지워집니다」 |
| 안내판 연결 | `backend/apps/dsm/legal_notice.py::retention_days` | **한 곳에서만 정한다** (안내판과 삭제가 같은 수를 본다) |

지우는 자리 셋(`retention.TARGETS`), 그리고 **지우지 않는 것**:

- 녹화 영상 `stream_monitors.StreamMonitorRecord` — 행 + 객체
- 영상 구간 참조 `stream_monitors.EventClip` — 행
- 이벤트 스냅샷 `stream_monitors.DetectionEvent.snapshot_path` — **이미지만**, 행은 남긴다
  (그 행은 오탐률의 분모이고 감사의 근거다. 지우면 「사건이 없었다」와 「기록을 지웠다」가 같아진다)

## 2. 값과 그 출처 — 지어내지 않았다

기본값 **30일**. 출처는 세종(CPO)이 쓴 서식
`docs/design/GX-LAW-02_영상정보처리기기_고지_초안_v0.1.md` 의 안내판 칸이다.
우리가 법조문을 읽고 정한 수가 **아니다**. 운영 설정(`VIDEO_RETENTION_DAYS` 등)이 있으면
그 값이 이긴다.

★ 차선 E 가 지난 턴에 30을 **안 적은 것은 옳았다**. 그때는 지우는 손이 없었기 때문이고,
집행 없이 적힌 수는 안내판을 거짓말로 만든다. 지금 값이 생긴 이유는 **집행이 생겼기
때문**이지 서식을 베껴서가 아니다 — 그 순서가 이 절의 전부다.

## 3. 실행한 명령과 출력 원문

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings     DB_TEST_NAME=test_gx_l python -m pytest tests/test_l_retention.py -q     --nomigrations -p no:randomly --tb=short 2>/dev/null'
13 passed, 4 warnings in 7.59s
```

세 파일을 함께:

```
$ ... pytest tests/test_l_retention.py tests/test_l_privacy_request.py tests/test_l_ai_act.py -q ...
43 passed, 1 skipped, 34 warnings in 20.83s
```

이웃 시험 회귀(고친 파일들이 물고 있는 자리):

```
$ ... pytest tests/test_e_cpo_doc_wiring.py tests/test_dsm_app.py tests/test_k2_notify_kernel.py       tests/test_route_tripwire.py tests/test_clip_playback.py -q ...
100 passed, 34 warnings in 52.94s
```

라우트 실측(대장 파일을 건드리지 않고 임시 파일로 떴다):

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings     python /repo/scripts/probe_route_inventory.py /tmp/routes_l.json'
[ROUTE-INVENTORY] 테넌트 범위: none 651 · required 47 · exempt 1
routes 699
  /api/dsm/law/retention            GET   tenant_scope=required  authn=JwtOrInboundKey
  /api/dsm/law/retention/sweep      POST  tenant_scope=required  authn=JwtOrInboundKey
```

게이트:

```
$ python scripts/verify_post_arg_style.py
[POSTARG] [입력] 서버 면 2개 모듈 · 라우트 47건 중 POST 15건
[POSTARG] POST 인자 방식: NOARG 2 · QUERY 13
[POSTARG] 통과 — 본문/질의가 어긋난 자리 0건

$ python scripts/verify_ui_copy.py
[COPY] [입력] 37개 화면 파일 (주석 걷어낸 뒤) · 패턴 7종
[COPY] 통과 — 새로 생긴 대장 언어 0건

$ python scripts/verify_layers.py
[LAYER] 통과 — 계층 위반 0건

$ python scripts/verify_dormant.py
[DORMANT] 통과 — 새로 잠든 것 0건 (기준선 315건 안에 있다)
```

## 4. 무엇을 쟀나 — 시험이 못박은 것

- **수가 하나다**: 안내판(`legal_notice.retention_days`)과 삭제(`retention.retention_days`)가
  같은 수를 본다.
- **양성과 음성**: 999일 된 녹화·구간 참조는 사라지고, 방금 만든 것은 남는다.
- **dry-run 이 기본값**: 인자 없이 부른 `sweep()` 은 `deleted_total == 0` 이고 행이 그대로다.
  그러면서 만료 건수는 **센다**(미리보기가 아무것도 못 세면 미리보기가 아니다).
- **소프트 삭제가 아니다**: `all_objects` · `deleted_objects` 어느 매니저에도 안 남는다.
- **감사**: 지운 행의 **식별자**가 `data_after.targets[].deleted_ids` 에 남고, LAW-08
  해시 체인의 `row_hash` 가 함께 온다. 미리보기도 남는다.
- **못 지운 바이트**: 객체 삭제가 실패하면 **행을 남긴다**(고아 영상을 만들지 않는다).
- **주기**: beat 표에 `common.video_retention_sweep_beat` 가 실재한다.
- **설정 오타**: `VIDEO_RETENTION_DAYS=0` 이나 `"이레"` 는 **0일 보존이 되지 않는다**.

## 5. 못 쟀고, 왜

- **객체저장소에서 바이트가 실제로 사라지는가** — 못 쟀다. 시험은 경로가 빈 행으로
  삭제 자체를 재고, 저장소 실패 갈래는 `_remove_object` 를 가려서 잰다. MinIO 에 실물
  녹화를 올려 지우는 것은 이 차선의 시험 범위 밖이다(E2E 자리).
  ★ 게다가 이 환경의 객체저장소 호스트는 `minio.invalid` 다 [실측 — Django 기동 로그:
  `[MinIO Init] Warning: ... Failed to resolve 'minio.invalid'`]. 닿지 못하는 저장소를
  상대로 「지웠다」를 잴 수는 없다 — 그래서 실패 갈래를 대신 쟀다.
- **주기가 실제로 03:20 에 도는 것을 본 적은 없다.** 잰 것은 **beat 표에 있다**까지다.
  beat 를 띄우는 것은 `backend/entrypoint.sh` 의 `celery -A config beat` 다 [실측] —
  `docker-compose.yml` 의 `celery` 서비스는 **worker 만** 띄운다.
- **테넌트별 보존기간** — 없다. 녹화 표(`StreamMonitorRecord`)에 소속 칸이 없어서
  집행이 전역이다 [실측 `stream_monitors/models.py:163`]. 그래서 실행 라우트는
  전역 관리자만 부를 수 있게 막았다. **약속할 수 없는 것을 약속하지 않았다.**

## 6. 법률 검토 대기

- 30일이 이 용도의 법정 기준에 맞는 수인가 — **대조 전**이다(`RETENTION_LEGAL_REVIEW`).
  이 절이 닫는 것은 「선언하고 그대로 지운다」이지 「그 수가 적법하다」가 아니다.
- 삭제 청구(LAW-07)에 따른 **개별 영상 삭제**는 이 집행과 다른 자리이며, 아직 없다.

## 7. 다음 사람이 확인할 것 3줄

1. `config/celery.py` 의 `law02a-video-retention-sweep` 를 지우면 화면의
   「보관 기간이 지난 영상은 자동으로 지워집니다」가 **거짓 문장**이 된다.
   지우려면 그 줄과 화면을 함께 내려야 한다(`retention.policy()['enforced']` 가 그것을 잰다).
2. 운영 반영 전에 `VIDEO_RETENTION_DAYS` 를 고객이 정하게 하라 — 기본값 30은
   **서식에서 온 수**이지 그 고객이 정한 수가 아니다.
3. 첫 집행은 되돌릴 수 없다. 반영 직후 `POST /api/dsm/law/retention/sweep`(dry_run 기본값)
   으로 **먼저 세어 보라**. 그 미리보기도 감사에 남는다.

## 부록 — 이 턴에 함께 움직인 것 (전 차선 회귀)

```
$ docker exec gx-shell sh -c 'cd /app && DJANGO_SETTINGS_MODULE=config.settings     DB_TEST_NAME=test_gx_l python -m pytest tests --ignore=tests/e2e -q     --nomigrations -p no:randomly --tb=line 2>/dev/null'
992 passed, 3 skipped, 34 warnings in 276.72s (0:04:36)
```

★ 첫 전수 실행은 **2 failed** 였다 — `test_f05_event_api.py::EntrySurfaceIsLockedTest`.
F-05 진입면 잠금이 새 라우트 여덟을 보고 멈춰 세운 것이고, **그것이 그 시험의 값이다.**
여덟 줄을 손으로 등재하는 일이 곧 「진입면을 넓힌다」는 선언이므로, 사유와 함께
`EVENT_ENTRY_SURFACE` 에 더했다. 지시보다 게이트가 위다.

이 차선이 만진 **공용 파일**(내 소유 목록 밖 · 사유와 함께):

| 파일 | 무엇을 | 왜 |
|---|---|---|
| `backend/kernels/k2_notify/services.py` | 알림 본문 꼬리 한 줄 + import | 고지가 닿아야 하는 자리이고, 커널은 App 을 import 할 수 없다 |
| `backend/common/ops_tasks.py` | 주기 태스크 하나 덧붙임 | 감사 정리 옆에 같은 모양으로 선다(지시대로) |
| `backend/config/celery.py` | beat 항목 하나 | 이 줄이 없으면 화면의 「자동으로 지워집니다」가 거짓이 된다 |
| `backend/apps/dsm/legal_notice.py` | `retention_days` 위임 + 낡은 사유 갱신 | 안내판과 삭제가 **같은 수**를 봐야 한다 |
| `backend/tests/test_f05_event_api.py` | 진입면 여덟 줄 등재 | 그 잠금이 요구하는 선언 |
| `scripts/verify_post_arg_style.py` | `API_MODULES` 에 새 컨트롤러 한 줄 | 안 적으면 새 파일이 게이트의 **눈 밖**이다 |
| `frontend/src/features/dsm/api.ts` | 끝에 엔드포인트 상수만 추가 | 기존 줄은 고치지 않았다 |
| `frontend/src/features/dsm/pages/ControlDashboard.tsx` | 고지 조각 부착 2줄 | 고지가 「읽는 자리」에 있어야 한다 |
