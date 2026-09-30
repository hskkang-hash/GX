# FWS-F3-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-05",
  "title_parts": [
    {
      "part": "오인 종결(사유)",
      "where": "POST .../verifications/{id}/reply(result=false_alarm, reason_code=5택 · F1-06 재사용)",
      "status": "present"
    },
    {
      "part": "산불 확정",
      "where": "POST .../verifications/{id}/reply(result=fire_confirmed · F1-06 재사용)",
      "status": "present"
    }
  ]
}
```
