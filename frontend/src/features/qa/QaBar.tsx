/**
 * QA 바 — WO-GRDX-20261003-04 · 규격 09 M4. 환경 이름 · 현재 사용자키 · 키 전환 · 현재 경로.
 *
 * 이 파일은 `VITE_QA_BUILD=true` 로 지은 번들에만 실린다(`App.tsx` 의 상수 분기 + 동적 import).
 * 정적 import 금지 — 비 QA 코드에서 이 모듈을 직접 끌면 운영 번들에 `qa/as` 가 실린다.
 *
 * - 화면 맨 위에 고정(position fixed)으로 떠 있고 레이아웃을 밀지 않는다. 접으면 오른쪽 위 작은 알약.
 * - 접힘 상태는 sessionStorage 에 기억한다(막혀도 화면은 정상).
 * - 자료: `GET /qa/keys` → `{ current: {key,type}|null, keys: [{key,type,state}] }`.
 *   실패해도 환경 이름과 경로는 뜨고 키 전환만 꺼진다.
 */
import { useEffect, useState } from 'react';
import type { createBrowserRouter } from 'react-router-dom';

type QaKey = { key: string; type: string; state?: string };
type QaKeysPayload = { current: { key: string; type: string } | null; keys: QaKey[] };

const COLLAPSE_STORAGE = 'gx.qa.bar.collapsed';
const ENV_NAME = 'QA · guardianx-qa';

function readCollapsed(): boolean {
  try {
    return window.sessionStorage.getItem(COLLAPSE_STORAGE) === '1';
  } catch {
    return false;
  }
}

function writeCollapsed(value: boolean): void {
  try {
    window.sessionStorage.setItem(COLLAPSE_STORAGE, value ? '1' : '0');
  } catch {
    /* 저장이 막혀도 화면은 정상 */
  }
}

export default function QaBar({ router }: { router: ReturnType<typeof createBrowserRouter> }) {
  const [collapsed, setCollapsed] = useState<boolean>(readCollapsed);
  const [data, setData] = useState<QaKeysPayload | null>(null);
  const [path, setPath] = useState<string>(() => router.state.location.pathname);

  useEffect(() => {
    setPath(router.state.location.pathname);
    return router.subscribe((state) => setPath(state.location.pathname));
  }, [router]);

  useEffect(() => {
    let alive = true;
    fetch('/qa/keys', { credentials: 'same-origin', headers: { Accept: 'application/json' } })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then((body: QaKeysPayload) => {
        if (alive && body && Array.isArray(body.keys)) setData(body);
      })
      .catch(() => {
        if (alive) setData(null);
      });
    return () => {
      alive = false;
    };
  }, []);

  const toggle = (next: boolean) => {
    setCollapsed(next);
    writeCollapsed(next);
  };

  const font = 'system-ui, -apple-system, "Segoe UI", sans-serif';

  if (collapsed) {
    return (
      <div role="region" aria-label="QA 도구" style={{ position: 'fixed', top: 0, right: 8, zIndex: 2147483000 }}>
        <button
          type="button"
          onClick={() => toggle(false)}
          aria-label="QA 도구 펼치기"
          aria-expanded={false}
          style={{
            font: `600 12px/20px ${font}`,
            background: '#1f2937',
            color: '#ffffff',
            border: 0,
            borderRadius: '0 0 8px 8px',
            padding: '0 10px',
            height: 20,
            cursor: 'pointer',
          }}
        >
          QA
        </button>
      </div>
    );
  }

  const currentKey = data?.current?.key ?? '';
  const userText = data ? (data.current ? `${data.current.key} · ${data.current.type}` : '키 없음') : '확인 불가';
  const field = { font: `12px/20px ${font}`, color: '#ffffff' } as const;

  return (
    <div
      role="region"
      aria-label="QA 도구"
      style={{
        position: 'fixed',
        top: 0,
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 2147483000,
        maxWidth: '100vw',
        height: 28,
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 10px',
        background: '#1f2937',
        borderRadius: '0 0 8px 8px',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        ...field,
      }}
    >
      <strong style={{ fontWeight: 700 }}>{ENV_NAME}</strong>
      <span>사용자: {userText}</span>
      <label style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        <span>키 전환</span>
        <select
          value={currentKey}
          disabled={!data || data.keys.length === 0}
          onChange={(e) => {
            const next = e.target.value;
            if (next) window.location.assign(`/qa/as/${encodeURIComponent(next)}`);
          }}
          style={{ font: `12px/18px ${font}`, height: 22, maxWidth: 220, color: '#111827', background: '#ffffff' }}
        >
          {!currentKey && <option value="">선택</option>}
          {(data?.keys ?? []).map((k) => (
            <option key={k.key} value={k.key}>
              {k.key} · {k.type}
            </option>
          ))}
        </select>
      </label>
      <span>경로: {path}</span>
      <button
        type="button"
        onClick={() => toggle(true)}
        aria-label="QA 도구 접기"
        aria-expanded
        style={{
          font: `600 12px/20px ${font}`,
          background: 'transparent',
          color: '#ffffff',
          border: '1px solid #9ca3af',
          borderRadius: 4,
          padding: '0 6px',
          height: 22,
          cursor: 'pointer',
        }}
      >
        접기
      </button>
    </div>
  );
}
