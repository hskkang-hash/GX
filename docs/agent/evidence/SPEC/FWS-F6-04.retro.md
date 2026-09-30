# FWS-F6-04 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-04.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-04",
  "title_parts": [
    {
      "part": "확산예측 결과 등록(업로드 경로 — 이미지/좌표 참조)",
      "where": "POST /api/fws/ap/incidents/{event_id}/spread-results · backend/apps/fws/ap_f6.py::record_spread_result()",
      "status": "measured: tests.test_ap_n4_f6_spread_upload.F6_04_SpreadUploadTest.test_upload_then_list_reads_back_the_same_values — 200, image_ref 그대로 응답"
    },
    {
      "part": "화선 도달 예상 시각(마을별 메모)",
      "where": "backend/apps/fws/ap_f6.py::record_spread_result() arrival_note 파라미터",
      "status": "measured: 같은 시험에서 arrival_note=\"본촌리 08:00\" 제출 → 재조회에 그대로 남음"
    },
    {
      "part": "재조회(등록한 결과가 그대로 남는가)",
      "where": "GET /api/fws/ap/incidents/{event_id}/spread-results · backend/apps/fws/ap_f6.py::list_spread_results()",
      "status": "measured: 같은 시험에서 GET 재조회 count=1, 값 일치 실측"
    },
    {
      "part": "확산예측 결과 수신(API 경로 — 산림과학원 실연동)",
      "where": "backend/apps/fws/ap_f6.py 머리말 — 이 파일이 여는 것은 업로드 경로뿐, API 수신 코드 없음",
      "status": "없음 — 산림과학원 등 외부 기관의 확산예측 API 실연동은 이 저장소에 없다",
      "excluded_by": "P-428",
      "excluded_why": "산림과학원 확산예측 API 수신은 외부 기관 실연동이다(WO-19 「외부 실연동은 하지 않는다」). 명세가 「API 또는 업로드」로 둘 중 하나를 허락했고, 업로드 경로는 이 턴이 실측으로 닫았다."
    }
  ]
}
```
