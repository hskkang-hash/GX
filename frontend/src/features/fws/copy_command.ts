/**
 * FWS F4(통합지휘본부장·상황실) 화면 언어 사전 — 턴 AO · 차선 N2 단독 소유.
 *
 * `../copy.ts`(공용, F1/F2/F5 언어)는 이 턴에 고치지 않는다 — 지휘 화면
 * (`/fws/command`)의 문구는 전부 이 파일에서 온다(`copy_office.ts` 머리말과
 * 같은 규약 — 서버 스키마 값은 여기서도 바꾸지 않는다, 표시 이름만 둔다).
 */

export const FWS_COMMAND_COPY = {
  home: {
    title: '산불 지휘',
    eventIdLabel: '사건 번호',
    loadButton: '지휘 화면 불러오기',
    loadFailed: '지휘 화면을 불러오지 못했습니다',
  },
  screen: {
    incidentTitle: '사건 개요',
    stageTitle: '대응단계',
    resourcesTitle: '자원 배정',
    clockTitle: '대응 시계',
    evacuationTitle: '대피 현황',
    commandPostTitle: '지휘본부',
    noneYet: '아직 없음',
  },
  stage: {
    title: '대응단계 확정·상향 · 지휘권 이양',
    stageLabel: '단계',
    reasonPlaceholder: '확정·상향 사유',
    commandLevelLabel: '지휘 수준(선택)',
    confirmButton: '확정',
    confirmedNotice: '대응단계 확정됨',
  },
  commandPost: {
    title: '통합지휘본부 설치 선언',
    addressPlaceholder: '설치 위치(주소)',
    orgPlaceholder: '구성 기관',
    situationRoomPhonePlaceholder: '시도 상황실 전화(선택)',
    declareButton: '설치 선언',
    declaredNotice: '지휘본부 설치 선언됨',
  },
  aircraft: {
    title: '헬기 요청 승인 · 투하구역 지정',
    orgPlaceholder: '요청 기관',
    baseLabel: '기지',
    etaLabel: '도착 예정',
    approveButton: '승인',
    approvedNotice: '헬기 요청 승인됨(30분 시계 시작)',
  },
  evacuation: {
    title: '대피 명령 승인 · 해제',
    urgencyImmediate: '즉시',
    urgencyPrepare: '준비',
    approveButton: '승인',
    releaseButton: '해제',
    approvedNotice: '대피 명령 승인됨',
    releasedNotice: '대피 해제됨',
  },
  agency: {
    title: '소방·경찰·군 협조 요청',
    agencyFire: '소방',
    agencyPolice: '경찰',
    agencyMilitary: '군',
    recordButton: '요청 기록',
    recordedNotice: '협조 요청 기록됨',
  },
  fireDeclaration: {
    title: '주불 진화·진화완료 선언',
    mainOutButton: '주불 진화 선언',
    extinguishedButton: '진화완료 선언',
    mainOutNotice: '주불 진화 선언됨',
    extinguishedNotice: '진화완료 선언됨',
  },
  hourlyReport: {
    title: '상황보고 승인(매시간)',
    approveButton: '승인',
    approvedNotice: '상황보고 승인됨',
  },
  contacts: {
    title: '연락처(1클릭)',
    forestService: '산림청 상황실',
    provincialRoom: '시도 상황실',
    unregistered: '미등록',
  },
  night: {
    title: '야간 전환',
    sunsetPlaceholder: '일몰 시각(ISO)',
    setButton: '일몰 시각 기록',
    helicopterAvailable: '헬기 가능',
    helicopterUnavailable: '헬기 불가',
  },
  meeting: {
    title: '상황판단회의 기록',
    attendeesPlaceholder: '참석자',
    decisionPlaceholder: '결정 사항',
    basisPlaceholder: '근거',
    recordButton: '기록',
    recordedNotice: '회의 기록됨',
  },
  priority: {
    title: '동시 다발 사건 우선순위',
    refreshButton: '새로고침',
  },
  postReport: {
    title: '사후 보고서 1쪽',
    downloadPdfButton: 'PDF 내려받기',
    summaryButton: '요약 보기',
    damagePending: '집계 전',
  },
};
