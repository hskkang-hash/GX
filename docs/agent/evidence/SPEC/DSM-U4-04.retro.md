# DSM-U4-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-04",
  "title_parts": [
    {
      "part": "통제 개소 등록",
      "where": "POST /control-points",
      "status": "있음"
    },
    {
      "part": "도달·결정·실행·해제 4시각",
      "where": "u4_regulations.CONTROL_STAGE_ORDER · advance()",
      "status": "있음"
    },
    {
      "part": "대피 인원·장소",
      "where": "evacuee_count · evacuation_site",
      "status": "있음"
    },
    {
      "part": "현황판(출력)",
      "where": "GET /control-points",
      "status": "있음"
    },
    {
      "part": "일일보고 자동 반영",
      "where": "[턴 AN] GET /control-points/daily-report · control_board_service.daily_reflection(ControlBoardDailyReportTest)",
      "status": "있음(신규)"
    },
    {
      "part": "controls 모델(처리)",
      "where": "감사 이력 대장(새 표 0 — AppStaysThinTest 와 같은 원칙)",
      "status": "있음(다른 모양 — 완결조건과 무관)"
    }
  ]
}
```
