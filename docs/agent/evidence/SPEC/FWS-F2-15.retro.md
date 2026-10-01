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
      "where": "backend/apps/fws/notify_prefs.py::duty_post(그날 편성표 = office.current_roster 의 오늘 날짜 + 내 이름 줄의 post_code) · GET /api/fws/notify-prefs 응답 duty_post · 편성표 올리기 POST /api/fws/office/roster(선택 칸 post_code)",
      "status": "measured: P-452 — 담당 초소는 저장한 메모(assigned_post_code)가 아니라 그날 편성표 배정을 읽는다. 편성 없음·초소 칸 빔·다른 날짜면 status=waiting(「대기」 배지 · post_code null · 지어낸 초소 0), 오늘 배정이면 assigned + 그 초소. 편성표를 올린 뒤 같은 GET 재조회로 확인, 다른 기관 사용자는 대기 · client_measured: backend/tests/test_ar_n1_half_remaining.py::DutyPostFromRosterTest::test_unassigned_is_waiting_then_roster_assigns_then_refetch_shows_post"
    },
    {
      "part": "화면(M4 설정 화면)",
      "where": "frontend/src/features/fws/pages/NotifyPrefsCard.tsx(FieldHome.tsx(진화대 F2) 에 붙음)::data-gx=fws-f2-15-quiet-start · fws-f2-15-quiet-end(근무 외 차단 시각) · fws-f2-15-quiet-post(담당 초소·구역) · fws-f2-15-quiet-save · fws-f2-15-quiet-saved(저장된 값 표시) · GET·POST /api/fws/notify-prefs",
      "status": "measured: tests.test_aq_n3_screens.FwsQuietHoursScreenTest — 저장 뒤 같은 GET 을 캐시 우회로 다시 불러 22:00~06:00·초소 값이 보이고, 바꾸면(23:30) 재조회에 바뀐 값 · 다른 사람 설정은 빈 값 · 소스 정적 대조(PatrolHome·FieldHome 두 화면)"
    },
    {
      "part": "담당 초소 화면(그날 편성 · 대기 배지)",
      "where": "frontend/src/features/fws/pages/NotifyPrefsCard.tsx::data-gx=fws-f2-15-quiet-duty-post · fws-f2-15-quiet-duty-post-code · fws-f2-15-quiet-duty-waiting — GET /api/fws/notify-prefs 의 duty_post",
      "status": "measured: 저장 뒤 재조회(reload)가 duty_post 를 다시 그린다 · 미배정이면 「대기」 태그 · 소스 정적 대조 backend/tests/test_ar_n1_half_remaining.py::DutyPostFromRosterTest::test_screen_shows_waiting_badge_and_duty_post · client_measured(브라우저 누름 아님)"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 저장값(감사 로그 guardianx.fws.notify_prefs)을 K2 webpush._blocked_reason 이 실제로 되읽어 근무 외 warning 을 막고(quiet_hours) 근무 중은 통과함을 같은 시험 두 발송으로 대조했다. 앞 판이 지어낸 critical 예외는 DSM 차단 계약을 깨서 뺐다. 담당 초소/구역 값의 쓰임과 M4 화면은 여전히 없다 — 열린 두 행으로 남긴다. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · M4 근무 외 차단 칸을 화면에 그려 저장값을 읽어 보인다(화면 행 닫음). 담당 초소/구역 값을 다른 로직이 읽는 행은 여전히 없다 — 열린 채 둔다. | 턴 AR 차선 N1 · 2026-09-30 · P-452(담당 초소 = 그날 편성표 배정 · 미배정이면 차단하지 않고 「대기」 배지 · 지어낸 초소 0). notify_prefs.duty_post 가 근무표(office 업로드, 선택 칸 post_code)의 오늘 줄을 읽고 화면이 대기 배지를 보인다 — 열린 행 0(client_measured)."
}
```
