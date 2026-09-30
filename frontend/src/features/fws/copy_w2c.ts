/**
 * 드론 운용 화면(`/fws/drone`) 비행 기록 칸의 추가 문구 — 턴 AQ · 2물결 차선 W2C.
 *
 * `../copy.ts` 는 공용 사전(여러 차선이 함께 쓴다)이라 이 차선이 고치지 않는다 —
 * F5-08 「비행 기록·배터리·기체 상태」 재조회 표에 쓰는 말만 여기 둔다.
 */
export const FWS_DRONE_W2C_COPY = {
  myFlightsTitle: '내 비행 기록',
  airframeLabel: '기체',
  batteryLabel: '배터리',
  minutesLabel: '비행',
  minutesUnit: '분',
  loggedAtLabel: '기록 시각',
  sourceManual: '직접 입력',
  sourceDji: '기체 연동(DJI)',
  empty: '아직 비행 기록이 없습니다',
} as const;
