# DSM-U4-08 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-08.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-08",
  "title_parts": [
    {
      "part": "상황보고 발송 이력",
      "where": "situation_reports.csv · apps/dsm/u4_evaluation_bundle_service.py::build_bundle_zip() → situation_report_ledger_service.list_reports() 재사용",
      "status": "measured: 이 시험 — ZIP 안 situation_reports.csv 존재 실측"
    },
    {
      "part": "CBS 승인 기록",
      "where": "cbs_drafts.csv → cbs_draft_service.list_drafts() 재사용",
      "status": "measured: 이 시험 — 방금 만든 초안(만안구)이 CSV 에 그대로 실측"
    },
    {
      "part": "통제 4시각",
      "where": "control_points.csv → control_board_service.list_board() 재사용",
      "status": "measured: 이 시험 — ZIP 안 control_points.csv 존재 실측"
    },
    {
      "part": "상황판단회의",
      "where": "situation_meetings.csv → situation_meeting_service.list_meetings() 재사용",
      "status": "measured: 이 시험 — ZIP 안 situation_meetings.csv 존재 실측"
    },
    {
      "part": "열람 대장",
      "where": "video_access_requests.csv → video_access_ledger_service.list_requests() 재사용",
      "status": "measured: 이 시험 — ZIP 안 video_access_requests.csv 존재 실측"
    },
    {
      "part": "훈련 실적",
      "where": "drill_report.csv → apps.dsm.services.drill_report() 재사용",
      "status": "measured: 이 시험 — ZIP 안 drill_report.csv 존재 실측"
    },
    {
      "part": "접속기록 요약",
      "where": "access_log.csv → access_log_service.read_csv() 재사용 (권한 없으면 그 파일 자리에 오류 메시지만 담고 나머지는 계속 담는다 — 부분 실패가 전체를 막지 않는다)",
      "status": "measured: 이 시험 — ZIP 안 access_log.csv 존재 실측"
    },
    {
      "part": "ZIP(PDF+CSV) — CSV 부분",
      "where": "build_bundle_zip() — zipfile.ZipFile 로 위 일곱 + manifest.json 을 하나로 묶는다",
      "status": "measured: 이 시험 — ZIP 1건에 여덟 항목 실측(완결 조건 「ZIP 1」)"
    },
    {
      "part": "ZIP(PDF+CSV) — PDF 부분",
      "where": "backend/apps/dsm/u4_evaluation_bundle_service.py::_render_summary_pdf → kernels.k4_report.render_html(공개 면 · D-278) · GET /api/dsm/evaluation-bundle.zip 안 evaluation_bundle.pdf(기간·생성 시각·일곱 원천별 줄 수·상태 요약 한 장) · manifest.json pdf.status",
      "status": "구현: tests.test_aq_n4_u4_08_pdf.EvaluationBundlePdfTest.test_bundle_zip_carries_a_real_pdf — ZIP 안 PDF 바이트가 %PDF 로 시작 · 쪽 ≥1 · manifest pdf.status=ok · CSV 일곱 그대로. 예전 excluded_by: P-392 는 번호 오용이라 지웠다(P-392 는 HWPX·F6-07 결정)"
    },
    {
      "part": "화면 — 기간 선택 → 묶음(ZIP) 내려받기 버튼",
      "where": "frontend/src/features/dsm/components/VideoAccessLedgerPanel.tsx(보고서 화면 Reports.tsx)::data-gx=dsm-u4-08-since · dsm-u4-08-until(기간 칸) · dsm-u4-08-download(묶음 내려받기 · 인증 헤더가 실리는 downloadDsmFile) · GET /api/dsm/evaluation-bundle.zip?since=&until=",
      "status": "measured: tests.test_aq_n3_screens.DsmU4_07_08ScreenTest.test_bundle_download_is_a_zip_for_the_chosen_period — 오늘~오늘 기간으로 200 · application/zip · ZIP 항목 ≥1 · 소스 정적 대조(test_screen_wires_ledger_stats_and_bundle)"
    }
  ],
  "retro": "턴 AQ 차선 N4 · 사람 확인 — P-436: PDF 행의 excluded_by: P-392 (번호 오용)를 지우고 K4 render_html 로 요약 PDF 를 ZIP 에 함께 싣는다. 화면 버튼은 아직 없다(grep 0 · 열린 행으로 남김). | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 기간 칸 둘 + 묶음 내려받기 버튼을 보고서 화면에 배선했다."
}
```
