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
      "where": "backend/apps/fws/verification.py:29-30,94 RESULT_CANNOT_ACCESS — 판정을 안 바꾸는 분기",
      "status": "없음: 코드에는 존재하나(RESULTS 3택에 포함, verdict=None으로 남기는 분기) backend/tests/test_fws_app.py 전체에 'cannot_access'를 실제로 POST하는 시험이 0건 — HTTP 실측이 없다(grep 결과 무일치)"
    },
    {
      "part": "회신 + 사진 1장 첨부",
      "where": "backend/apps/fws/verification.py::reply_verification 시그니처(scope, verification_id, result, reason_code, note) — 비교: api.py:311-313 drone_confirm_result 는 attachment_ref 파라미터가 있음",
      "status": "없음: 원 명세서(FWS_산불감시App_명세서_v1.0_...20260915.md:141행)의 제목 원문은 \"「산불 맞음」/「소각·오인」(사유5택)/「접근 불가」+사진1\"인데, F1-06의 reply_verification에는 사진/첨부 파라미터가 아예 없다(드론용 병행 엔드포인트 drone_confirm_result만 attachment_ref를 받음) — evidence.json의 title 필드조차 이미 '+사진1'을 빼고 적어 놓았다"
    }
  ]
}
```
