/**
 * QA 진입 화면 `/qa/enter?h=<인계표>` — WO-GRDX-20261002-09 · 규격 09 M2 (WO-GRDX-20261003-04 레인 C).
 *
 * 이 파일은 `VITE_QA_BUILD=true` 로 지은 번들에만 실린다(`App.tsx` 의 상수 분기 + 동적 import —
 * 스위치가 없으면 Vite 가 분기를 지우고 이 모듈은 산출물에 없다 · 검증: 운영 번들 `qa/as` 0건).
 *
 * 흐름: 뒷단 `GET /qa/as/<키>` 가 **실제 로그인 함수**로 로그인한 뒤 일회용 인계표만 들고 여기로 보낸다
 * (주소에 토큰 0). 이 화면은 인계표를 `POST /qa/handoff` 로 한 번 바꿔 받고, 로그인 화면
 * (`features/login/LoginDesktop.tsx` 의 `afterLogin`)과 **같은 순서**를 밟는다 — 인수 부품의
 * `login` → 프로필 → `updateUserInfo` → 첫 화면(`roleHome.resolveHome`). 인증을 건너뛰는 코드 0.
 */
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CustomRouters, useAPILogin, useLogin, useProfile, useUpdateUserInfo } from 'rj-core';

import { resolveHome } from '@/features/nav/roleHome';

type Handoff = { key: string; type: string; first_path: string; user: Record<string, any> };

export default function QaEntry() {
  const navigate = useNavigate();
  const { getProfileAPI, userProfileAPI } = useAPILogin();
  const login = useLogin();
  const updateUserInfo = useUpdateUserInfo();
  const { saveProfile } = useProfile();
  const [line, setLine] = useState('QA 사용자로 들어가는 중…');
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // 인계표는 한 번만 바꿀 수 있다 — 개발 모드의 두 번 실행도 막는다
    started.current = true;
    const h = new URLSearchParams(window.location.search).get('h');
    if (!h) {
      setLine('인계표가 없습니다 — /qa/as/<사용자키> 로 다시 들어오세요.');
      return;
    }
    (async () => {
      const res = await fetch('/qa/handoff', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ h }),
      }).catch(() => null);
      if (!res || !res.ok) {
        setLine('인계표가 지났거나 이미 쓰였습니다 — /qa/as/<사용자키> 로 다시 들어오세요.');
        return;
      }
      const data = (await res.json()) as Handoff;
      // 주소창에서 인계표를 지운다(이미 썼지만 남길 까닭이 없다).
      window.history.replaceState(null, '', '/qa/enter');
      const user = data.user;
      login({ token: user.access_token, refreshToken: user.refresh_token, isAuthenticated: true, userInfo: user });
      const [profile, extra] = await Promise.all([
        getProfileAPI(user.user_id),
        userProfileAPI(user.user_id).catch(() => ({ success: false, data: null })),
      ]);
      if (extra?.success && extra.data) saveProfile(extra.data);
      if (!profile?.success) {
        setLine(`${data.key} 로 로그인은 됐지만 사용자 정보를 불러오지 못했습니다.`);
        return;
      }
      updateUserInfo(profile.data);
      const home = resolveHome([profile.data, user], { device: 'desktop', fallback: data.first_path || CustomRouters.profile.path });
      navigate(home.path, { replace: true });
    })();
  }, [getProfileAPI, login, navigate, saveProfile, updateUserInfo, userProfileAPI]);

  return (
    <main style={{ padding: 32 }}>
      <h1 style={{ fontSize: 18 }}>QA 진입</h1>
      <p style={{ fontSize: 14 }} role="status">
        {line}
      </p>
    </main>
  );
}
