# FWS-F4-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-03",
  "title_parts": [
    {
      "part": "위치",
      "where": "요청 address(주소 문자열) → 응답 address — 지도 렌더는 §0.4 금지구역 밖이라 주소 문자열로 좁힌다",
      "status": "구현 — 실측"
    },
    {
      "part": "구성",
      "where": "요청 org_composition → 응답 org_composition",
      "status": "구현 — 실측(산림과·소방서·경찰서)"
    },
    {
      "part": "상황보고 반영(완결조건)",
      "where": "F4-08 approve_hourly_report 응답 command_post_reflected",
      "status": "구현 — 지휘소 선언 뒤 매시간 상황보고 승인에 그대로 반영됨을 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-03-declare · fws-f4-03-address · fws-f4-03-org · fws-f4-03-phone · fws-f4-03-current — API POST /api/fws/command/incidents/{id}/command-post · GET /api/fws/command/incidents/{id}/command-post",
      "status": "구현 — 화면 배선 · 설치 선언 버튼 → 재조회 post(위치·구성·상황실 번호)가 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_03_declare_then_reread_post · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 위치·구성 칸과 설치 선언 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_03_declare_then_reread_post 로 실측했다(테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
