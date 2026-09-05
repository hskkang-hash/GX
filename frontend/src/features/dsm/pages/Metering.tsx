/**
 * OPS-16 — **이번 달 사용량** (계량 · 2026-09-05 · 차선 E).
 *
 * 왜 이 화면이 「상용」의 뿌리인가
 * -------------------------------
 * [실측 2026-09-05] 계량 자리가 **0건**이었다. 가격표를 쓸 수는 있어도 **청구할 수는
 * 없었다** — 관리자가 「이번 달에 얼마나 썼나」에 답할 자리가 제품 안에 없었다.
 *
 * ★ **낱말은 우리가 고르지 않았다.** `docs/design/GX-COPY_v1.md` §5 「2026-09-05 턴 E
 *   추가」가 정본이다: 이번 달 사용량 · 카메라 대수 · 쓰는 사람 수 · 이벤트 수 ·
 *   보낸 알림 수 · 저장 용량 · 표 내려받기. 「계량」·「미터링」·「CSV 내보내기」는
 *   기계와 형식의 말이라 화면에 쓰지 않는다.
 *
 * ★ **라벨을 화면이 짓지 않는다.** 다섯 칸의 이름은 **서버가 실어 보낸 것**을 그린다
 *   (`cell.label`). 화면에 한 벌 더 적어 두면 서버의 말과 화면의 말이 갈리고,
 *   갈린 뒤에는 청구서와 화면이 다른 이름으로 같은 수를 부른다.
 *
 * ★ **「못 쟀다」와 「0」을 같은 그림으로 그리지 않는다** (DA-03 §2-5 규칙 1).
 *   저장 용량을 못 쟀는데 「0」으로 그리면 관리자는 「안 썼다」로 읽는다.
 *   서버가 `state: "unknown"` 을 실어 보내고, 이 화면은 그것을 **「못 쟀습니다」**로
 *   그린다 — 숫자 자리에 숫자를 지어 넣지 않는다.
 *
 * ★ **읽기 전용이다.** 이 화면은 아무것도 만들지 않는다 — 계량이 이벤트를 만들면
 *   그 수로 청구하게 된다.
 */
import { Alert, Button, Card, Col, Row, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { DsmApiError, dsmGet, dsmMeteringEndpoint } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';

const { Title, Text, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. GX-COPY §5 그대로. */
export const HEADLINE = '이번 달 사용량';

/** 표에 함께 낼 달 수. 이번 달 + 지난 다섯 달. */
const MONTHS = 6;

interface UsageCell {
  key: string;
  label: string;
  unit: string;
  value: number | null;
  state: 'ok' | 'unknown';
  why?: string;
}

interface Usage {
  title: string;
  month: string;
  tenant: string;
  measured_at: string;
  cells: UsageCell[];
  notifications_failed: number;
  storage_unsized: number | null;
  definitions: Record<string, string>;
}

interface UsageSeries {
  rows: Usage[];
}

/**
 * 바이트를 사람의 단위로. **반올림해서 0이 되는 값은 0으로 그리지 않는다** —
 * 「조금 썼다」와 「안 썼다」는 청구서에서 다른 사실이다.
 */
function humanBytes(value: number | null): string {
  if (value === null || value === undefined) return '못 쟀습니다';
  if (value === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let n = value;
  let i = 0;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i += 1;
  }
  return `${n < 10 ? n.toFixed(2) : Math.round(n)} ${units[i]}`;
}

/** 한 칸의 값을 그린다. **못 쟀으면 숫자를 지어 넣지 않는다.** */
function cellText(cell: UsageCell): string {
  if (cell.value === null) return '못 쟀습니다';
  if (cell.key === 'storage') return humanBytes(cell.value);
  return `${cell.value.toLocaleString()}${cell.unit}`;
}

export default function Metering() {
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState('');

  const usage = useDsmResource<Usage>(
    () => dsmGet<Usage>(dsmMeteringEndpoint.usage),
    [],
  );
  const series = useDsmResource<UsageSeries>(
    () => dsmGet<UsageSeries>(dsmMeteringEndpoint.usageSeries, { months: MONTHS }),
    [],
  );

  /**
   * 「표 내려받기」 — **서버가 만든 표를 받는다.**
   *
   * ★ 화면에서 CSV 를 조립하지 않는다. 조립식이 두 벌이 되면 화면의 표와 청구
   *   근거가 어긋나고, 어긋난 쪽은 대개 화면이다(고객이 들고 가는 것도 화면 쪽이다).
   * ★ `<a href>` 로 붙이지 않는다 — 브라우저의 그 요청은 이 앱의 인증 헤더를
   *   싣지 않아 401 이 오고, 화면에는 **아무 일도 안 일어난 것처럼** 보인다.
   */
  const download = useCallback(async () => {
    setDownloading(true);
    setDownloadError('');
    try {
      const text = await dsmGet<string>(dsmMeteringEndpoint.usageCsv, {
        months: MONTHS,
      });
      const blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `guardianx-사용량-${usage.data?.month ?? ''}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      // 안 풀면 표를 받을 때마다 blob 이 쌓인다 (fetchSnapshotUrl 와 같은 규약).
      URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(
        err instanceof DsmApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : String(err),
      );
    } finally {
      setDownloading(false);
    }
  }, [usage.data]);

  const cells = usage.data?.cells ?? [];
  const unmeasured = cells.filter((c) => c.state === 'unknown');

  const columns = useMemo(
    () => [
      { title: '달', dataIndex: 'month', key: 'month', width: 110 },
      ...(usage.data?.cells ?? []).map((c) => ({
        title: c.label,
        key: c.key,
        align: 'right' as const,
        render: (_: unknown, row: Usage) => {
          const found = row.cells.find((x) => x.key === c.key);
          if (!found) return '—';
          return found.value === null ? (
            <Text type="secondary">못 쟀습니다</Text>
          ) : (
            cellText(found)
          );
        },
      })),
    ],
    [usage.data],
  );

  return (
    <div style={{ padding: 24 }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Space align="baseline" style={{ justifyContent: 'space-between', width: '100%' }}>
          <Title level={4} style={{ margin: 0 }}>
            {HEADLINE}
          </Title>
          <Button loading={downloading} onClick={download} disabled={!usage.data}>
            표 내려받기
          </Button>
        </Space>

        {downloadError && <Alert type="error" showIcon message={downloadError} />}

        <StateBoundary
          state={usage.state}
          reason={usage.reason}
          onRetry={usage.reload}
        >
          <>
            <Text type="secondary">
              {usage.data?.tenant} · {usage.data?.month}
            </Text>
            <Row gutter={[12, 12]} style={{ marginTop: 8 }}>
              {/* 다섯 칸은 24 로 나누어떨어지지 않는다(24/5=4.8) — span 대신 flex 로
                  편다. span 을 4 로 깎으면 줄 끝에 빈 칸이 남고, 5 로 올리면
                  다섯째 칸이 아래로 떨어진다.
                  ⚠ 이 주석이 `map(...) => (` **안쪽 첫 줄**에 있으면 JSX 로는
                    형제 노드 둘이 되어 파싱이 깨진다 — `tsc -p tsconfig.json` 은
                    그것을 못 잡는다(아래 evidence 참조). eslint 가 잡았다. */}
              {cells.map((cell) => (
                <Col key={cell.key} flex="1 1 180px">
                  <Card size="small">
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {cell.label}
                    </Text>
                    <div style={{ fontSize: 22, fontWeight: 600, marginTop: 4 }}>
                      {cell.state === 'unknown' ? (
                        <Text type="secondary" style={{ fontSize: 16 }}>
                          못 쟀습니다
                        </Text>
                      ) : (
                        cellText(cell)
                      )}
                    </div>
                    {cell.why && (
                      <Text type="warning" style={{ fontSize: 11 }}>
                        {cell.why}
                      </Text>
                    )}
                  </Card>
                </Col>
              ))}
            </Row>
          </>
        </StateBoundary>

        {/* 못 잰 칸이 있으면 **말한다.** 조용히 0으로 두면 「안 썼다」가 된다. */}
        {unmeasured.length > 0 && (
          <Alert
            type="warning"
            showIcon
            message="아직 못 잰 칸이 있습니다."
            description={`${unmeasured
              .map((c) => c.label)
              .join(' · ')} — 이 칸은 0이 아니라 「못 쟀다」입니다. 청구 근거로 쓰기 전에 원인을 확인해 주십시오.`}
          />
        )}

        {typeof usage.data?.notifications_failed === 'number' &&
          usage.data.notifications_failed > 0 && (
            <Alert
              type="info"
              showIcon
              message={`보내지 못한 알림 ${usage.data.notifications_failed}건은 「보낸 알림 수」에 들어 있지 않습니다.`}
            />
          )}

        <StateBoundary
          state={series.state}
          reason={series.reason}
          onRetry={series.reload}
        >
          <Card size="small" title="달별 사용량">
            <Table<Usage>
              size="small"
              rowKey="month"
              pagination={false}
              columns={columns}
              dataSource={series.data?.rows ?? []}
            />
          </Card>
        </StateBoundary>

        <Card size="small" title="이 수는 이렇게 셉니다">
          {/* 정의 없는 수는 고객이 다시 셀 수 없고, 다시 못 세는 수는 다툼이 된다. */}
          {cells.map((cell) => (
            <Paragraph key={cell.key} style={{ marginBottom: 4 }}>
              <Tag>{cell.label}</Tag>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {usage.data?.definitions?.[cell.key]}
              </Text>
            </Paragraph>
          ))}
        </Card>
      </Space>
    </div>
  );
}
