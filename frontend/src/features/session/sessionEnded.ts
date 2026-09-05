/**
 * P-62 꼬리 — **끊긴 화면이 왜 끊겼는지 말한다.** (2026-09-05 턴 F · 차선 S)
 *
 * 무엇이 문제였나 [실측 턴 E · `docs/agent/authn_paths.md` §8]
 * ------------------------------------------------------------
 * 이 제품은 동시 접속이 1개다. 휴대전화로 로그인하면 자리 데스크톱이 그 자리에서 죽는다.
 * 그런데 죽은 화면이 받는 것은 `401 {"detail": "Unauthorized"}` 한 줄이었고, 앞단은
 * 그것을 보자마자 **말없이 `/login` 으로 튕겼다**(`services/API.ts::redirectOn401`).
 *
 *   → 사람이 보는 것: 하던 일이 사라지고 로그인 화면이 떠 있다. **왜인지는 아무데도 없다.**
 *     그리고 그 모양은 「토큰이 깨졌다」·「서버가 죽었다」와 **글자 하나까지 같다.**
 *
 * 서버는 이미 말하고 있다 [턴 E · `common/session_limit.py`]
 * ----------------------------------------------------------
 *     401 { "detail": "다른 기기에서 로그인되었습니다",
 *           "reason_code": "session_evicted",
 *           "origin_detail": "Unauthorized" }
 *
 * 그 글자가 사람에게 닿으려면 **앞단이 그것을 그려야 한다.** 이 파일이 그 한 줄이다.
 *
 * ★ 낱말을 만들지 않았다 (GX-COPY 규칙 1)
 * ----------------------------------------
 * 화면에 뜨는 문장은 **서버가 보낸 `detail` 그대로**다. 서버가 말이 없을 때만
 * 사전(`docs/design/GX-COPY_v1.md` §5)의 그 줄로 떨어진다. 여기서 새 문장을 지으면
 * 사전과 화면이 갈라지고, 갈라진 뒤에는 어느 쪽이 제품의 말인지 아무도 모른다.
 *
 * ⚠ **한 줄이지 절이 아니다.** 동시 세션을 여는 것은 이 파일이 못 한다 —
 *   그 벽은 dj-core 의 `user.token` 한 칸이고 §0.4 다(UX-24b). 월 대형 화면만은
 *   세션 없이 여는 길을 이번 턴에 냈다(UX-24a · `X-GX-Wall-Token`).
 */

/** 서버가 「밀려남」에 붙이는 표식. 이 글자가 서버와 다르면 이 절은 아무것도 안 그린다. */
export const SESSION_EVICTED_CODE = 'session_evicted';

/**
 * 사전 문구 — `docs/design/GX-COPY_v1.md` §5 「2026-09-05 턴 E 추가」.
 * **여기서 만든 문장이 아니다.** 서버가 말이 없을 때만 쓴다.
 */
export const COPY_SESSION_EVICTED = '다른 기기에서 로그인되었습니다';

/** 되돌아가는 문. 제품의 로그인 문은 하나다(`authn_paths.md` §1). */
export const LOGIN_PATH = '/login';

/** 창 안에서만 도는 신호. 서버로 나가지 않고, 저장되지도 않는다. */
export const SESSION_ENDED_EVENT = 'gx:session-ended';

export interface SessionEndedDetail {
  /** 사람이 읽을 한 줄. 서버의 `detail` 이 먼저다. */
  message: string;
}

/**
 * 이 401 이 **밀려남인가.** 아니면 이 절은 손대지 않는다.
 *
 * ★ 좁게 잡는다. 넓게 잡으면 비밀번호를 틀린 사람이 「다른 기기에서 로그인되었습니다」를
 *   읽고 있지도 않은 기기를 찾는다 — 서버 쪽이 같은 이유로 `reason_code` 를 붙였다.
 */
export function isSessionEvicted(body: unknown): boolean {
  if (!body || typeof body !== 'object') return false;
  return (body as { reason_code?: unknown }).reason_code === SESSION_EVICTED_CODE;
}

/** 서버가 보낸 문장. 없으면 사전의 그 줄. **여기서 새로 짓지 않는다.** */
export function messageOf(body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  return typeof detail === 'string' && detail.trim()
    ? detail
    : COPY_SESSION_EVICTED;
}

/**
 * 끊긴 사실을 화면에 알린다. **한 번만** — 401 은 보통 여러 요청에서 함께 온다
 * (월 모드는 20초마다 셋을 부른다). 그때마다 겹쳐 그리면 안내가 소음이 된다.
 */
let announced = false;

export function announceSessionEnded(body: unknown): void {
  if (announced) return;
  announced = true;
  const detail: SessionEndedDetail = { message: messageOf(body) };
  try {
    window.dispatchEvent(new CustomEvent(SESSION_ENDED_EVENT, { detail }));
  } catch {
    // 창이 없는 자리(시험·SSR)에서는 조용히 지나간다 — 안내 한 줄이 제품을 못 세운다.
  }
}

/** 시험이 쓰는 자리. 제품 코드에서는 부르지 않는다. */
export function resetSessionEndedForTest(): void {
  announced = false;
}

/** 이 창에서 이미 알렸는가. `redirectOn401` 이 **튕길지 말지**를 이것으로 고른다. */
export function sessionEndedAnnounced(): boolean {
  return announced;
}
