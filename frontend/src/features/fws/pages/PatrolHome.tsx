/**
 * FWS 현장 홈(FM1·FM2) — `/fws/home` (WO-GX-20260925-15 §5 P-356·357 · 턴 AK 차선 N2).
 *
 * 한 화면에 이 턴에 닫은 절의 진입면을 모은다 — 각 절의 실측은
 * `backend/tests/test_fws_app.py` 가 이미 했고(엔드포인트가 정본), 이 화면은
 * 그 문들을 사람이 누를 수 있는 자리로 잇는다.
 *
 * ★ 얇다 — 판정·집계는 전부 서버(`apps/fws`)에 있다. 이 화면은 응답을 그대로
 *   그릴 뿐이고, 새 계산을 하지 않는다(DA-04 §1-1 과 같은 규율).
 * ★ 문구는 전부 `./copy.ts` 에서 온다 — 화면에 문자열을 직접 짓지 않는다(P-357).
 * ★ 지도·좌표 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다(F1-04는 이번 차선 범위 밖).
 */
import { useEffect, useState } from 'react';

import { Alert, Button, Card, List, Space, Typography } from 'antd';

import { fwsEndpoint, fwsGet, fwsPostQuery } from '../api';
import { FWS_COPY, FWS_UNKNOWN } from '../copy';
import NotifyPrefsCard from './NotifyPrefsCard';
import PatrolW2aCards from './PatrolW2aCards';
import { checkinOrQueue, installAutoFlush, pendingCount } from '../offlineQueue';

interface RiskToday {
  level: string;
  fire_alert: boolean;
  mountain_entry_banned: boolean;
  season: string;
  as_of: string;
}

interface EmergencyContacts {
  fire_report: string;
  forest_report: string;
}

interface AlertRow {
  delivery_id: number;
  event_id: number;
  channel: string;
  occurred_at: string | null;
  sent_at: string | null;
  acknowledged: boolean;
}

const { Title, Text } = Typography;

export default function PatrolHome(): JSX.Element {
  const [risk, setRisk] = useState<RiskToday | null>(null);
  const [contacts, setContacts] = useState<EmergencyContacts | null>(null);
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [checkedIn, setCheckedIn] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  // [턴 AQ · 차선 W2A] 체크인 뒤 F1-11 실적 표를 다시 불러오게 하는 신호
  const [mineKey, setMineKey] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const remove = installAutoFlush();
    return remove;
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [riskRes, contactsRes, alertsRes] = await Promise.all([
          fwsGet<RiskToday>(fwsEndpoint.riskToday),
          fwsGet<EmergencyContacts>(fwsEndpoint.emergencyContacts),
          fwsGet<{ alerts: AlertRow[] }>(fwsEndpoint.alerts),
        ]);
        if (!alive) return;
        setRisk(riskRes);
        setContacts(contactsRes);
        setAlerts(alertsRes.alerts);
      } catch {
        if (alive) setError(FWS_COPY.error.generic);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  async function handleCheckin(): Promise<void> {
    try {
      const result = await checkinOrQueue({ post_code: 'P-1', method: 'gps' });
      if (result.queued) {
        setQueuedCount(pendingCount());
      } else {
        setCheckedIn(true);
        setMineKey((k) => k + 1);
      }
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  async function handleAck(deliveryId: number): Promise<void> {
    try {
      await fwsPostQuery(fwsEndpoint.alertAck(deliveryId), {});
      setAlerts((rows) =>
        rows.map((r) => (r.delivery_id === deliveryId ? { ...r, acknowledged: true } : r)),
      );
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  const riskLabel = risk
    ? (FWS_COPY.risk as Record<string, string>)[risk.level] ?? FWS_UNKNOWN
    : FWS_UNKNOWN;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_COPY.home.title}</Title>
      {error && <Alert type="error" message={error} showIcon />}

      <Card>
        <Space direction="vertical">
          <Text>
            {FWS_COPY.home.riskLevelPrefix}: <strong>{riskLabel}</strong>
          </Text>
          {risk?.mountain_entry_banned && (
            <Alert type="warning" showIcon message={FWS_COPY.home.mountainBannedLabel} />
          )}
        </Space>
      </Card>

      <Card>
        <Space>
          <Button type="primary" disabled={checkedIn} onClick={handleCheckin}>
            {checkedIn ? FWS_COPY.home.checkinDone : FWS_COPY.home.checkinButton}
          </Button>
          {queuedCount > 0 && <Text type="secondary">대기 {queuedCount}건(복귀 시 전송)</Text>}
        </Space>
      </Card>

      <Card>
        <Space>
          {contacts && (
            <>
              <a href={`tel:${contacts.fire_report}`}>
                <Button danger>{FWS_COPY.home.reportFireButton}</Button>
              </a>
              <a href={`tel:${contacts.forest_report}`}>
                <Button>{FWS_COPY.home.reportForestButton}</Button>
              </a>
            </>
          )}
        </Space>
      </Card>

      <Card title={FWS_COPY.alerts.title}>
        <List
          dataSource={alerts}
          locale={{ emptyText: FWS_UNKNOWN }}
          renderItem={(row) => (
            <List.Item
              actions={[
                row.acknowledged ? (
                  <Text type="secondary">{FWS_COPY.alerts.acked}</Text>
                ) : (
                  <Button size="small" onClick={() => handleAck(row.delivery_id)}>
                    {FWS_COPY.alerts.ackButton}
                  </Button>
                ),
              ]}
            >
              #{row.event_id} · {row.channel}
            </List.Item>
          )}
        />
      </Card>

      {/* [턴 AQ · 차선 W2A] F1-11 실적 표 · F1-02 순찰 경로 기록 · F1-06 현장 확인 회신 */}
      <PatrolW2aCards refreshKey={mineKey} />

      {/* [턴 AQ · 차선 N3] F1-12 M4 근무 외 알림 차단 칸 */}
      <NotifyPrefsCard gxPrefix="fws-f1-12-quiet" />
    </Space>
  );
}
