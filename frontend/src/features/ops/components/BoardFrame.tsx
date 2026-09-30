/**
 * 보드 겉틀 — 제목 · 다시 불러오기 · 결과 문장 칸 · 오류 칸. 턴 AQ · 차선 N2.
 *
 * `gx` 는 절 접두(`o-01` …). 다시 불러오기 단추는 `<gx>-refresh`, 결과 문장 칸은
 * `<gx>-outcome` 으로 선다 — 토스트는 사라지므로 결과는 화면에 남는 칸에 적는다.
 */
import { Alert, Button, Card, Space, Spin, Typography } from 'antd';
import type { ReactNode } from 'react';

import { OPS_ERROR_PREFIX, OPS_FORBIDDEN, OPS_RELOAD } from '../copy';

export interface BoardOutcome {
  ok: boolean;
  text: string;
}

export default function BoardFrame(props: {
  gx: string;
  title: string;
  loading: boolean;
  error: string | null;
  forbidden: boolean;
  outcome: BoardOutcome | null;
  onReload: () => void;
  extra?: ReactNode;
  children?: ReactNode;
}) {
  const { gx, title, loading, error, forbidden, outcome, onReload, extra, children } = props;
  return (
    <Card
      title={title}
      data-gx={`${gx}-board`}
      extra={
        <Space>
          {extra}
          <Button size="small" onClick={onReload} loading={loading} data-gx={`${gx}-refresh`}>
            {OPS_RELOAD}
          </Button>
        </Space>
      }
    >
      {forbidden && <Alert type="warning" showIcon message={OPS_FORBIDDEN} />}
      {error && <Alert type="error" showIcon message={`${OPS_ERROR_PREFIX}${error}`} />}
      {outcome && (
        <Typography.Paragraph
          data-gx={`${gx}-outcome`}
          type={outcome.ok ? 'success' : 'danger'}
          style={{ marginBottom: 12 }}
        >
          {outcome.text}
        </Typography.Paragraph>
      )}
      {loading && !children && <Spin />}
      {!forbidden && children}
    </Card>
  );
}
