/**
 * 감시원(F1)·진화대(F2) 화면 문구 — 턴 AQ · 2물결 차선 W2A 단독 소유.
 *
 * 공용 `./copy.ts` 는 고치지 않는다. 서버 값(`cannot_access` 등)은 여기서 표시 이름만 둔다.
 */
export const FWS_W2A_COPY = {
  patrolMine: {
    title: '내 근무 기록·순찰 실적',
    refresh: '새로 고침',
    colPeriod: '기간',
    colCheckins: '근무 시작',
    colTracks: 'GPS 트랙',
    colCheckpoints: '순찰함 통과',
    today: '오늘',
    week: '이번 주',
    asOfPrefix: '기준',
  },
  track: {
    title: '순찰 경로 기록',
    postPlaceholder: '초소 번호',
    gpsButton: '지금 위치 기록',
    checkpointPlaceholder: '순찰함 번호',
    checkpointButton: '순찰함 통과 기록',
    savedNotice: '기록했습니다 — 오늘 실적을 다시 불러왔습니다',
    noPosition: '위치를 확인하지 못했습니다 — 위치 권한을 확인해 주세요',
    needPost: '초소 번호를 먼저 입력해 주세요',
  },
  verify: {
    title: '확인 요청 회신',
    idPlaceholder: '확인 요청 번호',
    lookupButton: '불러오기',
    verdictPrefix: '판정',
    verdictNone: '판정 전',
    verdictConfirmed: '산불 확정',
    verdictRejected: '오인',
    reasonLabel: '오인 사유',
    photoLabel: '사진 1장(선택)',
    sentNotice: '회신했습니다 — 요청을 다시 불러왔습니다',
    repliesTitle: '보낸 회신',
    withPhoto: '사진 첨부',
    noReplies: '아직 보낸 회신이 없습니다',
  },
  mission: {
    enRouteButton: '이동 중',
    progressPrefix: '내 진행',
    progress: {
      dispatched: '출동',
      en_route: '이동 중',
      arrived: '도착',
      released: '철수·복귀',
    } as Record<string, string>,
    progressNone: '아직 회신 없음',
    trainingBadge: '훈련 임무',
    csvButton: 'CSV 내려받기(수당 근거)',
    csvDone: '내려받았습니다',
    totalPrefix: '총 투입',
    minutesSuffix: '분',
  },
} as const;
