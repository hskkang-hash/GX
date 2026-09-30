# FWS-F4-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-04",
  "title_parts": [
    {
      "part": "헬기 요청 승인",
      "where": "POST .../aircraft-request(F6-05 integration.request_helicopter 재사용) → 응답 request_id",
      "status": "구현 — 실측"
    },
    {
      "part": "투하 구역 지정",
      "where": "요청 drop_zone_lat/lng → 응답 drop_zone",
      "status": "구현 — 좌표 실측"
    },
    {
      "part": "30분 시계(완결조건)",
      "where": "응답 deadline_at·timeout_minutes=30",
      "status": "구현 — office2.GOLDEN_TIME_THRESHOLD_SEC 재사용 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-04-approve · fws-f4-04-org · fws-f4-04-lat · fws-f4-04-lng · fws-f4-04-base · fws-f4-04-eta · fws-f4-04-latest — API POST /api/fws/command/incidents/{id}/aircraft-request · GET /api/fws/command/incidents/{id}/aircraft-request",
      "status": "구현 — 화면 배선 · 승인 버튼 → 재조회 approvals 의 투하구역 좌표·30분 시계 마감이 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_04_approve_then_reread_drop_zone_and_clock · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 요청 기관·투하구역 좌표 칸과 승인 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_04_approve_then_reread_drop_zone_and_clock 로 실측했다(테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
