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

import { unwrap as adapterUnwrap } from './adapter';

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
  /**
   * UX-35 요원별 처리 현황 (차선 U24 · 턴 R). `apps/dsm/api_u24.py::stats_by_reviewer` —
   * 60초 캐시가 허용된 집계다(WO-01 §5 · 시계·건강 보드가 아니다).
   */
  statsByReviewer: '/api/dsm/stats/by-reviewer',
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
 * 봉투를 벗긴다. **해석은 `./adapter.ts::unwrap()` 한 곳이 한다** (P-129 · ADP-01 · 턴 Q).
 *
 * 여기서 하는 일은 판정 결과를 **던지는 것**뿐이다 — 이 파일의 부르는 쪽 전부가
 * `DsmApiError` 를 받도록 짜여 있고, 그 계약은 바꾸지 않는다.
 *
 * ★ [P-129 · 턴 Q] 종전 이 함수가 어댑터로 옮기며 **고친 것 둘**:
 *   ① `res?.status` 를 HTTP 상태로 읽었다 — 인터셉터가 **본문**을 주므로(아래 P-121)
 *      그 자리는 HTTP 상태가 아니라 **본문의 `status` 칸**이다(사건 상태 문자열 등).
 *      숫자 `status` 를 싣는 본문이 오면 거짓 실패가 났다. 이제 상태는 인터셉터가
 *      해소했다는 사실(2xx)과 거절 갈래의 `err.response.status` 로만 읽는다.
 *   ② `body?.data ?? body` — **맨몸 본문에 `data` 칸이 있으면 안쪽만** 돌려줬다.
 *      봉투의 `data` 와 도메인의 `data` 를 가르지 못한 것이다. 어댑터는 `success` 불리언이
 *      있을 때만 봉투로 읽는다. [실측 · grep] 지금 `/api/dsm/**` 응답에 맨몸 `data` 칸은 0.
 *   그리고 봉투의 `success:false` 는 상태가 200 이어도 **실패다**(DA-03 §0-1 — 둘 다 본다).
 *
 * ★ [차선 D · 2026-09-04] 사유가 `detail` 로 오는 자리가 있다 — 어댑터가 `message` 다음에
 *   `detail` 을 읽는다. 둘을 가르는 문장이 서버에 있는데 화면이 안 읽는 것은 D-284 의 조용한 판이다.
 */
function unwrap<T>(res: unknown): T {
  const r = adapterUnwrap<T>(res);
  if (!r.ok) {
    const status = r.status ?? 0;
    throw new DsmApiError(
      r.message ??
        (status > 0 ? `요청이 거절되었습니다 (${status})` : '응답을 알아보지 못했습니다.'),
      status,
      r.message !== null,
    );
  }
  return r.data as T;
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
    // ★ [P-129 · 턴 Q] 거절 갈래도 **어댑터로 읽는다.** 인터셉터는 4xx·5xx 를 여기로 보내므로
    //   ninja `HttpError` 의 사유(`{detail: "그런 이벤트가 없습니다."}`)는 이 자리에만 온다.
    //   종전에는 `.message` 만 읽어 그 문장이 버려지고 axios 의 영문 문장이 대신 떴다.
    const said =
      adapterUnwrap(err?.response?.data, status || null).message ?? undefined;
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
export interface SnapshotBytes {
  url: string;
  revoke: () => void;
  /** 실제로 받은 바이트 수. **증거의 단위**다 — 0 이면 그림이 아니다. */
  bytes: number;
  /** 서버가 뭐라고 부르는 바이트인가 (`image/jpeg`). */
  contentType: string;
}

/**
 * 봉투를 벗은 응답에서 **바이트를 찾는다.**
 *
 * ★★ [P-121 · 2026-09-10 턴 O · 실측] **여기가 사진이 죽던 자리다.**
 *
 *   `createApiClient` 가 다는 응답 인터셉터는 (rj-core dist 실측)
 *
 *       interceptors.response.use((i) => { …; return i.data; }, …)
 *
 *   즉 `API.get()` 이 돌려주는 것은 **AxiosResponse 가 아니라 본문**이다.
 *   `responseType:'blob'` 이면 그 본문이 **Blob 자체**다. 그런데 이 함수는
 *   `res.data` 를 읽고 있었고, Blob 에 `.data` 는 없다 —
 *
 *       URL.createObjectURL(undefined) → TypeError
 *
 *   그 TypeError 는 async 함수 안에서 나므로 **콘솔에 뜨지 않는다.** 부르는 쪽의
 *   `.catch` 가 삼키고 화면에는 「사진을 불러오지 못했습니다」가 뜬다 — 서버는
 *   **200 으로 37KB 를 보냈는데도**. [실측: XHR 200 · 37,472 bytes · 그려진 픽셀 0]
 *
 *   `dsmGet` 이 멀쩡했던 이유는 `unwrap()` 이 `res?.data ?? res` 로 **두 모양을
 *   다 받기** 때문이다. 그 관용이 여기에만 없었다.
 *
 *   ⚠ 그래서 이 함수는 **모양을 가정하지 않는다.** Blob 이면 Blob, 봉투면 봉투 안.
 *     인터셉터가 언젠가 원래 모양으로 돌아와도 이 함수는 그대로 산다.
 */
function pickBlob(res: unknown): Blob | undefined {
  if (typeof Blob !== 'undefined' && res instanceof Blob) return res;
  const inner = (res as { data?: unknown } | null | undefined)?.data;
  if (typeof Blob !== 'undefined' && inner instanceof Blob) return inner;
  return undefined;
}

/** 오류 본문이 Blob 으로 오는 자리(`responseType:'blob'`)에서 **사유 한 줄**을 꺼낸다. */
async function reasonFromBlob(body: unknown): Promise<string | undefined> {
  const blob = pickBlob(body);
  if (!blob) return pickMessage((body as { detail?: unknown })?.detail)
    ?? pickMessage((body as { message?: unknown })?.message);
  try {
    const text = await blob.text();
    const parsed = JSON.parse(text);
    return pickMessage(parsed?.message) ?? pickMessage(parsed?.detail);
  } catch {
    return undefined;
  }
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
 *
 * ★ [P-121] **상태를 잃지 않는다.** 인터셉터가 본문만 돌려주므로 성공 갈래에는
 *   HTTP 상태가 없다 — 그래서 실패는 **거절 갈래에서** 읽는다(`err.response.status`).
 *   종전에는 그 상태가 어디에도 없어 저장소 장애(503)가 「사진을 불러오지 못했습니다」로
 *   뭉개졌다. 503 과 4xx 는 **다른 사실**이고 화면이 다른 문장을 쓴다(UX-10).
 */
export async function fetchSnapshotUrl(
  eventId: number | string,
): Promise<SnapshotBytes> {
  let res: unknown;
  try {
    res = await API.get(dsmEndpoint.snapshot(eventId), {
      responseType: 'blob',
      // 캐시가 장애를 덮는다(P-19 · UniversalCacheMiddleware 는 적중 본문을 언제나
      // 200 으로 되살린다). 스냅샷은 소인에 **열람 시각**이 찍혀 나오므로 캐시된
      // 바이트는 남의 시각을 보여 준다 — 그것은 소인의 뜻을 지운다.
      headers: { 'X-No-Cache': 'true' },
    });
  } catch (err: unknown) {
    const e = err as { response?: { status?: number; data?: unknown } ; message?: string };
    const status = e?.response?.status ?? 0;
    const said = await reasonFromBlob(e?.response?.data);
    // ★ 상태 0 은 **HTTP 대답이 아예 없었다**는 뜻이다(끊김·취소). 4xx/5xx 와
    //   같은 문장으로 적으면 「서버가 거절했다」는 거짓이 된다.
    throw new DsmApiError(
      said ?? (status > 0
        ? `사진을 받지 못했습니다 (${status})`
        : '사진을 받는 중에 연결이 끊겼습니다.'),
      status,
      said !== undefined,
    );
  }

  const blob = pickBlob(res);
  if (!blob) {
    // 여기 오면 **응답 모양이 바뀐 것**이다. 조용히 빈 그림을 그리지 않는다.
    throw new DsmApiError('사진 바이트를 못 알아봤습니다.', 0);
  }
  if (blob.size === 0) {
    throw new DsmApiError('사진이 0바이트로 왔습니다.', 0);
  }
  const url = URL.createObjectURL(blob);
  return {
    url,
    revoke: () => URL.revokeObjectURL(url),
    bytes: blob.size,
    contentType: blob.type || '',
  };
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
 * ★ **서버가 이 키를 읽는다** [실측 2026-09-06 · 턴 I · 차선 C]. 턴 H 에는 이 자리에
 *   「서버 신호 대기 — 어느 라우트도 이 이름을 읽지 않는다」라고 적혀 있었고 그것이
 *   참이었다. 이제 아니다: `backend/common/idempotency.py` 의 `@idempotent` 가
 *   **판정 · 접수 · 회신 · 발송** 네 문에 붙어 있다. 창(10분) 안의 같은
 *   (사람 · 문 · 키) 는 **손을 대지 않고 그때 준 답을 그대로 받는다** — 새 자원이
 *   생기지 않는다. 같은 키가 날아가는 중이면 409 다.
 *   ⚠ 서버 쪽 창은 **Redis 캐시**다 — 영구 저장이 아니다. 캐시가 비면 창도 빈다.
 *   그래서 화면 쪽 잠금(아래 2초 창)을 **없애지 않는다.** 둘은 다른 것을 막는다:
 *     ① 화면 쪽 — 한 브라우저 안의 두 번 누름 (요청이 **아예 안 나간다**)
 *     ② 서버 쪽 — 두 탭 · 새로고침 뒤 재시도 · 모바일과 자리 화면 (요청은 나가되
 *        **자원이 안 는다**)
 *
 * ⚠⚠ **머리글자는 CORS 허용 목록에 이름이 있어야 브라우저가 보낸다.**
 *   월 표시 토큰이 정확히 이 자리에서 한 턴을 버렸다(`x-gx-wall-token` 이 목록에
 *   없어 브라우저가 그 문을 한 번도 안 불렀다). 그래서 이 이름도 함께 올렸다:
 *   `config/settings.py` 의 `CORS_ALLOW_HEADERS`. 목록에 없으면 증상은 조용하다 —
 *   **요청 자체가 안 나간다.**
 */

/**
 * P-147 역할 홈 · UX-46 온보딩 진행률 — **끝에 상수만 더한다** (턴 R · 차선 F).
 *
 * ★ 위쪽 객체 리터럴에 줄을 끼우지 않는 이유는 앞의 세 묶음과 같다 — 같은 턴에 여러
 *   차선이 이 파일을 읽고, 충돌한 상수 파일은 화면 전체를 못 세운다.
 *
 * ★ **홈이 부르는 문은 거의 다 이미 있다.** 띠의 세 수는 `dsmEndpoint.eventsSummary` 가
 *   내고, 카메라 건강은 `cameraPulse`·`cameraAddressGap` 이 낸다. 같은 수를 내는 문을
 *   하나 더 열지 않는다 — 두 문이 갈리면 홈과 목록이 다른 수를 말한다.
 */
export const dsmHomeEndpoint = {
  /** UX-46 「처음 시작하기」 카드와 진행률. **닫는 문(POST)은 없다** — 서버 기록이 닫는다. */
  onboardingProgress: '/api/dsm/onboarding/progress',
  /** UX-39 기간 집계. 합계는 같은 기간의 목록 수와 같다(서버가 같은 함수를 부른다). */
  statsSummary: '/api/dsm/stats/summary',
} as const;

/*
 * ⚠ 「요원별 처리 현황」의 경로는 **여기 적지 않는다.** 같은 턴에 차선 U24 가
 *   `dsmEndpoint.statsByReviewer` 로 이미 올렸다 — 같은 주소를 두 상수로 두면 한쪽만
 *   고쳐지는 날 화면이 갈린다(D-212). 홈은 그 상수를 그대로 부른다.
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
 * S-14 「사람·역할」· P-145 웹훅 서명키 — **차선 U56 · 턴 R**.
 *
 * ★ 끝에 붙인다. 위쪽 `dsmEndpoint` 리터럴에 줄을 끼우면 같은 턴의 다른 차선과
 *   충돌하고, 충돌한 상수 파일은 화면 전체를 못 세운다 — 위 세 상수 묶음과 같은 규약.
 *
 * ⚠ 경로가 `/settings/people` 이 아니라 `/settings/people/create` 인 이유:
 *   `/settings/people`(한 조각)은 `api.py` 의 `GET /settings/{domain}` 에 삼켜져
 *   POST 가 405 를 낸다(라우트 삼킴 · `api_u56.py` 머리말에 실측을 남겼다).
 */
export const dsmU56Endpoint = {
  /** UX-42 #1·#2 — 계정 생성(+역할). */
  peopleCreate: '/api/dsm/settings/people/create',
  /** UX-42 #3 — 계정 비활성화. **행을 지우지 않는다.** */
  peopleDeactivate: (userId: number | string) =>
    `/api/dsm/settings/people/${userId}/deactivate`,
  /**
   * P-145 — 서명키를 **서버가 만들어** 구독에 물린다. 값은 **응답에 한 번만** 있다 —
   * 이 화면은 그 값을 옮겨 적을 자리(복사 버튼)만 주고, 어디에도 다시 저장하지 않는다.
   */
  webhookSubscriptionIssue: '/api/dsm/settings/webhook-subscriptions/issue',
  /** 구독 목록 — 이름(`signing_key_ref`)만 있고 값은 없다. 기존 F-05 문(`api.py`) 그대로. */
  webhookSubscriptions: '/api/dsm/webhook-subscriptions',
} as const;

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

/**
 * M3 사진 올리기 — **본문이 파일이다** (2026-09-16 · 턴 R · 차선 U3).
 *
 * ★ 끝에 붙인다 — 위 규약과 같다(`dsmMeteringEndpoint` 머리말). 이 파일을 여러
 *   차선이 읽는 턴에 위쪽 리터럴이나 함수 사이에 줄을 끼우면 충돌한다.
 *
 * `dsmPost` 는 언제나 JSON 본문을 보낸다. 사진은 `multipart/form-data` 로 가야
 * 서버(`ninja.File` · `apps/dsm/api_u3.py::upload_field_photo`)가 읽는다 —
 * axios 는 `FormData` 를 주면 boundary 를 스스로 채운다. **`Content-Type` 을
 * 손으로 적지 않는다** — 적으면 boundary 가 빠져 서버가 본문을 못 연다.
 */
export function dsmPostForm<T>(url: string, form: FormData): Promise<T> {
  return withTimeout(async (signal) =>
    unwrap<T>(await API.post(url, form, { signal })),
  );
}

/**
 * **PUT 과 DELETE** — M4 알림 설정 · 웹푸시 구독 해지 (2026-09-16 · 턴 S · 차선 U3).
 *
 * ★ 끝에 붙인다 — 위 규약과 같다(`dsmPostForm` 머리말).
 *
 * ★★ **왜 새 파일이 아니라 여기인가.** 이 저장소에는 그동안 GET·POST 만 있었고,
 *   구독 해지(`DELETE`)와 설정 저장(`PUT`)은 이번 턴에 처음 생겼다. 그 둘을
 *   화면 쪽에서 `API.delete(...)` 로 직접 부르면 **봉투 판정이 두 벌**이 된다 —
 *   `unwrap()` 은 HTTP 상태와 본문의 `success` 를 **둘 다** 보는데(D-358), 손으로
 *   부른 자리는 그 판정을 안 지나고 「200 인데 실패」를 성공으로 그린다.
 *   갈리는 쪽은 언제나 오류 처리다(D-349 착시 ⑧ · D-212).
 *
 * ★ 인자를 **질의로** 싣는 것도 같은 이유다: 이 저장소의 dsm 라우트는 인자를
 *   원시 타입으로 받고(django-ninja 규약상 질의), 본문으로 보내면 돌아오는 것은
 *   **422 · "Field required"** 다 — 그 422 는 「값이 틀렸다」가 아니라
 *   「인자가 없다」이고, 둘을 헷갈리면 한나절이 간다(`dsmPostQuery` 머리말).
 */
export function dsmPut<T>(
  url: string,
  query: Record<string, string | number | boolean> = {},
): Promise<T> {
  const qs = new URLSearchParams(
    Object.entries(query).map(([k, v]) => [k, String(v)]),
  ).toString();
  return withTimeout(async (signal) =>
    unwrap<T>(await API.put(qs ? `${url}?${qs}` : url, {}, { signal })),
  );
}

export function dsmDelete<T>(url: string): Promise<T> {
  return withTimeout(async (signal) =>
    unwrap<T>(await API.delete(url, { signal })),
  );
}

/**
 * 큐 카드의 **현장 신호** — 「지원 요청」 배지 · 「종결 확인」 카드 (턴 S · 차선 U1).
 *
 * ★ 끝에 붙인다 — 위 네 묶음과 같은 규약이다(같은 턴에 여러 차선이 이 파일을 읽고,
 *   충돌한 상수 파일은 화면 전체를 못 세운다).
 *
 * ★ **읽기 하나뿐이다.** 종결은 이미 있는 대응 진행 문(`dsmEndpoint.response`)이
 *   한다 — 같은 일을 하는 문을 하나 더 열지 않는다. 이 문이 답하는 것은
 *   「현장이 뭐라고 했나」 하나다.
 */
export const dsmU1Endpoint = {
  /** 화면이 지금 그린 카드의 사건 번호만 물어본다(쉼표로 이어 보낸다). */
  queueFieldSignals: '/api/dsm/queue/field-signals',
} as const;

/**
 * UX-36 카메라 오탐률·임계값 — **차선 U24 · 턴 S** (부속서A U2 #10·#11 · BF-3).
 *
 * ★ 끝에 붙인다 — 위쪽 `dsmEndpoint` 리터럴에 줄을 끼우면 같은 턴의 다른 차선과
 *   충돌하고, 충돌한 상수 파일은 화면 전체를 못 세운다(위 네 상수 묶음과 같은 규약).
 *
 * ★★ **저장하는 문은 여기서 새로 만들지 않는다.** 임계값을 바꾸는 문은 F-12 의
 *   `POST /api/dsm/settings/thresholds` 하나이고 이미 서 있다 — 사유가 비면 400,
 *   계약이 못박은 값이면 409, 권한이 없으면 403(감사 번호와 함께)이다.
 *   같은 일을 하는 문을 하나 더 열면 문지기가 두 벌이 되고, 두 벌은 어긋난다.
 */
export const dsmU24Endpoint = {
  /** 「어느 카메라가 시끄러운가」 — 내림차순 · 상위 N 강조. 분모를 함께 낸다. */
  falsePositiveByCamera: '/api/dsm/stats/false-positive/by-camera',
  /** 슬라이더가 부르는 자리 — 「시간당 N건」. **아무것도 바꾸지 않는다.** */
  thresholdSimulate: '/api/dsm/stats/thresholds/simulate',
  /** 카메라별로 고칠 수 있는 임계값의 이름표. 화면이 키를 손으로 들지 않는다. */
  cameraThresholdKeys: '/api/dsm/stats/camera-thresholds',
  /** 「저장 → 재조회」의 재조회. 값이 없으면 `null` 이고 0 이 아니다. */
  cameraThreshold: '/api/dsm/stats/camera-threshold',
  /** F-12 임계값 쓰기 — **이미 있는 문**이다(위 머리말). 사유가 비면 400. */
  settingsThresholds: '/api/dsm/settings/thresholds',
} as const;

/**
 * S-16 「알림 받는 사람·채널」 · S-15 「내 정보」 — **차선 U56 · 턴 S** (UX-43 · UX-42-me).
 *
 * ★ 끝에 붙인다 — 위 묶음들과 같은 규약이다(같은 턴에 여러 차선이 이 파일을 읽고,
 *   충돌한 상수 파일은 화면 전체를 못 세운다).
 *
 * ⚠ **경로가 세 조각인 이유**: `/settings/notify-rules`(두 조각)는 `api.py` 의
 *   `GET /settings/{domain}` 에 `domain="notify-rules"` 로 **삼켜진다** — GET 은 501,
 *   POST 는 405 가 되고, 그것은 「있는데 없는 것처럼 보이는」 가장 나쁜 모양이다(D-410).
 *   `/settings/people/create` 가 같은 이유로 세 조각인 것과 같은 실측이다.
 *
 * ★ `/api/dsm/me` 는 한 조각인데도 안전하다 — `api.py` 의 변수 조각은
 *   `/settings/{domain}` 하나뿐이고 그것은 `settings/` 로 시작하는 것만 삼킨다.
 */
export const dsmU56NotifyEndpoint = {
  /** 등급별 도달 · 규칙 · 채널 · **심각이 막혔는가**를 한 번에. */
  list: '/api/dsm/settings/notify-rules/list',
  /** 규칙 저장. **심각을 0명으로 만드는 저장은 409** 다(400 이 아니다). */
  save: '/api/dsm/settings/notify-rules/save',
  /** 시험 발송 — **훈련 채널로만** 나간다. 채널을 고를 수 있는 인자가 없다. */
  test: '/api/dsm/settings/notify-rules/test',
  /** S-15 「내 정보」 — 읽기뿐. 「내 알림 설정」 쓰기는 U3 의 WS-02 다. */
  me: '/api/dsm/me',
} as const;
