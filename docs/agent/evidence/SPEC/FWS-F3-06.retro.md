# FWS-F3-06 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-06.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-06",
  "title_parts": [
    {
      "part": "신고 출처(119/산림청/시민)",
      "where": "request.source(REPORT_SOURCES 3택)",
      "status": "present"
    },
    {
      "part": "접수 항목(시간·장소·시설·차량진입·화세)",
      "where": "response.{reported_at,facility_note,vehicle_access,fire_intensity}(장소는 사건의 좌표·주소를 그대로 쓴다 — event_detail 재사용)",
      "status": "present"
    },
    {
      "part": "신고 시각 = 30분 시계 시작",
      "where": "response.clock_started_at = reported_at · clock_minutes=30",
      "status": "present"
    }
  ]
}
```
