/**
 * 로그인이 실패하는 **다섯 갈래**를 사람의 말로 옮긴다 (P-78 ② · 2026-09-06 턴 H).
 *
 * 무엇이 문제였나 [실측 · 직전 턴 `scripts/walk_states.py`]
 * --------------------------------------------------------
 *   500 · 503 · 403 · 타임아웃 · 서버 다운  →  **다섯 갈래 전부에서 본문이 203자
 *   그대로.** 화면이 실패를 **한 마디도 하지 않았다.**
 *   401(아이디·비밀번호 틀림)도 문구가 없었다(토스트를 놓칠까 1.5초·6초 두 번 읽었다).
 *   빈 값은 영문 「This field is required.」.
 *
 * 왜 그랬나 — **사유가 화면까지 오지 못했다**
 * -------------------------------------------
 * 인수 부품의 로그인 훅은 실패를 `{ success: false, message }` 로 접어 돌려준다.
 * 그 `message` 는 `err.response.data.message[언어]` 에서 온다. 그러므로
 *   ㉠ **응답이 없으면**(서버 다운·타임아웃) 그 자리는 `undefined` 이고,
 *      화면은 「사유가 없다」로 읽어 **아무것도 안 그린다** — 침묵이 기본값이다.
 *   ㉡ 응답이 있어도 상태 코드가 사라진다. 500 과 401 이 같은 모양으로 돌아오므로
 *      「서버가 아픈 것」과 「내가 틀린 것」을 **화면이 구별할 수 없다.**
 *   ㉢ 로그인 화면의 언어는 아직 영문이다(사람의 언어는 로그인 **뒤에** 정해진다).
 *      그래서 서버가 한국어를 함께 보내도 화면은 영문 쪽을 골랐다.
 *
 * 그래서 이 파일은 **응답을 접기 전의 사실**(상태 코드 · 본문 · 예외)을 받아
 * 다섯 갈래로 가른다. 갈래마다 문장이 다른 이유는 하나다 —
 * **사람이 다음에 할 일이 갈래마다 다르다.**
 *
 *   빈 값     칸을 채운다            (내가 지금 할 수 있다)
 *   틀림      다시 친다 · 몇 번 남았는지 안다
 *   잠금      **기다린다** — 얼마나 기다릴지 안다
 *   서버 오류 기다린다 · 내 잘못이 아님을 안다
 *   네트워크  **연결을 본다** — 서버가 아니라 길이 문제다
 *
 * ★ 문구는 전부 `docs/design/GX-COPY_v1.md` 의 「로그인이 실패하는 다섯 갈래」에서 온다.
 * ★ **순수 함수다.** 브라우저도 서버도 없이 시험할 수 있다.
 */

export type LoginFailureKind =
  | 'empty'
  | 'credentials'
  | 'locked'
  | 'rate_limited'
  | 'forbidden'
  | 'server'
  | 'network';

export interface LoginFailure {
  kind: LoginFailureKind;
  /** 화면에 그리는 줄. **이것 말고 다른 것은 그리지 않는다.** */
  text: string;
  /**
   * 율제한(SEC-21)일 때 서버가 준 **남은 초**. 화면은 이 수로 「N초 뒤 다시」를 세어 내린다.
   * 다른 갈래에는 없다 — 없는 수를 지어내지 않는다.
   */
  retryAfterSeconds?: number;
}

/** 빈 값 — 칸 옆에 붙는다. */
export const EMPTY_USERNAME = '아이디를 입력해 주십시오.';
export const EMPTY_PASSWORD = '비밀번호를 입력해 주십시오.';

/** 제출 중 — 눌린 단추가 침묵하면 사람이 한 번 더 누른다. */
export const SUBMITTING = '로그인 중입니다…';

/** 이미 보낸 요청을 또 누른 자리. **삼킨 것을 삼켰다고 말한다.** */
export const ALREADY_SUBMITTING = '처리 중입니다. 잠시만 기다려 주십시오.';

const CREDENTIALS = '아이디 또는 비밀번호가 올바르지 않습니다.';
const SERVER = '지금 로그인할 수 없습니다. 잠시 뒤 다시 시도해 주십시오.';
const NETWORK = '서버에 연결하지 못했습니다. 연결을 확인한 뒤 다시 시도해 주십시오.';
const FORBIDDEN = '이 계정에는 접근 권한이 없습니다. 관리자에게 문의해 주십시오.';

/**
 * 서버가 센 실패 횟수를 사람의 말로 붙인다.
 *
 * ★ **잠기기 전에** 말한다. 이 제품은 다섯 번 틀리면 계정을 잠그는데
 *   [실측 — 서버가 「Attempts N/5」를 함께 보낸다], 종전 화면은 그 수를 한 번도
 *   보여 주지 않았다. 잠긴 뒤에 세는 것은 사용자에게 늦다.
 */
export function attemptsLine(attempts: number, max: number): string {
  return `${max}회 틀리면 계정이 잠깁니다. (지금 ${attempts}회)`;
}

/**
 * 서버 본문에서 「N/M」을 읽는다. **없는 수를 지어내지 않는다** — 없으면 `null`.
 *
 * 서버가 보내는 문장은 언어마다 다르지만 숫자 두 개의 모양은 같다
 * (「Attempts 1/5.」 · 「시도 1/5회.」). 그래서 **문장이 아니라 수를 읽는다.**
 */
export function readAttempts(said: string | undefined): { now: number; max: number } | null {
  if (!said) return null;
  const m = /(\d+)\s*\/\s*(\d+)/.exec(said);
  if (!m) return null;
  const now = Number(m[1]);
  const max = Number(m[2]);
  if (!Number.isFinite(now) || !Number.isFinite(max) || max <= 0) return null;
  return { now, max };
}

/**
 * 율제한(SEC-21) — 너무 잦은 시도. **몇 초 뒤인지**가 이 문장의 값이다.
 * 서버(`common/rate_limit_body.py::rate_limited_message`)와 **같은 글자**다 — 화면이 세어 내리며
 * 다시 그릴 때도 서버가 처음 준 문장과 모양이 같아야 사람이 「다른 오류」로 읽지 않는다.
 * 0 이 되면 「지금 다시 시도할 수 있습니다」— 기다림이 끝났음을 말한다.
 */
export function rateLimitedLine(seconds: number): string {
  const s = Math.max(0, Math.trunc(seconds || 0));
  if (s <= 0) return '지금 다시 시도할 수 있습니다.';
  return `요청이 너무 잦습니다. ${s}초 뒤 다시 시도해 주십시오.`;
}

/**
 * 서버 본문에서 율제한의 **남은 초**를 읽는다. 없으면 `null` — 지어내지 않는다.
 * 읽는 순서: 본문 `retry_after_seconds`(SEC-21 규약) → `Retry-After` 헤더(초 단위 정수).
 */
export function readRetryAfter(body: unknown, retryAfterHeader?: string | null): number | null {
  const bag = (body ?? null) as Record<string, unknown> | null;
  const fromBody = bag && typeof bag.retry_after_seconds === 'number' ? bag.retry_after_seconds : null;
  if (fromBody !== null && Number.isFinite(fromBody) && fromBody >= 0) return Math.trunc(fromBody);
  if (retryAfterHeader) {
    const n = Number(retryAfterHeader.trim());
    if (Number.isFinite(n) && n >= 0) return Math.trunc(n);
  }
  return null;
}

/** 잠금 — **언제 풀리는지**가 이 문장의 값이다. */
export function lockedLine(minutes: number, seconds: number): string {
  const m = Math.max(0, Math.trunc(minutes || 0));
  const s = Math.max(0, Math.trunc(seconds || 0));
  if (m > 0 && s > 0) return `계정이 잠겼습니다. ${m}분 ${s}초 뒤에 다시 시도해 주십시오.`;
  if (m > 0) return `계정이 잠겼습니다. ${m}분 뒤에 다시 시도해 주십시오.`;
  return `계정이 잠겼습니다. ${s}초 뒤에 다시 시도해 주십시오.`;
}

/** 서버가 준 사유 한 줄을 문자열로 꺼낸다(언어 꾸러미도 그냥 문자열도 받는다). */
export function saidByServer(message: unknown): string | undefined {
  if (typeof message === 'string') return message.trim() || undefined;
  if (message && typeof message === 'object') {
    const bag = message as Record<string, unknown>;
    for (const key of ['ko', 'en']) {
      const v = bag[key];
      if (typeof v === 'string' && v.trim()) return v.trim();
    }
  }
  return undefined;
}

/** 판정에 필요한 사실 — **접히기 전의 것**이다. */
export interface LoginAttemptFacts {
  /** HTTP 상태. 응답이 아예 없었으면 `0`. */
  status: number;
  /** 응답 본문(있으면). */
  body?: unknown;
  /** 요청이 상한을 넘겼는가. */
  timedOut?: boolean;
  /** 연결 자체가 안 됐는가. */
  offline?: boolean;
  /** `Retry-After` 헤더(있으면). 율제한의 남은 초를 본문이 안 줄 때의 둘째 길이다. */
  retryAfterHeader?: string | null;
}

/**
 * 다섯 갈래 판정. **여기 한 곳에서만 갈린다.**
 *
 * 순서가 곧 판정이다:
 *   ① 연결이 없었다      — 서버는 이 요청을 본 적이 없다
 *   ② 잠금               — 본문이 잠금 시각을 들고 있으면 다른 모든 것보다 앞이다
 *   ③ 서버가 아프다(5xx) — 사용자의 입력 문제가 **아니다**
 *   ③′ 율제한(429)       — 너무 잦다 · **몇 초 뒤**인지 안다 (SEC-21)
 *   ④ 권한 없음(403)
 *   ⑤ 그 밖의 거절       — 아이디·비밀번호
 */
export function judgeLoginFailure(facts: LoginAttemptFacts): LoginFailure {
  const body = (facts.body ?? null) as Record<string, unknown> | null;

  // ⚠ [실측 2026-09-06 · 턴 H] 순서가 뒤집혀 있었다. 상한을 넘긴 요청도 상태 코드가
  //   `0` 이라서 **연결 없음으로 읽혔고**, 화면이 「연결을 확인하십시오」라고 말했다 —
  //   그런데 연결은 멀쩡했고 서버가 늦었을 뿐이다. 두 갈래는 사람이 할 일이 다르다.
  //   **늦음을 먼저 본다.**
  if (facts.timedOut || facts.status === 504 || facts.status === 408) {
    // 늦은 것도 「지금은 안 된다」이고, 사람이 할 일은 기다림이다.
    return { kind: 'server', text: SERVER };
  }
  if (facts.offline || facts.status === 0) {
    return { kind: 'network', text: NETWORK };
  }

  const lockMinutes = body && typeof body.lock_minutes === 'number' ? body.lock_minutes : null;
  const lockSeconds = body && typeof body.lock_seconds === 'number' ? body.lock_seconds : null;
  if (lockMinutes !== null || lockSeconds !== null) {
    return { kind: 'locked', text: lockedLine(lockMinutes ?? 0, lockSeconds ?? 0) };
  }

  // ★ 율제한(SEC-21) — 잠금 다음 · 5xx 앞. [실측 2026-09-17] 종전에는 이 답이 영문 HTML 403 이라
  //   「접근 권한 없음 · 관리자 문의」로 읽혔다 — 사람이 할 일은 **기다림**인데 다른 일을 시켰다.
  //   지금 서버는 429 JSON 에 `retry_after_seconds` 를 싣는다. 429 인데 초가 없으면 수를
  //   지어내지 않고 초 없는 문장(「잠시 뒤」)으로 말한다.
  const retryAfter = readRetryAfter(body, facts.retryAfterHeader);
  if (facts.status === 429 || (retryAfter !== null && body?.code === 'rate_limited')) {
    if (retryAfter === null) return { kind: 'rate_limited', text: SERVER };
    return { kind: 'rate_limited', text: rateLimitedLine(retryAfter), retryAfterSeconds: retryAfter };
  }

  if (facts.status >= 500) {
    return { kind: 'server', text: SERVER };
  }
  if (facts.status === 403) {
    return { kind: 'forbidden', text: FORBIDDEN };
  }

  // ★ 아이디가 틀렸는지 비밀번호가 틀렸는지 **적지 않는다.**
  //   서버는 둘을 다른 문장으로 말하지만(「사용자 이름이 올바르지 않습니다」),
  //   그 구별은 **계정이 있다는 사실을 남에게 알려 준다.** 화면이 한 문장으로 접는다.
  const said = saidByServer(body?.message);
  const attempts = readAttempts(said);
  if (attempts) {
    return {
      kind: 'credentials',
      text: `${CREDENTIALS} ${attemptsLine(attempts.now, attempts.max)}`,
    };
  }
  return { kind: 'credentials', text: CREDENTIALS };
}
