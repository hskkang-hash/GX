# FWS-F4-09 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-09.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-09",
  "title_parts": [
    {
      "part": "산림청 상황실 1클릭(전화)",
      "where": "응답 forest_service.phone(apps.fws.contacts F1-08 재사용)",
      "status": "구현 — 042-481-4119 실측"
    },
    {
      "part": "시도 상황실 1클릭(전화)",
      "where": "F4-03 지휘소 선언 situation_room_phone → 응답 provincial_situation_room.phone",
      "status": "구현 — 033-999-0000 등록 뒤 실측(미등록 시 null — 지어내지 않는다, D-284)"
    },
    {
      "part": "화상(화상회의) 연락",
      "where": "해당 없음 — 이 저장소에 화상회의 인프라(WebRTC/SIP 등) 자체가 없다",
      "excluded_by": "P-428",
      "excluded_why": "운영 집행·외부 실연동(화상회의 인프라 구축·상대 기관 연계)은 이 턴(WO-19 P-421)이 채우지 않는다 — 전화 1클릭 두 행은 실측으로 닫혔다",
      "status": "excluded_by: P-428 — 화상(외부 기관과의 화상회의 연결)은 외부 실연동 범위 밖으로 결정 제외, 전화 부분은 서버 실측"
    },
    {
      "part": "화면 — 지휘 화면(FW-04)의 연락 버튼(tel: 1클릭)",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx 연락처 카드::data-gx=fws-f4-09-contacts · fws-f4-09-call-forest · fws-f4-09-call-provincial(href=tel: 1클릭) · 미등록이면 fws-f4-09-unregistered-* · GET /api/fws/command/incidents/{id}/contacts(refreshAll 안)",
      "status": "measured: tests.test_aq_n3_screens.FwsF4_09_13ScreenTest.test_contacts_refetch_after_command_post_phone_registered — 산림청 번호 있음·시도 null → 지휘본부 설치 선언(시도 상황실 번호) 뒤 재조회에 그 번호 · 다른 테넌트 404 · tel: 링크 정적 대조. 통화 기록 문은 서버에 없어 배선하지 않았다(지어내지 않음)"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 「화상」 행에 excluded_by P-428 + 사유를 붙이고, 제목의 「버튼」을 화면 행으로 세워 CommandHome.tsx 를 grep 했다(연락 버튼·tel: 0건 — 열린 행). 전화 두 번호는 서버 HTTP 로 실측. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 지휘 화면에 tel: 전화 버튼 둘을 그렸다(누른 뒤 재조회는 refreshAll)."
}
```
