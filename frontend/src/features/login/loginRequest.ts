/**
 * 로그인 요청 한 곳 — **접히기 전의 사실을 그대로 들고 온다** (P-78 ② · 턴 H).
 *
 * ★ 왜 인수 부품의 로그인 훅을 안 쓰나 — **사실이 도중에 사라진다**
 * ------------------------------------------------------------------
 * 그 훅은 실패를 `{ success:false, message }` 로 접어 준다. 접히는 동안
 * **상태 코드가 사라지고**, 응답이 아예 없으면 `message` 마저 `undefined` 가 된다.
 * 그 두 값이 없으면 화면은 다섯 갈래를 **가를 수가 없다** — 그것이 직전 턴에
 * 다섯 갈래 전부가 침묵한 뿌리다. 그러므로 접는 자리를 우리가 가진다.
 *
 * ★ 인수 화면(`LoginPage`)을 **고치지 않는다.** 그 파일은 남의 것이고, 우리는
 *   같은 문을 우리 층에서 부른다. 성공한 뒤의 절차(토큰 · 프로필 · 첫 화면)는
 *   그 부품의 훅을 **그대로** 쓴다 — 거기까지 다시 짓지 않는다.
 *
 * ★ **이중 제출은 여기서 막는다.** 화면의 상태로 막으면 늦다 [실측]: 리액트의
 *   상태는 다음 그림에서 반영되고 사람의 두 번째 클릭은 그 그림보다 빠르다.
 *   그래서 날아가는 약속을 하나만 두고, 두 번째 부름은 **그 약속을 그대로 받는다.**
 */
import { IDEMPOTENCY_HEADER, newIdempotencyKey } from '@/features/dsm/api';

/** 로그인 문. 이 저장소의 인증 대장(`docs/agent/authn_paths.md`)이 정한 자리다. */
export const LOGIN_PATH = '/api/v1/auth/login';

/** 화면이 정한 상한. 이보다 늦으면 로딩이 아니라 실패다(DA-03 §4-3 과 같은 수). */
export const LOGIN_TIMEOUT_MS = 10_000;

export interface LoginOutcome {
  /** HTTP 상태. 응답이 아예 없었으면 `0`. */
  status: number;
  body: unknown;
  timedOut: boolean;
  offline: boolean;
}

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined) || '';
  return raw.replace(/\/+$/, '');
}

/**
 * 장고의 위조 방지 표를 실어 준다 — 인수 부품의 요청기가 하는 일과 **같은 일**이다.
 * 두 벌이 되지 않게 하는 유일한 길은 없다(그 부품의 인터셉터에 손이 닿지 않는다).
 * 그래서 하는 일을 여기에 적어 둔다: 다르면 다음 사람이 이 주석에서 안다.
 */
function csrfToken(): string | null {
  try {
    const hit = document.cookie
      .split(';')
      .map((c) => c.trim())
      .find((c) => c.startsWith('csrftoken='));
    return hit ? hit.split('=')[1] : null;
  } catch {
    return null;
  }
}

/**
 * 지금 살아 있는 로그인 시도. **하나뿐이다.**
 *
 * ⚠⚠ [실측 2026-09-06 · 턴 H] 처음에는 「날아가는 동안만」 막았다. 그래도 시험 도구는
 *   요청을 **2건** 셌다 — 두 번 누르는 간격보다 **첫 응답이 더 빨랐기 때문**이다.
 *   (가짜 응답은 즉시 오고, 실서버의 401 도 수십 ms 다.) 두 번째 누름이 도착했을 때
 *   첫 시도는 이미 끝나 있었고, 끝난 것은 막을 것이 없었다.
 *   → **끝난 뒤에도 잠깐 들고 있어야** 이중 제출이 막힌다. 그 잠깐이 멱등 창이다.
 *
 * ★ 창은 **같은 값**에만 적용된다. 사람이 비밀번호를 고쳐 다시 누르면 그것은
 *   다른 의도이고, 그 자리를 막으면 「고쳐 넣었는데 화면이 안 받는다」가 된다.
 */
const IDEMPOTENT_WINDOW_MS = 2_000;

let flight: Promise<LoginOutcome> | null = null;
let lastKey = '';
let lastAt = 0;
let lastOutcome: LoginOutcome | null = null;

function keyOf(u: string, p: string, e: boolean): string {
  return `${u}|${p}|${e ? 1 : 0}`;
}

/** 두 번째 누름이 첫 번째와 같은 것을 받는가 — 화면이 이 사실을 말한다. */
export function loginInFlight(): boolean {
  return flight !== null;
}

export async function requestLogin(
  username: string,
  password: string,
  endPreviousSession: boolean,
): Promise<LoginOutcome> {
  const key = keyOf(username, password, endPreviousSession);
  if (flight && key === lastKey) return flight;
  if (
    lastOutcome &&
    key === lastKey &&
    Date.now() - lastAt < IDEMPOTENT_WINDOW_MS
  ) {
    // 같은 값으로 곧바로 또 눌렀다. **같은 답을 준다** — 새 요청을 만들지 않는다.
    return lastOutcome;
  }
  lastKey = key;
  lastOutcome = null;

  const run = async (): Promise<LoginOutcome> => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), LOGIN_TIMEOUT_MS);
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      // ⚠ 서버 신호 대기 — 이 저장소의 어느 라우트도 아직 이 이름을 읽지 않는다.
      //   싣는 이유는 브라우저 쪽 중복 억제와, 서버가 받는 날의 준비다.
      [IDEMPOTENCY_HEADER]: newIdempotencyKey(),
    };
    const csrf = csrfToken();
    if (csrf) headers['X-CSRFToken'] = csrf;

    let res: Response;
    try {
      res = await fetch(`${apiBase()}${LOGIN_PATH}`, {
        method: 'POST',
        headers,
        credentials: 'include',
        cache: 'no-store',
        signal: ctrl.signal,
        body: JSON.stringify({
          username,
          password,
          end_previous_session: endPreviousSession,
          otp_code: '',
        }),
      });
    } catch {
      clearTimeout(timer);
      // 상한을 넘긴 것과 길이 끊긴 것은 **다른 갈래**다. 둘을 뭉치면 사용자가
      // 「연결을 봐라」와 「기다려라」 중 어느 것을 할지 모른다.
      if (ctrl.signal.aborted) {
        return { status: 0, body: null, timedOut: true, offline: false };
      }
      return { status: 0, body: null, timedOut: false, offline: true };
    }
    clearTimeout(timer);

    let body: unknown = null;
    try {
      body = await res.json();
    } catch {
      // 본문이 JSON 이 아니다(장고의 HTML 오류 쪽). **그 바이트를 화면에 옮기지
      // 않는다** — 그 자리가 「<!DOCTYPE」이 사용자 자리에 뜨는 문이다.
      body = null;
    }
    return { status: res.status, body, timedOut: false, offline: false };
  };

  flight = run()
    .then((outcome) => {
      lastOutcome = outcome;
      lastAt = Date.now();
      return outcome;
    })
    .finally(() => {
      flight = null;
    });
  return flight;
}
