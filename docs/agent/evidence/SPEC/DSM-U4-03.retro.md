# DSM-U4-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-03",
  "title_parts": [
    {
      "part": "유형·구역 선택",
      "where": "create_draft(kind, region)",
      "status": "있음"
    },
    {
      "part": "표준 문안(자동 생성)",
      "where": "[턴 AN] u4_regulations.CBS_STANDARD_TEMPLATE · message 를 비우면 create_draft 가 자동으로 채운다(CbsDraftStandardTemplateTest)",
      "status": "있음(신규)"
    },
    {
      "part": "글자 수 검사(90/157)",
      "where": "u4_regulations.CBS_LEN_LIMIT",
      "status": "있음"
    },
    {
      "part": "승인권자 결재 요청",
      "where": "POST /cbs-drafts/{id}/approve",
      "status": "있음"
    },
    {
      "part": "발송은 행안부 시스템(이 제품은 안 함)",
      "where": "발송 버튼 없음 — 명세 그대로",
      "status": "있음(설계로 보장)"
    },
    {
      "part": "발송 기록",
      "where": "POST /cbs-drafts/{id}/sent",
      "status": "있음"
    },
    {
      "part": "야간(21~06시) 안전안내 경고",
      "where": "night_warning 플래그",
      "status": "있음"
    }
  ]
}
```
