/**
 * 시드·훈련 데이터 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/seed — 테넌트별 훈련 상태 · 시드·훈련 기록 · 데이터 출처 분포.
 * 누름: POST /api/dsm/ops/seed/toggle(action = plant · hide · deploy_scenario · end_scenario)
 * → 같은 GET 재조회. 「훈련 시나리오 배포」는 그 테넌트의 훈련 모드를 실제로 켠다(켜진
 * 동안 그 테넌트 알림은 실채널이 아니라 훈련 채널로 간다) · 「훈련 종료」는 끈다.
 */
import { Button, Descriptions, Form, Input, Select, Space, Table, Tag } from 'antd';
import { useState } from 'react';

import {
  fetchSeedBoard,
  toggleSeed,
  type OpsDrillRow,
  type OpsSeedAction,
  type OpsSeedToggleRow,
} from '../api';
import {
  OPS_DONE,
  OPS_FAILED_PREFIX,
  OPS_SEED_ACTION_LABEL,
  OPS_SEED_COPY as C,
  OPS_TAB_LABEL,
} from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

interface SeedForm {
  tenant_code: string;
  scenario_code?: string;
  note?: string;
}

const ACTIONS: { action: OpsSeedAction; gx: string; label: string }[] = [
  { action: 'plant', gx: 'o-12-plant', label: C.plant },
  { action: 'hide', gx: 'o-12-hide', label: C.hide },
  { action: 'deploy_scenario', gx: 'o-12-deploy-scenario', label: C.deploy },
  { action: 'end_scenario', gx: 'o-12-end-scenario', label: C.end },
];

export default function SeedBoard() {
  const board = useOpsBoard(fetchSeedBoard);
  const [form] = Form.useForm<SeedForm>();
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const data = board.data;

  const act = async (action: OpsSeedAction) => {
    let values: SeedForm;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setBusy(action);
    const r = await runOpsAction(() => toggleSeed({ ...values, action }), board.reload);
    setBusy(null);
    setOutcome(
      r.ok ? { ok: true, text: OPS_DONE } : { ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` },
    );
  };

  return (
    <BoardFrame
      gx="o-12"
      title={OPS_TAB_LABEL.seed}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
    >
      <Form form={form} layout="inline" style={{ marginBottom: 16, rowGap: 8 }}>
        <Form.Item name="tenant_code" rules={[{ required: true }]}>
          <Select
            style={{ minWidth: 180 }}
            placeholder={C.tenant}
            data-gx="o-12-tenant"
            options={(data?.drill_by_tenant ?? []).map((t) => ({ value: t.tenant_code, label: t.name }))}
          />
        </Form.Item>
        <Form.Item name="scenario_code">
          <Input placeholder={C.scenario} data-gx="o-12-scenario" />
        </Form.Item>
        <Form.Item name="note">
          <Input placeholder={C.note} data-gx="o-12-note" />
        </Form.Item>
        <Space wrap>
          {ACTIONS.map((a) => (
            <Button
              key={a.action}
              loading={busy === a.action}
              data-gx={a.gx}
              type={a.action === 'deploy_scenario' ? 'primary' : 'default'}
              onClick={() => void act(a.action)}
            >
              {a.label}
            </Button>
          ))}
        </Space>
      </Form>

      <Table<OpsDrillRow>
        rowKey="tenant_code"
        size="small"
        pagination={false}
        dataSource={data?.drill_by_tenant ?? []}
        style={{ marginBottom: 16 }}
        columns={[
          { title: C.tenant, dataIndex: 'name' },
          {
            title: '',
            dataIndex: 'drill_mode',
            render: (on: boolean) => (
              <Tag color={on ? 'orange' : 'green'} data-gx="o-12-drill-state">
                {on ? C.drill : C.live}
              </Tag>
            ),
          },
          { title: C.since, dataIndex: 'since' },
          { title: C.by, dataIndex: 'by' },
        ]}
      />

      {data?.contamination_by_data_source && (
        <Descriptions size="small" title={C.contamination} style={{ marginBottom: 16 }} data-gx="o-12-contamination">
          <Descriptions.Item label={C.seedCount}>{data.contamination_by_data_source.seed}</Descriptions.Item>
          <Descriptions.Item label={C.liveCount}>
            {data.contamination_by_data_source.unknown_or_live}
          </Descriptions.Item>
        </Descriptions>
      )}

      <Table<OpsSeedToggleRow>
        rowKey={(r) => `${r.tenant_code}/${r.scenario_code}`}
        size="small"
        pagination={false}
        dataSource={data?.toggles ?? []}
        data-gx="o-12-history"
        title={() => C.history}
        columns={[
          { title: C.tenant, dataIndex: 'tenant_code' },
          { title: C.scenario, dataIndex: 'scenario_code' },
          {
            title: '',
            dataIndex: 'action',
            render: (a: string) => OPS_SEED_ACTION_LABEL[a] ?? a,
          },
          { title: C.note, dataIndex: 'note' },
          { title: C.since, dataIndex: 'at' },
        ]}
      />
    </BoardFrame>
  );
}
