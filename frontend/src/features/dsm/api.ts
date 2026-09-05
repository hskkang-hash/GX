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
  constructor(message: string, status: number) {
    super(message);
    this.name = 'DsmApiError';
    this.status = status;
  }
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
  const detail: string | undefined =
    typeof body?.detail === 'string' ? body.detail : undefined;

  if (httpStatus >= 400) {
    throw new DsmApiError(
      body?.message ?? detail ?? `요청이 실패했습니다 (${httpStatus})`,
      httpStatus,
    );
  }
  if (bodyStatus !== undefined && bodyStatus >= 400) {
    throw new DsmApiError(
      body?.message ?? detail ?? `요청이 거절되었습니다 (${bodyStatus})`,
      bodyStatus,
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
    const body = err?.response?.data;
    throw new DsmApiError(
      body?.message ?? err?.message ?? '요청이 실패했습니다.',
      status,
    );
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
