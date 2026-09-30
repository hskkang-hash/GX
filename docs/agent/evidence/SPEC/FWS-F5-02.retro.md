# FWS-F5-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F5-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F5-02",
  "title_parts": [
    {
      "part": "열점 표시(좌표 목록 제출)",
      "where": "POST /api/fws/drone/missions/{event_id}/hotspots (points_json) · backend/apps/fws/drone.py::submit_hotspots()",
      "status": "measured: tests.test_fws_f5.F5_02_HotspotsTest.test_submit_points_and_fireline_then_read_back — 열점 2점 제출 → 응답 points 2건 그대로"
    },
    {
      "part": "화선 표시(좌표 목록 제출, 최소 2점)",
      "where": "POST .../hotspots (fireline_json) · backend/apps/fws/drone.py::submit_hotspots()/_validate_points(min_count=2)",
      "status": "measured: 같은 시험에서 화선 2점 제출·응답 확인 + test_single_point_fireline_is_422 로 1점 미만 422 실측"
    },
    {
      "part": "재조회(제출 값이 그대로 남는가)",
      "where": "GET /api/fws/drone/missions/{event_id}/hotspots/mine · backend/apps/fws/drone.py::hotspots_mine()",
      "status": "measured: docs/agent/evidence/SPEC/FWS-F5-02.json — mine 재조회 batches[0].points/fireline 이 제출 값과 동일"
    },
    {
      "part": "열화상 프레임에서 좌표를 추출하는 입력 경로",
      "where": "backend/apps/fws/drone.py::submit_hotspots() — points_json/fireline_json 은 호출자가 그대로 넘기는 JSON 문자열, 열화상 프레임 처리·좌표 추출 로직 없음",
      "status": "없음 — 열화상 프레임을 입력받아 열점 좌표를 계산/추출하는 코드가 없다. 좌표는 호출자가 값으로 직접 제출한다(드론 0대, 실제 프레임 파이프라인 없음)",
      "excluded_by": "P-428",
      "excluded_why": "열화상 센서 프레임의 실시간 수신·판독은 드론 하드웨어 실연동이다 — WO-19 §「외부 실연동·드론 커넥터…는 하지 않는다」가 이 턴 범위 밖으로 명시했다. 좌표 값 자체(제출·저장·재조회)는 이미 완결됐다 — 그 좌표를 누가/무엇이 만들어내는지(사람 입력 vs 센서)는 별개 축이다."
    },
    {
      "part": "지도 위 폴리라인 표시(렌더링)",
      "where": "frontend 지도 컴포넌트(MapForRoute*) — §0.4 금지구역으로 이 차선이 만지지 않음. backend/apps/fws/drone.py 머리말에 명시",
      "status": "없음(프론트 지도 렌더 — §0.4 금지구역 밖이라 만들지 않음, 저장·재조회되는 것은 좌표 목록 값뿐)",
      "excluded_by": "P-428",
      "excluded_why": "지도 렌더는 §0.4 금지구역(MapForRoute*)에 인접해 이 차선이 손대지 않으며, WO-19 §「…지도 렌더는 하지 않는다」가 이 턴 범위 밖으로 명시했다. 값(좌표 목록)은 서버에 온전히 있다 — 그리는 것은 화면의 몫."
    }
  ]
}
```
