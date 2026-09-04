/**
 * UX-13 **단일 초점 큐** — W1 최상단은 목록이 아니라 **가장 급한 하나**다.
 *
 * 무엇이 문제였나
 * ---------------
 * 지금 W1 은 최신순 목록이다. 최신순이면 새 이벤트가 계속 최상단을 밀어내고,
 * **가장 오래 방치된 사건이 영원히 안 보인다.** 그리고 같은 카메라가 3분 사이 7번
 * 울리면 그 7장이 화면을 채워, 밀려난 자리에 있던 **다른 카메라의 첫 발생**이 사라진다.
 * 이 화면이 막는 것이 정확히 그 두 자리다.
 *
 * 무엇을 그리나
 * -------------
 *   ① **초점 카드 하나** — 대응 시계(UX-14) · 스냅샷 · 버튼 셋.
 *   ② 나머지를 5분 창 `stream+type` 으로 묶은 카드들. 각 카드에 **「×N」 배지**.
 *
 * ★ **이벤트를 접는 것이 아니다.** 원본 건수(`total_events`)를 화면에 **그대로 적는다** —
 *   카드 수(`card_total`)와 다른 수이고, 다른 것이 요점이다. F-14 통계는 원본을 세고
 *   접히는 것은 화면이지 기록이 아니다. 두 수를 나란히 두는 것이 그 약속의 증거다.
 *
 * ★ 「가장 급한」은 **서버가 정한다.** 화면이 정하면 화면마다 다른 하나가 최상단에
 *   오고, 교대 인계에서 두 사람이 다른 사건을 이야기하게 된다.
 *   이 파일에 `sort(` 도 `filter(` 도 없다 — 없는 것이 이 화면의 성질이다.
 *
 * ★ 버튼 셋은 **서버가 준 `allowed_next`** 로 그린다. 화면이 전이표를 따로 들면
 *   **서버가 거절하는 버튼**을 그리게 된다 (D-399).
 */
import { Alert, Badge, Button, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmPost, DsmApiError } from '../api';
import EventSnapshot from '../components/EventSnapshot';
import ResponseClock from '../components/ResponseClock';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../severity';
import { stamp, TIMEZONE_NOTE } from '../time';
import type { FocusQueue as FocusQueueView, QueueCard } from '../types';

const { Text, Title, Paragraph } = Typography;

const REFRESH_MS = 15_000;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = 'W1 단일 초점 — 지금 가장 급한 하나';

function eventPath(id: number): string {
  return `/dsm/events/${id}`;
}

function CardHead({ card }: { card: QueueCard }) {
  return (
    <Space wrap size={6}>
      <Tag color={SEVERITY_COLOR[card.severity] ?? 'default'}>
        {SEVERITY_ICON[card.severity] ?? '•'}{' '}
        {labelOf(SEVERITY_LABEL, card.severity)}
      </Tag>
      <Text strong>{labelOf(EVENT_TYPE_LABEL, card.event_type)}</Text>
      <Text type="secondary">{card.stream_monitor_name || '이름 없는 카메라'}</Text>
      <Tag>{labelOf(RESPONSE_STATE_LABEL, card.response_state)}</Tag>
      {card.count > 1 ? (
        // ★ 「×1」은 배지를 안 단다 — 정보가 아니라 소음이다.
        <Badge
          count={`×${card.count}`}
          style={{ backgroundColor: '#fa541c' }}
          title={
            `같은 카메라·같은 유형이 ${Math.round(card.window_seconds / 60)}분 창 안에 ` +
            `${card.count}번 났습니다. 카드만 묶였고 이벤트 ${card.count}건은 그대로 있습니다 ` +
            `(id: ${card.member_event_ids.join(', ')}).`
          }
        />
      ) : null}
    </Space>
  );
}

export default function FocusQueuePage() {
  const navigate = useNavigate();
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState<string>('');

  const queue = useDsmResource<FocusQueueView>(
    () => dsmGet(dsmEndpoint.eventsQueue, { limit: 200 }),
    [],
    {
      refreshMs: REFRESH_MS,
      isEmpty: (v) => (v?.total_events ?? 0) === 0,
    },
  );

  const advance = useCallback(
    async (eventId: number, toState: string) => {
      setActing(true);
      setActionError('');
      try {
        await dsmPost(dsmEndpoint.response(eventId), { to_state: toState });
        queue.reload();
      } catch (err) {
        // ★ 거절은 4xx 로 온다. 그 문장을 **화면에 그대로 낸다** — 서버가 왜
        //   거절했는지가 화면에 안 닿으면 사용자는 「버튼이 안 먹는다」로 읽는다.
        const message = err instanceof Error ? err.message : String(err);
        const status = err instanceof DsmApiError ? err.status : 0;
        setActionError(`${message}${status ? ` (${status})` : ''}`);
      } finally {
        setActing(false);
      }
    },
    [queue],
  );

  const data = queue.data;
  const focus = data?.focus ?? null;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              {HEADLINE}
            </Title>
          </Col>
          <Col>
            <Text type="secondary">
              {queue.loadedAt ? `갱신 ${stamp(queue.loadedAt)}` : ''} · {TIMEZONE_NOTE}
            </Text>
          </Col>
        </Row>

        <StateBoundary
          state={queue.state}
          reason={queue.reason}
          onRetry={queue.reload}
          emptyText="지금 열려 있는 이벤트가 없습니다 — 평온합니다."
        >
          {data ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* ★ 두 수를 **나란히** 둔다. 접힌 것은 카드이지 기록이 아니다. */}
              <Card size="small">
                <Row gutter={16}>
                  <Col>
                    <Statistic title="이벤트(원본 건수)" value={data.total_events} />
                  </Col>
                  <Col>
                    <Statistic title="카드(5분 창 묶음)" value={data.card_total} />
                  </Col>
                  <Col flex="auto">
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      같은 카메라·같은 유형이{' '}
                      {Math.round(data.window_seconds / 60)}분 창 안에 연속으로 나면
                      카드 한 장에 「×N」으로 묶입니다. <b>이벤트는 접지 않습니다</b> —
                      위 두 수가 다른 것이 그 약속의 증거이고, F-14 통계는 왼쪽 수를 봅니다.
                      {data.sample_capped
                        ? ' ⚠ 표본 상한에 닿았습니다 — 더 오래된 이벤트가 이 화면 밖에 있습니다.'
                        : ''}
                    </Paragraph>
                  </Col>
                </Row>
              </Card>

              {actionError ? (
                <Alert type="error" showIcon message="거절되었습니다." description={actionError} />
              ) : null}

              {focus ? (
                <Card
                  title={<CardHead card={focus} />}
                  extra={
                    <Button type="link" onClick={() => navigate(eventPath(focus.event_id))}>
                      상세 열기
                    </Button>
                  }
                >
                  <Row gutter={16}>
                    <Col xs={24} md={10}>
                      <EventSnapshot
                        eventId={focus.event_id}
                        snapshotPath={focus.snapshot_path}
                        height={240}
                      />
                    </Col>
                    <Col xs={24} md={14}>
                      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                        <div>
                          <Text type="secondary">대응 시계 · 발생 {stamp(focus.occurred_at)}</Text>
                          <ResponseClock
                            occurredAt={focus.occurred_at}
                            closedAt={focus.closed_at}
                            thresholds={data.tier_thresholds_sec}
                          />
                        </div>

                        {/* ★ 버튼은 서버가 준 `allowed_next` 로만 그린다 —
                            화면이 전이표를 들면 서버가 거절하는 버튼을 그리게 된다. */}
                        <Space wrap>
                          {(focus.allowed_next ?? []).map((next) => (
                            <Button
                              key={next}
                              type="primary"
                              loading={acting}
                              onClick={() => advance(focus.event_id, next)}
                            >
                              {labelOf(RESPONSE_STATE_LABEL, next)}(으)로
                            </Button>
                          ))}
                          {(focus.allowed_next ?? []).length === 0 ? (
                            <Text type="secondary">
                              더 갈 곳이 없습니다 — 이 사건은 대응 축의 끝에 있습니다.
                            </Text>
                          ) : null}
                        </Space>

                        {focus.count > 1 ? (
                          <Alert
                            type="info"
                            showIcon
                            message={`이 카드에 ${focus.count}건이 묶여 있습니다.`}
                            description={`이벤트 id: ${focus.member_event_ids.join(', ')} — 카드만 묶였고 기록은 그대로입니다.`}
                          />
                        ) : null}
                      </Space>
                    </Col>
                  </Row>
                </Card>
              ) : (
                <Alert
                  type="success"
                  showIcon
                  message="지금 가장 급한 사건이 없습니다."
                  description="열려 있는 이벤트가 0건입니다 — 못 가져온 것이 아니라 없습니다."
                />
              )}

              {/* 나머지 큐. 초점 하나 아래에 **작게** 둔다 — 여기가 커지면 다시 목록이 된다. */}
              <Card size="small" title={`대기 카드 ${data.queue.length}장`}>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {data.queue.length === 0 ? (
                    <Text type="secondary">대기 중인 카드가 없습니다.</Text>
                  ) : null}
                  {data.queue.map((card) => (
                    <Row
                      key={`${card.stream_monitor_id}-${card.event_type}-${card.event_id}`}
                      align="middle"
                      gutter={12}
                      style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}
                    >
                      <Col flex="auto">
                        <CardHead card={card} />
                        <div>
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            발생 {stamp(card.occurred_at)}
                          </Text>
                        </div>
                      </Col>
                      <Col>
                        <ResponseClock
                          occurredAt={card.occurred_at}
                          closedAt={card.closed_at}
                          thresholds={data.tier_thresholds_sec}
                          compact
                        />
                      </Col>
                      <Col>
                        <Button size="small" onClick={() => navigate(eventPath(card.event_id))}>
                          열기
                        </Button>
                      </Col>
                    </Row>
                  ))}
                </Space>
              </Card>
            </Space>
          ) : null}
        </StateBoundary>
      </Space>
    </Main>
  );
}
