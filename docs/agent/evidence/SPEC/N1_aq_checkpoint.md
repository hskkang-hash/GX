# N1 · 턴 AQ 체크포인트 (P-440) — F4 지휘 화면 배선

상태: **끝남** (2026-09-30).

- 서버 문: F4 쓰기·조회 문이 전부 이미 있었다(`api_command.py`) — 새 서버 문 0 · 백엔드 코드 수정 0.
- 프런트: `api.ts`(fwsCommandEndpoint · 캐시 우회 fwsGetFresh · fwsGetBlob) · `copy_command.ts`(문구) ·
  `CommandHome.tsx`(절별 버튼·칸 `data-gx="fws-f4-XX-<동작>"` · 누른 뒤 `refreshAll` 이 조회 GET 11개 재호출).
- 시험: `backend/tests/test_aq_n1_f4_command_wiring.py` 13 통과(절 12 + 정적 대조 1) ·
  `DB_TEST_NAME=test_gx_aq_n1` 로 돌렸다(기본 이름은 다른 차선과 부딪쳐 DuplicateTable).
- tsc 오류 0.
- retro: 닫음 10(F4-02·03·04·05·06·07·08·10·11·12) · 반쪽 유지 2(F4-01 지도·화선·한 화면 행 ·
  F4-15 HWPX 행 — P-392 는 U4-01 결정이라 붙이지 않았다).
