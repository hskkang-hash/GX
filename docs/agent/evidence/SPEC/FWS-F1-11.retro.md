# FWS-F1-11 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-11.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-11",
  "title_parts": [
    {
      "part": "오늘(today) 칸 — 체크인·트랙·순찰함 통과 카운트",
      "where": "backend/apps/fws/patrol.py::mine — GET /api/fws/patrol/mine",
      "status": "measured: F1_11_PatrolMineTest.test_todays_checkin_and_track_are_counted — today.checkins=1, today.tracks=1 실측"
    },
    {
      "part": "주(week) 칸",
      "where": "backend/apps/fws/patrol.py::mine — week_start = today_start - timedelta(주 시작 월요일)",
      "status": "measured: 같은 시험, week.checkins>=1 로 확인(오늘 값을 포함해 최소 1) — 다만 이번 주 중 오늘이 아닌 다른 날짜의 기록이 실제로 week 칸에 누적되는지는 이 시험이 따로 재지 않음(오늘 하루치만 넣고 확인)"
    },
    {
      "part": "화면에 표(일·주 실적)로 보여주는 자리",
      "where": "frontend/src/features/fws — fwsEndpoint.patrolMine 은 api.ts:19에 등록만 되고, 어떤 페이지도 호출하지 않음(grep 결과 0건)",
      "status": "없음: 서버 집계는 실측됐지만 F1 화면 어디에도 내 근무 기록·순찰 실적 표가 없다"
    }
  ]
}
```
