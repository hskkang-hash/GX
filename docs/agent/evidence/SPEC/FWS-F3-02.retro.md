# FWS-F3-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-02",
  "title_parts": [
    {
      "part": "조심기간 설정",
      "where": "POST/GET .../office/season(kind=dry_season)",
      "status": "present"
    },
    {
      "part": "특별대책기간 설정",
      "where": "POST/GET .../office/season(kind=special_measures)",
      "status": "present"
    },
    {
      "part": "초소 등록",
      "where": "POST/GET .../office/posts(kind=watchpost)",
      "status": "present"
    },
    {
      "part": "순찰 구역 등록",
      "where": "POST/GET .../office/posts(kind=patrol_zone)",
      "status": "present"
    }
  ]
}
```
