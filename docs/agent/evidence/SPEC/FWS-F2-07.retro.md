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
      "part": "문턱 규정값(선언 == 설정) — 풍향 급변 각도·시간창 · 투하 구역 반경",
      "where": "backend/apps/fws/alerts.py::_threshold 가 apps.fws.constants 의 WIND_SHIFT_ANGLE_DEG·WIND_SHIFT_WINDOW_MINUTES·DROP_ZONE_EXIT_RADIUS_M 를 이름으로 읽는다 — 명세 §5.1 F1-10·F2-07 은 말만 있고 숫자가 없다",
      "status": "없음 — 명세·조사 메모에 숫자가 없어 값을 짓지 않았다(이름만 · 값 None → 운영에서 judged=false). 세종 결정으로 값이 들어와야 운영 판정이 돈다(시험은 주입값으로 경계만 쟀다)"
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
      "where": "frontend/src/features/fws/pages/FieldHome.tsx — /api/fws/alerts 를 부르지 않는다(grep · 경보 목록·확인 버튼은 PatrolHome 에만 있다)",
      "status": "없음 — F2 진화대 화면에 안전 경보 칸·확인 버튼이 없다(명세 FM3 「풍향 급변 경보 시 이 칸이 빨강」)"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 판정 규칙 (apps/fws/alerts.py::report_wind_direction·report_drop_zone_position)을 HTTP 로 두드려 문턱 아래는 경보 0 · 문턱 위는 notify_event→K2 발송→GET /api/fws/alerts 도달→ack 를 대조했다. 문턱 숫자는 명세에 없어 constants.py 에 이름만 요청했고 (값 None → judged=false), 시험은 주입값으로 경계를 쟀다 — 규정값 행은 열린 채 둔다."
}
```
