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
      "where": "backend/apps/fws/missions.py:respond released 분기(225-249행) — 사건 상태는 그대로 둠",
      "status": "부분 — '복귀' 자체 기록(released_at, duration_minutes)은 남지만, 명세서 완결조건 「자원 배치판 해제」(F3 화면 몫)로 실제 이어지는지는 F2 쪽에서 검증되지 않는다. 표준 자원 배치 상태(standby.py 의 대기 상태)를 released 가 자동으로 되돌리는 연결 코드가 없다 — missions.py 와 standby.py 는 서로 다른 감사 로거를 쓰고 연결되지 않음(grep 결과 두 모듈 간 직접 호출 없음)"
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
    }
  ]
}
```
