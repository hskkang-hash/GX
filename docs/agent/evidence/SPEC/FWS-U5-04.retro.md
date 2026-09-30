# FWS-U5-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-U5-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-U5-04",
  "title_parts": [
    {
      "part": "등급별 수신",
      "where": "severities/rules",
      "status": "measured"
    },
    {
      "part": "진화대",
      "where": "role_suggestions[fws_response_team]",
      "status": "measured"
    },
    {
      "part": "산림과",
      "where": "role_suggestions[fws_forestry_dept]",
      "status": "measured"
    },
    {
      "part": "지휘",
      "where": "role_suggestions[fws_command]",
      "status": "measured"
    },
    {
      "part": "산림청",
      "where": "role_suggestions[fws_kfs_liaison]",
      "status": "measured"
    },
    {
      "part": "야간 5분대기조 채널",
      "where": "night_standby_zone",
      "status": "measured"
    },
    {
      "part": "화면 — 등급별 수신 표 · 역할(진화대·산림과·지휘·산림청) · 야간 5분대기조 채널 저장",
      "where": "frontend/src/features/fws/pages/AdminHome.tsx::NotifyCard (data-gx=fws-u5-04-card · fws-u5-04-severity · fws-u5-04-role · fws-u5-04-channels · fws-u5-04-night-standby · fws-u5-04-save · fws-u5-04-test · fws-u5-04-reach · fws-u5-04-rules) · GET/POST /api/fws/admin/notify-rules",
      "status": "구현 — 저장 뒤 reload() 가 fwsGetFresh 로 GET 을 다시 불러 등급별 도달 수·규칙 목록(야간 5분대기조 표식)을 그린다. 등급 선택지는 서버 severities(정보·경고·위험) 그대로 — 예전 화면의 high/medium/low 는 서버 등급이 아니어서 저장이 막혔다(고침). tests.test_aq_w2c_command_admin_drone.W2cAdminDroneTest.test_u5_04_screen_severity_values_save_and_night_zone_rereads · tests.test_aq_w2c_command_admin_drone.W2cScreenStaticTest.test_admin_notify_card_is_wired"
    }
  ],
  "retro": "턴 AQ 차선 W2C · 화면 배선 · 사람 확인 — 산불 설정 화면 알림 규칙 카드에 data-gx 를 달고, 저장 뒤 캐시 우회 재조회 · 등급별 도달 표 · 야간 5분대기조 표식을 그렸다(서버 등급이 아닌 선택지 제거)."
}
```
