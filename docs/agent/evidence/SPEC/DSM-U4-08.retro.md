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
      "where": "u4_evaluation_bundle_service.py 머리말 — PDF 렌더 코드 없음",
      "status": "없음 — PDF 는 이번 턴 만들지 않는다",
      "excluded_by": "P-392",
      "excluded_why": "이미 있는 결정을 재사용한다 — `situation_report_ledger_service.py` 머리말의 「HWPX 는 채우지 않는다」와 같은 결정 번호(HWPX/PDF 같은 문서 렌더링을 새 의존성으로 들이지 않는다). CSV(구조화 원자료)는 전부 실려 있다 — PDF 는 그 위의 사람이 읽을 서식일 뿐이다."
    }
  ]
}
```
