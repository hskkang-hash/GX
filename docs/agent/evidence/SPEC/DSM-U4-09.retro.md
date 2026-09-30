# DSM-U4-09 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U4-09.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U4-09",
  "title_parts": [
    {
      "part": "지역안전지수 6분야에 맞춘 유형 분류 열",
      "where": "GET /api/dsm/stats/safety-index · apps/dsm/u4_safety_index_stats.py::safety_index_axis()(stats.stats_axes() 의 event_type 축을 재접음, 새 질의 없음)",
      "status": "measured: 이 시험 — fire 2건→화재, vehicle 1건→교통사고로 실제로 갈림"
    },
    {
      "part": "분류 매핑 표",
      "where": "apps/dsm/u4_regulations.py::EVENT_TYPE_SAFETY_INDEX · 응답 mapping 칸",
      "status": "measured: 이 시험 — mapping[\"fire\"]==\"화재\" 실측, fields 6개(지역안전지수 6분야) 실측"
    }
  ]
}
```
