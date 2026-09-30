# W2A 턴 AQ 2물결 — 감시원·진화대 모바일 화면 · 진행 기록 (P-440)

- 시작: 규칙·retro 7절 읽음. 계획: F1-11(표) · F2-12(CSV 문+버튼) · F1-06(접근 불가+사진 1) · F2-03(이동 중 회신) · F2-13(임무에 훈련 배지) · F1-02(트랙 버튼) · F2-11(자원 배치판 해제 — F3 판 소유 밖, 열린 채 예상).
- 서버: missions.py(en_route · mine_csv · mission_detail 진행/훈련 배지) · verification.py(photo_id · replies) · api.py(FwsAPI 메서드 추가만).
- 화면: PatrolHome.tsx · FieldHome.tsx · 새 api_w2a.ts · copy_w2a.ts.
- 진행(약 50분): 서버·화면·새 시험 19 통과 · tsc 오류 0. retro 닫음: F1-11 · F2-12 · F1-06 · F2-03 · F2-13 (5절). F1-02 는 화면 행만 닫고 순찰함 등록 목록 대조 행 열림. F2-11 손대지 않음(자원 배치판은 F3 소유).
- 남은 것: test_fws_f2 · test_fws_app 회귀 확인 → 보고.
- 끝: 회귀 test_fws_f2+test_fws_app 30 통과 · test_fws_f5+route_tenant_scope+tenant_isolation 50 통과. 보고 제출.
