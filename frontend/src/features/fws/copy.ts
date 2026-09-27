/**
 * FWS(산불감시) 사용자 언어 사전 — `features/dsm/copy.ts` 와 같은 규약(P-27 · P-29 ·
 * P-357). **산불판 문구는 이 사전에 먼저 넣고 쓴다** — 화면 코드에 직접 짓지 않는다.
 *
 * DSM 사전을 재사용하지 않는 이유: 그 파일은 관제요원(U*) 언어이고, 이 화면은
 * 산불 현장 근무자(FM1·FM2) 언어다 — 같은 낱말이라도 문맥이 다르면(「사건」 vs
 * 「초소」) 한 사전에 섞으면 다음 사람이 어느 쪽 화면인지 코드만 보고 못 가른다.
 * 서버 스키마 값(`fire_confirmed` 등)은 여기서도 바꾸지 않는다 — 표시 이름만 둔다.
 */

export const FWS_COPY = {
  home: {
    title: '산불감시 현장',
    checkinButton: '근무 시작(체크인)',
    checkinDone: '근무 중',
    riskLevelPrefix: '오늘 위험도',
    mountainBannedLabel: '입산통제 중',
    reportFireButton: '119 신고',
    reportForestButton: '산림청 신고',
  },
  risk: {
    관심: '관심',
    주의: '주의',
    경계: '경계',
    심각: '심각',
  },
  verification: {
    title: '확인 요청',
    fireConfirmed: '산불 맞음',
    falseAlarm: '소각·오인',
    cannotAccess: '접근 불가',
  },
  falseAlarmReason: {
    agri_burning: '농산 부산물 소각',
    smoking: '흡연',
    fog_or_cloud: '안개·구름',
    dust_or_steam: '분진·수증기',
    other: '기타',
  },
  alerts: {
    title: '안전 알림',
    ackButton: '확인',
    acked: '확인함',
  },
  prefs: {
    title: '알림 설정',
    quietHours: '근무 외 알림 차단 시간',
    assignedPost: '담당 초소',
    save: '저장',
  },
  error: {
    generic: '잠시 후 다시 시도해 주세요',
    unauthenticated: '다시 로그인해 주세요',
  },
} as const;

/** 모르는 값이 왔을 때 그릴 말 — 원문(서버 코드)을 화면에 흘리지 않는다. */
export const FWS_UNKNOWN = '확인 중';
