# DSM-U5-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U5-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U5-05",
  "title_parts": [
    {
      "part": "CSV 업로드",
      "where": "POST /shifts/import",
      "status": "있음"
    },
    {
      "part": "shifts 저장",
      "where": "감사 이력 대장(재업로드=최근 줄 승)",
      "status": "있음"
    },
    {
      "part": "표(출력)",
      "where": "GET /shifts",
      "status": "있음"
    },
    {
      "part": "근무자 자동 조회(핵심 사실)",
      "where": "[턴 AN] GET /shifts/on-duty · shift_roster_service.current_workers(ShiftOnDutyTest)",
      "status": "있음(신규)"
    },
    {
      "part": "인계 메모 근무자 자동",
      "where": "[턴 AO] handover_service.build_draft() → shift_roster_service.current_workers() — 인계 초안 본문 5번째 줄과 on_duty 칸에 그대로 실린다(새 표 0 · HandoverRosterConnectionTest)",
      "status": "있음(신규)"
    },
    {
      "part": "일지 근무자 자동",
      "where": "backend/apps/dsm/handover_service.py::control_log · backend/apps/dsm/api_u5_an.py::u5an_control_log",
      "status": "measured — 관제일지 = 인계 메모 + 사건 타임라인 합본(새 표 0 · P-421 ② · 턴 AP N3): handover_service.control_log() 가 build_draft()(인계 메모)와 services.recent_events/response_clock(사건 타임라인, UX-14 공개 면 재사용)을 한 응답에 묶는다. 문: GET /api/dsm/u5an/control-log. 시험: tests.test_ap_n3_u5_05_control_log.ControlLogTest.test_control_log_combines_handover_and_incident_timeline"
    },
    {
      "part": "완결조건 「일지 근무자 = 편성표」",
      "where": "backend/apps/dsm/handover_service.py::control_log",
      "status": "measured — 일지 근무자(control_log().on_duty) == 편성표(shift_roster_service.current_workers()) 를 HTTP 응답에서 실측 대조(항등 — 같은 호출 하나를 옮겨 쓸 뿐 다른 값을 낼 길이 없다). 인계 메모의 on_duty 와도 일치(두 벌로 안 센다). 시험: tests.test_ap_n3_u5_05_control_log.ControlLogTest.test_control_log_combines_handover_and_incident_timeline"
    }
  ],
  "retro": "P-421 채움 · 관제일지(인계 메모 + 사건 타임라인) · 턴 AP 차선 N3"
}
```
