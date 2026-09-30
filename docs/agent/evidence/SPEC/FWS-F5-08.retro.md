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
      "part": "실제 기체·배터리 연동(DJI 등 외부 드론 커넥터로부터 실시간 상태 수신)",
      "where": "backend/apps/fws/drone.py::log_flight() source 파라미터 — 어댑터 이름을 담는 값 자리뿐, 실제 외부 API 호출 코드 없음(머리말 14행 및 evidence 'what' 명시)",
      "status": "없음 — 실제 DJI 등 기체 연동 API 호출은 0건이다. source·battery_pct·airframe_code 는 모두 호출자가 수동으로 입력하는 값이며, 기체로부터 자동 수신되는 경로가 없다",
      "excluded_by": "P-428",
      "excluded_why": "실제 기체(DJI 등)로부터의 실시간 자동 수신은 드론 커넥터 — 외부 하드웨어 실연동이다. WO-19 §「외부 실연동·드론 커넥터·지도 렌더는 하지 않는다」가 이 턴 범위 밖으로 명시했다. 제목이 부르는 「비행 기록·배터리·기체 상태」 자체(기록·검증·재조회)는 사람이 입력한 값으로 완결됐다 — 자동 수신은 그 위에 얹는 별도 어댑터 작업이다."
    }
  ]
}
```
