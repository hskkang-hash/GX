/**
 * 릴리스·배포 보드 — 배포 기록 화면. 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/releases — 배포마다 배포 결과 · 걷기 확인 · 되돌리기 시험을 그리고,
 * 최근 배포의 합격(셋 모두 통과)을 한 줄로 보인다. 누름: 「다시 불러오기」(`o-11-refresh`).
 * 배포·되돌리기 집행 자체는 이 화면에서 하지 않는다 — 기록을 읽는다.
 */
import { Descriptions, Table, Tag } from 'antd';

import { fetchReleaseBoard, type OpsDeployRow } from '../api';
import { OPS_NOT_READ, OPS_RELEASE_COPY as C, OPS_TAB_LABEL } from '../copy';
import BoardFrame from './BoardFrame';
import { useOpsBoard } from './useOpsBoard';

function passTag(v: boolean | null | undefined) {
  if (v === true) return <Tag color="green">{C.pass}</Tag>;
  if (v === false) return <Tag color="red">{C.fail}</Tag>;
  return <Tag>—</Tag>;
}

export default function ReleasesBoard() {
  const board = useOpsBoard(fetchReleaseBoard);
  const data = board.data;

  return (
    <BoardFrame
      gx="o-11"
      title={`${OPS_TAB_LABEL.releases} (${data?.count ?? 0})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={null}
      onReload={() => void board.reload()}
    >
      {data && !data.read && <span>{OPS_NOT_READ}</span>}
      {data && data.read && (
        <Descriptions size="small" column={{ xs: 1, md: 4 }} title={C.latest} style={{ marginBottom: 16 }}>
          <Descriptions.Item label={C.exit}>{passTag(data.latest_deploy_exit_ok)}</Descriptions.Item>
          <Descriptions.Item label={C.smoke}>{passTag(data.latest_smoke_ok)}</Descriptions.Item>
          <Descriptions.Item label={C.drill}>
            <span data-gx="o-11-latest-drill">{passTag(data.latest_rollback_drill_ok)}</span>
          </Descriptions.Item>
          <Descriptions.Item label={C.gate}>
            <span data-gx="o-11-gate">{passTag(data.deploy_gate_passed)}</span>
          </Descriptions.Item>
        </Descriptions>
      )}
      <Table<OpsDeployRow>
        rowKey={(r) => `${r.at ?? ''}/${r.commit ?? ''}`}
        size="small"
        pagination={{ pageSize: 20 }}
        dataSource={data?.deploys ?? []}
        data-gx="o-11-deploys"
        columns={[
          { title: C.at, dataIndex: 'at' },
          { title: C.commit, dataIndex: 'commit' },
          { title: C.reason, dataIndex: 'reason' },
          {
            title: C.exit,
            render: (_: unknown, r: OpsDeployRow) => passTag(r.exit === undefined ? null : r.exit === 0),
          },
          {
            title: C.smoke,
            render: (_: unknown, r: OpsDeployRow) =>
              passTag(r.smoke_exit === undefined ? null : r.smoke_exit === 0),
          },
          {
            title: C.drill,
            render: (_: unknown, r: OpsDeployRow) => (
              <span data-gx="o-11-drill">{passTag(r.drill_ok ?? null)}</span>
            ),
          },
        ]}
      />
    </BoardFrame>
  );
}
