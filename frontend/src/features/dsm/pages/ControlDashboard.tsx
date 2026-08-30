/**
 * 화면 ① **관제 대시보드** — E2E-1 의 첫 칸 (D-371 ①).
 *
 * ★ 이 화면이 하는 일은 셋이다. 그 밖의 것을 여기서 하지 않는다:
 *     ① 이 사람이 **어느 프리셋으로 떨어졌는지** 보여 준다 (K3 · U3)
 *     ② **5상태의 분모와 분자**를 보여 준다 (F-09 AC-09 ①)
 *     ③ **연계 상태 3표시**를 상단에 늘 띄운다 (계약 §2.2-2 장애격리)
 *
 * ★ 왜 프리셋을 **화면에 적나.** 「매핑을 못 찾아 가장 좁은 화면으로 떨어졌다」는
 *   상태는 서버만 알고 사용자는 모른다. 그러면 「원래 이런 화면인가 보다」가 되고,
 *   설정 누락이 영원히 안 보인다 — `preset_matched=false` 를 **눈에 보이게** 둔다 (D-290).
 *
 * ★ 「끊김」이어도 **이 화면은 계속 동작한다** (DA-03 §2-3). SDN 표시만 낮춘다.
 *   그것이 계약 §2.2-2 「일방 장애 시 타방 단독 동작」을 사람이 눈으로 보는 자리다.
 */
import { Alert, Badge, Card, Col, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { EVENT_TYPE_LABEL, labelOf, SEVERITY_COLOR, SEVERITY_ICON, SEVERITY_LABEL } from '../severity';
import { stamp, TIMEZONE_NOTE } from '../time';
import type { DashboardFrame, EventRow } from '../types';

const { Text, Title } = Typography;

/** 부분 갱신 간격. 재난 화면은 사람이 새로고침을 누르고 있을 수 없다. */
const REFRESH_MS = 15_000;

const LINK_BADGE: Record<string, { status: 'success' | 'processing' | 'error'; text: string }> = {
  ok: { status: 'success', text: '연계 정상' },
  healthy: { status: 'success', text: '연계 정상' },
  waiting: { status: 'processing', text: '연계 대기' },
  pending: { status: 'processing', text: '연계 대기' },
  down: { status: 'error', text: '연계 끊김' },
  disconnected: { status: 'error', text: '연계 끊김' },
};

export default function ControlDashboard() {
  const navigate = useNavigate();

  const frame = useDsmResource<DashboardFrame>(
    () => dsmGet<DashboardFrame>(dsmEndpoint.dashboardFrame),
    [],
    { refreshMs: REFRESH_MS },
  );

  const events = useDsmResource<{ total: number; events: EventRow[] }>(
    () => dsmGet(dsmEndpoint.events, { limit: 10 }),
    [],
    { refreshMs: REFRESH_MS, isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
  );

  const openEvent = useCallback(
    (id: number) => navigate(`/dsm/events/${id}`),
    [navigate],
  );

  const link = frame.data?.link;
  const badge = link ? LINK_BADGE[link.status] ?? { status: 'error' as const, text: `연계 ${link.status}` } : null;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              관제 대시보드
            </Title>
          </Col>
          <Col>
            <Space size="large">
              {/* ③ 연계 상태 — **끊김이어도 아래는 계속 동작한다** */}
              {badge && (
                <span title={link?.reason}>
                  <Badge status={badge.status} text={badge.text} />
                </span>
              )}
              <Text type="secondary">
                {frame.loadedAt ? `갱신 ${stamp(frame.loadedAt)}` : ''}
              </Text>
            </Space>
          </Col>
        </Row>

        {/* ① 프리셋 — 못 찾아 떨어진 상태를 **눈에 보이게** 둔다 */}
        {frame.data && !frame.data.preset_matched && (
          <Alert
            type="warning"
            showIcon
            message="역할 매핑을 찾지 못해 가장 좁은 화면으로 떨어졌습니다."
            description="관리자에게 역할–프리셋 매핑(K3_ROLE_PRESET_MAP) 등록을 요청하십시오. 지금 보이는 것이 이 계정의 전부가 아닐 수 있습니다."
          />
        )}

        <StateBoundary state={frame.state} reason={frame.reason} onRetry={frame.reload}>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={6}>
              <Card size="small">
                <Statistic
                  title="화면 프리셋"
                  value={frame.data?.preset ?? '—'}
                  suffix={
                    <Tag color={frame.data?.preset_matched ? 'green' : 'orange'}>
                      {frame.data?.preset_matched ? '역할 매칭' : '기본값'}
                    </Tag>
                  }
                />
              </Card>
            </Col>
            {/* ② 5상태 — **분모를 함께 낸다.** 「정상 3칸」만 보면 전체가 3인지 30인지 모른다 */}
            <Col xs={24} md={18}>
              <Card size="small" title={`패널 상태 (전체 ${frame.data?.panel_total ?? 0}칸)`}>
                <Space size="large" wrap>
                  {(frame.data?.five_states ?? []).map((s) => (
                    <Statistic
                      key={s}
                      title={s}
                      value={frame.data?.state_counts?.[s] ?? 0}
                      suffix={`/ ${frame.data?.panel_total ?? 0}`}
                    />
                  ))}
                </Space>
              </Card>
            </Col>
          </Row>
        </StateBoundary>

        <Card
          size="small"
          title="최근 이벤트"
          extra={<a onClick={() => navigate('/dsm/events')}>전체 목록</a>}
        >
          <StateBoundary
            state={events.state}
            reason={events.reason}
            onRetry={events.reload}
            emptyText="최근 이벤트가 없습니다. (요청은 성공했고 0건입니다)"
          >
            <Table<EventRow>
              size="small"
              rowKey="event_id"
              pagination={false}
              dataSource={events.data?.events ?? []}
              onRow={(row) => ({ onClick: () => openEvent(row.event_id) })}
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
                  title: '발생',
                  dataIndex: 'occurred_at',
                  width: 170,
                  render: (v: string) => stamp(v),
                },
              ]}
            />
          </StateBoundary>
        </Card>

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
