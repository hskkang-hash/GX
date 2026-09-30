# FWS-F4-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-03",
  "title_parts": [
    {
      "part": "위치",
      "where": "요청 address(주소 문자열) → 응답 address — 지도 렌더는 §0.4 금지구역 밖이라 주소 문자열로 좁힌다",
      "status": "구현 — 실측"
    },
    {
      "part": "구성",
      "where": "요청 org_composition → 응답 org_composition",
      "status": "구현 — 실측(산림과·소방서·경찰서)"
    },
    {
      "part": "상황보고 반영(완결조건)",
      "where": "F4-08 approve_hourly_report 응답 command_post_reflected",
      "status": "구현 — 지휘소 선언 뒤 매시간 상황보고 승인에 그대로 반영됨을 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx — 조회 카드만 그린다, 이 절에 해당하는 버튼 문구는 copy_command.ts 에 준비돼 있으나 렌더 0건(공통 결손 — F4-01 감사에서 확인)",
      "status": "없음(버튼 미배선 — 서버 상태변화·감사는 실측됐으나 화면에서 누를 자리가 없다)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
