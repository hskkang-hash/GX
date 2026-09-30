# FWS-F1-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-08",
  "title_parts": [
    {
      "part": "서버가 119(화재)·042-481-4119(산림청) 두 번호를 낸다",
      "where": "backend/apps/fws/contacts.py::emergency_contacts — GET /api/fws/emergency-contacts",
      "status": "measured: F1_08_EmergencyContactsTest.test_numbers_come_from_the_server_not_the_screen — 두 값 실측"
    },
    {
      "part": "익명 접근 차단(로그인한 감시원만)",
      "where": "backend/tests/test_fws_app.py:340",
      "status": "measured: 익명 GET이 401/403"
    },
    {
      "part": "화면이 서버 값으로 tel: 링크(1탭 버튼) 를 실제로 만든다",
      "where": "frontend/src/features/fws/pages/PatrolHome.tsx:136-144 — <a href={`tel:${contacts.fire_report}`}>, <a href={`tel:${contacts.forest_report}`}>",
      "status": "measured: 서버 응답 타입을 그대로 받아 tel: 링크 두 버튼을 렌더 — 화면 코드로 직접 번호를 다시 적지 않고 서버 값만 쓴다(코드 확인)"
    }
  ]
}
```
