# FWS-F2-11 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-11.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-11",
  "title_parts": [
    {
      "part": "철수 회신",
      "where": "backend/apps/fws/missions.py:respond(action=\"released\") · POST /api/fws/missions/{event_id}/response?action=released",
      "status": "measured: tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_mission_detail_dispatch_arrive_release_chain — 200, duration_minutes 계산·감사 기록 확인(SPEC/FWS-F2-11.json)"
    },
    {
      "part": "복귀 회신(자원 배치판 해제로 이어지는 신호)",
      "where": "backend/apps/fws/resource_board.py::_mission_state — 사람의 최신 임무 줄(mission.dispatch / mission.released, 대기 상태를 다시 저장한 뒤의 것만)을 읽어 GET /api/fws/resources/board 의 people[].mission_state · released_at · standby.on_standby/deployed/released 에 싣는다(missions.py 는 손대지 않고 상수만 읽음)",
      "status": "measured: 출동하면 deployed(대기 인원에서 빠짐), 철수 회신 뒤 released + released_at, 대기 인원에 다시 든다(배치판 해제). 대기를 다시 등록하면 옛 임무는 무시 · client_measured: backend/tests/test_ar_n1_half_remaining.py::ReleaseFreesBoardTest::test_dispatch_deploys_release_frees_and_refetch_shows_it"
    },
    {
      "part": "순서 보장(도착 없이 철수 시 거절)",
      "where": "backend/apps/fws/missions.py:_require_own(actor, event_id, ACTION_ARRIVED, ...) 226행",
      "status": "measured: tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_releasing_before_arriving_is_409 — 도착 없이 철수 시도 시 409 확인"
    },
    {
      "part": "사건 상태 보존(다른 진화대 안전)",
      "where": "backend/apps/fws/missions.py:respond released 분기(227-228행) — event_advanced=False, 사건 상태 안 옮김",
      "status": "measured: tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_second_crew_joins_without_409_and_release_keeps_event_open — 첫 진화대 철수 뒤에도 사건이 in_progress 로 유지됨을 확인"
    },
    {
      "part": "배치판 화면(출동 중 · 철수·해제 태그)",
      "where": "frontend/src/features/fws/pages/W2cCommandCards.tsx::data-gx=fws-f2-11-deployed · fws-f2-11-released — 지휘 화면 자원 배치판 카드(새로 보기 버튼이 GET /api/fws/resources/board 를 다시 부름)",
      "status": "measured: 소스 정적 대조 backend/tests/test_ar_n1_half_remaining.py::ReleaseFreesBoardTest::test_screen_draws_deployed_and_released_tags · 누른 뒤 재조회는 위 왕복"
    }
  ],
  "retro": "턴 AR 차선 N1 · 2026-09-30 · 철수 회신이 자원 배치판을 푼다(released 표시 + 대기 인원 복귀) — 부분 행 0(client_measured). 세종 결정 번호 없는 읽기 전용 파생이라 새 번호를 짓지 않았다."
}
```
