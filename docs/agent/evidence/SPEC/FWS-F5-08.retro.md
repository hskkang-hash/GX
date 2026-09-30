# FWS-F5-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F5-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F5-08",
  "title_parts": [
    {
      "part": "비행 기록(로그 한 줄 생성)",
      "where": "POST /api/fws/drone/flights · backend/apps/fws/drone.py::log_flight()",
      "status": "measured: tests.test_fws_f5.F5_08_FlightLogTest.test_log_is_recorded_and_read_back — POST 200, source=\"dji\" 응답"
    },
    {
      "part": "배터리 상태(battery_pct, 범위 검증)",
      "where": "backend/apps/fws/drone.py::log_flight() BATTERY_PCT_MIN/MAX 검증 · GET /api/fws/drone/flights/mine",
      "status": "measured: docs/agent/evidence/SPEC/FWS-F5-08.json row.battery_pct=68.5 실측 + test_battery_out_of_range_is_422 로 150 입력 시 422 실측"
    },
    {
      "part": "기체 상태(airframe_code)",
      "where": "backend/apps/fws/drone.py::log_flight() airframe_code 필드 · GET /api/fws/drone/flights/mine",
      "status": "measured: docs/agent/evidence/SPEC/FWS-F5-08.json row.airframe_code=\"M30T-7\" 값이 제출·재조회에 동일"
    },
    {
      "part": "기록 재조회(내 비행 기록 목록)",
      "where": "GET /api/fws/drone/flights/mine · backend/apps/fws/drone.py::flights_mine()",
      "status": "measured: 동일 시험에서 POST 후 GET mine 에 count=1, 값 일치 실측"
    },
    {
      "part": "화면 — 비행 기록 입력(연동 구분·기체·배터리·비행 분) · 내 비행 기록 표",
      "where": "frontend/src/features/fws/pages/DroneHome.tsx::FlightLogCard (data-gx=fws-f5-08-card · fws-f5-08-source · fws-f5-08-airframe · fws-f5-08-battery · fws-f5-08-minutes · fws-f5-08-save · fws-f5-08-minutes-total · fws-f5-08-flights) · POST /api/fws/drone/flights · GET /api/fws/drone/flights/mine · GET /api/fws/drone/flights/minutes",
      "status": "구현 — 저장 뒤 reloadFlights() 가 새 GET(flights/mine · minutes, 캐시 우회)으로 배터리·기체·비행 분 표를 다시 그린다. tests.test_aq_w2c_command_admin_drone.W2cAdminDroneTest.test_f5_08_flight_log_then_mine_rereads_battery_and_airframe · tests.test_aq_w2c_command_admin_drone.W2cScreenStaticTest.test_drone_flight_card_is_wired"
    },
    {
      "part": "실제 기체·배터리 연동(DJI 등 외부 드론 커넥터로부터 실시간 상태 수신)",
      "where": "backend/apps/fws/drone.py::log_flight() source 파라미터 — 어댑터 이름을 담는 값 자리뿐, 실제 외부 API 호출 코드 없음(머리말 14행 및 evidence 'what' 명시)",
      "status": "없음 — 실제 DJI 등 기체 연동 API 호출은 0건이다. source·battery_pct·airframe_code 는 모두 호출자가 수동으로 입력하는 값이며, 기체로부터 자동 수신되는 경로가 없다",
      "excluded_by": "P-428",
      "excluded_why": "실제 기체(DJI 등)로부터의 실시간 자동 수신은 드론 커넥터 — 외부 하드웨어 실연동이다. WO-19 §「외부 실연동·드론 커넥터·지도 렌더는 하지 않는다」가 이 턴 범위 밖으로 명시했다. 제목이 부르는 「비행 기록·배터리·기체 상태」 자체(기록·검증·재조회)는 사람이 입력한 값으로 완결됐다 — 자동 수신은 그 위에 얹는 별도 어댑터 작업이다."
    }
  ],
  "retro": "턴 AQ 차선 W2C · 화면 배선 · 사람 확인 — 드론 화면 비행 기록 카드에 data-gx 와 「내 비행 기록」 재조회 표를 달았다. 외부 기체 실연동 행은 P-428 그대로."
}
```
