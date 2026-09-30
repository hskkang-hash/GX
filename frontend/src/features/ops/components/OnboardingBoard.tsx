/**
 * 온보딩 관제 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/onboarding — 48행 재측 결과 · 역할별 진행률 · 막힌 카드 ·
 * 테넌트별 D-7~D+30 진행 표를 그대로 그린다. 누름: 「다시 불러오기」(`o-08-refresh`).
 */
import { Col, List, Progress, Row, Statistic, Table, Typography } from 'antd';

import { fetchOnboardingBoard, type OpsRoleProgress } from '../api';
import { OPS_NOT_READ, OPS_ONBOARDING_COPY as C, OPS_TAB_LABEL } from '../copy';
import BoardFrame from './BoardFrame';
import { useOpsBoard } from './useOpsBoard';

export default function OnboardingBoard() {
  const board = useOpsBoard(fetchOnboardingBoard);
  const data = board.data;
  const roles = Object.entries(data?.role_progress_6 ?? {}).map(([role, v]) => ({
    role,
    ...(v as OpsRoleProgress),
  }));

  return (
    <BoardFrame
      gx="o-08"
      title={OPS_TAB_LABEL.onboarding}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={null}
      onReload={() => void board.reload()}
    >
      {data && !data.read && <Typography.Text type="secondary">{OPS_NOT_READ}</Typography.Text>}
      {data && data.read && (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={6}>
            <Statistic
              title={C.score}
              value={String(data.score_over_denominator ?? '—')}
              data-gx="o-08-score"
            />
          </Col>
          <Col xs={24} md={18}>
            <Typography.Title level={5}>{C.roleProgress}</Typography.Title>
            <Table
              rowKey="role"
              size="small"
              pagination={false}
              dataSource={roles}
              data-gx="o-08-role-progress"
              columns={[
                { title: C.role, dataIndex: 'role' },
                {
                  title: C.roleProgress,
                  dataIndex: 'ratio',
                  render: (r: number) => <Progress percent={Math.round(r * 100)} size="small" />,
                },
                {
                  title: '',
                  render: (_: unknown, v: OpsRoleProgress) => `${v.green}/${v.total}`,
                },
              ]}
            />
          </Col>
          <Col xs={24} md={12}>
            <Typography.Title level={5}>{C.tenants}</Typography.Title>
            <Table
              rowKey="tenant_code"
              size="small"
              pagination={false}
              dataSource={data.tenants ?? []}
              data-gx="o-08-tenants"
              columns={[
                { title: '테넌트', dataIndex: 'name' },
                { title: C.dayN, dataIndex: 'day_n' },
                { title: C.stage, dataIndex: 'stage' },
              ]}
            />
          </Col>
          <Col xs={24} md={12}>
            <Typography.Title level={5}>{`${C.blocked} (${(data.blocked_cards ?? []).length})`}</Typography.Title>
            <List
              size="small"
              data-gx="o-08-blocked"
              locale={{ emptyText: C.none }}
              dataSource={data.blocked_cards ?? []}
              renderItem={(c) => (
                <List.Item>
                  <Typography.Text strong>{c.row}</Typography.Text>&nbsp;{c.why}
                </List.Item>
              )}
            />
          </Col>
        </Row>
      )}
    </BoardFrame>
  );
}
