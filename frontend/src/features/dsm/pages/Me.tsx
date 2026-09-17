/**
 * S-15 「내 정보」 — 나는 누구이고 **무엇을 받는가** (UX-42-me · 턴 S · 차선 U56).
 *
 * 왜 이 화면이 생겼나
 * -------------------
 * 부속서 A 의 여정표에서 U1 관제요원의 마지막 칸이 「내 정보 확인」이고(온보딩 U1 #7),
 * PRD §5 UX-42-me 는 「이름·이메일·휴대전화·비밀번호 변경·내 알림 설정」을 적었다.
 * 이 화면은 그중 **읽을 수 있는 것부터** 세운다.
 *
 * ★★ **이 화면은 아무것도 쓰지 않는다** — 그리고 그 사실을 화면에 적는다
 * ----------------------------------------------------------------------
 * 「내 알림 설정」(조용 시간 · 담당 구역 · 채널 좁히기)의 **쓰기 면**은 등록부
 * `docs/agent/write_surfaces_v11.yaml` 의 **WS-02 — 차선 U3** 다(표는
 * `DsmNotifyPrefs` · 마이그 0029). 이 차선(U56)이 같은 표에 손을 대면 한 표에 두
 * 차선의 손이 닿고, **그 표가 곧 당직자의 수신 여부**다. 그래서 여기서는 읽기만 한다.
 *
 *   ⚠ 그리고 **빈 칸으로 두지 않는다.** 서버가 `prefs_surface_open: false` 를 주고
 *     화면은 그것을 「아직 이 자리에 설정 화면이 없습니다」로 적는다 —
 *     빈 칸은 「설정이 없다」와 「설정 화면이 없다」를 같은 그림으로 만든다(D-290).
 *
 * ★ **비밀번호 변경 단추를 그리지 않는다.** 그 문은 dj-core 의 것이고(§0.4 — 읽기·호출만),
 *   이 턴에 우리 층에 그 자리가 없다. 누르면 아무 일도 안 일어나는 단추를 만들지 않는다
 *   (턴 R 의 이 화면 골격이 같은 판단으로 단추를 안 뒀다 — 그 판단을 잇는다).
 *
 * ★ 「내가 받는 알림」은 **역할로 답한다.** 규칙은 사람이 아니라 역할을 가리키므로
 *   (모델 머리말), 내가 받는지는 내 역할을 가리키는 규칙이 있는지로만 답할 수 있다.
 */
import {
  Alert,
  Card,
  Descriptions,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';

import { dsmGet, dsmU56NotifyEndpoint } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { SEVERITY_COLOR, severityLabel } from '../severity';

const { Title, Paragraph, Text } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '내 정보';

/** 내 역할을 가리키는 규칙이 하나도 없을 때의 말. */
export const RECEIVES_NOTHING_TITLE = '지금 나에게 오는 알림이 없습니다.';

interface ReceiveRow {
  severity: string;
  channels: string[];
  reaches_people: boolean;
}

interface MeView {
  user_id: number | null;
  username: string;
  email: string;
  display_name: string;
  group_id: number | null;
  group_name: string;
  roles: string[];
  receives: ReceiveRow[];
  receives_nothing: boolean;
  prefs_surface_open: boolean;
}

export default function MePage() {
  const me = useDsmResource<MeView>(() => dsmGet(dsmU56NotifyEndpoint.me), []);
  const data = me.data;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          내 계정과 <b>내가 받는 알림</b>을 보는 화면입니다.
        </Paragraph>
      </div>

      <StateBoundary
        state={me.state}
        reason={me.reason}
        status={me.status}
        onRetry={me.reload}
        where="Me.overview"
      >
        {data ? (
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <Card title="계정">
              <Descriptions column={1} bordered size="small">
                <Descriptions.Item label="아이디">{data.username || '—'}</Descriptions.Item>
                <Descriptions.Item label="표시 이름">
                  {data.display_name || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="이메일">
                  {data.email || (
                    <Text type="danger">
                      등록된 이메일이 없습니다 — 이메일 채널로는 아무것도 받지 못합니다.
                    </Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="소속">
                  {data.group_name || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="역할">
                  {data.roles.length ? (
                    <Space wrap>
                      {data.roles.map((r) => (
                        <Tag key={r}>{r}</Tag>
                      ))}
                    </Space>
                  ) : (
                    <Text type="warning">
                      아직 역할이 없습니다 — 역할이 없으면 알림 규칙이 나를 고르지 못합니다.
                    </Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            <Card title="내가 받는 알림">
              {data.receives_nothing ? (
                <Alert
                  type="warning"
                  showIcon
                  message={RECEIVES_NOTHING_TITLE}
                  description={
                    '내 역할을 가리키는 알림 규칙이 없습니다. 규칙은 사람이 아니라 '
                    + '역할을 가리킵니다 — 관리자에게 역할이나 규칙을 요청하십시오.'
                  }
                />
              ) : (
                <Table<ReceiveRow>
                  rowKey="severity"
                  size="small"
                  pagination={false}
                  dataSource={data.receives}
                  columns={[
                    {
                      title: '등급',
                      dataIndex: 'severity',
                      render: (s: string) => (
                        <Tag color={SEVERITY_COLOR[s]}>{severityLabel(s)}</Tag>
                      ),
                    },
                    {
                      title: '채널',
                      dataIndex: 'channels',
                      render: (cs: string[]) => cs.join(' · '),
                    },
                    {
                      title: '사람에게 도달',
                      dataIndex: 'reaches_people',
                      render: (ok: boolean) =>
                        ok ? (
                          <Tag color="green">도달</Tag>
                        ) : (
                          <Tag color="red">훈련 채널 — 안 옴</Tag>
                        ),
                    },
                  ]}
                />
              )}
            </Card>

            <Card title="내 알림 설정">
              {/* ★ 빈 칸으로 두지 않는다 — 「설정이 없다」와 「설정 화면이 없다」는 다르다. */}
              <Alert
                type="info"
                showIcon
                message="이 자리에 설정 화면이 아직 없습니다."
                description={
                  '근무 외 알림 차단 시간대 · 담당 구역 · 받을 채널 좁히기는 '
                  + '다음 증분에서 이 자리에 섭니다. 설정이 없다는 뜻이 아니라, '
                  + '설정을 바꾸는 화면이 아직 없다는 뜻입니다.'
                }
              />
              <Paragraph type="secondary" style={{ marginTop: 12 }}>
                비밀번호 변경도 아직 이 화면에 없습니다 — 누르면 아무 일도 일어나지 않는
                단추를 두지 않았습니다.
              </Paragraph>
            </Card>
          </Space>
        ) : null}
      </StateBoundary>
    </Space>
  );
}
