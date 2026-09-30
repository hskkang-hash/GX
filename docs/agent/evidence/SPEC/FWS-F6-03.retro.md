# FWS-F6-03 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-03.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-03",
  "title_parts": [
    {
      "part": "위험지수 수동 입력·기록",
      "where": "backend/apps/fws/integration.py::record_risk_forecast (POST /api/fws/liaison/risk-forecast)",
      "status": "있음 — 0~100 범위 검증(벗어나면 422, test_out_of_range_index_is_422 실측)"
    },
    {
      "part": "P-386 문턱(51/66/86)으로 위험 띠 계산",
      "where": "backend/apps/fws/constants.py::risk_index_band",
      "status": "있음 — 지수 70 → '경계' 띠 · test_record_then_read_back_band_from_p386_thresholds 실측"
    },
    {
      "part": "조회(재입력 값 재조회)",
      "where": "backend/apps/fws/integration.py::my_latest_risk_forecast (GET /api/fws/liaison/risk-forecast/mine)",
      "status": "있음 — POST 로 남긴 지수·띠가 GET 재조회에 그대로 남는다"
    },
    {
      "part": "산림과학원·산림청 API 연동(실시간 수신)",
      "where": "backend/apps/fws/integration.py:243-247 (머리말 주석 — 외부 자격증명·방화벽 규칙 필요, 대표 승인 필요라 범위 밖으로 적음)",
      "status": "없음 — annex 가 스스로 허락한 대안(\"API 또는 수동\") 중 '수동'만 지었다, 실시간 API 호출 코드는 없다"
    },
    {
      "part": "지자체 전체의 '지금 예보'(여러 사람이 입력한 값을 하나로 통합)",
      "where": "backend/apps/fws/integration.py::my_latest_risk_forecast (user_id=actor.pk 로 좁힘, line 269-272)",
      "status": "없음 — 감사 로그에 테넌트 칸이 없어 본인이 넣은 최신 값만 보인다(standby.py·missions.py 와 같은 한계), 여러 사람의 입력을 합치는 로직은 없다"
    }
  ]
}
```
