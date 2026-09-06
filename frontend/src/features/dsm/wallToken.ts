/**
 * 월 표시 토큰을 **브라우저가 싣는 자리** — 앞판 배선 (차선 C · 2026-09-06 턴 G).
 *
 * 무엇이 없었나 [실측 · 직전 턴 증거 문서 §8]
 * ------------------------------------------
 * 서버 면은 이미 섰다. 넷째 문(세션이 아닌 문)이 열리고, 쓰기 20건을 두드려 20건이
 * 거부됐고, 자리 데스크톱이 살아 있었다. 그런데 **브라우저는 그 문을 부른 적이 없다.**
 * 앞판이 머리글자 한 줄을 안 실었기 때문이다. 그래서 월 화면은 종전대로 로그인
 * 세션으로 떴고, 이 제품은 동시 접속이 하나이므로 **월을 켜면 자리 화면이 죽었다.**
 * 이 파일이 그 한 줄을 싣는다.
 *
 * ★ 왜 이 앱의 공용 요청기(`services/API.ts`)를 쓰지 않나 — **자격증명이 둘이면 닫힌다**
 * ----------------------------------------------------------------------------------
 * 서버는 한 요청에 자격증명이 둘이면(머리글자 + 로그인 자리) 그 자리에서 거절한다.
 * 낮은 권한 토큰이 높은 권한 자리에 얹혀 가는 모양을 만들지 않기 위한 판정이고,
 * 그 판정은 옳다. 공용 요청기는 인수 부품이 만든 것이라 로그인 자리를 **자동으로**
 * 채우고, 401 을 보면 재발급을 시도하고, 실패하면 로그인 화면으로 튕긴다 —
 * 셋 다 월 화면이 원하는 동작이 아니다. 그래서 이 파일은 **맨 요청기**를 쓴다.
 *
 * ★ 토큰은 **주소창에서 한 번만** 받는다
 * --------------------------------------
 * 관제실 대형 화면에는 자판이 없다. 사람이 할 수 있는 일은 주소를 한 번 여는 것뿐이고,
 * 그래서 `?token=` 으로 받는다. 받은 즉시 주소창에서 **지운다** — 지우지 않으면
 * 그 화면을 찍은 사진 한 장이 곧 토큰이 된다(관제실 화면은 사진에 자주 찍힌다).
 *
 * ⚠ 저장 자리는 이 브라우저의 로컬 저장소다. 대형 화면은 밤중에 스스로 새로고침하고,
 *   그때마다 사람이 주소를 다시 칠 수는 없다. 대신 **12시간이 지나면 서버가 거절**하고,
 *   회수되면 즉시 거절된다 — 저장한 값이 오래 사는 것이 아니라 **문이 짧게 산다**.
 */

/** 이 토큰이 실리는 자리. 로그인 자리가 **아니다**. */
export const WALL_TOKEN_HEADER = 'X-GX-Wall-Token';

/** 주소로 받는 이름. */
export const WALL_TOKEN_PARAM = 'token';

/** 이 브라우저에 적어 두는 이름. */
export const WALL_TOKEN_STORAGE_KEY = 'gx.wall.display.token';

/** 이 토큰이 여는 화면. 하나다. */
export const WALL_SCREEN_PATH = '/wall';

/** 서버가 이 토큰에게 여는 문 둘. 화면이 문을 더 부르려면 서버 목록도 함께 늘어야 한다. */
export const WALL_TOKEN_PATHS = [
  '/api/dsm/events/queue',
  '/api/dsm/cameras/pulse',
] as const;

/** 요청 상한. 공용 요청기와 같은 수를 쓴다 — 두 벌로 두면 한쪽이 늙는다. */
const WALL_TIMEOUT_MS = 10_000;

function storage(): Storage | null {
  try {
    return window.localStorage;
  } catch {
    // 사설 모드·정책으로 막힌 브라우저. 그때는 **이번 한 번만** 여는 것으로 족하다.
    return null;
  }
}

/** 지금 이 브라우저가 들고 있는 토큰. 없으면 `null`. */
export function wallToken(): string | null {
  const value = storage()?.getItem(WALL_TOKEN_STORAGE_KEY) ?? null;
  return value && value.trim() ? value.trim() : null;
}

export function clearWallToken(): void {
  try {
    storage()?.removeItem(WALL_TOKEN_STORAGE_KEY);
  } catch {
    /* 지우지 못해도 화면은 계속 돈다. 서버가 12시간 뒤 거절한다. */
  }
}

/**
 * 주소에 실려 온 토큰을 **받아 적고 주소에서 지운다.**
 *
 * 돌려주는 값은 「지금 월 토큰이 있는가」다. 앱이 라우터를 세우기 **전에** 한 번 부른다 —
 * 세운 뒤에 부르면 첫 화면이 이미 로그인 관문을 지나간 뒤다.
 */
export function adoptWallToken(): boolean {
  if (typeof window === 'undefined') return false;
  let received: string | null = null;
  try {
    const url = new URL(window.location.href);
    received = url.searchParams.get(WALL_TOKEN_PARAM);
    if (received && received.trim()) {
      storage()?.setItem(WALL_TOKEN_STORAGE_KEY, received.trim());
      // 주소창에서 지운다. 남겨 두면 이 화면을 찍은 사진이 곧 토큰이다.
      url.searchParams.delete(WALL_TOKEN_PARAM);
      window.history.replaceState(
        null,
        '',
        url.pathname + (url.search || '') + (url.hash || ''),
      );
    }
  } catch {
    /* 주소를 못 읽었다. 저장된 값이 있으면 그것으로 돈다. */
  }
  return wallToken() !== null;
}

/** 지금 월 토큰으로 열린 화면인가. */
export function hasWallToken(): boolean {
  return wallToken() !== null;
}

/** 이 토큰으로 부를 수 있다고 **서버가 선언한** 문인가. */
export function isWallTokenPath(path: string): boolean {
  const bare = (path.split('?')[0] || '').replace(/\/+$/, '') || '/';
  return WALL_TOKEN_PATHS.some((p) => p === bare);
}

export class WallTokenError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'WallTokenError';
    this.status = status;
  }
}

function apiBase(): string {
  const raw = (import.meta.env.VITE_API_URL as string | undefined) || '';
  return raw.replace(/\/+$/, '');
}

/**
 * 월 토큰으로 읽는다. **읽기뿐이다** — 이 함수에는 쓰기 갈래가 없다.
 *
 * ★ 로그인 자리를 싣지 않고 쿠키도 보내지 않는다. 서버가 자격증명 둘을 거절하기
 *   때문이고, 그 거절은 옳다. 여기서 지키는 것이 그 판정의 앞쪽 절반이다.
 */
export async function wallGet<T>(
  path: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const token = wallToken();
  if (!token) {
    throw new WallTokenError('월 표시 토큰이 없습니다.', 401);
  }
  if (!isWallTokenPath(path)) {
    // 서버가 거절할 것을 **부르기 전에** 안다. 부르면 403 이 오고, 그 403 은
    // 「고장」처럼 보인다 — 목록 밖 경로는 여기서 멈춘다.
    throw new WallTokenError(
      '월 화면이 열 수 없는 자리입니다.',
      403,
    );
  }
  const query = new URLSearchParams();
  Object.entries(params ?? {}).forEach(([k, v]) => {
    if (v !== undefined && v !== null) query.append(k, String(v));
  });
  const url = `${apiBase()}${path}${query.toString() ? `?${query}` : ''}`;

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), WALL_TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(url, {
      method: 'GET',
      headers: { [WALL_TOKEN_HEADER]: token, Accept: 'application/json' },
      credentials: 'omit',
      cache: 'no-store',
      signal: ctrl.signal,
    });
  } catch (err) {
    clearTimeout(timer);
    if (ctrl.signal.aborted) {
      throw new WallTokenError(
        `응답이 ${WALL_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`,
        504,
      );
    }
    throw new WallTokenError(
      err instanceof Error ? err.message : '요청이 실패했습니다.',
      0,
    );
  }
  clearTimeout(timer);

  let body: any = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    throw new WallTokenError(
      body?.detail ?? body?.message ?? `요청이 실패했습니다 (${res.status})`,
      res.status,
    );
  }
  // 이 저장소의 봉투는 거절을 200 안에 담아 내보내는 자리가 있다 — 본문도 본다.
  const inner = typeof body?.status_code === 'number' ? body.status_code : undefined;
  if (inner !== undefined && inner >= 400) {
    throw new WallTokenError(
      body?.detail ?? body?.message ?? `요청이 거절되었습니다 (${inner})`,
      inner,
    );
  }
  return (body?.data ?? body) as T;
}
