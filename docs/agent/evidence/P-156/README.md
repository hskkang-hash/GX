# P-156 — probe 표식 규약: 게이트용 씨앗 사건은 **매 회 생성 · 판정 뒤 표시 · 다음 표본에서 제외**

- 발행: 2026-09-17 · 턴 T · 차선 Q (P-159 ②) · 도구 `scripts/probe_marks.py`
- 근거 실측: `backend/stream_monitors/models.py` `DetectionEvent`(열 목록) · `backend/apps/dsm/services.py:211 event_data_source` ·
  `backend/apps/dsm/api.py:244-252`(목록 문 필드) · `backend/kernels/k1_event/services.py:229 record_detection(track_id=…)` ·
  `frontend/src` 에서 `track_id` grep **0건**

## 무엇을
게이트가 재려고 심는 사건(**씨앗**)이 다음 회의 표본에 섞이면 그 회의 수는 제품이 아니라 지난 회의 씨앗을 잰 수다
(턴 S 「캡처 직후 4/39」가 그 모양이었다). 그래서 씨앗에는 표식을 붙이고, 표본은 표식을 거른다.

## 표식을 어디에 — **모델을 고치지 않았다**
`data_source` 는 이벤트의 **열이 아니다.** `event_data_source` 가 훈련 창(감사)으로 계산해 `drill`/`live` 를 내며,
「열로 만들면 과거가 비고 빈 과거는 훈련 아님으로 읽힌다」고 그 함수가 스스로 적어 두었다. 그 판단을 존중한다.
이벤트의 자유 칸 가운데 **화면이 그리지 않고 · 64자 · K1 생성 경로가 받는** 칸이 `track_id` 하나라 거기 규약 문자열을 넣는다:

| 언제 | 누가 | `track_id` 값 |
|---|---|---|
| 심을 때 | `capture_screens.seed_events` (`record_detection(track_id=…)` — K1 경로를 지난 진짜 행) | `data_source=probe;run=<RUN_STAMP>` |
| 판정 뒤 | `capture_screens` 의 `finally` → `probe_marks.mark(ids, run, judged=True)` (정리 `clean_events` **앞**) | `data_source=probe;run=<RUN_STAMP>;judged=1` |
| 손으로 | `docker exec gx-shell python /repo/scripts/probe_marks.py --mark <id…> --run <stamp>` | 같음 |

⚠ `reject_reason` 은 사람이 읽는 칸(오탐 사유)이라 쓰지 않는다. `bbox` 는 검출 좌표라 뜻이 다르다.

## 제외 규칙
- **probe 사건** = `track_id` 가 `data_source=probe` 로 시작 **또는** 씨앗 카메라(`stream_monitor.code`/`stream_monitor_name` 이
  `gxprobe-D384-screen` 으로 시작)의 사건. 둘 중 하나면 probe 다(`probe_marks.is_probe`).
- 표본에서 뺀다 — 단 **이번 회에 심은 id 는 남긴다**(`probe_marks.exclude(records, keep_ids=[…])`). `keep_ids` 를 안 주면
  씨앗은 **전부** 빠진다: 「이번 것」을 모르면 빼는 쪽이 옳다(표본 0건은 판정기가 회색으로 적는다 — 분모 0 인 초록은 초록이 아니다).
- HTTP 로 고르는 게이트(`verify_click_completes` 드라이버)는 목록 문이 `track_id` 를 안 내므로 **카메라 이름**으로 가른다.
  같은 집합이다 — 씨앗은 전부 그 카메라 한 대에 심긴다. 이번 씨앗은 `--keep-event <id>` 로 넘긴다.
- 정리(`clean_events`)가 못 돈 회의 씨앗도 표식 덕에 다음 표본에 안 섞인다 — 표시가 정리보다 먼저다.

## 누가 표시하나
- 자동: `capture_screens.py` (심을 때 · 판정 뒤). `verify_click_completes.py` 는 심지 않고 **거르기만** 한다.
- 손: V 단독 세션이 게이트 밖에서 씨앗을 심었으면 같은 규약으로 `--mark` 한다. 표시 없이 남긴 씨앗은 다음 회의 거짓 빨강이다.

## 점검
    python scripts/probe_marks.py --self-test                                # 호스트 · Django 없이 (표본 4 · 판정 9)
    docker exec gx-shell python /repo/scripts/probe_marks.py --list          # DB 의 probe 사건 · 회차 · judged

## 한계 (적어 두지 않으면 초록으로 읽힌다)
- 목록 문에 `track_id` 가 없으므로 **씨앗 카메라 밖에 심은 probe** 는 HTTP 필터가 못 거른다 — 심는 자리를 그 카메라로 못박는 것이 규약의 절반이다.
- 이 턴에는 gx-shell 에서 `--list`/`--mark` 를 **돌리지 않았다**(차선은 게이트 서버·DB 에 손대지 않는다). ORM 갈래는 V 또는 조율자가 첫 실행에서 확인한다.
