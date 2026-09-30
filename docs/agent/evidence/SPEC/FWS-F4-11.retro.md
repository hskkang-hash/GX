# FWS-F4-11 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-11.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-11",
  "title_parts": [
    {
      "part": "야간 전환(일몰)",
      "where": "요청 sunset_at → 응답 is_night",
      "status": "구현 — 과거 일몰 시각으로 야간 전환 실측"
    },
    {
      "part": "헬기 불가",
      "where": "응답 helicopter_badge",
      "status": "구현 — '헬기 불가' 배지 실측"
    },
    {
      "part": "야간 진화 자원 표시(완결조건 '배지')",
      "where": "응답 night_resources[].available_at_night(F3-08 자원배정 재사용)",
      "status": "구현 — 진화대 가능·드론 불가 실측"
    },
    {
      "part": "화면(버튼·조회)",
      "where": "POST .../night-status — 프런트 호출 0건(CommandHome.tsx 에 포함 안 됨)",
      "status": "없음(완전 미배선)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 야간 전환·헬기 불가·야간 자원 표시는 서버에서 실측 닫힘을 재확인했으나 /night-status 를 부르는 화면이 전혀 없다 — 반쪽으로 내린다."
}
```
