# FWS-F3-12 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-12.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-12",
  "title_parts": [
    {
      "part": "마을별 완료",
      "where": "요청 completed → 응답 villages[].completed",
      "status": "구현 — 동리 완료 · 서리 미완료 실측"
    },
    {
      "part": "잔류자",
      "where": "요청 remaining_residents → 응답 remaining_residents_total",
      "status": "구현 — 3명 실측"
    },
    {
      "part": "요양시설",
      "where": "요청 care_facility_cleared → 응답 care_facilities_open",
      "status": "구현 — 미해제 1건 실측"
    },
    {
      "part": "이행 %(완결조건)",
      "where": "응답 percent_complete",
      "status": "구현 — 50.0 실측(2곳 중 1곳 완료)"
    }
  ]
}
```
