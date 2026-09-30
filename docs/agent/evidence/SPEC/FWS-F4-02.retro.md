# FWS-F4-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-02",
  "title_parts": [
    {
      "part": "대응단계 확정·상향",
      "where": "요청 stage → 응답 stage",
      "status": "구현 — 1단계 미설정 상태에서 2단계 확정 실측"
    },
    {
      "part": "사유",
      "where": "요청 reason → 응답 reason",
      "status": "구현 — 감사 사유로 남음(재조회 history 로 확인)"
    },
    {
      "part": "지휘권 이양 기록(시군구→시도)",
      "where": "요청 command_level → 응답 command_level(감사 한 줄 — 세종 판정 P-414, 새 표 0)",
      "status": "구현 — command_level=시도 실측"
    },
    {
      "part": "배지·감사(완결조건)",
      "where": "GET .../stage → history.current",
      "status": "구현 — 재조회로 남는 배지값 실측"
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
