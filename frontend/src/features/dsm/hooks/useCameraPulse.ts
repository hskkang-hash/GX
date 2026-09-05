/**
 * UX-16 월 모드의 **「카메라 상태」 칸** — 남의 차선이 이번 턴에 내는 문을 부른다.
 *
 * 왜 이렇게 겁이 많은가
 * --------------------
 * 이 문(`/api/dsm/cameras/pulse`)은 **아직 없다.** 다른 차선이 이번 턴에 내고,
 * 병합 때 붙는다. 그때까지 이 훅은 404 를 받는다 — 그리고 그것은 **월 모드가
 * 죽을 이유가 아니다.** 관제실 대형 화면에서 한 칸 때문에 세 칸이 같이 꺼지면
 * 그날 밤 관제요원은 아무것도 못 본다. 그래서:
 *
 *   ① 부르는 자리를 **따로** 둔다 — 이 칸의 오류가 큐와 지도에 닿지 않는다.
 *   ② 응답 **모양을 모르면 그 칸만 비운다.** 모양은 내는 쪽이 정하고, 우리는
 *      아는 이름들을 차례로 물어본 뒤 못 알아들으면 「못 알아들었다」고 적는다.
 *   ③ 모르는 값을 **지어내지 않는다.** 살았는지 모르면 `null` 이다 —
 *      「응답 없음」과 「모른다」는 다른 사실이고, 둘을 합치면 멀쩡한 카메라가
 *      죽은 것으로 보인다.
 *
 * ⚠ 이 경로는 `api.ts` 의 `dsmEndpoint` 에 아직 없다. 그 파일은 이번 턴에 여러
 *   차선이 함께 쓰는 자리라 여기서 고치지 않는다 — 조율자가 배선한다.
 */
import { dsmGet } from '../api';
import { useDsmResource } from './useDsmResource';
import type { Resource } from './useDsmResource';

/** 남의 차선이 내는 문. 병합 전에는 없고, 없어도 화면은 산다. */
export const CAMERA_PULSE_PATH = '/api/dsm/cameras/pulse';

export interface PulseRow {
  key: string;
  name: string;
  /** 참=응답 있음 · 거짓=응답 없음 · `null`=**모른다**. 셋을 합치지 않는다. */
  alive: boolean | null;
  /** 마지막 응답 시각. 없으면 `null` — 「없다」와 「언제부터 없다」는 다른 사실이다. */
  lastSeenAt: string | null;
}

export interface PulseView {
  /** 응답을 **알아들었는가.** 거짓이면 이 칸은 비운다. */
  understood: boolean;
  rows: PulseRow[];
  total: number;
}

const ARRAY_KEYS = ['cameras', 'items', 'results', 'rows', 'data', 'pulses'];
const NAME_KEYS = ['name', 'stream_monitor_name', 'camera_name', 'title', 'label'];
const ALIVE_KEYS = ['alive', 'online', 'ok', 'healthy', 'is_alive', 'up', 'responding'];
const STATUS_KEYS = ['status', 'state', 'pulse'];
const SEEN_KEYS = [
  'last_seen_at',
  'last_frame_at',
  'last_pulse_at',
  'last_seen',
  'last_response_at',
  'updated_at',
];
const ID_KEYS = ['id', 'camera_id', 'stream_monitor_id', 'key'];

const ALIVE_WORDS = ['alive', 'online', 'ok', 'up', 'healthy', 'normal', 'running', 'active'];
const DEAD_WORDS = ['down', 'offline', 'dead', 'lost', 'stale', 'unresponsive', 'no_response'];

type Bag = Record<string, unknown>;

function pickArray(payload: unknown): unknown[] | null {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== 'object') return null;
  const bag = payload as Bag;
  for (const k of ARRAY_KEYS) {
    const v = bag[k];
    if (Array.isArray(v)) return v;
    // 한 겹 더 싸여 오는 모양도 있다 — 한 겹만 벗긴다.
    if (v && typeof v === 'object') {
      const inner = pickArray(v);
      if (inner) return inner;
    }
  }
  return null;
}

function pickString(bag: Bag, keys: string[]): string | null {
  for (const k of keys) {
    const v = bag[k];
    if (typeof v === 'string' && v.trim()) return v;
    if (typeof v === 'number') return String(v);
  }
  return null;
}

function pickAlive(bag: Bag): boolean | null {
  for (const k of ALIVE_KEYS) {
    const v = bag[k];
    if (typeof v === 'boolean') return v;
  }
  for (const k of STATUS_KEYS) {
    const v = bag[k];
    if (typeof v !== 'string') continue;
    const word = v.trim().toLowerCase();
    if (ALIVE_WORDS.includes(word)) return true;
    if (DEAD_WORDS.includes(word)) return false;
  }
  // 못 알아들었다. **모른다고 적는다** — 죽었다고 적지 않는다.
  return null;
}

/** 아는 이름을 차례로 물어본다. 하나도 못 알아들으면 `understood` 가 거짓이다. */
export function readPulse(payload: unknown): PulseView {
  const arr = pickArray(payload);
  if (!arr) return { understood: false, rows: [], total: 0 };

  const rows: PulseRow[] = [];
  let readable = 0;
  arr.forEach((raw, i) => {
    if (!raw || typeof raw !== 'object') return;
    const bag = raw as Bag;
    const name = pickString(bag, NAME_KEYS);
    const alive = pickAlive(bag);
    const lastSeenAt = pickString(bag, SEEN_KEYS);
    if (name !== null || alive !== null || lastSeenAt !== null) readable += 1;
    rows.push({
      key: pickString(bag, ID_KEYS) ?? `${i}`,
      name: name ?? '이름 없는 카메라',
      alive,
      lastSeenAt,
    });
  });

  // 줄은 있는데 **한 줄도 못 읽었으면** 알아들은 것이 아니다.
  if (rows.length > 0 && readable === 0) return { understood: false, rows: [], total: 0 };
  return { understood: true, rows, total: rows.length };
}

export function useCameraPulse(refreshMs: number): Resource<PulseView> {
  return useDsmResource<PulseView>(
    async () => readPulse(await dsmGet<unknown>(CAMERA_PULSE_PATH)),
    [],
    { refreshMs },
  );
}
