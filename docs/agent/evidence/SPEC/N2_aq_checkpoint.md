# N2 턴 AQ 체크포인트 — O 운영 콘솔 보드

## 상태: 끝 (보고 제출)

- 화면: `frontend/src/features/ops/components/` 보드 10 + BoardFrame + useOpsBoard · OpsHome 탭 10 · api.ts 면 확장 · copy.ts 문구. tsc 오류 0.
- 서버(소유 파일만): ops_an_service.py — issue_tenant(departments= → user.Department 행) · list_tenants(region·departments) · toggle_seed(deploy_scenario/end_scenario → stream_monitors drill 스위치 실제 켬/끔) · seed_board(drill_by_tenant). api_ops_an.py — 발급 문에 departments 질의 1. 새 라우트 0.
- 시험: backend/tests/test_aq_n2_ops_boards.py 22 통과(DB_TEST_NAME=test_gx_aq_n2). 회귀: test_ops_an · test_ap_n3_o10_o11_ops · test_ap_n3_o01_proxy · test_ops_an_gate_can_fail · test_verify_spec_ops_gate_can_fail · test_f05_event_api 통과.
- retro: 닫힘 O-01 · 06 · 07 · 08 · 09 · 10 · 11 · 12 (8). 열린 채: O-02(유령 시드 자동 · 빠진 행 시드 소유권) · O-05(5xx · 게이트 16색).
