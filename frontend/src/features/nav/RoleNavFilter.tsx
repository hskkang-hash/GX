/**
 * P-122 · UX-28 — **표(`roleNav.ts`)를 사이드바에 적용하는 한 조각.** (턴 O · 차선 C2)
 *
 * 그리는 것이 없다(`null` 을 돌려준다). 하는 일은 하나다:
 * 인수 사이드바가 읽는 **메뉴 목록**을 역할의 표대로 갈아 끼운다.
 *
 * 왜 인수 사이드바를 고치지 않고 목록을 바꾸나
 * --------------------------------------------
 * 사이드바(`rj-core` 의 `CustomSidebar`)는 인수 자산이다. 그 안을 고치면 그 화면이
 * **인수 자산이 아니라 우리 빚**이 된다(UX-03 의 「처음이세요?」와 같은 규율).
 * 사이드바가 읽는 자리는 하나뿐이고(`useMenuData`), 그 자리는 인수 코드가
 * **바꿔 쓰라고 내준 문**이다 — 목록을 넣는 함수를 같은 훅이 돌려준다.
 *
 * ★★ **가리는 것이지 지우는 것이 아니다.**
 *   · dj-core `Menu`·`RoleMenu` 행은 한 줄도 안 바뀐다.
 *   · 라우터의 라우트도 그대로다 — 주소를 치면 들어간다.
 *   · 권한은 **서버가** 판정한다(SEC-11a · P-105). 이 파일은 구멍을 막지 않는다.
 *     막았다고 적으면 다음 사람이 서버 쪽을 안 본다.
 *
 * ⚠ **모르는 계정에서는 아무 일도 하지 않는다.** 역할이 표의 넷 중 어디에도 안
 *   맞으면(`bucketOf` 가 `null`) 인수 사이드바가 원래대로 뜬다. 그 자리를
 *   「빈 목록」으로 떨어뜨리면 사이드바가 **통째로 사라지고**, 그것은 가림이
 *   아니라 고장이다 — 그리고 고장은 「메뉴가 없는 역할」과 구별되지 않는다.
 */
import { useEffect } from 'react';
import { useMenuData, useUserInfo } from 'rj-core';

import type { MenuNode } from './roleNav';
import { bucketOf, filterNav, navSignature, roleCodesOf } from './roleNav';

export default function RoleNavFilter(): null {
  const userInfo = useUserInfo();
  const [menus, setMenus] = useMenuData();

  useEffect(() => {
    const list = (Array.isArray(menus) ? menus : []) as MenuNode[];
    // 아직 안 왔다. **없는 것과 안 온 것을 가른다** — 안 온 동안에는 아무것도 안 한다.
    if (list.length === 0) return;

    const bucket = bucketOf(roleCodesOf(userInfo));
    if (!bucket) return;

    const next = filterNav(list, bucket);
    // 표대로 자른 결과가 **비면 쓰지 않는다.** 빈 사이드바는 결정이 아니라 사고다.
    if (next.length === 0) return;
    // 이미 같은 모양이면 다시 쓰지 않는다 — 쓰면 이 훅이 다시 돌고, 끝나지 않는다.
    if (navSignature(list) === navSignature(next)) return;

    setMenus(next);
  }, [menus, setMenus, userInfo]);

  return null;
}
