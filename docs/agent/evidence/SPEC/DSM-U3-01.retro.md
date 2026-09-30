# DSM-U3-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U3-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U3-01",
  "title_parts": [
    {
      "part": "역할×유형 문안 표",
      "where": "u36_an_service.M2_PHRASE_TABLE",
      "status": "measured"
    },
    {
      "part": "M2 상단 한 줄",
      "where": "응답 text 칸",
      "status": "부분(서버 응답 GET .../m2-brief 는 실측됐으나 frontend/src 전수 grep 에 m2-brief·m2Brief 호출이 0건이다 — 이 문안을 실제로 띄우는 화면이 없다)"
    },
    {
      "part": "문안 사전 일치",
      "where": "시설+flood → '도로 통제 후 회신' (명세 원문 예시와 문자열 일치)",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 역할×유형 문안 표·문안 사전 일치는 실측 닫힘을 재확인했다. M2 상단 한 줄은 서버 응답만 있고 화면 호출이 0건이다 — 반쪽으로 내린다."
}
```
