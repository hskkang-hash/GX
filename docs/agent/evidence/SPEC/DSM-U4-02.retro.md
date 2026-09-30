# DSM-U4-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-02",
  "title_parts": [
    {
      "part": "08시·17시 기준 응급조치 보고 자동 초안(1일 2회)",
      "where": "POST /api/dsm/situation-reports/interim-batch · apps/dsm/u4_interim_report_service.py::issue_interim_batch()(슬롯 판정 `_slot_for` · 기존 situation_report_ledger_service.issue_report(kind=중간) 재사용)",
      "status": "measured: 이 시험 — 미종결 사건이 배치로 채번됨(issued)"
    },
    {
      "part": "같은 슬롯·같은 날 중복 채번 방지",
      "where": "u4_interim_report_service.py::_batch_marker_action() 감사 마커",
      "status": "measured: 이 시험 — 재호출 시 같은 사건이 skipped 로 빠짐(slot 값도 같음)"
    },
    {
      "part": "NDMS 입력용 표 내보내기(항목 1:1)",
      "where": "GET /api/dsm/situation-reports/ndms-export.csv · u4_interim_report_service.py::export_ndms_csv()",
      "status": "measured: tests.test_ap_n4_u4_02_interim_batch.InterimBatchTest.test_ndms_export_csv_lists_issued_reports — CSV 에 방금 채번된 사건번호·report_id 열이 실측됨"
    }
  ]
}
```
