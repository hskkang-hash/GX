# FWS-F5-10 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F5-10.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F5-10",
  "title_parts": [
    {
      "part": "비행 분 합계 계산(계량)",
      "where": "GET /api/fws/drone/flights/minutes · backend/apps/fws/drone.py::flight_minutes_total()",
      "status": "measured: tests.test_fws_f5.F5_10_FlightMinutesTest.test_flight_minutes_are_summed — 15분+27.5분 기록 후 flight_minutes_total=42.5 실측(docs/agent/evidence/SPEC/FWS-F5-10.json)"
    },
    {
      "part": "비행 건수 집계(flight_count)",
      "where": "backend/apps/fws/drone.py::flight_minutes_total() count 누적 · 동일 GET 응답",
      "status": "measured: 같은 시험에서 flight_count=2 실측"
    },
    {
      "part": "월별 필터(month 파라미터)",
      "where": "backend/apps/fws/drone.py::flight_minutes_total(month=...) · GET /api/fws/drone/flights/minutes?month=",
      "status": "measured: tests.test_ap_n4_f5_10_monthly.F5_10_MonthFilterTest.test_month_param_actually_filters_by_real_month — 이번 달로 좁히면 flight_count>=1, 1999-01 로 좁히면 flight_count=0 실측(drone.py 는 고치지 않았다 · 검증만 새로 했다)"
    },
    {
      "part": "명세가 가리키는 커널/S-20 계량 체계(kernel metering, 예: apps.dsm.metering / common.billing_marks)와의 연계",
      "where": "backend/apps/fws/drone.py 머리말(410행 부근) — \"커널도 새 표도 부르지 않는다\" 명시. backend/common/billing_marks.py·apps/dsm/metering.py 를 호출하는 코드는 F5-10 경로에 없음(grep 결과 무연계)",
      "status": "근사 — flight_minutes_total() 은 F5-08 감사 로그(logger.AuditLogs)를 자체 집계하는 드론 전용 로컬 카운터다. 명세서가 지목한 S-20/metering(커널 계량) 표와 실제로 연결되지 않은 근사 대체 집계이며, 정식 계량 표에는 반영되지 않는다"
    },
    {
      "part": "월 표(완료조건 — 월별 표 형태로 화면/보고서에 반영)",
      "where": "GET /api/fws/ap/drone/flights/minutes/monthly-table · backend/apps/fws/ap_f5.py::flight_minutes_monthly_table() [턴 AP · 차선 N4 신설 — drone.py::flights_mine() 값을 월별로 접는다, drone.py 는 고치지 않았다]",
      "status": "measured: tests.test_ap_n4_f5_10_monthly.F5_10_MonthlyTableTest.test_monthly_table_groups_flights_by_month — 같은 달 기록 둘이 한 행(합계 42.5분·2건)으로 접힘을 실측"
    }
  ]
}
```
