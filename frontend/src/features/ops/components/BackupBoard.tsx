/**
 * 백업·복구 보드 — 턴 AQ · 차선 N2.
 * 읽기: GET /api/dsm/ops/backups — 최근 백업 회수증(시각·판정·크기·목적지·하루 안 회수)과
 * 최근 복원 시험(시각·판정·복원 소요·복원된 표 수·한 달 안 시험)을 그대로 그린다.
 * 누름: 「다시 불러오기」(`o-07-refresh`) = 회수증을 다시 읽는다(같은 GET). 이 화면은
 * 새 저장을 만들지 않는다 — 회수증은 자동 백업이 쓰고 이 보드는 읽는다.
 */
import { Col, Descriptions, Row, Tag, Typography } from 'antd';

import { fetchBackupBoard } from '../api';
import { OPS_BACKUP_COPY as C, OPS_TAB_LABEL } from '../copy';
import BoardFrame from './BoardFrame';
import { useOpsBoard } from './useOpsBoard';

const dash = (v: unknown) => (v === null || v === undefined || v === '' ? '—' : String(v));

function yesNo(v: boolean | null | undefined) {
  if (v === true) return <Tag color="green">{C.yes}</Tag>;
  if (v === false) return <Tag color="red">{C.no}</Tag>;
  return <Tag>{C.unknown}</Tag>;
}

export default function BackupBoard() {
  const board = useOpsBoard(fetchBackupBoard);
  const b = board.data?.backup;
  const d = board.data?.restore_drill;

  return (
    <BoardFrame
      gx="o-07"
      title={OPS_TAB_LABEL.backups}
      loading={board.loading}
      error={board.error}
      forbidden={board.forbidden}
      outcome={null}
      onReload={() => void board.reload()}
    >
      {board.data && (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Descriptions title={C.receipt} column={1} size="small" bordered data-gx="o-07-receipt">
              <Descriptions.Item label={C.measuredAt}>
                <span data-gx="o-07-receipt-at">{dash(b?.measured_at)}</span>
              </Descriptions.Item>
              <Descriptions.Item label={C.verdict}>{dash(b?.verdict)}</Descriptions.Item>
              <Descriptions.Item label={C.bytes}>{dash(b?.db_bytes)}</Descriptions.Item>
              <Descriptions.Item label={C.destination}>
                <span data-gx="o-07-destination">{dash(b?.destination)}</span>
              </Descriptions.Item>
              <Descriptions.Item label={C.fresh24h}>{yesNo(b?.fresh_within_24h)}</Descriptions.Item>
            </Descriptions>
            <Typography.Paragraph type="secondary" style={{ marginTop: 8 }}>
              {C.destinationNote}
            </Typography.Paragraph>
          </Col>
          <Col xs={24} md={12}>
            <Descriptions title={C.drill} column={1} size="small" bordered data-gx="o-07-drill">
              <Descriptions.Item label={C.measuredAt}>
                <span data-gx="o-07-drill-at">{dash(d?.measured_at)}</span>
              </Descriptions.Item>
              <Descriptions.Item label={C.verdict}>{dash(d?.verdict)}</Descriptions.Item>
              <Descriptions.Item label={C.rto}>{dash(d?.rto_seconds)}</Descriptions.Item>
              <Descriptions.Item label={C.tables}>{dash(d?.tables_restored)}</Descriptions.Item>
              <Descriptions.Item label={C.fresh31d}>{yesNo(d?.fresh_within_31d)}</Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
      )}
    </BoardFrame>
  );
}
