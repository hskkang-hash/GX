/**
 * FWS-F2-07 — 진화대 현장(FM3) 안전 경보 칸 (턴 AQ · 차선 N3).
 *
 * ★ 경보 기준(풍향 급변 각도·시간창 · 투하 구역 이탈 반경)은 **기관 설정값**이다
 *   (P-434 · `GET /api/fws/admin/safety-thresholds` — 기관 사용자면 누구나 읽는다).
 *   미설정 칸은 「대기」 배지 — 그동안 규칙은 발화하지 않는다. 화면은 숫자를 짓지
 *   않는다: 서버가 준 값과 단위만 그대로 보인다.
 * ★ 받은 경보는 `GET /api/fws/alerts`(나에게 실제로 간 발송) · 확인은
 *   `POST /api/fws/alerts/{id}/ack` → **같은 GET 을 다시 불러** 확인 상태를 그린다.
 *   확인 전 경보가 있으면 칸 머리가 빨강이다(명세 FM3 「경보 시 이 칸이 빨강」).
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, Button, Card, List, Space, Tag, Typography } from 'antd';

import { fwsAqEndpoint, fwsEndpoint, fwsGetFresh, fwsPostQuery } from '../api';
import { FWS_AQ_N3_COPY } from '../copy_aq_n3';

const { Text } = Typography;
const C = FWS_AQ_N3_COPY.safetyAlerts;

interface ThresholdField {
  name: string;
  value: number | null;
  unit: string;
  status: string;
}
interface ThresholdView {
  fields: ThresholdField[];
  all_set: boolean;
}
interface AlertRow {
  delivery_id: number;
  event_id: number | null;
  channel: string;
  occurred_at: string | null;
  sent_at: string | null;
  acknowledged: boolean;
}

export default function SafetyAlertsCard(): JSX.Element {
  const [rules, setRules] = useState<ThresholdView | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async (): Promise<void> => {
    const [r, a] = await Promise.all([
      fwsGetFresh<ThresholdView>(fwsAqEndpoint.safetyThresholds).catch(() => null),
      fwsGetFresh<{ alerts: AlertRow[] }>(fwsEndpoint.alerts).catch(() => null),
    ]);
    setRules(r);
    if (a) setAlerts(a.alerts);
    else setError(C.loadFailed);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function ack(deliveryId: number): Promise<void> {
    setBusy(true);
    try {
      await fwsPostQuery(fwsEndpoint.alertAck(deliveryId), {});
      setError(null);
    } catch (e) {
      setError(`${C.ackFailed} — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  }

  const unacked = alerts.filter((a) => !a.acknowledged).length;

  return (
    <Card
      title={
        <Space>
          <span>{C.title}</span>
          {unacked > 0 && (
            <Tag color="red" data-gx="fws-f2-07-unacked">
              {C.unacked} {unacked}
            </Tag>
          )}
        </Space>
      }
      style={unacked > 0 ? { borderColor: '#cf1322' } : undefined}
      data-gx="fws-f2-07-card"
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {error && <Alert type="error" showIcon closable message={error} onClose={() => setError(null)} />}
        <div data-gx="fws-f2-07-rules">
          <Text type="secondary">{C.ruleLabel}: </Text>
          {(rules?.fields ?? []).map((f) => (
            <Tag key={f.name} color={f.value === null ? 'default' : 'blue'}
              data-gx={f.value === null ? 'fws-f2-07-waiting' : 'fws-f2-07-rule-set'}>
              {FWS_AQ_N3_COPY.thresholdNames[f.name] ?? f.name}{' '}
              {f.value === null ? C.waiting : `${f.value}${f.unit}`}
            </Tag>
          ))}
          {rules && !rules.all_set && (
            <div>
              <Text type="secondary">{C.waitingNote}</Text>
            </div>
          )}
        </div>
        <List
          size="small"
          data-gx="fws-f2-07-list"
          dataSource={alerts}
          locale={{ emptyText: C.empty }}
          renderItem={(a) => (
            <List.Item>
              <Space wrap>
                <Tag color={a.acknowledged ? 'green' : 'red'}>{a.acknowledged ? C.acked : C.unacked}</Tag>
                <Text>
                  {C.eventLabel} #{a.event_id ?? '-'} · {a.sent_at ?? a.occurred_at ?? ''}
                </Text>
                {!a.acknowledged && (
                  <Button size="small" type="primary" disabled={busy} data-gx="fws-f2-07-ack"
                    onClick={() => void ack(a.delivery_id)}>
                    {C.ackButton}
                  </Button>
                )}
              </Space>
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}
