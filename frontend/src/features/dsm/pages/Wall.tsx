/**
 * UX-16 **월 모드** — 관제실 대형 화면. 마우스가 없고, 사람이 3m 밖에 서 있다.
 *
 * 무엇이 문제였나 [대장 실측 2026-09-24]
 * -------------------------------------
 * 관제실 대형 화면에는 마우스가 없는데 지금 화면은 데스크톱 전용이다.
 * 그래서 이 화면의 규약은 셋이다: **최소 글자 24 · 자동 갱신 · 마우스 없는 조작.**
 *
 * ★ **멈춘 화면은 「사건이 없다」와 구별되지 않는다.** 이것이 이 화면에서 가장
 *   위험한 고장이다 — 밤새 얼어 있는 화면은 평온한 화면과 똑같이 생겼다. 그래서
 *   머리 한 줄이 **자동 갱신 중**과 **마지막 갱신 N분 전**을 스스로 말하고, 갱신이
 *   실패하면 그 사실을 크게 적는다. 낡은 자료는 지우지 않는다 — 낡았다고 말할 뿐이다.
 *
 * ★ **글자 크기를 컴포넌트 라이브러리에 맡기지 않았다.** 이 화면은 일부러 평범한
 *   상자와 글자로만 짰다. 라이브러리 기본값은 14 이고, 그 14 는 어느 구석에서
 *   조용히 되살아난다 — 3m 밖에서는 없는 글자다. 여기 적힌 크기가 곧 화면의 크기다.
 *   판정기 `verify_wall_keys.py` 가 이 파일의 크기 선언을 전부 세어 24 미만을 막는다.
 *
 * ★ **한 칸이 죽어도 나머지가 산다.** 세 칸은 서로 다른 문을 부르고 서로 다른
 *   자원(`useDsmResource`)을 갖는다. 카메라 상태 문은 이번 턴에 다른 차선이 내는
 *   문이라 병합 전에는 없다 — 없으면 그 칸만 「카메라 상태를 불러오지 못했습니다」로
 *   말하고 지도와 큐는 계속 돈다.
 *
 * ⚠ **로그인 세션 12시간은 이 화면이 못 고친다.** 토큰 수명은 인증 쪽(§0.4 금지구역)에
 *   있고, 여기서 고칠 수 있는 자리가 아니다. 이 화면이 할 수 있는 일은 세션이 끊겼을
 *   때 **그 사실을 크게 말하는 것**뿐이고, 그것은 아래 권한 갈래가 한다.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { CSSProperties, ReactNode } from 'react';

import { dsmEndpoint, dsmGet } from '../api';
import { CAMERA_PULSE_PATH, useCameraPulse } from '../hooks/useCameraPulse';
import { useDsmResource } from '../hooks/useDsmResource';
import { isTypingTarget } from '../hooks/useQueueKeys';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../severity';
import {
  duration,
  FALLBACK_TIER_THRESHOLDS_SEC,
  relative,
  TIER_COLOR,
  tierOf,
} from '../time';
import type { FocusQueue as FocusQueueView, QueueCard } from '../types';
import { hasWallToken, wallGet } from '../wallToken';

/** 20초. 대형 화면은 사람이 손대지 않으므로 **주기가 유일한 생명줄**이다. */
const REFRESH_MS = 20_000;
/** 「마지막 갱신 N분 전」이 스스로 자라야 한다 — 안 자라면 그 줄이 거짓말을 한다. */
const TICK_MS = 5_000;
/** 한 화면에 들어가는 줄 수. 넘는 것은 **몇 장이 더 있다고 적는다.** */
const QUEUE_ROWS = 8;
const PULSE_ROWS = 10;

const INK = '#e8ecf1';
const DIM = '#93a1b0';
const LINE = '#243040';

const SHELL: CSSProperties = {
  minHeight: '100vh',
  background: '#0b0f14',
  color: INK,
  padding: 24,
  fontSize: 24,
  lineHeight: 1.35,
  boxSizing: 'border-box',
};

const PANEL: CSSProperties = {
  background: '#131a23',
  border: `1px solid ${LINE}`,
  borderRadius: 10,
  padding: 20,
  minWidth: 0,
  overflow: 'hidden',
};

const PANEL_TITLE: CSSProperties = {
  fontSize: 28,
  fontWeight: 700,
  marginBottom: 12,
  color: INK,
};

const DIM_LINE: CSSProperties = { fontSize: 24, color: DIM };

const ROW: CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 16,
  padding: '10px 0',
  borderTop: `1px solid ${LINE}`,
  minWidth: 0,
};

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={PANEL}>
      <div style={PANEL_TITLE}>{title}</div>
      {children}
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
 * 지도 — **바깥 지도를 부르지 않는다.**
 *
 * 왜: 이 저장소의 지도 컴포넌트는 카카오·구글 열쇠를 요구하고, 열쇠가 없거나
 * 사설망이 막히면 **아무 말 없이 빈 사각형**이 된다. 빈 사각형은 「사건이 없다」와
 * 구별되지 않는다 — 이 화면이 가장 피해야 할 모양이다. 그래서 좌표를 우리 손으로
 * 찍는다: 바깥으로 나가는 요청이 0건이고, 좌표가 없으면 없다고 적는다.
 * ⚠ 이것은 실제 지도가 아니라 **좌표의 상대 위치**다. 배경 지도가 필요하면
 *   조율자가 열쇠와 함께 배선한다.
 * ═══════════════════════════════════════════════════════════════════════════ */
function Scatter({ cards, broken }: { cards: QueueCard[]; broken: boolean }) {
  const points = cards
    .map((c) => ({ card: c, lat: c.lat, lng: c.lng }))
    .filter((p): p is { card: QueueCard; lat: number; lng: number } =>
      typeof p.lat === 'number' && typeof p.lng === 'number' &&
      Number.isFinite(p.lat) && Number.isFinite(p.lng),
    );

  if (points.length === 0) {
    // ★ **못 가져온 것과 없는 것은 다른 사실이다.** 큐가 실패한 채로 「위치가
    //   없습니다」라고 적으면 그 문장은 「평온하다」로 읽힌다 — 이 화면이 가장
    //   피해야 할 모양이고, 이 파일의 머리말이 처음부터 그것을 적어 두었다.
    return (
      <div style={DIM_LINE}>
        {broken
          ? '지도에 표시할 위치를 불러오지 못했습니다.'
          : '지도에 표시할 위치가 없습니다.'}
      </div>
    );
  }

  const lats = points.map((p) => p.lat);
  const lngs = points.map((p) => p.lng);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLng = Math.min(...lngs);
  const maxLng = Math.max(...lngs);
  const spanLat = maxLat - minLat || 0.01;
  const spanLng = maxLng - minLng || 0.01;

  const x = (lng: number) => 8 + ((lng - minLng) / spanLng) * 84;
  // 위도는 위가 큰 값이라 뒤집는다. 안 뒤집으면 남북이 거꾸로 그려진다.
  const y = (lat: number) => 92 - ((lat - minLat) / spanLat) * 84;

  return (
    <div>
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ width: '100%', height: 260, background: '#0d141c', borderRadius: 8 }}
        role="img"
        aria-label="위치"
      >
        <rect x="1" y="1" width="98" height="98" fill="none" stroke={LINE} strokeWidth="0.4" />
        {points.map((p) => (
          <circle
            key={p.card.event_id}
            cx={x(p.lng)}
            cy={y(p.lat)}
            r={p.card.severity === 'critical' ? 2.6 : 1.8}
            fill={SEVERITY_COLOR[p.card.severity] === 'red' ? '#ff4d4f' : '#8fb4ff'}
            opacity="0.9"
          />
        ))}
      </svg>
      <div style={{ ...DIM_LINE, marginTop: 10 }}>
        위치를 아는 카드 {points.length}장 · 전체 {cards.length}장
      </div>
    </div>
  );
}

export default function Wall() {
  const [now, setNow] = useState(() => Date.now());

  /*
   * ★ 이 화면은 **두 가지 방법으로 열린다** (P-74 · 턴 G).
   *
   *   ㉠ 월 표시 토큰 — 세션을 세우지 않는다. 그래서 이 화면을 켜도 관제요원의
   *      자리 화면이 죽지 않는다. 이 제품은 동시 접속이 하나이고, 그것은 설정이
   *      아니라 자료구조라 여기서 고칠 수 있는 자리가 아니다.
   *   ㉡ 로그인 세션 — 종전 그대로. 자리에 앉은 사람이 이 화면을 잠깐 볼 때다.
   *
   * ⚠ 두 자격증명을 **함께** 실으면 서버가 거절한다. 그래서 갈래를 부르는 자리에서
   *   가른다 — 화면 안에서 섞이지 않는다.
   */
  const wallMode = useMemo(() => hasWallToken(), []);

  const fetchQueue = useCallback(
    () =>
      wallMode
        ? wallGet<FocusQueueView>(dsmEndpoint.eventsQueue, { limit: 200 })
        : dsmGet<FocusQueueView>(dsmEndpoint.eventsQueue, { limit: 200 }),
    [wallMode],
  );
  const fetchPulse = useCallback(
    () =>
      wallMode
        ? wallGet<unknown>(CAMERA_PULSE_PATH)
        : dsmGet<unknown>(CAMERA_PULSE_PATH),
    [wallMode],
  );

  const queue = useDsmResource<FocusQueueView>(fetchQueue, [fetchQueue], {
    refreshMs: REFRESH_MS,
  });
  const pulse = useCameraPulse(REFRESH_MS, fetchPulse);

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, []);

  // 마우스가 없는 화면이다. 있는 조작은 **다시 시도** 하나뿐이고 키로 든다.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => {
      if (isTypingTarget(ev.target)) return;
      if (ev.ctrlKey || ev.altKey || ev.metaKey) return;
      const slot = ev.code || '';
      const letter = (ev.key || '').toLowerCase();
      if (slot === 'KeyR' || (!slot && letter === 'r')) {
        queue.reload();
        pulse.reload();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [queue.reload, pulse.reload]);

  const data = queue.data;
  const cards = useMemo<QueueCard[]>(
    () => (data?.focus ? [data.focus, ...(data.queue ?? [])] : [...(data?.queue ?? [])]),
    [data],
  );
  const thresholds = data?.tier_thresholds_sec ?? [...FALLBACK_TIER_THRESHOLDS_SEC];

  const stale = queue.state === 'error';
  const noRight = queue.state === 'forbidden';
  /** 큐를 **못 가져왔다**. 「0건」과 절대 같은 그림이 되면 안 되는 상태다. */
  const queueBroken = stale || noRight;
  const shown = cards.slice(0, QUEUE_ROWS);
  const hidden = Math.max(cards.length - shown.length, 0);

  const pulseRows = pulse.data?.rows ?? [];
  const pulseShown = pulseRows.slice(0, PULSE_ROWS);
  const pulseBroken = pulse.state === 'error' || pulse.state === 'forbidden' ||
    (pulse.state === 'data' && pulse.data?.understood === false);

  return (
    <div style={SHELL}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          gap: 24,
          flexWrap: 'wrap',
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: 40, fontWeight: 800 }}>월 모드</div>
        <div style={{ fontSize: 28, color: DIM, textAlign: 'right' }}>
          {/*
            ★ 이 화면이 **무엇으로 열렸는지**를 화면이 스스로 말한다. 두 방법은
              겉이 똑같고, 그래서 「자리 화면이 왜 죽었나」를 나중에 아무도 못 가린다.
          */}
          <span>{wallMode ? '월 표시 토큰으로 열림' : '로그인 세션으로 열림'}</span>
          <span> · </span>
          <span>자동 갱신 중</span>
          <span> · </span>
          <span>
            마지막 갱신{' '}
            {queue.loadedAt ? relative(queue.loadedAt, new Date(now)) : '아직 없음'}
          </span>
        </div>
      </header>

      {noRight ? (
        <div
          style={{
            fontSize: 32,
            color: '#ffd666',
            border: '1px solid #7a5b00',
            background: '#241d05',
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
          }}
        >
          {wallMode
            ? '월 표시 토큰이 만료되었거나 회수되었습니다. 관리자에게 새 토큰을 받으십시오.'
            : '이 항목에 대한 권한이 없습니다. 다시 로그인해 주십시오.'}
        </div>
      ) : null}

      {stale ? (
        <div
          style={{
            fontSize: 32,
            color: '#ff7875',
            border: '1px solid #791a1a',
            background: '#2a1113',
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
          }}
        >
          불러오지 못했습니다. 아래는 마지막으로 받은 내용입니다.
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1.3fr) minmax(0, 1fr)',
          gap: 16,
          alignItems: 'start',
        }}
      >
        <Panel title="지도">
          <Scatter
            cards={cards}
            broken={queueBroken && cards.length === 0}
          />
        </Panel>

        <Panel title="지금 처리할 것">
          {queue.state === 'loading' ? <div style={DIM_LINE}>불러오는 중입니다.</div> : null}
          {/*
            ★ **여기가 이 화면에서 가장 위험한 두 줄이었다.** 종전 조건은
              「로딩이 아니고 카드가 0장」이었다. 첫 호출이 실패하면 카드는 0장이고,
              그래서 화면은 **「평온합니다」**라고 적었다 — 못 가져온 밤에.
              머리말이 처음부터 금지한 그 모양을 정작 이 칸이 하고 있었다.
              이제 「0건」은 **가져왔을 때만** 말한다.
          */}
          {queueBroken && cards.length === 0 ? (
            <div style={DIM_LINE}>지금 처리할 것을 불러오지 못했습니다.</div>
          ) : null}
          {!queueBroken && queue.state !== 'loading' && cards.length === 0 ? (
            <div style={DIM_LINE}>지금 열려 있는 이벤트가 없습니다 — 평온합니다.</div>
          ) : null}
          {shown.map((card) => {
            const elapsed =
              card.closed_at || card.elapsed_seconds === null
                ? card.elapsed_seconds
                : Math.max(
                    0,
                    Math.round((now - new Date(card.occurred_at).getTime()) / 1000),
                  );
            const tier = tierOf(elapsed, thresholds);
            return (
              <div key={card.event_id} style={ROW}>
                <div style={{ flex: '1 1 auto', minWidth: 0 }}>
                  <div style={{ fontSize: 28, fontWeight: 700 }}>
                    <span style={{ color: card.severity === 'critical' ? '#ff4d4f' : INK }}>
                      {SEVERITY_ICON[card.severity] ?? '•'}{' '}
                      {labelOf(SEVERITY_LABEL, card.severity)}
                    </span>
                    <span> · </span>
                    <span>{labelOf(EVENT_TYPE_LABEL, card.event_type)}</span>
                    {card.count > 1 ? <span> ×{card.count}</span> : null}
                  </div>
                  <div
                    style={{
                      fontSize: 24,
                      color: DIM,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {card.stream_monitor_name || '이름 없는 카메라'} ·{' '}
                    {labelOf(RESPONSE_STATE_LABEL, card.response_state)}
                  </div>
                </div>
                <div
                  style={{
                    fontSize: 40,
                    fontWeight: 800,
                    color: TIER_COLOR[Math.min(tier, TIER_COLOR.length - 1)],
                    whiteSpace: 'nowrap',
                  }}
                >
                  {duration(elapsed)}
                </div>
              </div>
            );
          })}
          {hidden > 0 ? (
            <div style={{ ...DIM_LINE, paddingTop: 12 }}>그 밖 {hidden}장</div>
          ) : null}
        </Panel>

        <Panel title="카메라 상태">
          {pulseBroken ? (
            <div style={DIM_LINE}>카메라 상태를 불러오지 못했습니다.</div>
          ) : null}
          {!pulseBroken && pulse.state === 'loading' ? (
            <div style={DIM_LINE}>불러오는 중입니다.</div>
          ) : null}
          {!pulseBroken &&
            pulseShown.map((row) => (
              <div key={row.key} style={ROW}>
                <div
                  style={{
                    flex: '1 1 auto',
                    minWidth: 0,
                    fontSize: 24,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {row.name}
                </div>
                <div
                  style={{
                    fontSize: 24,
                    whiteSpace: 'nowrap',
                    color: row.alive === false ? '#ff4d4f' : DIM,
                  }}
                >
                  {row.alive === false ? '응답 없음' : null}
                  {row.alive !== false && row.lastSeenAt
                    ? `마지막 응답 ${relative(row.lastSeenAt, new Date(now))}`
                    : null}
                  {row.alive !== false && !row.lastSeenAt ? '아직 없음' : null}
                </div>
              </div>
            ))}
          {!pulseBroken && pulse.state !== 'loading' && pulseRows.length === 0 ? (
            <div style={DIM_LINE}>표시할 항목이 없습니다.</div>
          ) : null}
          {!pulseBroken && pulseRows.length > pulseShown.length ? (
            <div style={{ ...DIM_LINE, paddingTop: 12 }}>
              그 밖 {pulseRows.length - pulseShown.length}대
            </div>
          ) : null}
        </Panel>
      </div>

      <div style={{ ...DIM_LINE, marginTop: 16 }}>단축키 R — 다시 시도</div>
    </div>
  );
}
