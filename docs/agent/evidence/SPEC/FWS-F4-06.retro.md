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
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-06-record · fws-f4-06-agency · fws-f4-06-detail · fws-f4-06-records — API POST /api/fws/command/incidents/{id}/agency-request · GET /api/fws/command/incidents/{id}/agency-request",
      "status": "구현 — 화면 배선 · 기관(소방·경찰·군) 고르고 요청 기록 버튼 → 재조회 records 목록이 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_06_record_then_reread_records · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 기관 선택·요청 내용 칸과 요청 기록 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_06_record_then_reread_records 로 실측했다(세 기관 3건 · 테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
