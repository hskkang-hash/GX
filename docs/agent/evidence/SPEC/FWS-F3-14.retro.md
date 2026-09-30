# FWS-F3-14 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-14.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-14",
  "title_parts": [
    {
      "part": "산불정보ID",
      "where": "응답 items[key=fire_info_id]",
      "status": "구현 — 미기재 시 FWS-{event_id} 자동 부여 실측"
    },
    {
      "part": "원인",
      "where": "요청 cause(5택: 입산자실화·소각·담뱃불·건축물화재·기타 · annex FF-7) → 응답 그대로",
      "status": "구현 — '소각' 실측"
    },
    {
      "part": "면적",
      "where": "요청 area_ha → 응답 그대로",
      "status": "구현 — 12.3ha 실측"
    },
    {
      "part": "문자전송 여부",
      "where": "요청 sms_sent → 응답 그대로",
      "status": "구현 — true 실측"
    },
    {
      "part": "일출몰",
      "where": "요청 sunrise·sunset → 응답 그대로",
      "status": "구현 — 06:32/18:07 실측(수동 입력 — 천문 계산 API 미연동)"
    },
    {
      "part": "항목 1:1(완결조건)",
      "where": "응답 items 6칸",
      "status": "구현 — KFS_EXPORT_FIELDS 와 같은 형으로 6항목 1:1 실측"
    }
  ]
}
```
