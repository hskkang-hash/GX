# FWS-F3-07 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-07.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-07",
  "title_parts": [
    {
      "part": "산림청 상황실 통보 기록(042-481-4119)",
      "where": "response.agency_phone(contacts.FOREST_REPORT_NUMBER 재사용) · notified_at",
      "status": "present"
    },
    {
      "part": "헬기 요청 기록(요청시각·기지·도착예정)",
      "where": "response.{helicopter_requested_at,helicopter_base,helicopter_eta}",
      "status": "present"
    }
  ]
}
```
