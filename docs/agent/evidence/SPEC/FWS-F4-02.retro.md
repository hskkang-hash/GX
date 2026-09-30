# FWS-F4-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-02",
  "title_parts": [
    {
      "part": "대응단계 확정·상향",
      "where": "요청 stage → 응답 stage",
      "status": "구현 — 1단계 미설정 상태에서 2단계 확정 실측"
    },
    {
      "part": "사유",
      "where": "요청 reason → 응답 reason",
      "status": "구현 — 감사 사유로 남음(재조회 history 로 확인)"
    },
    {
      "part": "지휘권 이양 기록(시군구→시도)",
      "where": "요청 command_level → 응답 command_level(감사 한 줄 — 세종 판정 P-414, 새 표 0)",
      "status": "구현 — command_level=시도 실측"
    },
    {
      "part": "배지·감사(완결조건)",
      "where": "GET .../stage → history.current",
      "status": "구현 — 재조회로 남는 배지값 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-02-confirm · fws-f4-02-stage · fws-f4-02-command-level · fws-f4-02-reason · fws-f4-02-current — API POST /api/fws/command/incidents/{id}/stage · GET /api/fws/command/incidents/{id}/stage",
      "status": "구현 — 화면 배선 · 확정 버튼 → 재조회 current(단계·이전 단계·지휘 수준 배지·사유·기록 건수)가 바뀐 값으로 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_02_confirm_then_reread_stage · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 확정·상향·지휘권 이양 칸과 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_02_confirm_then_reread_stage 로 실측했다(테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 서버 로직은 실측 닫힘을 재확인했으나 화면 버튼이 미배선이다 — 반쪽으로 내린다."
}
```
