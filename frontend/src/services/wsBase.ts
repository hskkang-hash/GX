/**
 * P-363 (턴 AK · 2026-09-27) — **웹소켓 주소는 화면이 온 곳을 따른다.**
 *
 * 무엇이 문제였나 [실측 2026-09-25 · 턴 AJ 번들 · 2026-09-27 8500]
 * ------------------------------------------------------------------
 * 소켓 주소가 `${VITE_STREAMING_WS}/ws/...` 였고, 8500 빌드의 그 값은
 * `ws://localhost:8000` 이었다. 대표 PC 밖의 브라우저에게 `localhost:8000` 은 **자기
 * 컴퓨터**다 — 바깥 사용자에게는 언제나 죽은 소켓이다(스테이징이 오는 날 빨강).
 *
 * 규칙 — 한 줄
 * ------------
 * **같은 출처 빌드**(`VITE_API_URL` 이 비었다 = API 도 화면이 온 곳으로 간다)이면 소켓도
 * 화면이 온 곳(`ws(s)://<지금 host>`)으로 간다. 따로 서버를 두는 빌드(`VITE_API_URL` 이
 * 있다)만 `VITE_STREAMING_WS` 를 쓴다. 두 값이 서로 다른 곳을 가리키는 빌드를 만들지 않는다.
 *
 * ⚠ 8500 nginx 에는 아직 `/ws/` 자리가 없다(실측 404) — 이 파일은 주소를 바로잡을 뿐
 *   받는 쪽을 세우지 않는다. 받는 쪽은 스테이징 nginx `/ws/` 프록시(ASGI)다.
 * ⚠ `features/delivery/**` 의 소켓은 §0.4 쪽이라 이 도우미를 안 부른다(표에 남김).
 */
export function wsBase(): string {
  const env = import.meta.env as Record<string, string | undefined>;
  if (!env.VITE_API_URL && typeof window !== 'undefined') {
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}`;
  }
  return env.VITE_STREAMING_WS ?? '';
}
