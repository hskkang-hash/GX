/**
 * P-471 · P-293 — **메뉴 밖 화면은 통째로 「이 화면은 ○○ 역할 화면입니다」.** (턴 AS · 차선 S)
 *
 * 무엇이 있었나 [실측 2026-09-30 · 턴 AR · V · 관제요원 U1 계정 · 8500]
 *   메뉴에 없는 10 라우트를 주소로 열었다:
 *     `/dsm/reports` · `/dsm/system` · `/dsm/notify` · `/roles` — 전체 셸이 뜨고 「권한이 없」
 *       한 줄이 섞인 **반쪽**
 *     `/dsm/people` · `/users` · `/device` · `/report-template` · `/dsm/cameras/import` ·
 *       `/dsm/team-status` — 거절 없이 **그냥 열림**
 *   메뉴(`roleNav.ts`)는 5줄로 자르는데 라우트에는 가드가 없었다. 두 표가 따로였다.
 *
 * 이 파일이 하는 일
 *   판정은 `roleNav.ts::routeVerdict` 한 곳이 한다 — 그 표(`roleScreens.json`)는 메뉴도
 *   함께 만든다. 이 컴포넌트는 판정을 **화면 통째**로 옮길 뿐이다: 허용이면 자식을 그대로
 *   그리고, 아니면 자식을 **아예 마운트하지 않는다**(= 그 화면의 API 를 부르지 않는다 —
 *   반쪽 화면이 만들던 403 요청 자체가 없다).
 *
 * ★★ 이것은 **자물쇠가 아니다.** 자료를 막는 것은 서버다(`common/role_gate.py` ·
 *   각 라우트의 문지기). 이 가드는 「열렸는데 반쯤 비어 있는 화면」을 없애는 화면 결정이다.
 *   그래서 사람(버킷)을 모르는 계정(전역 관리자·역할 0·배송 역할)은 막지 않는다 —
 *   모르는 것을 막으면 빈 화면이 사고가 된다.
 */
import type { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useUserInfo } from 'rj-core';

import { ROLE_HOME } from './roleHome';
import { bucketOf, roleCodesOf, routeVerdict } from './roleNav';

export function RoleRouteNotice({ ownerText, home }: { ownerText: string; home: string }) {
  return (
    <div
      role="alert"
      data-testid="role-route-notice"
      style={{
        margin: '48px auto',
        maxWidth: 560,
        padding: '28px 32px',
        border: '1px solid #d0d5dd',
        borderRadius: 8,
        background: '#fff',
        fontSize: 16,
        lineHeight: 1.7,
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>
        이 화면은 {ownerText} 역할 화면입니다
      </div>
      <div style={{ fontSize: 14, color: '#475467', marginBottom: 16 }}>
        지금 계정의 역할로는 열 수 없습니다. 필요하면 관리자에게 알려 주세요.
      </div>
      <Link to={home} style={{ fontSize: 14 }}>
        내 화면으로 돌아가기
      </Link>
    </div>
  );
}

export default function RoleRouteGuard({ children }: { children: ReactNode }) {
  const userInfo = useUserInfo();
  const { pathname } = useLocation();
  const bucket = bucketOf(roleCodesOf(userInfo));
  const verdict = routeVerdict(bucket, pathname);
  if (verdict.allowed || !bucket) return <>{children}</>;
  return <RoleRouteNotice ownerText={verdict.ownerText} home={ROLE_HOME[bucket]} />;
}
