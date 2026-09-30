# FWS-F3-11 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-11.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-11",
  "title_parts": [
    {
      "part": "대상 마을",
      "where": "요청 villages_json 목록 → 응답 drafts[].village",
      "status": "구현 — 실측 2건"
    },
    {
      "part": "대피소",
      "where": "요청 villages_json.shelter → 응답 drafts[].shelter",
      "status": "구현 — 실측 2건"
    },
    {
      "part": "문안(CBS 90/157자)",
      "where": "응답 drafts[].short/long (F6-07 integration.draft_evacuation_notice 재사용)",
      "status": "구현 — 90/157자 상한 실측"
    },
    {
      "part": "마을방송문",
      "where": "drafts[].long — annex 가 CBS 문안과 마을방송문을 같은 문안으로 대안(§5.1 F6-07 대안)",
      "status": "F6-07 대안 그대로 — 별도 필드 없음(문안 공용)"
    },
    {
      "part": "앱 푸시",
      "where": "해당 없음",
      "status": "[미확인] — 산림청 스마트산림재난 앱 연동은 F6-07 이 이미 범위 밖으로 남겼다(외부 자격증명 필요) · 이 절도 같은 한계를 물려받는다"
    },
    {
      "part": "F4 승인 요청",
      "where": "응답 status=pending_f4_approval",
      "status": "구현 — 승인 대기 상태로 남는다(F4 확정은 F4 담당 몫)"
    }
  ]
}
```
