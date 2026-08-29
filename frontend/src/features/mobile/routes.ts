/**
 * 모바일(U3 · 이동 중) 화면의 경로 — **한 곳에서만 정한다.**
 *
 * ★ `services/API.ts` 의 `CustomRoutes` 에 넣지 않은 이유: 그 파일은 이번 턴에
 *   여러 차선이 같이 쓰는 공용 자리다. 차선 D 가 그 파일을 고치면 병합에서 충돌하고,
 *   충돌한 쪽은 대개 **경로 문자열**이며 그 충돌은 라우팅 침묵으로 나타난다
 *   (라우트 삼킴 — 선언 순서가 곧 라우팅이다). 여기서 정하고 App.tsx 가 읽는다.
 *
 * ★ **무계정 링크 금지**(불변 제약). 이 경로들은 전부 `PrivateRouter` 아래에 등록한다 —
 *   모바일은 링크로 들어오지만 **링크가 인증을 대신하지 않는다.** 토큰이 없으면
 *   `/login` 으로 튕기고, 그것이 이 화면의 유일한 진입 규약이다.
 */
export const mobileRoutes = {
  title: '이동 중 수신 모드',
  /** M1 — 내게 온 이벤트(발송 기록 기준). */
  inbox: { title: '내게 온 이벤트', path: '/m/inbox' },
  /** M2 — 현장 상세. 목록에서 고른 값을 쓰지 않고 **서버에 다시 묻는다**. */
  eventDetail: { title: '현장 상세', path: '/m/events/:id' },
} as const;

/** 상세 경로를 만든다. 문자열 조립을 화면마다 흩지 않는다. */
export function mobileEventDetailPath(eventId: number | string): string {
  return `/m/events/${eventId}`;
}
