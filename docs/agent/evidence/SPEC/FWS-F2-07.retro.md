# FWS-F2-07 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-07.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-07",
  "title_parts": [
    {
      "part": "안전 경보 도달(내게 온 알림 목록)",
      "where": "backend/apps/fws/alerts.py::my_alerts · GET /api/fws/alerts",
      "status": "measured: 경보 발송 뒤 GET /api/fws/alerts 에 새 delivery 가 잡힘"
    },
    {
      "part": "확인(ack) — 완결조건",
      "where": "backend/apps/fws/alerts.py::ack_alert · POST /api/fws/alerts/{id}/ack",
      "status": "measured: 풍향 급변 경보 delivery 를 ack → acknowledged=true"
    },
    {
      "part": "'풍향 급변' 판정 → 안전 경보 자동 발송",
      "where": "backend/apps/fws/alerts.py::report_wind_direction → _fire_safety_alert → dsm_services.notify_event → K2 send · POST /api/fws/command/incidents/{id}/wind-reading",
      "status": "measured: 문턱값 그대로(45도 변화)는 alert_fired=false·알림 0 · 46도 변화는 alert_fired=true·delivered_count>=1·GET /api/fws/alerts 에 새 행 · ack 200(시험 주입 문턱 — 규정값은 아래 열린 행)"
    },
    {
      "part": "'헬기 투하 구역 이탈' 판정 → 안전 경보 자동 발송",
      "where": "backend/apps/fws/alerts.py::report_drop_zone_position(F4-04 승인 drop_zone 을 중심으로 재사용) · POST /api/fws/command/incidents/{id}/drop-zone-position",
      "status": "measured: 중심에서 299m 는 alert_fired=false·알림 0 · 301m 는 alert_fired=true·delivered_count>=1·GET /api/fws/alerts 에 새 행 · 승인 없으면 422(시험 주입 반경 — 규정값은 열린 행)"
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
      "part": "헬기 위치 실측원 — 항공기 위치(산림항공본부) 실연동",
      "where": "입력 문은 POST .../drop-zone-position(수동·연계용) 하나뿐",
      "excluded_by": "P-428",
      "excluded_why": "외부 기관 실연동(헬기 운항 위치)은 이 턴이 채우지 않는다 — 판정 규칙은 들어온 위치를 읽어 실제로 쏜다",
      "status": "excluded_by: P-428 — 헬기 위치 실연동 부분만 결정 제외"
    },
    {
      "part": "화면 — 진화대 임무 화면(FM3)에서 안전 경보 수신·확인",
      "where": "frontend/src/features/fws/pages/SafetyAlertsCard.tsx(FieldHome.tsx 에 붙음)::data-gx=fws-f2-07-card(확인 전 경보가 있으면 빨강 테두리·fws-f2-07-unacked) · fws-f2-07-rules(경보 기준 · 미설정 칸은 fws-f2-07-waiting 「대기」) · fws-f2-07-list · fws-f2-07-ack · GET /api/fws/admin/safety-thresholds · GET /api/fws/alerts · POST /api/fws/alerts/{id}/ack",
      "status": "measured: tests.test_aq_n3_screens.FwsF2_07FieldAlertsScreenTest — 진화대(일반 기관 사용자)가 기준을 읽으면 미설정 기관은 세 칸 모두 「대기」·값 null(화면이 숫자를 짓지 않는다) · 경보 목록 GET 200 · 확인 뒤 같은 GET 재조회(소스 정적 대조). 경보 발화→ack 왕복 자체는 N4 시험이 잰다"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 판정 규칙 (apps/fws/alerts.py::report_wind_direction·report_drop_zone_position)을 HTTP 로 두드려 문턱 아래는 경보 0 · 문턱 위는 notify_event→K2 발송→GET /api/fws/alerts 도달→ack 를 대조했다. 문턱 숫자는 명세에 없어 constants.py 에 이름만 요청했고 (값 None → judged=false), 시험은 주입값으로 경계를 쟀다 — 규정값 행은 열린 채 둔다. | 턴 AQ 차선 N4 · 화면 배선 · 사람 확인 — P-434: 문턱은 기관 설정값(U5 산불 설정 탭 · 안전경보 기준 카드)으로 옮겼고, 미설정은 「대기」로 보이며 발화 0 이다. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 진화대 화면에 안전 경보 칸(대기 배지·목록·확인)을 그렸다."
}
```
