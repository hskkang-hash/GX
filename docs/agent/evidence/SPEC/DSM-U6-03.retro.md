# DSM-U6-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U6-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U6-03",
  "title_parts": [
    {
      "part": "사회적약자(실종) 요청 수신",
      "where": "POST /search-requests",
      "status": "measured"
    },
    {
      "part": "객체 검색 사건 생성",
      "where": "응답 event_id · created=true",
      "status": "measured"
    },
    {
      "part": "요청 → 사건 1",
      "where": "감사 줄 수 diff == 1",
      "status": "measured"
    },
    {
      "part": "LAW-05 범위(감사 줄 1)",
      "where": "audit.record_event_action",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 4행(요청수신·사건생성·요청→사건1·LAW-05 감사줄) 재대조 — 기능명세 미포함표가 이 절을 '새 외부 의존 없음'으로 명시한다(재식별 AI 를 짓지 않는다고 evidence what 도 스스로 적는다). 순수 인바운드·내부 사건 생성 절이라 외부 기관 실연동·화면 요구가 없다. 빈 칸·열린 행 없음 — 깨끗함 유지(이상 없음)."
}
```
