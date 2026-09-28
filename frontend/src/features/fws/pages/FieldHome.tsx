/**
 * FWS 진화대 현장(FM3) — `/fws/field` (WO-GX-20260925-15 §5 P-356·357 · 턴 AL 차선 N2).
 *
 * F1(`PatrolHome.tsx`)과 같은 규율 — 얇다. 판정·집계는 전부 서버(`apps/fws`)에
 * 있다. 이 화면은 이 턴에 닫은 F2 절의 진입면을 모아 사람이 누를 수 있는 자리로
 * 잇는다(실측은 `backend/tests/test_fws_f2.py` 가 이미 했다).
 *
 * ★ 지도·좌표 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다. 위치는 값(위도·경도)으로만 다룬다.
 * ★ 문구는 전부 `../copy.ts` 에서 온다 — 화면에 문자열을 직접 짓지 않는다.
 */
import { useEffect, useState } from 'react';

import { Alert, Button, Card, Input, List, Radio, Space, Typography } from 'antd';

import { fwsEndpoint, fwsGet, fwsPostQuery } from '../api';
import { FWS_COPY, FWS_UNKNOWN } from '../copy';

const { Title, Text } = Typography;

interface StandbyStatus {
  status: string | null;
  location: { lat: number; lng: number } | null;
  set_at: string | null;
}

interface TrainingBadge {
  badge: string | null;
  drill_mode: boolean;
  real_channel_sends: number | null;
}

interface MissionDetail {
  mission_id: number;
  response_state: string;
  severity: string | null;
  address: string | null;
}

interface MissionRow {
  mission_id: number;
  dispatched_at: string | null;
  arrived_at: string | null;
  released_at: string | null;
  duration_minutes: number | null;
}

export default function FieldHome(): JSX.Element {
  const [standby, setStandby] = useState<StandbyStatus | null>(null);
  const [badge, setBadge] = useState<TrainingBadge | null>(null);
  const [missions, setMissions] = useState<MissionRow[]>([]);
  const [missionId, setMissionId] = useState('');
  const [mission, setMission] = useState<MissionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function reload(): Promise<void> {
    try {
      const [standbyRes, badgeRes, mineRes] = await Promise.all([
        fwsGet<StandbyStatus>(fwsEndpoint.standbyStatus),
        fwsGet<TrainingBadge>(fwsEndpoint.trainingMission),
        fwsGet<{ missions: MissionRow[] }>(fwsEndpoint.missionsMine),
      ]);
      setStandby(standbyRes);
      setBadge(badgeRes);
      setMissions(mineRes.missions);
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function handleStandby(status: string): Promise<void> {
    try {
      await fwsPostQuery(fwsEndpoint.standbyStatus, { status });
      await reload();
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  async function handleLoadMission(): Promise<void> {
    if (!missionId) return;
    try {
      const detail = await fwsGet<MissionDetail>(fwsEndpoint.mission(missionId));
      setMission(detail);
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  async function handleMissionAction(action: 'dispatch' | 'arrived' | 'released'): Promise<void> {
    if (!mission) return;
    try {
      await fwsPostQuery(fwsEndpoint.missionResponse(mission.mission_id), { action });
      setNotice(`${action} ${FWS_COPY.field.missionActionDoneSuffix}`);
      await handleLoadMission();
      await reload();
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  async function handleSupportRequest(kind: string): Promise<void> {
    if (!mission) return;
    try {
      await fwsPostQuery(fwsEndpoint.missionFieldReply(mission.mission_id), { kind });
      setNotice(`${FWS_COPY.field.supportButton}(${kind}) ${FWS_COPY.field.supportSentSuffix}`);
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_COPY.field.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      <Card title={FWS_COPY.field.standbyTitle}>
        <Space direction="vertical">
          <Text>
            {FWS_COPY.field.standbyNowPrefix}: <strong>{standby?.status ?? FWS_UNKNOWN}</strong>
          </Text>
          <Space>
            <Button onClick={() => handleStandby('standby_day')}>{FWS_COPY.field.standbyDay}</Button>
            <Button onClick={() => handleStandby('standby_night')}>{FWS_COPY.field.standbyNight}</Button>
            <Button onClick={() => handleStandby('off_duty')}>{FWS_COPY.field.standbyOff}</Button>
          </Space>
        </Space>
      </Card>

      {badge?.badge && (
        <Alert
          type="warning"
          showIcon
          message={`${FWS_COPY.field.trainingBadge} — ${FWS_COPY.field.trainingRealChannelPrefix} ${
            badge.real_channel_sends ?? FWS_UNKNOWN
          }`}
        />
      )}

      <Card title={FWS_COPY.field.missionTitle}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Input
              placeholder={FWS_COPY.field.missionIdPlaceholder}
              value={missionId}
              onChange={(e) => setMissionId(e.target.value)}
              style={{ width: 160 }}
            />
            <Button onClick={handleLoadMission}>{FWS_COPY.field.missionLookupButton}</Button>
          </Space>
          {mission && (
            <>
              <Text>
                #{mission.mission_id} · {mission.address ?? FWS_UNKNOWN} ·{' '}
                {FWS_COPY.field.responseStatePrefix} {mission.response_state}
              </Text>
              <Space wrap>
                <Button onClick={() => handleMissionAction('dispatch')}>
                  {FWS_COPY.field.dispatchButton}
                </Button>
                <Button onClick={() => handleMissionAction('arrived')}>
                  {FWS_COPY.field.arriveButton}
                </Button>
                <Button onClick={() => handleMissionAction('released')}>
                  {FWS_COPY.field.releaseButton}
                </Button>
              </Space>
              <Space wrap>
                {Object.entries(FWS_COPY.supportKind).map(([kind, label]) => (
                  <Button key={kind} size="small" onClick={() => handleSupportRequest(kind)}>
                    {FWS_COPY.field.supportButton}: {label}
                  </Button>
                ))}
              </Space>
            </>
          )}
        </Space>
      </Card>

      <Card title={FWS_COPY.field.myMissionsTitle}>
        <List
          dataSource={missions}
          locale={{ emptyText: FWS_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              #{row.mission_id} · {FWS_COPY.field.myMissionsDeployedPrefix}{' '}
              {row.duration_minutes ?? FWS_UNKNOWN}
              {FWS_COPY.field.myMissionsMinutesSuffix}
            </List.Item>
          )}
        />
      </Card>

      <EquipmentCheckCard
        onDone={() => setNotice(FWS_COPY.field.equipmentSavedNotice)}
        onError={() => setError(FWS_COPY.error.generic)}
      />
    </Space>
  );
}

function EquipmentCheckCard({
  onDone,
  onError,
}: {
  onDone: () => void;
  onError: () => void;
}): JSX.Element {
  const [equipmentType, setEquipmentType] = useState('backpack_pump');
  const [equipmentCode, setEquipmentCode] = useState('');
  const [result, setResult] = useState<'pass' | 'fail'>('pass');

  async function handleSubmit(): Promise<void> {
    try {
      await fwsPostQuery(fwsEndpoint.equipmentChecks, {
        equipment_type: equipmentType,
        equipment_code: equipmentCode,
        result,
      });
      onDone();
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_COPY.field.equipmentTitle}>
      <Space direction="vertical">
        <Input
          placeholder={FWS_COPY.field.equipmentCodePlaceholder}
          value={equipmentCode}
          onChange={(e) => setEquipmentCode(e.target.value)}
          style={{ width: 200 }}
        />
        <Radio.Group value={equipmentType} onChange={(e) => setEquipmentType(e.target.value)}>
          <Radio.Button value="backpack_pump">{FWS_COPY.field.equipmentBackpackPump}</Radio.Button>
          <Radio.Button value="fire_truck">{FWS_COPY.field.equipmentFireTruck}</Radio.Button>
        </Radio.Group>
        <Radio.Group value={result} onChange={(e) => setResult(e.target.value)}>
          <Radio.Button value="pass">{FWS_COPY.field.equipmentPass}</Radio.Button>
          <Radio.Button value="fail">{FWS_COPY.field.equipmentFail}</Radio.Button>
        </Radio.Group>
        <Button type="primary" onClick={handleSubmit}>
          {FWS_COPY.field.equipmentSaveButton}
        </Button>
      </Space>
    </Card>
  );
}
