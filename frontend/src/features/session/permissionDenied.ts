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

export interface PermissionDeniedDetail {
  /** 사람이 읽을 한 줄. 서버의 말이 먼저다. */
  message: string;
  /** 어느 문에서 났나. 화면이 「어디가 막혔는지」를 말할 수 있게 한다. */
  path: string;
}

/**
 * 서버가 보낸 문장을 고른다. dj-core 는 `message` 를 **다국어 객체**로도 보낸다:
 *
 *     { "en": "Permission denied.", "ko": "권한이 거부되었습니다.", … }
 *
 * 한국어가 있으면 그것, 없으면 영어, 그것도 없으면 사전의 그 줄이다.
 * **여기서 새로 짓지 않는다.**
 */
export function messageOfDenial(body: unknown): string {
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
  return COPY_PERMISSION_DENIED;
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

export function announcePermissionDenied(body: unknown, path: string): void {
  const key = path || '?';
  if (announcedPaths.has(key)) return;
  announcedPaths.add(key);
  const detail: PermissionDeniedDetail = { message: messageOfDenial(body), path: key };
  try {
    window.dispatchEvent(new CustomEvent(PERMISSION_DENIED_EVENT, { detail }));
  } catch {
    // 창이 없는 자리(시험·SSR)에서는 조용히 지나간다 — 안내 한 줄이 제품을 못 세운다.
  }
}

/** 시험이 쓰는 자리. 제품 코드에서는 부르지 않는다. */
export function resetPermissionDeniedForTest(): void {
  announcedPaths.clear();
}

/** 이 창에서 이미 알린 문들. 시험과 화면이 「무엇이 막혔나」를 물을 수 있게 한다. */
export function deniedPaths(): string[] {
  return [...announcedPaths];
}
