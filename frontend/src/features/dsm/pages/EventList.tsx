/**
 * 화면 ② **이벤트 목록 + W1 관제 프리셋** — E2E-1 의 가운데 칸 (D-371 ① · 차선 C).
 *
 * ★ 필터는 **서버가 건다.** 목록을 다 받아 화면에서 거르면 두 가지가 동시에 깨진다:
 *     ① 격리 — 화면이 거르기 전의 목록은 이미 브라우저에 와 있다
 *     ② F-05 p95 — 분모가 커질수록 느려지고, 그 느림은 로컬에서 안 보인다
 *   그래서 프리셋 **다섯**(P-120 에서 「전체」가 더해졌다)과 **기간**은 전부
 *   질의로 나간다. 이 파일에는 `rows.filter(...)` 가
 *   한 줄도 없고, 없는 것이 이 화면의 성질이다 — 있으면 페이지 밖 이벤트가
 *   **없는 것이 된다**(온보딩 U2 #2 가 막혀 있던 정확한 이유).
 *
 * ★ 프리셋은 **주소에 산다**(`?preset=`). 화면 안의 상태로만 두면 「지금 무엇을 보고
 *   있나」를 주소가 말하지 못하고, 교대 인계에서 링크를 건네줄 수 없다. 검수 촬영도
 *   그 주소로 직접 들어온다.
 *
 * ★ 「0건」과 「못 가져왔다」를 같은 그림으로 그리지 않는다 (DA-03 §2-5 규칙 1).
 *   `StateBoundary` 가 그 둘을 가른다 — 이 화면이 직접 그리지 않는 이유다.
 *
 * ★ 등급은 색 + 아이콘 + 라벨 셋으로 낸다. 색만 쓰면 색각 이상이 못 읽는다 (DA-03 §2-2).
 */
import {
  Alert, Badge, Button, Card, Col, DatePicker, Input, Modal, Popover, Row, Segmented,
  Select, Space, Table, Tag, Typography, message,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Main } from 'rj-core';

import {
  dsmDelete, dsmEndpoint, dsmGet, dsmPostQueryOnce, dsmU24StatsEndpoint, intentKey,
} from '../api';
import { linkStatusBadge, linkStatusLabel, userFacingError } from '../copy';
import { VerdictBadge } from '../components/ResponseSteps';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { useDetectionPing } from '../hooks/useDetectionPing';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  SYSTEM_EVENT_TYPES,
} from '../severity';
import { absolute, stamp, TIMEZONE_NOTE } from '../time';
import type { EventRow, EventSummary, UpperReportFlags } from '../types';

const { Text, Title } = Typography;

const REFRESH_MS = 15_000;
const PAGE_SIZE = 50;

/** 「지난 12시간」의 12. 요약 한 줄과 목록이 **같은 수**를 써야 두 줄이 같은 창을 말한다. */
const RECENT_HOURS = 12;

/**
 * W1 프리셋 — 넷이었고 **다섯이 되었다** (P-13 · P-120).
 *
 * `query` 가 **그대로 서버로 나간다.** 화면이 뒤에서 한 번 더 거르지 않는다 —
 * 그 한 줄이 생기는 순간 「서버 필터」라는 말이 거짓이 된다.
 *
 * ⚠ `system` 은 목록에 더해 **카드 하나**를 더 단다(연계 상태). 그 사유는 아래
 *   `SYSTEM_NOTE` 에 적혀 있다 — 이벤트와 「지금 이 순간의 신호」는 다른 것이다.
 */
type PresetKey = 'all' | 'unhandled' | 'recent' | 'mine' | 'system';

interface PresetDef {
  key: PresetKey;
  label: string;
  /** 그 프리셋이 켜졌을 때 화면에 뜨는 **그 화면에만 있는 글자** (검수 촬영의 단언 대상). */
  headline: string;
  why: string;
  query: Record<string, string | number | boolean>;
}

/**
 * ★ [UX-20 · 2026-09-26] **안내 줄을 사용자 언어로 다시 썼다.**
 *
 *   앞판의 `headline`·`why` 에는 「W1 프리셋」 같은 우리 절 이름과 서버 인자
 *   (`response_state=occurred` · `since` · `until` · `mine=true`) · 감사 채널 이름이
 *   백틱째로 들어 있었다. 백틱은 렌더되지 않고 **그대로 화면에 보인다.**
 *
 *   무엇을 어떻게 걸렀는가는 사실이지만 **당직자의 말이 아니다.** 그 사유는 여기
 *   주석과 대장의 자리에 남기고, 화면에는 「지금 무엇을 보고 있는가」만 남긴다
 *   (GX-COPY §0 · §4).
 *
 *   ⚠ 거른 쪽이 서버라는 사실 자체는 **버리지 않는다** — 「상한 밖의 것도 빠지지
 *     않습니다」는 사용자에게 뜻이 있는 문장이라 사용자 언어로 남겼다.
 *
 *   (내부 사실 · 화면에 적지 않는다)
 *     unhandled : `response_state=occurred` 를 서버로 보낸다
 *     recent    : `since` 와 `until` 을 **둘 다** 보낸다 — 여는 쪽만 보내면
 *                 「12시간 전부터 미래까지」가 된다
 *     mine      : `mine=true` 만 보낸다. 「나」가 누구인지는 서버가 안다.
 *                 ⚠ 내가 **판정**한 것이지 내가 **대응**한 것이 아니다 —
 *                 대응 전이의 행위자는 행이 아니라 감사에 있다
 *     system    : `event_type` 으로 서버가 거른다
 */
const PRESETS: PresetDef[] = [
  /**
   * ★★ [P-120 · UX-27 · 2026-09-10 턴 O] **「전체」가 없었다 — 그래서 종결된 사건은
   *   어느 화면에도 없었다.**
   *
   *   [실측 2026-09-10 · TARGET=http://localhost:8500 · gxseed_u2_manager]
   *   이 테넌트의 이벤트는 22건이고, 그중 **종결(closed) 8건**이다. 프리셋 넷이
   *   각각 서버에서 데려오는 수는 이랬다:
   *
   *       미처리(`response_state=occurred`)          2건 — 종결 0
   *       지난 12시간(`since`/`until`)                0건 — 자료가 7일 전이다
   *       내 담당(`mine=true`)                        0건 — 종결 0
   *       시스템(`event_type=camera_down,…`)          2건 — 종결 0
   *                                       ────────────────────────
   *                                       종결 도달 가능  **0 / 8**
   *
   *   기본은 「미처리」다. 즉 화면을 열면 22건 중 2건이 보이고, **종결된 8건은 어느
   *   프리셋으로도 닿지 않았다.** 대시보드의 「최근 이벤트 10건」에서 밀려나는 순간
   *   그 사건은 이 제품에서 **없는 것**이 된다 — 감사 질문(「12일 03시 14분에 무슨
   *   일이 있었나」)이 1단계에서 막힌 정확한 자리다.
   *
   *   고친 것은 한 칸이다: **거르지 않는 질의**를 하나 세웠다. 화면이 받아서 거르는
   *   것이 아니라, 서버에 「처리 단계로 거르지 말라」고 말하는 것이다 —
   *   그래서 이 프리셋에도 `rows.filter(...)` 는 없다.
   */
  {
    key: 'all',
    label: '전체 보기',
    headline: '전체 — 처리 단계를 가리지 않고 전부',
    why:
      '처리 단계로 거르지 않은 목록입니다. 종결된 사건도 여기에 있습니다. ' +
      '언제 일어난 일인지 알면 아래 기간을 좁혀 보십시오.',
    query: {},
  },
  {
    key: 'unhandled',
    label: '미처리 보기',
    headline: '미처리 — 아직 아무도 손대지 않은 것',
    why:
      '처리 단계가 「미처리」인 이벤트만 서버가 골라 준 목록입니다. ' +
      '화면이 받아서 거른 것이 아니므로, 아래 표에 안 보이는 오래된 건도 빠지지 않습니다.',
    query: { response_state: 'occurred' },
  },
  {
    key: 'recent',
    label: `지난 ${RECENT_HOURS}시간 보기`,
    headline: `지난 ${RECENT_HOURS}시간 — 이 시간 창 안에 난 것`,
    why:
      `지금부터 ${RECENT_HOURS}시간 전까지, 창의 두 끝을 정해 놓고 봅니다. ` +
      '화면을 새로 고쳐도 창이 미끄러지지 않아 위의 요약 한 줄과 같은 시간을 말합니다.',
    query: {},   // 아래에서 since·until 을 계산해 넣는다 (지금 시각이 필요하다)
  },
  {
    key: 'mine',
    label: '내 담당 보기',
    headline: '내 담당 — 내가 판정한 이벤트',
    why:
      '내가 실제·오탐을 판정한 이벤트입니다. 내가 처리 단계를 옮긴 것과는 다릅니다.',
    query: { mine: true },
  },
  {
    key: 'system',
    label: '시스템 보기',
    headline: '시스템 — 설비 자신이 낸 신호',
    why:
      '현장에서 난 일이 아니라 카메라·저장 장치 같은 설비 자신의 상태입니다. ' +
      '아래 「연계 상태」는 지난 일이 아니라 지금 이 순간의 신호라 따로 놓았습니다.',
    query: { event_type: SYSTEM_EVENT_TYPES.join(',') },
  },
];

/**
 * ★ 「시스템」 프리셋이 **목록이면서 카드 하나를 더 다는 이유** — [실측 2026-09-23]
 *
 *   1차판을 쓸 때 `DetectionEvent.EventType` 에는 시스템 유형이 없었고, 그래서 이
 *   프리셋을 「목록 아님」으로 두려 했다. 그 사이(같은 턴)에 차선 E2 의 P-20 이
 *   마이그레이션 0026 으로 `camera_down` · `storage_high` 둘을 열거에 더했다 —
 *   **화면을 처음 띄운 그 순간에 목록에서 그 두 유형을 보고 알았다.** 화면이 시험이었다.
 *   그래서 이 프리셋은 다른 셋과 똑같이 **서버 질의**로 거른다.
 *
 *   다만 「연계 상태」는 이벤트가 아니다. 그것은 **지금 이 순간의 신호**이고
 *   과거의 사건이 아니다 — 같은 표에 섞으면 「언제 일어났나」 칸이 거짓말을 한다.
 *   그래서 카드로 따로 붙인다(P-19 — 이 응답은 캐시를 지나지 않는다).
 *
 *   ⚠ 여전히 **여기 없는 시스템 신호가 있다.** 카메라 맥박 · 저장 용량 % 는
 *     `scripts/ops_monitor.py` 안에만 있고 부를 라우트가 없다 —
 *     온보딩 48행의 U1 #3 · U5 #15 가 그 자리다. 없는 것은 없다고 적는다(D-284).
 */
/**
 * ★ [P-27 · 2026-09-25 사고] 이 안내는 앞판에서 **우리 도구 경로**를 화면에 적고 있었다
 *   (`scripts/ops_monitor.py`). 없는 것을 없다고 적는 일은 옳지만, **어디에 없는지는
 *   사용자에게 뜻이 없다.** 없다는 사실만 사용자 언어로 남기고, 어디에 무엇이 있는지는
 *   주석과 대장의 자리로 되돌린다.
 */
const SYSTEM_NOTE =
  '이 목록은 설비 자신이 낸 신호입니다. 카메라 응답 여부와 저장 용량은 ' +
  '아직 이 화면에서 볼 수 없습니다 — 여기 없는 것은 아직 없는 것입니다.';

/**
 * ═══════════════════════════════════════════════════════════════════════════
 * P-120 / UX-27 — **기간** (2026-09-10 턴 O · 차선 C1)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 감사 질문은 언제나 **날짜로** 온다: 「12일 03시 14분에 무슨 일이 있었나」.
 * 종전 이 화면에는 날짜 칸이 한 개도 없었다 — 「지난 12시간」 하나뿐이었고,
 * 그 창은 어제 것도 못 본다.
 *
 * ★ **서버가 거른다.** [실측 2026-09-10 · `backend/apps/dsm/api.py::events`]
 *   이 라우트가 받는 인자는 `since · until · event_type · severity ·
 *   response_state · mine · limit` 이다. 기간은 `since`/`until` 로 **그대로 나간다** —
 *   화면이 받아서 자르지 않는다.
 *
 * ★ 두 끝을 **둘 다** 보낸다. 여는 쪽만 보내면 창이 아니라 반직선이 된다.
 *
 * ★ 창은 **주소에 산다**(`?period=` · `?since=` · `?until=`). 감사에서 건네줄 링크가
 *   그것이고, 「내가 무엇을 보고 그렇게 말했는가」를 링크가 재현한다.
 */
type PeriodKey = 'none' | 'today' | 'd7' | 'd30' | 'custom';

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: 'none', label: '전체 기간' },
  { key: 'today', label: '오늘' },
  { key: 'd7', label: '7일' },
  { key: 'd30', label: '30일' },
  { key: 'custom', label: '직접 입력' },
];

function parsePeriod(value: string | null): PeriodKey {
  const hit = PERIODS.find((x) => x.key === value);
  return hit ? hit.key : 'none';
}

/**
 * 창의 두 끝을 정한다. **한 곳에서만 정한다** — 두 곳에서 정하면 위의 요약 한 줄과
 * 아래 표가 다른 창을 말하게 되고, 그 어긋남은 화면에서 안 보인다.
 *
 * ⚠ 이 함수는 `now` 를 **인자로 받는다.** 안에서 `new Date()` 를 부르면 15초 갱신마다
 *   창이 미끄러지고, 미끄러지는 창은 같은 링크로 같은 목록을 재현하지 못한다.
 */
function windowOf(
  period: PeriodKey,
  preset: PresetKey,
  customSince: string | null,
  customUntil: string | null,
  now: Date,
): { since?: string; until?: string; label: string } {
  const end = dayjs(now);
  if (period === 'today') {
    return {
      since: end.startOf('day').toDate().toISOString(),
      until: end.endOf('day').toDate().toISOString(),
      label: `${end.format('YYYY-MM-DD')} 하루`,
    };
  }
  if (period === 'd7' || period === 'd30') {
    const days = period === 'd7' ? 7 : 30;
    const start = end.subtract(days, 'day');
    return {
      since: start.toDate().toISOString(),
      until: end.toDate().toISOString(),
      label: `${start.format('YYYY-MM-DD HH:mm')} ~ ${end.format('YYYY-MM-DD HH:mm')}`,
    };
  }
  if (period === 'custom') {
    // ★ 한쪽만 채웠으면 **그 한쪽만 보낸다.** 나머지를 화면이 지어내지 않는다 —
    //   지어낸 끝은 사용자가 정한 적 없는 창이고, 그 창의 0건은 거짓말이다.
    const a = customSince ? dayjs(customSince) : null;
    const b = customUntil ? dayjs(customUntil) : null;
    if (!a?.isValid() && !b?.isValid()) {
      return { label: '직접 입력 — 아직 고르지 않았습니다 (전체 기간을 봅니다)' };
    }
    return {
      since: a?.isValid() ? a.toDate().toISOString() : undefined,
      until: b?.isValid() ? b.toDate().toISOString() : undefined,
      label: `${a?.isValid() ? a.format('YYYY-MM-DD HH:mm') : '처음'} ~ ${
        b?.isValid() ? b.format('YYYY-MM-DD HH:mm') : '지금'}`,
    };
  }
  // 기간을 안 고른 채로 「지난 12시간 보기」를 누른 것 — 그 프리셋이 곧 창이다.
  if (preset === 'recent') {
    const start = end.subtract(RECENT_HOURS, 'hour');
    return {
      since: start.toDate().toISOString(),
      until: end.toDate().toISOString(),
      label: `${start.format('YYYY-MM-DD HH:mm')} ~ ${end.format('YYYY-MM-DD HH:mm')}`,
    };
  }
  return { label: '전체 기간 — 시간으로 거르지 않습니다' };
}

/**
 * ★★ **사건번호로 여는 칸 — 그리고 카메라 이름으로는 못 찾는다는 사실** (P-120)
 *
 *   [실측 2026-09-10 · TARGET=http://localhost:8500]
 *     GET /api/dsm/events?q=… / &search=… / &event_no=… / &camera=…
 *       → 넷 **전부** 22건(= 안 거른 전부)을 돌려준다. 즉 **읽지 않는 인자**다.
 *     라우트 서명에도 없다(`backend/apps/dsm/api.py::events`).
 *
 *   그래서 카메라 이름 검색은 **짓지 않았다.** 목록을 받아 화면에서 이름을 대조하면
 *   상한 50건 밖의 카메라는 「그런 카메라 없음」이 되고, 그것은 검색이 아니라
 *   **거짓말하는 검색**이다 (DA-04 · 이 화면의 첫 규약).
 *
 *   사건번호는 다르다. `GET /api/dsm/events/{id}` 는 **실재하는 문**이고
 *   (없으면 404 로 답한다 — 실측), 그 문을 두드리는 것은 목록을 거르는 일이 아니다.
 *   그래서 이 칸은 「거르기」가 아니라 **「열기」**다. 이름도 그렇게 붙였다.
 */
const CAMERA_SEARCH_GRAY =
  '카메라 이름으로 찾는 기능은 아직 없습니다. ' +
  '지금은 기간을 좁힌 뒤 「카메라」 칸을 눈으로 훑는 것이 유일한 길입니다.';

function parsePreset(value: string | null): PresetKey {
  const hit = PRESETS.find((p) => p.key === value);
  return hit ? hit.key : 'unhandled';
}

export default function EventList() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const preset = parsePreset(params.get('preset'));
  const severity = params.get('severity') ?? undefined;
  const eventType = params.get('event_type') ?? undefined;
  const period = parsePeriod(params.get('period'));
  const customSince = params.get('since');
  const customUntil = params.get('until');
  const active = PRESETS.find((p) => p.key === preset)!;

  /** 「사건번호로 열기」 칸의 글자. **주소에 두지 않는다** — 아직 안 누른 검색어다. */
  const [eventNo, setEventNo] = useState('');

  /** 지금 판정이 날아가는 중인 사건. **행마다 따로** 잠근다 — 하나를 누르면 표
   *  전체가 멎는 것은 「고장」으로 읽힌다. */
  const [busyId, setBusyId] = useState<number | null>(null);

  /** 주소 한 칸만 바꾼다 — 나머지 조건은 유지된다(프리셋을 바꿔도 등급 필터가 살아 있다). */
  const setParam = useCallback(
    (key: string, value?: string) => {
      const next = new URLSearchParams(params);
      if (value === undefined || value === '') next.delete(key);
      else next.set(key, value);
      setParams(next, { replace: false });
    },
    [params, setParams],
  );

  /**
   * 서버로 나가는 질의. **여기서 만든 것 말고는 아무 필터도 없다.**
   *
   * ⚠ 「지난 12시간」의 두 끝은 **그릴 때마다 다시 계산하지 않는다** — 매 갱신마다
   *   창이 미끄러지면 15초마다 다른 모수를 보게 되고, 그러면 요약 한 줄과 목록이
   *   서로 다른 창을 말한다. `preset` 이 바뀔 때만 잡는다.
   */
  /**
   * ★ [P-120] 창은 **한 곳**에서 나온다(`windowOf`). 프리셋이 창을 따로 계산하던
   *   가지를 지웠다 — 두 곳에서 계산하면 「지난 12시간」과 기간 단추가 서로 다른
   *   `since` 를 보내고, 어느 쪽이 이겼는지는 화면에 안 나온다.
   */
  const win = useMemo(
    () => windowOf(period, preset, customSince, customUntil, new Date()),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [period, preset, customSince, customUntil],
  );

  const serverQuery = useMemo(() => {
    const base: Record<string, string | number | boolean> = {
      limit: PAGE_SIZE,
      ...(severity ? { severity } : {}),
      ...(eventType ? { event_type: eventType } : {}),
      ...active.query,
      ...(win.since ? { since: win.since } : {}),
      ...(win.until ? { until: win.until } : {}),
    };
    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset, severity, eventType, win]);

  /**
   * 「사건번호로 열기」 — **거르지 않는다. 연다.**
   * 상세 화면이 서버에 다시 묻고, 없으면 서버가 404 로 답한다. 화면이 「없다」를
   * 지어내지 않는 이유가 그것이다.
   */
  const openByNo = useCallback(
    (raw: string) => {
      const no = raw.trim();
      if (!no) return;
      navigate(`/dsm/events/${encodeURIComponent(no)}`);
    },
    [navigate],
  );

  const events = useDsmResource<{ total: number; events: EventRow[] }>(
    () => dsmGet(dsmEndpoint.events, serverQuery),
    [serverQuery],
    {
      refreshMs: REFRESH_MS,
      isEmpty: (v) => (v?.events?.length ?? 0) === 0,
    },
  );

  /** W1 **요약 한 줄** — 오탐 N 의 원천(K6)을 부르는 첫 화면이다 (온보딩 U2 #1). */
  const summary = useDsmResource<EventSummary>(
    () => dsmGet(dsmEndpoint.eventsSummary, { hours: RECENT_HOURS }),
    [],
    { refreshMs: REFRESH_MS },
  );

  /** 「시스템」 프리셋이 더 읽는 **지금 이 순간의** 신호. P-19 — 캐시를 지나지 않는다. */
  const link = useDsmResource<{ status: string; detail?: string }>(
    () => dsmGet(dsmEndpoint.linkState),
    [],
    { enabled: active.key === 'system', refreshMs: REFRESH_MS },
  );

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(() => {
    events.reload();
    summary.reload();
  });

  /**
   * ★★ **재판정 — 목록에서 바로** (부속서A 업무플로우 U2 #3 · 차선 U24 · 턴 S).
   *
   *   종전에는 이 단추가 **상세에만** 있었다. 그래서 팀장이 밤사이 목록을 훑다가
   *   오탐 하나를 보면, 상세로 들어가 누르고 목록으로 돌아와 자리를 다시 찾아야
   *   했다 — 스무 건이면 스무 번이다. 같은 문을 목록에서도 연다.
   *
   * ★ **문을 새로 만들지 않는다.** 부르는 곳은 상세와 **같은 판정 문**이고, 사유도
   *   멱등 키도 같은 규약을 쓴다. 두 화면이 서로 다른 문을 부르면 한쪽만 고쳐지는
   *   날 두 화면이 다른 일을 한다.
   *
   * ★ 오탐은 **사유를 받는다.** 서버가 강제하지는 않지만 화면이 먼저 묻는다 —
   *   물어 두면 적히고, 적힌 사유가 다음 달의 같은 오탐을 줄인다.
   *
   * ★ 오탐으로 판정하면 **처리 단계도 함께 닫힌다.** 그 일은 화면이 하지 않는다 —
   *   서버가 한 번의 응답으로 끝낸다. 그래서 누른 뒤에 목록과 요약을 **다시 읽는다**:
   *   누른 것이 아니라 **누른 뒤에 서버가 말한 것**이 증거다.
   */
  const review = useCallback(
    (eventId: number, verdict: 'confirmed' | 'rejected') => {
      const isFalsePositive = verdict === 'rejected';
      let reason = '';
      Modal.confirm({
        title: isFalsePositive
          ? '이 탐지를 오탐으로 판정합니다'
          : '이 탐지를 실제로 판정합니다',
        content: (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary">
              {isFalsePositive
                ? '오탐으로 판정하면 처리 단계도 함께 종결됩니다. 되돌릴 수 없습니다 — 나중에 실제로 다시 판정해도 처리 단계는 열리지 않습니다.'
                : '판정은 종결한 뒤에도 지워지지 않습니다. 오탐률을 셀 때 이 건이 분모에 들어갑니다.'}
            </Text>
            <Input.TextArea
              rows={2}
              placeholder="사유 (개선 기록에 그대로 실립니다)"
              onChange={(ev) => {
                reason = ev.target.value;
              }}
            />
          </Space>
        ),
        okText: isFalsePositive ? '오탐으로 판정' : '실제로 판정',
        cancelText: '취소',
        onOk: async () => {
          setBusyId(eventId);
          try {
            await dsmPostQueryOnce(
              dsmEndpoint.review(eventId),
              { verdict, reason },
              intentKey(`review:${eventId}:${verdict}`),
            );
            message.success('판정을 기록했습니다.');
            events.reload();
            summary.reload();
          } catch (err) {
            message.error(
              userFacingError('EventList.review', err, '판정이 실패했습니다.'),
            );
            throw err; // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
          } finally {
            setBusyId(null);
          }
        },
      });
    },
    [events, summary],
  );

  const rows = useMemo(() => events.data?.events ?? [], [events.data]);

  /**
   * ★ [턴 T · 차선 U24 · P-164 ②] **상급 보고 체크** — 목록에서 토글.
   *   모델 칸은 이미 있다(`DsmUpperReportFlag` · 실측). 체크 여부는 **서버가 말한다** —
   *   목록의 사건 id 로 한 번에 묻고(`upper-report/flags`), 누른 뒤에는 **다시 읽는다**.
   *   화면이 자기 상태를 먼저 켜지 않는다 — 켰다가 서버가 거절하면 「했다」가 거짓이 된다.
   *   서버 값이 오지 않으면(실패·403) 칸에 「확인 못 함」이라고 적는다 — 회색이지 초록이 아니다.
   *   감사는 서버가 남긴다(성공·실패 모두) — 화면은 감사 번호를 안내 문장에 실을 뿐이다.
   */
  const idsKey = useMemo(() => rows.map((r) => r.event_id).join(','), [rows]);
  const flags = useDsmResource<UpperReportFlags>(
    () => dsmGet<UpperReportFlags>(dsmU24StatsEndpoint.upperReportFlags, { event_ids: idsKey }),
    [idsKey],
    { enabled: idsKey.length > 0 },
  );
  const [flagBusyId, setFlagBusyId] = useState<number | null>(null);
  const toggleUpperReport = useCallback(
    async (eventId: number, flagged: boolean) => {
      setFlagBusyId(eventId);
      try {
        const out = flagged
          ? await dsmDelete<{ audit_id: number }>(dsmU24StatsEndpoint.upperReport(eventId))
          : await dsmPostQueryOnce<{ audit_id: number }>(
              dsmU24StatsEndpoint.upperReport(eventId),
              { reason: '목록에서 체크' },
              intentKey(`upper-report:${eventId}`),
            );
        message.success(
          `${flagged ? '상급 보고 체크를 풀었습니다' : '상급 보고로 표시했습니다'} (감사 #${out.audit_id}).`,
        );
        flags.reload(); // 누른 뒤를 본다 — 응답이 아니라 다시 읽은 값이 증거다
      } catch (err) {
        message.error(userFacingError('EventList.upperReport', err, '상급 보고 표시를 바꾸지 못했습니다.'));
      } finally {
        setFlagBusyId(null);
      }
    },
    [flags],
  );

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              이벤트 목록
            </Title>
          </Col>
          <Col>
            <Text type="secondary">
              {events.loadedAt ? `갱신 ${stamp(events.loadedAt)}` : ''}
            </Text>
          </Col>
        </Row>

        {/* ── W1 요약 한 줄 (U2 #1 「밤사이 요약 보기」) ─────────────────────
            ★ 비율만 적지 않는다. **분자·분모를 같은 줄에** 적는다 (D-271 ③ · D-301).
            ★ 판정 0건이면 오탐률은 「0%」가 아니라 **「잴 수 없음」**이다 —
              0% 로 적으면 판정을 안 하기만 해도 지표가 좋아진다. */}
        <Card size="small" title={`요약 한 줄 · 지난 ${RECENT_HOURS}시간`}>
          <StateBoundary
            state={summary.state}
            reason={summary.reason} status={summary.status}
            onRetry={summary.reload}
          >
            {summary.data && (
              <Text>
                미처리{' '}
                <b>
                  {summary.data.unhandled}건
                  {summary.data.unhandled_capped ? ' 이상' : ''}
                </b>{' '}
                · 오탐 <b>{summary.data.false_positive}건</b> / 판정{' '}
                {summary.data.reviewed}건 ·{' '}
                {summary.data.measurable && summary.data.false_positive_rate !== null
                  ? `오탐률 ${(summary.data.false_positive_rate * 100).toFixed(1)}%`
                  : '아직 판정한 이벤트가 없습니다'}{' '}
                · 미판정 {summary.data.unreviewed}건
                {summary.data.closed_without_verdict > 0
                  ? ` (판정 없이 종료 ${summary.data.closed_without_verdict}건)`
                  : ''}
              </Text>
            )}
          </StateBoundary>
        </Card>

        <Card size="small">
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            {/* ★ [P-51 · 2026-09-05] 묶음 이름 **「프리셋」을 뺐다.**
                「프리셋」은 우리 말이다 — 사전(GX-COPY §5 턴 E)이 단추 넷에
                「…보기」라는 이름을 주었고, 그 이름이 **누르면 무엇이 보이는지**를
                먼저 말한다. 묶음에 이름을 다시 붙이려면 사전에 낱말이 있어야 하는데
                없다 — **없는 말을 만들지 않는다**(GX-COPY 규칙). 그래서 지운다.
                ⚠ 질의 인자 이름(`preset=`)은 **계약**이라 그대로다. 바뀐 것은
                  표시 이름뿐이다(GX-COPY 규칙 2). */}
            <Space wrap>
              {PRESETS.map((p) => (
                <Button
                  key={p.key}
                  type={p.key === preset ? 'primary' : 'default'}
                  onClick={() => setParam('preset', p.key)}
                >
                  {p.label}
                </Button>
              ))}
            </Space>
            {/* ── [P-120] 기간 · 한 줄 ─────────────────────────────────────
                ★ 이 줄이 생기기 전까지 이 화면에는 **날짜 칸이 하나도 없었다.**
                  감사 질문은 언제나 날짜로 온다.
                ★ 고른 창은 **글자로 다시 적는다**(아래 「보고 있는 기간」).
                  단추가 눌린 모양만으로는 「어디부터 어디까지인가」를 말하지 못하고,
                  그 문장이 없으면 사람이 자기가 본 창을 보고서에 옮겨 적지 못한다. */}
            <Space wrap align="center">
              <Text type="secondary">기간</Text>
              <Segmented
                value={period}
                onChange={(v) => setParam('period', String(v))}
                options={PERIODS.map((x) => ({ value: x.key, label: x.label }))}
              />
              {period === 'custom' && (
                <DatePicker.RangePicker
                  showTime={{ format: 'HH:mm' }}
                  format="YYYY-MM-DD HH:mm"
                  allowEmpty={[true, true]}
                  value={[
                    customSince && dayjs(customSince).isValid() ? dayjs(customSince) : null,
                    customUntil && dayjs(customUntil).isValid() ? dayjs(customUntil) : null,
                  ] as [Dayjs | null, Dayjs | null]}
                  onChange={(vals) => {
                    const next = new URLSearchParams(params);
                    next.set('period', 'custom');
                    const a = vals?.[0];
                    const b = vals?.[1];
                    if (a) next.set('since', a.toDate().toISOString());
                    else next.delete('since');
                    if (b) next.set('until', b.toDate().toISOString());
                    else next.delete('until');
                    setParams(next, { replace: false });
                  }}
                />
              )}
              <Text type="secondary" style={{ fontSize: 12 }}>
                보고 있는 기간: {win.label}
              </Text>
            </Space>

            {/* ── [P-120] 사건번호로 열기 ──────────────────────────────────
                ★ 「찾기」가 아니라 **「열기」**다. 목록을 거르는 것이 아니라
                  그 사건의 문을 두드린다 — 없으면 상세 화면이 서버의 404 를 그린다.
                ★ 카메라 이름 검색은 **회색이다.** 서버가 그 인자를 안 받는다는 사실을
                  화면에서 숨기지 않는다 — 있는 척한 검색은 없는 검색보다 나쁘다. */}
            <Space wrap align="center">
              <Input.Search
                allowClear
                placeholder="사건번호"
                enterButton="열기"
                style={{ width: 240 }}
                value={eventNo}
                onChange={(e) => setEventNo(e.target.value)}
                onSearch={openByNo}
              />
              <Popover content={<div style={{ maxWidth: 300 }}>{CAMERA_SEARCH_GRAY}</div>}>
                <Input
                  disabled
                  style={{ width: 200 }}
                  placeholder="카메라 이름 — 아직 못 찾습니다"
                />
              </Popover>
            </Space>

            <Space wrap>
              <Select
                allowClear
                placeholder="등급 전체"
                style={{ width: 140 }}
                value={severity}
                onChange={(v) => setParam('severity', v)}
                options={Object.entries(SEVERITY_LABEL).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
              <Select
                allowClear
                placeholder="유형 전체"
                style={{ width: 140 }}
                value={eventType}
                onChange={(v) => setParam('event_type', v)}
                options={Object.entries(EVENT_TYPE_LABEL).map(([value, label]) => ({
                  value,
                  label,
                }))}
              />
              <Button onClick={events.reload}>새로고침</Button>
              {/* ★ [UX-20] 「요청 상한 50건」을 본문에서 뺐다. 상한은 **사실**이지만
                  당직자의 말이 아니다 — 「?」 뒤로 옮겼다 (GX-COPY §2).
                  분모를 버린 것이 아니라 **한 칸 뒤로 옮긴 것**이다(D-301). */}
              <Space size={4}>
                <Text type="secondary">{rows.length}건</Text>
                <Popover
                  content={
                    <div style={{ maxWidth: 280 }}>
                      한 번에 최대 {PAGE_SIZE}건까지 받아 옵니다. 조건에 맞는 이벤트가
                      그보다 많으면 오래된 것부터 이 화면에 안 나올 수 있습니다 —
                      기간이나 등급을 좁혀 보십시오.
                    </div>
                  }
                >
                  <Button type="text" size="small" aria-label="건수 설명">
                    ?
                  </Button>
                </Popover>
              </Space>
            </Space>
          </Space>
        </Card>

        {/* 그 화면에만 있는 글자 — 검수 촬영이 이 줄로 「그 화면이 떴다」를 단언한다 */}
        <Alert type="info" showIcon message={active.headline} description={active.why} />

        {/* ★ [P-27 · P0] **여기가 사고가 난 자리다.**

            앞판은 서버가 준 사유를 그대로 문단으로 그렸다. 그 문단에는 상대사명 ·
            계약번호 · 조항 · 미이행 사실이 들어 있었고, 관제요원 화면에 떠 있었다.
            이제 화면이 그리는 것은 **한 단어**이고, 「자세히」는 서버가 관리자에게만
            `detail` 을 줄 때에만 나타난다 — 화면이 역할을 판정하지 않는다.
            판정하는 쪽이 둘이면 한쪽은 반드시 틀린다. */}
        {active.key === 'system' && (
          <Card size="small" title="연계 상태 (지금 이 순간)">
            <StateBoundary state={link.state} reason={link.reason} status={link.status} onRetry={link.reload}>
              {link.data && (
                <Space direction="vertical">
                  <Space size="small">
                    <Badge
                      status={linkStatusBadge(link.data.status)}
                      text={linkStatusLabel(link.data.status)}
                    />
                    {link.data.detail && (
                      <Popover content={<div style={{ maxWidth: 320 }}>{link.data.detail}</div>}>
                        <Button type="link" size="small">자세히</Button>
                      </Popover>
                    )}
                  </Space>
                  <Text type="secondary">{SYSTEM_NOTE}</Text>
                </Space>
              )}
            </StateBoundary>
          </Card>
        )}

        <StateBoundary
            state={events.state}
            reason={events.reason} status={events.status}
            onRetry={events.reload}
            emptyText="조건에 맞는 이벤트가 없습니다. (요청은 성공했고 0건입니다)"
          >
            <Table<EventRow>
              rowKey="event_id"
              dataSource={rows}
              pagination={{ pageSize: 20, showSizeChanger: false }}
              onRow={(row) => ({
                onClick: () => navigate(`/dsm/events/${row.event_id}`),
                style: { cursor: 'pointer' },
              })}
              columns={[
                {
                  title: '등급',
                  dataIndex: 'severity',
                  width: 110,
                  render: (v: string) => (
                    <Tag color={SEVERITY_COLOR[v] ?? 'default'}>
                      {SEVERITY_ICON[v] ?? '●'} {SEVERITY_LABEL[v] ?? v}
                    </Tag>
                  ),
                },
                {
                  title: '유형',
                  dataIndex: 'event_type',
                  width: 90,
                  render: (v: string) => labelOf(EVENT_TYPE_LABEL, v),
                },
                { title: '카메라', dataIndex: 'stream_monitor_name', ellipsis: true },
                {
                  // ★ [UX-22 · 2026-09-26] **세 열을 둘로 줄였다.** 앞판은 「대응 · 상태 ·
                  //   판정」을 나란히 세웠고, 셋 다 「이 사건이 어디까지 왔나」로 읽혀
                  //   사람이 어느 축을 보는지 몰랐다 (GX-COPY §1-4).
                  //   남긴 축은 둘이다 — **처리 단계**(사람이 어디까지 했나)와
                  //   **판정**(그 탐지가 진짜였나). 진위 축(`status`)은 판정과 같은 것을
                  //   두 이름으로 부르던 열이라 사용자 화면에서 내렸다(라우트·값은 그대로).
                  title: '처리 단계',
                  dataIndex: 'response_state',
                  width: 110,
                  render: (v: string) => labelOf(RESPONSE_STATE_LABEL, v),
                },
                {
                  // ★ 판정은 처리 단계와 **따로** 낸다 (D-293) — 종결돼도 오탐이었음을 말한다
                  title: '판정',
                  dataIndex: 'verdict',
                  width: 90,
                  render: (v: string) => <VerdictBadge verdict={v} />,
                },
                {
                  // ★★ [턴 S · 차선 U24] **재판정을 목록에도.** 상세에만 있던 문이다.
                  //   ⚠ 행 클릭은 상세로 간다 — 그래서 이 칸의 누름은 **위로 안 퍼지게**
                  //     막는다(`stopPropagation`). 안 막으면 판정을 누른 순간 상세로
                  //     떠나고, 사람은 자기가 무엇을 눌렀는지 모른 채 화면이 바뀐다.
                  title: '재판정',
                  key: 'review',
                  width: 180,
                  render: (_v: unknown, row: EventRow) => (
                    <Space
                      size={4}
                      onClick={(ev) => ev.stopPropagation()}
                    >
                      <Button
                        size="small"
                        loading={busyId === row.event_id}
                        onClick={() => review(row.event_id, 'confirmed')}
                      >
                        실제
                      </Button>
                      {/* ⚠ 빨강을 쓰지 않는다 — 빨강은 심각 등급 전용이다. 오탐 단추가
                          빨강이면 관제 화면에서 빨강이 두 뜻을 갖는다. */}
                      <Button
                        size="small"
                        loading={busyId === row.event_id}
                        onClick={() => review(row.event_id, 'rejected')}
                      >
                        오탐
                      </Button>
                    </Space>
                  ),
                },
                {
                  // ★ [턴 T · 차선 U24] 상급 보고 체크 — 서버 값으로만 그린다(위 머리말).
                  title: '상급 보고',
                  key: 'upper_report',
                  width: 120,
                  render: (_v: unknown, row: EventRow) => {
                    const flag = flags.data?.flags?.[String(row.event_id)];
                    const known = flags.state === 'data' || flags.state === 'empty';
                    return (
                      <Space size={4} onClick={(ev) => ev.stopPropagation()}>
                        {!known ? (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            {flags.state === 'loading' ? '확인 중' : '확인 못 함'}
                          </Text>
                        ) : (
                          <Button
                            size="small"
                            type={flag ? 'primary' : 'default'}
                            loading={flagBusyId === row.event_id}
                            title={flag?.reported_at ? `보고 시각 ${absolute(flag.reported_at)}` : '상급 보고로 표시'}
                            onClick={() => toggleUpperReport(row.event_id, Boolean(flag))}
                          >
                            {flag ? '보고함' : '보고 표시'}
                          </Button>
                        )}
                      </Space>
                    );
                  },
                },
                {
                  title: '발생',
                  dataIndex: 'occurred_at',
                  width: 180,
                  render: (v: string) => <span title={absolute(v)}>{stamp(v)}</span>,
                },
              ]}
            />
        </StateBoundary>

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
