# FWS-F3-17 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-17.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-17",
  "title_parts": [
    {
      "part": "카메라별 오탐률",
      "where": "응답 cameras[].false_alarm_rate_pct",
      "status": "구현 — 100.0 실측(오인 1/판정 1)"
    },
    {
      "part": "안개·소각 등 사유",
      "where": "응답 cameras[].reason_breakdown(verification.FALSE_ALARM_REASONS 재사용)",
      "status": "구현 — fog_or_cloud 1건 실측"
    },
    {
      "part": "임계값 시험(완결조건: 저장)",
      "where": "응답 result·computed_false_alarm_rate_pct(감사에 저장)",
      "status": "구현 — 임계값 50 대비 결과 fail 저장 실측"
    }
  ]
}
```
