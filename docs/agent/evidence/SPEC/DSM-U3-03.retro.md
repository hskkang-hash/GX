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
      "where": "backend/apps/dsm/photo_thumb.py(긴 변 <= 640 축소 JPEG + 워터마크 한 줄: 기관명 · 사건번호 · 시각) → backend/apps/dsm/incident_report.py ⑨ 첨부 「현장 사진」 칸 · backend/apps/dsm/docx_export.py(data URI 그림을 DOCX 에 싣는 한 갈래)",
      "status": "measured: P-451 — 문서에는 축소본(긴 변 <= 640 px) + 워터마크만 실린다. 원본 객체 키·링크·해시는 문서 어디에도 없고(zip 전체 바이트 대조) 원본은 서버(MinIO)에만 둔다. 저장소가 안 열리면 축소본 없이 수만 적는다 · client_measured: backend/tests/test_ar_n1_half_remaining.py::PhotoThumbnailTest::test_report_embeds_thumbnail_without_original_link_or_hash · ::test_thumbnail_long_side_and_watermark_are_applied · ::test_without_storage_the_paper_keeps_count_only"
    }
  ],
  "retro": "턴 AQ 차선 W2B · 사람 확인 · 2026-09-30 · 「의도적 설계」 행은 명세 제목(증빙 자동 첨부 · 상황보고 사진란)과 맞는다 — 결정 번호가 없어 열어 둔다(배선 없음). | 턴 AR 차선 N1 · 2026-09-30 · P-451(축소본 + 워터마크, 원본 링크·해시 0)로 「사진란」 행을 닫았다 — 계약 11조는 원본 무반출이라 축소본은 반출이 아니다. 열린 행 0(client_measured)."
}
```
