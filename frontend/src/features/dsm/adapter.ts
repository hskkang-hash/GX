/**
 * 응답 어댑터 — 프런트의 응답 해석은 **이 한 곳**이다 (WO-01 §5 「어댑터」 · P-129 · ADP-01).
 *
 * ★ 왜 한 곳인가 [P-129 · 턴 P 판정]
 *   「서버는 주는데 화면이 안 그린다」가 여섯 곳(사진 · 판정 · 상황판 · 실시간 ·
 *   역할 부여 · 웹훅)에서 같은 모양으로 났다. 화면마다 `res.data` · `res.data.data` ·
 *   `res.success` 를 제각각 읽고 있었고, 그중 하나가 틀리면 **값은 왔는데 화면이 빈다.**
 *   해석을 한 곳에 모으면 모양이 바뀌어도 고칠 자리가 하나다.
 *
 * ★ 모양은 셋이다 — 서버 실제 코드에서 확인했다
 *   ① `envelope` — dj-core 봉투 `{success, message, status_code?, data?}`.
 *      권한 거절은 `{success:false, status_code:403, message}` 로 **200 안에** 온다
 *      (`backend/common/api_contract.py:4-8` · `core/role/permission.py` 는 §0.4).
 *      승격 접두(`config/settings.py:379` `API_CONTRACT_PROMOTE_PATHS`) 안이면
 *      미들웨어가 **상태줄만** 4xx 로 올린다 — 본문은 그대로다
 *      (`api_contract.py:260-263` 「본문·헤더는 그대로 두고 상태줄만 고친다」).
 *      그래서 승격 **전**(200 + success:false)과 **후**(403 + success:false)가
 *      본문으로는 구별되지 않는다 — 판정은 반드시 **상태 + `success` 둘 다**다(DA-03 §0-1).
 *   ② `bare` — django-ninja 라우트가 스키마를 그대로 낸 본문(DSM 라우트 대부분).
 *      `success` 키가 없다. 값은 **본문 자체**다.
 *   ③ `error` — ninja `HttpError` 의 `{detail}` · 422 `{detail:[…]}` ·
 *      HTTP 4xx/5xx 인데 봉투가 아닌 본문 · 본문이 아예 없음.
 *
 * ★ 이 앱의 axios 는 **본문을 돌려준다** (rj-core `createApiClient` 의 응답 인터셉터
 *   `return i.data` — `features/dsm/api.ts:237-254` P-121 실측). 그래서 성공 갈래에는
 *   HTTP 상태가 **없다**. `httpStatus` 를 모르면(null·undefined) 인터셉터가 **해소했다**는
 *   뜻이므로 2xx 로 읽는다 — 실패 갈래는 `err.response.status` 를 넘겨 부른다.
 *   AxiosResponse 모양(`{data, status, headers, config}`)이 오면 그 안을 벗겨 읽는다 —
 *   인터셉터가 원래 모양으로 돌아와도 이 함수는 그대로 산다.
 *
 * ⚠ 서명은 고정이다 — U1·U3 차선이 이 서명에 코딩한다(턴 Q). 바꾸지 않는다.
 */

export type UnwrapShape = 'envelope' | 'bare' | 'error';

export interface Unwrapped<T> {
  /** 성공인가. **HTTP 상태와 본문 `success`/`status_code` 가 둘 다** 성공일 때만 참. */
  ok: boolean;
  /** 판정에 쓴 상태. HTTP 4xx/5xx 가 우선, 없으면 본문 `status_code`, 둘 다 없으면 null. */
  status: number | null;
  /** 값. 봉투면 `data`(없으면 `response`) · 맨몸이면 본문 자체 · 실패면 null. */
  data: T | null;
  /** 사람에게 보여 줄 수 있는 **서버의** 사유 한 줄. 서버가 안 썼으면 null. */
  message: string | null;
  shape: UnwrapShape;
}

/** 봉투를 알아보는 표지. `success` 가 **불리언**이어야 봉투다 — 도메인 필드와 헷갈리지 않게. */
function isEnvelope(body: unknown): body is Record<string, unknown> {
  return (
    !!body &&
    typeof body === 'object' &&
    !Array.isArray(body) &&
    typeof (body as Record<string, unknown>).success === 'boolean'
  );
}

/** AxiosResponse 모양인가. 인터셉터가 본문을 주는 지금은 거의 없지만 **둘 다 받는다.** */
function isAxiosResponse(value: unknown): value is { data: unknown; status: number } {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const v = value as Record<string, unknown>;
  return (
    'data' in v &&
    typeof v.status === 'number' &&
    'headers' in v &&
    'config' in v
  );
}

/**
 * 사유 한 줄을 **문자열로** 꺼낸다.
 *
 * ⚠ [실측] 로그인 면은 사유를 `{en, ko, vi, th}` 로 준다. 객체를 그대로 넣으면
 *   화면에 `[object Object]` 가 뜬다 (`features/dsm/api.ts:101-104`).
 *   422 는 `detail: [{msg, loc}]` 배열이다 — 첫 `msg` 를 쓴다.
 */
export function pickMessage(value: unknown): string | null {
  if (typeof value === 'string') return value.trim() || null;
  if (Array.isArray(value)) {
    for (const item of value) {
      const m = pickMessage((item as { msg?: unknown } | null)?.msg ?? item);
      if (m) return m;
    }
    return null;
  }
  if (value && typeof value === 'object') {
    const bag = value as Record<string, unknown>;
    for (const key of ['ko', 'en']) {
      const v = bag[key];
      if (typeof v === 'string' && v.trim()) return v.trim();
    }
  }
  return null;
}

function numericStatus(value: unknown): number | null {
  // bool 은 숫자가 아니다 — 서버 판정(`api_contract.py:119-121`)과 같게 좁힌다.
  return typeof value === 'number' && Number.isInteger(value) ? value : null;
}

/**
 * 응답 본문을 해석한다. **던지지 않는다** — 판정은 `ok` 로 돌려준다.
 *
 * @param body       인터셉터가 준 본문(또는 AxiosResponse · 또는 `err.response.data`)
 * @param httpStatus 아는 경우의 HTTP 상태. 모르면 생략 — 해소된 응답은 2xx 로 읽는다.
 */
export function unwrap<T = unknown>(
  body: unknown,
  httpStatus?: number | null,
): Unwrapped<T> {
  let raw = body;
  let http = numericStatus(httpStatus);
  if (isAxiosResponse(raw)) {
    if (http === null) http = raw.status;
    raw = raw.data;
  }
  const httpFailed = http !== null && (http < 200 || http >= 300);

  if (isEnvelope(raw)) {
    const bodyStatus = numericStatus(raw.status_code);
    const bodyFailed =
      raw.success === false || (bodyStatus !== null && bodyStatus >= 400);
    const ok = !httpFailed && !bodyFailed;
    // 판정에 쓴 상태: HTTP 실패가 먼저, 다음이 본문의 4xx·5xx, 그다음 HTTP 상태.
    const status = httpFailed
      ? http
      : bodyStatus !== null && bodyStatus >= 400
        ? bodyStatus
        : http ?? bodyStatus;
    // 값의 자리: `data` → `response` → **본문 자체**. 봉투인데 둘 다 없으면 도메인 칸이
    // 본문에 바로 붙어 온 것이다(예: `{success:true, sent:3}`) — 버리면 값이 사라진다.
    const payload =
      'data' in raw ? raw.data : 'response' in raw ? raw.response : raw;
    return {
      ok,
      status,
      data: ok ? ((payload === undefined ? null : payload) as T | null) : null,
      message: pickMessage(raw.message) ?? pickMessage(raw.detail),
      shape: 'envelope',
    };
  }

  const bodyStatus =
    raw && typeof raw === 'object' && !Array.isArray(raw)
      ? numericStatus((raw as Record<string, unknown>).status_code)
      : null;
  const bodyFailed = bodyStatus !== null && bodyStatus >= 400;
  // 본문이 **아예 없고** 상태도 모른다 = 대답을 못 받았다(끊김 · 부르는 쪽이 undefined 를 넘김).
  // 상태가 2xx 로 알려진 빈 본문(204 · `''`)은 성공이다 — 값이 없을 뿐이다.
  const noAnswer = (raw === undefined || raw === '') && http === null;

  if (httpFailed || bodyFailed || noAnswer) {
    const bag =
      raw && typeof raw === 'object' && !Array.isArray(raw)
        ? (raw as Record<string, unknown>)
        : {};
    return {
      ok: false,
      status: httpFailed ? http : bodyFailed ? bodyStatus : http,
      data: null,
      message: pickMessage(bag.message) ?? pickMessage(bag.detail),
      shape: 'error',
    };
  }

  return {
    ok: true,
    status: http,
    data: (raw === null || raw === undefined || raw === '' ? null : raw) as T | null,
    message: null,
    shape: 'bare',
  };
}
