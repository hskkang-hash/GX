/**
 * UX-15 **키보드** — 판정 경로가 클릭뿐이면 관제요원은 8시간 마우스를 쥐어야 한다.
 *
 * 왜 `event.key` 가 아니라 `event.code` 인가 [실측 판단 · 2026-09-05]
 * -----------------------------------------------------------------
 * 이 화면을 쓰는 사람은 한국어를 친다. 한글 입력기가 켜져 있으면 `j` 를 눌러도
 * `event.key` 는 `ㅓ` 로 온다 — 즉 **입력기가 켜진 순간 단축키가 전부 죽는다.**
 * 그 고장은 「가끔 안 먹는다」로 보고되고 아무도 재현하지 못한다.
 * `event.code` 는 **자판의 자리**라 입력기와 무관하다. 그래서 자리를 먼저 보고,
 * 자리를 못 읽는 옛 브라우저를 위해서만 `key` 로 물러선다.
 *
 * 입력창 안에서는 먹지 않는다
 * --------------------------
 * 이 문지기가 없으면 검색창에 `j` 를 못 친다 — 글자 하나가 화면을 스크롤한다.
 * 그래서 입력 요소(입력칸 · 여러 줄 칸 · 고르는 칸 · 편집 가능한 자리)에 초점이
 * 있으면 **아무것도 하지 않는다.** 조합키(Ctrl · Alt · Meta)가 눌린 것도 지나 보낸다 —
 * 그것은 브라우저와 운영체제의 자리다.
 */
import { useEffect, useRef } from 'react';

/**
 * 지금 초점이 **글자를 받는 자리**에 있는가.
 *
 * ★ 이 술어 하나가 「검색창에 j 를 못 친다」를 막는다. 판정기가 이 갈래의
 *   실재를 센다 — 없으면 화면은 멀쩡히 뜨고 검색만 조용히 망가지기 때문이다.
 */
export function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || typeof el !== 'object') return false;
  const tag = String((el as HTMLElement).tagName ?? '').toUpperCase();
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if ((el as HTMLElement).isContentEditable) return true;
  if (typeof el.closest === 'function') {
    if (el.closest('input, textarea, select, [contenteditable="true"]')) return true;
  }
  return false;
}

/** 자판의 자리 → 우리가 아는 이름. 자리를 못 읽으면 글자로 물러선다. */
function slotOf(ev: KeyboardEvent): string {
  const code = ev.code || '';
  if (code) return code;
  const key = (ev.key || '').toLowerCase();
  if (key === 'j') return 'KeyJ';
  if (key === 'k') return 'KeyK';
  if (key === 'm') return 'KeyM';
  if (key === 'r') return 'KeyR';
  if (key === 'enter') return 'Enter';
  if (key === '1') return 'Digit1';
  if (key === '2') return 'Digit2';
  if (key === '3') return 'Digit3';
  return '';
}

export interface QueueKeyActions {
  /** K — 위로. */
  onPrev?: () => void;
  /** J — 아래로. */
  onNext?: () => void;
  /** Enter — 선택한 카드의 상세. */
  onOpen?: () => void;
  /** 1 · 2 · 3 — 처리 단계 한 칸. 인자는 0 · 1 · 2 다. */
  onStep?: (slot: number) => void;
  /** M — 소리 켜기 / 소리 끄기. */
  onToggleSound?: () => void;
  /** R — 다시 시도. */
  onReload?: () => void;
}

export function useQueueKeys(actions: QueueKeyActions, enabled = true): void {
  //: 렌더마다 새 객체가 오므로 **의존성에 넣지 않는다** — 넣으면 렌더마다
  //: 처리기를 떼었다 붙였다 하고, 그 사이에 눌린 키가 사라진다.
  const ref = useRef(actions);
  ref.current = actions;

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') return undefined;

    const onKeyDown = (ev: KeyboardEvent) => {
      // ★ 입력창 안에서는 먹지 않는다. 이 한 줄이 없으면 검색이 망가진다.
      if (isTypingTarget(ev.target)) return;
      if (ev.ctrlKey || ev.altKey || ev.metaKey) return;
      if (ev.isComposing) return;

      const slot = slotOf(ev);
      const act = ref.current;
      let handled = true;
      switch (slot) {
        case 'KeyJ':
          act.onNext?.();
          break;
        case 'KeyK':
          act.onPrev?.();
          break;
        case 'Enter':
          act.onOpen?.();
          break;
        case 'KeyM':
          act.onToggleSound?.();
          break;
        case 'KeyR':
          if (act.onReload) act.onReload();
          else handled = false;
          break;
        case 'Digit1':
        case 'Numpad1':
          act.onStep?.(0);
          break;
        case 'Digit2':
        case 'Numpad2':
          act.onStep?.(1);
          break;
        case 'Digit3':
        case 'Numpad3':
          act.onStep?.(2);
          break;
        default:
          handled = false;
      }
      if (handled) ev.preventDefault();
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [enabled]);
}
