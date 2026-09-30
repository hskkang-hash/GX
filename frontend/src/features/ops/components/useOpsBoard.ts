/**
 * 보드 하나의 조회 GET 을 들고 있는 작은 갈고리 — 턴 AQ · 차선 N2.
 *
 * 누르는 자리(발급·설치·조치·회전 …)는 성공 뒤 **반드시 `reload()` 를 불러 같은 보드의
 * GET 을 다시 부른다** — 화면이 보여 주는 값은 언제나 서버가 방금 준 값이다(누른 결과를
 * 화면에서 손으로 끼워 넣지 않는다).
 */
import { useCallback, useEffect, useState } from 'react';

import { opsErrorStatus, opsErrorText } from '../api';

export interface OpsBoardState<T> {
  data: T | null;
  error: string | null;
  forbidden: boolean;
  loading: boolean;
  reload: () => Promise<void>;
}

export function useOpsBoard<T>(fetcher: () => Promise<T>): OpsBoardState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const next = await fetcher();
      setData(next);
      setError(null);
    } catch (e) {
      const status = opsErrorStatus(e);
      if (status === 401 || status === 403) {
        setForbidden(true);
      } else {
        setError(opsErrorText(e));
      }
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, error, forbidden, loading, reload };
}

/**
 * 누르는 자리 하나를 감싼다 — 서버 호출 → 성공이면 보드 GET 재조회 → 결과 문장.
 * 실패하면 서버가 준 거절 사유를 그대로 돌려준다(화면에서 판정을 다시 하지 않는다).
 */
export async function runOpsAction(
  call: () => Promise<unknown>,
  reload: () => Promise<void>,
): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    await call();
  } catch (e) {
    return { ok: false, message: opsErrorText(e) };
  }
  await reload();
  return { ok: true };
}
