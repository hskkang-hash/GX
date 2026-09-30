# DSM-U4-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-05",
  "title_parts": [
    {
      "part": "재난상황(오늘 발생·등급별·미종결)",
      "where": "GET /api/dsm/daily-report · apps/dsm/u4_daily_report_service.py::daily_report()(apps.dsm.services.recent_events 재사용, 새 질의 없음)",
      "status": "measured: 이 시험 — occurrence_count>=1 실측"
    },
    {
      "part": "통제 현황",
      "where": "u4_daily_report_service.py::daily_report() → control_board_service.daily_reflection() 재사용(턴 AN)",
      "status": "measured: 이 시험 — point_count=1 실측(daily_reflection 값 그대로)"
    },
    {
      "part": "대피(인원·장소)",
      "where": "u4_daily_report_service.py::daily_report() — 통제 지점의 evacuee_count/evacuation_site 합산(control_board_service.py 에 이 턴 구조화 칸(after=)을 더했다)",
      "status": "measured: 이 시험 — evacuee_count_total=3 · evacuation_sites=['만안체육관'] 실측"
    },
    {
      "part": "기상특보",
      "where": "u4_daily_report_service.py::daily_report() — weather_advisory 필드는 항상 None",
      "status": "없음 — 기상청/산림청 특보 수신 API 실연동이 이 저장소에 없다",
      "excluded_by": "P-428",
      "excluded_why": "기상특보 수신은 외부 기관(기상청) API 실연동이다 (WO-19 「외부 실연동은 하지 않는다」)."
    },
    {
      "part": "피해 누계",
      "where": "u4_daily_report_service.py::daily_report() — damage_cumulative 필드는 항상 None",
      "status": "없음 — 이 저장소에 피해(인명·재산) 값을 쥔 구조화 표가 없다(별지 제1호서식은 자유 입력칸, 재조회 가능한 표가 아니다 · incident_report.py 실측). 지어내지 않는다(D-280) — 외부 실연동이 아니라 내부 구조화 표가 없는 코드 결손이라 excluded_by 로 못 막는다."
    },
    {
      "part": "동원(자원 배치)",
      "where": "u4_daily_report_service.py::daily_report() — mobilization 필드는 항상 None",
      "status": "없음 — 동원 인력·장비를 쥔 구조화 표가 이 저장소에 없다. 지어내지 않는다(D-280)."
    },
    {
      "part": "향후 계획",
      "where": "u4_daily_report_service.py::daily_report() — future_plan 필드는 항상 None",
      "status": "없음 — 자유 서술 계획을 쥘 표가 이 저장소에 없다. 지어내지 않는다(D-280)."
    }
  ]
}
```
