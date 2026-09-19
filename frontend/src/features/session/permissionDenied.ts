/**
 * P-88 — **「볼 권한이 없다」와 「볼 것이 없다」는 다른 문장이다.** (2026-09-07 턴 J · 조율자)
 *
 * 무엇이 문제였나 [실측 2026-09-07 · 계정 `gxprobe_e2e` · `GET /api/devices/devices-management`]
 * -------------------------------------------------------------------------------------------
 * dj-core 의 `path_permission` 은 권한 거절을 **200 봉투 안**에 담아 보냈다:
 *
 *     HTTP 200  { "success": false, "status_code": 403, "message": "Permission denied." }
 *
 *   → 표는 행을 하나도 못 받고 **빈 표**를 그린다. 사람이 읽는 것은 「자료가 없다」다.
 *     오류율 대시보드도 그 거절을 **성공으로 센다**(D-358).
 *     **사람이 속는 자리**이고, `verify_envelope`(D-349)가 이 턴에 커밋을 막은 이유다.
 *
 * 이 턴에 서버 쪽은 고쳤다 — `API_CONTRACT_PROMOTE_PATHS` 에 그 라우트 하나를 더해
 * 같은 거절이 이제 **HTTP 403** 으로 나간다(전/후 실측 200 → 403).
 * 그러면 이번엔 앞단이 그 403 을 **말해야 한다.** 이 파일이 그 자리다.
 *
 * ★ 왜 이 파일이 필요한가 — **승격은 반쪽이면 더 나쁘다**
 * ------------------------------------------------------
 * 서버만 승격하고 앞단이 조용하면, 빈 표가 **빈 표 + 멈춘 스피너**가 된다.
 * 「거절을 200 으로 보내는 것」보다 「거절을 말없이 삼키는 것」이 낫지 않다.
 * 그래서 승격과 이 안내는 **같은 턴에 같이** 선다.
 *
 * ★ 낱말을 만들지 않았다 (GX-COPY 규칙 1) — `sessionEnded.ts` 와 같은 규칙
 * ----------------------------------------------------------------------
 * 화면에 뜨는 문장은 **서버가 보낸 `message`/`detail` 그대로**이고, 서버가 말이 없을
 * 때만 사전의 그 줄로 떨어진다. 여기서 새 문장을 지으면 사전과 화면이 갈라진다.
 *
 * ⚠ **이 파일은 오류를 삼키지 않는다.** 알리고 **그대로 다시 던진다** —
 *   화면이 제 갈래로 처리할 기회를 뺏지 않는다(`API.ts::noteEvictionOn401` 과 같은 규율).
 *
 * ⚠ **아직 그리는 쪽이 없다.** 이 파일은 신호를 낸다. 그 신호를 받아 화면에 한 줄을
 *   그리는 것은 차선 C 의 일이고(전역 거절 처리기 · 턴 J §3), 그 전까지 사람이 보는 것은
 *   **종전과 같다.** 없는 배선을 있는 척하지 않는다.
 */

/** 창 안에서만 도는 신호. 서버로 나가지 않고, 저장되지도 않는다. */
export const PERMISSION_DENIED_EVENT = 'gx:permission-denied';

/**
 * 사전 문구 — `docs/design/GX-COPY_v1.md`. **여기서 만든 문장이 아니다.**
 * 서버가 말이 없을 때만 쓴다.
 */
export const COPY_PERMISSION_DENIED = '볼 권한이 없습니다';

/**
 * ★★ [턴 V · 차선 U24] **읽기 거부와 쓰기 거부는 다른 문장이다.**
 *
 * 무엇이 이 갈래를 만들었나 [실측 2026-09-17 턴 U · V 가 U4 로 눌렀다 · `/dsm/reports`]
 * ------------------------------------------------------------------------------------
 * 읽기 전용 계정으로 「만들기」를 누르면 서버는 이렇게 답한다:
 *
 *     HTTP 403  { "code": "read_only_role",
 *                 "message": {"ko": "읽기 전용 계정입니다 — 이 작업은 수행할 수 없습니다."} }
 *
 * 서버의 그 한 줄은 **쓰기의 말**인데, 그 밑에 띠가 붙이던 결과줄은
 * 「이 자료는 지금 계정의 권한으로 열 수 없습니다.」 — **읽기의 말**이었다.
 * 한 상자 안에서 두 문장이 서로 다른 일을 말한다. 누른 사람은 「만들기」를 눌렀는데
 * 화면은 「못 연다」고 답한다.
 *
 * 그래서 **메서드로** 가른다 — 상태 코드가 아니라 메서드가 읽기와 쓰기를 가르는 칸이다.
 * `GET`·`HEAD`·`OPTIONS` 는 읽기, 나머지는 쓰기다. 메서드를 모르면(옛 부르는 쪽)
 * **읽기로 떨어진다** — 종전 문장이 그대로 나오므로 아무도 새로 다치지 않는다.
 */
export type DenialKind = 'read' | 'write';

/** 읽기로 세는 메서드. 이 밖은 전부 쓰기다. */
const READ_METHODS = new Set(['get', 'head', 'options']);

export function denialKindOf(method?: string | null): DenialKind {
  const m = String(method ?? '').trim().toLowerCase();
  if (!m) return 'read';
  return READ_METHODS.has(m) ? 'read' : 'write';
}

/** 서버가 말이 없을 때 쓰는 **쓰기** 쪽 한 줄. 사전에 등재돼 있다. */
export const COPY_PERMISSION_DENIED_WRITE = '고칠 권한이 없습니다';

/** 결과줄 두 개 — **최소쌍이다.** 한 낱말만 다르고 그 낱말이 전부다. */
export const COPY_DENIED_CONSEQUENCE: Record<DenialKind, string> = {
  read: '이 자료는 지금 계정의 권한으로 볼 수 없습니다.',
  write: '이 자료는 지금 계정의 권한으로 고칠 수 없습니다.',
};

export interface PermissionDeniedDetail {
  /** 사람이 읽을 한 줄. 서버의 말이 먼저다. */
  message: string;
  /** 어느 문에서 났나. 화면이 「어디가 막혔는지」를 말할 수 있게 한다. */
  path: string;
  /** 읽기가 막혔나 쓰기가 막혔나. 결과줄이 이 칸으로 갈린다. */
  kind: DenialKind;
}

/**
 * 서버가 보낸 문장을 고른다. dj-core 는 `message` 를 **다국어 객체**로도 보낸다:
 *
 *     { "en": "Permission denied.", "ko": "권한이 거부되었습니다.", … }
 *
 * 한국어가 있으면 그것, 없으면 영어, 그것도 없으면 사전의 그 줄이다.
 * **여기서 새로 짓지 않는다.**
 */
export function messageOfDenial(body: unknown, kind: DenialKind = 'read'): string {
  const raw = (body as { message?: unknown; detail?: unknown } | null) ?? null;
  const cand = raw?.message ?? raw?.detail;
  if (typeof cand === 'string' && cand.trim()) return cand;
  if (cand && typeof cand === 'object') {
    const m = cand as Record<string, unknown>;
    for (const key of ['ko', 'en']) {
      const v = m[key];
      if (typeof v === 'string' && v.trim()) return v;
    }
  }
  return kind === 'write' ? COPY_PERMISSION_DENIED_WRITE : COPY_PERMISSION_DENIED;
}

/**
 * 이 응답이 **권한 거절인가.**
 *
 * ★ 좁게 잡는다 — 403 만 본다. 401(누구인지 모른다)과 403(누구인지는 아는데 안 된다)은
 *   다른 문장이고, 401 은 이미 `sessionEnded.ts` 가 제 갈래로 본다.
 *   ⚠ 200 봉투 안의 `status_code: 403` 은 **여기서 세지 않는다.** 그것을 여기서
 *     받아 주면 봉투를 승격할 이유가 사라지고, `verify_envelope` 가 지키는 것이
 *     앞단의 친절로 덮인다 — 고칠 곳을 덮는 친절은 고치지 않는 것과 같다.
 */
export function isPermissionDenied(status: unknown): boolean {
  return status === 403;
}

/**
 * 거절을 화면에 알린다.
 *
 * **문마다 한 번씩** 알린다 — 한 화면이 여러 문을 부르는데 그중 하나만 막힐 수 있고,
 * 그때 「어디가 막혔는지」가 사라지면 안내가 소용없다. 같은 문이 반복해 막히는 것
 * (표 새로고침)은 겹쳐 그리지 않는다.
 */
const announcedPaths = new Set<string>();

/**
 * 열쇠는 **갈래 + 문**이다. 같은 문이 읽기로도 쓰기로도 막힐 수 있고
 * (`/api/dsm/reports/runs` 는 목록을 읽고 실행을 만든다), 그 둘은 다른 문장이다.
 * 열쇠를 문 하나로 두면 먼저 온 쪽이 나중 쪽을 삼킨다.
 */
function announceKey(kind: DenialKind, path: string): string {
  return kind + ' ' + path;
}

export function announcePermissionDenied(
  body: unknown,
  path: string,
  method?: string | null,
): void {
  const kind = denialKindOf(method);
  const p = path || '?';
  const key = announceKey(kind, p);
  if (announcedPaths.has(key)) return;
  announcedPaths.add(key);
  const detail: PermissionDeniedDetail = {
    message: messageOfDenial(body, kind),
    path: p,
    kind,
  };
  try {
    window.dispatchEvent(new CustomEvent(PERMISSION_DENIED_EVENT, { detail }));
  } catch {
    // 창이 없는 자리(시험·SSR)에서는 조용히 지나간다 — 안내 한 줄이 제품을 못 세운다.
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// ★★ [턴 V · 차선 U24] **한 거절은 한 자리에서만 말한다** — 임자 선언
// ═══════════════════════════════════════════════════════════════════════════
//
// 무엇이 문제였나 [실측 2026-09-17 턴 U · V · U4 로 `/dsm/reports` 의 「만들기」]
// -----------------------------------------------------------------------------
// 화면은 이미 제 **상태 칸**에 네 문장을 적는다(무엇을 못 했나 · 왜 · 무엇을 하면
// 되나 · **그 요청을 다시 내는 단추**). 그런데 같은 403 을 이 띠가 화면 맨 위에
// 덮개로 한 번 더 적었다. 사람이 보는 것은 **같은 사실 두 장**이고, 위의 한 장은
// 아래 상태 칸을 **가린다**. 두 장 중 값이 있는 쪽은 아래다 — 거기에만 단추가 있다.
//
// 그래서 화면이 **임자를 선언한다.** 「이 문들의 거절은 내가 내 상태 칸에 적는다」고
// 말한 화면이 붙어 있는 동안, 띠는 그 문들을 **안 그린다.**
//
// ★ 기본은 **띠가 그리는 것**이다. 선언하지 않은 화면은 종전 그대로다 —
//   말없이 삼키는 길을 기본으로 만들지 않는다(이 파일 머리말의 그 규율).
// ★ 자물쇠가 아니다. 거절은 그대로 `deniedPaths()` 에 남고 오류도 그대로 던져진다.
//   여기서 정하는 것은 **누가 말하는가**뿐이다.

/** 이 창에서 지금 임자가 있는 문 앞머리들. 화면이 사라지면 함께 사라진다. */
const ownedPrefixes = new Map<string, number>();

/** 임자 목록이 바뀌었다 — 띠가 다시 그린다. */
export const PERMISSION_DENIED_OWNER_EVENT = 'gx:permission-denied-owner';

function fireOwnerChanged(): void {
  try {
    window.dispatchEvent(new Event(PERMISSION_DENIED_OWNER_EVENT));
  } catch {
    /* 창이 없는 자리. */
  }
}

/**
 * 「이 문들의 거절은 내가 적는다」. 돌려주는 함수를 부르면 선언이 풀린다
 * (리액트 `useEffect` 의 청소 함수가 그대로 이것이다).
 *
 * 같은 앞머리를 두 화면이 선언할 수 있으므로 **수를 센다** — 하나가 떠나도
 * 남은 하나의 선언이 살아 있어야 한다.
 */
export function ownDenialPaths(prefixes: readonly string[]): () => void {
  const mine = prefixes.filter((p) => typeof p === 'string' && p.length > 0);
  for (const p of mine) ownedPrefixes.set(p, (ownedPrefixes.get(p) ?? 0) + 1);
  if (mine.length) fireOwnerChanged();
  let released = false;
  return () => {
    if (released) return;
    released = true;
    for (const p of mine) {
      const n = (ownedPrefixes.get(p) ?? 1) - 1;
      if (n <= 0) ownedPrefixes.delete(p);
      else ownedPrefixes.set(p, n);
    }
    if (mine.length) fireOwnerChanged();
  };
}

/** 이 문에 지금 임자가 있나. 있으면 띠는 입을 다문다. */
export function hasDenialOwner(path: string): boolean {
  const p = String(path || '');
  for (const prefix of ownedPrefixes.keys()) {
    if (p.startsWith(prefix)) return true;
  }
  return false;
}

/** 시험이 쓰는 자리. 제품 코드에서는 부르지 않는다. */
export function resetPermissionDeniedForTest(): void {
  announcedPaths.clear();
  ownedPrefixes.clear();
}

/**
 * 이 창에서 이미 알린 것들. 시험과 화면이 「무엇이 막혔나」를 물을 수 있게 한다.
 * ⚠ 한 줄은 **갈래와 문**이다(`read /api/...`) — 같은 문의 읽기와 쓰기가 따로 센다.
 */
export function deniedPaths(): string[] {
  return [...announcedPaths];
}
