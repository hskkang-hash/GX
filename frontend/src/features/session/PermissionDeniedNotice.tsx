/**
 * P-88 꼬리 — **막힌 화면의 한 줄.** (2026-09-07 턴 J · 차선 C)
 *
 * `permissionDenied.ts` 가 낸 신호(`gx:permission-denied`)를 **사람이 읽는 글자로**
 * 바꾸는 자리다. 그 파일의 머리말이 적어 둔 「아직 그리는 쪽이 없다」가 여기서 닫힌다.
 *
 * 무엇이 달라지나 [실측 2026-09-07 · 계정 `gxprobe_e2e` · `/device`]
 * -------------------------------------------------------------------
 *   승격 전: HTTP 200 + 본문 403 → 표가 행 0 개를 그린다 → **빈 표**
 *            사람이 읽는 것: 「자료가 없다」 (틀린 문장이다)
 *   승격 후 · 이 파일 없이: HTTP 403 → 표가 아무것도 못 받는다 → **빈 표 + 멈춘 스피너**
 *   승격 후 · 이 파일 있음: HTTP 403 → **「볼 권한이 없습니다」 한 줄**
 *
 * ★ **덮개가 아니다.** `SessionEndedNotice` 는 화면 전체를 막는다 — 그 뒤 화면은 이미
 *   죽었기 때문이다. 권한 거절은 다르다: **막힌 것은 문 하나**이고 나머지 화면은
 *   살아 있다(다른 표·메뉴·로그아웃은 그대로 된다). 그래서 이것은 위에서 내려오는
 *   띠 한 줄이고, 사람이 닫을 수 있고, 뒤의 조작을 막지 않는다.
 *   전체를 막으면 「권한이 하나 없다」가 「제품이 죽었다」로 읽힌다.
 *
 * ★ **문마다 한 줄.** 한 화면이 여러 문을 부르는데 그중 둘이 막힐 수 있다.
 *   그때 「어디가 막혔는지」가 뭉개지면 안내가 소용없다 — `announcePermissionDenied`
 *   가 이미 경로별로 한 번만 알리고, 여기서는 그 경로들을 **쌓아서** 보여 준다.
 *
 * ★ 문장을 여기서 짓지 않는다 (GX-COPY 규칙 1) — `permissionDenied.ts` 머리말 참조.
 *   화면에 뜨는 큰 글자는 **서버가 보낸 `message`** 이고, 서버가 말이 없을 때만
 *   사전의 「볼 권한이 없습니다」로 떨어진다.
 *
 * ⚠ **이 한 줄이 스피너를 끄지는 않는다.** 스피너는 부른 쪽의 `finally` 가 끈다
 *   (차선 C ② · 프런트 오류 처리). 안내가 떴는데 그 밑에서 스피너가 계속 돌면
 *   그것은 이 파일의 빨강이 아니라 **부른 화면의 빨강**이고, 따로 적는다.
 *   여기서 남의 스피너를 끄러 가면 고칠 곳이 덮인다.
 */
import { useEffect, useState } from 'react';

import {
  PERMISSION_DENIED_EVENT,
  type PermissionDeniedDetail,
} from './permissionDenied';

/** 「무엇이 막혔는가」는 결과고, 「무엇을 할 수 있는가」는 그 다음 줄이다. */
const CONSEQUENCE = '이 자료는 지금 계정의 권한으로 열 수 없습니다.';
const DISMISS = '닫기';

/** 화면에 쌓인 거절들. `path` 가 열쇠다 — 같은 문은 겹쳐 그리지 않는다. */
type Denial = PermissionDeniedDetail;

export function PermissionDeniedNotice() {
  const [denials, setDenials] = useState<Denial[]>([]);

  useEffect(() => {
    const onDenied = (event: Event) => {
      const detail = (event as CustomEvent<PermissionDeniedDetail>).detail;
      if (!detail?.message) return;
      setDenials((prev) =>
        prev.some((d) => d.path === detail.path) ? prev : [...prev, detail],
      );
    };
    window.addEventListener(PERMISSION_DENIED_EVENT, onDenied);
    return () => window.removeEventListener(PERMISSION_DENIED_EVENT, onDenied);
  }, []);

  if (denials.length === 0) return null;

  // 서버가 보낸 문장이 여럿이면 첫 줄만 크게 쓴다 — 문장 자체는 대개 같고,
  // 다른 것은 **막힌 문**이다. 그 목록은 아래 작은 글자로 그대로 적는다.
  const headline = denials[0].message;

  return (
    <div
      // ⚠ `alert` 이지 `alertdialog` 가 아니다 — 뒤 화면을 막지 않으므로 모달이 아니다.
      role="alert"
      aria-live="assertive"
      data-testid="gx-permission-denied"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 9998,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
        padding: '12px 16px',
        background: '#fef3c7',
        borderBottom: '1px solid #f59e0b',
        color: '#78350f',
        fontSize: 14,
        lineHeight: 1.5,
        boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 2 }}>{headline}</div>
        <div style={{ color: '#92400e' }}>{CONSEQUENCE}</div>
        <div
          style={{
            marginTop: 6,
            fontSize: 12,
            color: '#a16207',
            wordBreak: 'break-all',
          }}
        >
          {denials.map((d) => (
            <div key={d.path}>{d.path}</div>
          ))}
        </div>
      </div>
      <button
        type="button"
        onClick={() => setDenials([])}
        aria-label={DISMISS}
        style={{
          flex: '0 0 auto',
          fontSize: 13,
          fontWeight: 600,
          padding: '6px 14px',
          borderRadius: 6,
          border: '1px solid #d97706',
          color: '#78350f',
          background: 'transparent',
          cursor: 'pointer',
        }}
      >
        {DISMISS}
      </button>
    </div>
  );
}

export default PermissionDeniedNotice;
