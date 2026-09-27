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
};
