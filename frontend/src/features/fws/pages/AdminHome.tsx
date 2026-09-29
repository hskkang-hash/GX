/**
 * FWS 기관 관리자(U5) — `/fws/admin` (WO-GX-20260929-17 §5 · 턴 AN 차선 N4).
 *
 * FWS-U5-01(카메라 산불 표식) · FWS-U5-02(초소·순찰함·순찰 구역) · FWS-U5-03
 * (마을·대피소·요양시설 — 대피 대상 자동 산출) · FWS-U5-04(알림 규칙 · 야간
 * 5분대기조 채널)을 한 화면에 모은다 — `DroneHome.tsx` 와 같은 모양(카드 여러 장 ·
 * 문구는 전부 `../copy_admin.ts` 에서 온다).
 *
 * ★ 지도·폴리곤 렌더는 이 화면에 없다 — §0.4 인접 금지구역 밖에 남긴다. 감시
 *   반경 폴리곤은 좌표 목록 **값**(JSON 문자열)으로만 다룬다(`DroneHome.tsx` 의
 *   열점·화선과 같은 판단).
 * ★ 경로는 새 엔드포인트 상수 없이 **문자열 그대로** 부른다 — `../api.ts` 는
 *   공용 파일(여러 차선이 함께 쓴다)이라 이 차선이 고치지 않는다.
 */
import { useEffect, useState } from 'react';

import {
  Alert,
  Button,
  Card,
  Checkbox,
  Input,
  InputNumber,
  List,
  Select,
  Space,
  Typography,
} from 'antd';

import { fwsGet, fwsPostQuery } from '../api';
import { FWS_ADMIN_COPY, FWS_ADMIN_UNKNOWN } from '../copy_admin';

const { Title, Text } = Typography;

const CAMERAS = '/api/fws/admin/cameras';
const cameraMarker = (id: string | number) => `/api/fws/admin/cameras/${id}/fire-marker`;
const POSTS = '/api/fws/admin/posts';
const EVAC_TARGETS = '/api/fws/admin/evac-targets';
const NOTIFY_RULES = '/api/fws/admin/notify-rules';
const NOTIFY_RULES_TEST = '/api/fws/admin/notify-rules/test';

interface CameraRow {
  camera_id: number;
  name: string;
  is_highland: boolean;
  thermal_channel: string;
  ptz_presets: string[];
  radius_polygon: Array<{ lat: number; lng: number }>;
}

interface PostRow {
  post_code: string;
  name: string;
  patrol_zone: string;
  nfc_boxes: string[];
}

interface EvacEntity {
  kind: string;
  name: string;
  headcount: number;
}

interface EvacTargetsBody {
  entities: EvacEntity[];
  evacuee_target_total: number;
  shelter_capacity_total: number;
  shelter_covers_target: boolean;
}

interface RoleSuggestion {
  role_code: string;
  label: string;
}

interface NotifyRuleRow {
  rule_id: number;
  severity: string;
  role_code: string;
  zone: string | null;
  channels: string[];
}

interface NotifyOverview {
  role_suggestions: RoleSuggestion[];
  night_standby_zone: string;
  rules: NotifyRuleRow[];
  critical_blocked: boolean;
}

export default function AdminHome(): JSX.Element {
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function onError(): void {
    setError(FWS_ADMIN_COPY.error.generic);
  }

  function onDone(message: string): void {
    setNotice(message);
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_ADMIN_COPY.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      <CameraCard onDone={onDone} onError={onError} />
      <PostCard onDone={onDone} onError={onError} />
      <EvacCard onDone={onDone} onError={onError} />
      <NotifyCard onDone={onDone} onError={onError} />
    </Space>
  );
}

function CameraCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const copy = FWS_ADMIN_COPY.camera;
  const [cameraId, setCameraId] = useState('');
  const [isHighland, setIsHighland] = useState(false);
  const [thermalChannel, setThermalChannel] = useState('');
  const [ptzPresets, setPtzPresets] = useState('');
  const [radiusPolygonJson, setRadiusPolygonJson] = useState('');
  const [cameras, setCameras] = useState<CameraRow[]>([]);

  async function reload(): Promise<void> {
    try {
      const body = await fwsGet<{ cameras: CameraRow[] }>(CAMERAS);
      setCameras(body.cameras);
    } catch {
      onError();
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function handleSave(): Promise<void> {
    if (!cameraId) return;
    try {
      await fwsPostQuery(cameraMarker(cameraId), {
        is_highland: isHighland,
        thermal_channel: thermalChannel || undefined,
        ptz_presets: ptzPresets || undefined,
        radius_polygon_json: radiusPolygonJson || undefined,
      });
      onDone(`#${cameraId}${copy.savedSuffix}`);
      await reload();
    } catch {
      onError();
    }
  }

  return (
    <Card title={copy.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Input
            placeholder={copy.idPlaceholder}
            value={cameraId}
            onChange={(e) => setCameraId(e.target.value)}
            style={{ width: 140 }}
          />
          <Checkbox checked={isHighland} onChange={(e) => setIsHighland(e.target.checked)}>
            {copy.highlandLabel}
          </Checkbox>
          <Input
            placeholder={copy.thermalChannelPlaceholder}
            value={thermalChannel}
            onChange={(e) => setThermalChannel(e.target.value)}
            style={{ width: 160 }}
          />
        </Space>
        <Input
          placeholder={copy.ptzPresetsPlaceholder}
          value={ptzPresets}
          onChange={(e) => setPtzPresets(e.target.value)}
        />
        <Input.TextArea
          placeholder={copy.radiusPolygonPlaceholder}
          value={radiusPolygonJson}
          onChange={(e) => setRadiusPolygonJson(e.target.value)}
          rows={2}
        />
        <Button type="primary" onClick={handleSave}>
          {copy.saveButton}
        </Button>
        <Text strong>{copy.listTitle}</Text>
        <List
          dataSource={cameras}
          locale={{ emptyText: FWS_ADMIN_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              #{row.camera_id} {row.name} · {row.is_highland ? copy.highlandLabel : '-'} ·{' '}
              {row.thermal_channel || FWS_ADMIN_UNKNOWN} · {row.ptz_presets.join(',') || '-'} ·{' '}
              {row.radius_polygon.length}점
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}

function PostCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const copy = FWS_ADMIN_COPY.post;
  const [postCode, setPostCode] = useState('');
  const [name, setName] = useState('');
  const [patrolZone, setPatrolZone] = useState('');
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [nfcBoxes, setNfcBoxes] = useState('');
  const [posts, setPosts] = useState<PostRow[]>([]);

  async function reload(): Promise<void> {
    try {
      const body = await fwsGet<{ posts: PostRow[] }>(POSTS);
      setPosts(body.posts);
    } catch {
      onError();
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function handleSave(): Promise<void> {
    if (!postCode || !name) return;
    try {
      await fwsPostQuery(POSTS, {
        post_code: postCode,
        name,
        patrol_zone: patrolZone || undefined,
        lat: lat ?? undefined,
        lng: lng ?? undefined,
        nfc_boxes: nfcBoxes || undefined,
      });
      onDone(copy.saveButton);
      await reload();
    } catch {
      onError();
    }
  }

  return (
    <Card title={copy.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Input
            placeholder={copy.codePlaceholder}
            value={postCode}
            onChange={(e) => setPostCode(e.target.value)}
            style={{ width: 140 }}
          />
          <Input
            placeholder={copy.namePlaceholder}
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 180 }}
          />
          <Input
            placeholder={copy.zonePlaceholder}
            value={patrolZone}
            onChange={(e) => setPatrolZone(e.target.value)}
            style={{ width: 160 }}
          />
        </Space>
        <Space wrap>
          <InputNumber placeholder={copy.latPlaceholder} value={lat} onChange={setLat} />
          <InputNumber placeholder={copy.lngPlaceholder} value={lng} onChange={setLng} />
          <Input
            placeholder={copy.nfcBoxesPlaceholder}
            value={nfcBoxes}
            onChange={(e) => setNfcBoxes(e.target.value)}
            style={{ width: 220 }}
          />
        </Space>
        <Button type="primary" onClick={handleSave}>
          {copy.saveButton}
        </Button>
        <Text strong>{copy.listTitle}</Text>
        <List
          dataSource={posts}
          locale={{ emptyText: FWS_ADMIN_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              {row.post_code} · {row.name} · {row.patrol_zone || '-'} ·{' '}
              {row.nfc_boxes.join(',') || '-'}
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}

function EvacCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const copy = FWS_ADMIN_COPY.evac;
  const [kind, setKind] = useState('village');
  const [name, setName] = useState('');
  const [headcount, setHeadcount] = useState<number | null>(null);
  const [body, setBody] = useState<EvacTargetsBody | null>(null);

  async function reload(): Promise<void> {
    try {
      const b = await fwsGet<EvacTargetsBody>(EVAC_TARGETS);
      setBody(b);
    } catch {
      onError();
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function handleSave(): Promise<void> {
    if (!name || headcount == null) return;
    try {
      await fwsPostQuery(EVAC_TARGETS, { kind, name, headcount });
      onDone(copy.saveButton);
      await reload();
    } catch {
      onError();
    }
  }

  const headcountPlaceholder =
    kind === 'shelter' ? copy.headcountShelterPlaceholder : copy.headcountVillagePlaceholder;

  return (
    <Card title={copy.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space wrap>
          <Select
            value={kind}
            onChange={setKind}
            style={{ width: 140 }}
            options={[
              { value: 'village', label: copy.kindVillage },
              { value: 'shelter', label: copy.kindShelter },
              { value: 'care_facility', label: copy.kindCareFacility },
            ]}
          />
          <Input
            placeholder={copy.namePlaceholder}
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 180 }}
          />
          <InputNumber
            placeholder={headcountPlaceholder}
            value={headcount}
            onChange={setHeadcount}
            style={{ width: 160 }}
          />
        </Space>
        <Button type="primary" onClick={handleSave}>
          {copy.saveButton}
        </Button>
        <Text strong>{copy.listTitle}</Text>
        <List
          dataSource={body?.entities ?? []}
          locale={{ emptyText: FWS_ADMIN_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              {row.kind} · {row.name} · {row.headcount}
            </List.Item>
          )}
        />
        {body && (
          <Text>
            {copy.targetTotalPrefix}: {body.evacuee_target_total} · {copy.capacityTotalPrefix}:{' '}
            {body.shelter_capacity_total} ·{' '}
            {body.shelter_covers_target ? copy.coversOk : copy.coversShort}
          </Text>
        )}
      </Space>
    </Card>
  );
}

function NotifyCard({
  onDone,
  onError,
}: {
  onDone: (m: string) => void;
  onError: () => void;
}): JSX.Element {
  const copy = FWS_ADMIN_COPY.notify;
  const [overview, setOverview] = useState<NotifyOverview | null>(null);
  const [severity, setSeverity] = useState('critical');
  const [roleCode, setRoleCode] = useState('');
  const [channels, setChannels] = useState('');
  const [nightStandby, setNightStandby] = useState(false);

  async function reload(): Promise<void> {
    try {
      const body = await fwsGet<NotifyOverview>(NOTIFY_RULES);
      setOverview(body);
      if (!roleCode && body.role_suggestions.length > 0) {
        setRoleCode(body.role_suggestions[0].role_code);
      }
    } catch {
      onError();
    }
  }

  useEffect(() => {
    void reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave(): Promise<void> {
    if (!roleCode || !channels) return;
    try {
      await fwsPostQuery(NOTIFY_RULES, {
        severity,
        role_code: roleCode,
        channels,
        zone: nightStandby ? overview?.night_standby_zone : undefined,
      });
      onDone(copy.saveButton);
      await reload();
    } catch {
      onError();
    }
  }

  async function handleTest(): Promise<void> {
    try {
      const body = await fwsPostQuery<{ sent: number }>(NOTIFY_RULES_TEST, { severity });
      onDone(`${body.sent}${copy.testSentSuffix}`);
    } catch {
      onError();
    }
  }

  return (
    <Card title={copy.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {overview?.critical_blocked && (
          <Alert type="warning" showIcon message={copy.criticalBlockedWarning} />
        )}
        <Space wrap>
          <Select
            value={severity}
            onChange={setSeverity}
            style={{ width: 140 }}
            options={['critical', 'high', 'medium', 'low'].map((s) => ({ value: s, label: s }))}
          />
          <Select
            value={roleCode || undefined}
            onChange={setRoleCode}
            placeholder={copy.roleLabel}
            style={{ width: 180 }}
            options={(overview?.role_suggestions ?? []).map((r) => ({
              value: r.role_code,
              label: r.label,
            }))}
          />
          <Input
            placeholder={copy.channelsPlaceholder}
            value={channels}
            onChange={(e) => setChannels(e.target.value)}
            style={{ width: 220 }}
          />
          <Checkbox checked={nightStandby} onChange={(e) => setNightStandby(e.target.checked)}>
            {copy.nightStandbyLabel}
          </Checkbox>
        </Space>
        <Space>
          <Button type="primary" onClick={handleSave}>
            {copy.saveButton}
          </Button>
          <Button onClick={handleTest}>{copy.testButton}</Button>
        </Space>
        <List
          dataSource={overview?.rules ?? []}
          locale={{ emptyText: FWS_ADMIN_UNKNOWN }}
          renderItem={(row) => (
            <List.Item>
              {row.severity} · {row.role_code} · {row.zone ?? '-'} · {row.channels.join(',')}
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}
