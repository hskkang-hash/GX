/**
 * 키·자격 회전 보드 — 회전 절차 화면. 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/keys — 회전 주기 · 회전 필요 수 · 키별 다음 회전일 · 최근 회전
 * 감사 줄. 누름: POST /api/dsm/ops/keys/rotate(tenant_code=키 소유 테넌트 · key_id) →
 * 같은 GET 재조회. 새 키 값은 이 화면에 나타나지 않는다(응답에 비밀 칸이 없다).
 */
import { Alert, Button, Descriptions, Popconfirm, Table, Tag } from 'antd';
import { useState } from 'react';

import { fetchKeyBoard, rotateKey, type OpsKeyRow } from '../api';
import { OPS_DONE, OPS_FAILED_PREFIX, OPS_KEY_COPY as C, OPS_TAB_LABEL } from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));

export default function KeysBoard() {
  const board = useOpsBoard(fetchKeyBoard);
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const data = board.data;
  const last = data?.last_rotation_audit as { rotated_at?: string; tenant_code?: string } | null;

  const rotate = async (row: OpsKeyRow) => {
    setBusy(row.key_id);
    const r = await runOpsAction(
      () => rotateKey({ tenant_code: String(row.owner ?? ''), key_id: Number(row.key_id) }),
      board.reload,
    );
    setBusy(null);
    setOutcome(
      r.ok ? { ok: true, text: OPS_DONE } : { ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` },
    );
  };

  return (
    <BoardFrame
      gx="o-10"
      title={OPS_TAB_LABEL.keys}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
    >
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        message={C.runbookTitle}
        data-gx="o-10-runbook"
        description={
          <ol style={{ margin: 0, paddingLeft: 16, listStyle: 'none' }}>
            {C.runbook.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ol>
        }
      />
      {data && (
        <Descriptions size="small" column={{ xs: 1, md: 3 }} style={{ marginBottom: 16 }}>
          <Descriptions.Item label={C.policy}>{dash(data.policy_days)}</Descriptions.Item>
          <Descriptions.Item label={C.due}>{dash(data.due_count)}</Descriptions.Item>
          <Descriptions.Item label={C.rotationCount}>
            <span data-gx="o-10-rotation-count">{data.rotation_audit_count}</span>
          </Descriptions.Item>
          <Descriptions.Item label={C.lastRotation}>
            <span data-gx="o-10-last-rotation">
              {last ? `${dash(last.tenant_code)} · ${dash(last.rotated_at)}` : '—'}
            </span>
          </Descriptions.Item>
        </Descriptions>
      )}
      <Table<OpsKeyRow>
        rowKey="key_id"
        size="small"
        pagination={{ pageSize: 20 }}
        dataSource={data?.keys ?? []}
        columns={[
          { title: C.owner, dataIndex: 'owner' },
          { title: C.prefix, dataIndex: 'prefix' },
          { title: C.age, dataIndex: 'age_days' },
          {
            title: C.nextDue,
            dataIndex: 'next_rotation_due_at',
            render: (v: string | null, row: OpsKeyRow) => (
              <Tag color={(row.days_left ?? 0) < 0 ? 'red' : 'default'} data-gx="o-10-next-due">
                {dash(v)}
              </Tag>
            ),
          },
          { title: C.why, dataIndex: 'why' },
          {
            title: '',
            render: (_: unknown, row: OpsKeyRow) => (
              <Popconfirm title={C.rotate} onConfirm={() => void rotate(row)}>
                <Button size="small" danger loading={busy === row.key_id} data-gx="o-10-rotate">
                  {C.rotate}
                </Button>
              </Popconfirm>
            ),
          },
        ]}
      />
    </BoardFrame>
  );
}
