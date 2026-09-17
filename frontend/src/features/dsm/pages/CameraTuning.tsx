/**
 * 화면 — **카메라 오탐률 · 임계값** (S-10 · 부속서A 업무플로우 U2 #10·#11 · 턴 S).
 *
 * 이 화면이 닫는 것 셋 (정본 완결 조건 그대로)
 * --------------------------------------------
 *   #10  카메라별 오탐률 **내림차순 · 상위 3 강조**
 *   #11  슬라이더 → **「시간당 N건」 시뮬** → **저장(사유 필수)** → **재조회**
 *   그리고 시뮬이 시간당 6건을 넘으면 주황으로 말한다.
 *
 * ★★ **저장하는 문을 새로 만들지 않았다.** 임계값을 바꾸는 문은 이미 하나 있고
 *   (설정의 임계값 쓰기), 그 문이 사유를 강제한다 — 사유가 비면 서버가 400 으로
 *   거절한다. 화면이 사유를 먼저 묻는 이유는 그 거절을 사람이 안 만나게 하려는
 *   것이지, 화면이 그 규칙을 대신 판정하는 것이 아니다.
 *
 * ★★ **시뮬은 아무것도 바꾸지 않는다.** 슬라이더를 움직이는 동안 저장되는 것은
 *   없다. 「누르면 바뀌는 것」과 「끌면 보이는 것」을 가르지 않으면, 사람은 자기가
 *   이미 바꿨다고 믿은 채로 화면을 떠난다.
 *
 * ★ **두 축을 한 슬라이더에 묶지 않는다** — 이 화면에서 가장 조심한 자리다.
 *   시뮬의 축은 **확신도**(0에서 1)이고, 저장하는 임계값은 **그 항목의 단위**를
 *   갖는다(초·분·센티미터 …). 둘이 늘 같은 축일 것이라고 가정하면, 언젠가 확신도
 *   값이 센티미터 칸에 들어간다. 그래서 시뮬 값은 사람이 **직접 옮겨 담을 때만**
 *   저장 칸으로 간다.
 *
 * ★ 고칠 수 있는 임계값의 **이름표를 서버가 준다.** 화면이 키를 손으로 들면
 *   표가 늘거나 줄 때 화면만 옛말이 되고, 옛말이 된 것은 안 보인다.
 *   계약이 못박은 값은 그 목록에 아예 없다 — 옮길 수 있는 것처럼 그려 놓고
 *   저장에서 거절하는 것이 거짓말이기 때문이다.
 *
 * ★ 못 재는 것은 **못 잰다고 적는다.** 판정이 한 건도 없는 카메라의 오탐률은
 *   0%가 아니라 「아직 잴 수 없음」이고, 확신도가 비어 있는 사건만 있는 카메라의
 *   시뮬은 시간당 0건이 아니라 「잴 수 없음」이다. 0으로 적으면 판정을 미루기만
 *   해도 지표가 좋아지고, 문턱을 올리면 알림이 사라진 것처럼 보인다.
 *
 * ★ 턴 T (P-164 U24 ④·⑤ · D-479) — **두 축의 이름을 화면 문구로 가른다.**
 *   슬라이더 위에는 「시뮬 축 — 확신도」, 저장 칸 위에는 「저장 축 — 항목 단위」라고
 *   **다른 말로** 적는다. 같은 말(「문턱」)로 뭉개면 사람은 슬라이더 값이 저장되는 줄
 *   안다 — 저장되지 않는다(D-479: 탐지는 여전히 0.0 을 읽는다). 「갈라 둔 것이 옳다」.
 *   그리고 화면이 **둘로 열린다**: `mode="false-positive"`(정본 `/dsm/stats/false-positive` ·
 *   통계 축 — 오탐률 표만) · `mode="tuning"`(`/dsm/cameras/tuning` · 카메라 축 — 표는
 *   고르는 자리이고 시뮬·저장이 본문). 파일은 하나다 — 두 벌을 두지 않는다.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Modal,
  Row,
  Segmented,
  Select,
  Slider,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  dsmPostQuery,
  dsmPostQueryOnce,
  dsmU24Endpoint,
  dsmGet,
  intentKey,
} from '../api';
import { userFacingError } from '../copy';
import { dsmU24Routes } from '../routes.u24';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { absolute } from '../time';
import type {
  CameraFalsePositiveResponse,
  CameraFalsePositiveRow,
  CameraThresholdKey,
  CameraThresholdValue,
  ThresholdSimulation,
} from '../types';

const { Text, Title } = Typography;

const DAY_OPTIONS = [7, 30] as const;

/** 비율 한 줄. **비율만 적지 않는다** — 분자와 분모를 같은 줄에 적는다. */
function rateLine(row: CameraFalsePositiveRow): string {
  if (!row.measurable || row.false_positive_rate === null) {
    return '아직 잴 수 없음 (판정 0건)';
  }
  return `${Math.round(row.false_positive_rate * 100)}% (${row.false_positive}/${row.reviewed})`;
}

export type CameraTuningMode = 'false-positive' | 'tuning';

/** 화면 문구 — 두 축의 이름. GX-COPY 정본에 없어 **사전 등재 요청**(보고에 한 줄). */
const AXIS_COPY = {
  simulate: '시뮬 축 — 확신도 (0~1 · 모델이 낸 값 · 저장되지 않음)',
  save: '저장 축 — 항목 단위 (서버가 정한 단위 · 사유를 적어야 저장됨)',
} as const;

export default function CameraTuning({ mode = 'tuning' }: { mode?: CameraTuningMode } = {}) {
  const navigate = useNavigate();
  const isFpOnly = mode === 'false-positive';
  const [days, setDays] = useState<number>(7);
  const [cameraId, setCameraId] = useState<number | null>(null);
  const [thresholdKey, setThresholdKey] = useState<string | undefined>();

  /** 시뮬의 축 — 확신도. **저장 값과 다른 칸이다.** */
  const [confidence, setConfidence] = useState<number>(0.5);
  const [sim, setSim] = useState<ThresholdSimulation | null>(null);
  const [simBusy, setSimBusy] = useState(false);

  /** 저장의 축 — 그 항목의 단위. 시뮬 값이 자동으로 들어오지 않는다. */
  const [saveValue, setSaveValue] = useState<string>('');
  const [saving, setSaving] = useState(false);

  const cameras = useDsmResource<CameraFalsePositiveResponse>(
    () => dsmGet<CameraFalsePositiveResponse>(dsmU24Endpoint.falsePositiveByCamera, {
      days,
      top_n: 3,
    }),
    [days],
    { isEmpty: (v) => (v?.cameras?.length ?? 0) === 0 },
  );

  const keys = useDsmResource<{ keys: CameraThresholdKey[]; total: number }>(
    () => dsmGet(dsmU24Endpoint.cameraThresholdKeys),
    [],
    { isEmpty: (v) => (v?.keys?.length ?? 0) === 0 },
  );

  /**
   * 「저장 → 재조회」의 **재조회**. 저장 뒤 이것을 다시 불러 값이 실제로 바뀌었는지
   * 사람이 눈으로 본다 — 저장 응답만 믿으면 「썼다고 말한 것」과 「쓰인 것」을
   * 구별하지 못한다.
   */
  const current = useDsmResource<CameraThresholdValue>(
    () => dsmGet<CameraThresholdValue>(dsmU24Endpoint.cameraThreshold, {
      camera_id: cameraId!,
      key: thresholdKey!,
    }),
    [cameraId, thresholdKey],
    { enabled: Boolean(cameraId) && Boolean(thresholdKey) },
  );

  const rows = useMemo(() => cameras.data?.cameras ?? [], [cameras.data]);
  const selectedKey = useMemo(
    () => (keys.data?.keys ?? []).find((k) => k.key === thresholdKey),
    [keys.data, thresholdKey],
  );

  /** 슬라이더가 부르는 자리. **아무것도 바꾸지 않는다.** */
  const runSimulation = useCallback(
    async (value: number) => {
      if (!cameraId) {
        message.info('먼저 위 표에서 카메라를 고르십시오.');
        return;
      }
      setSimBusy(true);
      try {
        const res = await dsmPostQuery<ThresholdSimulation>(
          dsmU24Endpoint.thresholdSimulate,
          { camera_id: cameraId, confidence_min: value, days },
        );
        setSim(res);
      } catch (err) {
        setSim(null);
        message.error(
          userFacingError('CameraTuning.simulate', err, '시험 계산을 하지 못했습니다.'),
        );
      } finally {
        setSimBusy(false);
      }
    },
    [cameraId, days],
  );

  /**
   * 저장 — **사유가 필수다.** 서버도 사유가 비면 거절하지만, 화면이 먼저 묻는다.
   * 무엇에서 무엇으로 바뀌었는지는 기록이 알고, **왜** 는 여기서만 들어온다.
   */
  const save = useCallback(() => {
    if (!cameraId || !thresholdKey) {
      message.info('카메라와 항목을 먼저 고르십시오.');
      return;
    }
    const numeric = Number(saveValue);
    if (saveValue.trim() === '' || Number.isNaN(numeric)) {
      message.info('저장할 값을 숫자로 적어 주십시오.');
      return;
    }
    let reason = '';
    Modal.confirm({
      title: '이 카메라의 임계값을 바꿉니다',
      content: (
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">
            사유는 반드시 적어야 합니다. 무엇에서 무엇으로 바꿨는지는 기록이
            알지만, 왜 바꿨는지는 여기서만 남습니다. 사유가 비면 저장되지 않습니다.
          </Text>
          <Input.TextArea
            rows={2}
            placeholder="바꾸는 사유 (필수)"
            onChange={(ev) => {
              reason = ev.target.value;
            }}
          />
        </Space>
      ),
      okText: '저장',
      cancelText: '취소',
      onOk: async () => {
        if (!reason.trim()) {
          message.error('사유가 비어 있습니다. 사유 없이는 저장할 수 없습니다.');
          throw new Error('reason required');
        }
        setSaving(true);
        try {
          await dsmPostQueryOnce(
            dsmU24Endpoint.settingsThresholds,
            {
              key: thresholdKey,
              value: numeric,
              reason,
              scope_level: 'camera',
              scope_ref: cameraId,
            },
            intentKey(`threshold:${cameraId}:${thresholdKey}`),
          );
          message.success('저장했습니다. 아래 「지금 값」을 다시 읽습니다.');
          // ★ 누른 뒤를 본다 — 저장 응답이 아니라 **다시 읽은 값**이 증거다.
          current.reload();
        } catch (err) {
          message.error(
            userFacingError('CameraTuning.save', err, '저장하지 못했습니다.'),
          );
          throw err; // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
        } finally {
          setSaving(false);
        }
      },
    });
  }, [cameraId, thresholdKey, saveValue, current]);

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        {isFpOnly ? '카메라 오탐률' : '카메라 임계값 튜닝'}
      </Title>
      <Text type="secondary" style={{ fontSize: 12 }}>
        {isFpOnly
          ? '통계 축의 화면입니다 — 오탐률 표만 있습니다. 문턱을 옮기거나 저장하려면 카메라 축의 「임계값 튜닝」으로 갑니다.'
          : '카메라 축의 화면입니다 — 위 표에서 카메라를 고르고 아래에서 문턱을 옮겨 보고(시뮬 축) 저장합니다(저장 축). 두 축은 다른 칸입니다.'}
      </Text>

      {/* ── 어느 카메라가 시끄러운가 ─────────────────────────────────────── */}
      <Card
        size="small"
        title="어느 카메라가 시끄러운가"
        extra={
          <Space>
            <Segmented
              value={days}
              onChange={(v) => setDays(Number(v))}
              options={DAY_OPTIONS.map((d) => ({ value: d, label: `${d}일` }))}
            />
            <Button onClick={cameras.reload}>새로고침</Button>
            {isFpOnly ? (
              <Button onClick={() => navigate(dsmU24Routes.cameraTuning.path)}>
                임계값 튜닝으로
              </Button>
            ) : (
              <Button onClick={() => navigate(dsmU24Routes.falsePositive.path)}>
                오탐률 통계로
              </Button>
            )}
          </Space>
        }
      >
        <StateBoundary
          state={cameras.state}
          reason={cameras.reason}
          status={cameras.status}
          onRetry={cameras.reload}
          where="CameraTuning/카메라"
          emptyText="이 기간에 사건을 낸 카메라가 없습니다. (요청은 성공했고 0대입니다)"
        >
          {cameras.data && (
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text type="secondary">
                {absolute(cameras.data.since)} ~ {absolute(cameras.data.until)} · 카메라{' '}
                {cameras.data.camera_total}대
                {cameras.data.camera_capped
                  ? ` (한 번에 ${cameras.data.camera_cap}대까지 봅니다)`
                  : ''}
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                오탐률이 높은 차례로 놓았습니다. 판정이 한 건도 없는 카메라는 맨
                아래에 있습니다 — 오탐이 없는 것이 아니라 아직 잴 수 없는 것입니다.
              </Text>
              <Table<CameraFalsePositiveRow>
                size="small"
                rowKey="stream_monitor_id"
                dataSource={rows}
                pagination={false}
                rowClassName={(r) =>
                  r.stream_monitor_id === cameraId ? 'ant-table-row-selected' : ''
                }
                onRow={(r) => ({
                  onClick: () => {
                    setCameraId(r.stream_monitor_id);
                    setSim(null);
                  },
                  style: { cursor: 'pointer' },
                })}
                columns={[
                  {
                    title: '카메라',
                    dataIndex: 'stream_monitor_name',
                    ellipsis: true,
                    render: (v: string, r) => (
                      <Space size={4}>
                        {/* ★ 상위 표시는 서버가 매긴 것을 그대로 그린다 — 화면이
                            다시 세면 두 곳이 갈린다. 빨강을 쓰지 않는다(빨강은
                            심각 등급 전용이다). */}
                        {r.top && <Tag color="orange">상위</Tag>}
                        <span>{v || `카메라 ${r.stream_monitor_id}`}</span>
                      </Space>
                    ),
                  },
                  {
                    title: '오탐률',
                    dataIndex: 'false_positive_rate',
                    width: 200,
                    render: (_v, r) => rateLine(r),
                  },
                  { title: '판정', dataIndex: 'reviewed', width: 90 },
                  { title: '미판정', dataIndex: 'unreviewed', width: 90 },
                ]}
              />
            </Space>
          )}
        </StateBoundary>
      </Card>

      {/* ── 문턱을 옮겨 보기 (시뮬) — 카메라 축(튜닝)에서만 ─────────────────── */}
      {!isFpOnly && (
      <Card size="small" title="문턱을 옮겨 보기 (시뮬 축)">
        {!cameraId ? (
          <Text type="secondary">
            위 표에서 카메라를 한 대 고르면 여기에서 문턱을 옮겨 볼 수 있습니다.
          </Text>
        ) : (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Alert
              type="info"
              showIcon
              message="여기서 끄는 동안 바뀌는 것은 없습니다."
              description="아래 슬라이더는 계산만 합니다. 실제로 바꾸려면 맨 아래에서 사유를 적고 저장해야 합니다."
            />
            <Row gutter={16} align="middle">
              <Col xs={24} md={14}>
                <Text type="secondary">{AXIS_COPY.simulate}</Text>
                <Slider
                  min={0}
                  max={1}
                  step={0.01}
                  value={confidence}
                  onChange={(v) => setConfidence(Number(v))}
                  onChangeComplete={(v) => runSimulation(Number(v))}
                  tooltip={{ formatter: (v) => `${Math.round((v ?? 0) * 100)}%` }}
                />
              </Col>
              <Col xs={24} md={10}>
                <Space wrap>
                  <Text strong>{Math.round(confidence * 100)}%</Text>
                  <Button loading={simBusy} onClick={() => runSimulation(confidence)}>
                    이 문턱으로 계산
                  </Button>
                </Space>
              </Col>
            </Row>

            {sim && (
              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                {sim.measurable ? (
                  <Alert
                    type={sim.noisy ? 'warning' : 'success'}
                    showIcon
                    message={
                      `최근 ${sim.days}일 기준 시간당 ${(sim.events_per_hour ?? 0).toFixed(1)}건`
                      + (sim.noisy
                        ? ` — 시간당 ${sim.noisy_per_hour}건을 넘습니다`
                        : '')
                    }
                    description={
                      `지금은 시간당 ${(sim.current_per_hour ?? 0).toFixed(1)}건입니다. `
                      + `이 문턱이면 ${sim.graded_total}건 가운데 ${sim.kept}건이 남고 `
                      + `${sim.dropped}건이 빠집니다.`
                    }
                  />
                ) : (
                  <Alert
                    type="info"
                    showIcon
                    message="이 문턱으로는 잴 수 없습니다."
                    description={
                      '이 카메라의 사건에 확신도가 적혀 있지 않습니다. '
                      + '확신도가 없는 사건은 문턱으로 가를 수 없어, 시간당 몇 건이 '
                      + '남는지 말할 수 없습니다. 0건이라는 뜻이 아닙니다.'
                    }
                  />
                )}
                <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 4 }} bordered>
                  <Descriptions.Item label="사건">
                    {sim.events_total}건
                  </Descriptions.Item>
                  <Descriptions.Item label="확신도가 적힌 사건">
                    {sim.graded_total}건
                  </Descriptions.Item>
                  <Descriptions.Item label="확신도가 없는 사건">
                    {sim.unknown_confidence}건
                  </Descriptions.Item>
                  <Descriptions.Item label="본 기간">
                    {Math.round(sim.window_hours)}시간
                  </Descriptions.Item>
                </Descriptions>
                {sim.sample_capped && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    한 번에 보는 사건 수에 상한이 있어, 이 기간의 오래된 사건 일부는
                    위 계산에 들어가지 않았습니다.
                  </Text>
                )}
              </Space>
            )}
          </Space>
        )}
      </Card>
      )}

      {/* ── 저장 · 재조회 — 카메라 축(튜닝)에서만 ──────────────────────────── */}
      {!isFpOnly && (
      <Card size="small" title="임계값 저장 (저장 축)">
        <StateBoundary
          state={keys.state}
          reason={keys.reason}
          status={keys.status}
          onRetry={keys.reload}
          where="CameraTuning/항목"
          emptyText="카메라마다 따로 정할 수 있는 임계값 항목이 아직 없습니다."
        >
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Text type="secondary">{AXIS_COPY.save}</Text>
            <Text type="secondary">
              고칠 항목은 서버가 알려 준 것만 고를 수 있습니다. 바꿀 수 없도록 정해진
              값은 이 목록에 없습니다. 위 슬라이더(시뮬 축)의 값은 여기로 저절로 오지
              않습니다 — 「슬라이더 값 넣기」를 눌러 옮겨 담을 때만 옵니다.
            </Text>
            <Space wrap align="center">
              <Select
                allowClear
                style={{ width: 320 }}
                placeholder="고칠 항목"
                value={thresholdKey}
                onChange={(v) => setThresholdKey(v)}
                options={(keys.data?.keys ?? []).map((k) => ({
                  value: k.key,
                  label: `${k.title} (${k.unit})`,
                }))}
              />
              <Input
                style={{ width: 200 }}
                placeholder={selectedKey ? `값 (${selectedKey.unit})` : '값'}
                value={saveValue}
                onChange={(e) => setSaveValue(e.target.value)}
              />
              <Button
                onClick={() => setSaveValue(String(confidence))}
                disabled={!selectedKey}
              >
                슬라이더 값 넣기
              </Button>
              <Button type="primary" loading={saving} onClick={save}>
                사유를 적고 저장
              </Button>
            </Space>

            {selectedKey && (
              <Text type="secondary" style={{ fontSize: 12 }}>
                이 항목의 단위는 「{selectedKey.unit}」입니다. 위 슬라이더는 확신도를
                끄는 칸이라 단위가 다를 수 있습니다 — 옮겨 담기 전에 확인해 주십시오.
              </Text>
            )}

            {cameraId && thresholdKey && (
              <Card size="small" type="inner" title="지금 값 (저장한 뒤 다시 읽은 값)">
                <StateBoundary
                  state={current.state}
                  reason={current.reason}
                  status={current.status}
                  onRetry={current.reload}
                  where="CameraTuning/지금값"
                >
                  {current.data && (
                    <Space wrap>
                      <Text strong>
                        {current.data.set
                          ? `${current.data.value}`
                          : '아직 정해진 값이 없습니다'}
                      </Text>
                      {selectedKey && current.data.set && (
                        <Text type="secondary">{selectedKey.unit}</Text>
                      )}
                      <Button size="small" onClick={current.reload}>
                        다시 읽기
                      </Button>
                    </Space>
                  )}
                </StateBoundary>
              </Card>
            )}
          </Space>
        </StateBoundary>
      </Card>
      )}
    </Space>
  );
}
