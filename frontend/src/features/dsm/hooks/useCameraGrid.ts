/**
 * UX-23 카메라 격자 — 값을 부르는 자리 + **자동 순회의 시계** (차선 C2 · 2026-09-05).
 *
 * 왜 훅으로 떼나
 * --------------
 * 이 화면에는 두 개의 시계가 돈다: **갱신**(서버에 다시 묻는다)과 **순회**(보이는
 * 쪽을 넘긴다). 둘을 화면 컴포넌트 안에 같이 두면 렌더마다 타이머가 다시 걸리고,
 * 다시 걸린 타이머는 **순회가 제자리에서 멈추거나 두 배로 빨라지는** 모양으로만
 * 드러난다 — 오류가 아니라 「좀 이상하다」로 보이는 종류의 고장이다.
 *
 * ★ 판정은 서버가 한다. 여기에 **문턱이 하나도 없다** — 「응답 없음」인지는
 *   `alive` 한 칸이 말하고, 그 칸은 `camera_pulse` 의 규칙 하나에서 나온다.
 *   화면이 자기 문턱(예: 5분)을 들면 규칙이 바뀌는 날 화면만 옛말이 되고,
 *   옛말이 된 화면은 조용하다.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';

import { dsmEndpoint, dsmGet } from '../api';
import { useDsmResource } from './useDsmResource';
import type { Resource } from './useDsmResource';

/** 카메라 한 대의 맥박. **이름을 서버가 정한 그대로 쓴다.** */
export interface CameraPulseRow {
  id: number;
  name: string;
  /** 살아 있는가. 거짓이면 화면은 「응답 없음」을 그린다. */
  alive: boolean;
  /**
   * 마지막 응답 시각. `null` 은 **「한 번도 안 왔다」**이지 「0분 전」이 아니다 —
   * 방금 등록한 카메라와 방금 끊긴 카메라를 같은 글자로 그리면 안 된다.
   */
  last_seen_at: string | null;
  /** `null` 이면 위와 같은 이유로 「N분 전」 줄을 그리지 않는다. */
  silent_seconds: number | null;
}

export interface CameraPulseZone {
  zone_id: number;
  zone_name: string;
  /** 「봤는가」. 거짓이면 0건은 「안 걸렸다」가 아니라 「아예 안 봤다」다. */
  judged: boolean;
  total: number;
  never_seen: number;
  silent_camera_ids: number[];
  cluster_camera_ids: number[];
  fires: boolean;
}

export interface CameraPulse {
  now: string;
  rules: {
    pulse_timeout_seconds: number;
    cluster_window_seconds: number;
    cluster_min_cameras: number;
    cluster_min_down: number;
  };
  /** 분모를 함께 받는다 — 「2대」만 보면 전체가 3인지 300인지 모른다. */
  counts: { alive: number; total: number; never_seen: number };
  cameras: CameraPulseRow[];
  cluster: {
    zones_seen: number;
    cameras_seen: number;
    outage_count: number;
    zones: CameraPulseZone[];
  };
}

/** 서버에 다시 묻는 주기. 맥박의 문턱보다 **훨씬 짧다** — 늦게 물으면 늦게 안다. */
export const REFRESH_MS = 15_000;

/** 순회 한 쪽의 머무는 시간. PRD v1.1 UX-23′ 「4×4 · 30초」의 그 30초다. */
export const ROTATE_MS = 30_000;

/** 한 쪽에 그리는 타일 수. PRD v1.1 UX-23′ 「4×4」 — 관제실 화면 한 판의 격자 수다. */
export const PAGE_SIZE = 16;

export interface CameraGridView {
  pulse: Resource<CameraPulse>;
  /** 지금 그릴 타일들. 순회가 꺼져 있으면 첫 쪽에 머문다. */
  page: CameraPulseRow[];
  pageIndex: number;
  pageCount: number;
  rotating: boolean;
  toggleRotate: () => void;
  /** 응답 없는 카메라 수 — **분모와 함께** 쓰라고 counts 도 함께 준다. */
  downCount: number;
  /**
   * 이번 순회 걸음이 **온통 검은 쪽을 건너뛴 것인가** (UX-23′). 검은 칸(무응답
   * 카메라) 자체는 여전히 그 쪽에 그려진다 — 「표시」는 그대로다. 건너뛰는 것은
   * **쪽 전체가 검은 쪽**뿐이다: 그런 쪽만 순회 목록에서 빼서, 자동 순회가
   * 아무것도 안 보이는 화면 앞에 30초씩 머물지 않게 한다. 살아 있는 칸이
   * 하나도 없으면(전부 검다) 건너뛸 쪽이 없다는 뜻이므로 되돌려 전부를 돈다 —
   * 「순회가 멈췄다」와 「볼 것이 없다」를 같은 화면으로 만들지 않기 위해서다.
   */
  skippedAllDeadPages: number;
}

export function useCameraGrid(): CameraGridView {
  const pulse = useDsmResource<CameraPulse>(
    () => dsmGet(dsmEndpoint.cameraPulse),
    [],
    {
      refreshMs: REFRESH_MS,
      // 카메라 0대는 **평온이 아니라 설정 누락**이다 — 빈 상태로 그린다.
      isEmpty: (v) => (v?.cameras?.length ?? 0) === 0,
    },
  );

  // ★ 사람이 켠다. 처음부터 돌면 무엇인가 찾던 사람의 손 밑에서 화면이 넘어간다.
  const [rotating, setRotating] = useState(false);
  const [pageIndex, setPageIndex] = useState(0);

  const cameras = useMemo(() => pulse.data?.cameras ?? [], [pulse.data]);
  const pageCount = Math.max(1, Math.ceil(cameras.length / PAGE_SIZE));

  // 쪽마다 「살아 있는 칸이 하나라도 있는가」— `alive` 는 서버가 정한다(문턱
  // 없음). 순회가 도는 쪽 목록을 여기서 좁힌다: 온통 검은 쪽은 순회에서 뺀다.
  // ★ 전부 검으면(살아 있는 쪽이 하나도 없음) 뺄 수 없다 — 다 빼면 순회할
  //   쪽이 0이 되고, 그것은 「건너뛴다」가 아니라 「순회가 멈춘다」다. 그래서
  //   그때는 전부를 그대로 되돌린다.
  const rotatablePageIndexes = useMemo(() => {
    const withLive: number[] = [];
    for (let i = 0; i < pageCount; i += 1) {
      const start = i * PAGE_SIZE;
      const slice = cameras.slice(start, start + PAGE_SIZE);
      if (slice.some((c) => c.alive)) withLive.push(i);
    }
    return withLive.length > 0
      ? withLive
      : Array.from({ length: pageCount }, (_, i) => i);
  }, [cameras, pageCount]);

  const skippedAllDeadPages = pageCount - rotatablePageIndexes.length;

  // 카메라가 줄면 보고 있던 쪽이 사라진다. 없는 쪽에 머물면 빈 화면이 되고,
  // 빈 화면은 「카메라가 없다」와 구별되지 않는다.
  useEffect(() => {
    setPageIndex((n) => (n >= pageCount ? 0 : n));
  }, [pageCount]);

  useEffect(() => {
    if (!rotating || rotatablePageIndexes.length <= 1) return undefined;
    const id = setInterval(() => {
      setPageIndex((n) => {
        const at = rotatablePageIndexes.indexOf(n);
        const nextAt = (at === -1 ? 0 : at + 1) % rotatablePageIndexes.length;
        return rotatablePageIndexes[nextAt];
      });
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [rotating, rotatablePageIndexes]);

  const toggleRotate = useCallback(() => setRotating((on) => !on), []);

  const page = useMemo(
    () => cameras.slice(pageIndex * PAGE_SIZE, pageIndex * PAGE_SIZE + PAGE_SIZE),
    [cameras, pageIndex],
  );

  // ★ 여기서 다시 세지 않는다 — 서버가 센 수를 쓴다. 화면이 자기 목록으로 세면
  //   상한이 걸린 목록에서 「응답 없음 0대」가 나오고, 그 0은 거짓말이다.
  const counts = pulse.data?.counts;
  const downCount = counts ? counts.total - counts.alive : 0;

  return {
    pulse, page, pageIndex, pageCount, rotating, toggleRotate, downCount,
    skippedAllDeadPages,
  };
}
