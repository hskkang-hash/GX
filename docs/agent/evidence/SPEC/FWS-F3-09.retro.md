# FWS-F3-09 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-09.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-09",
  "title_parts": [
    {
      "part": "면적 입력",
      "where": "request.area_ha",
      "status": "present"
    },
    {
      "part": "풍속 입력",
      "where": "request.wind_mps",
      "status": "present"
    },
    {
      "part": "시설 우려 입력",
      "where": "request.buildings_at_risk",
      "status": "present"
    },
    {
      "part": "단계 제안",
      "where": "response.proposed_stage(constants.compute_fire_stage 재사용)",
      "status": "present"
    },
    {
      "part": "F4 확정 요청",
      "where": "response.status=pending_f4_confirmation · f4_notified_count(notify_event 재사용)",
      "status": "present"
    }
  ]
}
```
