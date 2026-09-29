/**
 * FWS F3 산림과 보고 — `/fws/office/report` (WO-GX-20260929-17 §5 P-397 · 턴 AN
 * 차선 N3).
 *
 * F3-11~20(대피·상황보고·통계·오탐률·단속·훈련·온보딩)의 화면 쪽 짝이다. 서버
 * 쪽 짝은 `backend/apps/fws/office2.py`·`api_office2.py` — 실측은
 * `backend/tests/test_fws_f3b.py` 가 이미 했다.
 *
 * ★ 지도 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·FormRoute.tsx)
 *   밖에 남긴다. 좌표·마을 이름은 값으로만 다룬다.
 * ★ 문구는 전부 `../copy_office2.ts` 에서 온다(공용 `../copy.ts` 는 이 턴에 고치지
 *   않는다) — 화면에 문자열을 직접 짓지 않는다.
 * ★ 서버 호출은 기존 `../api.ts` 의 `fwsGet`/`fwsPostQuery` 함수만 쓴다(그 파일은
 *   고치지 않는다) — 경로 문자열은 이 화면이 직접 들고 있다(`/office2/...` 접두어
 *   — 같은 턴 차선 N2 의 `api_office.py` 경로와 겹치지 않는다).
 */
import { useState } from 'react';

import { Alert, Button, Card, Checkbox, Input, InputNumber, List, Radio, Space, Typography } from 'antd';

import { fwsGet, fwsPostQuery } from '../api';
import { FWS_OFFICE2_COPY as T, FWS_OFFICE2_UNKNOWN } from '../copy_office2';

const { Title, Text } = Typography;

const office2 = {
  evacPlan: (eventId: string) => `/api/fws/office2/evacuations/${eventId}/plan`,
  evacProgress: (eventId: string) => `/api/fws/office2/evacuations/${eventId}/progress`,
  evacStatus: (eventId: string) => `/api/fws/office2/evacuations/${eventId}/status`,
  hourly: (eventId: string) => `/api/fws/office2/reports/${eventId}/hourly`,
  final: (eventId: string) => `/api/fws/office2/reports/${eventId}/final`,
  statsFires: '/api/fws/office2/stats/fires',
  statsCamera: '/api/fws/office2/stats/camera-false-alarms',
  cameraThresholdTest: '/api/fws/office2/stats/camera-false-alarms/threshold-test',
  patrolEnforcement: '/api/fws/office2/patrol/enforcement',
  patrolEnforcementMine: '/api/fws/office2/patrol/enforcement/mine',
  entryZones: '/api/fws/office2/entry-control-zones',
  drillStart: '/api/fws/office2/drill/start',
  drillStatus: '/api/fws/office2/drill/status',
  drillEnd: '/api/fws/office2/drill/end',
  onboarding: '/api/fws/office2/onboarding/progress',
};

interface EvacStatus {
  total_villages: number;
  completed_villages: number;
  percent_complete: number | null;
  remaining_residents_total: number | null;
  care_facilities_open: number;
}

export default function OfficeReport(): JSX.Element {
  const [eventId, setEventId] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function onError(): void {
    setError(T.common.error);
  }

  function onDone(message: string): void {
    setNotice(message);
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{T.page.title}</Title>
      <Text type="secondary">{T.page.subtitle}</Text>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}

      <Card size="small">
        <Input
          addonBefore="#"
          placeholder={T.common.eventIdPlaceholder}
          value={eventId}
          onChange={(e) => setEventId(e.target.value)}
          style={{ width: 220 }}
        />
      </Card>

      <EvacuationCard eventId={eventId} onDone={onDone} onError={onError} />
      <HourlyReportCard eventId={eventId} onDone={onDone} onError={onError} />
      <FinalReportCard eventId={eventId} onDone={onDone} onError={onError} />
      <StatsCard onError={onError} />
      <CameraFprCard onDone={onDone} onError={onError} />
      <PatrolCard onDone={onDone} onError={onError} />
      <DrillCard onDone={onDone} onError={onError} />
      <OnboardingCard />
    </Space>
  );
}

function EvacuationCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [villages, setVillages] = useState<{ village: string; shelter: string }[]>([
    { village: '', shelter: '' },
  ]);
  const [kind, setKind] = useState<'recommend' | 'order'>('order');
  const [village, setVillage] = useState('');
  const [completed, setCompleted] = useState(false);
  const [remaining, setRemaining] = useState<number | null>(0);
  const [careCleared, setCareCleared] = useState(false);
  const [status, setStatus] = useState<EvacStatus | null>(null);

  function updateVillage(idx: number, field: 'village' | 'shelter', value: string) {
    setVillages((prev) => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
  }

  async function handleDraft(): Promise<void> {
    if (!eventId) return;
    const rows = villages.filter((row) => row.village.trim() && row.shelter.trim());
    if (rows.length === 0) return;
    try {
      await fwsPostQuery(office2.evacPlan(eventId), {
        villages_json: JSON.stringify(rows),
        kind,
      });
      onDone(`${rows.length}${T.evacuation.draftDoneSuffix}`);
      await reloadStatus();
    } catch {
      onError();
    }
  }

  async function handleProgress(): Promise<void> {
    if (!eventId || !village) return;
    try {
      await fwsPostQuery(office2.evacProgress(eventId), {
        village,
        completed,
        remaining_residents: remaining ?? 0,
        care_facility_cleared: careCleared,
      });
      await reloadStatus();
    } catch {
      onError();
    }
  }

  async function reloadStatus(): Promise<void> {
    if (!eventId) return;
    try {
      const body = await fwsGet<EvacStatus>(office2.evacStatus(eventId));
      setStatus(body);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.evacuation.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)}>
          <Radio.Button value="recommend">{T.evacuation.kindRecommend}</Radio.Button>
          <Radio.Button value="order">{T.evacuation.kindOrder}</Radio.Button>
        </Radio.Group>
        {villages.map((row, idx) => (
          <Space key={idx} wrap>
            <Input
              placeholder={T.evacuation.villageLabel}
              value={row.village}
              onChange={(e) => updateVillage(idx, 'village', e.target.value)}
              style={{ width: 160 }}
            />
            <Input
              placeholder={T.evacuation.shelterLabel}
              value={row.shelter}
              onChange={(e) => updateVillage(idx, 'shelter', e.target.value)}
              style={{ width: 160 }}
            />
          </Space>
        ))}
        <Button onClick={() => setVillages((prev) => [...prev, { village: '', shelter: '' }])}>
          {T.evacuation.addVillageButton}
        </Button>
        <Button type="primary" onClick={handleDraft}>
          {T.evacuation.draftButton}
        </Button>

        <Title level={5}>{T.evacuation.progressTitle}</Title>
        <Space wrap>
          <Input
            placeholder={T.evacuation.villageLabel}
            value={village}
            onChange={(e) => setVillage(e.target.value)}
            style={{ width: 160 }}
          />
          <Checkbox checked={completed} onChange={(e) => setCompleted(e.target.checked)}>
            {T.evacuation.completedLabel}
          </Checkbox>
          <InputNumber
            placeholder={T.evacuation.remainingResidentsLabel}
            value={remaining}
            onChange={setRemaining}
          />
          <Checkbox checked={careCleared} onChange={(e) => setCareCleared(e.target.checked)}>
            {T.evacuation.careFacilityLabel}
          </Checkbox>
          <Button onClick={handleProgress}>{T.evacuation.recordProgressButton}</Button>
        </Space>

        <Title level={5}>{T.evacuation.statusTitle}</Title>
        {status ? (
          <Text>
            {T.evacuation.percentCompletePrefix}: {status.percent_complete ?? FWS_OFFICE2_UNKNOWN}% ·{' '}
            {T.evacuation.remainingTotalPrefix}: {status.remaining_residents_total ?? FWS_OFFICE2_UNKNOWN} ·{' '}
            {T.evacuation.careOpenPrefix}: {status.care_facilities_open}
          </Text>
        ) : (
          <Text type="secondary">{FWS_OFFICE2_UNKNOWN}</Text>
        )}
        <Button onClick={reloadStatus}>{T.common.refresh}</Button>
      </Space>
    </Card>
  );
}

function HourlyReportCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [personnel, setPersonnel] = useState<number | null>(null);
  const [equipmentNote, setEquipmentNote] = useState('');
  const [weatherNote, setWeatherNote] = useState('');
  const [count, setCount] = useState<number | null>(null);

  async function handleDraft(): Promise<void> {
    if (!eventId) return;
    try {
      await fwsPostQuery(office2.hourly(eventId), {
        personnel_count: personnel ?? undefined,
        equipment_note: equipmentNote || undefined,
        weather_note: weatherNote || undefined,
      });
      const listed = await fwsGet<{ count: number }>(office2.hourly(eventId));
      setCount(listed.count);
      onDone(`${listed.count}${T.hourlyReport.draftDoneSuffix}`);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.hourlyReport.title}>
      <Space direction="vertical">
        <Space wrap>
          <InputNumber placeholder={T.hourlyReport.personnelLabel} value={personnel} onChange={setPersonnel} />
          <Input
            placeholder={T.hourlyReport.equipmentLabel}
            value={equipmentNote}
            onChange={(e) => setEquipmentNote(e.target.value)}
            style={{ width: 220 }}
          />
          <Input
            placeholder={T.hourlyReport.weatherLabel}
            value={weatherNote}
            onChange={(e) => setWeatherNote(e.target.value)}
            style={{ width: 220 }}
          />
        </Space>
        <Button type="primary" onClick={handleDraft}>
          {T.hourlyReport.draftButton}
        </Button>
        {count != null && <Text>{count}</Text>}
      </Space>
    </Card>
  );
}

function FinalReportCard({
  eventId,
  onDone,
  onError,
}: {
  eventId: string;
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [cause, setCause] = useState('입산자실화');
  const [areaHa, setAreaHa] = useState<number | null>(null);
  const [smsSent, setSmsSent] = useState(false);

  async function handleSave(): Promise<void> {
    if (!eventId || areaHa == null) return;
    try {
      await fwsPostQuery(office2.final(eventId), { cause, area_ha: areaHa, sms_sent: smsSent });
      onDone(T.finalReport.savedSuffix);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.finalReport.title}>
      <Space wrap>
        <Radio.Group value={cause} onChange={(e) => setCause(e.target.value)}>
          <Radio.Button value="입산자실화">{T.finalReport.causeHiker}</Radio.Button>
          <Radio.Button value="소각">{T.finalReport.causeBurning}</Radio.Button>
          <Radio.Button value="담뱃불">{T.finalReport.causeCigarette}</Radio.Button>
          <Radio.Button value="건축물화재">{T.finalReport.causeBuilding}</Radio.Button>
          <Radio.Button value="기타">{T.finalReport.causeOther}</Radio.Button>
        </Radio.Group>
        <InputNumber placeholder={T.finalReport.areaLabel} value={areaHa} onChange={setAreaHa} />
        <Checkbox checked={smsSent} onChange={(e) => setSmsSent(e.target.checked)}>
          {T.finalReport.smsSentLabel}
        </Checkbox>
        <Button type="primary" onClick={handleSave}>
          {T.finalReport.saveButton}
        </Button>
      </Space>
    </Card>
  );
}

function StatsCard({ onError }: { onError: () => void }): JSX.Element {
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);

  async function handleLoad(): Promise<void> {
    try {
      const body = await fwsGet<Record<string, unknown>>(office2.statsFires);
      setStats(body);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.stats.title}>
      <Space direction="vertical">
        <Button onClick={handleLoad}>{T.common.refresh}</Button>
        {stats && (
          <Text>
            {T.stats.occurrenceLabel}: {String(stats.occurrence_count)} ·{' '}
            {T.stats.falseAlarmRateLabel}: {String(stats.false_alarm_rate_pct ?? FWS_OFFICE2_UNKNOWN)}% ·{' '}
            {T.stats.goldenTimeLabel}: {String(stats.golden_time_compliance_pct ?? FWS_OFFICE2_UNKNOWN)}%
          </Text>
        )}
        {stats && <Text type="secondary">{T.stats.goldenTimeNote}</Text>}
      </Space>
    </Card>
  );
}

function CameraFprCard({
  onDone,
  onError,
}: {
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [streamMonitorId, setStreamMonitorId] = useState<number | null>(null);
  const [thresholdPct, setThresholdPct] = useState<number | null>(20);
  const [result, setResult] = useState<string | null>(null);

  async function handleTest(): Promise<void> {
    if (streamMonitorId == null || thresholdPct == null) return;
    try {
      const body = await fwsPostQuery<{ result: string }>(office2.cameraThresholdTest, {
        stream_monitor_id: streamMonitorId,
        threshold_pct: thresholdPct,
      });
      setResult(body.result);
      onDone(body.result);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.camera.title}>
      <Space wrap>
        <InputNumber placeholder="카메라 번호" value={streamMonitorId} onChange={setStreamMonitorId} />
        <InputNumber placeholder={T.camera.thresholdLabel} value={thresholdPct} onChange={setThresholdPct} />
        <Button onClick={handleTest}>{T.camera.runTestButton}</Button>
        {result && <Text>{result}</Text>}
      </Space>
    </Card>
  );
}

function PatrolCard({
  onDone,
  onError,
}: {
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [kind, setKind] = useState<'guidance' | 'enforcement'>('guidance');
  const [location, setLocation] = useState('');
  const [zoneName, setZoneName] = useState('');

  async function handleRecord(): Promise<void> {
    try {
      await fwsPostQuery(office2.patrolEnforcement, { kind, location: location || undefined });
      onDone(T.patrol.recordButton);
    } catch {
      onError();
    }
  }

  async function handleSetZone(status: 'active' | 'lifted'): Promise<void> {
    if (!zoneName) return;
    try {
      await fwsPostQuery(office2.entryZones, { zone_name: zoneName, status });
      onDone(T.patrol.setZoneButton);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.patrol.title}>
      <Space direction="vertical">
        <Space wrap>
          <Radio.Group value={kind} onChange={(e) => setKind(e.target.value)}>
            <Radio.Button value="guidance">{T.patrol.kindGuidance}</Radio.Button>
            <Radio.Button value="enforcement">{T.patrol.kindEnforcement}</Radio.Button>
          </Radio.Group>
          <Input
            placeholder={T.patrol.locationLabel}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            style={{ width: 200 }}
          />
          <Button onClick={handleRecord}>{T.patrol.recordButton}</Button>
        </Space>
        <Space wrap>
          <Input
            placeholder={T.patrol.zoneNameLabel}
            value={zoneName}
            onChange={(e) => setZoneName(e.target.value)}
            style={{ width: 200 }}
          />
          <Button onClick={() => handleSetZone('active')}>{T.patrol.zoneActive}</Button>
          <Button onClick={() => handleSetZone('lifted')}>{T.patrol.zoneLifted}</Button>
        </Space>
      </Space>
    </Card>
  );
}

function DrillCard({
  onDone,
  onError,
}: {
  onDone: (message: string) => void;
  onError: () => void;
}): JSX.Element {
  const [reason, setReason] = useState('');
  const [inProgress, setInProgress] = useState<boolean | null>(null);

  async function handleStart(): Promise<void> {
    if (!reason) return;
    try {
      const body = await fwsPostQuery<{ drill_mode: boolean }>(office2.drillStart, { reason });
      setInProgress(body.drill_mode);
      onDone(T.drill.startButton);
    } catch {
      onError();
    }
  }

  async function handleEnd(): Promise<void> {
    try {
      const body = await fwsPostQuery<{ real_channel_sends: number }>(office2.drillEnd, {
        reason: reason || undefined,
      });
      setInProgress(false);
      onDone(`${T.drill.realChannelSendsPrefix}: ${body.real_channel_sends}`);
    } catch {
      onError();
    }
  }

  return (
    <Card title={T.drill.title}>
      <Space wrap>
        <Input
          placeholder={T.drill.reasonLabel}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          style={{ width: 220 }}
        />
        <Button onClick={handleStart}>{T.drill.startButton}</Button>
        <Button onClick={handleEnd}>{T.drill.endButton}</Button>
        <Text>{inProgress ? T.drill.inProgress : T.drill.notRunning}</Text>
      </Space>
    </Card>
  );
}

function OnboardingCard(): JSX.Element {
  const [cards, setCards] = useState<{ key: string; prompt: string; closed: boolean }[]>([]);
  const [percent, setPercent] = useState<number | null>(null);

  async function handleLoad(): Promise<void> {
    try {
      const body = await fwsGet<{ cards: typeof cards; percent: number }>(office2.onboarding);
      setCards(body.cards);
      setPercent(body.percent);
    } catch {
      // 조용히 무시 — 온보딩 카드는 부가 정보다.
    }
  }

  return (
    <Card title={T.onboarding.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        <Button onClick={handleLoad}>{T.common.refresh}</Button>
        {percent != null && (
          <Text>
            {T.onboarding.donePrefix}: {percent}%
          </Text>
        )}
        <List
          dataSource={cards}
          locale={{ emptyText: FWS_OFFICE2_UNKNOWN }}
          renderItem={(card) => (
            <List.Item>
              {card.prompt} — {card.closed ? '완료' : '미완료'}
            </List.Item>
          )}
        />
      </Space>
    </Card>
  );
}
