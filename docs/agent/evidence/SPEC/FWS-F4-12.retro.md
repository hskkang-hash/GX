# FWS-F4-12 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-12.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-12",
  "title_parts": [
    {
      "part": "회의 기록",
      "where": "POST .../meetings(DSM-U2-03 situation_meeting_service.record_meeting 재사용, 세종 판정 P-414) → 응답 decision",
      "status": "구현 — 실측"
    },
    {
      "part": "사건별 구분(완결조건 '기록')",
      "where": "GET .../meetings → count=1(다른 사건 회의와 안 섞임)",
      "status": "구현 — 두 사건 각각 기록 뒤 섞이지 않음을 실측"
    },
    {
      "part": "화면(버튼)",
      "where": "command.py:631(DSM-U2-03 재사용) — DSM 쪽 원본도 N1 감사(턴 AO)에서 '화면 0'로 이미 지적된 결손이 FWS 재사용에도 그대로 상속된다",
      "status": "없음(미배선)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 회의 기록·사건별 구분은 서버에서 실측 닫힘을 재확인했으나 화면 버튼이 없다(DSM 원본의 결손을 재사용이 그대로 물려받았다) — 반쪽으로 내린다."
}
```
