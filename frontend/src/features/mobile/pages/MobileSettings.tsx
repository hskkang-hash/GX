/**
 * **M4 — 내 알림 설정** (UX-43-M4 · 2026-09-16 · 턴 S · 차선 U3 · **골격**).
 *
 * 이동 중인 사람이 이 화면에서 정하는 넷:
 *   ① 이 기기로 알림을 받을 것인가      웹푸시 구독 (CH-03 · WS-08)
 *   ② 언제는 안 받을 것인가             근무 외 차단 시간대 (SET-01)
 *   ③ 어디를 맡고 있는가                담당 구역
 *   ④ 어느 채널로 받을 것인가           메일 · 문자 · 웹푸시
 *
 * ★★ **이 설정은 좁히기만 한다.** 규칙(`NotificationRule`)이 고른 수신을 줄일 뿐
 *   늘리지 못한다 — 그래서 빈 칸은 「아무것도 안 받는다」가 아니라 **「규칙 그대로
 *   받는다」**이고, 화면은 그 사실을 서버가 준 말(`note`)로 적는다. 이 구별을 화면이
 *   빼먹으면 사람은 빈 칸을 보고 「알림이 꺼져 있다」고 읽는다(D-290).
 *
 * ★★ **「미수신 신고」를 그리지 않았다** [실측 2026-09-16].
 *   UX-43-M4 는 넷째로 「알림을 못 받았다고 신고」를 적고 있고, 선등록표에도 자리가
 *   있다(WS-07 `me/notify-report`). 그런데 **그 문이 저장소에 없다** — 이번 턴에
 *   짓지 않았다(사유는 보고에 적었다). 문 없이 단추만 그리면 눌러도 아무 일이
 *   없거나, 더 나쁘게는 **신고가 접수됐다고 사람이 믿는다.**
 *   그래서 안 그렸다 — 「없는 것에 손잡이를 그리지 않는다」(`MobileEventDetail.tsx`
 *   가 전화 버튼에서 이미 지킨 규약).
 *
 * ★ 왜 별 화면인가: M3 는 「이 사건 앞에서 지금 하는 일」이라 한 화면의 한 순서지만,
 *   알림 설정은 사건과 무관하고 **한 번 정하면 오래 가는 값**이다(`routes.ts` 주석).
 */
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Descriptions,
  Input,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useState } from 'react';

import StateBoundary from '../../dsm/components/StateBoundary';
import { useDsmResource } from '../../dsm/hooks/useDsmResource';
import { userFacingError } from '@/features/dsm/copy';
import { dsmGet, dsmPut, mobileEndpoint } from '../api';
import MobileShell, { TOUCH_MIN } from '../components/MobileShell';
import {
  currentDeviceFingerprint,
  disableFieldPush,
  enableFieldPush,
  listFieldPushDevices,
  pushSupport,
  sendTestPush,
  type PushDevicePage,
  type TestSendResult,
} from '../push';
import { mobileRoutes } from '../routes';

const { Text, Paragraph } = Typography;

/**
 * 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다.
 * ⚠ 이 상수를 고치면 `scripts/capture_screens.py` 의 사본도 **같은 커밋에서** 고친다.
 */
export const SETTINGS_HEADLINE = '내 알림 설정';

/** 채널 이름표. 서버가 정한 이름(`allowed_channels`)에 사람의 말을 입힌다. */
const CHANNEL_LABEL: Record<string, string> = {
  email: '메일',
  sms: '문자',
  webpush: '이 기기 알림(웹푸시)',
};

interface NotifyPrefsView {
  quiet_start: string;
  quiet_end: string;
  zone_ids: number[];
  channels: string[];
  saved: boolean;
  allowed_channels: string[];
  note: string;
}

export default function MobileSettings() {
  const prefs = useDsmResource<NotifyPrefsView>(
    () => dsmGet<NotifyPrefsView>(mobileEndpoint.notifyPrefs),
    [],
  );
  const devices = useDsmResource<PushDevicePage>(
    () => listFieldPushDevices(),
    [],
    { isEmpty: (v) => (v?.subscriptions?.length ?? 0) === 0 },
  );

  const [quietStart, setQuietStart] = useState('');
  const [quietEnd, setQuietEnd] = useState('');
  const [zones, setZones] = useState('');
  const [channels, setChannels] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const [thisDevice, setThisDevice] = useState('');
  const [pushBusy, setPushBusy] = useState('');
  const [testResult, setTestResult] = useState<TestSendResult | null>(null);

  /** 서버 값이 오면 입력칸의 **출발점**으로 삼는다 — 화면이 값을 지어내지 않는다. */
  useEffect(() => {
    const view = prefs.data;
    if (!view) return;
    setQuietStart(view.quiet_start);
    setQuietEnd(view.quiet_end);
    setZones((view.zone_ids ?? []).join(','));
    setChannels(view.channels ?? []);
  }, [prefs.data]);

  useEffect(() => {
    void currentDeviceFingerprint().then(setThisDevice);
  }, []);

  const support = pushSupport();
  const rows = devices.data?.subscriptions ?? [];
  /** 지문이 맞는 줄이 있으면 **이 기기가 켜진 것**이다. 지문을 못 구하면 가리지 않는다. */
  const thisDeviceRow = thisDevice
    ? rows.find((r) => r.endpoint_sha12 === thisDevice)
    : undefined;

  const save = useCallback(async () => {
    setSaving(true);
    try {
      await dsmPut<NotifyPrefsView>(mobileEndpoint.notifyPrefs, {
        quiet_start: quietStart.trim(),
        quiet_end: quietEnd.trim(),
        zone_ids: zones.trim(),
        channels: channels.join(','),
      });
      message.success('알림 설정을 저장했습니다.');
      prefs.reload();
    } catch (err) {
      message.error(
        userFacingError('MobileSettings.save', err, '설정을 저장하지 못했습니다.'),
      );
    } finally {
      setSaving(false);
    }
  }, [quietStart, quietEnd, zones, channels, prefs]);

  const turnOn = useCallback(async () => {
    setPushBusy('on');
    try {
      const label = `${navigator.platform || '휴대전화'} · ${new Date().toLocaleDateString('ko-KR')}`;
      await enableFieldPush(label);
      message.success('이 기기로 알림을 받습니다.');
      setThisDevice(await currentDeviceFingerprint());
      devices.reload();
    } catch (err) {
      // ★ 사유를 **그대로** 보여 준다 — 기기 설정을 고쳐야 하는지 서버를 기다려야
      //   하는지는 사람이 알아야 하고, 그 둘은 할 일이 다르다(D-290).
      message.error(err instanceof Error ? err.message : '알림을 켜지 못했습니다.');
    } finally {
      setPushBusy('');
    }
  }, [devices]);

  const turnOff = useCallback(
    async (subscriptionId: number) => {
      setPushBusy(`off:${subscriptionId}`);
      try {
        await disableFieldPush(subscriptionId);
        message.success('이 기기 알림을 껐습니다.');
        devices.reload();
      } catch (err) {
        message.error(
          userFacingError('MobileSettings.pushOff', err, '알림을 끄지 못했습니다.'),
        );
      } finally {
        setPushBusy('');
      }
    },
    [devices],
  );

  const test = useCallback(async () => {
    setPushBusy('test');
    try {
      const result = await sendTestPush();
      setTestResult(result);
      // ★ 「보냈다」고만 말하지 않는다 — **모수와 함께** 적는다(D-301).
      message.info(`기기 ${result.devices}대 중 ${result.sent}대로 보냈습니다.`);
    } catch (err) {
      message.error(
        userFacingError('MobileSettings.testSend', err, '시험 알림을 보내지 못했습니다.'),
      );
    } finally {
      setPushBusy('');
    }
  }, []);

  return (
    <MobileShell
      title={SETTINGS_HEADLINE}
      loadedAt={prefs.loadedAt}
      onReload={() => {
        prefs.reload();
        devices.reload();
      }}
      backTo={mobileRoutes.inbox.path}
    >
      <Space direction="vertical" size={10} style={{ width: '100%' }}>
        {/* ① 이 기기 알림 — 상태 칸이 먼저, 단추가 그 다음 */}
        <Card size="small" title="이 기기 알림" styles={{ body: { padding: 12 } }}>
          <Space direction="vertical" size={8} style={{ width: '100%' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="이 기기">
                {!support.ok ? (
                  <Text type="secondary">켤 수 없음</Text>
                ) : !thisDevice ? (
                  // ★ 「꺼짐」이라고 적지 않는다 — 가리지 못한 것과 꺼진 것은 다른 사실이다.
                  <Text type="secondary">가릴 수 없음 (구독 없음 또는 지문 미확인)</Text>
                ) : thisDeviceRow ? (
                  <Tag color="green">켜짐</Tag>
                ) : (
                  <Tag>꺼짐</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="등록된 기기">
                {/* ★ 0 을 「없음」으로 적지 않는다 — 수로 적는다. */}
                {devices.data?.total ?? 0}대
              </Descriptions.Item>
            </Descriptions>

            {!support.ok ? (
              <Alert type="info" showIcon message={support.reason} />
            ) : (
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                {thisDeviceRow ? (
                  <Button
                    block
                    style={{ minHeight: TOUCH_MIN }}
                    loading={pushBusy === `off:${thisDeviceRow.subscription_id}`}
                    onClick={() => turnOff(thisDeviceRow.subscription_id)}
                  >
                    이 기기 알림 끄기
                  </Button>
                ) : (
                  <Button
                    block
                    type="primary"
                    style={{ minHeight: TOUCH_MIN }}
                    loading={pushBusy === 'on'}
                    onClick={turnOn}
                  >
                    알림 받기
                  </Button>
                )}
                <Button
                  block
                  style={{ minHeight: TOUCH_MIN }}
                  loading={pushBusy === 'test'}
                  disabled={(devices.data?.total ?? 0) === 0}
                  onClick={test}
                >
                  시험 알림 보내기 (훈련)
                </Button>
              </Space>
            )}

            {testResult ? (
              <Alert
                type={testResult.sent > 0 ? 'success' : 'warning'}
                showIcon
                message={`기기 ${testResult.devices}대 중 ${testResult.sent}대로 보냈습니다.`}
                description={
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    {testResult.results.map((r) => (
                      <Text key={r.endpoint_sha12} style={{ fontSize: 12 }}>
                        {r.label} — {r.sent ? '보냄' : `못 보냄: ${r.reason}`}
                      </Text>
                    ))}
                  </Space>
                }
              />
            ) : null}

            <StateBoundary
              state={devices.state}
              reason={devices.reason}
              status={devices.status}
              onRetry={devices.reload}
              emptyText="이 계정에 등록된 기기가 없습니다."
            >
              <Space direction="vertical" size={4} style={{ width: '100%' }}>
                {rows.map((r) => (
                  <Space key={r.subscription_id} size={6} wrap>
                    <Text style={{ fontSize: 12 }}>{r.label || '이름 없는 기기'}</Text>
                    {r.endpoint_sha12 === thisDevice ? <Tag color="blue">이 기기</Tag> : null}
                    <Button
                      size="small"
                      loading={pushBusy === `off:${r.subscription_id}`}
                      onClick={() => turnOff(r.subscription_id)}
                    >
                      끄기
                    </Button>
                  </Space>
                ))}
              </Space>
            </StateBoundary>
          </Space>
        </Card>

        {/* ②③④ 근무 외 · 구역 · 채널 */}
        <StateBoundary
          state={prefs.state}
          reason={prefs.reason}
          status={prefs.status}
          onRetry={prefs.reload}
          emptyText="설정을 불러오지 못했습니다."
        >
          <Space direction="vertical" size={10} style={{ width: '100%' }}>
            <Card size="small" title="언제는 안 받나" styles={{ body: { padding: 12 } }}>
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Space size={6} wrap>
                  <Input
                    style={{ width: 96 }}
                    placeholder="22:00"
                    value={quietStart}
                    onChange={(ev) => setQuietStart(ev.target.value)}
                  />
                  <Text>부터</Text>
                  <Input
                    style={{ width: 96 }}
                    placeholder="07:00"
                    value={quietEnd}
                    onChange={(ev) => setQuietEnd(ev.target.value)}
                  />
                  <Text>까지</Text>
                </Space>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  둘 다 비우면 차단 없음입니다. 한쪽만 채울 수는 없습니다 — 언제부터
                  언제까지 안 받는지 정해지지 않기 때문입니다.
                </Text>
              </Space>
            </Card>

            <Card size="small" title="어디를 맡고 있나" styles={{ body: { padding: 12 } }}>
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Input
                  placeholder="구역 번호를 쉼표로 (예: 3,4)"
                  value={zones}
                  onChange={(ev) => setZones(ev.target.value)}
                />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  비우면 전 구역입니다. (구역을 이름으로 고르는 칸은 다음 파에서 옵니다 —
                  지금은 번호로 받습니다.)
                </Text>
              </Space>
            </Card>

            <Card size="small" title="어느 채널로 받나" styles={{ body: { padding: 12 } }}>
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Checkbox.Group
                  value={channels}
                  onChange={(v) => setChannels(v as string[])}
                >
                  <Space direction="vertical" size={4}>
                    {(prefs.data?.allowed_channels ?? []).map((name) => (
                      <Checkbox key={name} value={name} style={{ minHeight: 32 }}>
                        {CHANNEL_LABEL[name] ?? name}
                      </Checkbox>
                    ))}
                  </Space>
                </Checkbox.Group>
                {/* ★ 서버가 준 말을 그대로 적는다 — 판정식도 문구도 두 벌로 두지 않는다. */}
                <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
                  {prefs.data?.note}
                </Paragraph>
              </Space>
            </Card>

            <Space direction="vertical" size={6} style={{ width: '100%' }}>
              <Button
                block
                type="primary"
                style={{ minHeight: TOUCH_MIN }}
                loading={saving}
                onClick={save}
              >
                설정 저장
              </Button>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {prefs.data?.saved
                  ? '저장된 설정이 있습니다.'
                  : '아직 정하지 않았습니다 — 규칙이 정한 대로 받습니다.'}
              </Text>
            </Space>
          </Space>
        </StateBoundary>
      </Space>
    </MobileShell>
  );
}
