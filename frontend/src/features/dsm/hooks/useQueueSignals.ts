/**
 * 큐 카드의 **현장 신호**를 읽는다 — 「지원 요청」 · 「조치 완료」 (턴 S · 차선 U1).
 *
 * 왜 큐 응답에 안 싣고 따로 부르나
 * --------------------------------
 * 초점 큐(`/events/queue`)는 **월 화면도 부르는 문**이다(세션 없이 읽는 자리가 있다).
 * 거기에 현장 회신 본문을 실으면 그 문이 나르는 것이 늘어나고, 늘어난 것은 되돌리기
 * 어렵다. 그래서 신호는 **다른 문**으로 부르고, 화면이 지금 그린 카드의 번호만 묻는다.
 *
 * ★ **실패가 화면을 죽이지 않는다.** 이 값은 곁들이(배지 하나 · 카드 하나)다 —
 *   못 읽었으면 배지가 안 뜨는 것으로 끝나야지, 큐 전체가 오류 상자가 되면 안 된다.
 *   그래서 이 훅은 자기 상태를 따로 들고, 부르는 쪽은 큐를 그대로 그린다.
 *
 * ★ **못 읽은 것을 「없다」로 그리지 않는다.** `wired` 가 거짓이면 화면은
 *   「배선 대기」라고 적는다 — 회신은 오는데 종류가 아직 안 달린 상태가 실재한다.
 */
import { useMemo } from 'react';

import { dsmGet, dsmU1Endpoint } from '../api';
import { useDsmResource } from './useDsmResource';

/** 한 사건의 신호. **서버가 정한 이름을 그대로 쓴다.** */
export interface QueueFieldSignal {
  event_id: number;
  reply_total: number;
  /** 종류를 달고 온 회신 수. 0이면 이 사건은 **분류를 못 한 것**이다. */
  typed_total: number;
  support_requested: boolean;
  support_text: string;
  action_done: boolean;
  action_done_text: string;
  last_text: string;
  last_author: string;
}

export interface QueueFieldSignals {
  asked: number;
  read: number;
  reply_total: number;
  /** 거짓이면 「데이터 없음」이 아니라 **배선 대기**다. */
  wired: boolean;
  typed_total: number;
  support_count: number;
  action_done_count: number;
  signals: QueueFieldSignal[];
  max_event_ids: number;
}

/** 큐와 같은 주기로 묻는다 — 배지가 카드보다 늦으면 두 칸이 다른 말을 한다. */
const REFRESH_MS = 15_000;

export interface UseQueueSignalsResult {
  /** 사건 번호 → 신호. 없는 번호는 **없는 채로** 둔다(지어내지 않는다). */
  byEvent: Map<number, QueueFieldSignal>;
  /** 지원 요청이 붙은 사건들 — 큐 머리의 수. */
  supportCount: number;
  /** 조치 완료가 온 사건들. 종결 확인 카드가 이 목록을 그린다. */
  doneSignals: QueueFieldSignal[];
  /** 배선이 섰는가. 거짓이면 화면이 「배선 대기」를 적는다. */
  wired: boolean;
  /** 한 번이라도 답을 받았는가. 거짓이면 아직 아무 말도 하지 않는다. */
  loaded: boolean;
}

export function useQueueSignals(eventIds: number[]): UseQueueSignalsResult {
  //: 물을 번호를 **한 문자열로** 만든다. 배열을 의존성에 그대로 넣으면 렌더마다
  //: 새 배열이라 주기 갱신이 매 렌더 다시 걸린다.
  const key = useMemo(() => eventIds.join(','), [eventIds]);

  const resource = useDsmResource<QueueFieldSignals>(
    () =>
      dsmGet<QueueFieldSignals>(dsmU1Endpoint.queueFieldSignals, {
        event_ids: key,
      }),
    [key],
    { refreshMs: REFRESH_MS, enabled: key.length > 0 },
  );

  const data = resource.data;

  const byEvent = useMemo(() => {
    const map = new Map<number, QueueFieldSignal>();
    for (const row of data?.signals ?? []) map.set(row.event_id, row);
    return map;
  }, [data]);

  const doneSignals = useMemo(
    () => (data?.signals ?? []).filter((s) => s.action_done),
    [data],
  );

  return {
    byEvent,
    supportCount: data?.support_count ?? 0,
    doneSignals,
    wired: Boolean(data?.wired),
    loaded: resource.state === 'data' || resource.state === 'empty',
  };
}
