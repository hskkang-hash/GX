/**
 * 화면 ② **이벤트 목록** — E2E-1 의 가운데 칸 (D-371 ①).
 *
 * ★ 필터는 **서버가 건다.** 목록을 다 받아 화면에서 거르면 두 가지가 동시에 깨진다:
 *     ① 격리 — 화면이 거르기 전의 목록은 이미 브라우저에 와 있다
 *     ② F-05 p95 — 분모가 커질수록 느려지고, 그 느림은 로컬에서 안 보인다
 *
 * ★ 「0건」과 「못 가져왔다」를 같은 그림으로 그리지 않는다 (DA-03 §2-5 규칙 1).
 *   `StateBoundary` 가 그 둘을 가른다 — 이 화면이 직접 그리지 않는 이유다.
 *
 * ★ 등급은 색 + 아이콘 + 라벨 셋으로 낸다. 색만 쓰면 색각 이상이 못 읽는다 (DA-03 §2-2).
 */
import { Button, Card, Col, Row, Select, Space, Table, Tag, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  STATUS_LABEL,
  VERDICT_LABEL,
} from '../severity';
import { absolute, stamp, TIMEZONE_NOTE } from '../time';
import type { EventRow } from '../types';

const { Text, Title } = Typography;

const REFRESH_MS = 15_000;
const PAGE_SIZE = 50;

export default function EventList() {
  const navigate = useNavigate();
  const [severity, setSeverity] = useState<string | undefined>();
  const [eventType, setEventType] = useState<string | undefined>();

  const events = useDsmResource<{ total: number; events: EventRow[] }>(
    () =>
      dsmGet(dsmEndpoint.events, {
        limit: PAGE_SIZE,
        // ★ 빈 값은 **보내지 않는다.** 빈 문자열을 보내면 서버가 "빈 등급"으로 거른다.
        ...(severity ? { severity } : {}),
        ...(eventType ? { event_type: eventType } : {}),
      }),
    [severity, eventType],
    { refreshMs: REFRESH_MS, isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
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

        <Card size="small">
          <Space wrap>
            <Select
              allowClear
              placeholder="등급 전체"
              style={{ width: 140 }}
              value={severity}
              onChange={setSeverity}
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
              onChange={setEventType}
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
        </Card>

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
                // 상태는 **형태**로 구분한다 — 색을 두 축에 쓰지 않는다 (DA-03 §2-2)
                title: '상태',
                dataIndex: 'status',
                width: 90,
                render: (v: string) => (
                  <span style={{ textDecoration: v === 'closed' ? 'line-through' : undefined }}>
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
