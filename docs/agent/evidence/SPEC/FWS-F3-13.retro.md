# FWS-F3-13 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-13.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-13",
  "title_parts": [
    {
      "part": "발생·위치",
      "where": "응답 occurred_at·lat·lng·address",
      "status": "구현 — K1 이벤트에서 그대로"
    },
    {
      "part": "면적",
      "where": "해당 없음",
      "status": "정직하게 비움[None] — 진행 중 사건의 면적은 F3-14 최종 실측 전까지 측정값이 없다(D-284, 지어내지 않는다)"
    },
    {
      "part": "진화 현황",
      "where": "응답 response_state·severity",
      "status": "구현 — K1 대응 진행 축 재사용"
    },
    {
      "part": "인력/장비",
      "where": "요청 personnel_count·equipment_note → 응답 그대로",
      "status": "구현 — 실측 12명 · 장비 메모"
    },
    {
      "part": "인명",
      "where": "요청 casualties_count → 응답 그대로",
      "status": "구현 — 실측 0"
    },
    {
      "part": "시설",
      "where": "요청 facility_note → 응답 그대로",
      "status": "구현 — 실측"
    },
    {
      "part": "기상",
      "where": "요청 weather_note → 응답 그대로",
      "status": "구현 — 실측"
    },
    {
      "part": "매시간 초안(완결조건)",
      "where": "GET 목록 count",
      "status": "구현 — 1건 누적 실측"
    },
    {
      "part": "산림청 입력 항목 내보내기(완결조건)",
      "where": "응답 kfs_export.fields(F6-01 export_kfs_feed 재사용)",
      "status": "구현 — 신고일시 등 라벨 실측"
    }
  ]
}
```
