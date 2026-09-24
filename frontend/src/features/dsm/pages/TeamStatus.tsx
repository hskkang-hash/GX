/**
 * 화면 — **요원별 현황** (S-09 · 부속서A 업무플로우 U2 #9 · 차선 U24 · 턴 S).
 *
 * 턴 R 은 골격이었다(서버가 낸 표를 그대로 폈다). 이번 턴이 닫는 것은 완결 조건 둘이다:
 *
 *   ① **요원 ≥ 2행** — 화면이 행을 접거나 합치지 않는다. 서버가 두 사람을 내면
 *      두 줄이 선다. 한 사람뿐인 기간이면 한 줄뿐이고, 그 사실을 화면이 말한다.
 *   ② **화면에 적힌 수 = 상세를 폈을 때의 수** — 위에 적은 합계와 아래 행들의 합이
 *      **같아야 한다.** 그래서 이 화면은 그 둘을 나란히 적고 **대조한 결과를 말한다.**
 *
 * ★★ **분모를 손으로 적지 않는다.** 이 화면이 그리는 수는 전부 서버가 준 것이다 —
 *   합계는 서버의 합계 칸이고, 「행 합」은 서버가 준 행들을 더한 것이다. 화면이
 *   자기 수를 만들어 적으면 그 수는 아무것도 대조하지 못한다(자기가 자기를 맞춘다).
 *
 * ★ 어긋나면 **어긋났다고 적는다.** 두 수가 다른 날 화면이 조용하면, 그 조용함이
 *   곧 「합계가 맞다」는 거짓 보고가 된다. 빨강을 회색으로 바꾸지 않는다.
 *
 * ★ 「없는 것은 없다고 적는다」. 이 집계에는 **사람 이름이 없다** — 서버가 판정자
 *   번호만 낸다. 화면이 이름을 지어내면 그 이름은 서버가 준 적 없는 값이다.
 *
 * ★ 이 집계는 최대 60초 지난 값일 수 있다(요청 시 집계 + 짧은 캐시). 시계·건강
 *   보드가 아니므로 캐시가 허용된 자리이고, 화면이 그 사실을 아래에 적는다.
 *
 * ★ 기간을 안 주면 **서버 기본값**을 그대로 받는다. 화면은 그 창을 다시 계산하지
 *   않고 서버가 돌려준 두 끝을 그대로 문장으로 적는다 — 두 곳에서 창을 계산하면
 *   어긋난 창이 안 보인다(목록 화면과 같은 규약).
 */
import { Alert, Button, Card, Descriptions, Segmented, Space, Table, Tag, Typography } from 'antd';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { dsmEndpoint, dsmGet } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { durationOrAbsent, absolute } from '../time';
import type { ByReviewerResponse, ReviewerRow } from '../types';

const { Title, Text } = Typography;

/**
 * 기간 단추. **서버가 아는 두 끝으로 보낸다** — 여는 쪽만 보내면 창이 아니라
 * 반직선이 되고, 그러면 「지난 7일」이 「7일 전부터 미래까지」가 된다.
 *
 * `null` 은 「기간을 안 준다」이고, 그때 창은 **서버가 정한다**(기본 30일).
 */
type PeriodKey = 'server' | 'd7' | 'd30';

const PERIODS: { key: PeriodKey; label: string; days: number | null }[] = [
  { key: 'server', label: '기본 기간', days: null },
  { key: 'd7', label: '7일', days: 7 },
  { key: 'd30', label: '30일', days: 30 },
];

export default function TeamStatus() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<PeriodKey>('server');

  const query = useMemo(() => {
    const days = PERIODS.find((p) => p.key === period)?.days ?? null;
    if (days === null) return undefined;
    const until = new Date();
    const since = new Date(until.getTime() - days * 24 * 60 * 60 * 1000);
    return { since: since.toISOString(), until: until.toISOString() };
  }, [period]);

  const stats = useDsmResource<ByReviewerResponse>(
    () => dsmGet<ByReviewerResponse>(dsmEndpoint.statsByReviewer, query),
    [query],
    { isEmpty: (v) => (v?.reviewers?.length ?? 0) === 0 },
  );

  const rows = useMemo(() => stats.data?.reviewers ?? [], [stats.data]);

  /**
   * 아래 행들을 더한 수. **서버가 준 행만 더한다** — 화면이 어디선가 수를 만들어
   * 오면 이 대조는 자기가 자기를 맞추는 일이 된다.
   */
  const rowSum = useMemo(
    () => rows.reduce((n, r) => n + (r.reviewed_total ?? 0), 0),
    [rows],
  );

  const serverTotal = stats.data?.total_reviewed ?? 0;
  const balanced = rowSum === serverTotal;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        요원별 현황
      </Title>

      <Card size="small">
        <Space wrap align="center">
          <Text type="secondary">기간</Text>
          <Segmented
            value={period}
            onChange={(v) => setPeriod(v as PeriodKey)}
            options={PERIODS.map((p) => ({ value: p.key, label: p.label }))}
          />
          <Button onClick={stats.reload}>새로고침</Button>
        </Space>
      </Card>

      <Card size="small">
        <StateBoundary
          state={stats.state}
          reason={stats.reason}
          status={stats.status}
          onRetry={stats.reload}
          where="TeamStatus/요원별"
          emptyText="이 기간에 판정한 요원이 없습니다. 기간을 넓혀 보십시오."
        >
          {stats.data && (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text type="secondary">
                {absolute(stats.data.since)} ~ {absolute(stats.data.until)} · 판정{' '}
                {serverTotal}건 · 요원 {rows.length}명
                {stats.data.capped
                  ? ` (상한 ${stats.data.row_cap}행 — 그 이상은 이 집계 밖입니다)`
                  : ''}
              </Text>

              {/* ── 합계 대조 — 이 화면의 완결 조건 ②
                  위에 적은 판정 건수와 아래 행들의 합이 같아야 한다. 같으면 같다고,
                  다르면 다르다고 적는다. 조용한 화면은 「맞다」로 읽힌다. */}
              {balanced ? (
                <Alert
                  type="success"
                  showIcon
                  message={`합계가 맞습니다 — 위 판정 ${serverTotal}건 = 아래 ${rows.length}명의 합 ${rowSum}건`}
                  description="행을 펴서 각 요원의 판정 건수를 더하면 위에 적힌 수와 같습니다."
                />
              ) : (
                <Alert
                  type="error"
                  showIcon
                  message={`합계가 맞지 않습니다 — 위 판정 ${serverTotal}건 · 아래 ${rows.length}명의 합 ${rowSum}건`}
                  description="두 수는 같아야 합니다. 이 화면의 수를 보고서에 옮기기 전에 확인해 주십시오."
                />
              )}

              {rows.length === 1 && (
                <Text type="secondary">
                  이 기간에 판정한 사람이 한 명뿐입니다. 여러 사람을 견주려면 기간을
                  넓혀 보십시오.
                </Text>
              )}

              <Table<ReviewerRow>
                size="small"
                rowKey="reviewer_id"
                dataSource={rows}
                pagination={false}
                /* ★ 행을 펴면 그 행을 이루는 수가 그대로 나온다 — 위의 합계가
                   어디서 왔는지를 사람이 한 화면에서 되짚는 자리다. */
                expandable={{
                  expandedRowRender: (row) => (
                    <Descriptions
                      size="small"
                      column={{ xs: 1, sm: 2, lg: 4 }}
                      bordered
                    >
                      <Descriptions.Item label="판정 건수">
                        {row.reviewed_total}건
                      </Descriptions.Item>
                      <Descriptions.Item label="종결">
                        {row.closed_total}건
                      </Descriptions.Item>
                      <Descriptions.Item label="오탐 판정">
                        {row.false_positive_total}건
                      </Descriptions.Item>
                      <Descriptions.Item label="평균 대응(발생에서 판정까지)">
                        {durationOrAbsent(row.avg_response_seconds, '아직 잴 수 없음')}
                      </Descriptions.Item>
                    </Descriptions>
                  ),
                }}
                columns={[
                  {
                    title: '요원',
                    dataIndex: 'reviewer_id',
                    width: 110,
                    render: (v: number) => <Tag>{`요원 ${v}`}</Tag>,
                  },
                  { title: '판정 건수', dataIndex: 'reviewed_total', width: 110 },
                  { title: '종결', dataIndex: 'closed_total', width: 90 },
                  { title: '오탐 판정', dataIndex: 'false_positive_total', width: 110 },
                  {
                    title: '평균 대응(발생에서 판정까지)',
                    dataIndex: 'avg_response_seconds',
                    width: 200,
                    render: (v: number | null) => durationOrAbsent(v, '아직 잴 수 없음'),
                  },
                ]}
                summary={() => (
                  <Table.Summary.Row>
                    <Table.Summary.Cell index={0} />
                    <Table.Summary.Cell index={1}>
                      <Text strong>합 {rowSum}건</Text>
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={2}>
                      {rows.reduce((n, r) => n + (r.closed_total ?? 0), 0)}건
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={3}>
                      {rows.reduce((n, r) => n + (r.false_positive_total ?? 0), 0)}건
                    </Table.Summary.Cell>
                    <Table.Summary.Cell index={4} />
                    <Table.Summary.Cell index={5} />
                  </Table.Summary.Row>
                )}
              />
            </Space>
          )}
        </StateBoundary>
      </Card>

      <Card size="small" title="내가 판정한 사건 보기">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <Text type="secondary">
            위 표는 사람별 건수입니다. 사건 하나하나를 보려면 사건 목록에서 봅니다 —
            다만 자기 것만 볼 수 있습니다. 남이 판정한 사건의 목록을 사번으로
            열어 보는 길은 열려 있지 않습니다.
          </Text>
          <Button onClick={() => navigate('/dsm/events?preset=mine')}>
            내가 판정한 사건 열기
          </Button>
        </Space>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        이 집계는 최대 60초 지난 값일 수 있습니다. 사람 이름은 아직 이 화면에
        없습니다 — 요원 번호로 구분합니다.
      </Text>
    </Space>
  );
}
