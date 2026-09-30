/**
 * 플랫폼 감사 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/audit(운영자 행위 전건) · 누름: POST /api/dsm/ops/audit/access-requests
 * (테넌트 열람 요청) · POST …/{request_id}/approve(승인) → 같은 GET 재조회.
 * 승인 뒤에만 GET /api/dsm/ops/tenants/{code}/members 가 열린다(승인 전은 서버가 거절 —
 * 화면은 그 거절 사유를 그대로 보인다).
 */
import { Button, Form, Input, List, Select, Space, Table, Tag } from 'antd';
import { useCallback, useState } from 'react';

import {
  approveTenantAccess,
  fetchAuditLog,
  fetchTenantMembers,
  fetchTenants,
  opsErrorText,
  requestTenantAccess,
  type OpsAuditEntry,
} from '../api';
import {
  OPS_AUDIT_ACTION_LABEL,
  OPS_AUDIT_COPY as C,
  OPS_AUDIT_KIND_LABEL,
  OPS_DONE,
  OPS_FAILED_PREFIX,
  OPS_TAB_LABEL,
} from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

interface RequestForm {
  tenant_code: string;
  reason: string;
}

export default function AuditBoard() {
  const load = useCallback(async () => {
    const [audit, tenants] = await Promise.all([fetchAuditLog(), fetchTenants()]);
    return { ...audit, tenants: tenants.tenants };
  }, []);
  const board = useOpsBoard(load);
  const [form] = Form.useForm<RequestForm>();
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [members, setMembers] = useState<{ code: string; names: string[] } | null>(null);

  const act = async (key: string, call: () => Promise<unknown>) => {
    setBusy(key);
    const r = await runOpsAction(call, board.reload);
    setBusy(null);
    setOutcome(
      r.ok ? { ok: true, text: OPS_DONE } : { ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` },
    );
  };

  const viewMembers = async (code: string) => {
    setBusy(`members/${code}`);
    try {
      const res = await fetchTenantMembers(code);
      setMembers({ code, names: res.members.map((m) => m.name) });
      setOutcome(null);
    } catch (e) {
      setMembers(null);
      setOutcome({ ok: false, text: `${OPS_FAILED_PREFIX}${opsErrorText(e)}` });
    }
    setBusy(null);
  };

  // 요청 행의 최신 상태 — 같은 request_id 의 가장 최근 줄(목록은 최신이 위).
  const latestRequests = new Map<string, OpsAuditEntry>();
  for (const e of board.data?.entries ?? []) {
    if (e.logger === 'guardianx.ops.tenant_access' && e.request_id && !latestRequests.has(e.request_id)) {
      latestRequests.set(e.request_id, e);
    }
  }

  return (
    <BoardFrame
      gx="o-09"
      title={`${OPS_TAB_LABEL.audit} (${board.data?.total ?? 0})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
    >
      <Form
        form={form}
        layout="inline"
        style={{ marginBottom: 16, rowGap: 8 }}
        onFinish={(v: RequestForm) => void act('request', () => requestTenantAccess(v))}
      >
        <Form.Item name="tenant_code" rules={[{ required: true }]}>
          <Select
            style={{ minWidth: 180 }}
            placeholder={C.tenant}
            data-gx="o-09-tenant"
            options={(board.data?.tenants ?? []).map((t) => ({ value: t.tenant_code, label: t.name }))}
          />
        </Form.Item>
        <Form.Item name="reason" rules={[{ required: true }]}>
          <Input placeholder={C.reason} data-gx="o-09-reason" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={busy === 'request'} data-gx="o-09-request-access">
            {C.requestAccess}
          </Button>
        </Form.Item>
      </Form>

      <List
        size="small"
        style={{ marginBottom: 16 }}
        dataSource={[...latestRequests.values()]}
        renderItem={(r) => (
          <List.Item data-gx="o-09-access-request">
            <Space wrap>
              <Tag>{r.tenant_code}</Tag>
              <span>{r.reason}</span>
              <Tag color={r.status === 'approved' ? 'green' : 'gold'} data-gx="o-09-access-status">
                {r.status === 'approved' ? '승인됨' : '요청됨'}
              </Tag>
              {r.status === 'requested' && (
                <Button
                  size="small"
                  loading={busy === `approve/${r.request_id}`}
                  data-gx="o-09-approve"
                  onClick={() =>
                    void act(`approve/${r.request_id}`, () => approveTenantAccess(String(r.request_id)))
                  }
                >
                  {C.approve}
                </Button>
              )}
              <Button
                size="small"
                loading={busy === `members/${r.tenant_code}`}
                data-gx="o-09-view-members"
                onClick={() => void viewMembers(String(r.tenant_code))}
              >
                {C.viewMembers}
              </Button>
            </Space>
          </List.Item>
        )}
      />
      {members && (
        <div data-gx="o-09-members" style={{ marginBottom: 16 }}>
          {`${C.members} (${members.code}): ${members.names.join(', ')}`}
        </div>
      )}

      <Table<OpsAuditEntry>
        rowKey="_audit_id"
        size="small"
        pagination={{ pageSize: 20 }}
        dataSource={board.data?.entries ?? []}
        data-gx="o-09-entries"
        columns={[
          { title: C.at, dataIndex: '_at' },
          { title: C.actor, dataIndex: '_actor' },
          {
            title: C.kind,
            dataIndex: 'logger',
            render: (l: string) => OPS_AUDIT_KIND_LABEL[l] ?? l,
          },
          {
            title: C.action,
            dataIndex: '_action',
            render: (a: string) => OPS_AUDIT_ACTION_LABEL[(a || '').split(':')[0]] ?? a,
          },
          { title: C.tenant, dataIndex: 'tenant_code' },
        ]}
      />
    </BoardFrame>
  );
}
