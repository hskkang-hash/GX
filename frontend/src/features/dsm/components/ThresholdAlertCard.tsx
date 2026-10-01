/**
 * DSM-U2-04 — **임계값 도달 카드 + 결정 버튼** (턴 AQ · 차선 W2B).
 *
 * 팀장(U2)·U4 홈에 「기준 도달 hh:mm · 통제 여부 결정 필요」(명세 원문 모양 · 시각은
 * 서버가 남긴 도달 감사 시각)를 카드로 띄운다. 「결정 남기기」는
 * `POST /api/dsm/thresholds/observe/{id}/decide` 한 번 → **`GET /api/dsm/thresholds/alerts`
 * 를 다시 불러** 결정됨을 그린다. 도달 시각·결정 시각은 서버에 각각 감사 줄로 남는다.
 */
import { FONT_SM } from '@/configs/fontTokens';
import { Alert, Button, Card, Input, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { dsmPostOnce, newIdempotencyKey } from '../api';
import { w2bDsmEndpoint, w2bFreshGet } from './w2bDecisionApi';

const { Text } = Typography;

interface ThresholdAlertRow {
  observation_id: number;
  key: string;
  camera_id: number;
  reached_at: string | null;
  notice: string;
  detail: string;
  decided: boolean;
  decision: string;
  decided_at: string | null;
}

export default function ThresholdAlertCard() {
  const [rows, setRows] = useState<ThresholdAlertRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [drafts, setDrafts] = useState<Record<number, string>>({});

  const reload = useCallback(async () => {
    try {
      setRows(await w2bFreshGet<ThresholdAlertRow[]>(w2bDsmEndpoint.thresholdAlerts, { limit: 10 }));
    } catch (e) {
      setError(`도달 알림을 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const decide = async (id: number) => {
    const decision = (drafts[id] ?? '').trim();
    if (!decision) {
      setError('통제 여부 결정을 적으십시오.');
      return;
    }
    setBusyId(id);
    try {
      await dsmPostOnce(w2bDsmEndpoint.thresholdDecide(id), { decision }, newIdempotencyKey());
      setError(null);
      setDrafts((d) => ({ ...d, [id]: '' }));
    } catch (e) {
      setError(`결정을 남기지 못했습니다 — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusyId(null);
    }
  };

  const pending = rows.filter((r) => !r.decided);
  return (
    <Card size="small" title="임계값 도달 알림" data-gx="dsm-u2-04-card">
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {rows.length === 0 ? (
          <Text type="secondary">기준에 닿은 관측값이 없습니다. 기준선은 설정에서 바꾸십시오.</Text>
        ) : null}
        {pending.length > 0 ? (
          <Alert
            type="warning"
            showIcon
            data-gx="dsm-u2-04-pending"
            message={`결정을 기다리는 도달 ${pending.length}건`}
          />
        ) : null}
        {rows.map((r) => (
          <Card key={r.observation_id} size="small" type="inner">
            <Space direction="vertical" size={4} style={{ width: '100%' }}>
              <Text strong data-gx="dsm-u2-04-notice">
                {r.notice}
              </Text>
              <Text type="secondary" style={{ fontSize: FONT_SM }}>
                {r.detail}
              </Text>
              {r.decided ? (
                <Tag color="green" data-gx="dsm-u2-04-decided">
                  결정됨 · {r.decision}
                </Tag>
              ) : (
                <Space.Compact style={{ width: '100%' }}>
                  <Input
                    data-gx="dsm-u2-04-decision"
                    value={drafts[r.observation_id] ?? ''}
                    onChange={(ev) =>
                      setDrafts((d) => ({ ...d, [r.observation_id]: ev.target.value }))
                    }
                    placeholder="통제 여부 결정(예: 통제 실시)"
                  />
                  <Button
                    type="primary"
                    data-gx="dsm-u2-04-decide"
                    loading={busyId === r.observation_id}
                    onClick={() => void decide(r.observation_id)}
                  >
                    결정 남기기
                  </Button>
                </Space.Compact>
              )}
            </Space>
          </Card>
        ))}
        {error ? <Alert type="error" showIcon message={error} /> : null}
      </Space>
    </Card>
  );
}
