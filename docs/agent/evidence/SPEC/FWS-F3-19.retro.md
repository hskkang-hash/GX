# FWS-F3-19 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-19.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-19",
  "title_parts": [
    {
      "part": "가상 사건",
      "where": "요청·응답 drill_mode(DSM 훈련 스위치 재사용 · training.py 와 같은 판단)",
      "status": "구현 — 시작·상태 실측"
    },
    {
      "part": "실채널 0(완결조건 · 첫 증거)",
      "where": "응답 real_channel_sends",
      "status": "구현 — 0 실측(drill_report 가 잰다)"
    },
    {
      "part": "보고서",
      "where": "응답 전체(drill_report)",
      "status": "구현 — 종료 보고서 실측"
    }
  ]
}
```
