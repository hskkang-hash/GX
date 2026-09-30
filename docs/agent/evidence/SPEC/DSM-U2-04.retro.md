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
      "where": "backend/apps/dsm/threshold_alert_service.py, backend/apps/dsm/api_u24.py (전문 grep — notify/알림/push 발송 코드 0건)",
      "status": "없음 — 도달 시 audit_writer 에 문구를 감사 줄로만 남길 뿐, 팀장·U4 계정으로 실제 알림을 보내는 코드가 없다(notify 계열 함수 부재, 2026-09-29 grep 재확인)"
    },
    {
      "part": "카드 + 결정 버튼 (프런트 UI)",
      "where": "frontend/src (thresholds/observe, threshold decide 문자열 grep 전수 0건)",
      "status": "없음 — 프런트에 이 흐름을 그리는 화면이 없다"
    },
    {
      "part": "완결 조건 「도달 시각·결정 시각 둘 다 감사」",
      "where": "backend/apps/dsm/threshold_alert_service.py::observe (threshold_reached 감사) + decide (threshold_decision 감사), test: tests.test_p356_u2_spec_promotions.EvidenceExportTest.test_reach_then_decide_leaves_two_audit_rows",
      "status": "measured: 도달 감사(observation_id=395)·결정 감사(decision_id=396) 둘 다 별도 줄로 남는 것을 시험이 직접 확인"
    }
  ]
}
```
