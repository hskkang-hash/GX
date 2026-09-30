# FWS-F4-07 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-07.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-07",
  "title_parts": [
    {
      "part": "주불 진화 선언",
      "where": "POST .../main-fire-out → 감사 한 줄(K1 에 없는 칸이라 App 층 선언, D-284)",
      "status": "구현 — 실측"
    },
    {
      "part": "진화완료 선언",
      "where": "POST .../extinguished → 응답 response_state",
      "status": "구현 — 실측"
    },
    {
      "part": "종결 축(완결조건)",
      "where": "dsm_services.advance_response(K1 closed) 재사용 — 응답 response_state=closed",
      "status": "구현 — K1 종결 축을 실제로 옮긴 것을 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-07-main-out · fws-f4-07-extinguished · fws-f4-07-reason · fws-f4-07-declarations — API POST /api/fws/command/incidents/{id}/main-fire-out · POST /api/fws/command/incidents/{id}/extinguished · GET /api/fws/command/incidents/{id}/fire-declarations · GET /api/fws/command/incidents/{id}/command",
      "status": "구현 — 화면 배선 · 주불 진화 선언·진화완료 선언 버튼 → 재조회 선언 시각과 대응 상태(closed)가 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_07_declare_then_reread_declarations_and_state · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 주불·진화완료 선언 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_07_declare_then_reread_declarations_and_state 로 실측했다(종결 축 closed 가 지휘 화면 GET 에 보임 · 테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
