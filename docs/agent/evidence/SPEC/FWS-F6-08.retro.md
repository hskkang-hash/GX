# FWS-F6-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-08",
  "title_parts": [
    {
      "part": "교통통제 협조 기록",
      "where": "backend/apps/fws/integration.py::record_police_coordination (kind=\"traffic_control\", POST /api/fws/liaison/fire-events/{id}/police-coordination)",
      "status": "있음 — test_record_then_list_by_event 실측(kind=traffic_control 로 기록 후 GET 재조회 1건)"
    },
    {
      "part": "입산통제 협조 기록",
      "where": "backend/apps/fws/integration.py::POLICE_COORDINATION_KIND_ENTRY_BAN=\"mountain_entry_control\" + record_police_coordination(교통통제와 같은 함수, 코드 분기 없음)",
      "status": "있음 — traffic_control 과 완전히 같은 범용 기록 경로가 kind 값만 다르게 받는다(POLICE_COORDINATION_KINDS 에 등재) · 다만 mountain_entry_control 값 자체를 HTTP 로 직접 두드린 전용 실측은 없다(test_unknown_kind_is_422 는 잘못된 값만 검증) — 코드는 있고 같은 함수라 결과가 갈릴 지점이 없어 CLOSED 로 두되, 전용 실측 부재는 그대로 남긴다"
    },
    {
      "part": "사건별 조회",
      "where": "backend/apps/fws/integration.py::police_coordination_records (GET /api/fws/liaison/fire-events/{id}/police-coordination)",
      "status": "있음 — 제출자를 가리지 않고 그 사건에 달린 기록 전부를 낸다 · test_record_then_list_by_event 실측"
    }
  ]
}
```
