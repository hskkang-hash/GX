/**
 * 앱 설치·버전 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/apps · 누름: POST /api/dsm/ops/apps/install(설치·업그레이드) ·
 * POST /api/dsm/ops/apps/status(활성·비활성) → 같은 GET 재조회.
 */
import { Button, Form, Input, Select, Space, Table, Tag } from 'antd';
import { useCallback, useState } from 'react';

import {
  fetchAppInstalls,
  fetchTenants,
  installApp,
  setAppStatus,
  type OpsAppInstallRow,
} from '../api';
import {
  OPS_APP_COPY as C,
  OPS_APP_STATUS_LABEL,
  OPS_DONE,
  OPS_FAILED_PREFIX,
  OPS_TAB_LABEL,
} from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

interface InstallForm {
  tenant_code: string;
  app_code: string;
  version: string;
}

export default function AppsBoard() {
  const load = useCallback(async () => {
    const [apps, tenants] = await Promise.all([fetchAppInstalls(), fetchTenants()]);
    return { ...apps, tenants: tenants.tenants };
  }, []);
  const board = useOpsBoard(load);
  const [form] = Form.useForm<InstallForm>();
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const act = async (key: string, call: () => Promise<unknown>) => {
    setBusy(key);
    const r = await runOpsAction(call, board.reload);
    setBusy(null);
    setOutcome(
      r.ok ? { ok: true, text: OPS_DONE } : { ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` },
    );
  };

  return (
    <BoardFrame
      gx="o-02"
      title={`${OPS_TAB_LABEL.apps} (${board.data?.count ?? 0})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
    >
      <div style={{ marginBottom: 12 }}>
        <Tag data-gx="o-02-marked">
          {C.markedProbe}{' '}
          {board.data?.marked == null ? C.markedUnknown : board.data.marked}
        </Tag>
        {board.data?.marked != null ? (
          <span data-gx="o-02-marked-split">
            {C.markedProbeLabel} {board.data.marked_probe ?? 0} · {C.markedSeedLabel}{' '}
            {board.data.marked_seed ?? 0}{' '}
          </span>
        ) : null}
        <span>{C.markedHint}</span>
      </div>
      <Form
        form={form}
        layout="inline"
        style={{ marginBottom: 16, rowGap: 8 }}
        onFinish={(v: InstallForm) => void act('install', () => installApp(v))}
      >
        <Form.Item name="tenant_code" rules={[{ required: true }]}>
          <Select
            style={{ minWidth: 180 }}
            placeholder={C.tenant}
            data-gx="o-02-tenant"
            options={(board.data?.tenants ?? []).map((t) => ({
              value: t.tenant_code,
              label: t.name,
            }))}
          />
        </Form.Item>
        <Form.Item name="app_code" rules={[{ required: true }]}>
          <Input placeholder={C.app} data-gx="o-02-app" />
        </Form.Item>
        <Form.Item name="version" rules={[{ required: true }]}>
          <Input placeholder={C.version} data-gx="o-02-version" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={busy === 'install'} data-gx="o-02-install">
            {C.install}
          </Button>
        </Form.Item>
      </Form>
      <Table<OpsAppInstallRow>
        rowKey={(r) => `${r.tenant_code}/${r.app_code}`}
        size="small"
        pagination={false}
        dataSource={board.data?.installs ?? []}
        columns={[
          { title: C.tenant, dataIndex: 'tenant_code' },
          { title: C.app, dataIndex: 'app_code' },
          { title: C.version, dataIndex: 'version' },
          { title: C.upgradedFrom, dataIndex: 'upgraded_from' },
          {
            title: C.status,
            dataIndex: 'status',
            render: (s: string) => (
              <Tag color={s === 'active' ? 'green' : 'default'} data-gx="o-02-status">
                {OPS_APP_STATUS_LABEL[s] ?? s}
              </Tag>
            ),
          },
          {
            title: '',
            render: (_: unknown, row: OpsAppInstallRow) => {
              const key = `${row.tenant_code}/${row.app_code}`;
              const next = row.status === 'active' ? 'inactive' : 'active';
              return (
                <Space>
                  <Button
                    size="small"
                    loading={busy === key}
                    data-gx={next === 'inactive' ? 'o-02-deactivate' : 'o-02-activate'}
                    onClick={() =>
                      void act(key, () =>
                        setAppStatus({
                          tenant_code: row.tenant_code,
                          app_code: row.app_code,
                          status: next,
                        }),
                      )
                    }
                  >
                    {next === 'inactive' ? C.deactivate : C.activate}
                  </Button>
                </Space>
              );
            },
          },
        ]}
      />
    </BoardFrame>
  );
}
