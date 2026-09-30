# FWS-F4-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-08",
  "title_parts": [
    {
      "part": "상황보고 승인",
      "where": "POST .../hourly-report/approve → 응답 hour",
      "status": "구현 — F3-13 초안(office2.hourly_reports)을 그대로 읽어 승인 실측"
    },
    {
      "part": "발송(완결조건)",
      "where": "응답 notified_count(notify_event 재사용)",
      "status": "구현 — 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-08-approve · fws-f4-08-approvals — API POST /api/fws/command/incidents/{id}/hourly-report/approve · GET /api/fws/command/incidents/{id}/hourly-report/approve",
      "status": "구현 — 화면 배선 · 승인 버튼 → 재조회 approvals(보고 시각·지휘본부 반영)가 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_08_approve_then_reread_approvals · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 상황보고 승인 버튼과 승인 목록을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_08_approve_then_reread_approvals 로 실측했다(F3-13 초안의 시각이 승인 목록에 보임 · 테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
