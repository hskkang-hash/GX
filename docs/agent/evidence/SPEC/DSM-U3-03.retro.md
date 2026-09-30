# DSM-U3-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U3-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U3-03",
  "title_parts": [
    {
      "part": "현장 사진 업로드",
      "where": "backend/apps/dsm/field.py::save_field_photo (POST /api/dsm/events/{id}/field-photo)",
      "status": "measured: tests.test_p356_u3u6_spec_promotions.py 가 mock 업로드로 사진 1장을 실제로 올림(UPLOAD_BYTES mock)"
    },
    {
      "part": "상황보고서(K4/별지 1호) ⑨ 첨부 칸에 사진 건수 자동 표시",
      "where": "backend/apps/dsm/incident_report.py::_field_photo_count, _render(...) 1101~1118행 (⑨ 첨부 섹션)",
      "status": "measured: GET /api/dsm/events/697/situation-report.docx 의 word/document.xml 을 직접 읽어 첨부 줄에 건수가 찍힌 것을 실측(evidence docx_attachment_line_contains_photo_count:true)"
    },
    {
      "part": "완결 조건 「첨부 1」(첨부 건수 ≥1 로 문서 반영)",
      "where": "backend/apps/dsm/incident_report.py 1116행 f'{field_photo_count}장이 이 사건에 자동 첨부되었습니다'",
      "status": "measured — 완결조건이 요구하는 숫자(건수) 그대로 측정됨"
    },
    {
      "part": "사진 원본 파일(바이트) 자체가 문서에 첨부되는가",
      "where": "backend/apps/dsm/field.py 934행 주석 '첨부 칸. 파일을 붙이지 않는다 — 이름과 사유만 적는다(계약 11조 · 원본 무반출)'",
      "status": "없음(의도적 설계) — '첨부'는 건수 텍스트 한 줄일 뿐, 사진 파일 자체는 원본 무반출 정책(계약 11조)에 따라 문서에 실리지 않는다. 명세서 완결조건('첨부 1')은 만족하지만, 제목의 '증빙 자동 첨부'를 실물 첨부로 읽으면 이 부분은 열려 있다"
    }
  ]
}
```
