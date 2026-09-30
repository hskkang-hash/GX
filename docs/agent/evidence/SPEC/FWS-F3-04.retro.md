# FWS-F3-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-04",
  "title_parts": [
    {
      "part": "1클릭 확인요청 발송",
      "where": "POST .../verification-request(notify_event 재사용)",
      "status": "present"
    },
    {
      "part": "10분 시계",
      "where": "response.deadline_at·timeout_minutes=10",
      "status": "present"
    },
    {
      "part": "가장 가까운 감시원 제안",
      "where": "response.suggested_officers(체크인 위치 하버사인 거리순)",
      "status": "present"
    },
    {
      "part": "가장 가까운 드론 제안",
      "where": "response.suggested_drones",
      "status": "missing — 이 저장소에 드론이 0대라(P-387) 위치 텔레메트리가 없다. 완결조건(발송·10분 시계, §5.3 표)은 위 두 항목으로 충족한다"
    }
  ]
}
```
