/**
 * FWS 기관 관리자(U5 · 산불 설정) 화면 언어 사전 — `copy.ts`(현장 근무자 언어)와
 * 다른 사전이다(턴 AN · 차선 N4). 관리자 화면은 문맥이 다르다(「등록」·「저장」 같은
 * 관리 동작 위주) — 같은 사전에 섞으면 다음 사람이 어느 화면 문구인지 코드만
 * 보고 못 가른다(`copy.ts` 머리말과 같은 판단).
 *
 * ★ 개발 용어·절 번호(`FWS-U5-01` 등)·영문 라벨은 화면에 내지 않는다 — 이 사전이
 *   그 대신 쓸 한국어 이름을 쥔다(규약 「셋째 조건」).
 */

export const FWS_ADMIN_COPY = {
  title: '산불 설정',
  camera: {
    title: '산불 감시 카메라 등록',
    listTitle: '카메라 목록',
    idPlaceholder: '카메라 번호',
    highlandLabel: '고지대',
    thermalChannelPlaceholder: '열화상 채널',
    ptzPresetsPlaceholder: 'PTZ 프리셋(쉼표로 구분)',
    radiusPolygonPlaceholder: '감시 반경 폴리곤(좌표 JSON)',
    saveButton: '표식 저장',
    savedSuffix: '에 산불 표식을 저장했습니다',
  },
  post: {
    title: '초소·순찰함(NFC)·순찰 구역',
    codePlaceholder: '초소 코드',
    namePlaceholder: '초소 이름',
    zonePlaceholder: '순찰 구역',
    latPlaceholder: '위도',
    lngPlaceholder: '경도',
    nfcBoxesPlaceholder: '순찰함(NFC) 코드(쉼표로 구분)',
    saveButton: '초소 등록',
    listTitle: '등록된 초소',
  },
  evac: {
    title: '마을·대피소·요양시설',
    kindLabel: '구분',
    kindVillage: '마을',
    kindShelter: '대피소',
    kindCareFacility: '요양시설',
    namePlaceholder: '이름',
    headcountVillagePlaceholder: '대피 대상 인원',
    headcountShelterPlaceholder: '수용 인원',
    saveButton: '등록',
    listTitle: '등록 목록',
    targetTotalPrefix: '대피 대상 총원(자동 산출)',
    capacityTotalPrefix: '대피소 수용 총원',
    coversOk: '수용 가능',
    coversShort: '수용 부족',
  },
  notify: {
    title: '산불 알림 규칙',
    severityLabel: '등급',
    roleLabel: '수신 역할',
    channelsPlaceholder: '채널(쉼표로 구분 — email,webhook 등)',
    nightStandbyLabel: '야간 5분대기조 채널로 저장',
    saveButton: '규칙 저장',
    testButton: '시험 발송',
    testSentSuffix: '건 훈련 채널로 나갔습니다(실채널 아님)',
    criticalBlockedWarning: '심각 등급을 받는 사람이 0명입니다',
    // 턴 AQ · 차선 W2C — 등급별 수신 표 · 야간 5분대기조 표시
    reachTitle: '등급별 수신',
    reachRecipientsSuffix: '명 수신',
    reachOk: '닿음',
    reachBlocked: '닿지 않음',
    rulesTitle: '저장된 규칙',
    nightStandbyTag: '야간 5분대기조',
    dayTag: '상시',
  },
  thresholds: {
    title: '안전경보 기준',
    intro: '풍향 급변·헬기 투하 구역 이탈 경보는 우리 기관이 정한 기준으로 울립니다.',
    windShiftAngle: '풍향 급변 각도',
    windShiftWindow: '풍향 급변 판단 시간',
    dropZoneExitRadius: '투하 구역 이탈 반경',
    unitDeg: '도',
    unitMinute: '분',
    unitMeter: 'm',
    waitingBadge: '대기',
    setBadge: '설정됨',
    waitingHint: '기관이 정하면 경보가 켜집니다',
    rangeAngle: '0보다 크고 180 이하로 입력하세요',
    rangePositive: '0보다 큰 값을 입력하세요',
    saveButton: '기준 저장',
    savedNotice: '안전경보 기준을 저장했습니다',
  },
  error: {
    generic: '요청이 실패했습니다',
  },
};

export const FWS_ADMIN_UNKNOWN = '확인 중';
