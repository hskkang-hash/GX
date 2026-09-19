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
  /**
   * ★★ [턴 W · 차선 U1 · P-188] **거절의 HTTP 상태.** 0 이면 거절이 없었다.
   *
   * 왜 필요한가 [실측 · `test_u1_queue_card_actions.py` 가 잡았다]: `allowed_next` 는
   * 「갈 수 있는 곳」이지 「지금 그냥 눌러도 되는 곳」이 아니다. 종결된 사건의
   * `allowed_next` 에는 **되돌림**(`closed → in_progress`)이 들어 있고, 그 칸은
   * **사유가 있어야**(400) 열리며 **관제팀장만**(403) 할 수 있다
   * (`kernels/k1_event/response_flow.py:100·154`).
   *
   * 즉 큐 카드가 `allowed_next` 만 보고 그린 단추 중 하나는 **누르면 반드시 실패**했다.
   * 커널은 이 셋을 **다른 상태코드**로 낸다(D-290): 409 는 「그 길은 없다」, 400 은
   * 「사유를 채워 다시」, 403 은 「팀장이 해야」. 화면은 그 셋에 **다른 행동**을 해야
   * 하므로 번호를 그대로 들고 온다 — 화면이 전이표를 따로 드는 것이 아니라,
   * **서버가 방금 한 말**을 읽는 것이다.
   */
  actionStatus: number;
  /** 어느 카드의 어느 칸이 거절당했나. 거절을 **그 카드 옆에** 적기 위한 것. */
  actionOn: { eventId: number; toState: string } | null;
  /** 거절 한 줄을 지운다 — 사람이 다시 누를 때 앞의 거절이 남아 있으면 거짓말이다. */
  clearActionError: () => void;
  /**
   * 대응 진행 한 칸(D-399) — 조치 시작·종결처럼 **판정이 필요 없는** 전이.
   *
   * ★ `reason` 은 **되돌림에만** 필요하다. 화면은 그것을 미리 알지 못하고(전이표를
   *   들지 않으므로) 알 필요도 없다 — 빈 채로 보내 보고, 서버가 400 으로 「사유를
   *   채워 다시」라고 하면 그때 받아서 다시 보낸다.
   */
  advance: (eventId: number, toState: string, reason?: string) => Promise<void>;
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
  const [actionStatus, setActionStatus] = useState(0);
  const [actionOn, setActionOn] =
    useState<{ eventId: number; toState: string } | null>(null);

  /** 거절의 HTTP 상태를 꺼낸다. 없으면 0 — **모르는 것을 0 이 아닌 수로 적지 않는다.** */
  const statusOf = (err: unknown): number =>
    err && typeof err === 'object' && 'status' in err
      ? Number((err as { status?: number }).status ?? 0) || 0
      : 0;

  const clearActionError = useCallback(() => {
    setActionError('');
    setActionStatus(0);
    setActionOn(null);
  }, []);

  const advance = useCallback(
    async (eventId: number, toState: string, reason = '') => {
      setActing(true);
      clearActionError();
      try {
        await dsmPostQueryOnce(
          dsmEndpoint.response(eventId),
          //: ★ 사유는 **있을 때만** 싣는다. 빈 문자열을 늘 보내면 서버의 「사유가
          //:   비었다」 갈래를 화면이 지워 버리고, 지워진 갈래는 아무도 못 본다.
          reason.trim() ? { to_state: toState, reason: reason.trim() } : { to_state: toState },
          //: 사유가 붙으면 **다른 요청**이다 — 같은 멱등 키를 쓰면 사유 없이 거절당한
          //: 앞 요청의 답이 되돌아온다(「사유를 채워 다시」가 영원히 반복된다).
          intentKey(
            reason.trim()
              ? `q.response:${eventId}:${toState}:with-reason`
              : `q.response:${eventId}:${toState}`,
          ),
        );
        onActionSuccess?.(`advance:${toState}`);
        queue.reload();
      } catch (err) {
        setActionError(userFacingError('FocusQueue.advance', err, '요청이 처리되지 않았습니다.'));
        setActionStatus(statusOf(err));
        setActionOn({ eventId, toState });
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess, clearActionError],
  );

  const reviewAndAcknowledge = useCallback(
    async (eventId: number) => {
      setActing(true);
      clearActionError();
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
        setActionStatus(statusOf(err));
        setActionOn({ eventId, toState: 'acknowledged' });
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess, clearActionError],
  );

  const reject = useCallback(
    async (eventId: number, reasonLabel: string) => {
      setActing(true);
      clearActionError();
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
        setActionStatus(statusOf(err));
        setActionOn({ eventId, toState: 'rejected' });
      } finally {
        setActing(false);
      }
    },
    [queue, onActionSuccess, clearActionError],
  );

  return {
    queue, cards, focus, thresholds, acting,
    actionError, actionStatus, actionOn, clearActionError,
    advance, reviewAndAcknowledge, reject,
  };
}
