/**
 * 편리성 계측 #5 — **수신부터 확인까지** (`u3_receive_to_ack`) (턴 U · 차선 U3).
 *
 * 무엇을 재는가
 * -------------
 *   현장 사람의 휴대전화에 알림이 **도착한 순간**(M1 「내게 온 이벤트」 목록에
 *   뜬 순간)부터, 그 사람이 그 사건을 **실제로 연 순간**(M3 상세를 연다)까지
 *   몇 초 걸렸는가. 「받았다」와 「봤다」 사이의 간격이다 — 그 간격이 길면
 *   웹푸시가 잠금화면까지 갔어도 사람이 늦게 봤다는 뜻이고, 그 사실은 P-166 이
 *   고친 구독 경로만으로는 안 보인다.
 *
 * `frontend/src/features/dsm/metrics.ts`(차선 U1)와 **같은 규약**을 따른다 —
 * 그 파일을 이번 턴에 읽고 그대로 옮겨 썼다:
 *   · **서버로 보내지 않는다** — `localStorage` 에 남고 걷는 도구가 창에서 꺼내 간다.
 *   · **사람을 식별하지 않는다** — 남기는 것은 사건 번호 · 클릭 수 · 밀리초 · 시각뿐.
 *   · **저장을 못 해도 화면은 돈다** — 전부 try/catch.
 *   · **판정을 담지 않는다** — 기준선이지 합격선이 아니다. 목표 대비 판정은 표가 한다.
 *
 * 다른 점 하나 — **동시에 여럿을 잰다**
 * --------------------------------------
 * `dsm/metrics.ts` 는 한 화면에 초점 카드가 하나뿐이라 지표마다 진행 중 측정을
 * **한 개**만 든다(`Map<지표, 진행>`). M1 목록에는 사건이 **여럿** 동시에 떠 있고,
 * 그중 하나를 열어도 나머지는 여전히 「받았는데 아직 안 봄」 상태다 — 한 슬롯이면
 * 먼저 뜬 사건의 시계가 나중 사건이 뜨는 순간 지워진다. 그래서 진행 중 측정을
 * **사건 번호로 키를 나눈 맵**(`Map<subject, Pending>`)으로 둔다.
 *
 * ★ 새 쓰기 면 0 — 이 파일은 읽기만 한다(기존 `GET` 들이 이미 화면에 있다).
 * ★ `metrics.ts`(U1 소유)를 고치지 않는다 — 지표 이름이 그 파일의 표에 없어서
 *   보고에 등록 요청으로 적는다(같은 화면 안에서만 쓰이는 지표라 급하지 않다).
 */

/** 지금은 하나뿐이다 — 이름을 바꾸면 걷는 도구의 창 자리도 같이 바꾼다. */
export type MobileConvenienceMetric = 'u3_receive_to_ack';

export const MOBILE_METRIC_NOTE: Record<MobileConvenienceMetric, string> = {
  u3_receive_to_ack:
    '수신부터 확인까지 — 사건이 M1 「내게 온 이벤트」 목록에 뜬 때부터 그 사건의 '
    + '상세(M3)를 연 때까지. subject 는 사건 번호다',
};

/** 한 번의 측정. **끝난 것만** 여기 들어온다. */
export interface MobileConvenienceRun {
  metric: MobileConvenienceMetric;
  /** 사건 번호. 사람을 가리키는 값은 넣지 않는다. */
  subject: string;
  clicks: number;
  elapsed_ms: number;
  completed: boolean;
  at: string;
}

interface Pending {
  startedAt: number;
  clicks: number;
}

const STORAGE_KEY = 'gx.u3.convenience.v1';
const MAX_RUNS = 60;

/** 사건 번호별 진행 중 측정 — **여럿을 동시에** 잰다(머리말 「다른 점」). */
const pending = new Map<string, Pending>();

function readRuns(): MobileConvenienceRun[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as MobileConvenienceRun[]) : [];
  } catch {
    return [];
  }
}

function writeRuns(runs: MobileConvenienceRun[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
  } catch {
    /* 저장을 못 해도 이번 근무 동안의 창 값은 살아 있다. */
  }
}

/**
 * 「받았다」를 표시한다. **이미 재고 있는 사건이면 다시 시작하지 않는다** — 목록이
 * 다시 읽힐 때마다(폴링·되읽기) 같은 사건이 또 지나가도 첫 도착 시각을 지킨다.
 */
export function startReceiveToAck(eventId: string): void {
  if (!eventId || pending.has(eventId)) return;
  pending.set(eventId, { startedAt: Date.now(), clicks: 0 });
}

/**
 * 「봤다」를 표시하고 **한 줄을 남긴다.** 시작한 적이 없으면(이 세션에서 목록을
 * 거치지 않고 상세로 바로 왔거나, 이미 한 번 확인한 사건이면) 아무것도 안 남긴다 —
 * 시작 없는 끝은 경과가 없다.
 */
export function finishReceiveToAck(eventId: string): MobileConvenienceRun | null {
  const live = pending.get(eventId);
  if (!live || !eventId) return null;
  pending.delete(eventId);

  const run: MobileConvenienceRun = {
    metric: 'u3_receive_to_ack',
    subject: eventId,
    clicks: live.clicks,
    elapsed_ms: Math.max(0, Date.now() - live.startedAt),
    completed: true,
    at: new Date().toISOString(),
  };

  const runs = readRuns();
  runs.push(run);
  writeRuns(runs.slice(-MAX_RUNS));
  return run;
}

/** 아직 「못 본」 사건들 — 진단용이다(수는 아니다). */
export interface MobileConvenienceInFlight {
  metric: MobileConvenienceMetric;
  subject: string;
  elapsed_ms_so_far: number;
}

export interface MobileConvenienceExport {
  schema: string;
  generated_at: string;
  notes: Record<string, string>;
  runs: MobileConvenienceRun[];
  in_flight: MobileConvenienceInFlight[];
  storage_ok: boolean;
}

function storageOk(): boolean {
  try {
    const probe = `${STORAGE_KEY}.probe`;
    window.localStorage.setItem(probe, '1');
    window.localStorage.removeItem(probe);
    return true;
  } catch {
    return false;
  }
}

/** 재 둔 것을 JSON 한 덩이로 낸다 — 걷는 도구가 창에서 꺼내 간다. */
export function exportMobileConvenience(): MobileConvenienceExport {
  const now = Date.now();
  const inFlight: MobileConvenienceInFlight[] = [];
  pending.forEach((live, subject) => {
    inFlight.push({
      metric: 'u3_receive_to_ack',
      subject,
      elapsed_ms_so_far: Math.max(0, now - live.startedAt),
    });
  });
  return {
    schema: 'gx.convenience.u3.v1',
    generated_at: new Date().toISOString(),
    notes: MOBILE_METRIC_NOTE,
    runs: readRuns(),
    in_flight: inFlight,
    storage_ok: storageOk(),
  };
}

/** 다음 측정을 위해 비운다. 사람이 부르는 자리다. */
export function resetMobileConvenience(): void {
  pending.clear();
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* 못 지워도 다음 실행이 덮어쓴다. */
  }
}

declare global {
  interface Window {
    /** `dsm/metrics.ts::window.__gxConvenience` 와 같은 자리 — 모바일 몫만 따로 둔다. */
    __gxMobileConvenience?: {
      export: () => MobileConvenienceExport;
      reset: () => void;
    };
    __gxMobileMetrics?: () => MobileConvenienceExport;
  }
}

if (typeof window !== 'undefined') {
  window.__gxMobileConvenience = {
    export: exportMobileConvenience,
    reset: resetMobileConvenience,
  };
  window.__gxMobileMetrics = exportMobileConvenience;
}
