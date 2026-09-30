# FWS-U5-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-U5-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-U5-04",
  "title_parts": [
    {
      "part": "등급별 수신",
      "where": "severities/rules",
      "status": "measured"
    },
    {
      "part": "진화대",
      "where": "role_suggestions[fws_response_team]",
      "status": "measured"
    },
    {
      "part": "산림과",
      "where": "role_suggestions[fws_forestry_dept]",
      "status": "measured"
    },
    {
      "part": "지휘",
      "where": "role_suggestions[fws_command]",
      "status": "measured"
    },
    {
      "part": "산림청",
      "where": "role_suggestions[fws_kfs_liaison]",
      "status": "measured"
    },
    {
      "part": "야간 5분대기조 채널",
      "where": "night_standby_zone",
      "status": "measured"
    }
  ]
}
```
