/**
 * FWS-F1-13 — 오프라인 큐. 산지에서 통신이 끊기면 체크인·트랙 요청을
 * `localStorage` 에 쌓아 두고, `online` 이벤트에서 **같은 Idempotency-Key** 로
 * 다시 보낸다.
 *
 * 서버 쪽 중복 제거는 `common/idempotency.py` 가 한다(재구현하지 않는다 — D-212).
 * 이 파일이 보장하는 것은 **큐 쪽**이다: 같은 항목을 두 번 넣지 않고, 보낸 항목은
 * 큐에서 지운다 — 재전송이 큐 자체를 두 배로 불리지 않게.
 *
 * ⚠ 브라우저 저장소는 이 브라우저 안에서만 산다(다른 기기·새로고침 뒤에도 남지만
 *   Claude 나 서버는 못 읽는다) — 여기서는 그것으로 충분하다: 큐가 지키는 약속은
 *   "이 기기가 다시 연결되면 이 기기가 쌓은 것을 보낸다"이지 더 넓지 않다.
 */
import { fwsEndpoint, fwsPostQuery, newFwsIdempotencyKey } from './api';

const STORAGE_KEY = 'gx-fws-offline-queue-v1';

export interface QueuedPatrolAction {
  key: string;
  kind: 'checkin' | 'track';
  params: Record<string, string | number | boolean>;
  queuedAt: string;
}

function readQueue(): QueuedPatrolAction[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeQueue(items: QueuedPatrolAction[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch {
    // 저장 실패(사생활 모드 등) — 조용히 넘긴다. 이 큐는 편의 기능이지
    // 반드시 지켜야 하는 상태가 아니다(artifact 규약과 같은 판단).
  }
}

/** 지금 온라인이 아니면 큐에 쌓고, 온라인이면 바로 보낸다. 둘 다 같은 키를 쓴다. */
export async function checkinOrQueue(
  params: Record<string, string | number | boolean>,
): Promise<{ queued: boolean }> {
  const key = newFwsIdempotencyKey();
  if (!navigator.onLine) {
    writeQueue([...readQueue(), { key, kind: 'checkin', params, queuedAt: new Date().toISOString() }]);
    return { queued: true };
  }
  await fwsPostQuery(fwsEndpoint.patrolCheckin, params, key);
  return { queued: false };
}

/** 복귀 시 전송 N — 쌓인 항목을 순서대로, 성공한 것만 지운다. */
export async function flushQueue(): Promise<number> {
  const items = readQueue();
  if (items.length === 0) return 0;
  let sent = 0;
  const remaining: QueuedPatrolAction[] = [];
  for (const item of items) {
    try {
      const endpoint =
        item.kind === 'checkin' ? fwsEndpoint.patrolCheckin : fwsEndpoint.patrolTrack;
      await fwsPostQuery(endpoint, item.params, item.key);
      sent += 1;
    } catch {
      remaining.push(item); // 아직도 실패하면 큐에 남겨 다음 기회에
    }
  }
  writeQueue(remaining);
  return sent;
}

export function pendingCount(): number {
  return readQueue().length;
}

/** 화면이 마운트될 때 한 번 걸어 둔다. */
export function installAutoFlush(): () => void {
  const handler = () => {
    void flushQueue();
  };
  window.addEventListener('online', handler);
  return () => window.removeEventListener('online', handler);
}
