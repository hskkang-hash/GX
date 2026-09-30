# N3 턴 AQ 체크포인트 (P-440)

- T+0:15 · 규칙·재판정·retro 9절 읽음. 계획: DSM 새 컴포넌트 3(M2 한 줄 · 통제 지점 표 · 영상 제공 연간 통계+U4-08 묶음) → EventDetail · ControlDashboard · Reports 에 한 줄씩 끼움(새 라우트 0). FWS: CommandHome(F4-13 목록·F4-09 tel·F3-16 투하 시각) · FieldHome/PatrolHome(F1-12·F2-15 근무 외 칸 · F2-07 경보 칸) · OfficeReport(F3-18 통계 기간 칸).
- 서버: office2 에 헬기 투하 시각 기록/조회 + fire_stats 투하 기준 준수율 · FwsCommandAPI 에 POST/GET /command/incidents/{id}/helicopter-drop · patrol_enforcement_stats 에 since/until.
- T+1:00 · 서버(office2 투하 기록·준수율·기간 칸 · api_command 두 문) + 화면(DSM 컴포넌트 3 · FWS 카드 2 · CommandHome · OfficeReport · Field/Patrol) 끝 · tsc 0. 다음: tests/test_aq_n3_screens.py → retro.
- T+1:25 · test_aq_n3_screens.py 18/18 통과. 다음: 이웃 시험(f3b·f4·라우트 대장) → retro 손질.
- T+1:45 · 이웃 시험 150/0 · retro 11 손질(닫힘: U3-01·U3-02·U4-07·U4-08·F2-07·F3-16·F3-18·F4-09·F4-13 전 행 · F1-12·F2-15 는 화면 행만 닫고 담당 초소 쓰임 행 열림). 보고 작성 끝.
