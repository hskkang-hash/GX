/**
 * 인시던트 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/incidents · 누름: POST /api/dsm/ops/incidents(접수) ·
 * POST …/{id}/respond(1차 대응) · …/{id}/escalate(에스컬레이션) · …/{id}/close(종결·원인)
 * → 같은 GET 재조회. SLA 기한과 종결 보고서는 서버가 계산한 값을 그대로 그린다.
 */
import { Button, Checkbox, Form, Input, Select, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';

import {
  closeIncident,
  escalateIncident,
  fetchIncidents,
  fetchTenants,
  openIncident,
  respondIncident,
  type OpsIncidentRow,
} from '../api';
import {
  OPS_DONE,
  OPS_FAILED_PREFIX,
  OPS_INCIDENT_COPY as C,
  OPS_INCIDENT_STATUS_LABEL,
  OPS_SEVERITY_LABEL,
  OPS_TAB_LABEL,
} from '../copy';
import BoardFrame, { type BoardOutcome } from './BoardFrame';
import { runOpsAction, useOpsBoard } from './useOpsBoard';

interface OpenForm {
  tenant_code: string;
  app_code: string;
  severity: string;
  summary?: string;
}

export default function IncidentsBoard() {
  const [showAll, setShowAll] = useState(false);
  const load = useCallback(async () => {
    const [inc, tenants] = await Promise.all([fetchIncidents(), fetchTenants()]);
    return { ...inc, tenants: tenants.tenants };
  }, []);
  const board = useOpsBoard(load);
  const [form] = Form.useForm<OpenForm>();
  const [outcome, setOutcome] = useState<BoardOutcome | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [cause, setCause] = useState<Record<string, string>>({});
  const [prevention, setPrevention] = useState<Record<string, string>>({});

  const act = async (key: string, call: () => Promise<unknown>) => {
    setBusy(key);
    const r = await runOpsAction(call, board.reload);
    setBusy(null);
    setOutcome(
      r.ok ? { ok: true, text: OPS_DONE } : { ok: false, text: `${OPS_FAILED_PREFIX}${r.message}` },
    );
  };

  const rows = (board.data?.incidents ?? []).filter((r) => showAll || r.status !== 'closed');

  return (
    <BoardFrame
      gx="o-06"
      title={`${OPS_TAB_LABEL.incidents} (${rows.length})`}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={outcome}
      onReload={() => void board.reload()}
      extra={
        <Checkbox checked={showAll} onChange={(e) => setShowAll(e.target.checked)} data-gx="o-06-show-all">
          {C.showAll}
        </Checkbox>
      }
    >
      <Form
        form={form}
        layout="inline"
        style={{ marginBottom: 16, rowGap: 8 }}
        initialValues={{ app_code: 'dsm', severity: 'major' }}
        onFinish={(v: OpenForm) => void act('open', () => openIncident(v))}
      >
        <Form.Item name="tenant_code" rules={[{ required: true }]}>
          <Select
            style={{ minWidth: 180 }}
            placeholder="테넌트"
            data-gx="o-06-tenant"
            options={(board.data?.tenants ?? []).map((t) => ({ value: t.tenant_code, label: t.name }))}
          />
        </Form.Item>
        <Form.Item name="app_code" rules={[{ required: true }]}>
          <Input placeholder="앱" data-gx="o-06-app" />
        </Form.Item>
        <Form.Item name="severity" rules={[{ required: true }]}>
          <Select
            style={{ minWidth: 100 }}
            data-gx="o-06-severity"
            options={Object.entries(OPS_SEVERITY_LABEL).map(([value, label]) => ({ value, label }))}
          />
        </Form.Item>
        <Form.Item name="summary">
          <Input placeholder={C.summary} data-gx="o-06-summary" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" loading={busy === 'open'} data-gx="o-06-open">
            {C.open}
          </Button>
        </Form.Item>
      </Form>
      <Table<OpsIncidentRow>
        rowKey="incident_id"
        size="small"
        pagination={false}
        dataSource={rows}
        expandable={{
          rowExpandable: (r) => Boolean(r.closing_report),
          expandedRowRender: (r) => (
            <Typography.Paragraph data-gx="o-06-closing-report">
              {C.report}: {r.closing_report}
            </Typography.Paragraph>
          ),
        }}
        columns={[
          { title: '테넌트', dataIndex: 'tenant_code' },
          { title: '앱', dataIndex: 'app_code' },
          {
            title: '심각도',
            dataIndex: 'severity',
            render: (s: string) => OPS_SEVERITY_LABEL[s] ?? s,
          },
          {
            title: '상태',
            dataIndex: 'status',
            render: (s: string) => (
              <Tag data-gx="o-06-status">{OPS_INCIDENT_STATUS_LABEL[s] ?? s}</Tag>
            ),
          },
          { title: C.summary, dataIndex: 'summary' },
          { title: C.firstDue, dataIndex: 'sla_first_response_due' },
          { title: C.escalationDue, dataIndex: 'sla_escalation_due' },
          {
            title: '',
            render: (_: unknown, r: OpsIncidentRow) => {
              if (r.status === 'closed') return null;
              const id = r.incident_id;
              return (
                <Space wrap>
                  {r.status === 'open' && (
                    <Button
                      size="small"
                      loading={busy === `${id}/respond`}
                      data-gx="o-06-respond"
                      onClick={() => void act(`${id}/respond`, () => respondIncident(id))}
                    >
                      {C.respond}
                    </Button>
                  )}
                  {(r.status === 'open' || r.status === 'acknowledged') && (
                    <Button
                      size="small"
                      loading={busy === `${id}/escalate`}
                      data-gx="o-06-escalate"
                      onClick={() => void act(`${id}/escalate`, () => escalateIncident(id))}
                    >
                      {C.escalate}
                    </Button>
                  )}
                  <Input
                    size="small"
                    style={{ width: 140 }}
                    placeholder={C.cause}
                    value={cause[id] ?? ''}
                    data-gx="o-06-cause"
                    onChange={(e) => setCause({ ...cause, [id]: e.target.value })}
                  />
                  <Input
                    size="small"
                    style={{ width: 140 }}
                    placeholder={C.prevention}
                    value={prevention[id] ?? ''}
                    data-gx="o-06-prevention"
                    onChange={(e) => setPrevention({ ...prevention, [id]: e.target.value })}
                  />
                  <Button
                    size="small"
                    danger
                    disabled={!(cause[id] ?? '').trim()}
                    loading={busy === `${id}/close`}
                    data-gx="o-06-close"
                    onClick={() =>
                      void act(`${id}/close`, () =>
                        closeIncident(id, (cause[id] ?? '').trim(), (prevention[id] ?? '').trim()),
                      )
                    }
                  >
                    {C.close}
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
