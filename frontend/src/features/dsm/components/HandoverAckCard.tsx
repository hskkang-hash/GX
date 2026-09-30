/**
 * DSM-U2-05 — **교대 인수인계 합동 확인** 홈 카드 「인계 확인 ✓」 (턴 AQ · 차선 W2B).
 *
 * `GET /api/dsm/handover/latest` 의 `acknowledged` 칸을 읽어 ✓ 를 그린다. 「인계 확인」은
 * `POST /api/dsm/handover/{id}/ack` 한 번 → **같은 GET 을 다시 불러** ✓ 로 바뀐 것을 그린다.
 * 인계 창(08~09시 · 명세 원문)은 서버가 내 준 `handover_window` 를 그대로 보인다 —
 * 화면이 시각을 따로 정하지 않는다. 창 밖 확인도 받되 그렇게 남는다(서버 감사 줄).
 */
import { Alert, Button, Card, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { dsmPostOnce, newIdempotencyKey } from '../api';
import { w2bDsmEndpoint, w2bFreshGet } from './w2bDecisionApi';

const { Text } = Typography;

interface HandoverLatest {
  exists: boolean;
  id?: number;
  body?: string;
  note?: string;
  created_at?: string;
  acknowledged?: boolean;
  acknowledgement?: { ack_id: number; reason: string; at: string | null } | null;
  handover_window?: { start: string; end: string; open: boolean };
}

export default function HandoverAckCard() {
  const [data, setData] = useState<HandoverLatest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    try {
      setData(await w2bFreshGet<HandoverLatest>(w2bDsmEndpoint.handoverLatest));
    } catch (e) {
      setError(`인계 메모를 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const ack = async () => {
    if (!data?.id) return;
    setBusy(true);
    try {
      await dsmPostOnce(w2bDsmEndpoint.handoverAck(data.id), {}, newIdempotencyKey());
      setError(null);
    } catch (e) {
      setError(`확인을 남기지 못했습니다 — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  };

  const win = data?.handover_window;
  return (
    <Card size="small" title="교대 인계 확인" data-gx="dsm-u2-05-card">
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        {win ? (
          <Text type="secondary" data-gx="dsm-u2-05-window">
            인계 창 {win.start}~{win.end} · {win.open ? '지금 인계 시간입니다' : '지금은 인계 시간 밖입니다'}
          </Text>
        ) : null}
        {data && !data.exists ? (
          <Text type="secondary">저장된 인계 메모가 없습니다. 인계 화면에서 먼저 저장하십시오.</Text>
        ) : null}
        {data?.exists ? (
          <>
            <Text style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{data.body}</Text>
            {data.note ? <Text type="secondary">특이사항: {data.note}</Text> : null}
            {data.acknowledged ? (
              <Space direction="vertical" size={2}>
                <Tag color="green" data-gx="dsm-u2-05-acked">
                  인계 확인 ✓
                </Tag>
                {data.acknowledgement?.reason ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {data.acknowledgement.reason}
                  </Text>
                ) : null}
              </Space>
            ) : (
              <Button
                type="primary"
                data-gx="dsm-u2-05-ack"
                loading={busy}
                onClick={() => void ack()}
              >
                인계 확인
              </Button>
            )}
          </>
        ) : null}
        {error ? <Alert type="error" showIcon message={error} /> : null}
      </Space>
    </Card>
  );
}
