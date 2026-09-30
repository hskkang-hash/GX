# FWS-F2-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-05",
  "title_parts": [
    {
      "part": "인력(personnel) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_PERSONNEL) · POST /api/fws/missions/{event_id}/field-reply?kind=personnel",
      "status": "measured: helicopter 로 실측된 것과 동일한 검증(SUPPORT_KINDS 튜플 멤버십 체크)·저장 경로를 탄다(missions.py 258-272행) — kind=personnel 전용 HTTP 실측은 없으나 같은 함수 안 같은 분기 | 턴 AQ W2C: kind 별 전용 HTTP 실측 추가 — tests.test_aq_w2c_command_admin_drone.W2cResourceBoardTest.test_f2_05_support_request_then_board_badges_rise"
    },
    {
      "part": "물(water) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_WATER)",
      "status": "measured: 위와 동일 — 같은 코드경로, kind=water 전용 HTTP 실측은 없음 | 턴 AQ W2C: kind 별 전용 HTTP 실측 추가 — tests.test_aq_w2c_command_admin_drone.W2cResourceBoardTest.test_f2_05_support_request_then_board_badges_rise"
    },
    {
      "part": "헬기(helicopter) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_HELICOPTER) · POST /api/fws/missions/{event_id}/field-reply?kind=helicopter",
      "status": "measured: tests.test_fws_f2.F2_05_SupportRequestTest.test_support_request_reaches_field_reply — 200, kind=\"helicopter\" 응답 확인, field_replies 목록 도달도 직접 조회로 확인(SPEC/FWS-F2-05.json)"
    },
    {
      "part": "중장비(heavy_equipment) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_HEAVY_EQUIPMENT)",
      "status": "measured: 위와 동일 — 같은 코드경로, kind=heavy_equipment 전용 HTTP 실측은 없음 | 턴 AQ W2C: kind 별 전용 HTTP 실측 추가 — tests.test_aq_w2c_command_admin_drone.W2cResourceBoardTest.test_f2_05_support_request_then_board_badges_rise"
    },
    {
      "part": "지휘 화면 배지(완결조건 — 명세서 §5.2 160행)",
      "where": "frontend/src/features/fws/pages/W2cCommandCards.tsx::ResourceBoardCard (지휘 화면 CommandHome.tsx · data-gx=fws-f2-05-support-badges · fws-f2-05-badge-personnel · fws-f2-05-badge-water · fws-f2-05-badge-helicopter · fws-f2-05-badge-heavy-equipment · fws-f2-05-support-list) · GET /api/fws/resources/board?event_id= · backend/apps/fws/resource_board.py::support_requests",
      "status": "구현 — 인력·물·헬기·중장비 네 종류를 각각 HTTP 로 요청한 뒤 같은 GET 재조회에 종류별 배지 1씩 · 다른 사건 0 · 남의 기관 404. tests.test_aq_w2c_command_admin_drone.W2cResourceBoardTest.test_f2_05_support_request_then_board_badges_rise · tests.test_aq_w2c_command_admin_drone.W2cScreenStaticTest.test_command_board_and_withdrawal_are_wired"
    }
  ],
  "retro": "턴 AQ 차선 W2C · 화면 배선 · 사람 확인 — 지휘 화면 자원 배치판에 지원 요청 종류별 배지를 그렸다(누른 뒤 refreshAll 재조회)."
}
```
