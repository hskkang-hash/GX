/**
 * S-17 「외부 연계」 — API 키 발급·범위·폐기 · 웹훅 구독(+서명키) · **filters** · health
 * (턴 T · 차선 U56 · P-164 U56 ①).
 *
 * ★★ 비밀 값은 **화면에 그리지 않는다** — 발급 응답에 한 번 오고, 이 화면은 그 값을
 *    **복사 단추 뒤에만** 둔다(DOM 에 글자로 놓지 않는다). 사람에게 보이는 것은
 *    sha256 앞 12자와 길이뿐이다. 「닫기」를 누르거나 화면을 떠나면 값은 사라진다 —
 *    되찾을 수 없고 회전만 가능하다(서버도 원문을 갖지 않는다 · `api.py::issue_api_key`).
 *
 * ★ 누른 뒤에는 **상태 칸**이 말한다 — 토스트가 아니다(사라지는 말은 캡처에 안 남고,
 *   V 도 못 본다). 발급·폐기·필터 저장·해지 넷 다 같은 규약이다.
 *
 * ★ 「범위(scope)」— 인바운드 키의 범위는 키마다가 아니라 **한 벌**이다
 *   (`settings/api_keys` 의 `inbound_capability` · 발급 문에 범위 인자가 없다). 화면은
 *   그 사실을 숨기지 않고 「이 키로 할 수 있는 일」로 그대로 보인다. 키마다 범위를 달리
 *   두려면 표에 칸이 있어야 하고, 그것은 모델·마이그레이션이라 등록 요청 감이다.
 *
 * ★ filters(WS-17) — 구독 목록 문에는 filters 칸이 없어(U3 소유 `api.py`) 구독마다
 *   `GET …/{id}/filters` 를 한 번 더 부른다. 발송기가 이 칸으로 거르는 한 줄은 아직
 *   등록 요청 중이다 — 그동안 화면은 「저장은 되나 발송을 거르지는 않는다」를 **말로** 적는다.
 */
import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';

import {
  dsmDelete,
  dsmGet,
  dsmPostQuery,
  dsmU56Endpoint,
  dsmU56IntegrationEndpoint,
} from '../api';
import StateBoundary from '../components/StateBoundary';
import { userFacingError } from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
import type {
  ApiKeyIssued,
  ApiKeysOverview,
  DsmHealth,
  InboundApiKeyRow,
  WebhookFilters,
  WebhookFiltersView,
  WebhookIssued,
  WebhookSubscriptionRow,
} from '../types';

const { Title, Paragraph, Text } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '외부 연계';

const SEVERITIES = ['info', 'warning', 'critical'] as const;

/** 값을 그리지 않고 **지문**만 만든다 — sha256 앞 12자 · 길이. */
async function fingerprint(secret: string): Promise<{ sha12: string; length: number }> {
  const bytes = new TextEncoder().encode(secret);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  const hex = Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return { sha12: hex.slice(0, 12), length: secret.length };
}

/** 한 번만 오는 비밀 — 복사 단추 뒤에만 두고 글자로는 지문만 보인다. */
function OneTimeSecret({
  label,
  secret,
  onClose,
}: {
  label: string;
  secret: string;
  onClose: () => void;
}) {
  const [fp, setFp] = useState<{ sha12: string; length: number } | null>(null);
  const [copied, setCopied] = useState('');
  useEffect(() => {
    let live = true;
    fingerprint(secret).then((f) => {
      if (live) setFp(f);
    });
    return () => {
      live = false;
    };
  }, [secret]);
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(secret);
      setCopied('복사했습니다 — 이 값은 다시 보이지 않습니다.');
    } catch {
      setCopied('복사하지 못했습니다(브라우저가 클립보드를 막았습니다). 발급을 다시 하려면 회전을 쓰십시오.');
    }
  }, [secret]);
  return (
    <Alert
      type="warning"
      showIcon
      data-gx="one-time-secret"
      message={`${label} — 값은 지금 한 번만 옮겨 적을 수 있습니다`}
      description={
        <Space direction="vertical">
          <Text>
            지문 sha256 앞 12자 <Text code>{fp?.sha12 ?? '…'}</Text> · 길이{' '}
            {fp?.length ?? '…'} — 값은 화면에 그리지 않습니다.
          </Text>
          <Space>
            <Button size="small" type="primary" onClick={copy}>
              값 복사
            </Button>
            <Button size="small" onClick={onClose}>
              닫기(값 버림)
            </Button>
          </Space>
          {copied ? <Text type="secondary">{copied}</Text> : null}
        </Space>
      }
    />
  );
}

function parseCsv(v: unknown): string[] {
  return String(v ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
}

function filtersText(f: WebhookFilters | null | undefined): string {
  if (!f || (!f.type?.length && !f.severity?.length && !f.camera?.length)) {
    return '거르지 않음(전부)';
  }
  const parts: string[] = [];
  if (f.type?.length) parts.push(`종류 ${f.type.join('·')}`);
  if (f.severity?.length) parts.push(`심각도 ${f.severity.join('·')}`);
  if (f.camera?.length) parts.push(`카메라 ${f.camera.join('·')}`);
  return parts.join(' / ');
}

export default function IntegrationsPage() {
  // ── health ───────────────────────────────────────────────────────────
  const health = useDsmResource<DsmHealth>(
    () => dsmGet(dsmU56IntegrationEndpoint.health),
    [],
  );

  // ── API 키 ───────────────────────────────────────────────────────────
  const keys = useDsmResource<ApiKeysOverview>(
    () => dsmGet(dsmU56IntegrationEndpoint.apiKeysOverview),
    [],
  );
  const [keyForm] = Form.useForm();
  const [keyBusy, setKeyBusy] = useState(false);
  const [keyStatus, setKeyStatus] = useState('');
  const [keyError, setKeyError] = useState('');
  const [keySecret, setKeySecret] = useState<{ label: string; secret: string } | null>(null);

  const onIssueKey = useCallback(
    async (values: { name: string; expires_days?: number | null }) => {
      setKeyBusy(true);
      setKeyError('');
      setKeyStatus('');
      try {
        const q: Record<string, string | number | boolean> = { name: values.name };
        if (values.expires_days) q.expires_days = values.expires_days;
        const issued = await dsmPostQuery<ApiKeyIssued>(dsmU56IntegrationEndpoint.apiKeyIssue, q);
        const fp = await fingerprint(issued.secret);
        setKeyStatus(
          `발급됨 — 키 #${issued.key_id} · ${issued.name} · 접두 ${issued.prefix} · 지문 ${fp.sha12} · 길이 ${fp.length} · 감사 #${issued.audit_id}`,
        );
        setKeySecret({ label: `API 키 ${issued.name}`, secret: issued.secret });
        keyForm.resetFields();
        keys.reload();
      } catch (err) {
        setKeyError(userFacingError('Integrations.apiKeyIssue', err, '키를 발급하지 못했습니다.'));
      } finally {
        setKeyBusy(false);
      }
    },
    [keyForm, keys],
  );

  const onRevokeKey = useCallback(
    async (row: InboundApiKeyRow) => {
      setKeyBusy(true);
      setKeyError('');
      setKeyStatus('');
      try {
        const done = await dsmDelete<InboundApiKeyRow & { audit_id?: number }>(
          dsmU56IntegrationEndpoint.apiKeyRevoke(row.key_id),
        );
        setKeyStatus(
          `폐기됨 — 키 #${done.key_id} · ${done.name} · 상태 ${done.status} · 행은 남고 꺼졌습니다`,
        );
        keys.reload();
      } catch (err) {
        setKeyError(userFacingError('Integrations.apiKeyRevoke', err, '키를 폐기하지 못했습니다.'));
      } finally {
        setKeyBusy(false);
      }
    },
    [keys],
  );

  // ── 웹훅 구독 ────────────────────────────────────────────────────────
  const subs = useDsmResource<{ total: number; subscriptions: WebhookSubscriptionRow[] }>(
    () => dsmGet(dsmU56Endpoint.webhookSubscriptions),
    [],
  );
  const [filtersById, setFiltersById] = useState<Record<number, WebhookFilters>>({});
  useEffect(() => {
    const rows = subs.data?.subscriptions ?? [];
    let live = true;
    Promise.all(
      rows.map((r) =>
        dsmGet<WebhookFiltersView>(dsmU56IntegrationEndpoint.webhookFilters(r.subscription_id))
          .then((v) => [r.subscription_id, v.filters] as const)
          .catch(() => [r.subscription_id, {}] as const),
      ),
    ).then((pairs) => {
      if (live) setFiltersById(Object.fromEntries(pairs));
    });
    return () => {
      live = false;
    };
  }, [subs.data]);

  const [hookForm] = Form.useForm();
  const [hookBusy, setHookBusy] = useState(false);
  const [hookStatus, setHookStatus] = useState('');
  const [hookError, setHookError] = useState('');
  const [hookSecret, setHookSecret] = useState<{ label: string; secret: string } | null>(null);

  const [filterForm] = Form.useForm();
  const [filterTarget, setFilterTarget] = useState<number | null>(null);
  const [filterStatus, setFilterStatus] = useState('');
  const [filterError, setFilterError] = useState('');

  const filtersFromForm = (v: Record<string, unknown>): WebhookFilters => {
    const out: WebhookFilters = {};
    const type = parseCsv(v.f_type);
    const severity = ((v.f_severity as string[] | undefined) ?? []).filter(Boolean);
    const camera = parseCsv(v.f_camera);
    if (type.length) out.type = type;
    if (severity.length) out.severity = severity;
    if (camera.length) out.camera = camera;
    return out;
  };

  const onIssueHook = useCallback(
    async (values: Record<string, unknown>) => {
      setHookBusy(true);
      setHookError('');
      setHookStatus('');
      try {
        const filters = filtersFromForm(values);
        const q: Record<string, string | number | boolean> = {
          endpoint_url: String(values.endpoint_url ?? ''),
          event_types: parseCsv(values.event_types).join(','),
          min_severity: String(values.min_severity ?? ''),
          payload_format: String(values.payload_format ?? 'json'),
        };
        if (Object.keys(filters).length) q.filters = JSON.stringify(filters);
        const issued = await dsmPostQuery<WebhookIssued>(
          dsmU56Endpoint.webhookSubscriptionIssue,
          q,
        );
        const fp = await fingerprint(issued.signing_key_secret);
        setHookStatus(
          `구독됨 — 구독 #${issued.subscription_id} · ${issued.endpoint_url} · 서명키 ${issued.signing_key_name} · 지문 ${fp.sha12} · 길이 ${fp.length} · 필터 ${filtersText(issued.filters)} · 감사 #${issued.audit_id}`,
        );
        setHookSecret({ label: `웹훅 서명키 ${issued.signing_key_name}`, secret: issued.signing_key_secret });
        hookForm.resetFields();
        subs.reload();
      } catch (err) {
        setHookError(userFacingError('Integrations.webhookIssue', err, '구독을 만들지 못했습니다.'));
      } finally {
        setHookBusy(false);
      }
    },
    [hookForm, subs],
  );

  const onRevokeHook = useCallback(
    async (row: WebhookSubscriptionRow) => {
      setHookBusy(true);
      setHookError('');
      setHookStatus('');
      try {
        const done = await dsmDelete<WebhookSubscriptionRow>(
          dsmU56IntegrationEndpoint.webhookRevoke(row.subscription_id),
        );
        setHookStatus(
          `해지됨 — 구독 #${done.subscription_id} · ${done.endpoint_url} · 켜짐 ${done.is_active ? '예' : '아니오'} · 행은 남고 꺼졌습니다`,
        );
        subs.reload();
      } catch (err) {
        setHookError(userFacingError('Integrations.webhookRevoke', err, '구독을 해지하지 못했습니다.'));
      } finally {
        setHookBusy(false);
      }
    },
    [subs],
  );

  const onSaveFilters = useCallback(
    async (values: Record<string, unknown>) => {
      if (filterTarget == null) return;
      setFilterError('');
      setFilterStatus('');
      try {
        const filters = filtersFromForm(values);
        const saved = await dsmPostQuery<WebhookFiltersView>(
          dsmU56IntegrationEndpoint.webhookFilters(filterTarget),
          { filters: JSON.stringify(filters) },
        );
        // ★ 왕복 — 저장 응답이 아니라 **재조회**가 상태 칸을 채운다.
        const back = await dsmGet<WebhookFiltersView>(
          dsmU56IntegrationEndpoint.webhookFilters(filterTarget),
        );
        setFiltersById((m) => ({ ...m, [filterTarget]: back.filters }));
        setFilterStatus(
          `필터 저장됨 — 구독 #${saved.subscription_id} · 재조회 ${filtersText(back.filters)} · 감사 #${saved.audit_id ?? '—'}`,
        );
      } catch (err) {
        setFilterError(userFacingError('Integrations.webhookFilters', err, '필터를 저장하지 못했습니다.'));
      }
    },
    [filterTarget],
  );

  const healthData = health.data;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          외부 시스템이 우리를 부를 때 쓰는 <b>API 키</b>와, 우리가 외부로 사건을 내보내는{' '}
          <b>웹훅 구독</b>을 다루는 화면입니다. 비밀 값은 발급 순간에만 옮겨 적을 수 있고 화면에
          다시 보이지 않습니다.
        </Paragraph>
      </div>

      <Card title="서버 상태 (GET /api/dsm/health · 인증 없이)">
        <StateBoundary
          state={health.state}
          reason={health.reason}
          status={health.status}
          onRetry={health.reload}
          where="Integrations.health"
        >
          {healthData ? (
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="전체">
                {healthData.status === 'ok' ? <Tag color="green">ok</Tag> : <Tag color="red">fail</Tag>}{' '}
                <Text type="secondary">스키마 {healthData.schema}</Text>
              </Descriptions.Item>
              {Object.entries(healthData.checks).map(([name, st]) => (
                <Descriptions.Item key={name} label={name}>
                  {st === 'ok' ? <Tag color="green">ok</Tag> : <Tag color="red">fail</Tag>}
                </Descriptions.Item>
              ))}
            </Descriptions>
          ) : null}
        </StateBoundary>
      </Card>

      <Card title="API 키 — 외부가 우리를 부를 때">
        <StateBoundary
          state={keys.state}
          reason={keys.reason}
          status={keys.status}
          onRetry={keys.reload}
          where="Integrations.apiKeys"
        >
          {keys.data ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Alert
                type="info"
                showIcon
                message="범위(이 키로 할 수 있는 일)"
                description={
                  <Text>
                    {keys.data.inbound_api_type || '인바운드'} — {keys.data.inbound_capability || '범위 선언이 비어 있습니다'}
                    <br />
                    <Text type="secondary">범위는 키마다 다르지 않고 한 벌입니다(발급 문에 범위 인자가 없습니다).</Text>
                  </Text>
                }
              />
              <Table<InboundApiKeyRow>
                size="small"
                rowKey="key_id"
                pagination={false}
                dataSource={keys.data.inbound}
                locale={{ emptyText: '발급된 키가 없습니다.' }}
                columns={[
                  { title: '#', dataIndex: 'key_id', width: 60 },
                  { title: '이름', dataIndex: 'name' },
                  { title: '접두', dataIndex: 'prefix', render: (p: string) => <Text code>{p}</Text> },
                  {
                    title: '상태',
                    dataIndex: 'status',
                    render: (s: string, row) =>
                      row.is_active ? <Tag color="green">{s}</Tag> : <Tag>{s}</Tag>,
                  },
                  { title: '만료', dataIndex: 'expires_at', render: (v: string | null) => v ?? '—' },
                  {
                    title: '',
                    key: 'revoke',
                    render: (_: unknown, row) => (
                      <Button
                        size="small"
                        danger
                        disabled={!row.is_active || keyBusy}
                        onClick={() => onRevokeKey(row)}
                      >
                        폐기
                      </Button>
                    ),
                  },
                ]}
              />
              <Form form={keyForm} layout="inline" onFinish={onIssueKey}>
                <Form.Item name="name" label="이름" rules={[{ required: true }]}>
                  <Input autoComplete="off" placeholder="예: 상급기관-연계" />
                </Form.Item>
                <Form.Item name="expires_days" label="만료(일)">
                  <InputNumber min={1} max={3650} placeholder="비우면 무기한" />
                </Form.Item>
                <Form.Item>
                  <Button type="primary" htmlType="submit" loading={keyBusy}>
                    키 발급
                  </Button>
                </Form.Item>
              </Form>
              {keyError ? <Alert type="error" showIcon message={keyError} /> : null}
              {keyStatus ? (
                <Alert type="success" showIcon data-gx="apikey-status" message={keyStatus} />
              ) : null}
              {keySecret ? (
                <OneTimeSecret
                  label={keySecret.label}
                  secret={keySecret.secret}
                  onClose={() => setKeySecret(null)}
                />
              ) : null}
            </Space>
          ) : null}
        </StateBoundary>
      </Card>

      <Card title="웹훅 구독 — 우리가 외부로 사건을 내보낼 때 (CAP 1.2)">
        <StateBoundary
          state={subs.state}
          reason={subs.reason}
          status={subs.status}
          onRetry={subs.reload}
          where="Integrations.webhooks"
        >
          {subs.data ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Table<WebhookSubscriptionRow>
                size="small"
                rowKey="subscription_id"
                pagination={false}
                dataSource={subs.data.subscriptions}
                locale={{ emptyText: '구독이 없습니다.' }}
                columns={[
                  { title: '#', dataIndex: 'subscription_id', width: 60 },
                  { title: '주소', dataIndex: 'endpoint_url' },
                  { title: '서명키 이름', dataIndex: 'signing_key_ref', render: (v: string) => <Text code>{v}</Text> },
                  {
                    title: '필터',
                    key: 'filters',
                    render: (_: unknown, row) => filtersText(filtersById[row.subscription_id]),
                  },
                  {
                    title: '켜짐',
                    dataIndex: 'is_active',
                    render: (on: boolean) => (on ? <Tag color="green">켜짐</Tag> : <Tag>꺼짐</Tag>),
                  },
                  {
                    title: '',
                    key: 'actions',
                    render: (_: unknown, row) => (
                      <Space>
                        <Button
                          size="small"
                          onClick={() => {
                            const f = filtersById[row.subscription_id] ?? {};
                            setFilterTarget(row.subscription_id);
                            setFilterStatus('');
                            setFilterError('');
                            filterForm.setFieldsValue({
                              f_type: (f.type ?? []).join(','),
                              f_severity: f.severity ?? [],
                              f_camera: (f.camera ?? []).join(','),
                            });
                          }}
                        >
                          필터 고치기
                        </Button>
                        <Button
                          size="small"
                          danger
                          disabled={!row.is_active || hookBusy}
                          onClick={() => onRevokeHook(row)}
                        >
                          해지
                        </Button>
                      </Space>
                    ),
                  },
                ]}
              />
              {hookError ? <Alert type="error" showIcon message={hookError} /> : null}
              {hookStatus ? (
                <Alert type="success" showIcon data-gx="webhook-status" message={hookStatus} />
              ) : null}
              {hookSecret ? (
                <OneTimeSecret
                  label={hookSecret.label}
                  secret={hookSecret.secret}
                  onClose={() => setHookSecret(null)}
                />
              ) : null}

              {filterTarget != null ? (
                <Card size="small" title={`구독 #${filterTarget} 필터 — 종류 · 심각도 · 카메라`}>
                  <Paragraph type="secondary">
                    비우면 「거르지 않음」입니다. 카메라는 카메라(stream monitor) 번호를 쉼표로
                    적습니다. ⚠ 발송기가 이 필터로 거르는 배선은 병합에서 조율자가 잇습니다 —
                    그 전까지 저장은 되지만 발송을 거르지는 않습니다.
                  </Paragraph>
                  <Form form={filterForm} layout="vertical" onFinish={onSaveFilters}>
                    <Form.Item name="f_type" label="사건 종류(쉼표)">
                      <Input autoComplete="off" placeholder="fire,smoke" />
                    </Form.Item>
                    <Form.Item name="f_severity" label="심각도">
                      <Select mode="multiple" options={SEVERITIES.map((s) => ({ label: s, value: s }))} />
                    </Form.Item>
                    <Form.Item name="f_camera" label="카메라 번호(쉼표)">
                      <Input autoComplete="off" placeholder="12,15" />
                    </Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit">
                        필터 저장
                      </Button>
                      <Button onClick={() => setFilterTarget(null)}>닫기</Button>
                    </Space>
                  </Form>
                  {filterError ? <Alert style={{ marginTop: 12 }} type="error" showIcon message={filterError} /> : null}
                  {filterStatus ? (
                    <Alert style={{ marginTop: 12 }} type="success" showIcon data-gx="webhook-filters-status" message={filterStatus} />
                  ) : null}
                </Card>
              ) : null}

              <Card size="small" title="새 구독 — 서명키는 서버가 만듭니다">
                <Form
                  form={hookForm}
                  layout="vertical"
                  onFinish={onIssueHook}
                  initialValues={{ payload_format: 'json', min_severity: '', f_severity: [] }}
                >
                  <Form.Item
                    name="endpoint_url"
                    label="받을 주소 (https)"
                    rules={[{ required: true }]}
                    extra="평문 http · 내부망 주소는 서버가 422 로 거절합니다."
                  >
                    <Input autoComplete="off" placeholder="https://partner.example/hook" />
                  </Form.Item>
                  <Form.Item name="event_types" label="사건 종류(쉼표 · 비우면 전부)">
                    <Input autoComplete="off" placeholder="fire,smoke" />
                  </Form.Item>
                  <Form.Item name="min_severity" label="이 등급 이상만">
                    <Select
                      options={[{ label: '전부', value: '' }, ...SEVERITIES.map((s) => ({ label: s, value: s }))]}
                    />
                  </Form.Item>
                  <Form.Item name="payload_format" label="형식">
                    <Select options={[{ label: 'CAP 1.2 (JSON)', value: 'json' }, { label: 'CAP 1.2 (XML)', value: 'xml' }]} />
                  </Form.Item>
                  <Form.Item name="f_type" label="필터 · 사건 종류(쉼표)">
                    <Input autoComplete="off" />
                  </Form.Item>
                  <Form.Item name="f_severity" label="필터 · 심각도">
                    <Select mode="multiple" options={SEVERITIES.map((s) => ({ label: s, value: s }))} />
                  </Form.Item>
                  <Form.Item name="f_camera" label="필터 · 카메라 번호(쉼표)">
                    <Input autoComplete="off" />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" loading={hookBusy}>
                    구독하고 서명키 발급
                  </Button>
                </Form>
              </Card>
            </Space>
          ) : null}
        </StateBoundary>
      </Card>
    </Space>
  );
}
