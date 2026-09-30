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
      "where": "backend/apps/fws/missions.py::mine_csv(mine() 값을 그대로 옮김 · 마지막 줄 total) · backend/apps/fws/api.py::my_missions_export — GET /api/fws/missions/mine/export(text/csv) · 화면 frontend/src/features/fws/pages/FieldHome.tsx::data-gx=\"fws-f2-12-csv\"(내려받은 뒤 reload) · \"fws-f2-12-table\" · \"fws-f2-12-total\" · api_w2a.ts::downloadMyMissionsCsv",
      "status": "measured: tests.test_aq_w2a_field_screens.F2_12_CsvScreenTest.test_export_matches_mine_after_release — 출동→도착→철수 뒤 CSV 머리줄 6칸·임무 줄·total 줄이 새 GET /missions/mine 의 count·total_minutes 와 같다 · 격리 test_other_tenant_export_has_no_rows_of_mine · 화면 정적 대조 test_screen_has_csv_button"
    }
  ],
  "retro": "턴 AQ 차선 W2A · 화면 배선 · 사람 확인 — 수당 근거 CSV 문을 더하고 진화대 화면 이력 칸에 내려받기 버튼을 달았다(누른 뒤 이력 재조회)"
}
```
