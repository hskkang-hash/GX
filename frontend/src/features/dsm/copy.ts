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
export type FailureKind =
  | 'network'
  | 'timeout'
  | 'server'
  | 'forbidden'
  /**
   * ★★ [P-123 · UX-31 ③ · 2026-09-10 턴 O] **404 는 실패가 아니라 부재다.**
   *
   *   [실측 2026-09-10] 없는 사건 번호로 상세를 열면 화면이 이렇게 말했다:
   *       「불러오지 못했습니다. 잠시 뒤 다시 시도해 주십시오.」  + 「다시 시도」
   *   그 문장은 **거짓 약속**이다. 잠시 뒤에 다시 시도해도 그 사건은 영영 없다.
   *   그 화면에서 사람은 기다리고, 새로 고치고, 다시 기다린다 — 그리고 옆에
   *   **「알림 보내기」가 살아 있었다.** 없는 사건에 알림을 보내는 단추다.
   *
   *   그래서 404 를 **다른 갈래**로 뽑는다. 다른 갈래라야 화면이 다른 상자를
   *   그리고(오류 빨강이 아니라 안내), 「다시 시도」를 **안 그린다** —
   *   누를 것이 없는 단추는 거짓말이다(`StateBoundary` 의 `onRetry` 규율과 같은 말).
   */
  | 'notfound'
  | 'unknown';

/**
 * 상태 코드 하나를 갈래로 옮긴다. **순수 함수다** — 시험이 이것만으로 전부 잰다.
 *
 * `0` 은 「응답이 아예 없었다」다: 서버가 죽었거나 길이 끊겼다. axios 가 그 자리에서
 * 「Network Error」를 만들고, 그 글자가 이 사전이 태어난 자리다.
 */
export function failureKind(status: number | undefined): FailureKind {
  if (status === 403 || status === 401) return 'forbidden';
  // 404 는 「지금 못 가져왔다」가 아니라 「그것이 없다」다. 다시 시도할 것이 없다.
  if (status === 404) return 'notfound';
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

/**
 * 없는 것의 제목 — **오류가 아니다.**
 *
 * ★ 기본값이 「항목」인 이유: 이 상자는 사건·청구·카메라·발송 어디에서나 쓰인다.
 *   무엇이 없는지 아는 것은 **부르는 쪽**이므로, 아는 화면은 `notFoundTitle` 로
 *   자기 말을 준다(사건 화면이라면 「없는 사건입니다」). 모르는 자리에서
 *   「없는 사건입니다」라고 적으면 그것은 없는 사실을 말하는 것이다.
 */
export const NOT_FOUND_TITLE = '없는 항목입니다.';

/** 사건 화면이 쓰는 말. 글자를 화면에 흩지 않기 위해 여기 둔다(P-123 · UX-31 ③). */
export const NOT_FOUND_TITLE_EVENT = '없는 사건입니다.';

/**
 * 제목 아래 한 줄 — **사용자가 다음에 할 일**을 적는다.
 *
 * ★ [턴 S · 차선 F] 이 한 줄은 이제 **네 문장 중 둘을 이어 붙인 것**이다
 *   (아래 `failureSpeech` 의 ②왜 + ③지금 무엇). 표를 두 벌로 두지 않기 위해서다 —
 *   두 벌이면 한쪽만 고쳐지는 날 화면과 사전이 갈린다(D-212 · D-369).
 */
export function failureHint(status: number | undefined): string {
  const said = failureSpeech(status);
  return `${said.why} ${said.next}`;
}

/**
 * 이 상태 코드가 **없음**인가. 화면이 「다시 시도」와 실행 단추를 **끄는** 자리다.
 *
 * ★ 함수 하나로 내주는 이유: 판정이 두 벌이 되면(`status === 404` 를 화면마다 적으면)
 *   한 화면만 고치는 날 나머지가 옛말이 된다(D-212).
 */
export function isNotFound(status: number | undefined): boolean {
  return failureKind(status) === 'notfound';
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

/* ════════════════════════════════════════════════════════════════════════
 * U1 — 큐 카드 키 1(판정+접수) · 오탐 사유 3택 (WO-01 §5 · AC-2 · 턴 Q)
 * ════════════════════════════════════════════════════════════════════════
 *
 * ★ 끝에 붙인다. 이번 턴에도 이 파일을 여러 차선이 함께 읽는다 — 위쪽에 줄을
 *   끼우면 충돌하고, 충돌한 사전 파일은 화면 전체를 못 세운다(위 다른 절과 같은
 *   규약 · `docs/design/GX-COPY_v1.md` §5 에도 같은 절을 올린다).
 *
 * ★ **서버에 오탐 사유의 정해진 목록(enum)이 아직 없다** — `/review` 라우트의
 *   `reason` 은 여전히 자유 텍스트다(`kernels/k1_event/services.py::review_event`).
 *   그래서 아래 세 문장은 **화면이 미리 채우는 값**일 뿐 새 계약이 아니다. 서버가
 *   정해진 목록을 갖게 되면(K6 오탐 학습 어휘) 그 값으로 이 목록을 갈아 끼운다.
 */
export interface FalsePositiveReasonOption {
  code: string;
  label: string;
}

export const FALSE_POSITIVE_REASONS: FalsePositiveReasonOption[] = [
  { code: 'not_person', label: '사람이 아님(동물·사물)' },
  { code: 'camera_glitch', label: '카메라 오작동·화면 이상' },
  { code: 'other', label: '기타' },
];

/** 큐 카드 키 1 — 판정(확인)+접수를 한 번에 묶는 단추의 말. */
export const REVIEW_AND_ACK_LABEL = '실제로 확인 · 접수';

/** 오탐 선택 단추의 말. */
export const REJECT_LABEL = '오탐으로 판정';

/* ════════════════════════════════════════════════════════════════════════
 * 사전 v1.1 — UX-31′ 네 문장 · GX-COPY §5 등재 (2026-09-16 턴 S · 차선 F)
 * ════════════════════════════════════════════════════════════════════════
 *
 * 정본은 여전히 `docs/design/GX-COPY_v1.md` 이고, 이 절은 그 사전의 **§5(아직 코드에
 * 없던 낱말)를 코드 쪽으로 옮긴 것**이다. PRD v1.1 §5 가 「사전 v1.1 = v1 + 역할 홈 ·
 * 온보딩 카드 · 빈 상태 문장 4종」이라고 적은 그 v1.1 이다.
 *
 * 규칙은 그대로다 — **사전에 없는 문구는 만들지 않는다.** 없으면 정본 문서에 먼저 한 줄을
 * 적고 여기에 올린 뒤 화면이 그것을 부른다.
 *
 * ⚠ **여기 옮겨 적지 않는 것**(두 벌이 되면 반드시 어긋난다 · D-369):
 *     · 로그인이 실패하는 다섯 갈래 · 제출 중 · 이중 제출  → `features/login/loginCopy.ts`
 *     · 모바일 지도 링크의 말                              → `features/mobile/pages/MobileEventDetail.tsx`
 *     · 발송 결과 세 문장(중복 억제 · 일부 실패 · 정상)     → `features/dsm/deliveryOutcome.tsx`
 *   그 셋은 이미 제 자리에 산다. 이 파일은 그 줄을 **복사하지 않고 자리만 가리킨다.**
 */

/** 이 사전의 판. 화면이 아니라 사람(우리)이 읽는 값이다 — 본문에 그리지 않는다. */
export const GX_COPY_VERSION = 'v1.1';

/**
 * UX-31′ — **오류 화면은 네 문장으로 말한다.**
 *
 *   ① 무슨 일이 일어났나 (`what`)
 *   ② 왜 그런가          (`why`)
 *   ③ 지금 무엇을 하면 되나 (`next`)
 *   ④ 그리고 **누를 것**   (`retryLabel` — 누르면 실제로 요청이 한 번 더 나간다)
 *
 * ★ `retryLabel` 이 `null` 인 갈래가 하나 있다 — **없는 것**(404). 다시 시도해도 영영
 *   없으므로 그 화면에는 단추를 그리지 않는다. 누를 것이 없는 단추는 거짓말이다.
 */
export interface FailureSpeech {
  what: string;
  why: string;
  next: string;
  /** `null` 이면 **단추를 그리지 않는다.** */
  retryLabel: string | null;
}

/** 다시 부르는 단추의 말. 화면마다 다른 말을 쓰지 않는다. */
export const RETRY_LABEL = '다시 시도';

/** 마우스가 없는 화면(월 모드·큐)이 같은 일을 키로 부르는 자리. */
export const RETRY_KEY_HINT = '단축키 R — 다시 시도';

/** ② 왜 그런가. **서버 안의 사정은 적지 않는다** — 사용자의 말이 아니다. */
const FAILURE_WHY: Record<FailureKind, string> = {
  network: '서버에 연결하지 못했습니다.',
  timeout: '응답이 제때 오지 않았습니다.',
  server: '서버가 이 요청을 처리하지 못했습니다.',
  forbidden: '이 계정에는 이 항목을 볼 권한이 없습니다.',
  notfound: '지워졌거나 처음부터 없던 번호입니다.',
  unknown: '요청이 받아들여지지 않았습니다.',
};

/** ③ 지금 무엇을 하면 되나. **할 수 있는 일을 적는다** — 위로가 아니라 다음 동작이다. */
const FAILURE_NEXT: Record<FailureKind, string> = {
  network: '연결을 확인한 뒤 다시 시도해 주십시오.',
  timeout: '잠시 뒤 다시 시도해 주십시오.',
  server: '잠시 뒤 다시 시도해 주십시오. 그래도 같으면 관리자에게 알려 주십시오.',
  forbidden: '다시 로그인하면 보일 수 있습니다. 그래도 안 보이면 관리자에게 역할을 요청하십시오.',
  notfound: '주소를 확인하고 목록으로 돌아가십시오.',
  unknown: '잠시 뒤 다시 시도해 주십시오.',
};

/**
 * 상태 코드 하나를 **네 문장**으로. 순수 함수다 — 시험이 이것만으로 전부 잰다.
 *
 * @param whatOverride 무엇이 없는지·무엇을 못 했는지 **부르는 쪽만 안다.** 주면 ①을 갈음한다
 *                     (사건 상세라면 「없는 사건입니다.」 · 쓰기 자리라면 「저장하지 못했습니다.」).
 */
export function failureSpeech(
  status: number | undefined,
  whatOverride?: string,
): FailureSpeech {
  const kind = failureKind(status);
  const what =
    whatOverride ??
    (kind === 'forbidden'
      ? FORBIDDEN_TITLE
      : kind === 'notfound'
        ? NOT_FOUND_TITLE
        : FAILURE_TITLE);
  return {
    what,
    why: FAILURE_WHY[kind],
    next: FAILURE_NEXT[kind],
    // ★ 없는 것에는 단추를 주지 않는다. 그 하나가 이 함수의 판정이다.
    retryLabel: kind === 'notfound' ? null : RETRY_LABEL,
  };
}

/**
 * 빈 상태의 네 문장. **오류와 같은 그림이 되면 안 된다** — 빈 것은 요청이 성공한 것이다.
 * 그래서 「다시 시도」가 없다(다시 불러도 0건이다).
 */
export function emptySpeech(nounLine: string): FailureSpeech {
  return {
    what: nounLine,
    why: '요청은 성공했고 보여 줄 것이 0건입니다.',
    next: '새 자료가 생기면 이 자리에 나타납니다.',
    retryLabel: null,
  };
}

/* ── GX-COPY §5 · 처음 시작하기 · 현장 회신 ───────────────────────────── */
export const ONBOARDING_COPY = {
  firstTime: '처음이세요?',
  start: '처음 시작하기',
  progress: (done: number, total: number, percent: number) =>
    `${percent}% · ${done}/${total} 끝났습니다. 하면 저절로 닫힙니다.`,
  blockedLine: (n: number) => `아직 세지 못하는 카드 ${n}장`,
  expand: '펼치기',
  collapse: '접기',
} as const;

export const FIELD_COPY = {
  replyTitle: '현장 회신 — 본 것을 한 줄로',
  replySend: '회신 보내기',
} as const;

/* ── GX-COPY §5 · 인계 (역할 홈의 카드가 부르는 말) ───────────────────── */
export const HANDOVER_COPY = {
  title: '인계 메모',
  read: '인계 읽기',
  compose: '인계 메모 쓰기',
  empty: '아직 인계 메모가 없습니다.',
  draftTitle: '교대 마무리 초안',
  lead: '이전 근무자가 남긴 한 줄입니다.',
} as const;

/* ── GX-COPY §5 · 월 모드 · 큐 · 카메라 격자 ──────────────────────────── */
export const WALL_COPY = {
  title: '월 모드',
  autoRefresh: '자동 갱신 중',
  lastRefresh: (line: string) => `마지막 갱신 ${line}`,
  map: '지도',
  mapEmpty: '지도에 표시할 위치가 없습니다.',
  mapBroken: '지도에 표시할 위치를 불러오지 못했습니다.',
  located: (known: number, total: number) =>
    `위치를 아는 카드 ${known}장 · 전체 ${total}장`,
  others: (n: number) => `그 밖 ${n}장`,
  loading: '불러오는 중입니다.',
  stale: '불러오지 못했습니다. 아래는 마지막으로 받은 내용입니다.',
  queueBroken: '지금 처리할 것을 불러오지 못했습니다.',
  calm: '지금 열려 있는 이벤트가 없습니다 — 평온합니다.',
  openedByToken: '월 표시 토큰으로 열림',
  openedBySession: '로그인 세션으로 열림',
  tokenGone: '월 표시 토큰이 만료되었거나 회수되었습니다. 관리자에게 새 토큰을 받으십시오.',
} as const;

export const QUEUE_COPY = {
  shortcuts: '단축키',
  shortcutsHelp: '단축키 안내',
  soundOn: '소리 켜기',
  soundOff: '소리 끄기',
  muted: '소리가 꺼져 있습니다',
  digitsNote: '숫자 키는 가장 급한 하나에만 듭니다.',
  soundNote: '소리는 심각에서만 납니다. 묶인 카드는 한 번만 납니다.',
  down: '아래로',
  up: '위로',
} as const;

export const CAMERA_COPY = {
  grid: '카메라 격자',
  autoRotate: '자동 순회',
  stopRotate: '순회 멈춤',
  noAnswer: '응답 없음',
  lastSeen: (line: string) => `마지막 응답 ${line}`,
  fillAddress: '카메라 주소 채우기',
  previewTable: '표 먼저 보기',
  fill: '채우기',
  broken: '카메라 상태를 불러오지 못했습니다.',
} as const;

/* ── GX-COPY §5 · 보관 기간 · 청구 · 계량 · 파기 ──────────────────────── */
export const RETENTION_COPY = {
  title: '영상 보관 기간',
  days: (n: number) => `${n}일`,
  autoDelete: '보관 기간이 지난 영상은 자동으로 지워집니다',
  autoAnalysis: '자동 분석 안내',
  autoAnalysisBody: '이 알림은 자동 분석 결과이며, 관제요원이 최종 확인합니다.',
} as const;

export const PRIVACY_COPY = {
  title: '열람·삭제 청구',
  submit: '청구 접수',
  receiptNo: '접수 번호',
  masked: '마스킹본 보기',
  noOriginal: '원본 영상은 제공되지 않습니다',
  replies: '회신 기록',
} as const;

export const METERING_COPY = {
  title: '이번 달 사용량',
  download: '표 내려받기',
} as const;

export const PURGE_COPY = {
  title: '보관 기간이 지난 영상 지우기',
  dryRun: '먼저 표로 보기',
  irreversible: '지운 뒤에는 되돌릴 수 없습니다',
  history: '지운 기록',
} as const;

/* ── GX-COPY §5 · 보존·백업 선언 (관리자 자리) ────────────────────────── */
export const BACKUP_COPY = {
  title: '보존·백업 설정',
  headline: '보존·백업 설정 — 선언하지 않으면 돌지 않습니다',
  undeclared: '미선언',
  waitingSignal: '서버 신호 대기',
  waitingNote: '이 값을 읽는 자리가 아직 없습니다. 선언되지 않았다는 뜻이 아닙니다.',
  notRunning: '돌지 않습니다',
  runsDaily: '매일 자동으로 지웁니다',
  whoDeclared: '누가 정했나',
} as const;

/* ── GX-COPY §5 · 세션 · 인수 화면 · 버전 ─────────────────────────────── */
export const SESSION_COPY = {
  ended: '다른 기기에서 로그인되었습니다',
  overLimit:
    '이 계정으로 함께 쓸 수 있는 기기 수를 넘었습니다. 가장 오래 켜 둔 화면을 닫았습니다.',
} as const;

export const INHERITED_COPY = {
  header: '관리자 전용 화면입니다. 아래 표기는 아직 영문입니다.',
  countUnknown: (noun: string) => `${noun} 수를 세지 못했습니다.`,
  countUnknownWhy: '아래 표가 비어 있어도 그것이 「없다」는 뜻은 아닙니다.',
} as const;

export const VERSION_COPY = {
  version: (short: string) => `버전 ${short}`,
  unknown: '버전 알 수 없음',
} as const;

/** 제품이 무엇을 하는 물건인가 — **세 자리에 같은 글자**로 선다. */
export const PRODUCT_LINE = 'GuardianX는 대응 시간을 잽니다.';

/** 목록 위 「보기」 넷. 「프리셋」은 우리 말이다. */
export const VIEW_COPY = {
  unhandled: '미처리 보기',
  last12h: '지난 12시간 보기',
  mine: '내 담당 보기',
  system: '시스템 보기',
} as const;

/* ════════════════════════════════════════════════════════════════════════
 * U1 — 큐 「지원 요청」 배지 · 종결 확인 카드 (턴 S)
 * ════════════════════════════════════════════════════════════════════════
 *
 * ★ 끝에 붙인다(위 절과 같은 관례). 사전 정본에도 같은 절을 올릴 것을 조율자에게
 *   청한다 — 이 파일은 사전의 코드 쪽 반쪽이다.
 *
 * ★ **「데이터 없음」과 「배선 대기」를 가르는 말이 여기 있다.** 현장 회신은 오는데
 *   그 회신에 종류 표시가 아직 안 붙는 상태가 실재한다. 그때 화면이 「없습니다」라고
 *   적으면 그것은 거짓이다 — 없는 것이 아니라 **우리가 아직 못 읽는 것**이다.
 */

/** 큐 카드 배지 — 현장이 혼자 못 한다고 했다. */
export const SUPPORT_BADGE_LABEL = '지원 요청';

/** 종결 확인 카드의 제목. 「무엇을 하는 칸인가」를 제목이 말한다. */
export const CLOSE_CONFIRM_TITLE = '종결 확인 — 현장이 조치를 마쳤다고 알린 사건';

/** 아직 아무 회신도 종류를 달고 오지 않았을 때의 표시. **없음이 아니다.** */
export const WIRING_WAITING_LABEL = '배선 대기';

/**
 * 그 표시 아래 한 줄. **왜 비었는지**를 적는다 — 이유 없는 빈 칸은 고장으로 읽힌다.
 */
export const WIRING_WAITING_NOTE =
  '현장 회신에 「지원 요청」·「조치 완료」 표시가 아직 붙지 않았습니다. '
  + '아래 한 줄은 이 칸이 어떻게 보일지 세워 둔 검수용 예시이고, 실제 회신이 아닙니다.';

/** 회신은 오는데 분류가 0건일 때 큐 머리에 적는 한 줄. */
export const SUPPORT_WAITING_NOTE =
  '지원 요청 표시는 현장 회신이 그 표시를 달고 올 때 이 자리에 뜹니다.';

/** 종결 확인 카드가 비었을 때 — 이쪽은 **진짜 없음**이다. */
export const CLOSE_CONFIRM_EMPTY =
  '조치를 마쳤다고 알려 온 사건이 없습니다.';

/**
 * 초점 카드가 아닌 사건은 **여기서 종결하지 않는다.**
 *
 * ★ 갈 수 있는 다음 칸은 서버가 초점 카드에만 준다. 대기 카드에 종결 단추를 그리면
 *   화면이 자기 전이표를 든 것이 되고, 서버가 거절하는 단추가 생긴다.
 */
export const CLOSE_CONFIRM_OPEN_INSTEAD = '이 사건은 상세에서 종결합니다';
