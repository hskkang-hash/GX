/**
 * FWS F3 산림과 상황 — `/fws/office` (WO-GX-20260929-17 §5 P-356·357·397 · 턴 AN
 * 차선 N2).
 *
 * 턴 AN · WO-17 · 차선 N2 단독 소유(조율자가 빈 화면으로 세워 `App.tsx` 에 등록해 둠).
 * ★ 문구는 이 차선의 `../copy_office.ts` 에서 온다 — 공용 `../copy.ts` 는 이 턴에
 *   고치지 않는다. 서버 호출은 공용 `../api.ts` 의 `fwsGet`·`fwsPostQuery`(그 파일도
 *   고치지 않는다 — 이 화면 전용 경로 상수만 이 파일 안에 둔다).
 * ★ 지도·위치 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다. 좌표는 값(숫자)으로만 다룬다.
 * ★ F3-05(오인 종결·산불 확정)는 새 문이 없다 — 기존 F1-06 문
 *   (`fwsEndpoint.verificationReply`)을 그대로 재사용한다(`apps/fws/office.py`
 *   머리말과 같은 판단).
 */
import { useState } from 'react';

import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Input,
  InputNumber,
  Radio,
  Row,
  Space,
  Typography,
} from 'antd';

import { fwsEndpoint, fwsGet, fwsPostQuery } from '../api';
import { FWS_OFFICE_COPY } from '../copy_office';

const { Title, Text } = Typography;

const OFFICE = {
  dashboard: '/api/fws/office/dashboard',
  season: '/api/fws/office/season',
  posts: '/api/fws/office/posts',
  roster: '/api/fws/office/roster',
  verificationRequest: (eventId: string) =>
    `/api/fws/office/fire-events/${eventId}/verification-request`,
  intake: (eventId: string) => `/api/fws/office/fire-events/${eventId}/intake`,
  agencyNotify: (eventId: string) => `/api/fws/office/fire-events/${eventId}/agency-notify`,
  resourceAssignment: (eventId: string) =>
    `/api/fws/office/fire-events/${eventId}/resource-assignment`,
  stageProposal: (eventId: string) => `/api/fws/office/fire-events/${eventId}/stage-proposal`,
};

interface DashboardBody {
  risk_index: { level: string; season: string };
  fire_alert: { active: boolean; mountain_entry_banned: boolean };
  post_duty: { on_duty: number; total_officers: number };
  camera_status: { alive: number; total: number; never_seen: number };
  ongoing_incidents: { count: number; items: unknown[] };
  resource_standby: Record<string, number>;
}

export default function OfficeHome(): JSX.Element {
  const [dashboard, setDashboard] = useState<DashboardBody | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [eventId, setEventId] = useState('');

  async function loadDashboard(): Promise<void> {
    try {
      const body = await fwsGet<DashboardBody>(OFFICE.dashboard);
      setDashboard(body);
    } catch {
      setError(FWS_OFFICE_COPY.dashboard.title + ' 조회 실패');
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_OFFICE_COPY.home.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      <DashboardCard dashboard={dashboard} onLoad={loadDashboard} />

      <Row gutter={16}>
        <Col span={12}>
          <SeasonCard onDone={(m) => setNotice(m)} onError={() => setError('저장 실패')} />
        </Col>
        <Col span={12}>
          <PostsCard onDone={(m) => setNotice(m)} onError={() => setError('저장 실패')} />
        </Col>
      </Row>

      <RosterCard onDone={(m) => setNotice(m)} onError={() => setError('저장 실패')} />

      <Card title={FWS_OFFICE_COPY.incident.title}>
        <Input
          placeholder={FWS_OFFICE_COPY.incident.eventIdPlaceholder}
          value={eventId}
          onChange={(e) => setEventId(e.target.value)}
          style={{ width: 200, marginBottom: 16 }}
        />
      </Card>

      <VerificationRequestCard
        eventId={eventId}
        onDone={(m) => setNotice(m)}
        onError={() => setError('요청 실패')}
      />
      <MisjudgeOrConfirmCard
        eventId={eventId}
        onDone={(m) => setNotice(m)}
        onError={() => setError('처리 실패')}
      />
      <IntakeCard eventId={eventId} onDone={(m) => setNotice(m)} onError={() => setError('저장 실패')} />
      <AgencyNotifyCard
        eventId={eventId}
        onDone={(m) => setNotice(m)}
        onError={() => setError('저장 실패')}
      />
      <ResourceAssignmentCard
        eventId={eventId}
        onDone={(m) => setNotice(m)}
        onError={() => setError('배정 실패')}
      />
      <StageProposalCard
        eventId={eventId}
        onDone={(m) => setNotice(m)}
        onError={() => setError('제안 실패')}
      />
    </Space>
  );
}

function DashboardCard({
  dashboard,
  onLoad,
}: {
  dashboard: DashboardBody | null;
  onLoad: () => void;
}): JSX.Element {
  return (
    <Card
      title={FWS_OFFICE_COPY.dashboard.title}
      extra={<Button onClick={onLoad}>{FWS_OFFICE_COPY.dashboard.refreshButton}</Button>}
    >
      {dashboard ? (
        <Row gutter={16}>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.riskIndex}</Text>
            <div>{dashboard.risk_index.level}</div>
          </Col>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.fireAlert}</Text>
            <div>{dashboard.fire_alert.active ? 'O' : 'X'}</div>
          </Col>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.postDuty}</Text>
            <div>
              {dashboard.post_duty.on_duty}/{dashboard.post_duty.total_officers}
            </div>
          </Col>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.cameraStatus}</Text>
            <div>
              {dashboard.camera_status.alive}/{dashboard.camera_status.total}
            </div>
          </Col>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.ongoingIncidents}</Text>
            <div>{dashboard.ongoing_incidents.count}</div>
          </Col>
          <Col span={4}>
            <Text strong>{FWS_OFFICE_COPY.dashboard.resourceStandby}</Text>
            <div>{Object.values(dashboard.resource_standby).reduce((a, b) => a + b, 0)}</div>
          </Col>
        </Row>
      ) : (
        <Text type="secondary">{FWS_OFFICE_COPY.dashboard.refreshButton}</Text>
      )}
    </Card>
  );
}

function SeasonCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [kind, setKind] = useState('dry_season');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  async function handleSave(): Promise<void> {
    if (!startDate || !endDate) return;
    try {
      await fwsPostQuery(OFFICE.season, { kind, start_date: startDate, end_date: endDate });
      onDone(FWS_OFFICE_COPY.season.savedNotice);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.season.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)}>
          <Radio.Button value="dry_season">{FWS_OFFICE_COPY.season.kindDry}</Radio.Button>
          <Radio.Button value="special_measures">{FWS_OFFICE_COPY.season.kindSpecial}</Radio.Button>
        </Radio.Group>
        <Space>
          <Input
            placeholder={FWS_OFFICE_COPY.season.startPlaceholder}
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            style={{ width: 160 }}
          />
          <Input
            placeholder={FWS_OFFICE_COPY.season.endPlaceholder}
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            style={{ width: 160 }}
          />
        </Space>
        <Button type="primary" onClick={handleSave}>
          {FWS_OFFICE_COPY.season.saveButton}
        </Button>
      </Space>
    </Card>
  );
}

function PostsCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [kind, setKind] = useState('watchpost');
  const [code, setCode] = useState('');
  const [name, setName] = useState('');

  async function handleRegister(): Promise<void> {
    if (!code) return;
    try {
      await fwsPostQuery(OFFICE.posts, { kind, code, name: name || undefined });
      onDone(FWS_OFFICE_COPY.posts.registeredNotice);
      setCode('');
      setName('');
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.posts.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)}>
          <Radio.Button value="watchpost">{FWS_OFFICE_COPY.posts.kindWatchpost}</Radio.Button>
          <Radio.Button value="patrol_zone">{FWS_OFFICE_COPY.posts.kindPatrolZone}</Radio.Button>
        </Radio.Group>
        <Space>
          <Input
            placeholder={FWS_OFFICE_COPY.posts.codePlaceholder}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ width: 120 }}
          />
          <Input
            placeholder={FWS_OFFICE_COPY.posts.namePlaceholder}
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 160 }}
          />
        </Space>
        <Button type="primary" onClick={handleRegister}>
          {FWS_OFFICE_COPY.posts.registerButton}
        </Button>
      </Space>
    </Card>
  );
}

function RosterCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [csvText, setCsvText] = useState('');

  async function handleUpload(): Promise<void> {
    if (!csvText.trim()) return;
    try {
      const body = await fwsPostQuery<{ count: number }>(OFFICE.roster, { csv_text: csvText });
      onDone(`${body.count}${FWS_OFFICE_COPY.roster.uploadedSuffix}`);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.roster.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Input.TextArea
          placeholder={FWS_OFFICE_COPY.roster.csvPlaceholder}
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          rows={4}
        />
        <Button type="primary" onClick={handleUpload}>
          {FWS_OFFICE_COPY.roster.uploadButton}
        </Button>
      </Space>
    </Card>
  );
}

function VerificationRequestCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  async function handleClick(): Promise<void> {
    if (!eventId) return;
    try {
      const body = await fwsPostQuery<{ timeout_minutes: number }>(
        OFFICE.verificationRequest(eventId),
        {},
      );
      onDone(`${body.timeout_minutes}${FWS_OFFICE_COPY.incident.verifyRequestSentSuffix}`);
    } catch {
      onError();
    }
  }

  return (
    <Button type="primary" onClick={handleClick} disabled={!eventId}>
      {FWS_OFFICE_COPY.incident.verifyRequestButton}
    </Button>
  );
}

function MisjudgeOrConfirmCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  async function handleReply(result: 'fire_confirmed' | 'false_alarm'): Promise<void> {
    if (!eventId) return;
    try {
      await fwsPostQuery(fwsEndpoint.verificationReply(eventId), {
        result,
        reason_code: result === 'false_alarm' ? 'other' : undefined,
      });
      onDone(result === 'fire_confirmed' ? '산불 확정됨' : '오인 종결됨');
    } catch {
      onError();
    }
  }

  return (
    <Space>
      <Button onClick={() => handleReply('fire_confirmed')} disabled={!eventId}>
        {FWS_OFFICE_COPY.incident.fireConfirmedButton}
      </Button>
      <Button onClick={() => handleReply('false_alarm')} disabled={!eventId}>
        {FWS_OFFICE_COPY.incident.falseAlarmButton}
      </Button>
    </Space>
  );
}

function IntakeCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [source, setSource] = useState('fire_119');
  const [facilityNote, setFacilityNote] = useState('');
  const [vehicleAccess, setVehicleAccess] = useState(false);
  const [fireIntensity, setFireIntensity] = useState('');

  async function handleSave(): Promise<void> {
    if (!eventId) return;
    try {
      await fwsPostQuery(OFFICE.intake(eventId), {
        source,
        facility_note: facilityNote || undefined,
        vehicle_access: vehicleAccess,
        fire_intensity: fireIntensity || undefined,
      });
      onDone(FWS_OFFICE_COPY.incident.intakeSavedNotice);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.incident.intakeTitle}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group value={source} onChange={(e) => setSource(e.target.value)}>
          <Radio.Button value="fire_119">{FWS_OFFICE_COPY.incident.intakeSource119}</Radio.Button>
          <Radio.Button value="forest_service">
            {FWS_OFFICE_COPY.incident.intakeSourceForest}
          </Radio.Button>
          <Radio.Button value="citizen">{FWS_OFFICE_COPY.incident.intakeSourceCitizen}</Radio.Button>
        </Radio.Group>
        <Space wrap>
          <Input
            placeholder="시설"
            value={facilityNote}
            onChange={(e) => setFacilityNote(e.target.value)}
            style={{ width: 160 }}
          />
          <Input
            placeholder="화세"
            value={fireIntensity}
            onChange={(e) => setFireIntensity(e.target.value)}
            style={{ width: 120 }}
          />
          <Checkbox checked={vehicleAccess} onChange={(e) => setVehicleAccess(e.target.checked)}>
            차량 진입 가능
          </Checkbox>
        </Space>
        <Button type="primary" onClick={handleSave} disabled={!eventId}>
          {FWS_OFFICE_COPY.incident.intakeSaveButton}
        </Button>
      </Space>
    </Card>
  );
}

function AgencyNotifyCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [helicopterBase, setHelicopterBase] = useState('');
  const [helicopterEta, setHelicopterEta] = useState('');

  async function handleSave(): Promise<void> {
    if (!eventId) return;
    try {
      await fwsPostQuery(OFFICE.agencyNotify(eventId), {
        helicopter_base: helicopterBase || undefined,
        helicopter_eta: helicopterEta || undefined,
      });
      onDone(FWS_OFFICE_COPY.incident.agencyNotifiedNotice);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.incident.agencyNotifyTitle}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Input
            placeholder={FWS_OFFICE_COPY.incident.helicopterBasePlaceholder}
            value={helicopterBase}
            onChange={(e) => setHelicopterBase(e.target.value)}
            style={{ width: 160 }}
          />
          <Input
            placeholder={FWS_OFFICE_COPY.incident.helicopterEtaPlaceholder}
            value={helicopterEta}
            onChange={(e) => setHelicopterEta(e.target.value)}
            style={{ width: 220 }}
          />
        </Space>
        <Button type="primary" onClick={handleSave} disabled={!eventId}>
          {FWS_OFFICE_COPY.incident.agencyNotifyButton}
        </Button>
      </Space>
    </Card>
  );
}

function ResourceAssignmentCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [kind, setKind] = useState('crew');
  const [resourceName, setResourceName] = useState('');

  async function handleAssign(): Promise<void> {
    if (!eventId || !resourceName) return;
    try {
      await fwsPostQuery(OFFICE.resourceAssignment(eventId), { kind, resource_name: resourceName });
      onDone(FWS_OFFICE_COPY.incident.resourceAssignedNotice);
      setResourceName('');
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.incident.resourceTitle}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)}>
          <Radio.Button value="crew">{FWS_OFFICE_COPY.incident.resourceKindCrew}</Radio.Button>
          <Radio.Button value="vehicle">{FWS_OFFICE_COPY.incident.resourceKindVehicle}</Radio.Button>
          <Radio.Button value="drone">{FWS_OFFICE_COPY.incident.resourceKindDrone}</Radio.Button>
        </Radio.Group>
        <Input
          placeholder={FWS_OFFICE_COPY.incident.resourceNamePlaceholder}
          value={resourceName}
          onChange={(e) => setResourceName(e.target.value)}
          style={{ width: 200 }}
        />
        <Button type="primary" onClick={handleAssign} disabled={!eventId}>
          {FWS_OFFICE_COPY.incident.resourceAssignButton}
        </Button>
      </Space>
    </Card>
  );
}

function StageProposalCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const [areaHa, setAreaHa] = useState<number | null>(null);
  const [windMps, setWindMps] = useState<number | null>(null);
  const [buildings, setBuildings] = useState<number | null>(null);
  const [proposed, setProposed] = useState<string | null>(null);

  async function handlePropose(): Promise<void> {
    if (!eventId || areaHa == null || windMps == null) return;
    try {
      const body = await fwsPostQuery<{ proposed_stage: string }>(OFFICE.stageProposal(eventId), {
        area_ha: areaHa,
        wind_mps: windMps,
        buildings_at_risk: buildings ?? undefined,
      });
      setProposed(body.proposed_stage);
      onDone(`${FWS_OFFICE_COPY.incident.stageProposedPrefix}: ${body.proposed_stage}`);
    } catch {
      onError();
    }
  }

  return (
    <Card title={FWS_OFFICE_COPY.incident.stageTitle}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <InputNumber
            placeholder={FWS_OFFICE_COPY.incident.areaPlaceholder}
            value={areaHa}
            onChange={setAreaHa}
          />
          <InputNumber
            placeholder={FWS_OFFICE_COPY.incident.windPlaceholder}
            value={windMps}
            onChange={setWindMps}
          />
          <InputNumber
            placeholder={FWS_OFFICE_COPY.incident.buildingsPlaceholder}
            value={buildings}
            onChange={setBuildings}
          />
        </Space>
        <Button type="primary" onClick={handlePropose} disabled={!eventId}>
          {FWS_OFFICE_COPY.incident.stageProposeButton}
        </Button>
        {proposed && (
          <Text>
            {FWS_OFFICE_COPY.incident.stageProposedPrefix}: {proposed}
          </Text>
        )}
      </Space>
    </Card>
  );
}
