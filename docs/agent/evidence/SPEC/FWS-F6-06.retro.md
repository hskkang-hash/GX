# FWS-F6-06 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-06.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-06",
  "title_parts": [
    {
      "part": "119 출동번호·연동 기록",
      "where": "backend/apps/fws/integration.py::link_fire_department (POST /api/fws/liaison/fire-events/{id}/fire-department-link)",
      "status": "있음 — dispatch_no·note 를 받아 기록한다"
    },
    {
      "part": "DSM 통해 전달(완결조건: DSM 카드가 읽는 자리)",
      "where": "backend/apps/fws/integration.py::link_fire_department → apps.dsm.services.field_reply",
      "status": "있음 — 새 표·새 배지를 만들지 않고 K1 현장 회신(field_reply)에 실어 DSM 이 읽는 자리로 보낸다 · test_link_reaches_dsm_field_replies 가 apps.dsm.services.field_replies() 재조회로 dispatch_no 문자열이 실제 도달함을 실측"
    },
    {
      "part": "재난안전 App(국가 재난안전통신망) 실제 API 연동",
      "where": "docs/agent/evidence/SPEC/N3_promotions.md:99-105 (FWS-F6-06 행 — 코드에 국가망 호출이 없음을 명문화) · backend/apps/fws/integration.py 는 dsm_services 만 부르고 외부 HTTP 호출이 없다",
      "status": "없음 — 제목의 '재난안전 App DSM 통해'에서 'DSM'은 이 저장소 내부 DSM App(지휘 화면)을 가리킨다(annex 문맥), 국가 재난안전통신망 자체·소방 119 종합상황실 시스템과의 실제 연동은 짓지 않았다"
    }
  ]
}
```
