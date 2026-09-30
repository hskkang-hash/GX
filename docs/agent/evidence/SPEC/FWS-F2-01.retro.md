# FWS-F2-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-01",
  "title_parts": [
    {
      "part": "주간 대기 상태 등록",
      "where": "backend/apps/fws/standby.py:set_status (STATUS_STANDBY_DAY) · POST /api/fws/resources/me/status?status=standby_day",
      "status": "measured: night 값으로 동일 코드경로 실측(test_set_then_read_back_standby_status) · day 는 같은 STATUSES 튜플의 값이라 같은 검증·저장 경로를 탄다(전용 HTTP 호출은 없음)"
    },
    {
      "part": "야간 5분대기조 상태 등록",
      "where": "backend/apps/fws/standby.py:set_status (STATUS_STANDBY_NIGHT) · POST /api/fws/resources/me/status?status=standby_night",
      "status": "measured: tests.test_fws_f2.F2_01_StandbyStatusTest.test_set_then_read_back_standby_status — POST 저장 뒤 GET 재조회에 status=standby_night 그대로 확인"
    },
    {
      "part": "위치 등록(대기 중 위치)",
      "where": "backend/apps/fws/standby.py:set_status/my_status (location={lat,lng}) · GET /api/fws/resources/me/status",
      "status": "measured: 같은 시험에서 lat=36.4,lng=127.4 저장 → 재조회 응답 location 필드로 그대로 확인(SPEC/FWS-F2-01.json response.body.location)"
    },
    {
      "part": "자원 배치판에 표시(완결조건 — 명세서 §5.2 156행)",
      "where": "frontend/src/features/fws/pages/W2cCommandCards.tsx::ResourceBoardCard (지휘 화면 CommandHome.tsx 에 붙음 · data-gx=fws-f2-01-board · fws-f2-01-board-refresh · fws-f2-01-standby-counts · fws-f2-01-count-day · fws-f2-01-count-night · fws-f2-01-standby-list) · GET /api/fws/resources/board · backend/apps/fws/resource_board.py::standby_roster (standby.set_status 가 테넌트 곁표를 붙여 남긴 줄 · 사람마다 최신 한 줄)",
      "status": "구현 — 대원 대기 상태 등록 뒤 지휘 화면 refreshAll 이 GET /resources/board 를 다시 불러 대기 인원·주간/야간 수·사람별 상태·위치를 그린다. 다른 기관 대원은 섞이지 않는다. tests.test_aq_w2c_command_admin_drone.W2cResourceBoardTest.test_f2_01_standby_then_board_rereads_people_and_counts · tests.test_aq_w2c_command_admin_drone.W2cScreenStaticTest.test_command_board_and_withdrawal_are_wired (곁표 이전에 쓴 옛 대기 줄은 기관을 모르므로 세지 않는다)"
    }
  ],
  "retro": "턴 AQ 차선 W2C · 화면 배선 · 사람 확인 — 지휘 화면에 자원 배치판(대기 인원·주간/야간·위치)을 그렸다 · 서버는 대기 저장에 기관 곁표를 붙이고 배치판 GET 하나를 더했다."
}
```
