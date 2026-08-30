/**
 * 화면 ③ **이벤트 상세** — E2E-1 의 마지막 칸 (D-371 ①).
 *
 * 이 화면이 E2E-1 전 구간을 닫는다: 탐지 → 목록 → **상세 → 알림 확인**.
 *
 * ★ 발송 이력을 같은 화면에 둔다. 계약 F-10 이 재는 두 점(발생 시각 · 발송 기록)이
 *   **한 화면에서 눈으로** 대조돼야 「30초 안에 나갔다」가 사람에게 사실이 된다.
 *
 * ★ **실패한 발송도 행으로 보인다.** K2 는 실패에 `sent_at` 을 찍지 않는다 —
 *   찍으면 F-10 이 거짓으로 달성된다. 화면도 그 규약을 따라야 하므로
 *   실패 행의 시각 칸을 「—」로 두고 **사유를 옆에 적는다.** 숨기지 않는다 (D-284).
 *
 * ★ 「없는 것은 없다고 적는다」 (D-290): `address_status` 가 `disabled` 면
 *   「조회 대상 아님」이라고 적는다. 빈칸으로 두면 「아직 조회 중」과 같아진다.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmPost } from '../api';
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
import { absolute, relative, stamp, TIMEZONE_NOTE } from '../time';
import type { DeliveryRow, EventDetailView } from '../types';

const { Text, Title } = Typography;

const ADDRESS_STATUS_LABEL: Record<string, string> = {
  resolved: '조회됨',
  pending: '조회 대기',
  disabled: '조회 대상 아님 (좌표 없음)',
};

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);

  const event = useDsmResource<EventDetailView>(
    () => dsmGet<EventDetailView>(dsmEndpoint.eventDetail(id!)),
    [id],
    { enabled: Boolean(id) },
  );

  const deliveries = useDsmResource<{ total: number; deliveries: DeliveryRow[] }>(
    () => dsmGet(dsmEndpoint.deliveries, { event_id: id }),
    [id],
    {
      enabled: Boolean(id),
      isEmpty: (v) => (v?.deliveries?.length ?? 0) === 0,
    },
  );

  const notify = useCallback(async () => {
    if (!id) return;
    setSending(true);
    try {
      await dsmPost(dsmEndpoint.notify(id));
      // ★ 「보냈다」가 아니라 **「발송을 요청했다」**고 말한다. 성공 여부는 아래
      //   이력이 말한다 — 실패도 200 이고, 실패는 행으로 보인다 (F-10).
      message.info('발송을 요청했습니다. 결과는 아래 발송 이력에서 확인하십시오.');
      deliveries.reload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '발송 요청이 실패했습니다.');
    } finally {
      setSending(false);
    }
  }, [id, deliveries]);

  const e = event.data;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button onClick={() => navigate('/dsm/events')}>← 목록</Button>
              <Title level={4} style={{ margin: 0 }}>
                이벤트 상세 #{id}
              </Title>
            </Space>
          </Col>
          <Col>
            <Button type="primary" loading={sending} onClick={notify}>
              규칙대로 발송
            </Button>
          </Col>
        </Row>

        <StateBoundary state={event.state} reason={event.reason} onRetry={event.reload}>
          {e && (
            <Card size="small">
              <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }} bordered>
                <Descriptions.Item label="등급">
                  <Tag color={SEVERITY_COLOR[e.severity] ?? 'default'}>
                    {SEVERITY_ICON[e.severity] ?? '●'} {SEVERITY_LABEL[e.severity] ?? e.severity}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="유형">
                  {labelOf(EVENT_TYPE_LABEL, e.event_type)}
                </Descriptions.Item>
                <Descriptions.Item label="상태">
                  <span style={{ textDecoration: e.status === 'closed' ? 'line-through' : undefined }}>
                    {labelOf(STATUS_LABEL, e.status)}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="판정">
                  {labelOf(VERDICT_LABEL, e.verdict)}
                </Descriptions.Item>
                <Descriptions.Item label="발생 시각">
                  {absolute(e.occurred_at)} · {relative(e.occurred_at)}
                </Descriptions.Item>
                <Descriptions.Item label="마지막 관측">
                  {e.last_seen_at ? stamp(e.last_seen_at) : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="카메라">
                  {e.stream_monitor_name || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="확신도">
                  {e.confidence === null || e.confidence === undefined
                    ? '—'
                    : `${(e.confidence * 100).toFixed(1)}%`}
                </Descriptions.Item>
                <Descriptions.Item label="좌표">
                  {e.lat !== null && e.lng !== null ? `${e.lat}, ${e.lng}` : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="주소" span={2}>
                  {e.address || '—'}{' '}
                  <Text type="secondary">
                    ({labelOf(ADDRESS_STATUS_LABEL, e.address_status)})
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="영상 구간">
                  {e.clip_path ? '있음' : '없음'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </StateBoundary>

        <Card size="small" title="발송 이력 (F-10)">
          {/* ★ F-10 은 「심각 등급 발생 후 30초 내 발송 기록」이다.
              위의 발생 시각과 아래의 발송 시각이 **한 화면에** 있어야 사람이 잰다. */}
          <StateBoundary
            state={deliveries.state}
            reason={deliveries.reason}
            onRetry={deliveries.reload}
            emptyText="발송 기록이 없습니다. (요청은 성공했고 0건입니다)"
          >
            <Table<DeliveryRow>
              size="small"
              rowKey={(r, i) => String(r.delivery_id ?? i)}
              pagination={false}
              dataSource={deliveries.data?.deliveries ?? []}
              columns={[
                { title: '채널', dataIndex: 'channel', width: 110 },
                { title: '수신자', dataIndex: 'recipient', ellipsis: true },
                {
                  title: '결과',
                  dataIndex: 'succeeded',
                  width: 90,
                  render: (v: boolean) => (v ? '성공' : '실패'),
                },
                {
                  // 실패에는 시각이 없다 — K2 가 찍지 않는다. 그 사실을 그대로 그린다.
                  title: '발송 시각',
                  dataIndex: 'sent_at',
                  width: 190,
                  render: (v: string | null) => (v ? `${absolute(v)} · ${relative(v)}` : '—'),
                },
                {
                  title: '실패 사유',
                  dataIndex: 'failure_reason',
                  ellipsis: true,
                  render: (v?: string) => v || '',
                },
              ]}
            />
          </StateBoundary>
        </Card>

        {e && e.severity === 'critical' && (
          <Alert
            type="info"
            showIcon
            message="계약 F-10 — 심각 등급은 발생 후 30초 안에 발송 기록이 남아야 합니다."
            description="위 발생 시각과 아래 발송 시각을 대조하십시오. 실패한 발송에는 시각이 찍히지 않습니다 — 그것이 30초를 거짓으로 통과하지 못하게 하는 규약입니다."
          />
        )}

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
