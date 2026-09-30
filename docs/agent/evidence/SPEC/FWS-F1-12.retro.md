# FWS-F1-12 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-12.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-12",
  "title_parts": [
    {
      "part": "저장(POST) 후 재조회(GET)에 방해 금지 시간대·담당 초소가 그대로 보인다",
      "where": "backend/apps/fws/notify_prefs.py::save_prefs/get_prefs — POST/GET /api/fws/notify-prefs",
      "status": "measured: 이 시험 setUp 의 POST 3회 뒤 GET 재조회로 확인"
    },
    {
      "part": "'근무 외 알림 차단' — 저장한 방해 금지 시간대가 실제로 알림 발송을 억제하는가",
      "where": "backend/kernels/k2_notify/webpush.py::_fws_quiet_hours_block/_blocked_reason(FWS_PREFS_LOGGER='guardianx.fws.notify_prefs' 를 같은 이름으로 되읽는다 · 턴 AP N2 · P-421 ①) → kernels/k2_notify/services.py::_send_one",
      "status": "measured: 근무 외 warning 발송 succeeded=False·failure_reason='quiet_hours' · 근무 중 재발송 succeeded=True (같은 시험 안 두 발송으로 대조)"
    },
    {
      "part": "'담당 초소' 저장값을 다른 기능이 실제로 읽어 쓰는가",
      "where": "backend/apps/fws — assigned_post_code 를 읽는 곳은 notify_prefs.py::get_prefs(재조회) 하나뿐(grep)",
      "status": "없음 — 담당 초소 값은 저장·재조회만 되고, 알림 대상·순찰·임무 배정 어느 로직도 그 값을 읽지 않는다(TITLE_PARTS §1-6)"
    },
    {
      "part": "화면(M4 설정 화면)",
      "where": "frontend/src/features/fws/api.ts 의 notifyPrefs 는 등록만 되고 PatrolHome·FieldHome 어느 페이지도 부르지 않는다(grep)",
      "status": "없음 — 감시원·진화대가 시간대·담당 초소/구역을 입력할 화면이 없다(App.tsx·routes.ts·copy.ts 는 공용 파일이라 이 차선이 못 붙인다)"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 저장값(감사 로그 guardianx.fws.notify_prefs)을 K2 webpush._blocked_reason 이 실제로 되읽어 근무 외 warning 을 막고(quiet_hours) 근무 중은 통과함을 같은 시험 두 발송으로 대조했다. 앞 판이 지어낸 critical 예외는 DSM 차단 계약을 깨서 뺐다. 담당 초소/구역 값의 쓰임과 M4 화면은 여전히 없다 — 열린 두 행으로 남긴다."
}
```
