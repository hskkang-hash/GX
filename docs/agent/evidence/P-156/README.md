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

## ★ [P-170 ② · 2026-09-18 턴 U · 차선 Q] 씨앗 id 파이프 · **정리 순서**

턴 T 의 오판 하나가 정확히 이 자리였다(D-487 ②): 씨앗 id 배선을 뒤 도구로 옮겨 놨는데
`capture_screens` 가 **스스로 씨앗을 지워** 넘길 id 가 없었다. 규약을 순서로 못박는다.

**순서 — 한 회의 씨앗이 거치는 네 걸음 (`capture_screens.py` 의 `finally`)**

1. **심는다** — `seed_events()` (K1 `record_detection` 경로 · `track_id=data_source=probe;run=<RUN_STAMP>`)
2. **표시한다** — `probe_marks.mark(ids, run, judged=True)` → `…;judged=1`
3. **명세를 쓴다** — `_write_seed_file()` → `docs/agent/evidence/P-157/runs/<RUN_STAMP>/seed.json`
4. **(명시했을 때만) 지운다** — `--clean-seeds` 를 손으로 적었을 때만 `clean_events()`

★ **기본은 남기기다**(`--keep-seeds`). 지우려면 손으로 적어야 한다.
★ 순서가 규약인 이유 둘: **정리가 명세보다 먼저면** 뒤 도구가 읽을 것이 없다(턴 T 의 그 자리) ·
  **표시가 정리보다 나중이면** 정리가 실패한 회의 씨앗이 표식 없이 남아 다음 표본을 더럽힌다.
★ 명세가 비면 **파일을 쓰지 않는다.** 빈 파일을 쓰면 「최신」이 빈 것을 가리키고, 그러면
  뒤 도구가 지난 회의 진짜 씨앗 대신 이번 회의 빈 것을 읽는다.

**`seed.json` 이 나르는 것** — id · severity · probe 표식 · 시각 (+ 주소 · 씨앗 카메라 · 소속)

| 칸 | 뜻 |
|---|---|
| `event_ids` · `first_event_id` | 이번 회가 심은 사건 번호. `--keep-event` 로 손으로 주던 값이 여기로 왔다 |
| `events[].severity` · `event_type` · `occurred_at` | 행마다의 등급·유형·시각 |
| `probe_mark` · `probe_tag` · `run` | `data_source=probe;run=<stamp>` · 씨앗 카메라 코드 접두 · 회차 |
| `address` | 씨앗 카메라의 설치 주소와 **그것을 어디서 빌렸는지**(아래 절) |

**읽는 쪽** — `--seed-file` (안 주면 `runs/` 의 **최신**. 최신은 **디렉터리 이름(시각)** 으로 고른다 —
파일 mtime 으로 고르면 git 체크아웃이 전부 같은 시각으로 만들어 놓은 뒤 아무 회차나 최신이 된다):

    scripts/verify_click_completes.py --measure [--seed-file …]
    scripts/verify_feature_reach.py             [--seed-file …]
    scripts/measure_onboarding_t.py             [--seed-file …]

읽는 함수는 한 곳이다 — `scripts/probe_marks.py::load_seed()` / `latest_seed_file()`.
**없으면 빈 벌**이고(없는 것은 없는 것이다 · D-301), 깨진 파일도 빈 벌 + 사유다. 지어내지 않는다.
부르는 쪽은 빈 벌을 **회색**으로 적어야 한다 — 빈 씨앗으로 잰 초록은 분모 0 인 초록이다.

    python scripts/probe_marks.py --self-test   # 표본 4 · 판정 9 + 씨앗 파이프 8 = 17

## ★ [턴 U · 절 6] 씨앗에 **주소가 있다** — 짐작하지 않고 **빌린다**

`U3#2`(「위치 확인 — 어디로 가나」)가 빨갛던 원인은 제품이 아니라 씨앗이었다:
씨앗 카메라의 `install_address` 가 비어 있어 사건 상세의 `address` 가 늘 빈 값이었다.

- 기본(`address=None`): `_borrow_real_address()` 가 **같은 소속의 실재 카메라**(씨앗 카메라 제외 ·
  `install_address` 가 빈 것 제외) 중 pk 가 가장 작은 한 대의 주소·상세·출처를 그대로 쓴다.
- 한 대도 없으면 **빈 채로 두고** 그 사실을 `seed.json` 의 `address.why` 에 적는다. 빈 것은 빈 것이다.
- `--seed-address` 로 손으로 정할 수 있으나 **기본이 아니다.** 주소는 알림에 그대로 나가는 칸이라
  지어낸 문자열을 기본값으로 삼지 않는다(D-330 · D-331).
