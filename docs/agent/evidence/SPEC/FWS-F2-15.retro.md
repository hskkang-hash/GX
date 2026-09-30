# FWS-F2-15 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-15.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-15",
  "title_parts": [
    {
      "part": "근무 외 시간대 저장·재조회(quiet_hours)",
      "where": "backend/apps/fws/notify_prefs.py:save_prefs/get_prefs · GET·POST /api/fws/notify-prefs",
      "status": "measured: 이 시험이 F1-12 와 같은 문을 재사용해 저장 뒤 재조회로 확인(F2 진화대도 같은 문을 쓴다)"
    },
    {
      "part": "담당 구역(assigned_post_code) 저장·재조회",
      "where": "backend/apps/fws/notify_prefs.py:save_prefs/get_prefs (assigned_post_code)",
      "status": "measured: 같은 시험 — assigned_post_code='ZONE-9' 저장 뒤 재조회 확인"
    },
    {
      "part": "근무 외 '차단' — 저장한 시간대에 실제로 알림 발송이 억제되는가",
      "where": "backend/kernels/k2_notify/webpush.py::_fws_quiet_hours_block · _blocked_reason (F1-12 와 같은 배선 — F2 도 같은 문을 쓰므로 같은 차단이 적용된다)",
      "status": "measured: F1-12 시험과 같은 왕복으로 근무 외 발송 succeeded=False('quiet_hours') · 근무 중 succeeded=True 실측 (F1-12·F2-15 가 저장 문을 공유하듯 차단 배선도 공유한다)"
    },
    {
      "part": "'담당 구역' 저장값을 다른 기능이 실제로 읽어 쓰는가",
      "where": "backend/apps/fws — assigned_post_code 를 읽는 곳은 notify_prefs.py::get_prefs(재조회) 하나뿐(grep)",
      "status": "없음 — 담당 구역 값은 저장·재조회만 되고, 알림 대상·순찰·임무 배정 어느 로직도 그 값을 읽지 않는다(TITLE_PARTS §1-6)"
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
