/**
 * P-59 — **화면이 자기 버전을 말한다.**
 *
 * 값은 빌드가 넣는다(`vite.config.ts` 의 `define`). 이 파일이 하는 일은 셋이다:
 *   ① 치환이 **안 된 경우**를 막는다 — 없는 전역을 읽으면 화면이 통째로 죽는다.
 *   ② 「모른다」를 **지어내지 않는다** — 빈 값이면 사전의 말로 「알 수 없음」이라 적는다.
 *   ③ 지원 창구와 게이트가 읽을 자리를 **런타임에도** 하나 남긴다.
 *
 * ★ 왜 `typeof` 로 감싸나: `define` 은 **글자 치환**이다. 어떤 경로로든 치환이 안 된
 *   번들이 뜨면 `__GX_COMMIT__` 은 선언되지 않은 이름이고, 그것을 그냥 읽으면
 *   `ReferenceError` 다. 버전을 못 읽는 것 때문에 화면 전체가 안 뜨는 것은
 *   **고치려던 것보다 나쁜 고장**이다.
 */

declare global {
  /** 빌드가 넣는 커밋 해시(짧은 형 · 사람이 읽는다). 빈 문자열은 「모른다」다. */
  const __GX_COMMIT__: string;
  /**
   * 빌드가 넣는 **게이트용 리터럴 토큰** — `GX_COMMIT:<40자리 16진>`.
   * 온전한 해시를 못 구한 빌드에서는 **빈 문자열**이고, 그러면 `GX_COMMIT:` 이라는
   * 글자가 번들에 아예 안 남는다(차선 Q 규약 ①).
   */
  const __GX_COMMIT_TOKEN__: string;
}

/** 이 번들이 난 커밋. **빈 문자열이면 모르는 것이다** — 없는 것이 아니다. */
export const GX_COMMIT: string =
  typeof __GX_COMMIT__ === 'string' ? __GX_COMMIT__ : '';

/** 화면에 뜨는 글자. 사전 등재 표시는 「버전 3d40cf6」 꼴이다. */
export const VERSION_LABEL = GX_COMMIT ? `버전 ${GX_COMMIT}` : '버전 알 수 없음';

/**
 * 게이트가 번들에서 찾는 토큰. **여기서 조립하지 않는다** — 접두어까지 포함해
 * 빌드가 완성해 넣은 글자를 그대로 든다. 소스에서 이어 붙이면 그 문장이 번들에
 * 리터럴로 남는다는 보장이 없다(상수 접기 · 트리셰이킹).
 */
export const GX_COMMIT_TOKEN: string =
  typeof __GX_COMMIT_TOKEN__ === 'string' ? __GX_COMMIT_TOKEN__ : '';

/**
 * 런타임 자리 하나 — **지원 창구가 전화로 물을 때** 브라우저 콘솔 한 줄로 답한다.
 *
 * ★ 대괄호로 넣는다. 점 표기(`window.__GX_COMMIT__ = …`)로 쓰면 그 자리가
 *   `define` 의 치환 규칙과 눈으로 구별되지 않아, 읽는 사람이 「여기도 치환되나」를
 *   매번 되묻게 된다. 글자열 열쇠는 치환 대상이 아닌 것이 **문법으로** 분명하다.
 * ★ 번들 해시 게이트의 **둘째 증거**이기도 하다 — 머리표가 첫째다.
 */
if (typeof globalThis !== 'undefined') {
  const g = globalThis as unknown as Record<string, string>;
  g['__GX_COMMIT__'] = GX_COMMIT;
  // ★ 이 대입이 **토큰을 번들에 살려 두는 것**이기도 하다. 어디서도 안 쓰이는 값은
  //   트리셰이킹이 지운다 — 지워지면 게이트는 「말하지 않는 번들」을 보게 된다.
  g['__GX_COMMIT_TOKEN__'] = GX_COMMIT_TOKEN;
}
