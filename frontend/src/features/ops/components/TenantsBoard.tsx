/**
 * 테넌트 발급 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/tenants · 누름: POST /api/dsm/ops/tenants(발급) → 같은 GET 재조회.
 */
import { Button, Form, Input, Table, Typography } from 'antd';
import { useState } from 'react';

import { fetchTenants, issueTenant, type OpsTenantRow } from '../api';
import { OPS_DONE, OPS_FAILED_PREFIX, OPS_TAB_LABEL, OPS_TENANT_COPY as C } from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

interface IssueForm {
  code: string;
  name: string;
  region?: string;
  departments?: string;
  domain?: string;
  public_url?: string;
  admin_username: string;
  admin_email: string;
  admin_password: string;
}

export default function TenantsBoard() {
  const board = useOpsBoard(fetchTenants);
  const [form] = Form.useForm<IssueForm>();
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);

  const onIssue = async (values: IssueForm) => {
    setBusy(true);
    const r = await runOpsAction(() => issueTenant(values), board.reload);
    setBusy(false);
    if (r.ok) {
      form.resetFields();
      setOutcome({ ok: true, text: OPS_DONE });
    } else {
      setOutcome({ ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` });
    }
  };

  return (
    <BoardFrame
      gx="o-01"
      title={`${OPS_TAB_LABEL.tenants} (${board.data?.count ?? 0})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
    >
      <Form form={form} layout="inline" onFinish={onIssue} style={{ marginBottom: 16, rowGap: 8 }}>
        <Form.Item name="code" rules={[{ required: true }]}>
          <Input placeholder={C.code} data-gx="o-01-code" />
        </Form.Item>
        <Form.Item name="name" rules={[{ required: true }]}>
          <Input placeholder={C.name} data-gx="o-01-name" />
        </Form.Item>
        <Form.Item name="region">
          <Input placeholder={C.region} data-gx="o-01-region" />
        </Form.Item>
        <Form.Item name="departments">
          <Input placeholder={C.departments} data-gx="o-01-departments" />
        </Form.Item>
        <Form.Item name="domain">
          <Input placeholder={C.domain} data-gx="o-01-domain" />
        </Form.Item>
        <Form.Item name="public_url">
          <Input placeholder={C.publicUrl} data-gx="o-01-public-url" />
        </Form.Item>
        <Form.Item name="admin_username" rules={[{ required: true }]}>
          <Input placeholder={C.adminUsername} data-gx="o-01-admin-username" />
        </Form.Item>
        <Form.Item name="admin_email" rules={[{ required: true }]}>
          <Input placeholder={C.adminEmail} data-gx="o-01-admin-email" />
        </Form.Item>
        <Form.Item name="admin_password" rules={[{ required: true }]}>
          <Input.Password placeholder={C.adminPassword} data-gx="o-01-admin-password" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={busy} data-gx="o-01-issue">
            {C.issue}
          </Button>
        </Form.Item>
      </Form>
      <Typography.Paragraph type="secondary" data-gx="o-01-certificate-note">
        {C.certificate}: {C.certificateNote}
      </Typography.Paragraph>
      <Table<OpsTenantRow>
        rowKey="tenant_code"
        size="small"
        pagination={false}
        dataSource={board.data?.tenants ?? []}
        columns={[
          { title: C.name, dataIndex: 'name' },
          { title: C.code, dataIndex: 'tenant_code' },
          { title: C.region, dataIndex: 'region' },
          {
            title: C.departments,
            render: (_: unknown, row: OpsTenantRow) => (row.departments ?? []).join(', '),
          },
          { title: C.domain, dataIndex: 'domain' },
          { title: C.publicUrl, dataIndex: 'public_url' },
          { title: C.members, dataIndex: 'member_count' },
        ]}
      />
    </BoardFrame>
  );
}
