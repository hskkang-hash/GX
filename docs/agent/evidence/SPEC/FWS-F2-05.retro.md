# FWS-F2-05 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F2-05.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F2-05",
  "title_parts": [
    {
      "part": "인력(personnel) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_PERSONNEL) · POST /api/fws/missions/{event_id}/field-reply?kind=personnel",
      "status": "measured: helicopter 로 실측된 것과 동일한 검증(SUPPORT_KINDS 튜플 멤버십 체크)·저장 경로를 탄다(missions.py 258-272행) — kind=personnel 전용 HTTP 실측은 없으나 같은 함수 안 같은 분기"
    },
    {
      "part": "물(water) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_WATER)",
      "status": "measured: 위와 동일 — 같은 코드경로, kind=water 전용 HTTP 실측은 없음"
    },
    {
      "part": "헬기(helicopter) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_HELICOPTER) · POST /api/fws/missions/{event_id}/field-reply?kind=helicopter",
      "status": "measured: tests.test_fws_f2.F2_05_SupportRequestTest.test_support_request_reaches_field_reply — 200, kind=\"helicopter\" 응답 확인, field_replies 목록 도달도 직접 조회로 확인(SPEC/FWS-F2-05.json)"
    },
    {
      "part": "중장비(heavy_equipment) 지원 요청",
      "where": "backend/apps/fws/missions.py:request_support (SUPPORT_HEAVY_EQUIPMENT)",
      "status": "measured: 위와 동일 — 같은 코드경로, kind=heavy_equipment 전용 HTTP 실측은 없음"
    },
    {
      "part": "지휘 화면 배지(완결조건 — 명세서 §5.2 160행)",
      "where": "backend/apps/fws/missions.py:request_support 머리말(254-257행) — 명시적으로 범위 밖이라 적음",
      "status": "없음(범위 밖) — 코드 머리말이 직접 「새 배지 위젯은 이 차선(App 서버 쪽)의 범위 밖이라 만들지 않는다(§0.4 인접 — DSM 화면은 lane L 소유)」라고 적음. field_replies 목록 도달까지만 실측, 지휘 화면 UI 배지 자체는 미실측·미구현"
    }
  ]
}
```
