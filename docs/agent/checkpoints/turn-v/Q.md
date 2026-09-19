# 차선 Q — 턴 V 체크포인트 (2026-09-18)

## 닫음
- **P-179 FC 정본 넷 정정** — `scripts/verify_click_completes.py` U2#6·U4#5·U4#7·U4#16.
  눌러서 확인: `python scripts/verify_click_completes.py --self-test` → **기대 호출 식 31 → 34** · 자기시험 통과
  (양성 34/34 · 변이 9/9 · 되돌림 선언 8자리). 전/후 표: `docs/agent/evidence/P-179/정정_전후.md`.
  ⚠ U4#5 는 정정 문안만 넣고 **회색으로 남겼다**(자동본은 사람이 누르지 않는다 · 읽기 전용 403 이 옳다) — 사유는 표에.
  ⚠ **FC 수는 안 쟀다 — V 가 잰다.**
- **P-180 온보딩 도구 22 → 35행** — `scripts/measure_onboarding_t.py`.
  눌러서 확인: `python scripts/measure_onboarding_t.py --check`
  → 「행 48 · 두 칸 35 · 정본 없음 13 · 이 도구가 재는 행 35 · O 문서와 도구가 같은 35행을 든다」.
  행 목록·분모를 **문서에서 읽는다**(하드코딩 목록을 없앴다) — 다시 갈리면 `--check` 가 이름으로 말한다.
- **U1 요청 셋** — ① `capture_screens._seed_snapshot` 이 제품 경로(`detection_snapshot.upload_snapshot`)를
  타서 씨앗에 그림을 싣는다 ② `seed.json` 의 `events[].snapshot_path` + `snapshot{}` 요약 ③ `--snap-event`
  기본값이 **그림 실린 첫 씨앗**, 없으면 U2#4 만 회색(나머지 34행은 잰다).
  눌러서 확인: 기존 `seed.json` 으로 `load_seed` → `first_snapshot_event_id=None` · `snapshot_by_id` 둘 다 빈 문자열
  (U1 실측과 같다). 우회 한 줄은 도구 머리말에 적었다 — **`--snap-event 4802`**.

## 손 위
- **P-181 걷기 W5·W6** — `scripts/walk_scenarios.py` 에 S5「팀장 아침 인수(U2·1440)」 · S6「관리자 설치 다음 날(U5·1440)」을
  **걷기 전용 접두 `W5`·`W6`** 로 등재. 다음 한 줄: `walk_scenarios.py` 의 시나리오 표와 `NOT_WALKED` 를 읽고
  `perf_load.SCENARIOS` 와 이름이 안 부딪히는지 대 본다.

## 안 한 것
- U3 요청(씨앗이 스냅샷 참조 / 사건에 주소) — **아직 안 왔다**. U1 요청 ②로 `snapshot_path` 는 이미 실린다.
- 재측 일체 — **V 의 몫이다**(고치는 사람과 재는 사람은 다르다).
