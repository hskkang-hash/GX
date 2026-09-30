# DSM-U3-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U3-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U3-02",
  "title_parts": [
    {
      "part": "통제 완료 버튼",
      "where": "POST /controls/{id}/executed",
      "status": "measured"
    },
    {
      "part": "시각 기록",
      "where": "advance() 감사 줄(occurred_at)",
      "status": "measured"
    },
    {
      "part": "통제 현황판 반영",
      "where": "frontend/src/features/dsm/components/ControlPointsBoard.tsx(관제 대시보드 ControlDashboard.tsx 아래에 붙음)::data-gx=dsm-u3-02-create(기준 도달 기록) · dsm-u3-02-decide(통제 결정) · dsm-u3-02-executed(통제 완료 → POST /api/dsm/controls/{id}/executed) · dsm-u3-02-release(해제) · dsm-u3-02-board(표) · 재조회 GET /api/dsm/control-points",
      "status": "measured: tests.test_aq_n3_screens.DsmU3_02ScreenTest.test_each_press_then_board_refetch_shows_new_stage — 누를 때마다 현황판 GET 재조회에서 도달→결정→실행→해제로 바뀜 · 결정 전 통제 완료 409 · 다른 테넌트 표에 없음·실행 404. 표에는 단계와 도달 시각(지점 글)을 보이고, 단계별 시각 열은 서버 현황판 응답에 없어 그리지 않았다(감사 줄에는 남는다)"
    },
    {
      "part": "도달→결정→실행 3시각",
      "where": "create_point→advance(결정)→POST /controls/{id}/executed 순서 검사",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 통제 완료 버튼·시각 기록·도달→결정→실행 3시각은 실측 닫힘을 재확인했다. 통제 현황판 반영은 서버 응답만 있고 그 화면이 없다(ControlDashboard.tsx 는 동명이지만 다른 절) — 반쪽으로 내린다. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 통제 지점 표를 관제 대시보드에 그리고 네 누름을 배선했다(누른 뒤 현황판 재조회)."
}
```
