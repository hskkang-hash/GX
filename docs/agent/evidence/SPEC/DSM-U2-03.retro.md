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
      "where": "frontend/src/features/dsm/components/SituationMeetingCard.tsx::data-gx=dsm-u2-03-occurred-at · dsm-u2-03-attendees · dsm-u2-03-decision · dsm-u2-03-alert-level · dsm-u2-03-basis · dsm-u2-03-submit · dsm-u2-03-list — 팀장(U2) 홈 pages/Home.tsx 의 DecisionHandoverRow 에 붙음 · POST /api/dsm/situation-meetings → GET /api/dsm/situation-meetings",
      "status": "measured: tests.test_aq_w2b_dsm_screens.SituationMeetingScreenTest.test_meeting_decision_moves_alert_level_axis_then_refetch — 네 칸을 한 폼으로 보내고 같은 목록 GET 을 캐시 우회로 다시 불러 새 기록을 그린다 · ScreenStaticTest(화면 요소 이름 글자 대조 · 쓰기 뒤 reload)"
    },
    {
      "part": "완결 조건 「결정 → 테넌트 상태 축 변경」",
      "where": "backend/apps/dsm/situation_meeting_service.py::record_meeting(alert_level) → alert_level_service.record_alert (위기경보·비상 단계 축 · latest_alert()/GET /api/dsm/alert-level 첫 행이 지금 단계) · 화면 SituationMeetingCard.tsx::data-gx=dsm-u2-03-alert-level ; 띠 AlertLevelBand.tsx::data-gx=dsm-u4-06-band 가 다시 읽음",
      "status": "measured: tests.test_aq_w2b_dsm_screens.SituationMeetingScreenTest — 회의가 「경계」를 정하면 GET /api/dsm/alert-level?limit=1 첫 행 level 이 경계로 바뀐다(doc_no=상황판단회의 기록 #id) · 단계를 안 고른 회의는 축 그대로 · 4단계 밖 400(아무것도 안 남음) · 남의 테넌트 축은 안 바뀜. 상태 축은 이미 있던 U4-06 위기경보·비상 단계 축이다(새 칸 0) — 통제·대피 결정은 자유 문장으로 남고 축을 바꾸지 않는다"
    }
  ],
  "retro": "턴 AQ 차선 W2B · 화면 배선 · 사람 확인 · 2026-09-30 · 네 칸 한 폼(팀장 홈) + 회의가 정한 비상 단계를 기존 위기경보·비상 단계 축에 반영 · 누른 뒤 목록·축 GET 재조회."
}
```
