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
      "status": "구현 — 실측"
    },
    {
      "part": "해제",
      "where": "POST .../release → 응답 status=released",
      "status": "구현 — 실측"
    },
    {
      "part": "화면 버튼(FW-04 완결조건)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx — 조회 카드만 그린다, 이 절에 해당하는 버튼 문구는 copy_command.ts 에 준비돼 있으나 렌더 0건(공통 결손 — F4-01 감사에서 확인)",
      "status": "없음(버튼 미배선)"
    },
    {
      "part": "CBS 실제 발송(행안부 외부 시스템)",
      "where": "command.py notify_event — 내부 앱 푸시(웹푸시)만 실행한다. 명세 원문 §5.4 는 '대피 명령은 제품이 내리지 않는다 — 초안·승인·기록까지이며 발송은 행안부 CBS 시스템'이라 적는다",
      "status": "없음(외부 기관 실연동 — excluded_by 번호 없음. 조율자 판단 후보: P-428, 이 행은 진짜 외부 실연동 범주라 자격은 있으나 N1 은 결정 번호를 스스로 안 붙인다)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · '푸시(완결조건)' 행이 사실은 내부 앱 푸시(notify_event)였고, 명세가 부르는 CBS 실제 발송(행안부)은 이 표에 아예 없었다 — 화면 버튼도 미배선 — 반쪽으로 내린다."
}
```
