# FWS-F3-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-01",
  "title_parts": [
    {
      "part": "위험지수",
      "where": "response.risk_index(F1-03 재사용)",
      "status": "present"
    },
    {
      "part": "위기경보",
      "where": "response.fire_alert(F1-03 재사용)",
      "status": "present"
    },
    {
      "part": "초소 근무",
      "where": "response.post_duty(오늘 체크인 집계)",
      "status": "present"
    },
    {
      "part": "카메라 정상",
      "where": "response.camera_status(UX-23 camera_pulse 재사용)",
      "status": "present"
    },
    {
      "part": "진행 사건",
      "where": "response.ongoing_incidents(F-09 recent_events 재사용)",
      "status": "present"
    },
    {
      "part": "자원 대기",
      "where": "response.resource_standby(F2-01 standby 집계)",
      "status": "present"
    }
  ]
}
```
