# FWS-F4-06 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-06.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-06",
  "title_parts": [
    {
      "part": "소방 협조 요청 기록",
      "where": "agency=fire_department 실측",
      "status": "구현 — 실측"
    },
    {
      "part": "경찰 협조 요청 기록",
      "where": "agency=police 실측",
      "status": "구현 — 실측"
    },
    {
      "part": "군 협조 요청 기록",
      "where": "agency=military 실측",
      "status": "구현 — 실측"
    },
    {
      "part": "기록(완결조건)",
      "where": "GET .../agency-request → count=3",
      "status": "구현 — 재조회로 3건 확인"
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
