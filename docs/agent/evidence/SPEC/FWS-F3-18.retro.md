# FWS-F3-18 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-18.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-18",
  "title_parts": [
    {
      "part": "계도·단속 통계",
      "where": "frontend/src/features/fws/pages/OfficeReport.tsx PatrolCard::data-gx=fws-f3-18-since · fws-f3-18-until(기간 칸) · fws-f3-18-stats(계도·단속·합계) · fws-f3-18-record · GET /api/fws/office2/patrol/enforcement/mine?since=&until=(기록 시각 창 · 비우면 전건) · office2.patrol_enforcement_stats",
      "status": "measured: tests.test_aq_n3_screens.FwsF3_18StatsScreenTest — 계도·단속 기록 뒤 오늘 창 재조회 total=2(1·1) · 시작일을 내일로 바꾸면 0 · 창 없으면 2 · 잘못된 날짜 422 · 다른 테넌트 0 · 기록 뒤 재조회 (patrolEnforcementMine 이 이제 화면에서 불린다)"
    },
    {
      "part": "입산통제구역 관리",
      "where": "응답 zones[](set_entry_control_zone·entry_control_zones)",
      "status": "구현 — 같은 테넌트 두 사람이 설정한 구역 2건 모두 조회 실측(다른 테넌트는 0건 실측)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 입산통제구역 관리(zones)는 OfficeReport.tsx 가 실제로 생성 폼을 그려(guidance/enforcement 라디오 버튼) 실측 닫힘을 재확인했다. 계도·단속 통계는 서버 집계는 진짜지만 그 수를 보여주는 화면이 없다(patrolEnforcementMine 죽은 코드) — 반쪽으로 내린다. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 계도·단속 통계를 기관 통계 화면에 기간 칸과 함께 그렸다(기간 바꿈·기록 뒤 재조회)."
}
```
