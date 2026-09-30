# FWS-F3-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-03",
  "title_parts": [
    {
      "part": "감시원 근무표(CSV)",
      "where": "POST .../office/roster(role=감시원 행)",
      "status": "present"
    },
    {
      "part": "대응단 근무표(CSV)",
      "where": "POST .../office/roster(role=대응단 행)",
      "status": "present"
    },
    {
      "part": "야간 5분대기조",
      "where": "response.rows[].night_standby_5min",
      "status": "present"
    }
  ]
}
```
