# FWS-F6-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-02",
  "title_parts": [
    {
      "part": "웹훅 이벤트 종류 4개 카탈로그(fws.fire.confirmed/stage_changed/evacuation_ordered/extinguished)",
      "where": "backend/apps/fws/integration.py::FWS_WEBHOOK_EVENT_TYPES, webhook_event_catalog (GET /api/fws/liaison/webhook-events/catalog)",
      "status": "있음 — 네 이름 전부 카탈로그에 있다 · test_catalog_lists_the_four_annex_kinds 실측"
    },
    {
      "part": "CAP 1.2 로 실제 발송",
      "where": "backend/apps/fws/integration.py::notify_fws_event → apps.dsm.services.notify_event → backend/common/webhook_outbox.py::dispatch_event (POST /api/fws/liaison/fire-events/{id}/webhook-notify)",
      "status": "있음 — 새 발신 경로가 아니라 기존 UX-19 dispatch_event(CAP 1.2)를 재사용한다, _post 만 몽키패치해 실제 호출 경로는 그대로 탄다"
    },
    {
      "part": "소방·시도 상황실 수신 200(완결조건)",
      "where": "backend/tests/test_fws_f6.py::F6_02_WebhookEventsTest.test_notify_reaches_a_subscribed_situation_room_with_200",
      "status": "있음 — register_webhook_subscription 으로 구독 등록 후 실제 POST 로 webhook_deliveries==webhook_succeeded(>=1) 를 실측(200 수신)"
    },
    {
      "part": "이 네 이름으로 구독을 걸러 받는 필터(종류별 필터)",
      "where": "backend/common/webhook_outbox.py::_passes_filter (line 292-309) — event.event_type 은 K1 DetectionEvent 의 닫힌 열거값(fire/smoke/... )일 뿐, fws.fire.confirmed 같은 문자열이 아니다",
      "status": "없음 — kind(fws.fire.confirmed 등)는 발신 시점의 선언·FWS 자기 감사 라벨일 뿐, 실제 구독 필터는 여전히 K1 event_type 기준이라 이 네 이름으로는 걸러 받을 수 없다(common/webhook_outbox.py·common/cap_1_2.py 변경이 필요, 범위 밖 — integration.py:182-192 머리말이 같은 사실을 스스로 적어 둠)"
    }
  ]
}
```
