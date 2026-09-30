# N4 · 턴 AQ 체크포인트 (P-440)

- ① P-434 끝: `backend/apps/fws/safety_thresholds.py`(새 · 기관 곁표 감사 줄 저장 · 새 모델/마이그레이션 없음) · alerts.py `_threshold(scope, name)` 기관값 → constants(None) · `threshold_status` 대기/설정됨 · api_admin.py GET/POST `/api/fws/admin/safety-thresholds` · AdminHome `SafetyThresholdCard`(data-gx fws-threshold-*) · `api_admin_thresholds.ts`(새) · copy_admin `thresholds`. 시험 `test_aq_n4_thresholds.py` 5/5 + 기존 `test_ap_n2_fws_safety_alerts.py` 4/4. tsc 0. retro F2-07·F1-10 문턱 행 닫음.
- ② P-436 끝: `u4_evaluation_bundle_service.py` 가 K4 `render_html` 로 요약 PDF 를 ZIP 에 싣는다. 시험 `test_aq_n4_u4_08_pdf.py` 1/1. 기존 `test_ap_n4_u4_08_bundle.py:74` 는 `not_generated` 단정이라 빨강 — 소유 차선(Q)이 한 줄 고쳐야 한다. retro PDF 행 닫음 · 화면 버튼 없음 행 추가(열림).
- ③ U4-05(기상특보·피해 누계·동원·향후 계획) · F5-10(커널 계량 연계) — 코드로 닫을 것 없음(소유 밖 표·외부 연동) → 「출시 뒤」 후보.
