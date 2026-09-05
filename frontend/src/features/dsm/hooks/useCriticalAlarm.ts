/**
 * UX-15 **심각만 소리가 난다** — 그리고 묶인 반복은 **한 번만** 운다.
 *
 * 무엇이 이 훅을 만들었나
 * ----------------------
 * 같은 카메라가 3분 사이 7번 울리면 큐 화면은 그것을 카드 **한 장**으로 접는다
 * (`count` = 7 · `member_event_ids` 7개). 소리를 이벤트마다 울리면 화면은 한 장인데
 * 귀는 일곱 번 맞는다 — 그러면 관제요원이 소리를 끄고, **꺼진 소리는 없는 소리보다
 * 나쁘다.** 그래서 소리도 화면과 같은 단위로 운다: **카드 한 장에 한 번.**
 *
 * 문지기 둘
 * ---------
 *   ① **등급** — `critical` 에서만 운다. 경계·주의는 소리를 갖지 않는다.
 *      (`critical` 은 계약 스키마 값이다 · 화면 표시 이름은 「심각」이고 따로 산다.)
 *   ② **이미 들은 것** — 카드가 데리고 있는 원본 id 를 전부 기억한다. 묶음이 8번째로
 *      늘어 카드가 다시 그려져도, 그 id 들 중 하나라도 아는 것이면 **다시 울지 않는다.**
 *
 * 첫 화면은 조용하다
 * -----------------
 * 화면을 처음 열면 이미 쌓여 있던 심각 스무 건이 한꺼번에 운다 — 그것은 알림이
 * 아니라 소음이다. 그래서 **첫 응답은 기억만 하고 울지 않는다**(`primed`).
 *
 * 기억은 화면만큼만 산다
 * ---------------------
 * 8시간이면 기억이 무한정 자란다. 그래서 매번 **지금 응답에 있는 id 만 남긴다** —
 * 큐를 떠난 사건은 잊는다. 떠났다 돌아온 사건은 다시 우는데, 그것이 맞다:
 * 다시 큐에 오른 심각은 다시 새 사건이다.
 */
import { useEffect, useRef } from 'react';

import { tierOf } from '../time';
import type { QueueCard } from '../types';
import type { AlertSound } from './useAlertSound';

/** 계약 스키마 값이다. 화면 표시 이름(「심각」)과 **다른 것**이고, 바꾸면 계약이 바뀐다. */
const CRITICAL = 'critical';

interface Options {
  /** 초점 하나 + 대기 카드들을 **한 줄로 이어 준다.** 이 훅은 거르지 않는다. */
  cards: QueueCard[];
  /** 서버가 준 문턱 표. 화면이 자기 표를 들면 서버 통계와 소리가 갈린다. */
  thresholds: number[];
  play: (name: AlertSound) => void;
  /** 자료가 한 번이라도 왔는가. 거짓이면 아무것도 기억하지 않는다. */
  ready: boolean;
}

export function useCriticalAlarm({ cards, thresholds, play, ready }: Options): void {
  /** 이미 울린 원본 id. 카드가 아니라 **원본 id** 로 기억한다 — 묶음이 자라도 같은 사건이다. */
  const heardRef = useRef<Set<number>>(new Set());
  /** 문턱을 넘었다고 이미 울린 카드. 넘은 뒤로는 계속 넘어 있으므로 따로 기억한다. */
  const overdueRef = useRef<Set<number>>(new Set());
  const primedRef = useRef(false);
  const playRef = useRef(play);
  playRef.current = play;

  useEffect(() => {
    if (!ready) return;

    const heard = heardRef.current;
    const overdue = overdueRef.current;
    const primed = primedRef.current;

    const liveIds = new Set<number>();
    const liveCards = new Set<number>();

    for (const card of cards) {
      const ids = [card.event_id, ...(card.member_event_ids ?? [])];
      for (const id of ids) liveIds.add(id);
      liveCards.add(card.event_id);

      // ① 등급 문지기 — 심각이 아니면 여기서 끝이다. 소리도, 기억도 없다.
      if (card.severity !== CRITICAL) continue;

      // ② 묶음 문지기 — 아는 id 가 하나라도 있으면 **이 카드는 이미 들은 것**이다.
      //    카드 하나에 한 번. `count` 가 7이어도 소리는 1회다.
      const known = ids.some((id) => heard.has(id));
      if (!known) {
        if (primed) playRef.current('newCritical');
        for (const id of ids) heard.add(id);
      }

      // 가장 오래 기다린 단계(문턱 표의 마지막 칸)를 넘은 심각은 한 번 더 운다.
      // 닫힌 사건은 시계가 멈췄으므로 울지 않는다.
      const tier = tierOf(card.elapsed_seconds, thresholds);
      const last = thresholds.length;
      if (!card.closed_at && last > 0 && tier >= last && !overdue.has(card.event_id)) {
        if (primed) playRef.current('overdueCritical');
        overdue.add(card.event_id);
      }
    }

    // 기억을 지금 화면만큼으로 줄인다 — 큐를 떠난 것은 잊는다.
    for (const id of Array.from(heard)) if (!liveIds.has(id)) heard.delete(id);
    for (const id of Array.from(overdue)) if (!liveCards.has(id)) overdue.delete(id);

    primedRef.current = true;
  }, [cards, thresholds, ready]);
}
