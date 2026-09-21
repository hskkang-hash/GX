/**
 * 기관 관리자 설정 — 구역 · 임계값 · 등급규칙 (턴 Z · 차선 A · P-210).
 *
 * ★★ **새 서버 문을 0개 만들었다.** 이 화면이 부르는 여섯 자리는 전부 이미 서 있던 것이다:
 *
 *      GET  /api/dsm/settings/zones         구역 목록 (설정 조회 문 domain=zones)
 *      POST /api/dsm/settings/zones         구역 저장 (save_zone)
 *      GET  /api/dsm/settings/thresholds    임계값 표 + 바꾼 기록
 *      POST /api/dsm/settings/thresholds    임계값 저장 (사유 필수)
 *      GET  /api/dsm/settings/grade_rules   등급규칙 표 + 바꾼 기록  ← **밑줄이다**
 *      POST /api/dsm/settings/grade-rules   등급규칙 저장 (사유 필수)
 *
 *   ⚠ 조회는 밑줄(`grade_rules`)이고 쓰기는 하이픈(`grade-rules`)이다. 설정 **영역
 *     이름**은 밑줄이고 쓰기 **경로**는 하이픈이라, 둘을 같은 글자로 쓰면 한쪽이
 *     405 로 죽는다 — 그 405 는 「없다」가 아니라 「이 문은 다른 메서드만 안다」다.
 *     `api.ts` 의 `apiKeysOverview`(`settings/api_keys`)가 같은 자리를 이미 겪었다.
 *
 * ★ **경로 문자열을 이 파일에 둔 이유** — 평소 규약은 `api.ts` 한 곳이다. 이번 턴에
 *   그 파일은 다른 차선의 것이라 줄을 끼우지 않는다(끼우면 병합이 깨지고, 깨지는 것은
 *   대개 경로 문자열이며 그 충돌은 **라우팅 침묵**으로 나타난다). 조율자가 병합할 때
 *   아래 `SETTINGS_PATH` 를 `api.ts` 로 옮기면 된다 — 옮겨도 화면은 그대로 돈다.
 *
 * ★★ **저장 인자가 어디로 실리는가 — 짐작하지 않고 쟀다**
 *   [실측 2026-09-21 · gx-shell · 돌고 있는 서버의 OpenAPI]
 *
 *      POST settings/thresholds    key · value · reason · scope_level · scope_ref  → **전부 질의**
 *      POST settings/grade-rules   event_type · severity · reason                  → **전부 질의**
 *      POST settings/zones         name · kind · zone_id · geometry · is_active    → 질의
 *                                  camera_ids                                      → **본문**(정수 배열)
 *
 *   그래서 구역 저장만 `질의 + 본문`을 함께 보낸다. 본문으로 보내야 할 것을 질의로
 *   보내면 돌아오는 것은 422 이고, 그 422 는 「값이 틀렸다」가 아니라 「인자가 없다」다.
 *
 * ★★ **폴리곤 구역은 이 화면에서 만들지 않는다 — 못 만든다(실측).**
 *   [실측 2026-09-21 · 돌고 있는 서버의 서명으로 A/B] `geometry` 는 **질의**에 실리는
 *   객체 칸이다. 브라우저가 보낼 수 있는 것은 글자뿐이므로 JSON 을 글자로 실어 보내면
 *
 *      422 — geometry: Input should be a valid dictionary (input_type=str)
 *
 *   로 멈춘다. 같은 호출에서 `kind=camera_group` (도형 없음)은 통과한다.
 *   즉 **카메라 묶음 구역은 지금 문으로 저장되고, 폴리곤은 지금 문으로 저장되지 않는다.**
 *   이 사실을 화면이 「아직 없다」로 덮지 않는다 — 폴리곤 칸을 그려 놓고 누를 때마다
 *   422 를 받게 하는 것이 사람에게 더 나쁘다. 그래서 그 칸을 **그리지 않고**, 대신
 *   못 하는 일을 누르기 전에 한 줄로 적는다.
 *
 * ★ **누른 뒤를 본다.** 세 갈래 모두 저장 응답을 믿지 않고 **새 GET 으로 다시 읽어**
 *   그 값을 화면의 「지금」 칸에 그린다. 저장 응답만 그리면 「썼다고 말한 것」과
 *   「쓰인 것」이 화면에서 같은 그림이 된다.
 *
 * ★ 사유는 **화면이 먼저 묻는다.** 서버도 사유가 비면 거절하지만(400), 거절을 사람이
 *   만나기 전에 묻는 것이 이 칸의 일이다 — 카메라 축 튜닝 화면이 이미 그렇게 한다.
 *
 * ★ 자리: **기관 관리자.** 권한이 없는 계정에는 조회가 403 이고, 그 403 은 이 화면이
 *   자기 자리에서 말한다(위에서 내려오는 띠가 상태 칸의 단추를 덮지 않게).
 */
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  Button,
  Card,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';

import { ownDenialPaths } from '@/features/session/permissionDenied';

import {
  dsmGet,
  dsmPost,
  dsmPostQuery,
  intentKey,
  dsmPostQueryOnce,
} from '../api';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { userFacingError } from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
import { EVENT_TYPE_LABEL, SEVERITY_LABEL, labelOf } from '../severity';

const { Title, Text, Paragraph } = Typography;

/**
 * 부르는 자리 여섯. **문자열을 화면 곳곳에 흩지 않는다** — 한 곳에서만 정한다
 * (머리말의 「경로 문자열을 이 파일에 둔 이유」를 보라).
 */
const SETTINGS_PATH = {
  /** 구역 — 한 경로에 GET·POST 가 함께 선다. */
  zones: '/api/dsm/settings/zones',
  /** 임계값 — 같은 모양. */
  thresholds: '/api/dsm/settings/thresholds',
  /** 등급규칙 **조회** — 설정 영역 이름이라 밑줄이다. */
  gradeRulesRead: '/api/dsm/settings/grade_rules',
  /** 등급규칙 **쓰기** — 쓰기 경로라 하이픈이다. */
  gradeRulesWrite: '/api/dsm/settings/grade-rules',
} as const;

/** 서버가 쓰는 구역 종류 값. 화면이 새 낱말을 만들지 않는다. */
const ZONE_KIND_CAMERA_GROUP = 'camera_group';

/** 구역 종류의 우리말 — 서버 모형이 이미 이 낱말로 부른다. */
const ZONE_KIND_LABEL: Record<string, string> = {
  camera_group: '카메라 묶음',
  polygon: '폴리곤',
};

/** 계약이 못박은 세 등급. 새 등급을 이 화면에서 만들 수 없다(서버가 거절한다). */
const SEVERITY_CHOICES = ['critical', 'warning', 'info'] as const;

interface ZoneRow {
  zone_id: number;
  name: string;
  kind: string;
  geometry_status: string;
  is_active: boolean;
  camera_count: number;
  crs: string;
  judgeable: boolean;
  reason: string;
}

interface ZonesView {
  zones: ZoneRow[];
  crs: string;
}

interface ThresholdRow {
  key: string;
  title: string;
  unit: string;
  default: number | null;
  value: number | null;
  /** 이 값이 어디서 왔나 — 정의 기본값인가, 누가 덮어쓴 값인가. */
  source: string;
  /** 이 항목이 사는 층. 저장할 층을 화면이 짐작하지 않고 여기서 고른다. */
  applies_to: string;
  contract_fixed: boolean;
}

interface ThresholdHistoryRow {
  key: string;
  scope_level: string;
  old: number | null;
  new: number | null;
  reason: string;
  changed_at: string | null;
}

interface ThresholdsView {
  thresholds: ThresholdRow[];
  history: ThresholdHistoryRow[];
}

interface GradeRuleRow {
  event_type: string;
  severity: string;
  default_severity: string;
  overridden: boolean;
  reason: string;
  /** 참이면 그 유형은 **조용해진 것**이다. 화면이 반드시 보여 줘야 하는 칸. */
  lowered: boolean;
}

interface GradeRuleHistoryRow {
  event_type: string;
  old_severity: string;
  new_severity: string;
  reason: string;
  changed_at: string | null;
}

interface GradeRulesView {
  grade_rules: GradeRuleRow[];
  lowered_count: number;
  history: GradeRuleHistoryRow[];
}

/**
 * 저장할 층 — **짐작하지 않는다.** 서버가 이 항목을 전체 층 것이라 적어 두었으면
 * 전체로, 아니면 기관 층으로 쓴다. 전체 층 항목에 기관 층을 쓰면 서버가 거절한다.
 */
function levelOf(row: ThresholdRow): string {
  return row.applies_to === 'global' ? 'global' : 'tenant';
}

/**
 * 사유를 **먼저 묻는다.** 비우고 확인을 누르면 창이 닫히지 않는다 —
 * 닫히면 저장된 것처럼 보인다.
 */
function askReason(title: string, onOk: (reason: string) => Promise<void>): void {
  let typed = '';
  Modal.confirm({
    title,
    content: (
      <Space direction="vertical" style={{ width: '100%' }}>
        <Text type="secondary">
          사유는 반드시 적어야 합니다. 무엇에서 무엇으로 바꿨는지는 기록이 알지만,
          왜 바꿨는지는 여기서만 남습니다. 사유가 비면 저장되지 않습니다.
        </Text>
        <Input.TextArea
          rows={2}
          placeholder="바꾸는 사유 (필수)"
          onChange={(ev) => {
            typed = ev.target.value;
          }}
        />
      </Space>
    ),
    okText: '저장',
    cancelText: '취소',
    onOk: async () => {
      if (!typed.trim()) {
        message.error('사유가 비어 있습니다. 사유 없이는 저장할 수 없습니다.');
        throw new Error('reason required');
      }
      await onOk(typed.trim());
    },
  });
}

/* ═══════════════════════════════════════════════════════════════════════════
 * 구역
 * ═══════════════════════════════════════════════════════════════════════════ */
function ZonesTab() {
  const [name, setName] = useState('');
  const [cameraIds, setCameraIds] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<{ text: string; status: number } | null>(null);

  const zones = useDsmResource<ZonesView>(
    () => dsmGet<ZonesView>(SETTINGS_PATH.zones),
    [],
    { isEmpty: (v) => (v?.zones?.length ?? 0) === 0 },
  );

  const rows = useMemo(() => zones.data?.zones ?? [], [zones.data]);
  const activeCount = rows.filter((r) => r.is_active).length;

  /**
   * 만들기 — 이름과 (있으면) 카메라 번호들.
   * ⚠ 카메라 번호는 **본문**으로 간다. 질의로 보내면 서버가 「인자가 없다」로 멈춘다.
   */
  const create = useCallback(() => {
    const trimmed = name.trim();
    if (!trimmed) {
      message.info('구역 이름을 적어 주십시오.');
      return;
    }
    const ids = cameraIds
      .split(/[^0-9]+/)
      .filter((s) => s !== '')
      .map((s) => Number(s));
    setSaving(true);
    setSaveError(null);
    (async () => {
      try {
        const qs = new URLSearchParams({
          name: trimmed,
          kind: ZONE_KIND_CAMERA_GROUP,
          is_active: 'true',
        }).toString();
        await dsmPost(`${SETTINGS_PATH.zones}?${qs}`, ids.length ? ids : null);
        setName('');
        setCameraIds('');
        message.success('저장했습니다. 아래 표를 다시 읽습니다.');
        // ★ 누른 뒤를 본다 — 저장 응답이 아니라 **다시 읽은 목록**이 증거다.
        zones.reload();
      } catch (err) {
        setSaveError({
          text: userFacingError('SettingsRules.zoneCreate', err, '구역을 저장하지 못했습니다.'),
          status: (err as { status?: number })?.status ?? 0,
        });
      } finally {
        setSaving(false);
      }
    })();
  }, [name, cameraIds, zones]);

  /** 끄기·켜기 — **같은 문으로 되돌아온다.** 한 번 더 누르면 원래 값이다. */
  const toggle = useCallback(
    async (row: ZoneRow) => {
      setSaving(true);
      setSaveError(null);
      try {
        const qs = new URLSearchParams({
          zone_id: String(row.zone_id),
          name: row.name,
          kind: row.kind,
          is_active: row.is_active ? 'false' : 'true',
        }).toString();
        await dsmPost(`${SETTINGS_PATH.zones}?${qs}`, null);
        message.success('저장했습니다. 아래 표를 다시 읽습니다.');
        zones.reload();
      } catch (err) {
        setSaveError({
          text: userFacingError('SettingsRules.zoneToggle', err, '구역을 저장하지 못했습니다.'),
          status: (err as { status?: number })?.status ?? 0,
        });
      } finally {
        setSaving(false);
      }
    },
    [zones],
  );

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small" title="새 구역 만들기">
        <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
          카메라 묶음 구역을 만듭니다. 폴리곤 구역은 이 화면에서 만들지 않습니다.
        </Paragraph>
        <Space wrap>
          <Input
            style={{ width: 220 }}
            placeholder="구역 이름"
            value={name}
            onChange={(ev) => setName(ev.target.value)}
            allowClear
          />
          <Input
            style={{ width: 220 }}
            placeholder="카메라 번호 (쉼표로 나눕니다 · 비워도 됩니다)"
            value={cameraIds}
            onChange={(ev) => setCameraIds(ev.target.value)}
            allowClear
          />
          <Button type="primary" loading={saving} onClick={create}>
            만들기
          </Button>
        </Space>
      </Card>

      {saveError ? (
        <FailureNotice
          title="구역을 저장하지 못했습니다."
          detail={saveError.text}
          status={saveError.status}
          onRetry={() => setSaveError(null)}
          retryLabel="닫기"
        />
      ) : null}

      <Card size="small" title="등록된 구역">
        <Paragraph data-gx="zones-now" style={{ marginBottom: 8 }}>
          가동 중인 구역 {activeCount}개 · 전체 {rows.length}개
        </Paragraph>
        <StateBoundary
          state={zones.state}
          reason={zones.reason}
          status={zones.status}
          onRetry={zones.reload}
          emptyText="아직 만든 구역이 없습니다. (요청은 성공했고 0건입니다)"
          emptyNext="위에서 구역을 만들면 이 자리에 나타납니다."
          where="SettingsRules.zones"
        >
          <Table<ZoneRow>
            size="small"
            rowKey="zone_id"
            dataSource={rows}
            pagination={false}
            columns={[
              { title: '이름', dataIndex: 'name' },
              {
                title: '종류',
                dataIndex: 'kind',
                width: 120,
                render: (v: string) => ZONE_KIND_LABEL[v] ?? v,
              },
              { title: '카메라 대수', dataIndex: 'camera_count', width: 110 },
              {
                title: '가동',
                dataIndex: 'is_active',
                width: 90,
                render: (v: boolean) => (v ? <Tag color="green">가동</Tag> : <Tag>멈춤</Tag>),
              },
              {
                title: '판정',
                dataIndex: 'judgeable',
                width: 150,
                render: (v: boolean, row: ZoneRow) =>
                  v ? <Tag color="green">판정할 수 있습니다</Tag> : (
                    <Tag color="red">{row.reason || '판정할 수 없습니다'}</Tag>
                  ),
              },
              {
                title: '',
                key: 'act',
                width: 90,
                render: (_: unknown, row: ZoneRow) => (
                  <Button size="small" loading={saving} onClick={() => toggle(row)}>
                    {row.is_active ? '끄기' : '켜기'}
                  </Button>
                ),
              },
            ]}
          />
        </StateBoundary>
      </Card>
    </Space>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
 * 임계값
 * ═══════════════════════════════════════════════════════════════════════════ */
function ThresholdsTab() {
  const [picked, setPicked] = useState<string>('');
  const [value, setValue] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<{ text: string; status: number } | null>(null);

  const view = useDsmResource<ThresholdsView>(
    () => dsmGet<ThresholdsView>(SETTINGS_PATH.thresholds),
    [],
    { isEmpty: (v) => (v?.thresholds?.length ?? 0) === 0 },
  );

  const rows = useMemo(() => view.data?.thresholds ?? [], [view.data]);
  const history = view.data?.history ?? [];
  const overridden = rows.filter((r) => r.source === 'override').length;
  const current = rows.find((r) => r.key === picked) ?? null;

  const save = useCallback(() => {
    if (!current) {
      message.info('바꿀 항목을 먼저 고르십시오.');
      return;
    }
    const numeric = Number(value);
    if (value.trim() === '' || Number.isNaN(numeric)) {
      message.info('저장할 값을 숫자로 적어 주십시오.');
      return;
    }
    askReason('이 항목의 기준선을 바꿉니다', async (reason) => {
      setSaving(true);
      setSaveError(null);
      try {
        await dsmPostQueryOnce(
          SETTINGS_PATH.thresholds,
          {
            key: current.key,
            value: numeric,
            reason,
            scope_level: levelOf(current),
          },
          intentKey(`baseline:${current.key}`),
        );
        message.success('저장했습니다. 아래 표를 다시 읽습니다.');
        // ★ 누른 뒤를 본다 — 다시 읽은 표의 「지금 값」이 증거다.
        view.reload();
      } catch (err) {
        setSaveError({
          text: userFacingError('SettingsRules.thresholdSave', err, '기준선을 저장하지 못했습니다.'),
          status: (err as { status?: number })?.status ?? 0,
        });
        throw err; // 창을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
      } finally {
        setSaving(false);
      }
    });
  }, [current, value, view]);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small" title="저장 축 — 항목 단위 (서버가 정한 단위 · 사유를 적어야 저장됨)">
        <Space wrap>
          <Select
            style={{ width: 320 }}
            placeholder="바꿀 항목"
            value={picked || undefined}
            onChange={(v: string) => {
              setPicked(v);
              const row = rows.find((r) => r.key === v);
              setValue(row?.value === null || row?.value === undefined ? '' : String(row.value));
            }}
            options={rows.map((r) => ({
              value: r.key,
              label: r.contract_fixed ? `${r.title} (계약이 정한 값)` : r.title,
            }))}
          />
          <Input
            style={{ width: 160 }}
            placeholder="바꿀 값"
            value={value}
            onChange={(ev) => setValue(ev.target.value)}
            suffix={current?.unit ?? ''}
          />
          <Button
            type="primary"
            loading={saving}
            disabled={!current || current.contract_fixed}
            onClick={save}
          >
            저장
          </Button>
        </Space>
        {current?.contract_fixed ? (
          <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>
            계약이 정한 값이라 이 화면에서 바꿀 수 없습니다.
          </Paragraph>
        ) : null}
      </Card>

      {saveError ? (
        <FailureNotice
          title="기준선을 저장하지 못했습니다."
          detail={saveError.text}
          status={saveError.status}
          onRetry={() => setSaveError(null)}
          retryLabel="닫기"
        />
      ) : null}

      <Card size="small" title="지금 값">
        <Paragraph data-gx="thresholds-now" style={{ marginBottom: 8 }}>
          바꿔 둔 항목 {overridden}개 · 전체 {rows.length}개
        </Paragraph>
        <StateBoundary
          state={view.state}
          reason={view.reason}
          status={view.status}
          onRetry={view.reload}
          emptyText="읽을 항목이 없습니다. (요청은 성공했고 0건입니다)"
          where="SettingsRules.thresholds"
        >
          <Table<ThresholdRow>
            size="small"
            rowKey="key"
            dataSource={rows}
            pagination={false}
            columns={[
              { title: '항목', dataIndex: 'title' },
              {
                title: '지금 값',
                dataIndex: 'value',
                width: 130,
                render: (v: number | null, row: ThresholdRow) =>
                  v === null || v === undefined ? '아직 없음' : `${v} ${row.unit ?? ''}`,
              },
              {
                title: '기본값',
                dataIndex: 'default',
                width: 110,
                render: (v: number | null) =>
                  v === null || v === undefined ? '아직 없음' : String(v),
              },
              {
                title: '누가 정했나',
                dataIndex: 'source',
                width: 140,
                render: (v: string) =>
                  v === 'override' ? <Tag color="blue">사람이 바꾼 값</Tag> : (
                    v === 'default' ? <Tag>정의 기본값</Tag> : <Tag color="orange">정해지지 않음</Tag>
                  ),
              },
            ]}
          />
        </StateBoundary>
      </Card>

      <Card size="small" title="바꾼 기록">
        {history.length === 0 ? (
          <Text type="secondary">아직 바꾼 기록이 없습니다. (요청은 성공했고 0건입니다)</Text>
        ) : (
          <Table<ThresholdHistoryRow>
            size="small"
            rowKey={(r, i) => `${r.key}:${r.changed_at ?? ''}:${i ?? 0}`}
            dataSource={history}
            pagination={false}
            columns={[
              { title: '항목', dataIndex: 'key', width: 220 },
              {
                title: '무엇에서 무엇으로',
                key: 'move',
                render: (_: unknown, r: ThresholdHistoryRow) =>
                  `${r.old ?? '아직 없음'} → ${r.new ?? '아직 없음'}`,
              },
              { title: '사유', dataIndex: 'reason' },
            ]}
          />
        )}
      </Card>
    </Space>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
 * 등급규칙
 * ═══════════════════════════════════════════════════════════════════════════ */
function GradeRulesTab() {
  const [picked, setPicked] = useState<string>('');
  const [severity, setSeverity] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<{ text: string; status: number } | null>(null);

  const view = useDsmResource<GradeRulesView>(
    () => dsmGet<GradeRulesView>(SETTINGS_PATH.gradeRulesRead),
    [],
    { isEmpty: (v) => (v?.grade_rules?.length ?? 0) === 0 },
  );

  const rows = useMemo(() => view.data?.grade_rules ?? [], [view.data]);
  const history = view.data?.history ?? [];
  const loweredCount = view.data?.lowered_count ?? 0;
  const overridden = rows.filter((r) => r.overridden).length;

  const save = useCallback(() => {
    if (!picked || !severity) {
      message.info('유형과 등급을 먼저 고르십시오.');
      return;
    }
    askReason('이 유형의 등급 규칙을 바꿉니다', async (reason) => {
      setSaving(true);
      setSaveError(null);
      try {
        await dsmPostQuery(SETTINGS_PATH.gradeRulesWrite, {
          event_type: picked,
          severity,
          reason,
        });
        message.success('저장했습니다. 아래 표를 다시 읽습니다.');
        // ★ 누른 뒤를 본다 — 다시 읽은 표의 「지금 등급」과 「낮춘 규칙」이 증거다.
        view.reload();
      } catch (err) {
        setSaveError({
          text: userFacingError('SettingsRules.gradeRuleSave', err, '등급 규칙을 저장하지 못했습니다.'),
          status: (err as { status?: number })?.status ?? 0,
        });
        throw err;
      } finally {
        setSaving(false);
      }
    });
  }, [picked, severity, view]);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Card size="small" title="등급 바꾸기 (사유를 적어야 저장됨)">
        <Space wrap>
          <Select
            style={{ width: 240 }}
            placeholder="유형"
            value={picked || undefined}
            onChange={(v: string) => {
              setPicked(v);
              setSeverity(rows.find((r) => r.event_type === v)?.severity ?? '');
            }}
            options={rows.map((r) => ({
              value: r.event_type,
              label: labelOf(EVENT_TYPE_LABEL, r.event_type),
            }))}
          />
          <Select
            style={{ width: 160 }}
            placeholder="등급"
            value={severity || undefined}
            onChange={(v: string) => setSeverity(v)}
            options={SEVERITY_CHOICES.map((s) => ({ value: s, label: SEVERITY_LABEL[s] }))}
          />
          <Button type="primary" loading={saving} disabled={!picked || !severity} onClick={save}>
            저장
          </Button>
        </Space>
      </Card>

      {saveError ? (
        <FailureNotice
          title="등급 규칙을 저장하지 못했습니다."
          detail={saveError.text}
          status={saveError.status}
          onRetry={() => setSaveError(null)}
          retryLabel="닫기"
        />
      ) : null}

      <Card size="small" title="지금 규칙">
        <Paragraph data-gx="grade-rules-now" style={{ marginBottom: 4 }}>
          바꿔 둔 규칙 {overridden}개 · 전체 {rows.length}개 · 낮춘 규칙 {loweredCount}개
        </Paragraph>
        {/*
          ★ 낮춘 규칙을 **이 자리에서 따로 말한다.** 낮춘 유형은 경보가 안 오고,
            경보가 안 오는 것은 화면에서 「아무 일도 없음」과 같은 그림이다.
        */}
        {loweredCount > 0 ? (
          <Paragraph type="warning" style={{ marginBottom: 8 }}>
            낮춘 규칙이 있습니다. 낮춘 유형은 경보가 조용해집니다.
          </Paragraph>
        ) : null}
        <StateBoundary
          state={view.state}
          reason={view.reason}
          status={view.status}
          onRetry={view.reload}
          emptyText="읽을 규칙이 없습니다. (요청은 성공했고 0건입니다)"
          where="SettingsRules.gradeRules"
        >
          <Table<GradeRuleRow>
            size="small"
            rowKey="event_type"
            dataSource={rows}
            pagination={false}
            columns={[
              {
                title: '유형',
                dataIndex: 'event_type',
                render: (v: string) => labelOf(EVENT_TYPE_LABEL, v),
              },
              {
                title: '지금 등급',
                dataIndex: 'severity',
                width: 110,
                render: (v: string) => SEVERITY_LABEL[v] ?? v,
              },
              {
                title: '정의 등급',
                dataIndex: 'default_severity',
                width: 110,
                render: (v: string) => SEVERITY_LABEL[v] ?? v,
              },
              {
                title: '누가 정했나',
                dataIndex: 'overridden',
                width: 140,
                render: (v: boolean) =>
                  v ? <Tag color="blue">사람이 바꾼 값</Tag> : <Tag>정의 기본값</Tag>,
              },
              {
                title: '낮춤',
                dataIndex: 'lowered',
                width: 110,
                render: (v: boolean) => (v ? <Tag color="orange">낮춤</Tag> : null),
              },
              { title: '사유', dataIndex: 'reason' },
            ]}
          />
        </StateBoundary>
      </Card>

      <Card size="small" title="바꾼 기록">
        {history.length === 0 ? (
          <Text type="secondary">아직 바꾼 기록이 없습니다. (요청은 성공했고 0건입니다)</Text>
        ) : (
          <Table<GradeRuleHistoryRow>
            size="small"
            rowKey={(r, i) => `${r.event_type}:${r.changed_at ?? ''}:${i ?? 0}`}
            dataSource={history}
            pagination={false}
            columns={[
              {
                title: '유형',
                dataIndex: 'event_type',
                width: 200,
                render: (v: string) => labelOf(EVENT_TYPE_LABEL, v),
              },
              {
                title: '무엇에서 무엇으로',
                key: 'move',
                render: (_: unknown, r: GradeRuleHistoryRow) =>
                  `${SEVERITY_LABEL[r.old_severity] ?? r.old_severity} → ${
                    SEVERITY_LABEL[r.new_severity] ?? r.new_severity
                  }`,
              },
              { title: '사유', dataIndex: 'reason' },
            ]}
          />
        )}
      </Card>
    </Space>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
export default function SettingsRules() {
  /**
   * ★ 이 문들의 거절은 **이 화면이 적는다** — 위에서 내려오는 띠가 아니라.
   *   띠는 덮개라 상태 칸의 단추를 가린다. 같은 사실을 두 번 말하면서 값 있는 쪽을
   *   덮는 것이다. 숨기는 것이 아니다 — 403 은 아래 상태 칸에 그대로 적힌다.
   */
  useEffect(() => ownDenialPaths(['/api/dsm/settings/']), []);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        설정 — 구역 · 임계값 · 등급규칙
      </Title>
      <Text type="secondary" style={{ fontSize: 12 }}>
        기관 관리자의 자리입니다. 세 가지를 바꾸면 그 자리에서 다시 읽어 지금 값을 보여 줍니다.
      </Text>

      <Tabs
        defaultActiveKey="zones"
        items={[
          { key: 'zones', label: '구역', children: <ZonesTab /> },
          { key: 'thresholds', label: '임계값', children: <ThresholdsTab /> },
          { key: 'grade-rules', label: '등급규칙', children: <GradeRulesTab /> },
        ]}
      />
    </Space>
  );
}
