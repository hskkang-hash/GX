# FWS-F4-13 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F4-13.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F4-13",
  "title_parts": [
    {
      "part": "동시 다발 사건 목록",
      "where": "GET /api/fws/command/incidents?sort=risk → 응답 items(dsm_services.recent_events 재사용 · 진행 중 사건만)",
      "status": "measured: 네 사건이 한 목록에 선다"
    },
    {
      "part": "위험도 — 사건별 산불위험지수(0~100) 기록",
      "where": "POST /api/fws/command/incidents/{id}/risk-index → command.py::record_incident_risk_index(구간은 fws_constants.risk_index_band — F6-03 과 같은 함수)",
      "status": "measured: 86→심각 · 85.9→경계 · 51→주의(문턱 경계) · 100.5 는 422"
    },
    {
      "part": "정렬(완결조건) — 산불위험지수 51/66/86 눈금, 등급 근사 아님",
      "where": "command.py::priority_queue 가 사건별 최신 기록 지수를 읽어 내림차순(_latest_risk_index_by_event · 한 질의) · 응답 items[].risk_index·risk_band · risk_scale",
      "status": "measured: 등급을 거꾸로 심은 네 사건(info=86 · warning=85.9 · critical=51 · critical=기록 없음)이 지수 순 86 > 85.9 > 51 > 없음 으로 선다 — 등급 정렬이면 빨강. 기록 없는 사건은 risk_index=null 로 뒤(지어내지 않는다)"
    },
    {
      "part": "화면 — 지휘 화면(FW-01)의 우선순위 목록",
      "where": "frontend/src/features/fws/pages/CommandHome.tsx 우선순위 카드::data-gx=fws-f4-13-list · fws-f4-13-risk(지수·구간) · fws-f4-13-risk-input · fws-f4-13-record · fws-f4-13-refresh · fws-f4-13-open · GET /api/fws/command/incidents?sort=risk · POST .../{id}/risk-index",
      "status": "measured: tests.test_aq_n3_screens.FwsF4_09_13ScreenTest.test_risk_record_then_list_refetch_reorders — 51·86 기록 뒤 목록 재조회 86 > 51 · 51 이던 사건을 90 으로 고치면 재조회 순서가 뒤집힘 · 다른 테넌트 목록에 없음 · 소스 정적 대조(기록 뒤 refreshPriority)"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 정렬 키를 K1 등급(→문턱 근사)에서 사건별 기록 지수로 바꾸고, 등급을 거꾸로 심은 네 사건으로 등급 정렬이면 빨강이 되게 쟀다. 86/85.9 경계 확인. 지휘 화면 목록은 없다(열린 행). | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 지휘 화면에 위험도 목록과 지수 입력 칸을 그렸다(기록 뒤 목록 재조회)."
}
```
