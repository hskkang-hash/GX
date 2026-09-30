# FWS-F1-10 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-10.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-10",
  "title_parts": [
    {
      "part": "K2 발송이 내 목록(GET /api/fws/alerts)에 '도달'로 나타난다",
      "where": "backend/apps/fws/alerts.py::my_alerts — GET /api/fws/alerts",
      "status": "measured: 풍향 급변 경보 발송 뒤 목록에 새 delivery"
    },
    {
      "part": "확인(ack) 처리",
      "where": "backend/apps/fws/alerts.py::ack_alert — POST /api/fws/alerts/{id}/ack",
      "status": "measured: 같은 시험 — ack 200 · acknowledged=true"
    },
    {
      "part": "화면에서 알림 목록 표시 + 확인 버튼",
      "where": "frontend/src/features/fws/pages/PatrolHome.tsx(List + ackButton · handleAck 가 alertAck 엔드포인트를 부른다)",
      "status": "present: 턴 AO 소급이 코드로 확인한 행 그대로(이 차선은 화면을 바꾸지 않았다)"
    },
    {
      "part": "'풍향 급변' 판정 → 안전 경보 자동 발송",
      "where": "backend/apps/fws/alerts.py::report_wind_direction → _fire_safety_alert → dsm_services.notify_event → K2 send · POST /api/fws/command/incidents/{id}/wind-reading",
      "status": "measured: 문턱값 그대로(45도 변화)는 alert_fired=false·알림 0 · 46도 변화는 alert_fired=true·delivered_count>=1·GET /api/fws/alerts 에 새 행 · ack 200(시험 주입 문턱 — 규정값은 아래 열린 행)"
    },
    {
      "part": "문턱 = 기관 설정값(P-434) — 풍향 급변 각도·시간창 · 투하 구역 반경",
      "where": "frontend/src/features/fws/pages/AdminHome.tsx::SafetyThresholdCard (data-gx=fws-threshold-wind-shift-angle · fws-threshold-wind-shift-window · fws-threshold-drop-zone-exit-radius · 미설정 배지 *-waiting · fws-threshold-save) · GET/POST /api/fws/admin/safety-thresholds · backend/apps/fws/safety_thresholds.py(기관 곁표로 좁힌 최신 감사 줄) · backend/apps/fws/alerts.py::_threshold(scope, name) 가 요청자 기관 값을 읽는다",
      "status": "구현: 세종 P-434 「명세에 없는 숫자는 기관 설정」 — 기본값·권장값 0(범위 검증만: 각 0<x≤180 · 분>0 · 반경>0). 미설정이면 판정 0 · threshold_status=\"대기\"(화면 「대기」 배지 + 「기관이 정하면 경보가 켜집니다」). tests.test_aq_n4_thresholds: SetThenJudgeTest(U5 저장 → 새 GET 재조회 값·설정됨 → 45도 0/46도 발화 · 299m 0/301m 발화 · 감사 줄 전→후) · UnsetMeansWaitingTest · OtherTenantDoesNotLeakTest · WriteGuardTest(비U5 403·범위 밖 422). 기관이 실제 값을 넣기 전 운영 판정은 「대기」다"
    },
    {
      "part": "풍향 실측원 — 기상 관측(기상청·산림청 AWS) 실연동",
      "where": "입력 문은 POST /api/fws/command/incidents/{id}/wind-reading (수동·연계용) 하나뿐",
      "excluded_by": "P-428",
      "excluded_why": "외부 기관 실연동(기상 관측 API)은 이 턴이 채우지 않는다 — 판정 규칙은 들어온 판독을 읽어 실제로 쏜다",
      "status": "excluded_by: P-428 — 외부 기상 관측 실연동 부분만 결정 제외"
    },
    {
      "part": "'대피 지시'·'철수' 전용 알림이 F1 감시원의 /alerts 목록에 뜨는가",
      "where": "대피 지시: backend/apps/fws/command.py::approve_evacuation → dsm_services.notify_event (F4-05 승인 · 기존 연결) · 철수: backend/apps/fws/alerts.py::order_withdrawal → _fire_safety_alert → notify_event (새 채널 0) · POST/GET /api/fws/command/incidents/{id}/withdrawal-order · 화면 frontend/src/features/fws/pages/W2cCommandCards.tsx::FieldSafetyAlertCard (지휘 화면 CommandHome.tsx · data-gx=fws-f1-10-card · fws-f1-10-evac-notified · fws-f1-10-withdrawal-reason · fws-f1-10-withdrawal-order · fws-f1-10-withdrawal-list) · 받는 쪽 GET /api/fws/alerts",
      "status": "구현 — 대피 승인 뒤 받는 사람의 GET /api/fws/alerts 에 새 알림 · ack 200 · 철수 지시 뒤 같은 목록에 새 알림 · GET withdrawal-order 재조회에 사유·도달 수 · 빈 사유 422 · 남의 기관 404. tests.test_aq_w2c_command_admin_drone.W2cFieldSafetyAlertTest (test_f1_10_evac_approval_reaches_field_alerts · test_f1_10_withdrawal_order_reaches_alerts_and_rereads · test_f1_10_withdrawal_guards) · tests.test_aq_w2c_command_admin_drone.W2cScreenStaticTest.test_command_board_and_withdrawal_are_wired. 알림 목록 한 줄은 풍향 급변과 같은 모양(사건·채널·시각)이라 종류 글자는 지휘 쪽 기록(withdrawal-order)에 있다"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 판정 규칙 (apps/fws/alerts.py::report_wind_direction·report_drop_zone_position)을 HTTP 로 두드려 문턱 아래는 경보 0 · 문턱 위는 notify_event→K2 발송→GET /api/fws/alerts 도달→ack 를 대조했다. 문턱 숫자는 명세에 없어 constants.py 에 이름만 요청했고 (값 None → judged=false), 시험은 주입값으로 경계를 쟀다 — 규정값 행은 열린 채 둔다. | 턴 AQ 차선 N4 · 화면 배선 · 사람 확인 — P-434: 문턱은 기관 설정값(U5 산불 설정 탭 · 안전경보 기준 카드)으로 옮겼고, 미설정은 「대기」로 보이며 발화 0 이다. | 턴 AQ 차선 W2C · 화면 배선 · 사람 확인 — 대피 승인이 현장 알림에 닿는 것을 시험으로 보였고, 철수 지시는 지휘 화면 버튼 → 기존 안전경보 경로(notify_event)로 잇었다."
}
```
