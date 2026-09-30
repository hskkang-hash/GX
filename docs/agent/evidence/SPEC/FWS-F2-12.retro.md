# FWS-F2-12 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-12.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-12",
  "title_parts": [
    {
      "part": "내 임무 이력(표)",
      "where": "backend/apps/fws/missions.py:mine · GET /api/fws/missions/mine",
      "status": "measured: tests.test_fws_f2.F2_12_MissionsMineTest.test_dispatch_arrive_release_are_counted_in_mine — 출동→도착→철수 뒤 GET, count=1·mission_id 일치 확인(SPEC/FWS-F2-12.json)"
    },
    {
      "part": "투입 시간(duration_minutes/total_minutes)",
      "where": "backend/apps/fws/missions.py:mine (duration_minutes, total_minutes 계산 296-304행)",
      "status": "measured: 같은 시험 — row[\"duration_minutes\"] 가 not None 확인, evidence body 에 total_minutes 도 실림"
    },
    {
      "part": "수당 근거로 쓰일 CSV 내보내기(완결조건 — 명세서 §5.2 167행 「표 · CSV」)",
      "where": "backend/apps/fws/missions.py, backend/apps/fws/api.py — /missions/mine 경로에 대한 CSV 포맷 옵션 없음(grep 결과: fws 앱의 csv 관련 코드는 F6-01 산림청 연계 내보내기·F3-03 근무표 업로드뿐, missions/mine 에는 없음)",
      "status": "없음 — GET /api/fws/missions/mine 은 JSON 만 낸다. backend/apps/fws/api.py:363-383(FWS-F6-01), office.py:339-362(FWS-F3-03) 에만 csv 처리가 있고 F2-12 몫의 CSV 내보내기는 코드에 없다"
    }
  ]
}
```
