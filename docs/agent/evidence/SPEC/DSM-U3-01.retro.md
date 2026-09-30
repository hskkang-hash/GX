# DSM-U3-01 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `DSM-U3-01.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "DSM-U3-01",
  "title_parts": [
    {
      "part": "역할×유형 문안 표",
      "where": "u36_an_service.M2_PHRASE_TABLE",
      "status": "measured"
    },
    {
      "part": "M2 상단 한 줄",
      "where": "frontend/src/features/dsm/components/M2BriefLine.tsx::data-gx=dsm-u3-01-role(역할 분류 축 라디오 넷) · dsm-u3-01-line(한 줄) — M2 화면 features/mobile/pages/MobileEventDetail.tsx 맨 위에 붙음 · GET /api/dsm/events/{id}/m2-brief?role=",
      "status": "measured: tests.test_aq_n3_screens.DsmU3_01ScreenTest — 역할 축을 바꾸면(useEffect [eventId, role]) 같은 GET 을 캐시 우회로 다시 불러 그 역할의 줄을 그린다 · 시설/flood=「도로 통제 후 회신」 · 당직은 다른 줄 · 다른 테넌트 404 · 소스 정적 대조"
    },
    {
      "part": "문안 사전 일치",
      "where": "시설+flood → '도로 통제 후 회신' (명세 원문 예시와 문자열 일치)",
      "status": "measured"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 역할×유형 문안 표·문안 사전 일치는 실측 닫힘을 재확인했다. M2 상단 한 줄은 서버 응답만 있고 화면 호출이 0건이다 — 반쪽으로 내린다. | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · M2 상단 한 줄을 M2 현장 상세 화면 맨 위에 역할 축과 함께 그렸다(재조회 = 역할 바꿈)."
}
```
