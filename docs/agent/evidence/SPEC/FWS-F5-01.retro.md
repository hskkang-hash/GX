# FWS-F5-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F5-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F5-01",
  "title_parts": [
    {
      "part": "정찰 임무 수신(요청) — 요청 접수",
      "where": "POST /api/fws/drone/missions/{event_id}/recon?action=request · backend/apps/fws/drone.py::recon() (RECON_REQUEST)",
      "status": "measured: tests.test_fws_f5.F5_01_ReconTest.test_request_accept_airborne_return_and_mine_reflects_state — action=request 200, radius_m=300 그대로 응답"
    },
    {
      "part": "반경(발화 추정 반경 값, radius_m)",
      "where": "backend/apps/fws/drone.py::recon() radius_m 파라미터 · GET /api/fws/drone/missions/mine 응답 row.radius_m",
      "status": "measured: 위 시험에서 radius_m=300 요청 → mine 재조회에서도 300.0 그대로 (docs/agent/evidence/SPEC/FWS-F5-01.json 의 response.body.requests[0].radius_m)"
    },
    {
      "part": "발화 추정 좌표(사건의 위치 값)",
      "where": "GET /api/fws/ap/drone/missions/{event_id}/recon-coords · backend/apps/fws/ap_f5.py::recon_coords() [턴 AP · 차선 N4 신설 — K1 이벤트의 lat/lng(apps.dsm.services.event_detail) 과 드론 반경을 합친다 · drone.py 는 고치지 않았다]",
      "status": "measured: tests.test_ap_n4_f5_recon_coords_thermal.F5_01_ReconCoordsTest.test_recon_coords_carries_the_events_lat_lng_and_radius — lat=36.11·lng=127.21·radius_m=300 이 한 응답에 실측"
    },
    {
      "part": "→ 열화상 정찰 실행(상태 전이: 수락→이륙→귀환)",
      "where": "POST .../recon?action=accept|airborne|return · backend/apps/fws/drone.py::recon() (_RECON_PREV 순서 강제) · GET /api/fws/drone/missions/mine",
      "status": "measured: 같은 시험에서 accept·airborne·return 세 전이 모두 200, mine.state=\"return\" 확인. 순서 위반은 test_airborne_without_accept_is_409 로 409 실측"
    },
    {
      "part": "열화상(thermal) 센서 데이터·프레임 자체",
      "where": "backend/apps/fws/drone.py 머리말(P-387) — \"드론 0대\", 실제 열화상 프레임 수신/저장 코드 없음",
      "status": "없음 — 이 절은 서류상 상태 전이(요청·상태)만 만든다고 머리말에 명시. 실제 열화상 센서 프레임을 수신·저장·판독하는 경로는 존재하지 않는다(연동 하드웨어 0대)",
      "excluded_by": "P-428",
      "excluded_why": "열화상 센서 프레임의 실시간 수신은 드론 하드웨어 실연동이다 — WO-19 §「외부 실연동·드론 커넥터…는 하지 않는다」가 이 턴 범위 밖으로 명시했다. 「정찰 임무 수신(좌표·반경) → 열화상 정찰」 제목의 앞부분(임무 수신·좌표·반경·상태 전이)은 전부 닫혔다 — 뒷부분(실제 센서 프레임)만 하드웨어 부재로 제외한다."
    }
  ]
}
```
