# DSM-U5-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U5-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U5-03",
  "title_parts": [
    {
      "part": "스마트시티 통합플랫폼",
      "where": "service=smart_city",
      "status": "measured"
    },
    {
      "part": "112",
      "where": "service=police_112",
      "status": "measured"
    },
    {
      "part": "119",
      "where": "service=fire_119",
      "status": "measured"
    },
    {
      "part": "NDMS",
      "where": "service=ndms",
      "status": "measured"
    },
    {
      "part": "엔드포인트",
      "where": "endpoint_name",
      "status": "measured"
    },
    {
      "part": "자격 참조명",
      "where": "outbound_api_key_ref",
      "status": "measured"
    },
    {
      "part": "연결 시험",
      "where": "POST /u5an/integrations/test",
      "status": "measured"
    },
    {
      "part": "상태 한 단어",
      "where": "status",
      "status": "measured"
    }
  ]
}
```
