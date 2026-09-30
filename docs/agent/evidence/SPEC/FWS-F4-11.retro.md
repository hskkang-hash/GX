# FWS-F4-11 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-11.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-11",
  "title_parts": [
    {
      "part": "야간 전환(일몰)",
      "where": "요청 sunset_at → 응답 is_night",
      "status": "구현 — 과거 일몰 시각으로 야간 전환 실측"
    },
    {
      "part": "헬기 불가",
      "where": "응답 helicopter_badge",
      "status": "구현 — '헬기 불가' 배지 실측"
    },
    {
      "part": "야간 진화 자원 표시(완결조건 '배지')",
      "where": "응답 night_resources[].available_at_night(F3-08 자원배정 재사용)",
      "status": "구현 — 진화대 가능·드론 불가 실측"
    },
    {
      "part": "화면(버튼·조회)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-11-sunset · fws-f4-11-sunset-at · fws-f4-11-badge · fws-f4-11-resources — API POST /api/fws/command/incidents/{id}/sunset · GET /api/fws/command/incidents/{id}/night-status",
      "status": "구현 — 화면 배선 · 일몰 시각 기록 버튼 → 재조회 야간·헬기 불가 배지와 자원별 야간 가능/불가가 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_11_sunset_then_reread_night_badge(화면 칸이 보내는 datetime-local 모양 그대로) · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 일몰 시각 칸·기록 버튼과 night-status 배지·자원 목록을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_11_sunset_then_reread_night_badge 로 실측했다(진화대 가능·드론 불가 · 테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 야간 전환·헬기 불가·야간 자원 표시는 서버에서 실측 닫힘을 재확인했으나 /night-status 를 부르는 화면이 전혀 없다 — 반쪽으로 내린다."
}
```
