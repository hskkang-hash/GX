# DSM-U6-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U6-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U6-01",
  "title_parts": [
    {
      "part": "112 긴급영상(사건+카메라 스트림 URL)",
      "where": "source=police_112",
      "status": "measured"
    },
    {
      "part": "119 출동(화재 사건)",
      "where": "source=fire_119",
      "status": "measured"
    },
    {
      "part": "재난상황 긴급대응(상황실 전송)",
      "where": "source=smart_city",
      "status": "measured"
    },
    {
      "part": "CAP 1.2 프로파일(스키마 버전 검증)",
      "where": "X-GX-Schema 헤더 부재 → 401",
      "status": "measured"
    },
    {
      "part": "서명 검증(서명 비밀 = 그 기관의 들어오는 키 · P-432)",
      "where": "common/inbound_api_key.py::verify_signed_with_request_key · X-GX-Signature 불일치 → 401 · agency 서명 → 401 · 같은 테넌트 다른 키 서명 → 401 · 시각 창 밖 → 401",
      "status": "measured — tests.test_dsm_u36_an.U6_01_ExternalEventsTest(test_bad_signature_is_401 · test_agency_key_signature_is_401 · test_another_valid_key_cannot_sign_for_this_key · test_replayed_old_timestamp_is_401) · 턴 AQ 조율자 E 손 확인"
    },
    {
      "part": "기관 인증(들어오는 키 · events:ingest)",
      "where": "키 없음/JWT → 401 · 읽기 키 → 403 · 남의 테넌트 카메라 → 404",
      "status": "measured"
    },
    {
      "part": "data_source=external 표식",
      "where": "응답 data_source 칸",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 6행(112·119·재난상황·CAP1.2·서명검증·data_source=external) 전부 재대조 — 서명 검증은 common/webhook_contract.verify 의 진짜 HMAC 판정식(REJECT_NO_SECRET 등 거절 경로 있음)이었다. 이 절은 인바운드(외부가 우리를 부른다) 전용으로 설계됐고 기능명세 미포함표도 '새 외부 의존 없음'이라 적는다 — 실제 112/119 상대 시스템과의 라이브 연동은 이 절의 완결조건이 아니다. 화면 요구도 없다(순수 API·감사 절). 빈 칸·열린 행 없음 — 깨끗함 유지(이상 없음)."
}
```
