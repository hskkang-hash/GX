# DSM-U2-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U2-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U2-05",
  "title_parts": [
    {
      "part": "인계 메모(선행 조건) 자동 초안·저장",
      "where": "backend/apps/dsm/handover_service.py::build_draft / save (UX-34, 이전 턴 구현)",
      "status": "measured — 이 턴 이전부터 존재, DsmHandover 행으로 저장됨(evidence latest_after_ack.body 에서 자동 초안 문구 확인)"
    },
    {
      "part": "특정 시간대(08~09시) 인계 창",
      "where": "backend/apps/dsm/handover_service.py::HANDOVER_WINDOW_START_HOUR=8 · HANDOVER_WINDOW_END_HOUR=9(명세 §4.2 84행 원문 숫자) · handover_window() → GET /api/dsm/handover/latest 의 handover_window · acknowledge() 감사 줄에 「인계 창 08:00~09:00 안/밖」 · 화면 frontend/src/features/dsm/components/HandoverAckCard.tsx::data-gx=dsm-u2-05-window",
      "status": "measured: tests.test_aq_w2b_dsm_screens.HandoverAckScreenTest.test_window_bounds_are_the_spec_hours(08:30 안 · 07:59·09:00 밖 — 서버 현지 시각 settings.TIME_ZONE) · test_ack_then_refetch_shows_check_and_window(재조회 응답에 창 08:00~09:00 · 확인 감사 문장에 창 안/밖). 창 밖 확인은 막지 않고 「밖」으로 남긴다 — 명세는 관행 시간대를 적었지 거절을 요구하지 않는다"
    },
    {
      "part": "팀장이 「확인」 체크(ack)",
      "where": "backend/apps/dsm/handover_service.py::acknowledge (POST /api/dsm/handover/{id}/ack)",
      "status": "measured: evidence — ack 후 latest().acknowledged 가 true 로 바뀌는 것을 같은 시험에서 재확인(test_p356_u2_spec_promotions.py)"
    },
    {
      "part": "홈 카드 「인계 확인 ✓」 UI",
      "where": "frontend/src/features/dsm/components/HandoverAckCard.tsx::data-gx=dsm-u2-05-card · dsm-u2-05-ack(「인계 확인」 버튼) · dsm-u2-05-acked(「인계 확인 ✓」) — 팀장(U2) 홈 pages/Home.tsx 의 DecisionHandoverRow · POST /api/dsm/handover/{id}/ack → GET /api/dsm/handover/latest",
      "status": "measured: tests.test_aq_w2b_dsm_screens.HandoverAckScreenTest.test_ack_then_refetch_shows_check_and_window — 누르기 전 acknowledged=false · 누른 뒤 같은 GET 재조회 acknowledged=true(카드가 ✓ 로 바뀜) · 남의 테넌트 인계는 내 카드에 안 옴 · ScreenStaticTest(data-gx 글자 대조)"
    },
    {
      "part": "완결 조건 「감사」",
      "where": "backend/apps/dsm/handover_service.py::acknowledge → audit_writer.write(logger_name=_ACK_LOGGER_NAME)",
      "status": "measured: ack 마다 audit_writer 감사 줄 1건(evidence ack_id=397)"
    }
  ],
  "retro": "턴 AQ 차선 W2B · 화면 배선 · 사람 확인 · 2026-09-30 · 팀장 홈에 「인계 확인 ✓」 카드 + 명세 원문 08~09시 인계 창(표시·감사) · 누른 뒤 GET /handover/latest 재조회."
}
```
