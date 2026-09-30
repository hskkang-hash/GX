# FWS-F2-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-03",
  "title_parts": [
    {
      "part": "이동 회신(출동 확인 뒤 이동 중 상태)",
      "where": "backend/apps/fws/missions.py:respond(action=\"en_route\" — 출동한 진화대만 · 사건 상태는 안 옮김 · K1 현장 회신 [이동] GPS + 자기 감사 mission.en_route) · mission_detail.my_progress · POST /api/fws/missions/{event_id}/response?action=en_route&lat=&lng= · 화면 frontend/src/features/fws/pages/FieldHome.tsx::data-gx=\"fws-f2-03-en-route\" → GET /api/fws/missions/{id} 재조회 ; data-gx=\"fws-f2-03-progress\"(「이동 중」)",
      "status": "measured: tests.test_aq_w2a_field_screens.F2_03_EnRouteScreenTest.test_dispatch_en_route_then_refetch_shows_my_progress — 출동 뒤 en_route POST 200 · 새 GET 재조회 my_progress=en_route · response_state=acknowledged 유지 · /missions/mine en_route_at 기록 · 출동 없이 409(test_en_route_without_dispatch_is_409) · 격리 404(test_other_tenant_en_route_is_404) · 화면 정적 대조 test_screen_has_en_route_button_and_progress"
    },
    {
      "part": "도착 회신(GPS 좌표 포함)",
      "where": "backend/apps/fws/missions.py:respond(action=\"arrived\", lat, lng) · POST /api/fws/missions/{event_id}/response?action=arrived&lat=...&lng=...",
      "status": "measured: tests.test_fws_f2.F2_02_03_11_MissionResponseTest.test_mission_detail_dispatch_arrive_release_chain — lat=36.1,lng=127.2 로 POST, 200 · to=\"in_progress\" 확인(SPEC/FWS-F2-03.json)"
    },
    {
      "part": "30분 시계(완결조건 — 명세서 §5.2 158행 「도달 시각 · 30분 시계」, P2 초기대응 30분 규칙)",
      "where": "backend/apps/fws/missions.py:respond (elapsed_minutes, within_30_min 계산, 214-219행)",
      "status": "measured: SPEC/FWS-F2-03.json response.body.elapsed_minutes=5.0, within_30_min=true — event.occurred_at 대비 경과분·30분 이내 여부가 응답에 실제로 계산되어 나옴"
    },
    {
      "part": "GPS 좌표가 감사·현장 회신에 남는다",
      "where": "backend/apps/fws/missions.py:respond → dsm_services.field_reply(text=f\"[도착] GPS lat={lat} lng={lng}...\") 208-210행 · 자기 감사 _write_own(ACTION_ARRIVED, {lat,lng,...}) 213-214행",
      "status": "measured: 같은 실측 요청의 응답이 200 이고, 코드가 K1 현장 회신과 자체 감사 양쪽에 좌표를 기록함을 확인(field_reply 호출·감사 payload 모두 lat/lng 포함)"
    }
  ],
  "retro": "턴 AQ 차선 W2A · 화면 배선 · 사람 확인 — 이동 중 회신(en_route)을 진화대 자신의 기록으로 더하고 화면 버튼·내 진행 칸을 달았다(누른 뒤 임무 재조회)"
}
```
