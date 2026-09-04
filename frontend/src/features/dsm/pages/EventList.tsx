/**
 * 화면 ② **이벤트 목록 + W1 관제 프리셋** — E2E-1 의 가운데 칸 (D-371 ① · 차선 C).
 *
 * ★ 필터는 **서버가 건다.** 목록을 다 받아 화면에서 거르면 두 가지가 동시에 깨진다:
 *     ① 격리 — 화면이 거르기 전의 목록은 이미 브라우저에 와 있다
 *     ② F-05 p95 — 분모가 커질수록 느려지고, 그 느림은 로컬에서 안 보인다
 *   그래서 프리셋 넷은 **전부 질의로 나간다.** 이 파일에는 `rows.filter(...)` 가
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
import { Alert, Badge, Button, Card, Col, Popover, Row, Select, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet } from '../api';
import { linkStatusBadge, linkStatusLabel } from '../copy';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  STATUS_LABEL,
  SYSTEM_EVENT_TYPES,
  VERDICT_LABEL,
} from '../severity';
import { absolute, stamp, TIMEZONE_NOTE } from '../time';
import type { EventRow, EventSummary } from '../types';

const { Text, Title } = Typography;

const REFRESH_MS = 15_000;
const PAGE_SIZE = 50;

/** 「지난 12시간」의 12. 요약 한 줄과 목록이 **같은 수**를 써야 두 줄이 같은 창을 말한다. */
const RECENT_HOURS = 12;

/**
 * W1 프리셋 넷 (P-13).
 *
 * `query` 가 **그대로 서버로 나간다.** 화면이 뒤에서 한 번 더 거르지 않는다 —
 * 그 한 줄이 생기는 순간 「서버 필터」라는 말이 거짓이 된다.
 *
 * ⚠ `system` 은 목록에 더해 **카드 하나**를 더 단다(연계 상태). 그 사유는 아래
 *   `SYSTEM_NOTE` 에 적혀 있다 — 이벤트와 「지금 이 순간의 신호」는 다른 것이다.
 */
type PresetKey = 'unhandled' | 'recent' | 'mine' | 'system';

interface PresetDef {
  key: PresetKey;
  label: string;
  /** 그 프리셋이 켜졌을 때 화면에 뜨는 **그 화면에만 있는 글자** (검수 촬영의 단언 대상). */
  headline: string;
  why: string;
  query: Record<string, string | number | boolean>;
}

const PRESETS: PresetDef[] = [
  {
    key: 'unhandled',
    label: '미처리',
    headline: 'W1 프리셋 · 미처리 — 대응 축이 아직 「발생」인 것',
    why:
      '서버가 `response_state=occurred` 로 걸러 준 목록입니다. ' +
      '화면이 페이지를 받아 거른 것이 아니므로 상한 밖의 이벤트도 빠지지 않습니다.',
    query: { response_state: 'occurred' },
  },
  {
    key: 'recent',
    label: `지난 ${RECENT_HOURS}시간`,
    headline: `W1 프리셋 · 지난 ${RECENT_HOURS}시간 — 창의 두 끝을 서버가 받는다`,
    why:
      '`since` 와 `until` 을 둘 다 보냅니다. 여는 쪽만 보내면 그것은 ' +
      '「지난 12시간」이 아니라 「12시간 전부터 미래까지」입니다.',
    query: {},   // 아래에서 since·until 을 계산해 넣는다 (지금 시각이 필요하다)
  },
  {
    key: 'mine',
    label: '내 담당',
    headline: 'W1 프리셋 · 내 담당 — 내가 판정한 이벤트',
    why:
      '`mine=true` 만 보냅니다. 사번을 화면이 정하지 않습니다 — 「나」가 누구인지는 ' +
      '서버가 압니다. ⚠ 내가 「판정」한 것이지 내가 「대응」한 것이 아닙니다: ' +
      '대응 전이의 행위자는 행이 아니라 감사(guardianx.dsm.response)에 있습니다.',
    query: { mine: true },
  },
  {
    key: 'system',
    label: '시스템',
    headline: 'W1 프리셋 · 시스템 — 장애인가 현장인가',
    why:
      `현장 탐지가 아니라 설비 자신의 상태입니다 (${SYSTEM_EVENT_TYPES.join(' · ')}). ` +
      '서버가 유형으로 걸러 줍니다 — 화면이 목록을 받아 고른 것이 아닙니다. ' +
      '아래 「연계 상태」는 이벤트가 아니라 지금 이 순간의 신호라 따로 놓았습니다.',
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
  const active = PRESETS.find((p) => p.key === preset)!;

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
  const serverQuery = useMemo(() => {
    const base: Record<string, string | number | boolean> = {
      limit: PAGE_SIZE,
      ...(severity ? { severity } : {}),
      ...(eventType ? { event_type: eventType } : {}),
      ...active.query,
    };
    if (active.key === 'recent') {
      const until = new Date();
      const since = new Date(until.getTime() - RECENT_HOURS * 3600_000);
      base.since = since.toISOString();
      base.until = until.toISOString();
    }
    return base;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preset, severity, eventType]);

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

  const rows = useMemo(() => events.data?.events ?? [], [events.data]);

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
            reason={summary.reason}
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
                  : '오탐률 잴 수 없음 (판정 0건 — 분모가 없다)'}{' '}
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
            <Space wrap>
              <Text strong>프리셋</Text>
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
              {/* 분모를 늘 보여 준다 (D-301) — 「3건」만 보면 걸러진 것인지 없는 것인지 모른다 */}
              <Text type="secondary">
                표시 {rows.length}건 (요청 상한 {PAGE_SIZE}건)
              </Text>
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
            <StateBoundary state={link.state} reason={link.reason} onRetry={link.reload}>
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
            reason={events.reason}
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
                  // ★ 대응 진행 — **판정과 다른 축이다** (D-399). 이 칸이 목록에 없어서
                  //   U2 의 「미처리 이벤트 확인」이 눈짐작이었다(온보딩 U2 #2).
                  title: '대응',
                  dataIndex: 'response_state',
                  width: 120,
                  render: (v: string) => labelOf(RESPONSE_STATE_LABEL, v),
                },
                {
                  // 상태는 **형태**로 구분한다 — 색을 두 축에 쓰지 않는다 (DA-03 §2-2)
                  title: '상태',
                  dataIndex: 'status',
                  width: 90,
                  render: (v: string) => (
                    <span
                      style={{ textDecoration: v === 'closed' ? 'line-through' : undefined }}
                    >
                      {labelOf(STATUS_LABEL, v)}
                    </span>
                  ),
                },
                {
                  // ★ 판정은 상태와 **따로** 낸다 (D-293) — 종료돼도 오탐이었음을 말한다
                  title: '판정',
                  dataIndex: 'verdict',
                  width: 90,
                  render: (v: string) => labelOf(VERDICT_LABEL, v),
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
