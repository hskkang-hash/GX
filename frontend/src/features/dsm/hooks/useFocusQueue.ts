/**
 * UX-13 단일 초점 큐의 **자료 + 쓰기**를 한 곳에 모은다 (WO-01 §4.1 U1 소유).
 *
 * 왜 훅으로 뽑았나
 * ----------------
 * `FocusQueuePage` 는 이미 키보드·소리·경보 훅 셋을 부르고 있었다. 쓰기 셋
 * (접수·판정+접수·오탐)을 화면 파일에 손으로 더 얹으면 그 파일이 **자료를 만드는
 * 곳과 그리는 곳**을 함께 지게 된다. 이 훅은 앞쪽(자료 + 쓰기)만 진다 — 그리는
 * 일은 여전히 화면의 것이다.
 *
 * ★ **판정 + 접수를 한 트랜잭션으로 묶는 문**(`POST /events/{id}/review-and-
 *   acknowledge`)은 이번 턴에 새로 열렸다(WO-01 §5 · AC-2). 큐 카드 키 **1** 은
 *   이제 이 문 하나를 부른다 — 종전처럼 접수(`/response`)만 부르지 않는다. 「이
 *   탐지는 진짜다, 그리고 내가 접수한다」가 사람에게는 한 번의 행동이기 때문이고,
 *   두 번 왕복하면 첫 호출만 성공했을 때 반쪽짜리 사건이 화면에 남는다.
 *
 * ★ **이 문은 아직 `dsmEndpoint`(`../api.ts`)에 없다** — 이번 턴에 여러 차선이
 *   그 파일을 함께 건드리므로(끝에 붙이는 관례) 이 파일 안에서 경로를 짓는다.
 *   조율자가 `dsmEndpoint.reviewAndAcknowledge` 로 등재하면 그쪽으로 옮긴다.
 *
 * ★ **오탐은 기존 문을 그대로 쓴다**(`dsmEndpoint.review` · 재사용 · WO-01 §5).
 *   새 계약을 만들지 않는다 — 오탐 사유 3택은 이 화면이 **미리 채우는 값**일
 *   뿐이고, 서버의 `reason` 은 여전히 자유 텍스트다(`copy.ts` 머리말 참조).
 *
 * ★ **토스트를 쓰지 않는다**(UX-25). 성공은 카드의 상태 칸(`response_state` 태그)
 *   이 「접수」 등으로 스스로 보인다 — 그것이 이 제품의 불변("상태는 칸으로")이다.
 *   이 훅은 성공 뒤 `queue.reload()` 만 하고, 소리는 부르는 쪽이 `onActionSuccess`
 *   로 얹는다(소리 음소거 상태는 화면이 들고 있어 훅에 들일 이유가 없다).
 */
import { useCallback, useMemo, useState } from 'react';

import { dsmEndpoint, dsmGet, dsmPostQueryOnce, intentKey } from '../api';
import { userFacingError } from '../copy';
import { useDsmResource } from './useDsmResource';
import { FALLBACK_TIER_THRESHOLDS_SEC } from '../time';
import type { FocusQueue as FocusQueueView, QueueCard } from '../types';

const REFRESH_MS = 15_000;

/** ★ `dsmEndpoint` 에 아직 없는 자리 — 위 머리말 참조. 문자열을 화면 곳곳에 흩지
 *  않기 위해 이 훅 한 곳에만 짓는다. */
function reviewAndAcknowledgePath(eventId: number | string): string {
  return `/api/dsm/events/${eventId}/review-and-acknowledge`;
}

export interface UseFocusQueueOptions {
  /**
   * 쓰기 하나가 성공한 **직후**(재조회 전) 부르는 곁가지 — 화면이 소리를 얹는 자리.
   *
   * ★ [턴 S] **무엇이 성공했는지를 함께 준다.** 소리는 셋 다 같지만 계측은 다르다 —
   *   「사건 1건 처리」의 시계는 **접수에서 멈추고** 오탐에서는 멈추지 않는다.
   *   인자가 없으면 부르는 쪽이 어느 쓰기였는지 짐작해야 하고, 짐작한 계측은 수가 아니다.
   *   값은 `review-ack` · `reject` · `advance:<다음 칸>` 셋이다.
   */
  onActionSuccess?: (what: string) => void;
}

export interface UseFocusQueueResult {
  queue: ReturnType<typeof useDsmResource<FocusQueueView>>;
  /** 초점 하나 + 대기 카드들. **여기서 거르지도 정렬하지도 않는다** — 서버 순서 그대로. */
  cards: QueueCard[];
  focus: QueueCard | null;
  thresholds: number[];
  /** 쓰기 하나가 날아가는 중인가. 셋(접수·판정+접수·오탐)이 **함께** 잠근다 —
   *  두 쓰기가 같은 카드에 동시에 날아가면 둘 중 하나가 남의 결과를 덮는다. */
  acting: boolean;
  actionError: string;
  /** 대응 진행 한 칸(D-399) — 조치 시작·종결처럼 **판정이 필요 없는** 전이. */
  advance: (eventId: number, toState: string) => Promise<void>;
  /** 큐 카드 키 **1** — 판정(확인)+접수를 한 트랜잭션으로(WO-01 §5). */
  reviewAndAcknowledge: (eventId: number) => Promise<void>;
  /** 오탐 판정. `reasonLabel` 은 3택 중 하나(또는 자유 텍스트) — 기존 `/review` 재사용. */
  reject: (eventId: number, reasonLabel: string) => Promise<void>;
}

export function useFocusQueue(options: UseFocusQueueOptions = {}): UseFocusQueueResult {
  const { onActionSuccess } = options;

  const queue = useDsmResource<FocusQueueView>(
    () => dsmGet<FocusQueueView>(dsmEndpoint.eventsQueue, { limit: 200 }),
    [],
    {
      refreshMs: REFRESH_MS,
      isEmpty: (v) => (v?.total_events ?? 0) === 0,
    },
  );

  const data = queue.data;
  const focus = data?.focus ?? null;

  const cards = useMemo<QueueCard[]>(
    () => (focus ? [focus, ...(data?.queue ?? [])] : [...(data?.queue ?? [])]),
    [focus, data],
  );

  const thresholds = data?.tier_thresholds_sec ?? [...FALLBACK_TIER_THRESHOLDS_SEC];

  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState('');

  const advance = useCallback(
    async (eventId: number, toState: string) => {
      setActing(true);
      setActionError('');
      try {
        await dsmPostQueryOnce(
          dsmEndpoint.response(eventId),
          { to_state: toState },
          intentKey(`q.response:${eventId}:${toState}`),
        );
        onActionSuccess?.(`advance:${toState}`);
        queue.reload();
      } catch (err) {
        setActionError(userFacingError('FocusQueue.advance', err, '요청이 처리되지 않았습니다.'));
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess],
  );

  const reviewAndAcknowledge = useCallback(
    async (eventId: number) => {
      setActing(true);
      setActionError('');
      try {
        await dsmPostQueryOnce(
          reviewAndAcknowledgePath(eventId),
          {},
          intentKey(`q.review-ack:${eventId}`),
        );
        onActionSuccess?.('review-ack');
        queue.reload();
      } catch (err) {
        setActionError(
          userFacingError('FocusQueue.reviewAndAcknowledge', err,
            '판정과 접수가 처리되지 않았습니다.'),
        );
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess],
  );

  const reject = useCallback(
    async (eventId: number, reasonLabel: string) => {
      setActing(true);
      setActionError('');
      try {
        await dsmPostQueryOnce(
          dsmEndpoint.review(eventId),
          { verdict: 'rejected', reason: reasonLabel },
          intentKey(`q.review:${eventId}:rejected`),
        );
        onActionSuccess?.('reject');
        queue.reload();
      } catch (err) {
        setActionError(userFacingError('FocusQueue.reject', err, '오탐 판정이 처리되지 않았습니다.'));
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess],
  );

  return { queue, cards, focus, thresholds, acting, actionError, advance, reviewAndAcknowledge, reject };
}
