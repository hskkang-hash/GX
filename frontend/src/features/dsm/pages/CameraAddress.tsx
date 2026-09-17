/**
 * UX-02 — **카메라 설치 주소를 화면에서 채우는 첫 장.**
 *
 * 왜 이 화면인가
 * --------------
 * 주소를 채우는 길은 지금까지 **관리 명령 하나뿐**이었다. 명령은 설치하는 사람의
 * 도구이고, 카메라를 옮기거나 한 대를 새로 다는 사람은 터미널 앞에 있지 않다.
 * 「채울 수 있다」와 「화면에서 채운다」는 다른 절이고, 이 화면이 뒤쪽이다.
 *
 * ★ **새로 짓지 않았다 — 이미 선 서버 면을 감쌌다.** 부르는 문은 둘 다 있던 것이다:
 *     주소 채움 현황   기존 배지 문 (분모와 함께 낸다)
 *     한 대 채우기     기존 일괄 등록 문에 **한 줄짜리 표**를 보낸다
 *   단건 주소 문을 새로 뚫지 않은 이유: 같은 일을 하는 문이 둘이 되면 판정식이
 *   두 벌이 되고, 두 벌은 반드시 어긋난다. 일괄이 이미 「이름으로 찾아 주소를
 *   채운다」를 하고 있으므로 한 대는 그 표의 한 줄이다.
 *
 * ★ **표가 먼저다.** 쓰기 전에 무엇이 바뀌는지 보여 준다 — 일괄과 같은 규약이고,
 *   같은 판정식을 지난다. 틀린 주소는 없는 주소보다 나쁘다: 그 주소가 알림에 그대로
 *   나가 사람을 엉뚱한 곳으로 보낸다.
 */
import { Alert, Button, Card, Descriptions, Form, Input, Space, Table, Typography } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { dsmEndpoint, dsmGet, dsmPostQuery } from '../api';
import { userFacingError } from '../copy';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';

const { Title, Text } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '카메라 주소 채우기 — 한 대씩';

interface AddressGap {
  total: number;
  with_address: number;
  without_address: number;
  coverage: number;
  measurable: boolean;
}

interface PlanRow {
  line: number;
  name: string;
  action: string;
  reason: string;
  address: string;
}

interface ImportPlan {
  dry_run: boolean;
  fatal: string;
  total: number;
  will_write: number;
  rows: PlanRow[];
}

/** 판정 다섯의 **표시 이름**. 서버 값은 그대로 두고 라벨만 매핑한다. */
const ACTION_LABEL: Record<string, string> = {
  create: '새로 등록',
  update: '주소 채움',
  unchanged: '바뀌는 것 없음',
  error: '채울 수 없음',
};

/**
 * 한 줄짜리 표를 만든다. 머리글은 일괄 등록이 읽는 것과 **같은 이름**이다 —
 * 다르면 같은 파일이 두 자리에서 다르게 읽힌다.
 *
 * ⚠ 쉼표·따옴표·줄바꿈이 든 값은 반드시 감싼다. 안 감싸면 주소 한가운데의 쉼표가
 *   칸을 하나 늘려 **엉뚱한 카메라의 주소**가 된다.
 */
function oneRowCsv(name: string, address: string, detail: string): string {
  const cell = (v: string) => `"${v.replace(/"/g, '""')}"`;
  return `name,address,detail\n${cell(name)},${cell(address)},${cell(detail)}\n`;
}

export default function CameraAddress() {
  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [detail, setDetail] = useState('');
  const [plan, setPlan] = useState<ImportPlan | null>(null);
  const [done, setDone] = useState<ImportPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  /** ★ [UX-31′] 표를 보려던 것인가 채우려던 것인가 — 「다시 시도」가 그 둘을 안 바꾼다. */
  const [lastDryRun, setLastDryRun] = useState<boolean | null>(null);

  const gap = useDsmResource<AddressGap>(
    () => dsmGet(dsmEndpoint.cameraAddressGap),
    [],
  );

  const ready = name.trim().length > 0 && address.trim().length > 0;

  const run = useCallback(
    async (dryRun: boolean) => {
      setBusy(true);
      setError('');
      setLastDryRun(dryRun);
      try {
        // ★ 질의로 보낸다 — 본문이면 422(인자 없음)다.
        const result = await dsmPostQuery<ImportPlan>(dsmEndpoint.cameraImport, {
          csv_text: oneRowCsv(name.trim(), address.trim(), detail.trim()),
          dry_run: dryRun,
        });
        setPlan(result);
        if (dryRun) {
          setDone(null);
        } else {
          setDone(result);
          gap.reload();
        }
      } catch (err) {
        // 400·403 을 한 낱말로 묶지 않는다 — 무엇을 고쳐 다시 보낼지 화면이 말해야 한다.
        setError(userFacingError('CameraAddress', err, '요청이 실패했습니다.'));
      } finally {
        setBusy(false);
      }
    },
    [name, address, detail, gap],
  );

  const rows = useMemo(() => plan?.rows ?? [], [plan]);

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Title level={4} style={{ margin: 0 }}>
          {HEADLINE}
        </Title>

        {/* 분모를 함께 낸다 — 「3대」만 보면 4 중 3인지 400 중 3인지 모른다. */}
        <StateBoundary state={gap.state} reason={gap.reason} status={gap.status} onRetry={gap.reload}>
          <Card size="small">
            <Descriptions size="small" column={3}>
              <Descriptions.Item label="카메라">
                {gap.data?.total ?? 0}대
              </Descriptions.Item>
              <Descriptions.Item label="주소 있음">
                {gap.data?.with_address ?? 0}대
              </Descriptions.Item>
              <Descriptions.Item label="주소 없음">
                {gap.data?.without_address ?? 0}대
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </StateBoundary>

        <Card size="small" title="한 대의 주소를 채웁니다">
          <Form layout="vertical">
            <Form.Item label="카메라 이름" required>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="등록된 카메라 이름과 같아야 합니다."
              />
            </Form.Item>
            <Form.Item label="도로명주소" required>
              <Input
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="경기도 안양시 만안구 안양로 123"
              />
            </Form.Item>
            <Form.Item label="현장 표현">
              <Input
                value={detail}
                onChange={(e) => setDetail(e.target.value)}
                placeholder="정문 · 3층 복도처럼 현장에서 부르는 이름"
              />
            </Form.Item>
            <Space>
              <Button
                type="primary"
                loading={busy}
                disabled={!ready}
                onClick={() => run(true)}
              >
                표 먼저 보기
              </Button>
              <Button
                danger
                loading={busy}
                disabled={!plan || plan.will_write === 0 || Boolean(plan.fatal)}
                onClick={() => run(false)}
              >
                채우기
              </Button>
            </Space>
          </Form>
          <Text type="secondary" style={{ fontSize: 12 }}>
            표를 본 뒤에만 채웁니다. 틀린 주소는 없는 주소보다 나쁩니다 — 알림에 그대로
            나가 사람을 엉뚱한 곳으로 보냅니다.
          </Text>
        </Card>

        {/* ★ [UX-31′] 네 문장 + **살아 있는 단추** — 방금 보낸 그 요청을 그대로 다시 낸다. */}
        {error && (
          <FailureNotice
            title={
              lastDryRun === false
                ? '주소를 채우지 못했습니다.'
                : '표를 만들지 못했습니다.'
            }
            detail={error}
            busy={busy}
            onRetry={lastDryRun === null ? undefined : () => run(lastDryRun)}
          />
        )}

        {plan?.fatal && <Alert type="warning" showIcon message={plan.fatal} />}

        {plan && !plan.fatal && (
          <Card
            size="small"
            title={done ? '채웠습니다' : '이렇게 바뀝니다 (아직 쓰지 않았습니다)'}
          >
            <Table<PlanRow>
              size="small"
              rowKey={(r) => `${r.line}-${r.name}`}
              pagination={false}
              dataSource={rows}
              columns={[
                { title: '카메라', dataIndex: 'name' },
                {
                  title: '판정',
                  dataIndex: 'action',
                  render: (v: string) => ACTION_LABEL[v] ?? v,
                },
                { title: '주소', dataIndex: 'address' },
                { title: '사유', dataIndex: 'reason' },
              ]}
            />
          </Card>
        )}
      </Space>
    </div>
  );
}
