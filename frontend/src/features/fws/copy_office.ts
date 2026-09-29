/**
 * FWS F3(산림과 담당) 화면 언어 사전 — 턴 AN · 차선 N2 단독 소유.
 *
 * `../copy.ts`(공용, F1/F2/F5 언어)는 이 턴에 고치지 않는다 — 산림과 담당
 * 화면(`/fws/office`)의 문구는 전부 이 파일에서 온다(`copy.ts` 머리말과 같은
 * 규약 — 서버 스키마 값은 여기서도 바꾸지 않는다, 표시 이름만 둔다).
 */

export const FWS_OFFICE_COPY = {
  home: {
    title: '산림과 상황',
  },
  dashboard: {
    title: '산불 상황판',
    refreshButton: '새로고침',
    riskIndex: '위험지수',
    fireAlert: '위기경보',
    postDuty: '초소 근무',
    cameraStatus: '카메라 정상',
    ongoingIncidents: '진행 사건',
    resourceStandby: '자원 대기',
    onDutyOfSuffix: '명 근무 중',
  },
  season: {
    title: '조심기간·특별대책기간 설정',
    kindDry: '조심기간',
    kindSpecial: '특별대책기간',
    startPlaceholder: '시작일(YYYY-MM-DD)',
    endPlaceholder: '종료일(YYYY-MM-DD)',
    saveButton: '저장',
    savedNotice: '설정 저장됨',
  },
  posts: {
    title: '초소·순찰 구역 등록',
    kindWatchpost: '초소',
    kindPatrolZone: '순찰 구역',
    codePlaceholder: '코드',
    namePlaceholder: '이름',
    registerButton: '등록',
    registeredNotice: '등록됨',
  },
  roster: {
    title: '근무표 업로드(CSV)',
    csvPlaceholder: 'name,role,shift_date,shift_type,night_standby_5min',
    uploadButton: '업로드',
    uploadedSuffix: '행 저장됨',
    nightBadge: '야간 5분대기조',
  },
  incident: {
    title: '사건별 처리',
    eventIdPlaceholder: '사건 번호',
    verifyRequestButton: '확인 요청(1클릭)',
    verifyRequestSentSuffix: '분 시계 시작 · 발송됨',
    fireConfirmedButton: '산불 확정',
    falseAlarmButton: '오인 종결',
    intakeTitle: '신고 접수 기록',
    intakeSource119: '119',
    intakeSourceForest: '산림청',
    intakeSourceCitizen: '시민',
    intakeSaveButton: '접수 기록',
    intakeSavedNotice: '접수 기록됨(30분 시계 시작)',
    agencyNotifyTitle: '산림청 통보·헬기 요청',
    agencyPhonePrefix: '산림청 상황실',
    helicopterBasePlaceholder: '헬기 기지',
    helicopterEtaPlaceholder: '도착 예정(ISO 시각)',
    agencyNotifyButton: '통보 기록',
    agencyNotifiedNotice: '통보 기록됨',
    resourceTitle: '자원 배정',
    resourceKindCrew: '진화대',
    resourceKindVehicle: '차량',
    resourceKindDrone: '드론',
    resourceNamePlaceholder: '자원 이름',
    resourceAssignButton: '배정',
    resourceAssignedNotice: '배정됨(임무 문안 자동 발송)',
    stageTitle: '대응단계 제안',
    areaPlaceholder: '면적(ha)',
    windPlaceholder: '풍속(m/s)',
    buildingsPlaceholder: '시설 우려(건물 수)',
    stageProposeButton: '단계 제안',
    stageProposedPrefix: '제안 단계',
  },
} as const;
