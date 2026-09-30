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
      "where": "GET /control-points 지점 행 stage",
      "status": "부분(GET /control-points 서버 응답은 실측됐으나 frontend/src 전수 grep 에 control-points·controlPoints 호출이 0건이다. frontend/src/features/dsm/pages/ControlDashboard.tsx 는 이름이 비슷할 뿐 F-09 관제 대시보드(카메라·5상태)로 다른 절이다 — 이 절의 통제 현황판 화면은 없다)"
    },
    {
      "part": "도달→결정→실행 3시각",
      "where": "create_point→advance(결정)→POST /controls/{id}/executed 순서 검사",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 통제 완료 버튼·시각 기록·도달→결정→실행 3시각은 실측 닫힘을 재확인했다. 통제 현황판 반영은 서버 응답만 있고 그 화면이 없다(ControlDashboard.tsx 는 동명이지만 다른 절) — 반쪽으로 내린다."
}
```
