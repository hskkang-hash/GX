/**
 * P-471 — 라우터 설정 전체에서 **사이드바 밑 라우트**마다 `RoleRouteGuard` 를 씌운다.
 *
 * 라우트를 하나씩 손으로 감싸지 않는 이유: 감싸는 손이 곧 빠뜨리는 손이다(D-348 · P-83 의
 * 「올리지 않은 접두가 구멍」과 같은 모양). 새 라우트가 사이드바 밑에 서면 **저절로** 가드가
 * 붙는다 — 표(`roleScreens.json`)에 없는 주소는 「플랫폼 운영자 화면」으로 세므로, 표를
 * 안 고친 새 화면은 열리지 않고 **눈에 띈다**(조용히 열리지 않는다).
 *
 * 건드리지 않는 것: 사이드바가 아닌 가지(로그인·월 모드·온보딩), `*`(없는 주소),
 * 리다이렉트(`Navigate`)와 element 가 없는 줄.
 */
import { Navigate } from 'react-router-dom';
import type { ReactElement } from 'react';
import type { RouteObject } from 'react-router-dom';

import RoleRouteGuard from './RoleRouteGuard';

function guardOne(route: RouteObject): RouteObject {
  const el = route.element as ReactElement | null | undefined;
  if (!el || route.path === '*') return route;
  if ((el as ReactElement).type === Navigate) return route;
  return { ...route, element: <RoleRouteGuard>{el}</RoleRouteGuard> };
}

export function withRoleGuard(sidebar: ReactElement, routes: RouteObject[]): RouteObject[] {
  const walk = (list: RouteObject[]): RouteObject[] =>
    list.map((r) => {
      if (r.element && (r.element as ReactElement).type === sidebar.type && r.children) {
        return { ...r, children: r.children.map(guardOne) };
      }
      return r.children ? { ...r, children: walk(r.children) } : r;
    });
  return walk(routes);
}
