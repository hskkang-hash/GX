# FWS-F3-16 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F3-16.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F3-16",
  "title_parts": [
    {
      "part": "발생",
      "where": "응답 occurrence_count",
      "status": "구현 — 2건 이상 실측"
    },
    {
      "part": "면적",
      "where": "응답 area_ha_total(F3-14 최종보고 되짚기)",
      "status": "구현 — 5.5ha 실측"
    },
    {
      "part": "원인",
      "where": "응답 cause_breakdown",
      "status": "구현 — 입산자실화 1건 실측"
    },
    {
      "part": "시간대",
      "where": "응답 by_hour",
      "status": "구현 — 시각별 집계 실측"
    },
    {
      "part": "구역",
      "where": "응답 by_zone",
      "status": "구현 — 카메라 이름별 집계 실측"
    },
    {
      "part": "오인율",
      "where": "응답 false_alarm_rate_pct",
      "status": "구현 — 판정된 2건 중 오인 1건 실측"
    },
    {
      "part": "확인 시간",
      "where": "응답 verification_seconds_avg",
      "status": "구현 — occurred_at→reviewed_at 평균 실측"
    },
    {
      "part": "골든타임 준수율 — 대응 시계 실측(신고 접수 → 현장 도착 30분)",
      "where": "office2.py::_golden_time_from_response_clock → stream_monitors/services/response_clock.py::stamps_for (arrived_at) + F3-06 신고 접수 clock_started_at · 응답 golden_time_compliance_pct·golden_time_measured_n·golden_time_compliant_n",
      "status": "measured: 세 사건(45분 초과 · 5분 준수 · 발생 50분 전이나 신고 10분 전 → 준수)에서 3건 중 2건 = 66.7% — 신고 기준이 실제로 읽힘(발생 기준이면 33.3%)"
    },
    {
      "part": "골든타임 준수율 — 헬기 물 투하 시각(신고 → 투하 30분)",
      "where": "저장 칸: frontend/src/features/fws/pages/CommandHome.tsx F4-04 헬기 카드::data-gx=fws-f3-16-dropped-at · fws-f3-16-drop-save · fws-f3-16-drops(재조회 표시) · POST·GET /api/fws/command/incidents/{id}/helicopter-drop → backend/apps/fws/office2.py::record_helicopter_drop·helicopter_drops · 집계: office2.fire_stats heli_drop_compliance_pct·heli_drop_measured_n·heli_drop_compliant_n(신고 접수 F3-06, 없으면 발생 → 첫 투하 · 30분 = GOLDEN_TIME_THRESHOLD_SEC 그대로) · 통계 화면 OfficeReport.tsx::fws-f3-16-heli-drop-pct",
      "status": "measured: tests.test_aq_n3_screens.FwsF3_16HeliDropScreenTest — 저장 뒤 GET 재조회에 count 1·first_dropped_at · 발생 20분 전·투하 5분 전(준수) + 발생 2시간 전·투하 10분 전(초과) + 기록 없음(분모 밖) → 2건 중 1 = 50.0% · 미래 시각 422 · 다른 테넌트 404·통계 0"
    }
  ],
  "retro": "P-421 채움 · 확인한 것 — 턴 AP 차선 N2b · 2026-09-29 · 골든타임을 「확인 회신 30분」 근사에서 대응 시계 arrived_at 실측으로 바꾸고, 신고 접수 기준이 실제로 읽히는지(66.7% vs 발생 기준 33.3%) 대조했다. 헬기 투하 시각은 저장소에 없어 열린 행으로 남긴다 — 앞 판의 excluded_by P-428 은 뺐다(코드 결손이지 외부 실연동이 아니다 · TITLE_PARTS §3). | 턴 AQ 차선 N3 · 화면 배선 · 사람 확인 · 2026-09-30 · 헬기 물 투하 시각이 저장소에 없던 결손을 지휘 화면 F4-04 카드의 저장 칸으로 채우고, 그 기록을 읽는 준수율을 따로 낸다(새 숫자 0)."
}
```
