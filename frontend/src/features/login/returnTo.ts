/**
 * 로그인이 필요한 주소로 온 사람을 **로그인 뒤 그 화면으로** 돌려보낸다 — WO-GRDX-20261002-06 AC-6.
 *
 * 무엇이 문제였나 [실측 2026-10-02 · 세종 클릭 · 영실 재측]
 *   `/dsm/queue` 를 직접 쳐서 온 사람은 아무 말 없이 로그인 화면을 보고, 로그인하면 **역할의 홈**으로
 *   갔다 — 가려던 화면은 잊혔다.
 *
 * 왜 여기서 고치나 — 관문은 이미 알려 주고 있었다
 *   인수 부품의 `PrivateRouter`(rj-core · 이 저장소에 소스 없음)는 `/login` 으로 보낼 때
 *   `state: { from: location }` 을 싣는다 [실측 · 배포 번들 `index-D7n8w_2e.js` 의 PrivateRouter 본문].
 *   로그인 화면이 그것을 **읽지 않았을 뿐**이다. 그래서 관문은 한 줄도 안 고치고 여기서 읽는다.
 *
 * 안전: 같은 출처의 화면 주소만 돌려보낸다 — `/` 로 시작하고 `//` 가 아니며 로그인 앞 화면이 아닌 것.
 *   (밖으로 튀는 주소는 `state` 로는 들어올 수 없지만, 읽는 쪽이 한 번 더 막는다.)
 */

/** 문구 — 지시서 AC-6 의 글자 그대로. */
export const LOGIN_REQUIRED = '로그인이 필요합니다';

const PUBLIC_PATHS = ['/login', '/forgot-password', '/reset-password', '/start'];

type FromLike = { pathname?: unknown; search?: unknown; hash?: unknown } | null | undefined;

/** `location.state` 에서 돌아갈 주소를 꺼낸다. 없거나 안전하지 않으면 `null`. */
export function returnPathFrom(state: unknown): string | null {
  const from = (state as { from?: FromLike } | null | undefined)?.from;
  const pathname = typeof from?.pathname === 'string' ? from.pathname : '';
  if (!pathname.startsWith('/') || pathname.startsWith('//')) return null;
  if (pathname === '/' || PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return null;
  }
  const search = typeof from?.search === 'string' ? from.search : '';
  const hash = typeof from?.hash === 'string' ? from.hash : '';
  return `${pathname}${search}${hash}`;
}
