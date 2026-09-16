/**
 * 화면 — **요원별 현황** (UX-35 · U2 #9 「요원별 처리 현황」 · 차선 U24 · 턴 R).
 *
 * ★ 이 턴의 지시는 **골격까지만**이다. 서버(`apps/dsm/stats.py::stats_by_reviewer`)가
 *   내는 값 그대로를 표로 편다 — 이름 짓기·정렬·내보내기 같은 다음 층은 여기 없다.
 *
 * ★ 「없는 것은 없다고 적는다」(D-284 · D-290). 이 집계에는 **사람 이름이 없다** —
 *   서버가 `reviewer_id` 만 낸다(가정: 이름 조인은 다음 파). 화면이 이름을 지어내면
 *   그 이름은 서버가 준 적 없는 값이고, 감사 앞에서 그 이름은 근거가 없다.
 *
 * ★ 이 집계는 **60초 캐시가 허용된다**(WO-01 §5 — 배치 테이블이 아니라 요청 시 집계
 *   + 캐시로 좁힌 것, `apps/dsm/stats.py` 머리말 그대로). 시계·건강 보드가 아니므로
 *   `verify_cache_bypass` 대상이 아니다 — **캐시 처리를 여기 선언한다.**
 *
 * ★ 기간을 안 주면 서버 기본값(최근 30일 · `_DEFAULT_WINDOW`)을 그대로 받는다.
 *   이 화면은 그 값을 다시 계산하지 않고 **서버가 돌려준 `since`·`until`을 그대로
 *   문장으로 적는다** — 두 곳에서 창을 계산하면 어긋난 창이 안 보이게 된다
 *   (`EventList.tsx::windowOf` 머리말과 같은 규약).
 */
import { Card, Space, Table, Typography } from 'antd';

import { dsmEndpoint, dsmGet } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { durationOrAbsent, absolute } from '../time';
import type { ByReviewerResponse, ReviewerRow } from '../types';

const { Title, Text } = Typography;

export default function TeamStatus() {
  const stats = useDsmResource<ByReviewerResponse>(
    () => dsmGet<ByReviewerResponse>(dsmEndpoint.statsByReviewer),
    [],
    { isEmpty: (v) => (v?.reviewers?.length ?? 0) === 0 },
  );

  const rows = stats.data?.reviewers ?? [];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        요원별 현황
      </Title>

      <Card size="small">
        <StateBoundary
          state={stats.state}
          reason={stats.reason}
          status={stats.status}
          onRetry={stats.reload}
          emptyText="이 기간에 판정한 요원이 없습니다. (요청은 성공했고 0명입니다)"
        >
          {stats.data && (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text type="secondary">
                {absolute(stats.data.since)} ~ {absolute(stats.data.until)} · 판정{' '}
                {stats.data.total_reviewed}건 · 요원 {rows.length}명
                {stats.data.capped
                  ? ` (상한 ${stats.data.row_cap}행 — 그 이상은 이 집계 밖입니다)`
                  : ''}
              </Text>
              <Table<ReviewerRow>
                size="small"
                rowKey="reviewer_id"
                dataSource={rows}
                pagination={false}
                columns={[
                  {
                    title: '요원',
                    dataIndex: 'reviewer_id',
                    width: 100,
                    render: (v: number) => `#${v}`,
                  },
                  { title: '판정 건수', dataIndex: 'reviewed_total', width: 110 },
                  { title: '종결', dataIndex: 'closed_total', width: 90 },
                  { title: '오탐 판정', dataIndex: 'false_positive_total', width: 110 },
                  {
                    title: '평균 대응(발생→판정)',
                    dataIndex: 'avg_response_seconds',
                    width: 180,
                    render: (v: number | null) => durationOrAbsent(v, '아직 잴 수 없음'),
                  },
                ]}
              />
            </Space>
          )}
        </StateBoundary>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        이 집계는 최대 60초 지난 값일 수 있습니다(캐시 처리 · 야간 배치 대신 요청 시
        집계 + 60초 캐시). 사람 이름은 아직 이 화면에 없습니다 — 요원 번호로 구분합니다.
      </Text>
    </Space>
  );
}
