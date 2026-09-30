/**
 * 지휘 화면(`CommandHome.tsx`)의 두 칸 — 턴 AQ · 2물결 차선 W2C.
 *
 * - `ResourceBoardCard` — FWS-F2-01 「자원 배치판에 표시」(대기 인원 · 주간/야간
 *   5분대기조 · 위치) · FWS-F2-05 「지휘 화면 배지」(인력·물·헬기·중장비 지원 요청 수).
 *   값은 `GET /api/fws/resources/board?event_id=` 한 번(부모의 `refreshAll` 이 부른다).
 * - `FieldSafetyAlertCard` — FWS-F1-10 「대피 지시·철수」 현장 알림. 대피 지시는 F4-05
 *   승인이 이미 보낸 알림의 도달 수를, 철수는 이 칸의 버튼이 보낸다(기존 알림 경로 ·
 *   `POST .../withdrawal-order`). 누른 뒤에는 부모의 `refreshAll` 이 재조회한다.
 *
 * ★ 이 칸은 상태를 쥐지 않는다 — 그리는 값은 전부 부모가 재조회한 서버 값이다.
 * ★ 지도 렌더 없음(§0.4 인접) — 위치는 좌표 글자로만 보인다.
 */
import { Button, Card, Empty, Input, List, Space, Tag, Typography } from 'antd';

import type { ResourceBoardBody, StandbyStatus, WithdrawalOrdersBody } from '../api_w2c';
import { FWS_COMMAND_COPY as C } from '../copy_command';

const { Text } = Typography;

const STATUS_LABEL: Record<StandbyStatus, string> = {
  standby_day: C.board.statusDay,
  standby_night: C.board.statusNight,
  off_duty: C.board.statusOff,
};

const STATUS_COLOR: Record<StandbyStatus, string> = {
  standby_day: 'blue',
  standby_night: 'purple',
  off_duty: 'default',
};

export function ResourceBoardCard({
  board,
  busy,
  onRefresh,
}: {
  board: ResourceBoardBody | null;
  busy: boolean;
  onRefresh: () => void;
}): JSX.Element {
  const standby = board?.standby ?? null;
  const support = board?.support ?? null;
  return (
    <Card
      title={C.board.title}
      data-gx="fws-f2-01-board"
      extra={
        <Button size="small" disabled={busy} onClick={onRefresh} data-gx="fws-f2-01-board-refresh">
          {C.board.refreshButton}
        </Button>
      }
    >
      {board === null ? (
        <Text type="secondary">{C.board.loadFailed}</Text>
      ) : (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap data-gx="fws-f2-01-standby-counts">
            <Text strong>
              {C.board.onStandbyLabel} {standby?.on_standby ?? 0}
            </Text>
            <Tag color="blue" data-gx="fws-f2-01-count-day">
              {C.board.statusDay} {standby?.counts.standby_day ?? 0}
            </Tag>
            <Tag color="purple" data-gx="fws-f2-01-count-night">
              {C.board.statusNight} {standby?.counts.standby_night ?? 0}
            </Tag>
            <Tag data-gx="fws-f2-01-count-off">
              {C.board.statusOff} {standby?.counts.off_duty ?? 0}
            </Tag>
          </Space>
          <List
            size="small"
            data-gx="fws-f2-01-standby-list"
            dataSource={standby?.people ?? []}
            locale={{ emptyText: C.board.noPeople }}
            renderItem={(p) => (
              <List.Item>
                <Space wrap>
                  <Text>{p.name}</Text>
                  {p.status ? (
                    <Tag color={STATUS_COLOR[p.status]}>{STATUS_LABEL[p.status]}</Tag>
                  ) : null}
                  {p.location ? (
                    <Text type="secondary">
                      {C.board.locationLabel} {p.location.lat}, {p.location.lng}
                    </Text>
                  ) : null}
                  {p.set_at ? <Text type="secondary">{p.set_at}</Text> : null}
                </Space>
              </List.Item>
            )}
          />
          <Text strong>{C.board.supportTitle}</Text>
          <Space wrap data-gx="fws-f2-05-support-badges">
            <Tag color={support?.badges.personnel ? 'red' : 'default'} data-gx="fws-f2-05-badge-personnel">
              {C.board.supportPersonnel} {support?.badges.personnel ?? 0}
            </Tag>
            <Tag color={support?.badges.water ? 'red' : 'default'} data-gx="fws-f2-05-badge-water">
              {C.board.supportWater} {support?.badges.water ?? 0}
            </Tag>
            <Tag color={support?.badges.helicopter ? 'red' : 'default'} data-gx="fws-f2-05-badge-helicopter">
              {C.board.supportHelicopter} {support?.badges.helicopter ?? 0}
            </Tag>
            <Tag
              color={support?.badges.heavy_equipment ? 'red' : 'default'}
              data-gx="fws-f2-05-badge-heavy-equipment"
            >
              {C.board.supportHeavyEquipment} {support?.badges.heavy_equipment ?? 0}
            </Tag>
          </Space>
          {support && support.count > 0 ? (
            <List
              size="small"
              data-gx="fws-f2-05-support-list"
              dataSource={support.requests}
              renderItem={(r) => (
                <List.Item>
                  {supportLabel(r.kind)}
                  {r.amount ? ` · ${r.amount}` : ''}
                  {r.note ? ` · ${r.note}` : ''}
                  {r.requested_at ? ` · ${r.requested_at}` : ''}
                </List.Item>
              )}
            />
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={C.board.noSupport} />
          )}
        </Space>
      )}
    </Card>
  );
}

function supportLabel(kind: string): string {
  switch (kind) {
    case 'personnel':
      return C.board.supportPersonnel;
    case 'water':
      return C.board.supportWater;
    case 'helicopter':
      return C.board.supportHelicopter;
    case 'heavy_equipment':
      return C.board.supportHeavyEquipment;
    default:
      return C.board.supportTitle;
  }
}

export function FieldSafetyAlertCard({
  evacNotifiedCount,
  evacApproved,
  withdrawals,
  reason,
  onReasonChange,
  busy,
  onOrder,
}: {
  evacNotifiedCount: number | null;
  evacApproved: boolean;
  withdrawals: WithdrawalOrdersBody | null;
  reason: string;
  onReasonChange: (v: string) => void;
  busy: boolean;
  onOrder: () => Promise<void>;
}): JSX.Element {
  return (
    <Card title={C.withdrawal.title} data-gx="fws-f1-10-card">
      <Space direction="vertical" style={{ width: '100%' }}>
        <div data-gx="fws-f1-10-evac-notified">
          <Text>
            {C.withdrawal.evacNotifiedLabel}:{' '}
            {evacApproved
              ? `${evacNotifiedCount ?? 0}${C.withdrawal.peopleSuffix}`
              : C.withdrawal.evacNotYet}
          </Text>
        </div>
        <Input
          placeholder={C.withdrawal.reasonPlaceholder}
          value={reason}
          onChange={(e) => onReasonChange(e.target.value)}
          data-gx="fws-f1-10-withdrawal-reason"
        />
        <Button
          danger
          disabled={busy || !reason.trim()}
          onClick={() => void onOrder()}
          data-gx="fws-f1-10-withdrawal-order"
        >
          {C.withdrawal.orderButton}
        </Button>
        <List
          size="small"
          data-gx="fws-f1-10-withdrawal-list"
          header={
            <Text strong>
              {C.withdrawal.ordersLabel} {withdrawals?.count ?? 0}
            </Text>
          }
          dataSource={withdrawals?.orders ?? []}
          locale={{ emptyText: C.withdrawal.none }}
          renderItem={(o) => (
            <List.Item>
              {o.reason} · {o.delivered ?? 0}
              {C.withdrawal.peopleSuffix} · {o.ordered_at ?? ''}
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}
