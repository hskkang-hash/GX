# FWS-F4-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-01",
  "title_parts": [
    {
      "part": "사건 1건",
      "where": "GET .../command → 응답 event_id·incident",
      "status": "구현 — 실측"
    },
    {
      "part": "단계",
      "where": "응답 stage(F4-02 재사용)",
      "status": "구현 — 2단계 실측"
    },
    {
      "part": "자원",
      "where": "응답 resources(F3-08 재사용)",
      "status": "구현 — 1건 실측"
    },
    {
      "part": "시계",
      "where": "응답 response_clock(F4-10 재사용)",
      "status": "구현 — 실측"
    },
    {
      "part": "대피",
      "where": "응답 evacuation(F3-11 재사용)",
      "status": "구현 — 1개 마을 실측"
    },
    {
      "part": "한 화면(완결조건)",
      "where": "GET /command/incidents/{id}/command 응답 하나에 위 다섯이 함께 실린다",
      "status": "부분(단일 응답으로 실측했으나 지도·화선 렌더는 제외됐다 — §0.4 금지구역 밖·화선 데이터 자체가 저장소에 없음. excluded_by 번호 없이 프로즈로만 뺀 것이라 P-406 상 여전히 열린 행이다)"
    },
    {
      "part": "지도(명사 부분)",
      "where": "(없음)",
      "status": "없음(§0.4 금지구역 밖으로 제외 — 지도 렌더 자체가 이 절 계약에서 빠졌다, excluded_by 번호 없음)"
    },
    {
      "part": "화선(명사 부분)",
      "where": "(없음)",
      "status": "없음(화선 데이터가 이 저장소에 없다 — F3-10 확산예측 미착수, excluded_by 번호 없음)"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-01-load · fws-f4-01-screen(+ 같은 화면의 fws-f4-02~12·15 버튼) — API GET /api/fws/command/incidents/{id}/command",
      "status": "구현 — 화면 배선 · 사건 개요·단계·지휘본부·자원·대피를 한 카드에 그리고 그 아래 절별 버튼을 같은 화면에 배선, 누를 때마다 이 GET 을 다시 부른다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_01_screen_rereads_stage_and_post_after_press · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 한 화면 카드와 절별 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_01_screen_rereads_stage_and_post_after_press 로 실측했다 · 남은 열린 행: 한 화면(완결조건 — 지도·화선 없이 그린다) · 지도 · 화선(결정 번호 없음 — §3 상 excluded_by 로 뺄 수 있는 범주(운영 집행·외부 실연동)도 아니다) — 반쪽 유지 · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 명사 부분 6개 중 지도·화선 2개가 excluded_by 없이 조용히 빠졌고, 완결조건(한 화면)도 버튼이 아니라 조회 카드뿐이다 — 반쪽으로 내린다."
}
```
