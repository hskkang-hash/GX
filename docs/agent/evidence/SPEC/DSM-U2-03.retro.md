# DSM-U2-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U2-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U2-03",
  "title_parts": [
    {
      "part": "회의 시각(occurred_at) 기록",
      "where": "backend/apps/dsm/situation_meeting_service.py::record_meeting",
      "status": "measured: POST /api/dsm/situation-meetings body.occurred_at → response.occurred_at (evidence)"
    },
    {
      "part": "참석(attendees) 기록",
      "where": "backend/apps/dsm/situation_meeting_service.py::record_meeting",
      "status": "measured: body.attendees='상황실장·팀장·U4' 그대로 응답에 옮겨짐"
    },
    {
      "part": "결정(통제·대피·비상 단계) 기록",
      "where": "backend/apps/dsm/situation_meeting_service.py::record_meeting (decision 필수, 빈 값 400)",
      "status": "measured — 단, decision 은 자유 텍스트다(통제/대피/비상 단계 enum 검증 없음, 코드 전문 확인)"
    },
    {
      "part": "근거 값(수위·강우, basis) 기록",
      "where": "backend/apps/dsm/situation_meeting_service.py::record_meeting",
      "status": "measured: body.basis='수위 182cm · 강우 41mm' 그대로 옮겨짐"
    },
    {
      "part": "「한 화면」— 위 4칸을 한 폼에서 입력하는 프런트 화면",
      "where": "frontend/src (situation-meetings 문자열 grep 전수 0건 — 화면 코드 없음)",
      "status": "없음 — 프런트에 이 엔드포인트를 부르는 화면이 전혀 없다(grep 0건, 2026-09-29 재확인)"
    },
    {
      "part": "완결 조건 「결정 → 테넌트 상태 축 변경」",
      "where": "backend/apps/dsm/situation_meeting_service.py (파일 전문 — record_meeting/list_meetings 뿐, latest()/상태 갱신 함수 없음)",
      "status": "없음 — 회의 기록은 감사 로그 한 줄로만 남고, 결정값이 테넌트의 어떤 상태 축(모드·경보 단계 등)도 바꾸지 않는다. 동일 차선의 alert_level_service.py 는 'latest_alert()'로 이 개념을 대신하지만 situation_meeting_service.py 에는 그런 read-back 함수 자체가 없다"
    }
  ]
}
```
