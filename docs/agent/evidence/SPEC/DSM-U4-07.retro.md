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
    },
    {
      "part": "화면 — 대장 표 · 연간 통계(완결조건)",
      "where": "frontend/src/features/dsm/components/VideoAccessLedgerPanel.tsx(보고서 화면 Reports.tsx 에 붙음)::data-gx=dsm-u4-07-create(요청 접수 · 공문번호·목적·범위) · dsm-u4-07-approve · dsm-u4-07-provide(마스킹본) · dsm-u4-07-ledger(대장 표) · dsm-u4-07-year(연도 칸) · dsm-u4-07-stats · GET /api/dsm/video-access-requests · GET /api/dsm/video-access-requests/annual-stats?year=",
      "status": "measured: tests.test_aq_n3_screens.DsmU4_07_08ScreenTest.test_ledger_presses_then_ledger_and_stats_refetch — 접수→승인→제공 누를 때마다 대장 GET 재조회에서 상태 요청→승인→제공 · 연간 통계 재조회에서 요청·승인·제공이 각각 +1 · 연도 칸을 전년으로 바꾸면 0 · 다른 테넌트 대장·통계 0"
    }
  ],
  "retro": "턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 대장 표·연간 통계 화면이 없던 결손(N1 재판정 §1)을 보고서 화면에 그려 닫았다."
}
```
