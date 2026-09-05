/**
 * P-62 꼬리 — **끊긴 화면의 한 줄.** (2026-09-05 턴 F · 차선 S)
 *
 * 휴대전화에서 로그인하면 이 화면이 닫힌다. 그 사실을 **이 화면이 말한다** —
 * 말없이 `/login` 으로 튕기지 않는다. 튕기면 사람은 자기가 무엇을 잘못했는지 모르고,
 * 「고장」과 「밀려남」을 구별하지 못한다.
 *
 *   ┌─────────────────────────────────────────────┐
 *   │  다른 기기에서 로그인되었습니다              │   ← 서버가 보낸 문장 그대로
 *   │  이 화면은 닫혔습니다.                        │
 *   │                       [ 다시 로그인 ]        │   ← 1클릭
 *   └─────────────────────────────────────────────┘
 *
 * ★ **절이 아니라 한 줄이다.** 재시도·자동 복구·세션 목록 같은 것을 여기 붙이지 않는다.
 *   동시 세션 자체는 dj-core 의 `user.token` 한 칸이고 §0.4 다(UX-24b · 손 밖).
 *
 * ★ 문장을 여기서 짓지 않는다 (GX-COPY 규칙 1) — `sessionEnded.ts` 의 머리말 참조.
 *
 * ⚠ 이 안내가 뜨는 동안 **뒤 화면은 이미 죽어 있다**(토큰이 남의 세션 것이다).
 *   그래서 덮개는 화면 전체를 막는다 — 반쯤 살아 있는 것처럼 보이게 두면 사람은
 *   버튼을 계속 누르고, 그 요청들은 전부 401 이다.
 */
import { useEffect, useState } from 'react';

import {
  LOGIN_PATH,
  SESSION_ENDED_EVENT,
  type SessionEndedDetail,
} from './sessionEnded';

/** 「이 화면이 닫혔다」는 사실. 위 한 줄이 원인이고, 이 줄이 결과다. */
const CONSEQUENCE = '이 화면은 닫혔습니다.';
const ACTION = '다시 로그인';

export function SessionEndedNotice() {
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const onEnded = (event: Event) => {
      const detail = (event as CustomEvent<SessionEndedDetail>).detail;
      setMessage(detail?.message ?? null);
    };
    window.addEventListener(SESSION_ENDED_EVENT, onEnded);
    return () => window.removeEventListener(SESSION_ENDED_EVENT, onEnded);
  }, []);

  if (!message) return null;

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label={message}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(11, 15, 20, 0.72)',
      }}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: 12,
          padding: '28px 32px',
          maxWidth: 420,
          boxShadow: '0 12px 40px rgba(0,0,0,0.28)',
          textAlign: 'center',
        }}
      >
        <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8, color: '#111827' }}>
          {message}
        </div>
        <div style={{ fontSize: 15, color: '#4b5563', marginBottom: 20 }}>{CONSEQUENCE}</div>
        <button
          type="button"
          autoFocus
          onClick={() => {
            // 1클릭. 상태를 들고 가지 않는다 — 들고 갈 만한 것이 이미 죽었다.
            window.location.href = LOGIN_PATH;
          }}
          style={{
            fontSize: 16,
            fontWeight: 600,
            padding: '10px 24px',
            borderRadius: 8,
            border: 'none',
            color: '#ffffff',
            background: '#1f6feb',
            cursor: 'pointer',
          }}
        >
          {ACTION}
        </button>
      </div>
    </div>
  );
}

export default SessionEndedNotice;
