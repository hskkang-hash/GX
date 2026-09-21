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
 * ★★ 턴 AA — **「사람 수」로 내던 초록을 걷었다** (P-220 · 차선 U56)
 * -----------------------------------------------------------------
 * [세종 실측 2026-09-21 · 고객 자리] 이 화면 맨 위에 **「심각 경보를 받는 사람
 * 4명」 초록**이 떠 있고, 바로 아래 등급 표의 세 줄이 전부 **「닿지 않음」 빨강**
 * 이었다. 규칙의 채널이 `log`(훈련)뿐이라 **아무에게도 안 갔다** — 같은 화면이
 * 두 말을 했고, 위의 초록이 거짓이었다.
 *
 * 배지를 그리던 서버 칸(`critical_blocked`)이 **사람 수만** 셌기 때문이다. 같은
 * 응답의 등급 표는 `reaches_people`(사람 수 > 0 **그리고** 사람에게 닿는 채널)로
 * 그렸다 — **판정식이 두 벌**이었고 두 벌은 갈렸다(D-212). 이제 배지도 그
 * `reaches_people` 하나를 읽는다(`kernels/k2_notify/rule_admin.py`).
 *
 * ★ 초록에 **닿는 채널 이름을 적는다.** 「4명」만으로는 그 4명이 무엇으로 받는지
 *   알 수 없고, 알 수 없는 초록은 다시 거짓이 될 자리다.
 * ★ 빨강의 사유도 **서버가 쓴 한국어**다(`critical_block_reason`). 「사람이 없다」와
 *   「채널이 사람에게 안 간다」는 다음 손이 다르므로 갈라 말한다(P-221).
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
import {
  hasRoleDisplayName,
  roleCodeTitle,
  roleDisplayName,
} from '../roleNames';
import { SEVERITY_COLOR, severityLabel } from '../severity';

const { Title, Paragraph, Text } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '알림 받는 사람·채널';

/**
 * 심각이 막혔을 때의 말. **사전에 없는 문구를 화면에 흩지 않으려고** 여기 상수로 둔다.
 *
 * ★★ [턴 AB · U56] **머리글도 두 사유를 가른다.**
 *   턴 AA 에 사유(본문)는 갈랐는데 **머리글은 하나였다**: 「지금 심각 경보를 받는
 *   사람이 없습니다.」 그런데 ETRI-Group 의 실제 상태는 **사람이 4명 있고 채널만
 *   훈련용**이다 [실측 2026-09-21 턴 AA]. 그 화면의 머리글은 **거짓말**이었다 —
 *   사람을 더 넣으러 간 운영자는 넣어도 빨강이 안 풀리는 것을 보게 된다.
 *   본문만 고치고 머리글을 안 고치면, 사람이 먼저 읽는 줄이 여전히 틀린 것이다.
 */
export const CRITICAL_BLOCKED_TITLE = '지금 심각 경보를 받는 사람이 없습니다.';

/** 사람은 있는데 **채널이 사람에게 안 가는** 경우의 머리글. 다음 손이 다르다(P-221). */
export const CRITICAL_NO_HUMAN_CHANNEL_TITLE =
  '심각 경보가 사람에게 닿지 않습니다 — 채널이 훈련·검수용뿐입니다.';

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
  /** ★ [턴 AA] 심각이 **사람에게 닿는** 채널들. 비면 「N명」은 거짓이다. */
  critical_human_channels?: string[];
  critical_blocked: boolean;
  /** ★ [턴 AA] 왜 막혔나 — **서버가 쓴 한국어.** 안 막혔으면 빈 문자열. */
  critical_block_reason?: string;
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

/**
 * 막힌 사유의 **갈래** — 「사람이 없다」인가 「채널이 사람에게 안 간다」인가.
 *
 * ★ 판정의 정본은 서버다(`critical_block_reason` · `critical_blocked`). 이 함수는
 *   **머리글을 고르는 데에만** 쓴다 — 서버가 이미 「막혔다」고 말한 뒤에, 그 빨강에
 *   어느 이름을 붙일지만 정한다. 막혔는지 아닌지를 여기서 다시 세지 않는다.
 *   (다시 세면 판정식이 두 벌이 되고, 두 벌은 갈린다 — D-212. 턴 AA 의 거짓 초록이
 *   바로 그 두 벌이었다.)
 */
function blockedByNoPeople(data: Overview): boolean {
  return Number(data.critical_recipient_count ?? 0) === 0;
}

/** 서버가 사유 문장을 안 줄 때만 쓰는 말. **둘을 뭉치지 않는다.** */
function fallbackBlockReason(data: Overview): string {
  return blockedByNoPeople(data)
    ? ('심각 등급 규칙이 없거나, 규칙이 가리키는 역할에 사람이 없습니다. '
      + '이 상태에서는 재난이 나도 아무에게도 알림이 가지 않습니다. '
      + '아래에서 심각 규칙을 하나 세우거나 그 역할에 사람을 넣어 주십시오.')
    : (`심각 규칙이 가리키는 사람은 ${data.critical_recipient_count}명 있지만, `
      + '그 규칙의 채널이 사람에게 닿지 않는 채널뿐입니다(훈련·검수용). '
      + '아래에서 심각 규칙의 채널에 사람에게 닿는 것을 하나 이상 넣어 주십시오.');
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
                data-gx="notify-critical-blocked"
                message={
                  blockedByNoPeople(data)
                    ? CRITICAL_BLOCKED_TITLE
                    : CRITICAL_NO_HUMAN_CHANNEL_TITLE
                }
                description={
                  <Space direction="vertical" size={4}>
                    {/*
                      ★★ [턴 AB · U56] **대비책도 두 사유를 가른다.**
                      종전 대비책 한 줄은 「규칙이 없거나 · 사람이 없습니다」로 둘을
                      뭉쳤다 — 이 화면이 P-221 로 갈라 놓은 바로 그 두 사유를
                      **서버 문장이 안 올 때만** 다시 뭉치고 있었다. 그러면 옛 서버
                      앞에서 운영자가 엉뚱한 쪽을 고치고, 고쳐도 안 풀린다.
                      ⚠ 서버 문장이 정본이다 — 아래는 그것이 **없을 때만** 쓴다.
                         화면이 사유를 짓지 않는다(D-212).
                    */}
                    <span>{data.critical_block_reason || fallbackBlockReason(data)}</span>
                    {/*
                      ★ **초록이 되는 조건을 같은 자리에 적는다.** 빨강이 무엇을
                        해야 풀리는지 말하지 않으면, 사람은 이 화면을 여러 번 열고도
                        같은 빨강을 본다(P-221 — 원인과 다음 손을 같은 줄에).
                    */}
                    {/*
                      ⚠ 별표(마크다운)를 쓰지 않는다 — 이 상자는 마크다운을 안 그리고,
                        그러면 고객이 별표를 글자로 읽는다(서버 `_critical_block_reason`
                        머리말이 같은 이유로 같은 금지를 적어 두었다).
                    */}
                    <Text type="secondary">
                      초록이 되는 조건: 심각 규칙이 가리키는 역할에{' '}
                      <Text strong>사람 1명 이상</Text>, 그 규칙의 채널에{' '}
                      <Text strong>사람에게 닿는 채널 1개 이상</Text>. 둘 다여야 합니다.
                    </Text>
                  </Space>
                }
              />
            ) : (
              <Alert
                type="success"
                showIcon
                data-gx="notify-critical-ok"
                message={
                  `심각 경보를 받는 사람 ${data.critical_recipient_count}명 · `
                  + `${(data.critical_human_channels ?? []).join(' · ')}로 닿습니다`
                }
                description="심각 등급은 최소 한 사람에게, 사람에게 닿는 채널로 갑니다."
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
                  {
                    // ★ [턴 AA · U56] 고객 화면에 영문 내부 코드를 두지 않는다.
                    //   사전에 없는 코드는 **지어내지 않고** 「표시명 없음」이고,
                    //   원래 코드는 `title` 에만 있다(`roleNames.ts` 머리말).
                    title: '역할',
                    dataIndex: 'role_code',
                    render: (code: string) => {
                      const known = hasRoleDisplayName(code);
                      return (
                        <Text
                          type={known ? undefined : 'secondary'}
                          title={roleCodeTitle(code) || undefined}
                        >
                          {roleDisplayName(code)}
                        </Text>
                      );
                    },
                  },
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
                    // ★ [턴 T · U5#9 「누른 뒤」] 한 번 누름으로 규칙 하나가 바뀌는 자리.
                    //   같은 저장 문(`notify-rules/save`)에 켜짐만 뒤집어 보낸다 — 심각을
                    //   0명으로 만드는 끄기는 서버가 409 로 거절하고 그 사유가 아래 칸에 뜬다.
                    render: (on: boolean, row: RuleRow) => (
                      <Space size="small">
                        {on ? <Tag color="green">켜짐</Tag> : <Tag>꺼짐</Tag>}
                        <Button
                          size="small"
                          disabled={saving}
                          onClick={() =>
                            onSave({
                              severity: row.severity,
                              role_code: row.role_code,
                              channels: row.channels,
                              zone: row.zone ?? '',
                              is_active: !on,
                              rule_id: String(row.rule_id),
                            })
                          }
                        >
                          {on ? '끄기' : '켜기'}
                        </Button>
                      </Space>
                    ),
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
                {/*
                  * ★ [턴 AA · U56 · Q 의 표시명 사전 게이트] 여기 본문에 내부 역할 코드
                  *   둘(`fire_user` · `operator`)이 **예시로** 적혀 있었다. 고객 화면의
                  *   본문에 우리 개발 어휘를 두는 것은 표 칸에 두는 것과 같은 일이다.
                  *
                  * ★ 그렇다고 **예시를 표시명으로 바꾸지 않았다.** 이 칸이 서버에 보내는
                  *   값은 표시명이 아니라 **코드**이고, 표시명을 예시로 적으면 사람이
                  *   그것을 그대로 쳐서 없는 역할을 만든다. 그리고 예시로 쓸 만한 코드
                  *   둘 중 하나(`operator`)는 이 사전에 **표시명이 없는 자리**다 —
                  *   거기에 그럴듯한 한국어를 붙이는 것이 `roleNames.ts` 가 막으려는 일이다.
                  *
                  * ★ 그래서 **예시를 빼고 찾는 길을 적는다.** 위 규칙 표의 역할 이름에
                  *   마우스를 올리면 그 역할의 코드가 `title` 로 나온다(같은 턴에 단 것이다).
                  *   「아래에서 고치기」를 누르면 이 칸이 그 코드로 **채워진다** — 사람이
                  *   코드를 외울 일이 없다. 원인과 다음 손을 같은 줄에 둔다(P-221).
                  */}
                <Form.Item
                  name="role_code"
                  label="역할 코드"
                  rules={[{ required: true }]}
                  extra={
                    '규칙은 사람이 아니라 역할을 가리킵니다 — 인사이동이 있어도 규칙을 '
                    + '고치지 않아도 됩니다. 코드를 모르시면 위 규칙 표에서 「아래에서 '
                    + '고치기」를 누르십시오. 이 칸이 그 역할의 코드로 채워집니다.'
                  }
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
                  data-gx="notify-rule-saved"
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
