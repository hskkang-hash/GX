# FWS-F4-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-01",
  "title_parts": [
    {
      "part": "사건 1건",
      "where": "GET .../command → 응답 event_id·incident",
      "status": "구현 — 실측"
    },
    {
      "part": "단계",
      "where": "응답 stage(F4-02 재사용)",
      "status": "구현 — 2단계 실측"
    },
    {
      "part": "자원",
      "where": "응답 resources(F3-08 재사용)",
      "status": "구현 — 1건 실측"
    },
    {
      "part": "시계",
      "where": "응답 response_clock(F4-10 재사용)",
      "status": "구현 — 실측"
    },
    {
      "part": "대피",
      "where": "응답 evacuation(F3-11 재사용)",
      "status": "구현 — 1개 마을 실측"
    },
    {
      "part": "한 화면(완결조건)",
      "where": "GET /command/incidents/{id}/command 응답 하나에 위 다섯이 함께 실린다",
      "status": "부분(단일 응답으로 실측했으나 지도·화선 렌더는 제외됐다 — §0.4 금지구역 밖·화선 데이터 자체가 저장소에 없음. excluded_by 번호 없이 프로즈로만 뺀 것이라 P-406 상 여전히 열린 행이다)"
    },
    {
      "part": "지도(명사 부분)",
      "where": "(없음)",
      "status": "없음(§0.4 금지구역 밖으로 제외 — 지도 렌더 자체가 이 절 계약에서 빠졌다, excluded_by 번호 없음)"
    },
    {
      "part": "화선(명사 부분)",
      "where": "(없음)",
      "status": "없음(화선 데이터가 이 저장소에 없다 — F3-10 확산예측 미착수, excluded_by 번호 없음)"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx(169줄) — copy_command.ts 의 버튼 문구(stage·commandPost·aircraft·evacuation·agency·fireDeclaration·hourlyReport·night·meeting·postReport)는 준비돼 있으나 렌더 0건, 조회 카드만 그린다(파일 자신의 머리말도 자백)",
      "status": "없음(버튼 미배선 — 서버 상태변화는 실측됐으나 화면에서 누를 자리가 없다)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 명사 부분 6개 중 지도·화선 2개가 excluded_by 없이 조용히 빠졌고, 완결조건(한 화면)도 버튼이 아니라 조회 카드뿐이다 — 반쪽으로 내린다."
}
```
