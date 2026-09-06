/**
 * DSM(재난안전 모니터링) 화면이 부르는 면 — F-09 · F-10 (D-371 ①).
 *
 * ★ 응답 판정은 **HTTP 상태 + `success` 필드 둘 다** 본다 (DA-03 §4-4 · D-349 착시 ⑧).
 *   이 저장소의 dj-core 봉투는 권한 거절을 **200 안에 담아** 내보낸다
 *   (`{status_code: 403}`). 봉투만 보면 우리 화면이 「성공」으로 그리고,
 *   그 상태가 곧 「오류율 0%」를 보고하는 대시보드다 — D-358 이 못박은 자리.
 *   그래서 `unwrap()` 이 **본문을 읽는다.**
 *
 * ★ 로딩 타임아웃 10초 — 초과하면 로딩이 아니라 **오류**다 (DA-03 §4-3).
 *   영원한 스피너는 「기다리는 중」으로 보이지만 사용자는 아무것도 모른다.
 */
import API from '@/services/API';

/** 화면이 부르는 자리. 문자열을 화면 코드에 흩지 않는다 — 한 곳에서만 정한다. */
export const dsmEndpoint = {
  dashboardFrame: '/api/dsm/dashboard/frame',
  linkState: '/api/dsm/dashboard/link-state',
  events: '/api/dsm/events',
  /** W1 요약 한 줄 — 오탐 N 의 원천(K6 `false_positive_rate`)을 **부르는 첫 화면**. */
  eventsSummary: '/api/dsm/events/summary',
  eventDetail: (id: number | string) => `/api/dsm/events/${id}`,
  notify: (id: number | string) => `/api/dsm/events/${id}/notify`,
  /** 진위 판정(오탐/실제) — U1 #11 이 누를 자리가 없던 그 문 (D-414). */
  review: (id: number | string) => `/api/dsm/events/${id}/review`,
  /** 대응 진행 한 칸 (D-399). **판정과 다른 축이다** — 버튼도 따로 둔다. */
  response: (id: number | string) => `/api/dsm/events/${id}/response`,
  deliveries: '/api/dsm/deliveries',
  /**
   * ★ P-25 스냅샷 **바이트**. 인증 뒤에 서고 소인이 찍혀 나온다 —
   *   `<img src>` 로 그냥 붙이면 브라우저가 **인증 헤더 없이** 부르고 401 이 온다.
   *   `fetchSnapshotUrl()` 로 받아 objectURL 로 붙인다.
   */
  snapshot: (id: number | string) => `/api/dsm/events/${id}/snapshot`,
  /** UX-13 단일 초점 큐 — 최상단의 **하나**와 5분 창 묶음. */
  eventsQueue: '/api/dsm/events/queue',
  /** UX-14 월간 p50/p95 — 자동 종결을 뺀 분모. */
  responseTimes: '/api/dsm/events/response-times',
  /** UX-14 네 시각 타임라인. */
  timeline: (id: number | string) => `/api/dsm/events/${id}/timeline`,
  /** UX-17 훈련 모드 스위치(GET 상태 · POST 전환). **한 경로 두 메서드**다. */
  drill: '/api/dsm/drill',
  drillReport: '/api/dsm/drill/report',
  /** UX-18 「주소 없는 카메라 N대」 배지. */
  cameraAddressGap: '/api/dsm/cameras/address-gap',
  /** UX-18 벌크 등록. **`dry_run` 기본값이 참**이다 — 표가 먼저다(D-209). */
  cameraImport: '/api/dsm/cameras/import',
  /** M3 현장 회신 — 이동 중인 사람이 한 줄을 돌려주는 자리 (쓰기). */
  fieldReply: (id: number | string) => `/api/dsm/events/${id}/field-reply`,
  /** M3 현장 회신 목록 (읽기). */
  fieldReplies: (id: number | string) => `/api/dsm/events/${id}/field-replies`,
  /**
   * UX-23 카메라 맥박 — 카메라별 생사 + 군집 두절. **읽기 전용**이고
   * 아무것도 만들지 않는다. 판정은 서버 한 곳(`camera_pulse`)이 한다.
   */
  cameraPulse: '/api/dsm/cameras/pulse',
  /**
   * LAW-02a 영상 보관 기간 — 선언된 값과 「그 수대로 지우는가」를 함께 낸다.
   */
  lawRetention: '/api/dsm/law/retention',
  /** LAW-02a 보존기간 집행. **dry_run 기본값이 참**이다 — 표가 먼저다. */
  lawRetentionSweep: '/api/dsm/law/retention/sweep',
  /** LAW-06 다섯 의무 자리표 + 고지 문구. */
  lawAiActDuties: '/api/dsm/law/ai-act/duties',
  /** LAW-07 열람·삭제 청구 목록(GET) · 접수(POST). **한 경로 두 메서드**다. */
  privacyRequests: '/api/dsm/law/privacy-requests',
  privacyRequestDetail: (no: string) => `/api/dsm/law/privacy-requests/${no}`,
  /** ★ 마스킹본. 원본 경로는 이 응답의 어느 칸에도 없다. */
  privacyRequestMasked: (no: string) =>
    `/api/dsm/law/privacy-requests/${no}/masked`,
  privacyRequestReply: (no: string) =>
    `/api/dsm/law/privacy-requests/${no}/reply`,
} as const;

/** DA-03 §4-3 — 로딩이 이보다 길면 그것은 로딩이 아니라 오류다. */
export const LOAD_TIMEOUT_MS = 10_000;

export class DsmApiError extends Error {
  readonly status: number;
  /**
   * 이 문장을 **서버가 썼는가.**
   *
   * ★ [P-78 · 2026-09-06 턴 H] 이 한 칸이 「화면에 그려도 되는 사유」와
   *   「그리면 안 되는 원문」을 가른다. 서버가 준 한국어 사유(「표의 3행에 필요한
   *   값이 없습니다.」)는 사용자의 말이고, axios 가 만든 문장(「Network Error」)은
   *   아니다. 종전에는 둘이 같은 `message` 칸에 담겨 **구별할 방법이 없었다** —
   *   그래서 화면이 둘 다 그렸고, 여섯 화면에서 원문이 사람의 자리에 떴다.
   */
  readonly fromServer: boolean;
  constructor(message: string, status: number, fromServer = false) {
    super(message);
    this.name = 'DsmApiError';
    this.status = status;
    this.fromServer = fromServer;
  }
}

/**
 * 봉투의 사유 한 줄을 **문자열로** 꺼낸다.
 *
 * ⚠ [실측] 이 저장소의 로그인 면은 사유를 `{en, ko, vi, th}` 로 준다. 그 객체를
 *   그대로 `Error` 에 넣으면 화면에 **`[object Object]`** 가 뜬다 — 사유가 통째로
 *   사라진 자리이고, `walk_states` 의 원문 표본 목록에 이름으로 올라 있다.
 */
function pickMessage(value: unknown): string | undefined {
  if (typeof value === 'string') return value.trim() || undefined;
  if (value && typeof value === 'object') {
    const bag = value as Record<string, unknown>;
    for (const key of ['ko', 'en']) {
      const v = bag[key];
      if (typeof v === 'string' && v.trim()) return v.trim();
    }
  }
  return undefined;
}

/**
 * 봉투를 벗긴다. **HTTP 상태와 본문 상태를 둘 다** 본다.
 *
 * 본문에 `status_code` 가 있고 그것이 4xx·5xx 면 **봉투가 200 이어도 오류다.**
 * 없으면 그대로 통과 — 없는 것을 있다고 가정하지 않는다.
 */
function unwrap<T>(res: any): T {
  const httpStatus: number = res?.status ?? 0;
  const body = res?.data ?? res;
  const bodyStatus: number | undefined =
    typeof body?.status_code === 'number' ? body.status_code : undefined;

  // ★ [차선 D · 2026-09-04] 사유가 `detail` 로 오는 자리가 있다.
  //   `message` 만 읽던 동안 404 의 사유가 **화면에 닿지 않았다** — 사용자는
  //   「요청이 실패했습니다 (404)」만 보고, 그것이 「없다」인지 「못 가져왔다」인지 모른다.
  //   둘을 가르는 문장이 서버에 있는데 화면이 안 읽는 것은 D-284 의 조용한 판이다.
  const detail: string | undefined = pickMessage(body?.detail);
  const said: string | undefined = pickMessage(body?.message) ?? detail;

  if (httpStatus >= 400) {
    throw new DsmApiError(
      said ?? `요청이 실패했습니다 (${httpStatus})`,
      httpStatus,
      said !== undefined,
    );
  }
  if (bodyStatus !== undefined && bodyStatus >= 400) {
    throw new DsmApiError(
      said ?? `요청이 거절되었습니다 (${bodyStatus})`,
      bodyStatus,
      said !== undefined,
    );
  }
  // 봉투 안에 `data` 가 있으면 그것이 값이고, 없으면 본문 자체가 값이다.
  return (body?.data ?? body) as T;
}

/** 10초를 넘기면 **오류로 전이한다.** 취소도 함께 건다 — 버려진 요청은 낭비다. */
async function withTimeout<T>(run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), LOAD_TIMEOUT_MS);
  try {
    return await run(ctrl.signal);
  } catch (err: any) {
    if (ctrl.signal.aborted) {
      throw new DsmApiError(
        `응답이 ${LOAD_TIMEOUT_MS / 1000}초 안에 오지 않았습니다.`,
        504,
      );
    }
    if (err instanceof DsmApiError) throw err;
    const status = err?.response?.status ?? 0;
    const said = pickMessage(err?.response?.data?.message);
    // ★ `err.message` 를 **`fromServer` 로 세우지 않는다.** 그 자리가 axios 가
    //   「Network Error」를 넣는 자리다 — 서버가 쓴 문장이 아니다.
    throw new DsmApiError(said ?? err?.message ?? '요청이 실패했습니다.', status,
      said !== undefined);
  } finally {
    clearTimeout(timer);
  }
}

export function dsmGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  return withTimeout(async (signal) =>
    unwrap<T>(await API.get(url, { params, signal })),
  );
}

export function dsmPost<T>(url: string, body?: unknown): Promise<T> {
  return withTimeout(async (signal) =>
    unwrap<T>(await API.post(url, body ?? {}, { signal })),
  );
}

/**
 * 쿼리로 POST 한다 — **본문이 아니라 질의다.**
 *
 * ★ [실측 2026-09-05] 이 저장소의 dsm 라우트들은 인자를 원시 타입으로 받는다
 *   (`def camera_import(self, request, csv_text: str, dry_run: bool = True)`).
 *   django-ninja 규약상 그것은 **질의**이고, 본문으로 보내면 돌아오는 것은
 *   **422 · loc: ["query", …] · "Field required"** 다. 그 422 는 「값이 틀렸다」가
 *   아니라 **「인자가 없다」**이고, 둘을 헷갈리면 한나절이 간다.
 *
 * ★ 이 함수가 생긴 이유: 같은 조립을 화면마다 손으로 짜다가 **두 화면이 빠뜨렸다** —
 *   카메라 일괄 등록과 훈련 모드의 쓰기가 그렇게 422 로 죽어 있었고,
 *   캡처는 제목 글자만 보므로 **화면은 멀쩡히 떠 있었다.** 조립을 한 곳에 둔다.
 */
export function dsmPostQuery<T>(
  url: string,
  query: Record<string, string | number | boolean>,
): Promise<T> {
  const qs = new URLSearchParams(
    Object.entries(query).map(([k, v]) => [k, String(v)]),
  ).toString();
  return dsmPost<T>(`${url}?${qs}`);
}

/**
 * ★ P-25 — **인증 헤더가 실리는 경로로** 스냅샷을 받는다.
 *
 * 왜 `<img src="/api/dsm/events/1/snapshot">` 이면 안 되나: 브라우저의 이미지 요청은
 * 이 앱의 axios 인터셉터를 지나지 않는다. 토큰이 안 실리고, 그러면 **401 이 오고
 * 화면에는 깨진 이미지 아이콘**이 뜬다 — 그 아이콘은 「스냅샷이 없다」와 구별되지
 * 않는다(D-290). 서명 URL 로 여는 길은 **무계정 링크 금지**로 막혀 있다.
 *
 * 그래서 axios 로 받아 objectURL 을 만든다. 부르는 쪽은 **반드시 `revoke` 를 부른다** —
 * 안 부르면 카드가 갱신될 때마다 blob 이 쌓여 관제 화면이 밤새 메모리를 먹는다.
 */
export async function fetchSnapshotUrl(
  eventId: number | string,
): Promise<{ url: string; revoke: () => void }> {
  const res = await API.get(dsmEndpoint.snapshot(eventId), {
    responseType: 'blob',
    // 캐시가 장애를 덮는다(P-19 · UniversalCacheMiddleware 는 적중 본문을 언제나
    // 200 으로 되살린다). 스냅샷은 소인에 **열람 시각**이 찍혀 나오므로 캐시된
    // 바이트는 남의 시각을 보여 준다 — 그것은 소인의 뜻을 지운다.
    headers: { 'X-No-Cache': 'true' },
  });
  const status: number = res?.status ?? 0;
  if (status >= 400) {
    throw new DsmApiError(`스냅샷을 받지 못했습니다 (${status})`, status);
  }
  const url = URL.createObjectURL(res.data as Blob);
  return { url, revoke: () => URL.revokeObjectURL(url) };
}

/**
 * OPS-16 계량 · P-57 파기 — **끝에 상수만 더한다** (2026-09-05 · 차선 E).
 *
 * ★ 왜 `dsmEndpoint` 안이 아니라 여기인가: 이번 턴에 이 파일을 여러 차선이 읽는다.
 *   위쪽 객체 리터럴에 줄을 끼우면 그 줄이 충돌하고, **충돌한 상수 파일은
 *   화면 전체를 못 세운다.** 끝에 붙이는 것은 아무 줄도 안 건드린다.
 *
 * ★ 문자열을 화면 코드에 흩지 않는다 — `dsmEndpoint` 와 같은 규약이다.
 */
export const dsmMeteringEndpoint = {
  /** OPS-16 「이번 달 사용량」 다섯 칸. `month=YYYY-MM` 을 주면 그 달. */
  usage: '/api/dsm/metering',
  /** 최근 몇 달을 한 번에 — 지난 달과 견주는 자리. */
  usageSeries: '/api/dsm/metering/series',
  /**
   * 「표 내려받기」. **CSV 본문이 그대로 온다** — 봉투가 아니다.
   * ⚠ `<a href>` 로 붙이면 브라우저가 **인증 헤더 없이** 부르고 401 이 온다
   *   (`fetchSnapshotUrl` 머리말과 같은 자리). 반드시 이 앱의 axios 로 받는다.
   */
  usageCsv: '/api/dsm/metering/csv',
} as const;

/** P-57 파기 — 「보관 기간이 지난 영상 지우기」. **되돌릴 수 없다.** */
export const dsmPurgeEndpoint = {
  /** 보존 일수를 **선언한** 테넌트만. 여기 없으면 파기 대상이 아니다. */
  tenants: '/api/dsm/law/purge/tenants',
  /** 파기(POST). **`dry_run` 기본값이 참**이다 — 표가 먼저다(D-209). */
  purge: '/api/dsm/law/purge',
  /** 「지운 기록」. 전역 관리자가 아니면 내 테넌트 것만 보인다. */
  history: '/api/dsm/law/purge/history',
} as const;

/**
 * P-67 U5 시스템 설정 — **보존·백업 선언** (2026-09-06 · 차선 C).
 *
 * ★ 끝에 붙인다. 위쪽 객체 리터럴에 줄을 끼우면 같은 턴의 다른 차선과 충돌하고,
 *   충돌한 상수 파일은 화면 전체를 못 세운다 — 위 두 상수 묶음과 같은 규약이다.
 */
export const dsmSystemEndpoint = {
  /**
   * 영상 보관 기간 선언. **이 문은 실재한다** — 선언이 없으면 `declared: false` 와
   * 출처 「미선언」이 온다(P-67 뒤로 코드 기본값이 없다).
   */
  retention: '/api/dsm/law/retention',
  /**
   * 백업 목적지·일정·보존·복구 시험 선언.
   *
   * ⚠ **이 문은 아직 없다.** 서버 쪽 선언은 설정에 서 있으나(개발·스테이징) 그것을
   *   화면에 내주는 자리가 없다. 없는 것을 있는 척하지 않는다 — 화면은 404 를
   *   「미선언」이 아니라 **「백엔드 신호 대기」**로 그린다. 둘은 다른 사실이다:
   *   미선언은 「아무도 안 정했다」이고 신호 대기는 「우리가 못 읽는다」다.
   */
  backupDeclaration: '/api/dsm/ops/backup/declaration',
} as const;

/* ════════════════════════════════════════════════════════════════════════
 * 이중 제출 0 — **멱등 키** (P-78 ③ · 2026-09-06 턴 H)
 * ════════════════════════════════════════════════════════════════════════
 *
 * 무엇이 문제였나 [실측 · 직전 턴 walk_states]
 * -------------------------------------------
 * 로그인에서 빠르게 두 번 누르면 요청이 **2번** 나갔다. 단추에 `loading` 이 걸려
 * 있었는데도 그랬다 — 리액트의 상태는 **다음 그림에서** 반영되고, 사람의 두 번째
 * 클릭은 그 그림보다 빠르다. 즉 **단추 잠금만으로는 못 막는다.**
 *
 * ★ 그래서 잠금을 **요청 자리**에 둔다. 같은 의도(같은 멱등 키)가 이미 날아가
 *   있으면 새 요청을 만들지 않고 **그 약속을 그대로 돌려준다.** 두 번째 클릭은
 *   첫 번째의 결과를 받는다 — 삼킨 것이 아니라 **같은 것을 받은 것**이다.
 *
 * ⚠ **서버 신호 대기.** 이 저장소의 어느 라우트도 `Idempotency-Key` 를 아직 읽지
 *   않는다 [실측 · 저장소 전수 검색 0건]. 그러므로 이 헤더는 지금 **서버에서 아무
 *   일도 하지 않는다.** 그래도 싣는 이유는 두 가지다:
 *     ① 브라우저 쪽 중복은 이 키가 **실제로** 막는다(위 약속 재사용).
 *     ② 서버가 이 규약을 받는 날, 화면을 다시 고칠 필요가 없다.
 *   없는 것을 있는 것처럼 적지 않는다 — 서버 면이 설 때까지 이 문단이 그 사실이다.
 *
 * ⚠⚠ **머리글자는 CORS 허용 목록에 이름이 있어야 브라우저가 보낸다.**
 *   월 표시 토큰이 정확히 이 자리에서 한 턴을 버렸다(`x-gx-wall-token` 이 목록에
 *   없어 브라우저가 그 문을 한 번도 안 불렀다). 그래서 이 이름도 함께 올렸다:
 *   `config/settings.py` 의 `CORS_ALLOW_HEADERS`. 목록에 없으면 증상은 조용하다 —
 *   **요청 자체가 안 나간다.**
 */

/** 멱등 키가 실리는 자리. 이름을 두 벌로 적지 않는다. */
export const IDEMPOTENCY_HEADER = 'Idempotency-Key';

/**
 * 키 하나에 약속 하나. **끝난 뒤에도 잠시 들고 있는다.**
 *
 * ⚠⚠ [실측 2026-09-06 · 턴 H] 처음에는 끝나는 즉시 지웠다. 그런데 시험 도구가
 *   두 번 누르는 간격보다 **첫 응답이 더 빨랐고**(가짜 응답은 즉시 온다),
 *   그래서 두 번째 누름이 「이미 끝난 의도」를 새 요청으로 만들었다 — 요청 2건.
 *   사람의 손도 같다: 응답이 20ms 에 오는 자리에서 더블클릭은 언제나 두 번 나간다.
 *   **날아가는 동안만 막는 것은 이중 제출을 못 막는다.** 잠시 더 들고 있어야 한다.
 *
 * ★ 그 「잠시」가 곧 멱등 창이다. 창 안에서 같은 키는 **같은 답**을 받는다 —
 *   서버가 이 규약을 받는 날 서버가 할 일과 정확히 같은 일이다.
 */
const IDEMPOTENT_WINDOW_MS = 2_000;

interface Entry {
  promise: Promise<unknown>;
  settledAt: number | null;
}

const entries = new Map<string, Entry>();

function live(key: string): Promise<unknown> | null {
  const e = entries.get(key);
  if (!e) return null;
  if (e.settledAt !== null && Date.now() - e.settledAt > IDEMPOTENT_WINDOW_MS) {
    entries.delete(key);
    return null;
  }
  return e.promise;
}

function remember<T>(key: string, promise: Promise<T>): Promise<T> {
  const entry: Entry = { promise, settledAt: null };
  entries.set(key, entry);
  promise
    .catch(() => undefined)
    .finally(() => {
      entry.settledAt = Date.now();
    });
  return promise;
}

/**
 * 새 멱등 키 한 장. **의도가 시작될 때 한 번** 만들고, 재시도에는 같은 것을 쓴다.
 *
 * `crypto.randomUUID` 가 없는 환경(오래된 브라우저·비보안 문맥)에서도 돌아야 한다 —
 * 없으면 화면 전체가 그 자리에서 죽고, 그것은 이 절이 막으려던 것보다 큰 고장이다.
 */
export function newIdempotencyKey(): string {
  try {
    const c = globalThis.crypto as Crypto | undefined;
    if (c && typeof c.randomUUID === 'function') return c.randomUUID();
  } catch {
    /* 아래로 내려간다 */
  }
  return `gx-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * 질의로 POST 하되 **같은 키가 날아가 있으면 새로 안 보낸다.**
 *
 * 돌려주는 값은 언제나 그 의도의 결과다 — 두 번째 누름도 **성공을 본다.**
 * 「눌렀는데 아무 일도 안 일어났다」로 보이지 않게 하는 것이 이 규약의 절반이다.
 */
export function dsmPostQueryOnce<T>(
  url: string,
  query: Record<string, string | number | boolean>,
  idempotencyKey: string,
): Promise<T> {
  const existing = live(idempotencyKey);
  if (existing) return existing as Promise<T>;

  const qs = new URLSearchParams(
    Object.entries(query).map(([k, v]) => [k, String(v)]),
  ).toString();

  return remember(
    idempotencyKey,
    withTimeout<T>(async (signal) =>
      unwrap<T>(
        await API.post(`${url}?${qs}`, {}, {
          signal,
          headers: { [IDEMPOTENCY_HEADER]: idempotencyKey },
        }),
      ),
    ),
  );
}

/** 본문으로 POST 하는 자리의 같은 규약(현장 회신 · 알림 발송). */
export function dsmPostOnce<T>(
  url: string,
  body: unknown,
  idempotencyKey: string,
): Promise<T> {
  const existing = live(idempotencyKey);
  if (existing) return existing as Promise<T>;

  return remember(
    idempotencyKey,
    withTimeout<T>(async (signal) =>
      unwrap<T>(
        await API.post(url, body ?? {}, {
          signal,
          headers: { [IDEMPOTENCY_HEADER]: idempotencyKey },
        }),
      ),
    ),
  );
}

/** 이 키가 아직 살아 있는가(날아가는 중이거나 멱등 창 안이거나). */
export function isInFlight(idempotencyKey: string): boolean {
  return live(idempotencyKey) !== null;
}

/**
 * 같은 **의도**에는 같은 키를 준다 — 두 번 눌린 것과 다시 눌린 것을 가른다.
 *
 *   두 번 눌렸다 = 앞의 요청이 **아직 날아가는 중** → 같은 키 → 요청 하나
 *   다시 눌렀다  = 앞의 요청이 **끝났다**(실패했거나 사람이 또 하고 싶다) → 새 키
 *
 * ★ 이 구별이 이 함수의 전부다. 키를 언제나 새로 만들면 두 번 눌림이 안 막히고,
 *   키를 영원히 고정하면 **실패한 뒤 다시 시도할 수 없다.** 둘 다 결함이다.
 */
const intentKeys = new Map<string, string>();

export function intentKey(intent: string): string {
  const live = intentKeys.get(intent);
  if (live && isInFlight(live)) return live;
  const fresh = newIdempotencyKey();
  intentKeys.set(intent, fresh);
  return fresh;
}
