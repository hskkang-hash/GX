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

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-14 대응 시계 — **관제요원은 숫자를 읽지 않는다. 크기를 본다.**
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 야간 관제실에서 40인치 화면을 3m 밖에서 보는 사람에게 「07:41」과 「12:03」은
 * 같은 그림이다. 그래서 경과 시간이 문턱을 넘을 때마다 **글자가 한 단계 커진다.**
 *
 * ★ 왜 색이 아니라 크기인가: 색은 배경과 싸우고(야간 모드·프로젝터·반사),
 *   색각 이상(남성 8%)에게는 아예 안 읽힌다. 크기는 둘 다에서 그대로 읽힌다.
 *   색도 함께 쓰지만 **크기가 정보이고 색은 보조**다 (DA-03 §2-2 와 같은 규약).
 *
 * ★ 문턱 표는 **서버가 준다.** 화면은 시계가 계속 도니까 자기도 계산해야 하는데,
 *   표를 화면이 따로 들면 서버 통계와 화면 글자가 다른 문턱을 쓰게 된다.
 *   그래서 `tierOf` 는 문턱 배열을 **인자로 받는다** — `allowed_next` 와 같은 규약.
 *   아래 상수는 서버가 아직 답하지 않았을 때의 **표시용 폴백**이고, 그것이
 *   폴백이라는 사실을 이름에 적는다.
 */

/** 서버(`tier_thresholds_sec`)가 오기 전에 쓰는 폴백. 30초 · 2분 · 5분 · 8분. */
export const FALLBACK_TIER_THRESHOLDS_SEC = [30, 120, 300, 480] as const;

/** 0(방금) ~ 4(8분 넘음). **닫힌 이벤트는 0** — 시계가 멈췄다. */
export function tierOf(
  elapsedSeconds: number | null | undefined,
  thresholds: readonly number[] = FALLBACK_TIER_THRESHOLDS_SEC,
): number {
  if (elapsedSeconds === null || elapsedSeconds === undefined) return 0;
  return thresholds.reduce((n, t) => (elapsedSeconds >= t ? n + 1 : n), 0);
}

/**
 * 단계별 글자 크기(px). **한 단계마다 눈에 띄게 커진다** — 2px씩 키우면
 * 「커졌다」가 안 보이고, 안 보이는 단계는 없는 단계다.
 */
export const TIER_FONT_PX = [14, 18, 24, 32, 44] as const;

/** 단계별 색. **보조다** — 이 색만으로는 아무것도 읽히지 않아야 한다. */
export const TIER_COLOR = [
  '#8c8c8c', // 0 방금
  '#1677ff', // 1 30초 넘음
  '#faad14', // 2 2분 넘음
  '#fa541c', // 3 5분 넘음
  '#cf1322', // 4 8분 넘음
] as const;

/** 단계가 무엇을 뜻하는지 **글자로도** 적는다 — 크기는 스크린리더가 못 읽는다. */
export const TIER_LABEL = [
  '방금',
  '30초 경과',
  '2분 경과',
  '5분 경과',
  '8분 경과 — 가장 오래 기다린 사건',
] as const;

/** 「3분 12초」. 초 단위를 버리지 않는다 — 30초 문턱이 초로 갈리기 때문이다. */
export function duration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—';
  if (!Number.isFinite(seconds)) return '—';
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s}초`;
  const m = Math.floor(s / 60);
  if (m < 60) return s % 60 ? `${m}분 ${s % 60}초` : `${m}분`;
  const h = Math.floor(m / 60);
  return m % 60 ? `${h}시간 ${m % 60}분` : `${h}시간`;
}

/**
 * 「—」와 「0초」를 가른다 (D-290).
 *
 * `null` 은 **「그 일이 아직 안 일어났다」**이고 `0` 은 **「즉시 일어났다」**이다.
 * 둘을 같은 글자로 그리면 「아무도 접수 안 함」이 「즉시 접수」로 보인다.
 */
export function durationOrAbsent(
  seconds: number | null | undefined,
  absent = '아직 없음',
): string {
  return seconds === null || seconds === undefined ? absent : duration(seconds);
}
