/**
 * 화면 — **통계** (UX-39 · 차선 U24 · 턴 T · P-164 U24 ①).
 *
 * 이 화면이 닫는 것 셋
 * -------------------
 *   ① **축 5** — 카메라 · 유형 · 심각도 · 판정 · 시간대. 축의 이름과 차례는 **서버가
 *      준다**(`axis_order` · `axis_titles`). 화면이 축 이름을 손으로 들면 행에 축이
 *      늘거나 줄 때 화면만 옛말이 된다. 「구역」 축은 행에 없어 여기 없다 — 지어내지 않는다.
 *   ② **합계 = 목록 수** — 같은 창으로 `GET /events` 를 한 번 더 불러 그 `total` 과
 *      집계의 `total` 을 **나란히 적고 대조한다.** 다르면 빨강으로 말한다(`TeamStatus`
 *      의 「합계 = 행 합」과 같은 규약). 조용한 화면은 「맞다」로 읽힌다.
 *      그리고 축마다 행의 합이 `total` 과 같은지도 적는다 — 어느 행이 두 번 세어지거나
 *      빠지면 그 축이 빨강이다.
 *   ③ **표 내려받기**(GX-COPY 정본 문구) — **서버 라우트** `GET /api/dsm/stats/export.csv`
 *      가 같은 집계를 그대로 CSV 로 편다(UTF-8 BOM). 화면이 파일을 만들지 않는다 —
 *      화면의 수와 파일의 수가 갈리는 첫 자리가 그것이다.
 *
 * ★★ **분모를 손으로 적지 않는다.** 이 화면이 그리는 수는 전부 서버가 준 것이다.
 * ★ 이 집계는 최대 60초 지난 값일 수 있다 — 화면이 그 사실을 아래에 적는다.
 * ★ 기간을 안 주면 서버 기본값(30일)을 받고, 서버가 돌려준 두 끝을 그대로 적는다.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Row,
  Segmented,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { downloadStatsCsv, dsmEndpoint, dsmGet, dsmU24StatsEndpoint } from '../api';
import FailureNotice from '../components/FailureNotice';
import { userFacingError } from '../copy';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { dsmU24Routes } from '../routes.u24';
import { absolute } from '../time';
import type { StatsAxesResponse, StatsAxisRow } from '../types';

const { Title, Text } = Typography;

type PeriodKey = 'server' | 'd7' | 'd30';

const PERIODS: { key: PeriodKey; label: string; days: number | null }[] = [
  { key: 'server', label: '기본 기간', days: null },
  { key: 'd7', label: '7일', days: 7 },
  { key: 'd30', label: '30일', days: 30 },
];

export default function Stats() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<PeriodKey>('server');
  const [downloading, setDownloading] = useState(false);
  /** 내려받기 결과·사유를 남기는 칸 — 사라지는 토스트가 아니다(P-173). */
  const [csvError, setCsvError] = useState<{ text: string; status: number } | null>(null);
  const [csvDone, setCsvDone] = useState<string>('');

  /**
   * 두 끝을 **둘 다** 보낸다 — 여는 쪽만 보내면 창이 아니라 반직선이다.
   * `undefined` 면 서버가 창을 정한다.
   */
  const query = useMemo(() => {
    const days = PERIODS.find((p) => p.key === period)?.days ?? null;
    if (days === null) return undefined;
    const until = new Date();
    const since = new Date(until.getTime() - days * 24 * 60 * 60 * 1000);
    return { since: since.toISOString(), until: until.toISOString() };
  }, [period]);

  const axes = useDsmResource<StatsAxesResponse>(
    () => dsmGet<StatsAxesResponse>(dsmU24StatsEndpoint.axes, query),
    [query],
    { isEmpty: (v) => (v?.total ?? 0) === 0 },
  );

  /**
   * ★ 대조용 목록 — 집계와 **같은 창**(서버가 돌려준 `since`·`until`)으로 목록을 불러
   *   `total` 을 받는다. `limit` 은 서버의 행 상한(`row_cap`)과 같게 — 집계가 자른
   *   자리와 목록이 자른 자리가 같아야 두 수가 같은 것을 센다.
   */
  const win = axes.data ? { since: axes.data.since, until: axes.data.until } : null;
  const list = useDsmResource<{ total: number }>(
    () => dsmGet(dsmEndpoint.events, { ...win!, limit: axes.data!.row_cap }),
    [win?.since, win?.until, axes.data?.row_cap],
    { enabled: Boolean(win) },
  );

  const serverTotal = axes.data?.total ?? 0;
  const listTotal = list.data?.total ?? null;
  const balanced = listTotal !== null && listTotal === serverTotal;

  /**
   * 「표 내려받기」 — 결과도 실패도 **상태 칸**에 남긴다 (턴 U · P-173 · 조율자 지시).
   *
   * ★ 왜 토스트를 뺐나 [차선 F 재스캔 · 2026-09-18]: 토스트는 3초 뒤 사라지고, 사라진
   *   문장은 「안 눌렸다」와 구별되지 않는다. 그리고 실패 토스트에는 **누를 것이 없다** —
   *   사람이 할 수 있는 일은 같은 단추를 스스로 다시 찾는 것뿐이다(`FailureNotice` 머리말).
   *   성공도 칸에 적는다: **받은 바이트 수**가 「받았다」의 증거이고, 0바이트는 성공이 아니다.
   */
  const download = useCallback(async () => {
    setDownloading(true);
    setCsvError(null);
    try {
      const { bytes } = await downloadStatsCsv(query ?? {});
      setCsvDone(`${bytes.toLocaleString()}바이트`);
    } catch (err) {
      setCsvError({
        text: userFacingError('Stats.download', err, '표를 내려받지 못했습니다.'),
        status: (err as { status?: number })?.status ?? 0,
      });
    } finally {
      setDownloading(false);
    }
  }, [query]);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        통계
      </Title>

      <Card size="small">
        <Space wrap align="center">
          <Text type="secondary">기간</Text>
          <Segmented
            value={period}
            onChange={(v) => setPeriod(v as PeriodKey)}
            options={PERIODS.map((p) => ({ value: p.key, label: p.label }))}
          />
          <Button onClick={axes.reload}>새로고침</Button>
          <Button
            type="primary"
            loading={downloading}
            disabled={axes.state !== 'data' && axes.state !== 'empty'}
            onClick={download}
          >
            표 내려받기
          </Button>
          <Button onClick={() => navigate(dsmU24Routes.falsePositive.path)}>
            카메라 오탐률
          </Button>
          <Button onClick={() => navigate('/dsm/team-status')}>요원별 현황</Button>
        </Space>
      </Card>

      {/* ── 내려받기 상태 칸 — 토스트를 쓰지 않는다(P-173 · 새 토스트 0) ────────── */}
      {csvError && (
        <FailureNotice
          title="표를 내려받지 못했습니다."
          detail={csvError.text}
          status={csvError.status}
          busy={downloading}
          onRetry={download}
        />
      )}
      {csvDone && !csvError && (
        <Card size="small">
          <Space wrap>
            <Tag color="green">표를 내려받았습니다</Tag>
            <Text type="secondary">{csvDone}</Text>
          </Space>
        </Card>
      )}

      <Card size="small">
        <StateBoundary
          state={axes.state}
          reason={axes.reason}
          status={axes.status}
          onRetry={axes.reload}
          where="Stats/축"
          emptyText="이 기간에 사건이 없습니다. 기간을 넓혀 보십시오."
        >
          {axes.data && (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text type="secondary">
                {absolute(axes.data.since)} ~ {absolute(axes.data.until)} · 사건{' '}
                {serverTotal}건
                {axes.data.capped
                  ? ` (상한 ${axes.data.row_cap}행 — 그 이상은 이 집계 밖입니다)`
                  : ''}
              </Text>

              {/* ── 합계 대조 — 이 화면의 완결 조건 ②
                  집계의 합계와 같은 창의 목록 수가 같아야 한다. */}
              {list.state === 'loading' && (
                <Alert type="info" showIcon message="목록 수를 대조하는 중입니다." />
              )}
              {(list.state === 'error' || list.state === 'forbidden') && (
                <Alert
                  type="warning"
                  showIcon
                  message="목록 수를 받지 못해 합계를 대조하지 못했습니다."
                  description="대조하지 못한 합계는 맞다고 말할 수 없습니다 — 회색이지 초록이 아닙니다."
                  action={<Button size="small" onClick={list.reload}>다시 대조</Button>}
                />
              )}
              {listTotal !== null && (balanced ? (
                <Alert
                  type="success"
                  showIcon
                  message={`합계가 맞습니다 — 집계 ${serverTotal}건 = 목록 ${listTotal}건`}
                  description="같은 기간으로 사건 목록을 불러 센 수와 이 집계의 합계가 같습니다."
                />
              ) : (
                <Alert
                  type="error"
                  showIcon
                  message={`합계가 맞지 않습니다 — 집계 ${serverTotal}건 · 목록 ${listTotal}건`}
                  description="두 수는 같아야 합니다. 이 화면의 수를 보고서에 옮기기 전에 확인해 주십시오."
                />
              ))}

              <Row gutter={[12, 12]}>
                {axes.data.axis_order.map((axis) => {
                  const rows: StatsAxisRow[] = axes.data!.axes[axis] ?? [];
                  const rowSum = rows.reduce((n, r) => n + (r.count ?? 0), 0);
                  const axisOk = rowSum === serverTotal;
                  const title = axes.data!.axis_titles[axis] ?? axis;
                  return (
                    <Col xs={24} md={12} xl={8} key={axis}>
                      <Card
                        size="small"
                        type="inner"
                        title={
                          <Space size={6}>
                            <span>{title}</span>
                            {axis === 'hour' && (
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                ({axes.data!.hour_tz} 기준)
                              </Text>
                            )}
                          </Space>
                        }
                        extra={
                          axisOk ? (
                            <Tag color="green">행 합 {rowSum} = 합계</Tag>
                          ) : (
                            <Tag color="red">행 합 {rowSum} ≠ 합계 {serverTotal}</Tag>
                          )
                        }
                      >
                        <Table<StatsAxisRow>
                          size="small"
                          rowKey="key"
                          dataSource={rows}
                          pagination={rows.length > 12 ? { pageSize: 12, size: 'small' } : false}
                          columns={[
                            { title, dataIndex: 'label', ellipsis: true },
                            { title: '건수', dataIndex: 'count', width: 80, align: 'right' },
                          ]}
                        />
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            </Space>
          )}
        </StateBoundary>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        이 집계는 최대 60초 지난 값일 수 있습니다. 「표 내려받기」는 서버가 같은 집계를
        그대로 파일로 낸 것입니다(한글이 깨지지 않게 UTF-8 BOM). 구역 축은 사건 행에
        구역 칸이 없어 이 화면에 없습니다.
      </Text>
    </Space>
  );
}
