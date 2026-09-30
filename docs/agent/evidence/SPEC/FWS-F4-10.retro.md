# FWS-F4-10 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-10.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-10",
  "title_parts": [
    {
      "part": "신고",
      "where": "F3-06 intake(office.record_intake) → 응답 timeline.reported_at",
      "status": "구현 — 실측"
    },
    {
      "part": "확인",
      "where": "dsm_services.response_clock(DSM 대응 시계 재사용, P-414) → timeline.acknowledged_at",
      "status": "구현 — K1 acknowledged_at 재사용"
    },
    {
      "part": "헬기 투하",
      "where": "F4-04 승인 기록 → timeline.helicopter_dropped_at",
      "status": "구현 — 실측"
    },
    {
      "part": "주불",
      "where": "F4-07 선언 → timeline.main_fire_out_at",
      "status": "구현 — 실측"
    },
    {
      "part": "진화완료",
      "where": "K1 closed_at → timeline.extinguished_at",
      "status": "구현 — 아직 미선언이라 null(정직 — D-284), 다른 시험(F4-07)이 closed 값을 실측한다"
    },
    {
      "part": "골든타임(30분) 초과 사유",
      "where": "응답 golden_time_seconds=1800 · golden_time_exceeded",
      "status": "구현 — office2.GOLDEN_TIME_THRESHOLD_SEC 재사용, 헬기 투하로 false 실측"
    },
    {
      "part": "화면(골든타임 초과 사유 입력·대응시계 타임라인)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-10-timeline · fws-f4-10-golden · fws-f4-10-reason · fws-f4-10-golden-reason — API GET /api/fws/command/incidents/{id}/response-timeline · POST /api/fws/command/incidents/{id}/golden-time-reason",
      "status": "구현 — 화면 배선 · 대응 시계 다섯 칸(신고·확인·헬기 투하·주불·진화완료)을 response-timeline GET 으로 그리고, 사유 기록 버튼 → 재조회에서 초과 표시가 풀리고 기록된 사유가 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_10_reason_then_reread_timeline · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 전용 대응 시계 카드(response-timeline GET)와 골든타임 초과 사유 칸·버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_10_reason_then_reread_timeline 로 실측했다(초과 true → 사유 기록 뒤 false · 테넌트 B 쓰기 404 · 주인 재조회 불변) · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · 6개 시계 칸·골든타임 문턱(선언 30분==설정 1800초)은 서버에서 실측 닫힘을 재확인했다. 다만 골든타임 초과 사유 입력·전용 타임라인 화면은 미배선이다 — 반쪽으로 내린다."
}
```
