# FWS-F2-13 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-13.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-13",
  "title_parts": [
    {
      "part": "훈련 배지(drill_mode 상태 표시)",
      "where": "backend/apps/fws/training.py:training_mission_badge · GET /api/fws/training/mission",
      "status": "measured: tests.test_fws_f2.F2_13_TrainingBadgeTest.test_badge_and_zero_real_channel_when_drill_mode_is_on — drill_mode=true 일 때 badge=\"훈련\" 확인, 꺼져있을 때 badge=None 도 별도 시험(test_no_badge_when_drill_mode_is_off)으로 확인"
    },
    {
      "part": "실채널 0(완결조건 — 명세서 §5.2 168행)",
      "where": "backend/apps/fws/training.py:training_mission_badge (real_channel_sends = drill_report()[\"real_channel_sends\"]) 40-42행",
      "status": "measured: 같은 시험 — real_channel_sends=0 확인(SPEC/FWS-F2-13.json), apps.dsm.services.drill_report 값을 그대로 재사용해 다시 세지 않음"
    },
    {
      "part": "훈련 '임무'(가상 사건) 자체 수신 — 실제 발화점·화세 등을 담은 모의 임무가 F2 에게 전달되는가",
      "where": "backend/apps/fws/missions.py::mission_detail → data_source · training_badge(판정은 DSM 공개 면 apps.dsm.services.event_data_source 한 곳 — 훈련 창에 든 사건이면 drill · P-201) · GET /api/fws/missions/{id} · 화면 frontend/src/features/fws/pages/FieldHome.tsx::data-gx=\"fws-f2-13-mission-badge\"(임무 카드 위 「훈련 임무」 — 임무 조회·회신 뒤 fwsGetFresh 재조회로 그림)",
      "status": "measured: tests.test_aq_w2a_field_screens.F2_13_TrainingMissionScreenTest.test_event_inside_drill_window_carries_training_badge — 훈련 창 안에서 난 사건을 임무로 GET 하면 발화점·화세와 함께 data_source=drill·training_badge=훈련, 훈련 전 사건은 null · 같은 창 real_channel_sends=0 · 격리 404(test_other_tenant_training_mission_is_404) · 화면 정적 대조 test_screen_draws_badge_on_mission_card"
    }
  ],
  "retro": "턴 AQ 차선 W2A · 화면 배선 · 사람 확인 — 훈련 창에 든 사건을 임무로 받으면 임무 카드에 훈련 배지가 뜬다(사건 단위 표식은 DSM 창 판정 재사용)"
}
```
