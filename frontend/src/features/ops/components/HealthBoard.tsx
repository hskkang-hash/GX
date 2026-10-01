/**
 * 건강 보드(전 테넌트) — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/health — 카메라 맥박 · 큐 지연 · 저장 % · 백업 회수증 · 생존 알림 ·
 * 상태 색 · 자동 인시던트를 그대로 그린다. 서버가 「측정하지 않는다」고 밝힌 항목은
 * 「아직 재지 않음」으로 보인다(지어낸 값 0). 다시 불러오기가 곧 다시 재기다 — 빨강이면
 * 서버가 인시던트를 자동으로 연다(중복은 열지 않는다).
 */
import { List, Table, Tag, Typography } from 'antd';
import { fetchHealthBoard, type OpsHealthRow } from '../api';
import {
  OPS_HEALTH_COLOR_LABEL,
  OPS_HEALTH_COPY as C,
  OPS_HEALTH_NOT_MEASURED_LABEL,
  OPS_TAB_LABEL,
} from '../copy';
import BoardFrame from './BoardFrame';
import { useOpsBoard } from './useOpsBoard';

const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));

export default function HealthBoard() {
  const board = useOpsBoard(fetchHealthBoard);
  const notMeasured = Object.keys(board.data?.not_measured ?? {}).map(
    (k) => OPS_HEALTH_NOT_MEASURED_LABEL[k] ?? k,
  );

  return (
    <BoardFrame
      gx="o-05"
      title={`${OPS_TAB_LABEL.health} (${board.data?.tenant_count ?? 0})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={null}
      onReload={() => void board.reload()}
    >
      <Table<OpsHealthRow>
        rowKey="tenant_code"
        size="small"
        pagination={false}
        dataSource={board.data?.tenants ?? []}
        columns={[
          { title: '테넌트', dataIndex: 'name' },
          {
            title: C.cameras,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-cameras">{`${row.cameras.active}/${row.cameras.total}`}</span>
            ),
          },
          {
            title: C.queueLag,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-queue-lag">{dash(row.queue_lag_sec)}</span>
            ),
          },
          {
            title: C.storage,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-storage">{dash(row.storage_used_pct)}</span>
            ),
          },
          {
            title: C.backupReceipt,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-backup-receipt">{dash(row.backup_receipt_at)}</span>
            ),
          },
          {
            title: C.survival,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-survival">{dash(row.survival_alert_late)}</span>
            ),
          },
          {
            title: C.color,
            dataIndex: 'color',
            render: (color: string) => (
              <Tag color={color === 'red' ? 'red' : 'green'} data-gx="o-05-color">
                {OPS_HEALTH_COLOR_LABEL[color] ?? color}
              </Tag>
            ),
          },
          {
            title: C.autoIncident,
            render: (_: unknown, row: OpsHealthRow) => (
              <span data-gx="o-05-auto-incident">{dash(row.auto_incident_id)}</span>
            ),
          },
        ]}
      />
      <div style={{ marginTop: 12 }} data-gx="o-05-5xx">
        <Typography.Text strong>{C.fiveXx}: </Typography.Text>
        {board.data?.front_door?.measured ? (
          <Typography.Text data-gx="o-05-5xx-value">
            {board.data.front_door['5xx']} / {board.data.front_door.total} (
            {board.data.front_door.rate_pct}%)
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary" data-gx="o-05-5xx-unmeasured">
            {C.fiveXxUnmeasured}
          </Typography.Text>
        )}
        <div>
          <Typography.Text type="secondary">{C.fiveXxScope}</Typography.Text>
        </div>
      </div>
      {notMeasured.length > 0 && (
        <div style={{ marginTop: 12 }} data-gx="o-05-not-measured">
          <Typography.Text type="secondary">{C.notMeasured}</Typography.Text>
          <List size="small" dataSource={notMeasured} renderItem={(t) => <List.Item>{t}</List.Item>} />
        </div>
      )}
    </BoardFrame>
  );
}
