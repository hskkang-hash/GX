# FWS-F4-15 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-15.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-15",
  "title_parts": [
    {
      "part": "PDF(완결조건)",
      "where": "GET .../post-report.pdf(dsm_services.incident_report — UX-30 재사용) → Content-Type application/pdf",
      "status": "구현 — PDF 바이트 실측(대응시계·판정·피해현황 포함)"
    },
    {
      "part": "자원",
      "where": "GET .../post-report/summary → resources",
      "status": "구현 — F3-08 자원배정 재사용 실측"
    },
    {
      "part": "대피",
      "where": "GET .../post-report/summary → evacuation",
      "status": "구현 — F3-11 대피현황 재사용 실측"
    },
    {
      "part": "피해",
      "where": "GET .../post-report/summary → damage.status",
      "status": "구현 — '집계 전'을 정직하게 낸다(이 저장소에 피해집계 칸이 없다, incident_report.py::_damage_block 과 같은 정직함 — 0 으로 지어내지 않는다)"
    },
    {
      "part": "HWPX 산출물(명세 완결조건)",
      "where": "(없음)",
      "status": "없음(PDF만 있음 — HWPX 자체가 없다, excluded_by 번호 없음. DSM 쪽 situation_report_ledger_service.py 는 같은 결손을 P-392 로 명시 인용하나 이 절은 인용이 없다)"
    },
    {
      "part": "화면(PDF 다운로드 버튼)",
      "where": "copy_command.ts postReport.downloadPdfButton·summaryButton 문구는 있음 · CommandHome.tsx 렌더 0건",
      "status": "없음(버튼 미배선)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · PDF·자원·대피·피해(정직한 '집계 전')는 실측 닫힘을 재확인했다. 명세 완결조건이 부르는 HWPX 산출물이 표에 없었고(인용 없는 결손), 다운로드 버튼도 미배선이다 — 반쪽으로 내린다."
}
```
