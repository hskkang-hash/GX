# DSM-U2-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U2-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U2-04",
  "title_parts": [
    {
      "part": "외부 관측값(하천 수위·강우량 등) 수용",
      "where": "backend/apps/dsm/threshold_alert_service.py::observe (POST /api/dsm/thresholds/observe)",
      "status": "measured: evidence POST /api/dsm/thresholds/observe/395/decide 의 observe 블록(camera_id/key/value)"
    },
    {
      "part": "통제 기준 도달 판정",
      "where": "backend/apps/dsm/threshold_alert_service.py::observe → kernels.k5_trust.services.resolve_threshold",
      "status": "measured: value(182) ≥ threshold(180) → reached:true (evidence response.observe)"
    },
    {
      "part": "팀장·U4에게 「기준 도달 03:40 · 통제 여부 결정 필요」 알림 발송",
      "where": "backend/apps/dsm/threshold_alert_service.py::list_alerts(NOTICE_FMT='기준 도달 {hhmm} · 통제 여부 결정 필요' — 명세 원문 모양 · 시각=도달 감사 줄 created_on) · GET /api/dsm/thresholds/alerts · 화면 frontend/src/features/dsm/components/ThresholdAlertCard.tsx::data-gx=dsm-u2-04-notice — DecisionHandoverRow 가 팀장(U2)·U4 홈 둘 다에 그림",
      "status": "measured: tests.test_aq_w2b_dsm_screens.ThresholdAlertScreenTest.test_card_notice_then_decide_then_refetch — 도달 뒤 GET 카드 notice 가 ^기준 도달 hh:mm · 통제 여부 결정 필요$ · 남의 테넌트 카드 안 보임. 알림 = 팀장·U4 홈 카드(앱 안) — 앱 밖 푸시·문자 발송은 없다(명세 처리 칸이 「카드 + 결정 버튼」)"
    },
    {
      "part": "카드 + 결정 버튼 (프런트 UI)",
      "where": "frontend/src/features/dsm/components/ThresholdAlertCard.tsx::data-gx=dsm-u2-04-card · dsm-u2-04-decision · dsm-u2-04-decide · dsm-u2-04-decided — POST /api/dsm/thresholds/observe/{id}/decide → GET /api/dsm/thresholds/alerts",
      "status": "measured: tests.test_aq_w2b_dsm_screens.ThresholdAlertScreenTest.test_card_notice_then_decide_then_refetch — 결정 누른 뒤 같은 GET 재조회에 decided=true · decision='통제 실시' · decided_at 존재 · ScreenStaticTest(data-gx 글자 대조)"
    },
    {
      "part": "완결 조건 「도달 시각·결정 시각 둘 다 감사」",
      "where": "backend/apps/dsm/threshold_alert_service.py::observe (threshold_reached 감사) + decide (threshold_decision 감사), test: tests.test_p356_u2_spec_promotions.EvidenceExportTest.test_reach_then_decide_leaves_two_audit_rows",
      "status": "measured: 도달 감사(observation_id=395)·결정 감사(decision_id=396) 둘 다 별도 줄로 남는 것을 시험이 직접 확인"
    }
  ],
  "retro": "턴 AQ 차선 W2B · 화면 배선 · 사람 확인 · 2026-09-30 · 팀장·U4 홈에 도달 카드(명세 문구 모양 · 실제 도달 시각) + 결정 버튼 · 누른 뒤 GET /thresholds/alerts 재조회. 앱 밖 푸시는 없음(명세가 요구한 것은 카드)."
}
```
