# FWS-F1-06 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F1-06.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F1-06",
  "title_parts": [
    {
      "part": "result=fire_confirmed('산불 맞음') → K1 사건 판정이 confirmed로 바뀐다",
      "where": "backend/apps/fws/verification.py::reply_verification — POST /api/fws/verifications/{id}/reply?result=fire_confirmed",
      "status": "measured: F1_05_06_VerificationTest.test_verification_detail_and_fire_confirmed_reply — verdict=confirmed 실측"
    },
    {
      "part": "result=false_alarm('소각·오인') + 오인 사유 5택 검증",
      "where": "backend/apps/fws/verification.py:32-39 FALSE_ALARM_REASONS(5개) · POST .../reply?result=false_alarm&reason_code=...",
      "status": "measured: test_false_alarm_requires_one_of_five_reasons — 잘못된 사유는 422, 유효 사유(agri_burning)는 200+verdict=rejected"
    },
    {
      "part": "result=cannot_access('접근 불가')",
      "where": "backend/apps/fws/verification.py RESULT_CANNOT_ACCESS(판정을 안 바꾸는 분기) · POST /api/fws/verifications/{id}/reply?result=cannot_access · 화면 frontend/src/features/fws/pages/PatrolW2aCards.tsx::data-gx=\"fws-f1-06-cannot-access\"(PatrolHome.tsx 에 마운트) · 누른 뒤 GET /api/fws/verifications/{id} 재조회 ; data-gx=\"fws-f1-06-verdict\" · \"fws-f1-06-replies\"",
      "status": "measured: tests.test_aq_w2a_field_screens.F1_06_ReplyScreenTest.test_cannot_access_with_photo_then_refetch_shows_reply — cannot_access POST 200 · verdict=None · 새 GET 재조회에서 verdict=None 그대로·replies[0].result=cannot_access · 격리 test_other_tenant_cannot_read_or_reply(404) · 화면 정적 대조 test_screen_offers_cannot_access_and_photo"
    },
    {
      "part": "회신 + 사진 1장 첨부",
      "where": "사진 저장은 기존 DSM 현장 사진 문 POST /api/dsm/events/{id}/field-photo(apps/dsm/api_u3.py::upload_field_photo) · 회신에 묶기 backend/apps/fws/verification.py::reply_verification(photo_id — 그 사건에 올라온 사진인지 대조, 아니면 422) · api.py::reply_verification(photo_id) · 화면 PatrolW2aCards.tsx::data-gx=\"fws-f1-06-photo\"(1장 · 회신 버튼이 올린 뒤 photo_id 를 실어 보냄) · api_w2a.ts::uploadFieldPhoto",
      "status": "measured: tests.test_aq_w2a_field_screens.F1_06_ReplyScreenTest.test_cannot_access_with_photo_then_refetch_shows_reply — 사진 업로드(저장소 _upload_bytes 만 patch) → photo_id 로 회신 → 새 GET 재조회 replies[0].photo_id 일치 · 다른 사건의 사진은 422(test_photo_of_another_event_is_422)"
    }
  ],
  "retro": "턴 AQ 차선 W2A · 화면 배선 · 사람 확인 — 감시원 화면에 회신 3택(접근 불가 포함)·사진 1장 칸을 달고 누른 뒤 확인 요청을 다시 불러 판정·회신을 그린다"
}
```
