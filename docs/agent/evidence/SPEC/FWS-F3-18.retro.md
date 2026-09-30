# FWS-F3-18 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-18.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-18",
  "title_parts": [
    {
      "part": "계도·단속 통계",
      "where": "응답 by_kind·total(patrol_enforcement_stats)",
      "status": "부분(guidance 1건·enforcement 1건 → total=2 서버 실측은 진짜지만 화면 표시가 없다 — frontend/src/features/fws/pages/OfficeReport.tsx 의 patrolEnforcementMine 상수는 정의만 되고 호출 0건이다)"
    },
    {
      "part": "입산통제구역 관리",
      "where": "응답 zones[](set_entry_control_zone·entry_control_zones)",
      "status": "구현 — 같은 테넌트 두 사람이 설정한 구역 2건 모두 조회 실측(다른 테넌트는 0건 실측)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 입산통제구역 관리(zones)는 OfficeReport.tsx 가 실제로 생성 폼을 그려(guidance/enforcement 라디오 버튼) 실측 닫힘을 재확인했다. 계도·단속 통계는 서버 집계는 진짜지만 그 수를 보여주는 화면이 없다(patrolEnforcementMine 죽은 코드) — 반쪽으로 내린다."
}
```
