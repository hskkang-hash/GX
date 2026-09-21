/**
 * 시각 표기 — **KST 표기 + 상대시간 병기** (DA-03 §4-6).
 *
 *     "14:32 · 3분 전"
 *
 * ★ 둘 중 하나만 쓰지 않는다. 절대시각만 있으면 관제요원이 「방금인가」를 계산해야 하고,
 *   상대시간만 있으면 인수인계와 보고서에서 그 줄을 다시 찾지 못한다.
 */
import dayjs from 'dayjs';

/* ★ 문구는 **사전에서 온다**(P-27). 이 파일이 정하는 것은 **언제 그 말을 쓰는가**
   (문턱·날 수)이고, **무슨 말인가**는 `copy.ts` 한 곳이다 — 두 벌이 되면 한쪽이 늙는다.
   `copy.ts` 는 아무것도 import 하지 않으므로 순환이 없다 [실측 2026-09-21]. */
import { elapsedDaysPhrase } from './copy';

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

/**
 * 단계가 무엇을 뜻하는지 **글자로도** 적는다 — 크기는 스크린리더가 못 읽는다.
 *
 * ★★ [턴 W · 차선 U1 · P-188] **이 배열은 폴백 이름이고, 화면이 그대로 쓰면 거짓말이다.**
 *   종전 문안은 `['방금','30초 경과','2분 경과','5분 경과','8분 경과 — 가장 오래 기다린 사건']`
 *   이었다. 두 군데가 거짓이었다:
 *
 *   ① **「8분」은 고정 숫자였다.** 문턱 표는 서버가 준다(`tier_thresholds_sec`). 서버가
 *      `[60,180,600,1200]` 을 주면 단계 4 는 **20분**인데 화면은 계속 「8분 경과」라고
 *      적었다. 그리고 실제 경과가 47분이어도 「8분 경과」였다 — 「넘었다」를 「이다」로
 *      적은 것이다. 숫자 자체는 바로 위 큰 글자(`duration(elapsed)`)가 이미 말한다.
 *   ② **「가장 오래 기다린 사건」은 순위 주장이다.** 단계 4 인 카드가 열 장이면 열 장
 *      전부가 자기가 가장 오래 기다렸다고 적었다. 순위는 **한 장에만** 붙는 사실이고,
 *      이 배열은 한 장인지 열 장인지 모른다 — 그래서 여기서 뗐다.
 *
 *   ⇒ 이름은 `tierLabel(tier, thresholds)` 가 **서버 문턱으로 지어 낸다**.
 *      순위는 카드를 **전부 보는 화면**이 `rankNote` 로 따로 얹는다(`FocusQueue.tsx`).
 */
export const TIER_LABEL = [
  '방금',
  '30초 넘음',
  '2분 넘음',
  '5분 넘음',
  '8분 넘음',
] as const;

/**
 * 「5분 넘음」 — **서버가 준 문턱 표로 지어 낸다.**
 *
 * `tier` 가 n(>0)이면 넘은 문턱은 `thresholds[n-1]` 이다. 표가 짧으면(서버가 단계
 * 수를 줄여 보내면) 그 자리가 없으므로 **폴백 이름을 쓰되 폴백임을 부르는 쪽이 적는다** —
 * 여기서 없는 숫자를 지어내지 않는다.
 */
export function tierLabel(
  tier: number,
  thresholds: readonly number[] = FALLBACK_TIER_THRESHOLDS_SEC,
): string {
  if (tier <= 0) return TIER_LABEL[0];
  const crossed = thresholds[tier - 1];
  if (crossed === undefined || !Number.isFinite(crossed)) {
    return TIER_LABEL[Math.min(tier, TIER_LABEL.length - 1)];
  }
  return `${duration(crossed)} 넘음`;
}

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

/* ═══════════════════════════════════════════════════════════════════════════
 * P-221 — 대응 시계가 **하루를 넘기면 말이 바뀐다** (2026-09-21 · 턴 AA · 차선 U1)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 세종이 고객 자리에 앉아 잰 것: 큐의 「가장 급한 하나」가 15일 전 사건이고 시계가
 * **「377시간 27분」 빨강**이었다. *「제품은 옳다(오래 열린 것이 급하다). 그러나 고객
 * 첫날 화면에 377시간은 「이 시스템은 방치돼 있다」로 읽힌다.」*
 *
 * ★ **수를 고치지 않는다. 말을 고친다.** `duration` 은 그대로다 — 그 함수는 5분 문턱과
 *   초 단위를 재는 자리에 계속 쓰이고, 거기서 「0일」로 반올림되면 문턱이 안 보인다.
 *   여기 더하는 것은 **읽는 쪽이 부르는 한 줄**이다.
 * ★ **다음 손을 같은 줄에.** 하루가 넘은 사건에 남은 손은 대응이 아니라 종결 검토다
 *   (「정직한 회색을 고객 말로」 · 문구 정본은 `copy.ts::elapsedDaysPhrase`).
 * ★ 정확한 초는 **없어지지 않는다** — 부르는 쪽이 툴팁·스크린리더 라벨에 `duration`
 *   을 그대로 싣는다. 감추는 것이 아니라 **큰 글자의 자리를 바꾸는 것**이다.
 */
/** 말이 바뀌는 문턱. 24시간 — 「하루가 넘었다」가 사람이 아는 단위다. */
export const LONG_ELAPSED_SEC = 24 * 60 * 60;

/** 이 경과가 **하루를 넘겼는가.** `null`(시계 없음)은 넘지 않은 것으로 본다. */
export function isLongElapsed(seconds: number | null | undefined): boolean {
  return (
    seconds !== null && seconds !== undefined && Number.isFinite(seconds) &&
    seconds >= LONG_ELAPSED_SEC
  );
}

/**
 * 시계의 **큰 글자**. 하루 아래면 종전 그대로(`duration`), 넘으면 날 + 다음 손.
 *
 * ★ 날 수는 **버림**이다. 15.7일을 「16일」로 적으면 아직 오지 않은 하루를 적은 것이
 *   되고, 종결 검토 기한을 세는 사람이 그 하루를 잃는다.
 */
export function elapsedHeadline(seconds: number | null | undefined): string {
  if (!isLongElapsed(seconds)) return duration(seconds);
  return elapsedDaysPhrase(Math.floor((seconds as number) / LONG_ELAPSED_SEC));
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

/* ═══════════════════════════════════════════════════════════════════════════
 * P-188 경과 **순위** — 「가장 오래 기다린 사건」은 한 장에만 붙는 사실이다
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 왜 여기 있나: 단계 이름(`tierLabel`)과 **같은 질문**이고, 둘 다 리액트를 모른다.
 * 화면 파일에 두면 `rj-core`·antd 를 끌고 와서 **따로 돌려 볼 수가 없다** — 돌려
 * 볼 수 없는 함수의 0건 갈래는 「그렇게 그려질 것」이지 잰 것이 아니다.
 */
/** 순위 한 줄의 앞머리 — 검수 촬영이 이 글자를 찾는다. */
export const OLDEST_WAIT_LABEL = '가장 오래 기다린 사건';

/**
 * 경과 순위 — **정렬이 아니라 세기다.**
 *
 * 한 카드의 순위 = 「나보다 **오래** 기다린 카드 수 + 1」. 화면에 그려지는 순서는
 * 건드리지 않는다(서버가 정한 순서 그대로). 그래서 이 파일에는 여전히 `sort(` 가 없다.
 *
 * ★ 세는 값은 **서버가 준 `elapsed_seconds`** 다. 카드마다 화면 시계로 다시 재면
 *   같은 순간의 수가 아니게 되어 순위가 깜박인다.
 * ★ 시계가 멈춘 카드(`elapsed_seconds === null` · 종결)는 **분모에도 분자에도 없다** —
 *   기다리고 있지 않은 것은 기다린 순위에 들 수 없다.
 */
export interface WaitRank {
  /** 1 이 가장 오래 기다린 것. */
  rank: number;
  /** 나와 **같은** 경과를 가진 카드 수(나 포함). 2 이상이면 동률이다. */
  tied: number;
  /** 시계가 도는 카드 수 — **센 수다. 손으로 적지 않는다.** */
  total: number;
}

export function waitRanks(
  cards: readonly { event_id: number; elapsed_seconds?: number | null }[],
): Map<number, WaitRank> {
  const running: { id: number; elapsed: number }[] = [];
  for (const card of cards) {
    const e = card.elapsed_seconds;
    if (e === null || e === undefined || !Number.isFinite(e)) continue;
    running.push({ id: card.event_id, elapsed: e });
  }
  const out = new Map<number, WaitRank>();
  for (const me of running) {
    let older = 0;
    let tied = 0;
    for (const other of running) {
      if (other.elapsed > me.elapsed) older += 1;
      else if (other.elapsed === me.elapsed) tied += 1;
    }
    out.set(me.id, { rank: older + 1, tied, total: running.length });
  }
  return out;
}

/** 순위 한 줄. 모르면 **빈 문자열** — 모르는 것을 적지 않는다. */
export function rankNoteOf(rank: WaitRank | undefined): string {
  if (!rank) return '';
  if (rank.total <= 1) return '시계가 도는 사건이 이 하나뿐입니다 — 견줄 상대가 없습니다.';
  if (rank.rank === 1) {
    return rank.tied > 1
      ? `${OLDEST_WAIT_LABEL} — 동률 ${rank.tied}건 (시계가 도는 ${rank.total}건 중 1번째)`
      : `${OLDEST_WAIT_LABEL} (시계가 도는 ${rank.total}건 중 1번째)`;
  }
  return `경과 ${rank.rank}번째 (시계가 도는 ${rank.total}건 중)`;
}
