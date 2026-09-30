# DSM-U4-06 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-06.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-06",
  "title_parts": [
    {
      "part": "단계(관심·주의·경계·심각) 접수",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert (LEVELS enum 검증)",
      "status": "measured: evidence body.level='경계' → response.level='경계'"
    },
    {
      "part": "접수 시각 기록",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert",
      "status": "measured: response.occurred_at 존재"
    },
    {
      "part": "문서번호(doc_no) 기록",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert",
      "status": "measured: evidence body.doc_no='제3호' → response.doc_no"
    },
    {
      "part": "비상 근무 편성 인원 수(staffing) 기록",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert (staffing<0 이면 400)",
      "status": "measured: evidence body.staffing=24 → response.staffing"
    },
    {
      "part": "상단바 띠 UI 표시",
      "where": "frontend/src/App.tsx::PrivateLayout `<AlertLevelBand global />` → frontend/src/features/dsm/components/AlertLevelBand.tsx::data-gx=dsm-u4-06-band · dsm-u4-06-band-level (GET /api/dsm/alert-level?limit=1 첫 행 level · /dsm 경로의 모든 화면 위)",
      "status": "measured — 띠 컴포넌트 재조회 tests.test_aq_w2b_dsm_screens.AlertLevelScreenTest.test_record_then_band_refetch_reads_fields · ScreenStaticTest · App.tsx 끼움은 턴 AQ 조율자 창 ② 병합(손 확인)"
    },
    {
      "part": "홈 카드 표시",
      "where": "frontend/src/features/dsm/components/AlertLevelCard.tsx::data-gx=dsm-u4-06-card · dsm-u4-06-current(지금 단계) · dsm-u4-06-level · dsm-u4-06-occurred-at · dsm-u4-06-doc-no · dsm-u4-06-staffing · dsm-u4-06-submit · dsm-u4-06-list — 팀장(U2)·U4 홈 pages/Home.tsx 의 DecisionHandoverRow · POST /api/dsm/alert-level → GET /api/dsm/alert-level",
      "status": "measured: tests.test_aq_w2b_dsm_screens.AlertLevelScreenTest.test_record_then_band_refetch_reads_fields — 접수 뒤 같은 GET 재조회 첫 행이 (경계 · 제3호 · 24명 · 2026-09-30 08:10) 칸으로 온다(alert_level_service._parse) · test_isolation(남의 테넌트 단계 안 보임) · ScreenStaticTest"
    },
    {
      "part": "완결 조건 「변경 감사」(및 '처리' 칸의 '테넌트 상태 축' 대응)",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert(audit_writer.write) + latest_alert(가장 최근 감사 줄 = 지금 단계)",
      "status": "measured — 접수마다 감사 줄이 남고, latest_alert() 이 최근 줄을 '지금 단계'로 읽어 별도 상태 칸 없이 상태 축 역할을 대신한다(docstring 9~12행이 그 설계 판단을 명시)"
    }
  ],
  "retro": "턴 AQ 차선 W2B · 화면 배선 · 사람 확인 · 2026-09-30 · 홈 카드(접수 폼 + 지금 단계) 닫음 · 누른 뒤 GET /alert-level 재조회. 상단바 띠는 조율자 창 ② 에 App.tsx::PrivateLayout 한 줄로 끼워 닫음."
}
```
