# FWS-F3-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-08",
  "title_parts": [
    {
      "part": "진화대 배정",
      "where": "POST .../resource-assignment(kind=crew)",
      "status": "present"
    },
    {
      "part": "차량 배정",
      "where": "POST .../resource-assignment(kind=vehicle)",
      "status": "present"
    },
    {
      "part": "드론 배정",
      "where": "POST .../resource-assignment(kind=drone)",
      "status": "present"
    },
    {
      "part": "임무 문안 자동",
      "where": "response.mission_text(자동 조립) · field_reply 로 F2 도달(재사용)",
      "status": "present"
    }
  ]
}
```
