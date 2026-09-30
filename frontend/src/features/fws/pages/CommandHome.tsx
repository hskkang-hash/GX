/**
 * FWS F4 통합지휘본부장 · 상황실 — `/fws/command` (WO-GX-20260930-18 §5 P-414 ·
 * 턴 AO 차선 N2 · 턴 AQ 차선 N1 이 버튼을 배선).
 *
 * ★ 문구는 `../copy_command.ts` 에서, 경로는 `../api.ts::fwsCommandEndpoint` 에서
 *   온다(서버 짝 `backend/apps/fws/api_command.py` — 새 서버 문 0).
 * ★ 누르는 자리마다 `data-gx="fws-f4-XX-<동작>"` 를 단다. 누른 뒤에는 **그 화면의
 *   조회 GET 을 전부 다시 부른다**(`refreshAll` — 캐시 우회 `fwsGetFresh`).
 *   서버가 돌려준 쓰기 응답으로 화면을 그리지 않는다 — 재조회 값만 그린다.
 * ★ 지도·화선 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다. 위치는 주소 문자열로만 보인다(F4-03).
 */
import { useCallback, useEffect, useState } from 'react';

import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  List,
  Radio,
  Row,
  Select,
  Space,
  Tag,
  Typography,
} from 'antd';

import {
  fwsCommandEndpoint,
  fwsGetBlob,
  fwsGetFresh,
  fwsPostQuery,
  newFwsIdempotencyKey,
} from '../api';
import {
  fetchResourceBoard,
  fetchWithdrawalOrders,
  fwsW2cEndpoint,
  type ResourceBoardBody,
  type WithdrawalOrdersBody,
} from '../api_w2c';
import { FWS_COMMAND_COPY as C } from '../copy_command';
import { FieldSafetyAlertCard, ResourceBoardCard } from './W2cCommandCards';

const { Title, Text } = Typography;

type Row0 = Record<string, unknown>;

interface CommandScreenBody {
  event_id: number;
  incident: {
    address: string | null;
    severity: string | null;
    response_state: string | null;
    occurred_at: string | null;
  };
  stage: { stage: string; command_level: string | null } | null;
  resources: Array<{ kind: string; resource_name: string }>;
  response_clock: Record<string, string | null>;
  evacuation: { percent_complete: number | null; total_villages: number };
  command_post: { address: string; org_composition: string } | null;
}

interface StageBody {
  count: number;
  current: { stage: string; prior_stage: string | null; command_level: string | null; reason: string } | null;
}
interface CommandPostBody {
  declared: boolean;
  post: { address: string; org_composition: string; situation_room_phone: string | null } | null;
}
interface AircraftBody {
  count: number;
  approvals: Array<{
    requesting_org: string;
    drop_zone: { lat: number; lng: number };
    approved_at: string;
    deadline_at: string;
  }>;
}
interface EvacStatusBody {
  latest_approval: { urgency: string; approved_at: string; villages: string[]; status: string } | null;
  latest_release: { released_at: string; reason: string; status: string } | null;
}
interface AgencyBody {
  count: number;
  records: Array<{ agency: string; request_detail: string; requested_at: string }>;
}
interface FireDeclBody {
  main_fire_out: Array<{ declared_at: string }>;
  extinguished: Array<{ declared_at: string; response_state: string | null }>;
}
interface HourlyBody {
  count: number;
  approvals: Array<{ hour: string; approved_at: string; command_post_reflected: Row0 | null }>;
}
interface TimelineBody {
  response_state: string | null;
  timeline: Record<string, string | null>;
  golden_time_exceeded: boolean;
  golden_time_exceeded_reason: { reason: string } | null;
}
interface NightBody {
  sunset_at: string | null;
  is_night: boolean;
  helicopter_badge: string;
  night_resources: Array<{ resource_name: string; kind: string; available_at_night: boolean }>;
}
interface MeetingsBody {
  count: number;
  meetings: Array<Row0>;
}
interface ContactsBody {
  forest_service: { phone: string | null };
  provincial_situation_room: { phone: string | null };
}
interface HeliDropBody {
  count: number;
  drops: Array<{ dropped_at: string; recorded_at: string }>;
  first_dropped_at: string | null;
}
interface PriorityBody {
  count: number;
  unscored_count: number;
  items: Array<{
    event_id: number;
    severity: string | null;
    risk_index: number | null;
    risk_band: string | null;
    response_state: string | null;
    occurred_at: string | null;
    address: string | null;
  }>;
}
interface SummaryBody {
  response_state: string | null;
  resources: Array<{ kind: string; resource_name: string }>;
  evacuation: { total_villages: number; percent_complete: number | null };
  damage: { status: string };
}

interface Loaded {
  screen: CommandScreenBody | null;
  stage: StageBody | null;
  post: CommandPostBody | null;
  aircraft: AircraftBody | null;
  evac: EvacStatusBody | null;
  agency: AgencyBody | null;
  fire: FireDeclBody | null;
  hourly: HourlyBody | null;
  timeline: TimelineBody | null;
  night: NightBody | null;
  meetings: MeetingsBody | null;
  contacts: ContactsBody | null;
  heliDrops: HeliDropBody | null;
}

const EMPTY: Loaded = {
  screen: null,
  stage: null,
  post: null,
  aircraft: null,
  evac: null,
  agency: null,
  fire: null,
  hourly: null,
  timeline: null,
  night: null,
  meetings: null,
  contacts: null,
  heliDrops: null,
};

/** 대응단계 값 — 서버 `apps.fws.constants.FIRE_STAGES` 와 같은 글자(표시 이름 겸). */
const STAGES = ['1단계', '2단계', '3단계'];
/** 협조 기관 — 서버 `command.COORDINATION_AGENCIES` 값 ↔ 표시 이름. */
const AGENCIES: Array<{ value: string; label: string }> = [
  { value: 'fire_department', label: C.agency.agencyFire },
  { value: 'police', label: C.agency.agencyPolice },
  { value: 'military', label: C.agency.agencyMilitary },
];
const agencyLabel = (v: string): string => AGENCIES.find((a) => a.value === v)?.label ?? v;

async function settled<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

export default function CommandHome(): JSX.Element {
  const [eventId, setEventId] = useState('');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [data, setData] = useState<Loaded>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 입력 칸
  const [stage, setStage] = useState(STAGES[1]);
  const [stageReason, setStageReason] = useState('');
  const [commandLevel, setCommandLevel] = useState('');
  const [postAddress, setPostAddress] = useState('');
  const [postOrg, setPostOrg] = useState('');
  const [postPhone, setPostPhone] = useState('');
  const [heliOrg, setHeliOrg] = useState('');
  const [heliLat, setHeliLat] = useState('');
  const [heliLng, setHeliLng] = useState('');
  const [heliBase, setHeliBase] = useState('');
  const [heliEta, setHeliEta] = useState('');
  const [urgency, setUrgency] = useState('immediate');
  const [releaseReason, setReleaseReason] = useState('');
  const [agency, setAgency] = useState(AGENCIES[0].value);
  const [agencyDetail, setAgencyDetail] = useState('');
  const [extReason, setExtReason] = useState('');
  const [goldenReason, setGoldenReason] = useState('');
  const [sunsetAt, setSunsetAt] = useState('');
  const [attendees, setAttendees] = useState('');
  const [decision, setDecision] = useState('');
  const [basis, setBasis] = useState('');
  const [summary, setSummary] = useState<SummaryBody | null>(null);
  // [턴 AQ · N3] F4-13 우선순위 목록 · 사건별 지수 입력 칸 · F3-16 투하 시각 칸
  const [priority, setPriority] = useState<PriorityBody | null>(null);
  const [riskInputs, setRiskInputs] = useState<Record<number, string>>({});
  const [droppedAt, setDroppedAt] = useState('');
  // [턴 AQ · W2C] F2-01 자원 배치판 · F2-05 지원 요청 배지 · F1-10 철수 지시
  const [board, setBoard] = useState<ResourceBoardBody | null>(null);
  const [withdrawals, setWithdrawals] = useState<WithdrawalOrdersBody | null>(null);
  const [withdrawReason, setWithdrawReason] = useState('');

  /** F4-13 — 동시 다발 사건 목록(위험지수 내림차순)을 캐시 우회로 다시 부른다. */
  const refreshPriority = useCallback(async (): Promise<void> => {
    try {
      setPriority(await fwsGetFresh<PriorityBody>(fwsCommandEndpoint.priority));
    } catch {
      setError(C.priorityExtra.loadFailed);
    }
  }, []);

  useEffect(() => {
    void refreshPriority();
  }, [refreshPriority]);

  /** F4-13 — 한 사건의 산불위험지수 기록 → 목록 재조회(바뀐 정렬을 그린다). */
  async function recordRisk(targetId: number): Promise<void> {
    const raw = (riskInputs[targetId] ?? '').trim();
    if (!raw) return;
    setBusy(true);
    setNotice(null);
    try {
      await fwsPostQuery(fwsCommandEndpoint.riskIndex(targetId), { risk_index: raw },
        newFwsIdempotencyKey());
      setError(null);
      setNotice(C.action.done);
      setRiskInputs((prev) => ({ ...prev, [targetId]: '' }));
    } catch (e) {
      setError(`${C.action.failed} — ${(e as Error).message}`);
    } finally {
      await refreshPriority();
      if (activeId) await refreshAll(activeId);
      setBusy(false);
    }
  }

  /** 이 화면의 조회 GET 전부를 다시 부른다 — 누른 뒤 새 값은 여기서만 온다. */
  async function refreshAll(id: string): Promise<void> {
    const E = fwsCommandEndpoint;
    const [screen, stageB, post, aircraft, evac, agencyB, fire, hourly, timeline, night, meetings,
      contacts, heliDrops] =
      await Promise.all([
        settled(fwsGetFresh<CommandScreenBody>(E.screen(id))),
        settled(fwsGetFresh<StageBody>(E.stage(id))),
        settled(fwsGetFresh<CommandPostBody>(E.commandPost(id))),
        settled(fwsGetFresh<AircraftBody>(E.aircraft(id))),
        settled(fwsGetFresh<EvacStatusBody>(E.evacStatus(id))),
        settled(fwsGetFresh<AgencyBody>(E.agency(id))),
        settled(fwsGetFresh<FireDeclBody>(E.fireDeclarations(id))),
        settled(fwsGetFresh<HourlyBody>(E.hourlyApprove(id))),
        settled(fwsGetFresh<TimelineBody>(E.timeline(id))),
        settled(fwsGetFresh<NightBody>(E.nightStatus(id))),
        settled(fwsGetFresh<MeetingsBody>(E.meetings(id))),
        settled(fwsGetFresh<ContactsBody>(E.contacts(id))),
        settled(fwsGetFresh<HeliDropBody>(E.helicopterDrop(id))),
      ]);
    setData({
      screen,
      stage: stageB,
      post,
      aircraft,
      evac,
      agency: agencyB,
      fire,
      hourly,
      timeline,
      night,
      meetings,
      contacts,
      heliDrops,
    });
    if (screen === null) setError(C.home.loadFailed);
    // [턴 AQ · W2C] 자원 배치판(대기 인원·지원 요청 배지)·철수 지시도 같은 재조회에 싣는다.
    const [boardB, withdrawalsB] = await Promise.all([
      settled(fetchResourceBoard(id)),
      settled(fetchWithdrawalOrders(id)),
    ]);
    setBoard(boardB);
    setWithdrawals(withdrawalsB);
  }

  async function loadScreen(): Promise<void> {
    const id = eventId.trim();
    if (!id) return;
    setActiveId(id);
    setSummary(null);
    setError(null);
    setNotice(null);
    await refreshAll(id);
  }

  /** 쓰기 한 번 → 성공이면 조회 GET 재호출. 실패면 서버가 준 까닭을 그대로 보인다. */
  async function act(
    url: (id: string) => string,
    query: Record<string, string | number | boolean | undefined>,
  ): Promise<void> {
    if (!activeId) return;
    setBusy(true);
    setNotice(null);
    try {
      await fwsPostQuery(url(activeId), query, newFwsIdempotencyKey());
      setError(null);
      setNotice(C.action.done);
    } catch (e) {
      setError(`${C.action.failed} — ${(e as Error).message}`);
    } finally {
      await refreshAll(activeId);
      setBusy(false);
    }
  }

  async function loadSummary(): Promise<void> {
    if (!activeId) return;
    try {
      setSummary(await fwsGetFresh<SummaryBody>(fwsCommandEndpoint.postReportSummary(activeId)));
    } catch (e) {
      setError(`${C.action.failed} — ${(e as Error).message}`);
    }
  }

  async function downloadPdf(): Promise<void> {
    if (!activeId) return;
    try {
      const blob = await fwsGetBlob(fwsCommandEndpoint.postReportPdf(activeId));
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `guardianx-fws-command-${activeId}.pdf`;
      a.click();
      URL.revokeObjectURL(href);
    } catch {
      setError(C.postReport.downloadFailed);
    }
  }

  const none = <Text type="secondary">{C.screen.noneYet}</Text>;
  const E = fwsCommandEndpoint;
  const { screen } = data;

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{C.home.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      {/* ── F4-13 동시 다발 사건 우선순위(산불위험지수 눈금 · 정렬은 서버 한 곳) ── */}
      <Card title={C.priority.title}
        extra={<Button onClick={() => void refreshPriority()} data-gx="fws-f4-13-refresh">
          {C.priority.refreshButton}</Button>}>
        <List size="small" data-gx="fws-f4-13-list"
          dataSource={priority?.items ?? []}
          locale={{ emptyText: C.priorityExtra.empty }}
          renderItem={(it) => (
            <List.Item data-gx="fws-f4-13-row">
              <Space wrap>
                <Text strong>#{it.event_id}</Text>
                {it.risk_index === null ? (
                  <Tag>{C.priorityExtra.unscored}</Tag>
                ) : (
                  <Tag color="red" data-gx="fws-f4-13-risk">
                    {C.priorityExtra.riskLabel} {it.risk_index}{it.risk_band ? ` · ${it.risk_band}` : ''}
                  </Tag>
                )}
                <Text type="secondary">{it.address ?? ''} {it.occurred_at ?? ''}</Text>
                <Input style={{ width: 150 }} placeholder={C.priorityExtra.riskPlaceholder}
                  value={riskInputs[it.event_id] ?? ''}
                  onChange={(e) => setRiskInputs((prev) => ({ ...prev, [it.event_id]: e.target.value }))}
                  data-gx="fws-f4-13-risk-input" />
                <Button size="small" type="primary" disabled={busy} data-gx="fws-f4-13-record"
                  onClick={() => void recordRisk(it.event_id)}>
                  {C.priorityExtra.recordButton}
                </Button>
                <Button size="small" data-gx="fws-f4-13-open"
                  onClick={() => {
                    const id = String(it.event_id);
                    setEventId(id);
                    setActiveId(id);
                    setSummary(null);
                    setError(null);
                    void refreshAll(id);
                  }}>
                  {C.priorityExtra.openButton}
                </Button>
              </Space>
            </List.Item>
          )} />
      </Card>

      <Card>
        <Space wrap>
          <Input
            placeholder={C.home.eventIdLabel}
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            style={{ width: 200 }}
            data-gx="fws-f4-01-event-id"
          />
          <Button type="primary" onClick={loadScreen} data-gx="fws-f4-01-load">
            {C.home.loadButton}
          </Button>
        </Space>
      </Card>

      {screen && activeId && (
        <Row gutter={[16, 16]}>
          {/* ── F4-01 한 화면 — 사건 개요·단계·자원·시계·대피·지휘본부 ── */}
          <Col span={24}>
            <Card title={C.screen.incidentTitle} data-gx="fws-f4-01-screen">
              <Descriptions column={2} size="small">
                <Descriptions.Item label="주소">{screen.incident.address ?? C.screen.noneYet}</Descriptions.Item>
                <Descriptions.Item label="등급">{screen.incident.severity}</Descriptions.Item>
                <Descriptions.Item label="대응 상태">{screen.incident.response_state}</Descriptions.Item>
                <Descriptions.Item label="발생 시각">{screen.incident.occurred_at}</Descriptions.Item>
                <Descriptions.Item label={C.screen.stageTitle}>
                  {screen.stage
                    ? `${screen.stage.stage}${screen.stage.command_level ? ` · ${screen.stage.command_level}` : ''}`
                    : C.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label={C.screen.commandPostTitle}>
                  {screen.command_post
                    ? `${screen.command_post.address} · ${screen.command_post.org_composition}`
                    : C.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label={C.screen.resourcesTitle}>
                  {screen.resources.length === 0
                    ? C.screen.noneYet
                    : screen.resources.map((r) => `${r.kind} · ${r.resource_name}`).join(', ')}
                </Descriptions.Item>
                <Descriptions.Item label={C.screen.evacuationTitle}>
                  {screen.evacuation.total_villages}곳 중 {screen.evacuation.percent_complete ?? 0}% 완료
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>

          {/* ── F4-02 대응단계 확정·상향 · 지휘권 이양 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.stage.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-02-current">
                  {data.stage?.current ? (
                    <Space wrap>
                      <Tag color="red">{data.stage.current.stage}</Tag>
                      {data.stage.current.command_level && <Tag>{data.stage.current.command_level}</Tag>}
                      <Text type="secondary">
                        {C.stageExtra.priorLabel}: {data.stage.current.prior_stage ?? C.screen.noneYet} ·{' '}
                        {data.stage.current.reason} · {C.action.history} {data.stage.count}
                        {C.action.count}
                      </Text>
                    </Space>
                  ) : (
                    none
                  )}
                </div>
                <Space wrap>
                  <Select value={stage} onChange={setStage} style={{ width: 110 }} data-gx="fws-f4-02-stage"
                    options={STAGES.map((s) => ({ value: s, label: s }))} />
                  <Select value={commandLevel} onChange={setCommandLevel} style={{ width: 150 }}
                    data-gx="fws-f4-02-command-level"
                    options={[
                      { value: '', label: C.stage.commandLevelLabel },
                      { value: '시군구', label: C.stageExtra.levelMunicipal },
                      { value: '시도', label: C.stageExtra.levelProvincial },
                    ]} />
                </Space>
                <Input placeholder={C.stage.reasonPlaceholder} value={stageReason}
                  onChange={(e) => setStageReason(e.target.value)} data-gx="fws-f4-02-reason" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-02-confirm"
                  onClick={() => act(E.stage, { stage, reason: stageReason, command_level: commandLevel || undefined })}>
                  {C.stage.confirmButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-03 통합지휘본부 설치 선언 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.commandPost.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-03-current">
                  {data.post?.post ? (
                    <Text>
                      {data.post.post.address} · {data.post.post.org_composition}
                      {data.post.post.situation_room_phone ? ` · ${data.post.post.situation_room_phone}` : ''}
                    </Text>
                  ) : (
                    none
                  )}
                </div>
                <Input placeholder={C.commandPost.addressPlaceholder} value={postAddress}
                  onChange={(e) => setPostAddress(e.target.value)} data-gx="fws-f4-03-address" />
                <Input placeholder={C.commandPost.orgPlaceholder} value={postOrg}
                  onChange={(e) => setPostOrg(e.target.value)} data-gx="fws-f4-03-org" />
                <Input placeholder={C.commandPost.situationRoomPhonePlaceholder} value={postPhone}
                  onChange={(e) => setPostPhone(e.target.value)} data-gx="fws-f4-03-phone" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-03-declare"
                  onClick={() => act(E.commandPost, {
                    address: postAddress, org_composition: postOrg, situation_room_phone: postPhone || undefined,
                  })}>
                  {C.commandPost.declareButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-04 헬기 요청 승인 · 투하구역 지정(30분 시계) ── */}
          <Col xs={24} lg={12}>
            <Card title={C.aircraft.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-04-latest">
                  {data.aircraft && data.aircraft.approvals.length > 0 ? (() => {
                    const a = data.aircraft.approvals[data.aircraft.approvals.length - 1];
                    return (
                      <Text>
                        {a.requesting_org} · {C.aircraftExtra.dropZoneLabel} ({a.drop_zone.lat}, {a.drop_zone.lng}) ·{' '}
                        {C.aircraftExtra.deadlineLabel} {a.deadline_at}
                      </Text>
                    );
                  })() : none}
                </div>
                <Input placeholder={C.aircraft.orgPlaceholder} value={heliOrg}
                  onChange={(e) => setHeliOrg(e.target.value)} data-gx="fws-f4-04-org" />
                <Space wrap>
                  <Input placeholder={C.aircraftExtra.latPlaceholder} value={heliLat}
                    onChange={(e) => setHeliLat(e.target.value)} data-gx="fws-f4-04-lat" />
                  <Input placeholder={C.aircraftExtra.lngPlaceholder} value={heliLng}
                    onChange={(e) => setHeliLng(e.target.value)} data-gx="fws-f4-04-lng" />
                </Space>
                <Space wrap>
                  <Input placeholder={C.aircraft.baseLabel} value={heliBase}
                    onChange={(e) => setHeliBase(e.target.value)} data-gx="fws-f4-04-base" />
                  <Input placeholder={C.aircraft.etaLabel} value={heliEta}
                    onChange={(e) => setHeliEta(e.target.value)} data-gx="fws-f4-04-eta" />
                </Space>
                <Button type="primary" disabled={busy} data-gx="fws-f4-04-approve"
                  onClick={() => act(E.aircraft, {
                    requesting_org: heliOrg, drop_zone_lat: heliLat, drop_zone_lng: heliLng,
                    base: heliBase || undefined, eta: heliEta || undefined,
                  })}>
                  {C.aircraft.approveButton}
                </Button>
                {/* ── F3-16 헬기 물 투하 시각 저장(골든타임 「신고 → 투하 30분」의 끝 시각) ── */}
                <Text strong>{C.heliDrop.title}</Text>
                <div data-gx="fws-f3-16-drops">
                  {data.heliDrops && data.heliDrops.count > 0 ? (
                    <Text>
                      {C.heliDrop.firstLabel} {data.heliDrops.first_dropped_at} · {C.heliDrop.countLabel}{' '}
                      {data.heliDrops.count}{C.action.count}
                    </Text>
                  ) : none}
                </div>
                <Space wrap>
                  <Input type="datetime-local" placeholder={C.heliDrop.droppedAtPlaceholder} value={droppedAt}
                    onChange={(e) => setDroppedAt(e.target.value)} data-gx="fws-f3-16-dropped-at" />
                  <Button disabled={busy} data-gx="fws-f3-16-drop-save"
                    onClick={() => act(E.helicopterDrop, { dropped_at: droppedAt || undefined })}>
                    {C.heliDrop.saveButton}
                  </Button>
                </Space>
              </Space>
            </Card>
          </Col>

          {/* ── F4-09 산림청·시도 상황실 연락(전화 1클릭 · tel:) ── */}
          <Col xs={24} lg={12}>
            <Card title={C.contacts.title}>
              <Space direction="vertical" style={{ width: '100%' }} data-gx="fws-f4-09-contacts">
                {[
                  { key: 'forest', gx: 'fws-f4-09-call-forest', label: C.contacts.forestService, phone: data.contacts?.forest_service.phone ?? null },
                  {
                    key: 'provincial',
                    gx: 'fws-f4-09-call-provincial',
                    label: C.contacts.provincialRoom,
                    phone: data.contacts?.provincial_situation_room.phone ?? null,
                  },
                ].map((c) => (
                  <Space key={c.key} wrap>
                    <Text>{c.label}</Text>
                    {c.phone ? (
                      <Button type="primary" href={`tel:${c.phone.replace(/[^0-9+]/g, '')}`}
                        data-gx={c.gx}>
                        {C.contactsExtra.callButton} {c.phone}
                      </Button>
                    ) : (
                      <Tag data-gx={`fws-f4-09-unregistered-${c.key}`}>{C.contacts.unregistered}</Tag>
                    )}
                  </Space>
                ))}
              </Space>
            </Card>
          </Col>

          {/* ── F4-05 대피 명령 승인(즉시/준비) · 해제 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.evacuation.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-05-status">
                  {data.evac?.latest_approval ? (
                    <Text>
                      {C.evacuationExtra.statusLabel}:{' '}
                      {data.evac.latest_release &&
                      data.evac.latest_release.released_at > data.evac.latest_approval.approved_at
                        ? `${C.evacuation.releasedNotice} (${data.evac.latest_release.released_at})`
                        : `${C.evacuation.approvedNotice} (${data.evac.latest_approval.urgency === 'immediate'
                          ? C.evacuation.urgencyImmediate : C.evacuation.urgencyPrepare}) · ${
                          C.evacuationExtra.villagesLabel} ${data.evac.latest_approval.villages.join(', ')}`}
                    </Text>
                  ) : (
                    none
                  )}
                </div>
                <Radio.Group value={urgency} onChange={(e) => setUrgency(e.target.value)} data-gx="fws-f4-05-urgency">
                  <Radio value="immediate">{C.evacuation.urgencyImmediate}</Radio>
                  <Radio value="prepare">{C.evacuation.urgencyPrepare}</Radio>
                </Radio.Group>
                <Button type="primary" disabled={busy} data-gx="fws-f4-05-approve"
                  onClick={() => act(E.evacApprove, { urgency })}>
                  {C.evacuation.approveButton}
                </Button>
                <Input placeholder={C.evacuationExtra.releaseReasonPlaceholder} value={releaseReason}
                  onChange={(e) => setReleaseReason(e.target.value)} data-gx="fws-f4-05-release-reason" />
                <Button danger disabled={busy} data-gx="fws-f4-05-release"
                  onClick={() => act(E.evacRelease, { reason: releaseReason })}>
                  {C.evacuation.releaseButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── [턴 AQ · W2C] F2-01 자원 배치판 · F2-05 지원 요청 배지 ── */}
          <Col xs={24} lg={12}>
            <ResourceBoardCard
              board={board}
              busy={busy}
              onRefresh={() => void refreshAll(activeId)}
            />
          </Col>

          {/* ── [턴 AQ · W2C] F1-10 현장 안전 알림 — 대피 지시 도달 · 철수 지시 ── */}
          <Col xs={24} lg={12}>
            <FieldSafetyAlertCard
              evacNotifiedCount={
                (data.evac?.latest_approval as { notified_count?: number } | null | undefined)
                  ?.notified_count ?? null
              }
              evacApproved={Boolean(data.evac?.latest_approval)}
              withdrawals={withdrawals}
              reason={withdrawReason}
              onReasonChange={setWithdrawReason}
              busy={busy}
              onOrder={async () => {
                if (!withdrawReason.trim()) return;
                await act(fwsW2cEndpoint.withdrawalOrder, { reason: withdrawReason.trim() });
              }}
            />
          </Col>

          {/* ── F4-06 소방·경찰·군 협조 요청 기록 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.agency.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <List size="small" data-gx="fws-f4-06-records"
                  dataSource={data.agency?.records ?? []}
                  locale={{ emptyText: C.screen.noneYet }}
                  renderItem={(r) => (
                    <List.Item>
                      {agencyLabel(r.agency)} · {r.request_detail || '-'} · {r.requested_at}
                    </List.Item>
                  )} />
                <Space wrap>
                  <Select value={agency} onChange={setAgency} options={AGENCIES} style={{ width: 110 }}
                    data-gx="fws-f4-06-agency" />
                  <Input placeholder={C.agencyExtra.detailPlaceholder} value={agencyDetail}
                    onChange={(e) => setAgencyDetail(e.target.value)} data-gx="fws-f4-06-detail" />
                </Space>
                <Button type="primary" disabled={busy} data-gx="fws-f4-06-record"
                  onClick={() => act(E.agency, { agency, request_detail: agencyDetail || undefined })}>
                  {C.agency.recordButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-07 주불 진화 선언 · 진화완료 선언(종결 축) ── */}
          <Col xs={24} lg={12}>
            <Card title={C.fireDeclaration.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-07-declarations">
                  <div>
                    {C.fireDeclaration.mainOutNotice}:{' '}
                    {data.fire && data.fire.main_fire_out.length > 0
                      ? data.fire.main_fire_out[data.fire.main_fire_out.length - 1].declared_at
                      : C.screen.noneYet}
                  </div>
                  <div>
                    {C.fireDeclaration.extinguishedNotice}:{' '}
                    {data.fire && data.fire.extinguished.length > 0
                      ? data.fire.extinguished[data.fire.extinguished.length - 1].declared_at
                      : C.screen.noneYet}
                  </div>
                  <div>
                    {C.fireExtra.responseStateLabel}: {screen.incident.response_state ?? C.screen.noneYet}
                  </div>
                </div>
                <Button disabled={busy} data-gx="fws-f4-07-main-out"
                  onClick={() => act(E.mainFireOut, {})}>
                  {C.fireDeclaration.mainOutButton}
                </Button>
                <Input placeholder={C.fireExtra.extinguishedReasonPlaceholder} value={extReason}
                  onChange={(e) => setExtReason(e.target.value)} data-gx="fws-f4-07-reason" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-07-extinguished"
                  onClick={() => act(E.extinguished, { reason: extReason || undefined })}>
                  {C.fireDeclaration.extinguishedButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-08 상황보고 승인(매시간) ── */}
          <Col xs={24} lg={12}>
            <Card title={C.hourlyReport.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <List size="small" data-gx="fws-f4-08-approvals"
                  dataSource={data.hourly?.approvals ?? []}
                  locale={{ emptyText: C.screen.noneYet }}
                  renderItem={(r) => (
                    <List.Item>
                      {C.hourlyExtra.hourLabel} {r.hour} · {r.approved_at}
                      {r.command_post_reflected ? ` · ${C.hourlyExtra.reflectedLabel}` : ''}
                    </List.Item>
                  )} />
                <Button type="primary" disabled={busy} data-gx="fws-f4-08-approve"
                  onClick={() => act(E.hourlyApprove, {})}>
                  {C.hourlyReport.approveButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-10 대응 시계 + 골든타임 초과 사유 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.timeline.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Descriptions column={1} size="small" data-gx="fws-f4-10-timeline">
                  <Descriptions.Item label={C.timeline.reported}>
                    {data.timeline?.timeline.reported_at ?? C.screen.noneYet}
                  </Descriptions.Item>
                  <Descriptions.Item label={C.timeline.acknowledged}>
                    {data.timeline?.timeline.acknowledged_at ?? C.screen.noneYet}
                  </Descriptions.Item>
                  <Descriptions.Item label={C.timeline.helicopter}>
                    {data.timeline?.timeline.helicopter_dropped_at ?? C.screen.noneYet}
                  </Descriptions.Item>
                  <Descriptions.Item label={C.timeline.mainOut}>
                    {data.timeline?.timeline.main_fire_out_at ?? C.screen.noneYet}
                  </Descriptions.Item>
                  <Descriptions.Item label={C.timeline.extinguished}>
                    {data.timeline?.timeline.extinguished_at ?? C.screen.noneYet}
                  </Descriptions.Item>
                </Descriptions>
                <div data-gx="fws-f4-10-golden">
                  {data.timeline?.golden_time_exceeded ? (
                    <Tag color="red">{C.timeline.goldenExceeded}</Tag>
                  ) : (
                    <Tag color="green">{C.timeline.goldenOk}</Tag>
                  )}
                  {data.timeline?.golden_time_exceeded_reason && (
                    <Text>
                      {C.timeline.reasonLabel}: {data.timeline.golden_time_exceeded_reason.reason}
                    </Text>
                  )}
                </div>
                <Input placeholder={C.timeline.reasonPlaceholder} value={goldenReason}
                  onChange={(e) => setGoldenReason(e.target.value)} data-gx="fws-f4-10-reason" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-10-golden-reason"
                  onClick={() => act(E.goldenTimeReason, { reason: goldenReason })}>
                  {C.timeline.reasonButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-11 야간 전환(일몰) — 헬기 불가 · 야간 진화 자원 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.night.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <div data-gx="fws-f4-11-badge">
                  {data.night ? (
                    <Space wrap>
                      <Tag color={data.night.is_night ? 'blue' : 'gold'}>
                        {data.night.is_night ? C.nightExtra.nightNow : C.nightExtra.dayNow}
                      </Tag>
                      <Tag color={data.night.is_night ? 'red' : 'green'}>
                        {data.night.is_night ? C.night.helicopterUnavailable : C.night.helicopterAvailable}
                      </Tag>
                      <Text type="secondary">
                        {C.nightExtra.sunsetLabel}: {data.night.sunset_at ?? C.screen.noneYet}
                      </Text>
                    </Space>
                  ) : (
                    none
                  )}
                </div>
                <List size="small" data-gx="fws-f4-11-resources"
                  dataSource={data.night?.night_resources ?? []}
                  locale={{ emptyText: C.screen.noneYet }}
                  renderItem={(r) => (
                    <List.Item>
                      {r.kind} · {r.resource_name} ·{' '}
                      <Tag color={r.available_at_night ? 'green' : 'red'}>
                        {r.available_at_night ? C.nightExtra.nightOk : C.nightExtra.nightNo}
                      </Tag>
                    </List.Item>
                  )} />
                <Input type="datetime-local" placeholder={C.night.sunsetPlaceholder} value={sunsetAt}
                  onChange={(e) => setSunsetAt(e.target.value)} data-gx="fws-f4-11-sunset-at" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-11-sunset"
                  onClick={() => act(E.sunset, { sunset_at: sunsetAt })}>
                  {C.night.setButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-12 상황판단회의 기록 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.meeting.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <List size="small" data-gx="fws-f4-12-meetings"
                  dataSource={data.meetings?.meetings ?? []}
                  locale={{ emptyText: C.screen.noneYet }}
                  renderItem={(m) => <List.Item>{String(m.text ?? '')}</List.Item>} />
                <Input placeholder={C.meeting.attendeesPlaceholder} value={attendees}
                  onChange={(e) => setAttendees(e.target.value)} data-gx="fws-f4-12-attendees" />
                <Input placeholder={C.meeting.decisionPlaceholder} value={decision}
                  onChange={(e) => setDecision(e.target.value)} data-gx="fws-f4-12-decision" />
                <Input placeholder={C.meeting.basisPlaceholder} value={basis}
                  onChange={(e) => setBasis(e.target.value)} data-gx="fws-f4-12-basis" />
                <Button type="primary" disabled={busy} data-gx="fws-f4-12-record"
                  onClick={() => act(E.meetings, {
                    decision, attendees: attendees || undefined, basis: basis || undefined,
                  })}>
                  {C.meeting.recordButton}
                </Button>
              </Space>
            </Card>
          </Col>

          {/* ── F4-15 사후 보고서 1쪽 ── */}
          <Col xs={24} lg={12}>
            <Card title={C.postReport.title}>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Space wrap>
                  <Button onClick={loadSummary} data-gx="fws-f4-15-summary">
                    {C.postReport.summaryButton}
                  </Button>
                  <Button type="primary" onClick={downloadPdf} data-gx="fws-f4-15-pdf">
                    {C.postReport.downloadPdfButton}
                  </Button>
                </Space>
                <div data-gx="fws-f4-15-summary-view">
                  {summary ? (
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label={C.fireExtra.responseStateLabel}>
                        {summary.response_state ?? C.screen.noneYet}
                      </Descriptions.Item>
                      <Descriptions.Item label={C.postReport.resourcesLabel}>
                        {summary.resources.length === 0
                          ? C.screen.noneYet
                          : summary.resources.map((r) => `${r.kind} · ${r.resource_name}`).join(', ')}
                      </Descriptions.Item>
                      <Descriptions.Item label={C.postReport.evacuationLabel}>
                        {summary.evacuation.total_villages}곳 · {summary.evacuation.percent_complete ?? 0}%
                      </Descriptions.Item>
                      <Descriptions.Item label={C.postReport.damageLabel}>
                        {summary.damage.status || C.postReport.damagePending}
                      </Descriptions.Item>
                    </Descriptions>
                  ) : (
                    none
                  )}
                </div>
              </Space>
            </Card>
          </Col>
        </Row>
      )}
    </Space>
  );
}
