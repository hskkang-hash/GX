# FWS-U5-02 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-U5-02.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-U5-02",
  "title_parts": [
    {
      "part": "초소",
      "where": "post_code/name",
      "status": "measured"
    },
    {
      "part": "순찰함(NFC)",
      "where": "nfc_boxes",
      "status": "measured"
    },
    {
      "part": "순찰 구역",
      "where": "patrol_zone",
      "status": "measured"
    },
    {
      "part": "테넌트 전체(같은 테넌트 여러 관리자)",
      "where": "GET .../admin/posts — P-77·P-78 둘 다",
      "status": "구현 — 곁표(AuditScope)로 실측(다른 테넌트는 0건)"
    }
  ]
}
```
