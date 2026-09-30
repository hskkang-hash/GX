# FWS-F6-07 — 사람이 확인한 제목 부분 표

P-431 · **손으로만 고친다** — 시험·쓰개가 이 파일을 쓰면 반쪽 게이트가 빨강이다.
기계 실측(요청/응답)은 옆 파일 `FWS-F6-07.json` 이다. 아래 json 블록 하나가 정본이다.

```json
{
  "id": "FWS-F6-07",
  "title_parts": [
    {
      "part": "대피 소요시간(P-386)",
      "where": "constants.evacuation_deadline_hours",
      "status": "있음"
    },
    {
      "part": "CBS 초안(재난문자 글자수 상한)",
      "where": "draft_evacuation_text — 표준 90자·확장 157자",
      "status": "있음"
    },
    {
      "part": "대피 지시 기록",
      "where": "liaison.evacuation_cbs_draft 감사",
      "status": "있음"
    },
    {
      "part": "산림청 스마트산림재난 앱 실제 푸시 발송",
      "where": "annex 원문 그대로 [미확인] — 열지 않는다",
      "status": "없음(세종 판정 · 결정 사항)",
      "excluded_by": "P-392",
      "excluded_why": "산림청 스마트산림재난 앱 실제 발송은 세종 판정으로 F6-07 범위 밖 — 웹푸시 훈련 채널이 이 절의 앱 푸시 연계다"
    },
    {
      "part": "앱 푸시 연계(제목이 부르는 것)",
      "where": "[턴 AN] POST .../evacuation-webpush-drill · kernels.k2_notify.send_webpush · 제목 [훈련] 고정 · drill: 표식(F6_07_WebpushDrillTest)",
      "status": "있음(대체 — 웹푸시 훈련 채널 · 실발송 아님)"
    }
  ],
  "retro": "P-419 재판정(턴 AP · N1) · 2026-09-29 · 턴 AO §3-1 그대로 확인 — 산림청 앱 실제 푸시는 excluded_by P-392(외부 기관 실연동 · P-428 범위에도 해당)로 닫힘, 웹푸시 훈련 채널이 이 절의 실제 앱 푸시 연계를 대체한다(정직하게 '대체'라 적음, 근사/대리 앞머리 아님). 빈 칸·열린 행 없음 — 깨끗함 유지(이상 없음)."
}
```
