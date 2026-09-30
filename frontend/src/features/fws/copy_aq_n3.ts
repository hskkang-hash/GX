/**
 * FWS 잔여 화면 문구 — 턴 AQ · 차선 N3 단독 소유.
 *
 * 공용 `./copy.ts`(F1/F2/F5 언어)는 고치지 않는다. 이 파일은 M4 근무 외 알림 칸
 * (F1-12 · F2-15) · 진화대 안전 경보 칸(F2-07) · 기관 통계 기간 칸(F3-18)의 말만 쥔다.
 */
export const FWS_AQ_N3_COPY = {
  notifyPrefs: {
    title: '근무 외 알림 차단',
    startLabel: '차단 시작',
    endLabel: '차단 끝',
    postLabel: '담당 초소·구역',
    postPlaceholder: '예: 초소 번호',
    saveButton: '저장',
    savedNotice: '저장했습니다 — 저장된 값을 다시 불러왔습니다',
    currentLabel: '지금 저장된 값',
    notSet: '설정 안 함(모든 알림을 받습니다)',
    blockNote: '이 시간대에는 알림을 받지 않습니다 — 심각 경보는 예외로 받습니다.',
    failed: '저장하지 못했습니다',
    loadFailed: '설정을 불러오지 못했습니다',
  },
  safetyAlerts: {
    title: '안전 경보',
    ruleLabel: '경보 기준',
    waiting: '대기',
    waitingNote: '기관이 기준을 정하면 경보가 켜집니다',
    set: '설정됨',
    unacked: '확인 전',
    acked: '확인함',
    ackButton: '확인',
    empty: '받은 경보가 없습니다',
    eventLabel: '사건',
    loadFailed: '경보를 불러오지 못했습니다',
    ackFailed: '확인을 기록하지 못했습니다',
  },
  thresholdNames: {
    wind_shift_angle_deg: '풍향 급변 각도',
    wind_shift_window_minutes: '풍향 급변 시간창',
    drop_zone_exit_radius_m: '투하 구역 이탈 반경',
  } as Record<string, string>,
  heliDropStats: {
    label: '골든타임 준수율(신고 → 헬기 투하 30분)',
  },
  enforcementStats: {
    title: '계도·단속 통계',
    sinceLabel: '시작일',
    untilLabel: '종료일',
    totalLabel: '합계',
    guidance: '계도',
    enforcement: '단속',
    loadFailed: '통계를 불러오지 못했습니다',
  },
};
