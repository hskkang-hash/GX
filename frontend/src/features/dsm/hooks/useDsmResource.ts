/**
 * 한 번 부르고 **5상태 중 하나로** 끝난다 (F-09).
 *
 * ★ 왜 훅 하나로 모으나: 화면 셋이 각자 로딩·오류를 다루면 **셋이 어긋난다.**
 *   어긋난 쪽은 대개 오류 처리이고, 오류 처리가 어긋나면 그 화면만 조용히
 *   「성공」으로 그린다 — 우리가 이미 한 번 만난 상태다 (D-349 착시 ⑧).
 *
 * ★ `empty` 는 **호출한 쪽이 정한다.** 「0건」의 뜻은 자료마다 다르다 —
 *   이벤트 0건은 평온이고 패널 0건은 설정 누락이다. 여기서 한 뜻으로 정하지 않는다.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { DsmApiError } from '../api';
import type { WidgetState } from '../types';

interface Options<T> {
  /** 성공한 값이 「빈 것」인가. 주지 않으면 빈 상태를 쓰지 않는다. */
  isEmpty?: (value: T) => boolean;
  /** 자동 갱신 간격(ms). 주면 **부분 갱신**한다 — 스켈레톤을 다시 그리지 않는다. */
  refreshMs?: number;
  /** 거짓이면 부르지 않는다 (경로 파라미터가 아직 없을 때). */
  enabled?: boolean;
}

export interface Resource<T> {
  state: WidgetState;
  data: T | null;
  /**
   * 왜 실패했나 — **관리자·개발자 자리의 값이다.** 화면은 이 값을 그리지 않는다.
   *
   * ⚠ [P-78 · 2026-09-06 턴 H] 이 자리에는 서버 원문도 axios 원문도 들어온다.
   *   종전에는 `StateBoundary` 가 이것을 사용자 자리에 그대로 그렸고, 여섯 화면에서
   *   「Network Error」가 사람의 자리에 떴다. 이제 그 값은 콘솔로만 간다.
   */
  reason: string;
  /**
   * 실패의 **상태 코드**. 사전 문구가 여기서 갈린다 —
   * 응답이 없었나(0) · 늦었나(504) · 서버가 답은 했나(5xx) · 권한인가(401·403).
   * 성공했으면 0 이다.
   */
  status: number;
  reload: () => void;
  /** 마지막으로 성공한 시각. 「언제 것인가」가 없는 화면은 낡은 줄을 모른다. */
  loadedAt: Date | null;
}

export function useDsmResource<T>(
  fetcher: () => Promise<T>,
  deps: unknown[],
  options: Options<T> = {},
): Resource<T> {
  const { isEmpty, refreshMs, enabled = true } = options;

  const [state, setState] = useState<WidgetState>(enabled ? 'loading' : 'empty');
  const [data, setData] = useState<T | null>(null);
  const [reason, setReason] = useState('');
  const [status, setStatus] = useState(0);
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);

  // 값을 한 번이라도 받았으면 갱신 때 스켈레톤으로 돌아가지 않는다 (DA-03 §4-5).
  const hasValue = useRef(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(() => setTick((n) => n + 1), []);

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    if (!hasValue.current) setState('loading');

    fetcherRef
      .current()
      .then((value) => {
        if (!alive) return;
        hasValue.current = true;
        setData(value);
        setReason('');
        setStatus(0);
        setLoadedAt(new Date());
        setState(isEmpty && isEmpty(value) ? 'empty' : 'data');
      })
      .catch((err: unknown) => {
        if (!alive) return;
        const status = err instanceof DsmApiError ? err.status : 0;
        const message = err instanceof Error ? err.message : String(err);
        // ★ 403 은 오류가 아니라 **권한없음**이다. 한 칸에 두면 운영자가
        //   「고장」과 「내 권한이 아님」을 구별하지 못한다 (DA-03 §2-5).
        setState(status === 403 || status === 401 ? 'forbidden' : 'error');
        setReason(message);
        setStatus(status);
      });

    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, enabled, ...deps]);

  useEffect(() => {
    if (!refreshMs || !enabled) return;
    const id = setInterval(reload, refreshMs);
    return () => clearInterval(id);
  }, [refreshMs, enabled, reload]);

  return { state, data, reason, status, reload, loadedAt };
}
