/**
 * P-342 — **비밀번호 찾기 화면은 실패를 말한다.** (2026-09-25 턴 AJ · 차선 D)
 *
 * 무엇이 문제였나 [실측 2026-09-24 턴 AI]
 * ----------------------------------------
 * 서버 길목(P-325 · `backend/common/reset_mail_gate.py`)은 SMTP 가 죽어 있으면 503 과
 * 「지금은 메일을 보낼 수 없습니다 — 관리자에게 문의하십시오.」를 돌려준다. 그런데
 * 화면(rj-core `ForgotPasswordPage` · 우리 `ForgotPasswordMobile`)은 실패를
 * `console.log` 로만 삼켰다 — 거짓 「보냈습니다」가 **무반응**으로 옮겨 갔을 뿐이다.
 *
 * 어떻게 고쳤나 — rj-core 는 안 고친다(§0.4)
 * ------------------------------------------
 * 이 띠가 두 화면을 **감싼다**(`App.tsx::ForgotPassword`). 띠는 서버에
 * `GET /api/v1/auth/forgot-password/availability` 로 「지금 보낼 수 있나」만 묻는다 —
 * ① 화면이 열릴 때 ② 안쪽 폼이 제출될 때(`onSubmitCapture` · 뒤이어 한 번 더).
 * 막혔으면 서버가 보낸 문장을 그대로 그리고 「다시 시도」를 준다. 묻는 것 자체가
 * 실패하면(네트워크) 사전의 「불러오지 못했습니다.」를 그린다.
 *
 * ★ 주소를 보내지 않는다 — 이 문은 계정 존재와 무관하다(서버 시험 `test_p342_*` ③).
 * ★ 낱말을 만들지 않았다(GX-COPY 규칙 1) — 큰 글자는 서버의 `message`, 없을 때만
 *   `features/dsm/copy.ts` 의 줄이다.
 */
import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

import { FAILURE_TITLE, RETRY_LABEL } from '@/features/dsm/copy';

export const AVAILABILITY_PATH = '/api/v1/auth/forgot-password/availability';

/** 제출 뒤 다시 묻기까지 — 안쪽 화면의 요청이 먼저 서버에 닿게 둔다. */
const RECHECK_AFTER_SUBMIT_MS = 1500;

export type MailState =
  | { kind: 'unknown' }
  | { kind: 'ok' }
  | { kind: 'blocked'; line: string }
  | { kind: 'unreachable' };

type Probe = { available?: unknown; message?: unknown };

/** 서버 답 하나를 상태로 옮긴다. 순수 함수 — 시험이 이 이름을 부른다. */
export function toMailState(body: Probe | null, lang: string): MailState {
  if (!body || typeof body.available !== 'boolean') return { kind: 'unreachable' };
  if (body.available) return { kind: 'ok' };
  const m = body.message;
  let line: string | null = null;
  if (typeof m === 'string' && m.trim()) line = m;
  else if (m && typeof m === 'object') {
    const d = m as Record<string, unknown>;
    for (const key of [lang, 'ko', 'en']) {
      const v = d[key];
      if (typeof v === 'string' && v.trim()) {
        line = v;
        break;
      }
    }
  }
  return line ? { kind: 'blocked', line } : { kind: 'unreachable' };
}

async function probe(lang: string): Promise<MailState> {
  const base = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
  try {
    const resp = await fetch(`${base}${AVAILABILITY_PATH}`, {
      credentials: 'omit',
      cache: 'no-store',
    });
    if (!resp.ok) return { kind: 'unreachable' };
    return toMailState((await resp.json()) as Probe, lang);
  } catch {
    return { kind: 'unreachable' };
  }
}

export function ResetMailNotice({ children }: { children: ReactNode }) {
  const { i18n } = useTranslation();
  const lang = (i18n.language || 'ko').slice(0, 2);
  const [state, setState] = useState<MailState>({ kind: 'unknown' });
  const timer = useRef<number | undefined>(undefined);

  const check = useCallback(() => {
    void probe(lang).then(setState);
  }, [lang]);

  useEffect(() => {
    check();
    return () => window.clearTimeout(timer.current);
  }, [check]);

  const onSubmitCapture = () => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(check, RECHECK_AFTER_SUBMIT_MS);
  };

  const line =
    state.kind === 'blocked' ? state.line : state.kind === 'unreachable' ? FAILURE_TITLE : null;

  return (
    <div onSubmitCapture={onSubmitCapture}>
      {line && (
        <div
          role="alert"
          data-gx="reset-mail-notice"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1000,
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            justifyContent: 'center',
            flexWrap: 'wrap',
            padding: '10px 16px',
            background: '#fff4e5',
            color: '#7a3e00',
            borderBottom: '1px solid #f0c48a',
            fontSize: 14,
          }}
        >
          <span>{line}</span>
          <button
            type="button"
            onClick={check}
            style={{
              border: '1px solid #7a3e00',
              background: 'transparent',
              color: '#7a3e00',
              borderRadius: 4,
              padding: '2px 10px',
              cursor: 'pointer',
            }}
          >
            {RETRY_LABEL}
          </button>
        </div>
      )}
      {children}
    </div>
  );
}
