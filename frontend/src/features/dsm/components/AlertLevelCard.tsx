/**
 * DSM-U4-06 — **위기경보·비상 단계 접수** 홈 카드 (턴 AQ · 차선 W2B).
 *
 * 상급 발령(단계·시각·문서번호)과 비상 근무 편성 인원 수를 한 폼에서 받아
 * `POST /api/dsm/alert-level` 한 번 → **`GET /api/dsm/alert-level` 을 다시 불러** 지금 단계와
 * 최근 접수를 그린다. 띠(`AlertLevelBand`)도 같은 신호로 다시 읽는다.
 */
import { Alert, Button, Card, Input, InputNumber, Select, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { dsmPostOnce, newIdempotencyKey } from '../api';
import {
  ALERT_LEVELS,
  ALERT_LEVEL_COLOR,
  type AlertLevelRow,
  announceAlertLevelChanged,
  w2bDsmEndpoint,
  w2bFreshGet,
} from './w2bDecisionApi';

const { Text } = Typography;

export default function AlertLevelCard() {
  const [rows, setRows] = useState<AlertLevelRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [level, setLevel] = useState<string | undefined>(undefined);
  const [occurredAt, setOccurredAt] = useState('');
  const [docNo, setDocNo] = useState('');
  const [staffing, setStaffing] = useState<number | null>(null);

  const reload = useCallback(async () => {
    try {
      setRows(await w2bFreshGet<AlertLevelRow[]>(w2bDsmEndpoint.alertLevel, { limit: 5 }));
    } catch (e) {
      setError(`접수 이력을 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submit = async () => {
    if (!level) {
      setError('단계를 고르십시오.');
      return;
    }
    setBusy(true);
    try {
      await dsmPostOnce(
        w2bDsmEndpoint.alertLevel,
        {
          level,
          occurred_at: occurredAt || null,
          doc_no: docNo,
          staffing,
        },
        newIdempotencyKey(),
      );
      setError(null);
      setNotice(`${level} 단계 접수를 남겼습니다.`);
      setDocNo('');
      setOccurredAt('');
      setStaffing(null);
      announceAlertLevelChanged();
    } catch (e) {
      setError(`접수하지 못했습니다 — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  };

  const now = rows[0];
  return (
    <Card size="small" title="위기경보·비상 단계" data-gx="dsm-u4-06-card">
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Text data-gx="dsm-u4-06-current">
          지금 단계:{' '}
          {now && now.level ? (
            <Tag color={ALERT_LEVEL_COLOR[now.level] ?? 'default'}>{now.level}</Tag>
          ) : (
            <Text type="secondary">접수 없음</Text>
          )}
          {now?.doc_no ? <Text type="secondary"> {now.doc_no}</Text> : null}
          {now && now.staffing !== null ? (
            <Text type="secondary"> · 비상 근무 {now.staffing}명</Text>
          ) : null}
        </Text>
        <Select
          data-gx="dsm-u4-06-level"
          placeholder="단계"
          value={level}
          onChange={setLevel}
          options={ALERT_LEVELS.map((l) => ({ label: l, value: l }))}
          style={{ width: '100%' }}
        />
        <Input
          data-gx="dsm-u4-06-occurred-at"
          type="datetime-local"
          value={occurredAt}
          onChange={(ev) => setOccurredAt(ev.target.value)}
          placeholder="접수 시각(비우면 지금)"
        />
        <Input
          data-gx="dsm-u4-06-doc-no"
          value={docNo}
          onChange={(ev) => setDocNo(ev.target.value)}
          placeholder="문서번호"
        />
        <InputNumber
          data-gx="dsm-u4-06-staffing"
          min={0}
          value={staffing}
          onChange={(v) => setStaffing(typeof v === 'number' ? v : null)}
          placeholder="비상 근무 편성 인원"
          style={{ width: '100%' }}
        />
        <Button
          type="primary"
          data-gx="dsm-u4-06-submit"
          loading={busy}
          onClick={() => void submit()}
        >
          접수 남기기
        </Button>
        {error ? <Alert type="error" showIcon message={error} /> : null}
        {notice ? <Alert type="success" showIcon message={notice} /> : null}
        {rows.length > 0 ? (
          <Space direction="vertical" size={2} data-gx="dsm-u4-06-list">
            {rows.map((r) => (
              <Text key={r.alert_id} type="secondary" style={{ fontSize: 12 }}>
                {r.text}
              </Text>
            ))}
          </Space>
        ) : null}
      </Space>
    </Card>
  );
}
