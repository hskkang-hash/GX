/**
 * 사용자 언어 사전 — **화면 본문에 쓰는 말은 여기서만 나온다** (P-27 · P-29).
 *
 * 왜 사전인가 (사고 · 2026-09-25)
 * -------------------------------
 * 「연계 상태」 상자가 서버가 준 사유를 **그대로** 그렸다. 그 사유는 우리 언어였고,
 * 상대사명 · 계약번호 · 조항이 관제요원 화면에 문단으로 떴다. 정직하려던 것이 누출이 됐다.
 *
 * 뿌리는 「사유를 화면에 적어라」였다. 정정: **사유·출처·판정 근거는 관리자 자리와
 * 문서의 자리에 산다.** 사용자 본문에는 사용자 언어만.
 *
 * 규칙 하나
 * ---------
 * **사전에 없는 문구는 만들지 않는다.** 없으면 사전에 먼저 넣고 쓴다.
 * 정본은 `docs/design/GX-COPY_v1.md` 이고, 이 파일은 그 사전의 **코드 쪽 반쪽**이다.
 *
 * ⚠ 서버 열거값을 화면이 다시 정하지 않는다. 여기 있는 것은 **표시 이름**뿐이고,
 *   계약 스키마의 값(`waiting` · `critical` …)은 그대로 둔다 — 이름을 바꾸면
 *   계약이 바뀐다.
 */

/** 연계 상태 세 값의 **표시 이름**. 모르는 값이 오면 원문을 그리지 않는다 (아래 참조). */
export const LINK_STATUS_LABEL: Record<string, string> = {
  normal: '연계 정상',
  ok: '연계 정상',
  healthy: '연계 정상',
  waiting: '연계 대기',
  pending: '연계 대기',
  down: '연계 끊김',
  disconnected: '연계 끊김',
};

/** 표시 이름에 딸린 배지 색. 색만으로 구분하지 않으므로 **라벨과 한 줄에** 둔다. */
export const LINK_STATUS_BADGE: Record<string, 'success' | 'processing' | 'error'> = {
  normal: 'success',
  ok: 'success',
  healthy: 'success',
  waiting: 'processing',
  pending: 'processing',
  down: 'error',
  disconnected: 'error',
};

/**
 * 모르는 상태값이 왔을 때 그릴 말.
 *
 * ★ 원문(`link.status`)을 그리지 않는다. 앞판은 `연계 ${status}` 로 **영문 열거값을
 *   화면에 흘렸다** — 모르는 값을 원문으로 그리는 것은 안전한 기본값처럼 보이지만,
 *   그 자리는 사용자가 읽을 수 없는 말이 나오는 문이다.
 */
export const LINK_STATUS_UNKNOWN = '연계 상태 확인 중';

export function linkStatusLabel(status: string | undefined): string {
  if (!status) return LINK_STATUS_UNKNOWN;
  return LINK_STATUS_LABEL[status] ?? LINK_STATUS_UNKNOWN;
}

export function linkStatusBadge(status: string | undefined): 'success' | 'processing' | 'error' {
  if (!status) return 'processing';
  return LINK_STATUS_BADGE[status] ?? 'processing';
}

/* ════════════════════════════════════════════════════════════════════════
 * 실패를 말하는 자리 (P-78 · 2026-09-06 턴 H · GX-COPY 「불러오지 못한 자리」)
 * ════════════════════════════════════════════════════════════════════════
 *
 * 무엇이 이 표를 만들었나 [실측 · 직전 턴 walk_states]
 * ---------------------------------------------------
 * `StateBoundary` 가 사유를 받은 그대로 그렸다. 그 사유는 axios 가 만든 문장이고,
 * 서버가 죽으면 화면에 문자 그대로 「Network Error」, 500 이면 「Request failed with
 * status code 500」이 떴다 — 여섯 화면에서. 사전 2절이 이름으로 금지한 그 줄이다.
 *
 * ★ **소스 게이트로는 영영 안 잡힌다.** 그 문자열은 우리 소스 어디에도 없다 —
 *   런타임에 axios 가 넣는다. 그래서 고칠 자리는 「그 글자를 지우는 것」이 아니라
 *   **원문이 사용자 자리로 흘러드는 통로 자체를 끊는 것**이다. 통로는 한 곳이다.
 *
 * ★ 원문을 **버리지 않는다.** 콘솔로 보낸다 — 화면에서 지운 사유가 아무 데도 없으면
 *   다음 사람이 「왜 실패했나」를 못 되짚고, 그러면 이 판정이 디버깅을 죽인 셈이 된다.
 */

/** 실패의 갈래. **사람이 다음에 할 일이 다르면 다른 갈래다.** */
export type FailureKind = 'network' | 'timeout' | 'server' | 'forbidden' | 'unknown';

/**
 * 상태 코드 하나를 갈래로 옮긴다. **순수 함수다** — 시험이 이것만으로 전부 잰다.
 *
 * `0` 은 「응답이 아예 없었다」다: 서버가 죽었거나 길이 끊겼다. axios 가 그 자리에서
 * 「Network Error」를 만들고, 그 글자가 이 사전이 태어난 자리다.
 */
export function failureKind(status: number | undefined): FailureKind {
  if (status === 403 || status === 401) return 'forbidden';
  if (status === 504 || status === 408) return 'timeout';
  if (status === undefined || status === 0) return 'network';
  if (status >= 500) return 'server';
  if (status >= 400) return 'unknown';
  return 'unknown';
}

/** 오류 상자의 제목. 갈래가 무엇이든 **한 줄이다** — 제목까지 갈리면 화면이 시끄럽다. */
export const FAILURE_TITLE = '불러오지 못했습니다.';

/** 권한없음 상자의 제목. 오류와 **다른 상자**다 (DA-03 §2-5). */
export const FORBIDDEN_TITLE = '이 항목에 대한 권한이 없습니다.';

/** 제목 아래 한 줄 — **사용자가 다음에 할 일**을 적는다. */
const FAILURE_HINT: Record<FailureKind, string> = {
  network: '서버에 연결하지 못했습니다. 연결을 확인해 주십시오.',
  timeout: '응답이 늦어 불러오지 못했습니다.',
  server: '잠시 뒤 다시 시도해 주십시오.',
  forbidden: '다시 로그인하면 보일 수 있습니다.',
  unknown: '잠시 뒤 다시 시도해 주십시오.',
};

export function failureHint(status: number | undefined): string {
  return FAILURE_HINT[failureKind(status)];
}

/**
 * **원문을 콘솔로 보낸다.** 화면에는 한 자도 안 나간다.
 *
 * ⚠ 원문에는 서버가 준 사유가 통째로 들어 있을 수 있다(P-27 이 닫은 그 사고).
 *   그래서 이 함수 밖으로 원문을 돌려주지 않는다 — 돌려주면 부르는 쪽이 그것을
 *   화면에 그린다. 통로를 끊는다는 것은 **돌려줄 값을 안 만든다**는 뜻이다.
 */
export function reportFailure(where: string, raw: unknown, status?: number): void {
  try {
    // eslint-disable-next-line no-console
    console.warn('[gx.failure]', where, { status, raw });
  } catch {
    /* 콘솔이 없는 환경. 화면은 그대로 돈다. */
  }
}

/**
 * 잡은 예외 하나를 **화면에 그려도 되는 한 줄**로 옮긴다.
 *
 * 규칙 하나: **서버가 쓴 한국어 사유는 통과시키고, 그 밖에는 사전 문구로 바꾼다.**
 *   서버 사유 「표의 3행에 필요한 값이 없습니다.」는 사용자의 말이다.
 *   axios 사유 「Network Error」는 아니다. 둘을 가르는 칸이 `DsmApiError.fromServer` 다.
 *
 * ⚠ 서버가 준 문장이어도 **원문 표식이 섞여 있으면 버린다** — 서버가 예외를 그대로
 *   문자열로 실어 보내는 자리가 있고(500 본문), 그것은 서버가 「쓴」 문장이 아니라
 *   서버에서 **샌** 문장이다.
 */
const RAW_MARKERS = [
  'Network Error',
  'Request failed with status code',
  'AxiosError',
  'Internal Server Error',
  'Traceback (most recent call last)',
  '<!DOCTYPE',
  '[object Object]',
  'ECONNREFUSED',
  'status_code',
  'xhr poll error',
  'is not a function',
  'undefined',
];

function looksRaw(text: string): boolean {
  return RAW_MARKERS.some((m) => text.includes(m));
}

export function userFacingError(where: string, err: unknown, fallback: string): string {
  const status =
    err && typeof err === 'object' && 'status' in err
      ? (err as { status?: number }).status
      : undefined;
  const fromServer =
    err && typeof err === 'object' && 'fromServer' in err
      ? Boolean((err as { fromServer?: boolean }).fromServer)
      : false;
  const raw = err instanceof Error ? err.message : String(err);

  reportFailure(where, raw, status);

  if (fromServer && raw && !looksRaw(raw)) return raw;
  return `${fallback} ${failureHint(status)}`;
}

/**
 * 자료 출처 배지 — 사전 §2 의 「출처 칩」 줄이 요구한 것.
 *
 * ⚠ [실측 2026-09-06 · 턴 H] 훈련 모드 화면에 아직 「data_source = live」 칩이
 *   그대로 있었다. 사전이 §2 와 §4 **두 곳에서** 이름으로 금지한 줄이고,
 *   `walk_states` 는 이것을 「사용자 본문에 대장 언어」로 잡는다.
 *
 * ★ 사전이 정한 대로 **시드·훈련일 때만 그린다.** 실운영은 평상이고, 평상에
 *   배지를 붙이면 배지가 뜻을 잃는다.
 */
const DATA_SOURCE_LABEL: Record<string, string> = {
  seed: '시드(검수용)',
  seeded: '시드(검수용)',
  demo: '시드(검수용)',
  drill: '훈련',
  training: '훈련',
};

/** 그릴 말. 실운영(또는 모르는 값)이면 `null` — **그리지 않는다**는 뜻이다. */
export function dataSourceBadge(value: string | undefined): string | null {
  if (!value) return null;
  return DATA_SOURCE_LABEL[value.toLowerCase()] ?? null;
}
