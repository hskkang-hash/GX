# FWS-F6-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-05",
  "title_parts": [
    {
      "part": "헬기 출동 요청 등록(요청 기관·메모)",
      "where": "backend/apps/fws/integration.py::request_helicopter (POST /api/fws/liaison/fire-events/{id}/helicopter-requests)",
      "status": "있음 — requesting_org 필수(빈 값이면 422, test_blank_org_is_422 실측)"
    },
    {
      "part": "위치(위도·경도) 수신",
      "where": "backend/apps/fws/integration.py::request_helicopter (lat, lng 파라미터, line 288-299)",
      "status": "있음(값만) — 좌표는 숫자 값으로만 저장·재조회된다(지도는 그리지 않는다 · §0.4 인접 MapForRoute·FormRoute 금지구역이라 값만 낸다는 것이 이 절의 명시적 범위)"
    },
    {
      "part": "사건별 조회",
      "where": "backend/apps/fws/integration.py::helicopter_requests (GET /api/fws/liaison/fire-events/{id}/helicopter-requests)",
      "status": "있음 — test_request_then_list_by_event 가 POST 뒤 GET 재조회에 1건으로 남는 것을 실측"
    },
    {
      "part": "산림항공본부 실시간 연동(요청·위치 자동 수신)",
      "where": "backend/apps/fws/integration.py:281-284 (머리말 주석 — 실시간 연동 없음, 수동 입력 대안만 지었다고 스스로 적음)",
      "status": "없음 — annex 가 허락한 '수동 입력 대안'만 지었다, 산림항공본부 시스템과의 실시간 API 연동 코드는 없다"
    }
  ]
}
```
