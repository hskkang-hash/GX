# FWS-U5-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-U5-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-U5-03",
  "title_parts": [
    {
      "part": "마을",
      "where": "kind=village",
      "status": "measured"
    },
    {
      "part": "대피소",
      "where": "kind=shelter",
      "status": "measured"
    },
    {
      "part": "요양시설",
      "where": "kind=care_facility",
      "status": "measured"
    },
    {
      "part": "대피 대상 자동 산출",
      "where": "evacuee_target_total",
      "status": "measured"
    },
    {
      "part": "테넌트 전체(같은 테넌트 여러 관리자)",
      "where": "GET .../admin/evac-targets — count=3(두 관리자가 나눠 등록)",
      "status": "구현 — 곁표(AuditScope)로 실측(다른 테넌트는 0건)"
    }
  ]
}
```
