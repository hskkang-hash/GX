import { useEffect } from 'react';

import './prelogin.css';

/**
 * 로그인 전 화면이 떠 있는 동안만 `<html>` 에 `data-gx-prelogin` 을 단다 — WO-GRDX-20261002-07 AC-1.
 *
 * 뿌리 글씨를 폭에 묶는 규칙(`index.css`·`Global.scss` 의 `html { font-size: calc(… vw) !important }`)은
 * 앱 전체의 것이라 지우지 않는다(로그인 뒤 화면의 겉모습은 이 지시서의 금지). 그 대신 로그인 전
 * 화면에서만 더 구체적인 `html[data-gx-prelogin]` 이 이긴다. 떠날 때 뗀다 — 남으면 로그인 뒤가 바뀐다.
 */
export function usePreloginRoot(): void {
  useEffect(() => {
    // 클래스가 아니라 속성이다 — 테마 코드가 `<html>` 의 className 을 통째로 덮어쓴다
    //   [실측 22:1x · 배포 뒤 `document.documentElement.className` = "light" — 단 클래스가 지워져 있었다].
    const root = document.documentElement;
    root.setAttribute('data-gx-prelogin', '');
    return () => root.removeAttribute('data-gx-prelogin');
  }, []);
}
