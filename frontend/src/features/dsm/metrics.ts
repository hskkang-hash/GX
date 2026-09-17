/**
 * 편리성 계측 — **클릭 수와 경과 시간을 재서 JSON 으로 남긴다** (턴 S · 차선 U1).
 *
 * 무엇을 재는가 — 지표 셋 (상용 정본 §6 「5배」 표의 1·2·3행)
 * ----------------------------------------------------------
 *   #1 사건 1건 처리 — 판정에서 접수까지 **몇 번 눌렀나 · 몇 초 걸렸나**
 *   #2 교대 인계 메모 — 초안이 뜨고 사람이 그것을 쓰기까지 **몇 초 걸렸나**
 *   #3 죽은 카메라 확인 — 화면을 열고 **몇 번 눌러야** 무응답 수를 아는가
 *
 * ⚠ **줄이는 것이 목적이 아니다. 지금 몇 번인지 재는 것이 목적이다.**
 *   첫 수는 기준선이지 합격선이 아니다 — 걷기 도구가 같은 문장을 머리에 달고 있고,
 *   이 파일도 같은 규율을 따른다. 그래서 여기에는 **판정이 없다**: 목표를 넘겼는지
 *   아닌지를 이 코드가 말하지 않는다. 수를 적을 뿐이고, 판정은 사람과 표가 한다.
 *
 * ★ **서버로 보내지 않는다.** 계측을 위해 새 쓰기 면을 여는 것은 재려던 것보다 큰
 *   변경이고, 관제 화면에서 나가는 요청이 하나 느는 일이다. 값은 이 브라우저 안에
 *   남고(`localStorage`), 걷는 도구가 창에서 **꺼내 간다**(아래 `window` 자리).
 *
 * ★ **사람을 식별하지 않는다.** 남기는 것은 지표 이름 · 대상의 종류 · 클릭 수 ·
 *   밀리초 · 시각뿐이다. 사건 번호는 남기되 본문은 한 자도 남기지 않는다 —
 *   회신 본문에는 현장의 말이 들어 있고, 그것은 계측의 자리가 아니다.
 *
 * ★ **저장을 못 해도 화면은 돈다.** 사파리 비공개 창처럼 저장이 막힌 환경이 있고,
 *   계측이 화면을 죽이면 그것은 재려던 것보다 큰 고장이다. 전부 try/catch 다.
 */

/** 재는 지표 셋. 이름을 바꾸면 표의 행과 갈린다 — 표가 정본이다. */
export type ConvenienceMetric =
  | 'u1_handle_event'
  | 'u1_handover_note'
  | 'u1_dead_camera_check';

/** 지표 한 줄이 무엇인가 — **JSON 이 스스로를 설명하게** 한다. */
export const METRIC_NOTE: Record<ConvenienceMetric, string> = {
  u1_handle_event:
    '사건 1건 처리 — 초점 카드가 뜬 때부터 판정과 접수가 끝날 때까지. 클릭은 그 사이에 이 화면에서 누른 수',
  u1_handover_note:
    '교대 인계 메모 — 인계 자리가 뜬 때부터 사람이 초안을 가져가거나 쓰기를 누를 때까지',
  u1_dead_camera_check:
    '죽은 카메라 확인 — 격자 화면이 뜬 때부터 무응답 수가 화면에 적힐 때까지. 클릭 0이 목표다',
};

/** 한 번의 측정. **끝난 것만** 여기 들어온다 — 하다 만 것은 수가 아니다. */
export interface ConvenienceRun {
  metric: ConvenienceMetric;
  /** 무엇에 대한 측정인가(사건 번호 등). 사람을 가리키는 값은 넣지 않는다. */
  subject: string;
  clicks: number;
  elapsed_ms: number;
  /** 끝까지 갔는가. 거짓이면 중간에 화면을 떠난 것이고, 그것도 사실이다. */
  completed: boolean;
  at: string;
}

interface Pending {
  subject: string;
  clicks: number;
  startedAt: number;
}

const STORAGE_KEY = 'gx.u1.convenience.v1';

/** 한 브라우저에 쌓아 두는 상한. 8시간 근무에도 자라지 않아야 한다. */
const MAX_RUNS = 60;

/** 아직 안 끝난 측정들. 화면을 떠나면 그대로 사라진다 — 그것이 옳다. */
const pending = new Map<ConvenienceMetric, Pending>();

function readRuns(): ConvenienceRun[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as ConvenienceRun[]) : [];
  } catch {
    // 못 읽으면 없는 것으로 본다 — 계측이 화면을 죽이지 않는다.
    return [];
  }
}

function writeRuns(runs: ConvenienceRun[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(runs));
  } catch {
    /* 저장을 못 해도 이번 근무 동안의 창 값은 살아 있다. */
  }
}

/**
 * 측정을 시작한다. **같은 대상으로 두 번 부르면 처음 것을 지킨다** —
 * 렌더가 여러 번 돌아도 시계가 다시 0이 되면 안 된다.
 */
export function startMetric(metric: ConvenienceMetric, subject: string): void {
  const live = pending.get(metric);
  if (live && live.subject === subject) return;
  pending.set(metric, { subject, clicks: 0, startedAt: Date.now() });
}

/** 사람이 한 번 눌렀다. 시작 전이면 **세지 않는다** — 없는 측정의 클릭은 없다. */
export function countClick(metric: ConvenienceMetric): void {
  const live = pending.get(metric);
  if (live) live.clicks += 1;
}

/** 지금까지 센 클릭 수(화면이 자기 수를 보여 줄 때 쓴다). 없으면 `null`. */
export function clicksSoFar(metric: ConvenienceMetric): number | null {
  return pending.get(metric)?.clicks ?? null;
}

/**
 * 측정을 끝내고 **한 줄을 남긴다.** 시작한 적이 없으면 아무것도 안 남긴다 —
 * 시작 없는 끝은 경과가 없고, 경과 없는 수는 수가 아니다.
 */
export function finishMetric(
  metric: ConvenienceMetric,
  options: { completed?: boolean } = {},
): ConvenienceRun | null {
  const live = pending.get(metric);
  if (!live) return null;
  pending.delete(metric);

  const run: ConvenienceRun = {
    metric,
    subject: live.subject,
    clicks: live.clicks,
    elapsed_ms: Math.max(0, Date.now() - live.startedAt),
    completed: options.completed !== false,
    at: new Date().toISOString(),
  };

  const runs = readRuns();
  runs.push(run);
  writeRuns(runs.slice(-MAX_RUNS));
  return run;
}

/** 시작한 측정을 **수 없이** 버린다(대상이 바뀌었을 때). */
export function cancelMetric(metric: ConvenienceMetric): void {
  pending.delete(metric);
}

/** 아직 안 끝난 측정 — 「왜 값이 없나」를 V 가 볼 수 있게 함께 낸다(수는 아니다). */
export interface ConvenienceInFlight {
  metric: ConvenienceMetric;
  subject: string;
  clicks_so_far: number;
  elapsed_ms_so_far: number;
}

export interface ConvenienceExport {
  schema: string;
  generated_at: string;
  notes: Record<string, string>;
  runs: ConvenienceRun[];
  /** 끝나지 않은 측정들. `runs` 에 들어가지 않고 대장에도 안 붙는다 — 진단용이다. */
  in_flight: ConvenienceInFlight[];
  /** 이 브라우저의 저장이 살아 있는가. 거짓이면 `runs` 는 이번 화면 수명 동안의 값도 못 담는다. */
  storage_ok: boolean;
}

/**
 * 재 둔 것을 **JSON 한 덩이로** 낸다. 걷는 도구가 이것을 꺼내 증거 대장에 붙인다.
 *
 * ★ 판정을 담지 않는다 — 기준선·목표와 견주는 일은 표가 한다.
 */
export function exportConvenience(): ConvenienceExport {
  const now = Date.now();
  const inFlight: ConvenienceInFlight[] = [];
  pending.forEach((live, metric) => {
    inFlight.push({
      metric,
      subject: live.subject,
      clicks_so_far: live.clicks,
      elapsed_ms_so_far: Math.max(0, now - live.startedAt),
    });
  });
  return {
    schema: 'gx.convenience.u1.v1',
    generated_at: new Date().toISOString(),
    notes: METRIC_NOTE,
    runs: readRuns(),
    in_flight: inFlight,
    storage_ok: storageOk(),
  };
}

/** 저장이 되는가 — 한 번 써 보고 지운다. 비공개 창·차단 환경이면 거짓이다. */
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

/** 다음 측정을 위해 비운다. **사람이 부르는 자리**다(자동으로 안 지운다). */
export function resetConvenience(): void {
  pending.clear();
  try {
    window.localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* 못 지워도 다음 실행이 덮어쓴다. */
  }
}

/**
 * 창에 꺼내 두는 자리 — **걷는 도구가 브라우저에서 이 이름으로 꺼내 간다.**
 *
 * ★ 이 이름이 없으면 계측은 이 브라우저 안에서 끝나고 아무 데도 안 남는다.
 *   서버로 보내지 않기로 한 판단의 반대쪽 짝이 이 세 줄이다.
 */
declare global {
  interface Window {
    __gxConvenience?: {
      export: () => ConvenienceExport;
      reset: () => void;
    };
    /** 같은 것의 짧은 이름 — 지시서(턴 T)가 부르는 철자. `JSON.stringify(window.__gxMetrics())`. */
    __gxMetrics?: () => ConvenienceExport;
  }
}

if (typeof window !== 'undefined') {
  window.__gxConvenience = {
    export: exportConvenience,
    reset: resetConvenience,
  };
  window.__gxMetrics = exportConvenience;
}
