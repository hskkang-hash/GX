/**
 * FWS 드론 운용자(F5) 현장 — `/fws/drone` (WO-GX-20260925-15 §5 P-356·357·387 · 턴 AM
 * 차선 N2).
 *
 * 세종 판정 P-387 — 요청·상태·결과 세 축뿐, 드론은 0대다. 이 화면은 그 세 축의
 * 진입면(`apps/fws/drone.py`)을 사람이 누를 수 있는 자리로 잇는다. 실측은
 * `backend/tests/test_fws_f5.py` 가 이미 했다.
 *
 * ★ 지도·폴리라인 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다. 열점·화선은 좌표 목록 **값**(JSON)으로만 다룬다.
 * ★ 문구는 전부 `../copy.ts` 에서 온다 — 화면에 문자열을 직접 짓지 않는다.
 */
import { useState } from 'react';

import { Alert, Button, Card, Input, InputNumber, List, Radio, Space, Typography } from 'antd';

import { fwsEndpoint, fwsGet, fwsPostQuery } from '../api';
import { FWS_COPY, FWS_UNKNOWN } from '../copy';

const { Title, Text } = Typography;

interface ReconRow {
  event_id: number;
  state: string | null;
  radius_m: number | null;
  requested_at: string | null;
  accepted_at: string | null;
  airborne_at: string | null;
  returned_at: string | null;
}

export default function DroneHome(): JSX.Element {
  const [eventId, setEventId] = useState('');
  const [radiusM, setRadiusM] = useState<number | null>(null);
  const [recon, setRecon] = useState<ReconRow | null>(null);
  const [myRequests, setMyRequests] = useState<ReconRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function reloadMine(): Promise<void> {
    try {
      const mine = await fwsGet<{ requests: ReconRow[] }>(fwsEndpoint.droneReconMine);
      setMyRequests(mine.requests);
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  async function handleReconAction(action: 'request' | 'accept' | 'airborne' | 'return') {
    if (!eventId) return;
    try {
      const params: Record<string, string | number> = { action };
      if (action === 'request' && radiusM != null) params.radius_m = radiusM;
      await fwsPostQuery(fwsEndpoint.droneRecon(eventId), params);
      setNotice(`${FWS_COPY.drone.stateLabel[action]} ${FWS_COPY.drone.stateActionDoneSuffix}`);
      await reloadMine();
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_COPY.drone.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      <Card title={FWS_COPY.field.missionTitle}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Input
              placeholder={FWS_COPY.drone.missionIdPlaceholder}
              value={eventId}
              onChange={(e) => setEventId(e.target.value)}
              style={{ width: 160 }}
            />
            <InputNumber
              placeholder={FWS_COPY.drone.radiusPlaceholder}
              value={radiusM}
              onChange={(v) => setRadiusM(v)}
              style={{ width: 140 }}
            />
          </Space>
          <Space wrap>
            <Button type="primary" onClick={() => handleReconAction('request')}>
              {FWS_COPY.drone.requestButton}
            </Button>
            <Button onClick={() => handleReconAction('accept')}>{FWS_COPY.drone.acceptButton}</Button>
            <Button onClick={() => handleReconAction('airborne')}>{FWS_COPY.drone.airborneButton}</Button>
            <Button onClick={() => handleReconAction('return')}>{FWS_COPY.drone.returnButton}</Button>
          </Space>
        </Space>
      </Card>

      <Card title={FWS_COPY.drone.myRequestsTitle}>
        <List
          dataSource={myRequests}
          locale={{ emptyText: FWS_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              #{row.event_id} · {FWS_COPY.field.responseStatePrefix}{' '}
              {row.state && row.state in FWS_COPY.drone.stateLabel
                ? FWS_COPY.drone.stateLabel[row.state as keyof typeof FWS_COPY.drone.stateLabel]
                : FWS_UNKNOWN}{' '}
              ·{' '}
              {row.radius_m ?? FWS_UNKNOWN}m
            </List.Item>
          )}
        />
      </Card>

      <HotspotsCard
        eventId={eventId}
        onDone={(n) => setNotice(`${n}${FWS_COPY.drone.hotspotsSentSuffix}`)}
        onError={() => setError(FWS_COPY.error.generic)}
      />

      <VerifyResultCard
        eventId={eventId}
        onDone={() => setNotice(FWS_COPY.drone.verifyTitle)}
        onError={() => setError(FWS_COPY.error.generic)}
      />

      <FlightLogCard
        onDone={() => setNotice(FWS_COPY.drone.flightLogTitle)}
        onError={() => setError(FWS_COPY.error.generic)}
      />
    </Space>
  );
}

function HotspotsCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (count: number) => void;
  onError: () => void;
}): JSX.Element {
  const [pointsJson, setPointsJson] = useState('');
  const [firelineJson, setFirelineJson] = useState('');

  async function handleSubmit(): Promise<void> {
    if (!eventId) return;
    try {
      const body = await fwsPostQuery<{ points: unknown[]; fireline: unknown[] }>(
        fwsEndpoint.droneHotspots(eventId),
        { points_json: pointsJson || undefined, fireline_json: firelineJson || undefined },
      );
      onDone(body.points.length + body.fireline.length);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_COPY.drone.hotspotsTitle}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Input.TextArea
          placeholder='points_json — [{"lat":36.1,"lng":127.2}]'
          value={pointsJson}
          onChange={(e) => setPointsJson(e.target.value)}
          rows={2}
        />
        <Input.TextArea
          placeholder='fireline_json — [{"lat":36.1,"lng":127.2}, ...]'
          value={firelineJson}
          onChange={(e) => setFirelineJson(e.target.value)}
          rows={2}
        />
        <Button type="primary" onClick={handleSubmit}>
          {FWS_COPY.drone.requestButton}
        </Button>
      </Space>
    </Card>
  );
}

function VerifyResultCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: () => void;
  onError: () => void;
}): JSX.Element {
  const [attachmentRef, setAttachmentRef] = useState('');

  async function handleReply(result: 'fire_confirmed' | 'false_alarm'): Promise<void> {
    if (!eventId) return;
    try {
      await fwsPostQuery(fwsEndpoint.droneVerificationReply(eventId), {
        result,
        attachment_ref: attachmentRef || undefined,
      });
      onDone();
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_COPY.drone.verifyTitle}>
      <Space direction="vertical">
        <Input
          placeholder={FWS_COPY.drone.attachmentRefPlaceholder}
          value={attachmentRef}
          onChange={(e) => setAttachmentRef(e.target.value)}
          style={{ width: 280 }}
        />
        <Space>
          <Button onClick={() => handleReply('fire_confirmed')}>{FWS_COPY.drone.fireConfirmed}</Button>
          <Button onClick={() => handleReply('false_alarm')}>{FWS_COPY.drone.falseAlarm}</Button>
        </Space>
      </Space>
    </Card>
  );
}

function FlightLogCard({ onDone, onError }: { onDone: () => void; onError: () => void }): JSX.Element {
  const [source, setSource] = useState('manual');
  const [airframeCode, setAirframeCode] = useState('');
  const [batteryPct, setBatteryPct] = useState<number | null>(null);
  const [flightMinutes, setFlightMinutes] = useState<number | null>(null);
  const [total, setTotal] = useState<number | null>(null);

  async function handleSave(): Promise<void> {
    try {
      await fwsPostQuery(fwsEndpoint.droneFlights, {
        source,
        airframe_code: airframeCode || undefined,
        battery_pct: batteryPct ?? undefined,
        flight_minutes: flightMinutes ?? undefined,
      });
      const minutes = await fwsGet<{ flight_minutes_total: number }>(fwsEndpoint.droneFlightMinutes);
      setTotal(minutes.flight_minutes_total);
      onDone();
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_COPY.drone.flightLogTitle}>
      <Space direction="vertical">
        <Radio.Group value={source} onChange={(e) => setSource(e.target.value)}>
          <Radio.Button value="manual">manual</Radio.Button>
          <Radio.Button value="dji">dji</Radio.Button>
        </Radio.Group>
        <Input
          placeholder={FWS_COPY.drone.flightAirframePlaceholder}
          value={airframeCode}
          onChange={(e) => setAirframeCode(e.target.value)}
          style={{ width: 200 }}
        />
        <Space>
          <InputNumber
            placeholder={FWS_COPY.drone.flightBatteryPlaceholder}
            value={batteryPct}
            onChange={setBatteryPct}
          />
          <InputNumber
            placeholder={FWS_COPY.drone.flightMinutesPlaceholder}
            value={flightMinutes}
            onChange={setFlightMinutes}
          />
        </Space>
        <Button type="primary" onClick={handleSave}>
          {FWS_COPY.drone.flightSaveButton}
        </Button>
        {total != null && (
          <Text>
            {FWS_COPY.drone.flightMinutesTotalPrefix}: {total}
          </Text>
        )}
      </Space>
    </Card>
  );
}
