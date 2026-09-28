/**
 * FWS(산불감시) 화면 경로 — 한 곳에서만 정한다(`features/dsm/routes.ts` 와 같은 규약).
 *
 * P-357: FWS 는 새 앱이 아니다 — 같은 SPA 안 `/fws/*` 가지 하나다. `App.tsx` 의
 * `CustomRoutes`(공용 파일 · 여러 차선이 같이 씀)를 고치지 않고 이 파일 하나로
 * 좁힌다 — `dsm2Routes` 가 이미 세운 판단과 같다.
 *
 * ⚠ `/fws/home` 은 최상위 리터럴이라 다른 어떤 가지의 변수 조각도 삼키지 않는다.
 */
export const fwsRoutes = {
  /** FM1·FM2 현장 홈 — 체크인·오늘 위험도·확인 요청·알림·설정을 한 화면에 모은다. */
  home: { title: '산불감시 현장', path: '/fws/home' },
  /** FM3 진화대 홈(턴 AL · F2) — 대기 상태·임무·지원 요청·훈련 배지·장비 점검을
   * 한 화면에 모은다. `/fws/home` 과 형제 가지 — 최상위 리터럴이라 서로 안 삼킨다. */
  field: { title: '진화대 현장', path: '/fws/field' },
  /** F5 드론 운용자 홈(턴 AM · 세종 판정 P-387) — 정찰 요청·상태·열점·화선·확인
   * 회신·비행 기록을 한 화면에 모은다. `/fws/home`·`/fws/field` 와 형제 가지 —
   * 최상위 리터럴이라 서로 안 삼킨다. */
  drone: { title: '드론 운용', path: '/fws/drone' },
};
