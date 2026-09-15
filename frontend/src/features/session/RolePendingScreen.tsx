/**
 * P-105 꼬리 — **역할 0개 계정이 보는 그 한 화면.** (2026-09-07 턴 M · 차선 C)
 *
 *   ┌──────────────────────────────────────────────────────┐
 *   │                                                      │
 *   │            역할이 아직 없습니다                       │
 *   │   관리자(홍길동)에게 역할 부여를 요청했습니다          │  ← 서버가 이름을 줄 때만
 *   │                                                      │
 *   │   역할을 받기 전까지 이 계정으로 열 수 있는           │
 *   │   화면은 이 화면뿐입니다.                             │
 *   │                                                      │
 *   │                   [ 로그아웃 ]                        │
 *   └──────────────────────────────────────────────────────┘
 *
 * ★ **덮개가 아니라 화면이다.** `PermissionDeniedNotice` 는 띠 한 줄이었다 —
 *   막힌 것이 문 하나였고 나머지 화면은 살아 있었기 때문이다. 여기는 반대다:
 *   이 계정으로 열 수 있는 화면이 **이것 하나뿐**이므로, 뒤에 아무것도 두지 않는다.
 *   사이드바도 두지 않는다 — 누를 수 있는 자리를 그려 놓고 전부 403 을 내는 것이
 *   지금 33장이 하고 있는 일이고, 그것을 끝내려고 이 화면을 만든다.
 *
 * ★ **로그아웃은 남긴다.** 나갈 문이 없는 화면은 갇힌 화면이다. 이 계정으로 할 수
 *   있는 일이 하나도 없을 때 사람이 할 수 있는 유일한 조작이 이것이다.
 *
 * ★ 문장을 여기서 짓지 않는다 (GX-COPY 규칙 1) — `rolePending.ts` 머리말 참조.
 *   특히 **관리자 이름과 「요청했습니다」는 서버가 말할 때만 쓴다.**
 *
 * ⚠ 이 화면이 떠 있다고 해서 문이 닫힌 것이 아니다. 뒷단이 403 을 내기 전까지
 *   `/api/dsm/events` 는 이 계정에게도 **자료를 그대로 준다** [실측 2026-09-07].
 *   그 사실은 `rolePending.ts` 머리말과 `docs/agent/evidence/P-105/frontend/` 에 있다.
 */
import { useEffect, useState } from 'react';

import API from '@/services/API';

import {
  COPY_CONSEQUENCE,
  COPY_NOT_REQUESTED,
  COPY_ROLE_PENDING_HEADLINE,
  ROLE_PENDING_PATH,
  copyRequestedTo,
  readRolePending,
  type RolePendingState,
} from './rolePending';
import { LOGIN_PATH } from './sessionEnded';

const ACTION_LOGOUT = '로그아웃';

export function RolePendingScreen() {
  /**
   * `null` 은 **아직 묻는 중**이다. 「모른다」와 「없다」를 한 값으로 접으면
   * 둘째 줄이 깜빡이며 바뀐다 — 사람이 읽는 도중에 문장이 바뀌는 화면이 된다.
   */
  const [state, setState] = useState<RolePendingState | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await API.get(ROLE_PENDING_PATH);
        if (alive) setState(readRolePending(res?.data));
      } catch {
        /*
         * 문이 아직 없거나(404) 답이 안 온다. **그래도 이 화면은 뜬다** —
         * 머리줄은 앞단이 아는 사실(`roles.length === 0`)만으로 참이기 때문이다.
         * 모르는 것은 둘째 줄뿐이고, 그 줄은 「아직 요청이 가지 않았다」로 내려
         * 적는다. 화면 전체를 오류로 바꾸지 않는다 — 그러면 역할이 없다는
         * 사실조차 사람에게 전달되지 않는다.
         */
        if (alive) setState({ pending: true, admin: null, notified: false });
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  /**
   * 둘째 줄을 고른다. **셋 중 하나**이고, 셋의 차이가 이 화면의 정직함이다.
   *   · 아직 묻는 중        → 아무 줄도 쓰지 않는다 (지어내지 않는다)
   *   · 이름 + 알림이 나갔다 → 「관리자(이름)에게 역할 부여를 요청했습니다」
   *   · 그 밖               → 「아직 역할 부여를 요청하지 못했습니다 …」
   */
  const second =
    state === null
      ? null
      : state.notified && state.admin
        ? copyRequestedTo(state.admin.name)
        : COPY_NOT_REQUESTED;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="gx-role-pending"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9997,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: '#f8fafc',
        color: '#0f172a',
      }}
    >
      <div
        style={{
          width: '100%',
          // 390px 폭에서도 좌우가 잘리지 않는다 — 이 화면은 휴대전화에서도 뜬다.
          maxWidth: 520,
          background: '#ffffff',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '32px 24px',
          boxShadow: '0 4px 20px rgba(15,23,42,0.06)',
          textAlign: 'center',
        }}
      >
        <h1
          style={{
            margin: 0,
            fontSize: 22,
            lineHeight: 1.4,
            fontWeight: 700,
          }}
        >
          {COPY_ROLE_PENDING_HEADLINE}
        </h1>

        {second && (
          <p
            data-testid="gx-role-pending-request"
            style={{
              margin: '12px 0 0',
              fontSize: 15,
              lineHeight: 1.6,
              color: '#334155',
            }}
          >
            {second}
          </p>
        )}

        <p
          style={{
            margin: '20px 0 0',
            fontSize: 14,
            lineHeight: 1.6,
            color: '#64748b',
          }}
        >
          {COPY_CONSEQUENCE}
        </p>

        {/* 관리자에게 닿는 다른 길. 서버가 준 것만 적는다 — 지어내지 않는다. */}
        {state?.admin?.email && (
          <p style={{ margin: '10px 0 0', fontSize: 13, color: '#64748b' }}>
            <a
              href={`mailto:${state.admin.email}`}
              style={{ color: '#2563eb' }}
            >
              {state.admin.email}
            </a>
          </p>
        )}

        <button
          type="button"
          onClick={() => {
            /*
             * 나갈 문. 토큰을 지우고 로그인 화면으로 보낸다 — 지우지 않고 보내면
             * 관문이 다시 이 계정을 들여보내고 같은 화면이 뜬다.
             */
            try {
              localStorage.clear();
              sessionStorage.clear();
            } catch {
              /* 저장소가 막힌 창에서도 이동은 해야 한다 */
            }
            window.location.assign(LOGIN_PATH);
          }}
          style={{
            marginTop: 24,
            fontSize: 14,
            fontWeight: 600,
            padding: '10px 22px',
            borderRadius: 8,
            border: '1px solid #cbd5e1',
            background: '#ffffff',
            color: '#0f172a',
            cursor: 'pointer',
          }}
        >
          {ACTION_LOGOUT}
        </button>
      </div>
    </div>
  );
}

export default RolePendingScreen;
