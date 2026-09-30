# FWS-F4-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-05",
  "title_parts": [
    {
      "part": "승인(즉시/준비)",
      "where": "요청 urgency=immediate → 응답 status=approved",
      "status": "구현 — 즉시 승인 실측"
    },
    {
      "part": "CBS 초안 확정(완결조건)",
      "where": "F3-11 초안(villages) → 응답 villages",
      "status": "구현 — F3-11 문안을 다시 안 짓고 승인만 확정(D-212)"
    },
    {
      "part": "푸시(완결조건)",
      "where": "응답 notified_count(notify_event 재사용)",
      "status": "구현 — 내부 앱 푸시(notify_event 재사용) 실측 · 행안부 CBS 실제 발송은 아래 행(P-428)으로 따로 뺐다"
    },
    {
      "part": "해제",
      "where": "POST .../release → 응답 status=released",
      "status": "구현 — 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx::data-gx=fws-f4-05-approve · fws-f4-05-urgency · fws-f4-05-release · fws-f4-05-release-reason · fws-f4-05-status — API POST /api/fws/command/evacuations/{id}/approve · POST /api/fws/command/evacuations/{id}/release · GET /api/fws/command/evacuations/{id}/command-status",
      "status": "구현 — 화면 배선 · 승인(즉시/준비)·해제 버튼 → 재조회 latest_approval·latest_release 가 승인/해제 상태로 그려진다 · 누른 뒤 재조회 시험 backend/tests/test_aq_n1_f4_command_wiring.py::AqN1F4CommandWiringTest::test_f4_05_approve_release_then_reread_status · 정적 대조 AqN1F4ScreenSourceTest::test_screen_declares_data_gx_and_calls_each_path"
    },
    {
      "part": "CBS 실제 발송(행안부 외부 시스템)",
      "where": "command.py notify_event — 내부 앱 푸시(웹푸시)만 실행한다. 명세 원문 §5.4 는 '대피 명령은 제품이 내리지 않는다 — 초안·승인·기록까지이며 발송은 행안부 CBS 시스템'이라 적는다",
      "excluded_by": "P-428",
      "excluded_why": "외부 기관 실연동 — 행안부 CBS 실제 발송은 외부 시스템 몫(명세 §5.4 「발송은 행안부 CBS 시스템」) · 제품은 초안·승인·기록·내부 푸시까지이며 그 부분은 실측으로 닫혔다(WO-20 §4 N1 줄이 이 행에 P-428 을 지정)",
      "status": "excluded_by: P-428 — 행안부 CBS 실제 발송(외부 실연동)은 결정으로 제외"
    }
  ],
  "retro": "턴 AQ 차선 N1 · 화면 배선 · 사람 확인 · 2026-09-30 · CommandHome.tsx 에 긴급도(즉시/준비) 선택·승인·해제 사유·해제 버튼을 배선하고 누른 뒤 조회 GET(캐시 우회) 재호출을 test_f4_05_approve_release_then_reread_status 로 실측했다(테넌트 B 쓰기 404 · 주인 재조회 불변) · CBS 실발송 행에 excluded_by P-428(WO-20 §4 N1 지정) · 「푸시」 행은 내부 앱 푸시임을 status 에 정직하게 적었다 · 앞 판: P-419 재판정(턴 AP · N1) · 2026-09-29 · '푸시(완결조건)' 행이 사실은 내부 앱 푸시(notify_event)였고, 명세가 부르는 CBS 실제 발송(행안부)은 이 표에 아예 없었다 — 화면 버튼도 미배선 — 반쪽으로 내린다."
}
```
