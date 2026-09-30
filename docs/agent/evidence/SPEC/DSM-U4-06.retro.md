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
      "where": "backend/apps/dsm/alert_level_service.py 6~7행 docstring '「상단바 띠·홈 카드」 화면은 이번 범위 밖이다(P-356 — 화면은 선택)'; frontend/src alert-level 문자열 grep 0건",
      "status": "없음 — 개발자 스스로 범위 밖으로 명시했고, 프런트 코드도 없다"
    },
    {
      "part": "홈 카드 표시",
      "where": "상동(alert_level_service.py docstring), frontend/src 0건",
      "status": "없음 — 상동"
    },
    {
      "part": "완결 조건 「변경 감사」(및 '처리' 칸의 '테넌트 상태 축' 대응)",
      "where": "backend/apps/dsm/alert_level_service.py::record_alert(audit_writer.write) + latest_alert(가장 최근 감사 줄 = 지금 단계)",
      "status": "measured — 접수마다 감사 줄이 남고, latest_alert() 이 최근 줄을 '지금 단계'로 읽어 별도 상태 칸 없이 상태 축 역할을 대신한다(docstring 9~12행이 그 설계 판단을 명시)"
    }
  ]
}
```
