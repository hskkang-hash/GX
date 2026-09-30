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
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-12-record · fws-f4-12-attendees · fws-f4-12-decision · fws-f4-12-basis · fws-f4-12-meetings — API POST /api/fws/command/incidents/{id}/meetings · GET /api/fws/command/incidents/{id}/meetings",
      "status": "구현 — 화면 배선 · 참석자·결정·근거 칸과 기록 버튼 → 재조회 이 사건의 회의 목록이 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_12_record_then_reread_meetings · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 회의 기록 칸·버튼과 회의 목록을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_12_record_then_reread_meetings 로 실측했다(테넌트 B 쓰기 404 · 주인 재조회 불변 · DSM 원본 화면 결손은 이 절 밖) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 회의 기록·사건별 구분은 서버에서 실측 닫힘을 재확인했으나 화면 버튼이 없다(DSM 원본의 결손을 재사용이 그대로 물려받았다) — 반쪽으로 내린다."
}
```
