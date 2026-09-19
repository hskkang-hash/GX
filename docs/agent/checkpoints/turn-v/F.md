# 차선 F — 턴 V 체크포인트 (P-176)

갱신: 2026-09-18 · 2차

## 닫음 (눌러서 본 것만)

- **`handled_note` 쓰는 문** — `POST /api/dsm/system/requests/{id}/handled`
  (`backend/apps/dsm/api_f_ops.py` 신설 · `urls.py` 등록).
  `pytest tests/test_f_system_request_handled.py` → **13 passed, 1 skipped**.
  라우트 해석 실측: `resolve('/api/dsm/system/requests/1/handled')` → ninja_extra ·
  이웃한 없는 자리는 `NO ROUTE`(음성 대조).
- **등재 해제 + 배선이 같은 변경** — `verify_dead_fields.py` 호스트 실행
  `exit=0 · 새 빚 0 · 선언 등재 8 → 7 · 배선되어 빠진 것 0` [실측].
- **U3·U6 온보딩 버킷** + U4 HWPX 카드 1 — `verify_onboarding_walk.py`
  `[입력] 사람 6/6 · 카드 38장(닫는 카드 20 · 못 재는 카드 18)` · 구조 `exit=0` ·
  자기시험 **18/18**(출생 표본 ③ 「닿지 않는 카드 표」 신설) [실측].
- `pytest tests/test_onboarding_progress.py` → **42 passed**(건너뜀 0).
- 조율자가 준 **빨강 다섯** 닫음: 계층 위반(App 이 커널 서브모듈 import) → 사본 상수 +
  커널과 대 보는 시험 · `EVENT_ENTRY_SURFACE` 에 새 문 등재.
  `pytest tests/test_f05_event_api.py tests/test_k1_event_kernel.py
  tests/test_onboarding_progress.py` → **77 passed** [실측].
- 동음이의 래칫: 내 몫 1건 닫음(177 → 176). 남은 +2 는 내 파일이 아니다(아래).

## 손 위

- 전량 단위시험 `pytest tests --ignore=tests/e2e` 실행 중 — **수를 보고에 적는다.**
- **다음 한 줄**: 전량 결과를 받아 실패가 있으면 닫고, 보고를 쓴다.

## 안 한 것

- **살아 있는 게이트 서버로는 못 눌렀다(회색).** `gx-shell` 의 runserver 가
  `--noreload` 로 04:47 에 떴다 — 내 코드가 안 올라가 있다(`?persona=U9` 가 422 대신
  200 · 응답에 `viewer_role` 없음). **재기동은 조율자 자리**(다른 차선이 재는 중이다).
- 프런트 배선 0 — 점검 창 기록 문을 부르는 화면은 U56 소유 파일.
- 라우트 대장(D-343) 761 → **762 갱신 안 함** — 병합 시점에 조율자가 `--refresh`/`--freeze`.
- 성능: 3벌 쟀다. 1벌은 **경합으로 버렸다**(401 466건 — 같은 계정 세션이 밀렸다).
  2·3벌은 오류 0. 판정은 `exit=2`(회색) — 잡음 30~67% 가 문턱 20% 보다 크다.
