/**
 * FWS F3 산림과 담당 잔여(대피·상황보고·통계·훈련) 화면 언어 사전 — 턴 AN 차선 N3
 * 단독 소유. 공용 `../copy.ts` 는 이 턴에 고치지 않는다(§0.4 인접) — 이 화면의
 * 문구는 전부 여기서만 온다.
 *
 * 셋째 조건(화면 문구 규약): 한국어 · 개발 용어·절 번호(`D-123`·`P-123`)·영문
 * 라벨을 화면에 내지 않는다. 이 사전의 **값**(사람이 읽는 문자열)은 그 규약을
 * 따른다 — 객체 키(코드 식별자)는 규약 대상이 아니다.
 */

export const FWS_OFFICE2_COPY = {
  page: {
    title: '산림과 보고',
    subtitle: '대피 · 상황보고 · 통계 · 훈련',
  },
  common: {
    save: '저장',
    submit: '보내기',
    refresh: '새로고침',
    error: '잠시 후 다시 시도해 주세요',
    eventIdPlaceholder: '사건 번호',
  },
  evacuation: {
    title: '대피 계획',
    villageLabel: '마을',
    shelterLabel: '대피소',
    addVillageButton: '마을 추가',
    kindLabel: '대피 종류',
    kindRecommend: '권고',
    kindOrder: '지시',
    draftButton: '대피 초안 작성',
    draftDoneSuffix: '곳의 대피 초안을 작성했습니다 — 승인 대기 중입니다',
    progressTitle: '대피 이행 확인',
    completedLabel: '완료',
    remainingResidentsLabel: '잔류자 수',
    careFacilityLabel: '요양시설 대피 완료',
    noteLabel: '메모',
    recordProgressButton: '이행 확인 기록',
    statusTitle: '이행 현황',
    percentCompletePrefix: '이행률',
    remainingTotalPrefix: '전체 잔류자',
    careOpenPrefix: '요양시설 미완료',
  },
  hourlyReport: {
    title: '매시간 상황보고',
    personnelLabel: '투입 인력',
    equipmentLabel: '장비 현황',
    casualtiesLabel: '인명 피해',
    facilityLabel: '시설 위험',
    weatherLabel: '기상 상황',
    draftButton: '이번 시간 초안 작성',
    draftDoneSuffix: '번째 상황보고를 작성했습니다',
    exportTitle: '산림청 제출 항목',
  },
  finalReport: {
    title: '진화완료 보고',
    causeLabel: '발생 원인',
    causeHiker: '입산자 실화',
    causeBurning: '소각',
    causeCigarette: '담뱃불',
    causeBuilding: '건축물 화재',
    causeOther: '기타',
    areaLabel: '피해 면적(ha)',
    smsSentLabel: '재난문자 발송 여부',
    sunriseLabel: '일출 시각',
    sunsetLabel: '일몰 시각',
    fireInfoIdLabel: '산불정보 번호',
    saveButton: '진화완료 보고 저장',
    savedSuffix: '진화완료 보고를 저장했습니다',
  },
  stats: {
    title: '산불 통계',
    occurrenceLabel: '발생 건수',
    areaLabel: '피해 면적 합계',
    causeLabel: '원인별',
    hourLabel: '시간대별',
    zoneLabel: '구역별',
    falseAlarmRateLabel: '오인율',
    verificationTimeLabel: '평균 확인 시간(초)',
    goldenTimeLabel: '골든타임 준수율(근사)',
    goldenTimeNote: '헬기 투하·지상 도달 실제 시각이 아니라 확인 회신 시각으로 '
      + '근사한 값입니다',
  },
  camera: {
    title: '카메라 오탐률',
    rateLabel: '오탐률',
    reasonLabel: '오인 사유',
    thresholdLabel: '임계값(%)',
    runTestButton: '임계값 시험 실행',
    resultPass: '기준 이내',
    resultFail: '기준 초과',
    resultUnmeasurable: '측정 불가',
  },
  patrol: {
    title: '계도 · 단속',
    kindGuidance: '계도',
    kindEnforcement: '단속',
    locationLabel: '장소',
    recordButton: '기록하기',
    statsTitle: '내 실적',
    zoneTitle: '입산통제구역',
    zoneNameLabel: '구역 이름',
    zoneActive: '통제 중',
    zoneLifted: '해제',
    setZoneButton: '구역 설정',
  },
  drill: {
    title: '훈련 시나리오',
    reasonLabel: '훈련 사유',
    startButton: '훈련 시작',
    endButton: '훈련 종료',
    inProgress: '훈련 진행 중',
    notRunning: '지금 훈련 중이 아닙니다',
    realChannelSendsPrefix: '실제 발송 건수',
  },
  onboarding: {
    title: '시작 카드',
    donePrefix: '진행률',
  },
} as const;

export const FWS_OFFICE2_UNKNOWN = '확인되지 않음';
