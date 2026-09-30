# DSM-U4-07 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-07.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-07",
  "title_parts": [
    {
      "part": "수사기관 요청 접수(공문번호·목적·범위)",
      "where": "POST /video-access-requests",
      "status": "있음"
    },
    {
      "part": "승인",
      "where": "POST .../approve",
      "status": "있음"
    },
    {
      "part": "마스킹본 제공(가림 처리)",
      "where": "[턴 AN] provide(image_b64=...) → apps.dsm.privacy_request.mask_jpeg 실제 실행 · 원본≠결과 해시로 확인(VideoAccessMaskingTest)",
      "status": "있음(신규)"
    },
    {
      "part": "개인영상정보 관리대장 자동 기재",
      "where": "GET /video-access-requests(요청→승인→제공 세 단계)",
      "status": "있음"
    },
    {
      "part": "원본 반출 0",
      "where": "함수 어디에도 원본 파일 경로 매개변수가 없다(구조로 보장)",
      "status": "있음"
    },
    {
      "part": "연간 통계(출력)",
      "where": "[턴 AO] GET /video-access-requests/annual-stats · video_access_ledger_service.annual_stats — 같은 감사 이력을 연도로 걸러 요청·승인·제공 건수·월별 요청 건수를 낸다(새 표 0 · VideoAccessAnnualStatsTest)",
      "status": "있음(신규)"
    }
  ]
}
```
