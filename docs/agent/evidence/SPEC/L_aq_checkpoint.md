# 차선 L · 턴 AQ 체크포인트 (P-440)

- 09-30 T+0:20 — 규칙·WO-20·아홉째 회차(`ONB-T/turn_ap_9.json`) 읽음. 반 7 · 빨강 10 확인.
- 측정기 술어 읽는 중(`scripts/measure_onboarding_t.py` rows_u1~u6).
- 첫 발견: U5#14 셋째 조건 「절 ID」 = `/dsm/system` 백업 카드 「누가 정했나」 칸이 `back.source`
  (settings.RETENTION_DECLARATION_SOURCE "… 세종 P-67 …") 를 원문으로 그린다 — 턴 AP 고침(넷)이 빠뜨린 다섯째 자리.
- T+0:50 — 술어 대조 끝. 발견: ① U2#4 술어는 `img` 의 **src 에 'snapshot'** 을 본다(data-gx 안 봄) — 턴 AP 가 단 data-gx 는 술어 밖, blob: src 라 0.
  ② U1#8·U2#2·U4#15 — 씨앗(capture_screens.seed_events)이 **probe 표식**(track_id)이라 고객 목록(P-220 include_probe=False)에서 빠진다 — 씨앗을 더 심어도 목록 행은 0.
  ③ U5#15 — 라이브 gunicorn 에 GX_STORAGE_CAPACITY_GB 선언 있음(길이만 확인) · /dsm/metering 화면은 % 를 그리는 칸 자체가 없다.
  ④ U4#9 — 화면이 /clip 을 안 불러 측정기 대체 호출이 JWT 없이 401.
  고칠 것: SystemSettings back.source · EventSnapshot src · Metering 저장 % · EventDetail clip 티켓.
- T+1:20 — 고침 넷 끝: SystemSettings.tsx(누가 정했나 safeFreeText) · EventSnapshot.tsx(img src `#snapshot-<id>`) ·
  Metering.tsx(저장 용량 상한 대비 % · why/definitions safeFreeText) · EventDetail.tsx(GET …/clip 호출 · 404=null).
  tsc 오류 0. 시험 `backend/tests/test_aq_l_onboarding_cells.py` 돌리는 중. 다음: 장부 「c 확정 표 — 최신(턴 AQ)」 절.
- T+1:45 — 장부 절 「c 확정 표 — 최신(턴 AQ)」 추가(옛 c 표 셋 〔역사〕 표기 · c_rows 옛 줄 이름 바꿈 · 삭제 0). SystemSettings 「누가 정했나」 칸이 둘(policy·back) — 둘 다 고침.
  tsc 오류 0. 시험 재실행 중(조율자 지시 `-e DB_TEST_NAME=test_gx_aq_l`). 첫 실행 12 통과 · 2 실패(칸 둘 발견 · clip HTTP) → 고치는 중.
- T+2:05 — 끝. `test_aq_l_onboarding_cells.py` 15 통과 · 이웃 시험(test_ao_l_screen_language · test_ap_l_click_declares · test_u24_empty_states) 39 통과 · tsc 오류 0. 보고 제출.
