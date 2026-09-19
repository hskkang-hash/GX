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
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * ★★ 턴 V · 차선 U24 — **고친 것 둘** [실측 2026-09-17 턴 U · V 가 U4 로 눌렀다]
 * ═══════════════════════════════════════════════════════════════════════════
 * V 가 `/dsm/reports` 에서 「만들기」를 눌러 403 을 받았고, 그 자리에 흠 둘을 적었다.
 *
 * ① **결과줄이 읽기의 말이었다.** 서버의 큰 글자는 「읽기 전용 계정입니다 — 이 작업은
 *    수행할 수 없습니다.」(쓰기)인데, 그 밑에 이 파일이 고정으로 붙이던 줄은
 *    「이 자료는 지금 계정의 권한으로 열 수 없습니다.」(읽기)였다. 한 상자가 두 말을 했다.
 *    → `COPY_DENIED_CONSEQUENCE` 로 **갈래를 갈랐다**(볼 수 없습니다 ↔ 고칠 수 없습니다).
 *      갈래는 상태 코드가 아니라 **요청 메서드**가 정한다 — 403 하나로는 못 가른다.
 *
 * ② **상태 칸과 겹쳐 떴다.** 화면은 이미 제 상태 칸에 같은 403 을 적고 **거기에만
 *    「다시 시도」가 있다.** 이 띠는 화면 맨 위 고정 덮개라 그 칸을 가린다.
 *    → 화면이 `ownDenialPaths()` 로 **임자를 선언**하면 이 띠는 그 문들을 안 그린다.
 *      ⚠ 선언하지 않은 화면은 **종전 그대로 띠가 그린다** — 조용히 삼키는 길을
 *        기본으로 만들지 않는다(이 파일이 태어난 이유가 바로 그 침묵이다).
 */
import { useEffect, useState } from 'react';

import {
  COPY_DENIED_CONSEQUENCE,
  PERMISSION_DENIED_EVENT,
  PERMISSION_DENIED_OWNER_EVENT,
  hasDenialOwner,
  type PermissionDeniedDetail,
} from './permissionDenied';

const DISMISS = '닫기';

/** 화면에 쌓인 거절들. **갈래 + 문**이 열쇠다 — 같은 것은 겹쳐 그리지 않는다. */
type Denial = PermissionDeniedDetail;

export function PermissionDeniedNotice() {
  const [denials, setDenials] = useState<Denial[]>([]);
  /** 임자 목록이 바뀔 때마다 다시 거른다. 값 자체에는 뜻이 없다 — 다시 그리는 신호다. */
  const [ownerTick, setOwnerTick] = useState(0);

  useEffect(() => {
    const onDenied = (event: Event) => {
      const detail = (event as CustomEvent<PermissionDeniedDetail>).detail;
      if (!detail?.message) return;
      setDenials((prev) =>
        prev.some((d) => d.path === detail.path && d.kind === detail.kind)
          ? prev
          : [...prev, detail],
      );
    };
    const onOwner = () => setOwnerTick((n) => n + 1);
    window.addEventListener(PERMISSION_DENIED_EVENT, onDenied);
    window.addEventListener(PERMISSION_DENIED_OWNER_EVENT, onOwner);
    return () => {
      window.removeEventListener(PERMISSION_DENIED_EVENT, onDenied);
      window.removeEventListener(PERMISSION_DENIED_OWNER_EVENT, onOwner);
    };
  }, []);

  // ★★ 임자가 있는 문은 **그리지 않는다.** 그 화면의 상태 칸이 이미 같은 말을
  //   하고 있고, 그 칸에는 「다시 시도」가 있다. 덮개를 한 장 더 얹으면 그 단추를
  //   가린다 — 같은 사실을 두 번 말하면서 값 있는 쪽을 덮는다.
  //   `ownerTick` 은 임자가 바뀐 순간 이 줄을 다시 재게 하는 신호다.
  void ownerTick;
  const shown = denials.filter((d) => !hasDenialOwner(d.path));

  if (shown.length === 0) return null;

  // 서버가 보낸 문장이 여럿이면 첫 줄만 크게 쓴다 — 문장 자체는 대개 같고,
  // 다른 것은 **막힌 문**이다. 그 목록은 아래 작은 글자로 그대로 적는다.
  const headline = shown[0].message;
  // ★ 결과줄은 **갈래로 갈린다** — 읽기가 막힌 것과 쓰기가 막힌 것은 다른 사실이다.
  //   섞여 있으면(한 화면이 읽기도 쓰기도 막혔다) 쓰기가 더 센 말이므로 그쪽으로 적는다.
  const kind = shown.some((d) => d.kind === 'write') ? 'write' : 'read';
  const consequence = COPY_DENIED_CONSEQUENCE[kind];

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
        <div style={{ color: '#92400e' }}>{consequence}</div>
        <div
          style={{
            marginTop: 6,
            fontSize: 12,
            color: '#a16207',
            wordBreak: 'break-all',
          }}
        >
          {shown.map((d) => (
            <div key={d.kind + ' ' + d.path}>{d.path}</div>
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
