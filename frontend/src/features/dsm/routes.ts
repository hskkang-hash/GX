/**
 * 2파 DSM 화면들의 경로 — **한 곳에서만 정한다** (차선 C · 2026-09-24).
 *
 * ★ `services/API.ts` 의 `CustomRoutes` 에 넣지 않은 이유: 그 파일은 여러 차선이
 *   같이 쓰는 공용 자리다. 이번 파에 S·Q·E3·C 넷이 동시에 도니까 그 파일을 고치면
 *   병합에서 충돌하고, 충돌한 쪽은 대개 **경로 문자열**이며 그 충돌은 **라우팅 침묵**으로
 *   나타난다 — 화면이 안 뜨는데 오류도 안 난다. 차선 D 가 `features/mobile/routes.ts` 로
 *   같은 판단을 이미 했고, 여기서도 같게 한다.
 *
 * ★ **무계정 링크 금지**(불변 제약). 이 셋은 전부 `PrivateLayout` + `Sidebar` 아래에
 *   등록한다 — 토큰이 없으면 `/login` 으로 튕긴다.
 *
 * ⚠ 기존 `/dsm/events/:id` 보다 **뒤에 오지 않게** 한다. `:id` 는 변수 조각이라
 *   `/dsm/events/queue` 같은 리터럴을 삼킬 수 있다 — 그래서 큐는 `/dsm/queue` 로
 *   **다른 가지**에 둔다. 삼킬 수 없는 자리에 두는 것이 순서를 외우는 것보다 안전하다.
 */
export const dsm2Routes = {
  /** UX-13 단일 초점 큐. W1 최상단이 목록이 아니라 「가장 급한 하나」가 되는 화면. */
  focusQueue: { title: '단일 초점 큐', path: '/dsm/queue' },
  /** UX-17 훈련 모드 스위치 + 종료 보고서. */
  drill: { title: '훈련 모드', path: '/dsm/drill' },
  /** UX-18 벌크 등록 (dry-run 먼저). */
  cameraImport: { title: '카메라 벌크 등록', path: '/dsm/cameras/import' },
} as const;
