/**
 * 편리성 계측 #5 — **수신부터 접수까지** (`u3_receive_to_ack`) (턴 U · 차선 U3).
 *
 * 무엇을 재는가
 * -------------
 *   현장 사람의 휴대전화에 알림이 **도착한 순간**(M1 「내게 온 이벤트」 목록에
 *   뜬 순간)부터, 그 사람이 그 사건을 **접수한 순간**(M3 「접수하기」가 서버에
 *   기록된 때)까지 몇 초, 몇 탭 걸렸는가.
 *
 * ★★ [턴 V · 차선 U3] **시계가 멈추는 자리를 옮겼다.** 턴 U 판은 「상세를 연 때」에
 *   멈췄다. 그런데 PRD §6 의 5번 항목이 재기로 한 것은 그것이 아니다:
 *
 *       #5 | U3 | **문자 수신 → 접수 회신** | 전화 왕복 3~5분 → **≤ 30초**(1탭 · 「1」 회신)
 *
 *   「열어 봤다」는 「접수했다」가 아니다. 열기만 하고 아무 회신도 없으면 관제는
 *   여전히 아무것도 모르고, 기준선(전화 왕복 3~5분)이 재던 것도 **회신이 관제에
 *   닿기까지**였다. 열기에서 멈춘 시계는 **언제나 더 작은 수**를 내므로, 그 수로
 *   5번 칸을 채우면 목표를 쉬운 것으로 바꿔 초록을 만드는 일이 된다.
 *   그래서 열기는 **끝이 아니라 탭 한 번**으로 센다(`markOpened`) — 목표의 「1탭」이
 *   그 자리에서 세어진다.
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
    '수신부터 접수까지 — 사건이 M1 「내게 온 이벤트」 목록에 뜬 때부터 그 사건을 '
    + 'M3 에서 접수한 때까지. 상세를 연 것은 끝이 아니라 탭 한 번으로 센다. '
    + 'subject 는 사건 번호다',
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
  /**
   * 「받았다」에서 **상세를 연 때**까지. 전체(`elapsed_ms`)의 부분이다 —
   * 수신부터 접수까지가 길 때 **보는 데 늦은 것인지 누르는 데 늦은 것인지**를
   * 가른다. 열기 전에 접수한 경우(그런 길은 지금 없다)는 `null` 이다.
   */
  opened_ms: number | null;
}

interface Pending {
  startedAt: number;
  clicks: number;
  /** 상세를 연 때. 아직 안 열었으면 `null` — 0 으로 두지 않는다(0 은 시각이다). */
  openedAt: number | null;
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
  pending.set(eventId, { startedAt: Date.now(), clicks: 0, openedAt: null });
}

/**
 * 「열었다」를 표시한다 — **끝이 아니라 탭 한 번이다**(머리말 ★★).
 *
 * 목표의 「1탭」이 세어지는 자리이고, 같은 사건을 두 번 열어도 **탭은 두 번**이다
 * (실제로 두 번 눌렀으므로). 다만 열린 시각은 **처음 것만** 지킨다 — 나중 것으로
 * 덮으면 「보는 데 걸린 시간」이 볼 때마다 짧아진다.
 */
export function markOpened(eventId: string): void {
  const live = pending.get(eventId);
  if (!live || !eventId) return;
  live.clicks += 1;
  if (live.openedAt === null) live.openedAt = Date.now();
}

/**
 * 「접수했다」를 표시하고 **한 줄을 남긴다.** 시작한 적이 없으면(이 세션에서 목록을
 * 거치지 않고 상세로 바로 왔거나, 이미 한 번 접수한 사건이면) 아무것도 안 남긴다 —
 * 시작 없는 끝은 경과가 없다.
 *
 * ★ 접수 요청이 **성공한 뒤에만** 부른다. 누른 때 부르면 서버가 거절한 접수가
 *   수에 들어가고, 그 수는 「30초 안에 접수했다」를 거짓으로 만든다.
 */
export function finishReceiveToAck(eventId: string): MobileConvenienceRun | null {
  const live = pending.get(eventId);
  if (!live || !eventId) return null;
  pending.delete(eventId);

  const now = Date.now();
  const run: MobileConvenienceRun = {
    metric: 'u3_receive_to_ack',
    subject: eventId,
    //: 접수 단추를 누른 그 한 탭을 함께 센다 — 목표가 세는 것이 탭이다.
    clicks: live.clicks + 1,
    elapsed_ms: Math.max(0, now - live.startedAt),
    completed: true,
    at: new Date().toISOString(),
    opened_ms: live.openedAt === null
      ? null
      : Math.max(0, live.openedAt - live.startedAt),
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
  /** 지금까지의 탭 수. 붙이는 도구가 이 이름으로 읽는다(`merge_convenience_u1`). */
  clicks_so_far: number;
  /** 열어는 봤는가. 「받고도 안 열었다」와 「열고도 접수 안 했다」는 다른 사실이다. */
  opened: boolean;
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
      clicks_so_far: live.clicks,
      opened: live.openedAt !== null,
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
