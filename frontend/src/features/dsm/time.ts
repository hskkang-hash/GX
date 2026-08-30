/**
 * 시각 표기 — **KST 표기 + 상대시간 병기** (DA-03 §4-6).
 *
 *     "14:32 · 3분 전"
 *
 * ★ 둘 중 하나만 쓰지 않는다. 절대시각만 있으면 관제요원이 「방금인가」를 계산해야 하고,
 *   상대시간만 있으면 인수인계와 보고서에서 그 줄을 다시 찾지 못한다.
 */
import dayjs from 'dayjs';

const KST = 'Asia/Seoul';

export function absolute(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = dayjs(value);
  if (!d.isValid()) return '—';
  return d.format('YYYY-MM-DD HH:mm:ss');
}

export function shortAbsolute(value: string | Date | null | undefined): string {
  if (!value) return '—';
  const d = dayjs(value);
  return d.isValid() ? d.format('HH:mm') : '—';
}

/** 「3분 전」. 미래 시각은 **미래라고 적는다** — 조용히 0으로 접지 않는다. */
export function relative(value: string | Date | null | undefined, now = new Date()): string {
  if (!value) return '';
  const d = dayjs(value);
  if (!d.isValid()) return '';
  const diffSec = Math.round((dayjs(now).valueOf() - d.valueOf()) / 1000);
  if (diffSec < 0) return '잠시 후';
  if (diffSec < 60) return `${diffSec}초 전`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}분 전`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}시간 전`;
  return `${Math.floor(diffSec / 86400)}일 전`;
}

/** 화면이 쓰는 한 줄. 시간대 이름을 함께 두는 이유는 I-4 의 시간대가 미확인이기 때문이다. */
export function stamp(value: string | Date | null | undefined, now?: Date): string {
  if (!value) return '—';
  return `${shortAbsolute(value)} · ${relative(value, now)}`;
}

export const TIMEZONE_NOTE = `표기 시간대: ${KST}`;
