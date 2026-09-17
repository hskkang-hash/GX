/**
 * S-16 「알림 받는 사람·채널」 — **등급 × 역할 × 채널** (UX-43 · WS-14 · 턴 S · 차선 U56).
 *
 * 턴 R 에는 이 화면이 **골격**이었다 — 그리고 그 사실을 화면에 적어 두었다:
 * 「이 표를 채우는 문(GET /settings/notify-rules)이 아직 없습니다.」 그 문이 이번 턴에
 * 섰다(`apps/dsm/api_u56.py` · 커널 `kernels/k2_notify/rule_admin.py`). 그래서 이 파일은
 * **골격을 지우고 실제 자료로 바꾼다** — 빈 틀은 이제 거짓이기 때문이다.
 *
 * ★★ 이 화면이 **가장 먼저 그리는 것은 규칙 표가 아니라 「심각이 막혔는가」**다
 * ---------------------------------------------------------------------------
 * 규칙이 있어도 그 역할에 사람이 없으면 **아무에게도 안 간다.** 「규칙 3건」이라고 적힌
 * 표는 그 상태에서도 초록으로 보이고, 그것이 DA-03 §3-2 가 이름 붙인 조용한 무력화다.
 * 그래서 서버가 `critical_blocked` 를 **같은 응답에** 실어 주고, 화면은 그것을 표보다
 * 위에 빨강으로 그린다. 「규칙이 있다」와 「사람이 받는다」는 다른 사실이다(D-301).
 *
 * ★ 「심각 수신자 0명」 저장은 **서버가 409 로 거절한다** — 화면이 막지 않는다
 * ------------------------------------------------------------------------------
 * 화면에서 미리 막으면 그 판정식이 서버 판정의 복제본이 되고, 복제본은 갈린다(D-212).
 * 그리고 화면만 막는 것은 자물쇠가 아니다 — 주소로 직접 부르면 그만이다. 여기서는
 * **누르게 두고 서버의 사유를 그대로 보여 준다.** 그 사유는 서버가 쓴 한국어다.
 *
 * ★ 시험 발송은 **훈련 채널로만** 나간다 — 그 사실을 누르기 **전에** 적는다
 * --------------------------------------------------------------------------
 * 응답의 `reaches_people` 은 언제나 거짓이다. 「보냈습니다」만 그리면 사람은 자기
 * 수신함을 확인하러 가고, 안 온 것을 **고장으로** 읽는다.
 *
 * ★ 채널 목록을 화면이 **짓지 않는다.** 서버가 레지스트리를 읽어 내려 준다
 * (`channels[]` — `available` · `reaches_people` · 사유). 화면이 목록을 들면 U3 이
 * 웹푸시 발송기를 끼우는 날 이 화면만 옛말이 되고, **옛말이 된 것은 안 보인다**(D-286).
 */
import { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd';

import { dsmGet, dsmPostQuery, dsmU56NotifyEndpoint } from '../api';
import StateBoundary from '../components/StateBoundary';
import { userFacingError } from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
import { SEVERITY_COLOR, severityLabel } from '../severity';

const { Title, Paragraph, Text } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '알림 받는 사람·채널';

/** 심각이 막혔을 때의 말. **사전에 없는 문구를 화면에 흩지 않으려고** 여기 상수로 둔다. */
export const CRITICAL_BLOCKED_TITLE = '지금 심각 경보를 받는 사람이 없습니다.';

interface ChannelOption {
  channel: string;
  available: boolean;
  reaches_people: boolean;
  note: string;
  unavailable_reason: string;
}

interface SeverityRow {
  severity: string;
  label: string;
  rule_count: number;
  recipient_count: number;
  human_channels: string[];
  reaches_people: boolean;
}

interface RuleRow {
  rule_id: number;
  severity: string;
  role_code: string;
  role_id: number;
  zone: string | null;
  channels: string[];
  is_active: boolean;
}

interface Overview {
  severities: SeverityRow[];
  rules: RuleRow[];
  channels: ChannelOption[];
  critical_recipient_count: number;
  critical_blocked: boolean;
  test_channel: string;
}

interface TestResult {
  severity: string;
  channel: string;
  reaches_people: boolean;
  recipients: number;
  sent: number;
  note: string;
}

export default function NotifySettingsPage() {
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saved, setSaved] = useState<RuleRow | null>(null);

  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState('');
  const [tested, setTested] = useState<TestResult | null>(null);

  const overview = useDsmResource<Overview>(
    () => dsmGet(dsmU56NotifyEndpoint.list),
    [],
  );

  const data = overview.data;

  /** 고를 수 있는 채널 — **서버가 준 목록 그대로.** 화면이 짓지 않는다. */
  const channelOptions = useMemo(
    () =>
      (data?.channels ?? []).map((c) => ({
        label: c.reaches_people ? c.channel : `${c.channel} (사람에게 안 감)`,
        value: c.channel,
      })),
    [data?.channels],
  );

  const onSave = useCallback(
    async (values: {
      severity: string;
      role_code: string;
      channels: string[];
      zone?: string;
      is_active?: boolean;
      rule_id?: string;
    }) => {
      setSaving(true);
      setSaveError('');
      setSaved(null);
      try {
        const result = await dsmPostQuery<RuleRow>(dsmU56NotifyEndpoint.save, {
          severity: values.severity,
          role_code: values.role_code,
          channels: (values.channels ?? []).join(','),
          zone: values.zone ?? '',
          is_active: values.is_active ?? true,
          // 0 이 「새로 만든다」다 — 서버가 그렇게 읽는다.
          rule_id: Number(values.rule_id ?? 0) || 0,
        });
        setSaved(result);
        overview.reload();
      } catch (err) {
        // ★ 409(심각 0명)의 사유는 **서버가 쓴 한국어**다 — 그대로 보여 준다.
        setSaveError(userFacingError('NotifySettings.save', err, '저장하지 못했습니다.'));
      } finally {
        setSaving(false);
      }
    },
    [overview],
  );

  const onTest = useCallback(
    async (severity: string) => {
      setTesting(true);
      setTestError('');
      setTested(null);
      try {
        const result = await dsmPostQuery<TestResult>(dsmU56NotifyEndpoint.test, {
          severity,
        });
        setTested(result);
      } catch (err) {
        setTestError(
          userFacingError('NotifySettings.test', err, '시험 발송을 하지 못했습니다.'),
        );
      } finally {
        setTesting(false);
      }
    },
    [],
  );

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          등급별로 누가 · 무슨 채널로 받는지 정하는 화면입니다. 규칙은 <b>사람이 아니라
          역할</b>을 가리킵니다 — 인사이동이 있어도 규칙을 고치지 않아도 됩니다.
        </Paragraph>
      </div>

      <StateBoundary
        state={overview.state}
        reason={overview.reason}
        status={overview.status}
        onRetry={overview.reload}
        where="NotifySettings.overview"
      >
        {data ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            {/* ★★ 표보다 먼저 온다 — 「규칙이 있다」가 「사람이 받는다」를 덮지 않게. */}
            {data.critical_blocked ? (
              <Alert
                type="error"
                showIcon
                message={CRITICAL_BLOCKED_TITLE}
                description={
                  '심각 등급 규칙이 없거나, 규칙이 가리키는 역할에 사람이 없습니다. '
                  + '이 상태에서는 재난이 나도 아무에게도 알림이 가지 않습니다. '
                  + '아래에서 심각 규칙을 하나 세우거나 그 역할에 사람을 넣어 주십시오.'
                }
              />
            ) : (
              <Alert
                type="success"
                showIcon
                message={`심각 경보를 받는 사람 ${data.critical_recipient_count}명`}
                description="심각 등급은 최소 한 사람에게 닿습니다."
              />
            )}

            <Card title="등급별 수신 현황">
              <Table<SeverityRow>
                rowKey="severity"
                size="small"
                pagination={false}
                dataSource={data.severities}
                columns={[
                  {
                    title: '등급',
                    dataIndex: 'severity',
                    render: (s: string) => (
                      <Tag color={SEVERITY_COLOR[s]}>{severityLabel(s)}</Tag>
                    ),
                  },
                  { title: '규칙', dataIndex: 'rule_count', render: (n: number) => `${n}건` },
                  {
                    title: '받는 사람',
                    dataIndex: 'recipient_count',
                    render: (n: number) => `${n}명`,
                  },
                  {
                    title: '사람에게 도달',
                    key: 'reach',
                    render: (_: unknown, row: SeverityRow) =>
                      row.reaches_people ? (
                        <Tag color="green">{row.human_channels.join(' · ')}</Tag>
                      ) : (
                        <Tag color="red">닿지 않음</Tag>
                      ),
                  },
                  {
                    title: '시험 발송',
                    key: 'test',
                    render: (_: unknown, row: SeverityRow) => (
                      <Button
                        size="small"
                        loading={testing}
                        onClick={() => onTest(row.severity)}
                      >
                        시험 발송
                      </Button>
                    ),
                  },
                ]}
              />
              <Paragraph type="secondary" style={{ marginTop: 8 }}>
                시험 발송은 <b>훈련 채널({data.test_channel})로만</b> 나갑니다 — 실제
                수신함·휴대전화로는 한 건도 가지 않습니다.
              </Paragraph>
              {testError ? (
                <Alert type="error" showIcon message={testError} />
              ) : null}
              {tested ? (
                <Alert
                  type="info"
                  showIcon
                  message={`시험 발송 — 받을 사람 ${tested.recipients}명 중 ${tested.sent}건이 훈련 채널(${tested.channel})로 나갔습니다.`}
                  description={tested.note}
                />
              ) : null}
            </Card>

            <Card title="규칙 — 등급 × 역할 × 채널">
              <Table<RuleRow>
                rowKey="rule_id"
                size="small"
                pagination={false}
                dataSource={data.rules}
                locale={{ emptyText: '아직 규칙이 없습니다.' }}
                columns={[
                  {
                    title: '등급',
                    dataIndex: 'severity',
                    render: (s: string) => (
                      <Tag color={SEVERITY_COLOR[s]}>{severityLabel(s)}</Tag>
                    ),
                  },
                  { title: '역할', dataIndex: 'role_code' },
                  {
                    title: '구역',
                    dataIndex: 'zone',
                    render: (z: string | null) => z || '모든 구역',
                  },
                  {
                    title: '채널',
                    dataIndex: 'channels',
                    render: (cs: string[]) => cs.join(' · '),
                  },
                  {
                    title: '켜짐',
                    dataIndex: 'is_active',
                    render: (on: boolean) =>
                      on ? <Tag color="green">켜짐</Tag> : <Tag>꺼짐</Tag>,
                  },
                  {
                    title: '',
                    key: 'edit',
                    render: (_: unknown, row: RuleRow) => (
                      <Button
                        size="small"
                        onClick={() =>
                          form.setFieldsValue({
                            severity: row.severity,
                            role_code: row.role_code,
                            channels: row.channels,
                            zone: row.zone ?? '',
                            is_active: row.is_active,
                            rule_id: String(row.rule_id),
                          })
                        }
                      >
                        아래에서 고치기
                      </Button>
                    ),
                  },
                ]}
              />
            </Card>

            <Card title="규칙 세우기 · 고치기">
              <Form
                form={form}
                layout="vertical"
                onFinish={onSave}
                initialValues={{ is_active: true, rule_id: '0' }}
              >
                <Form.Item name="severity" label="등급" rules={[{ required: true }]}>
                  <Select
                    options={data.severities.map((s) => ({
                      label: severityLabel(s.severity),
                      value: s.severity,
                    }))}
                  />
                </Form.Item>
                <Form.Item
                  name="role_code"
                  label="역할 코드"
                  rules={[{ required: true }]}
                  extra="규칙은 사람이 아니라 역할을 가리킵니다 (예: fire_user · operator)."
                >
                  <Input autoComplete="off" />
                </Form.Item>
                <Form.Item
                  name="channels"
                  label="채널"
                  rules={[{ required: true }]}
                  extra="「사람에게 안 감」은 훈련·검수용 채널입니다. 운영 규칙에 넣으면 당직자가 못 받습니다."
                >
                  <Select mode="multiple" options={channelOptions} />
                </Form.Item>
                <Form.Item name="zone" label="구역" extra="비우면 모든 구역에 적용됩니다.">
                  <Input autoComplete="off" />
                </Form.Item>
                <Form.Item name="is_active" label="켜짐" valuePropName="checked">
                  <Switch />
                </Form.Item>
                <Form.Item name="rule_id" hidden>
                  <Input />
                </Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving}>
                    저장
                  </Button>
                  <Button
                    onClick={() => {
                      form.resetFields();
                      setSaved(null);
                      setSaveError('');
                    }}
                  >
                    새 규칙으로
                  </Button>
                </Space>
              </Form>

              {saveError ? (
                <Alert style={{ marginTop: 12 }} type="error" showIcon message={saveError} />
              ) : null}
              {saved ? (
                <Alert
                  style={{ marginTop: 12 }}
                  type="success"
                  showIcon
                  message={`저장했습니다 — 규칙 #${saved.rule_id} · ${severityLabel(saved.severity)} · ${saved.role_code}`}
                  description={`채널 ${saved.channels.join(' · ')}`}
                />
              ) : null}
            </Card>

            <Card title="채널">
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                {data.channels.map((c) => (
                  <div key={c.channel}>
                    <Space>
                      <Text strong>{c.channel}</Text>
                      {c.available ? (
                        <Tag color="green">쓸 수 있음</Tag>
                      ) : (
                        <Tag color="orange">고를 수는 있으나 아직 안 나감</Tag>
                      )}
                      {c.reaches_people ? null : <Tag>사람에게 안 감</Tag>}
                    </Space>
                    <div>
                      <Text type="secondary">{c.note}</Text>
                    </div>
                  </div>
                ))}
              </Space>
              <Paragraph type="secondary" style={{ marginTop: 12 }}>
                「고를 수는 있으나 아직 안 나감」은 규칙에 저장은 되지만 발송기가 아직
                없다는 뜻입니다 — 그 채널만으로는 알림이 도달하지 않습니다.
              </Paragraph>
            </Card>
          </Space>
        ) : null}
      </StateBoundary>
    </Space>
  );
}
