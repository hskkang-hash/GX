/**
 * UX-17 **훈련 모드** — 켜면 이 테넌트의 알림이 사람에게 가지 않는다.
 *
 * ★ 이 화면은 **끄는 스위치**를 그린다. 그래서 다른 어떤 설정 화면보다 크게 경고한다:
 *   켜져 있는 동안 **진짜 경보도 로그로 간다.** 켠 줄 모르고 밤을 넘기면 그날 밤의
 *   미발송은 장애와 구별되지 않는다 — 그래서 상태 카드에 「언제부터 · 누가 · 왜」를
 *   반드시 함께 그린다.
 *
 * ★ 첫 증거는 「스위치를 켠 뒤 **실채널 발송 0**」이다. 그 수는 이 화면의 보고서 칸에
 *   **분모와 함께** 나온다 — 창 안 발송 전건이 몇이고 그중 실채널이 몇인지.
 *   분모 없는 0 은 「발송 자체가 없었다」와 구별되지 않고, 그러면 스위치가 안 걸린 채
 *   아무 일도 없던 밤이 「훈련 성공」이 된다 (D-301).
 *
 * ⚠ **아직 채널이 안 바뀐다** [실측 2026-09-24]. 스위치·상태 판정·보고서는 서 있고,
 *   실제 채널 우회는 `kernels/k2_notify/` 안에서 일어나야 한다(발송 경로는 하나다).
 *   그 파일은 조율자의 것이고 이 차선은 만지지 않았다. 그 사실을 **화면이 말한다** —
 *   말하지 않으면 이 화면은 「켜면 안 나간다」고 거짓말을 하게 된다 (D-284).
 */
import { Alert, Button, Card, Col, Descriptions, Input, Row, Space, Statistic, Switch, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmPostQuery } from '../api';
import { dataSourceBadge, userFacingError } from '../copy';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { absolute, stamp } from '../time';
import type { DrillReport, DrillState } from '../types';

const { Text, Title, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '훈련 모드 — 켜면 알림이 사람에게 가지 않습니다';

/**
 * ★ 아직 배선되지 않은 것을 **화면이 말한다.** 이 문장을 지우려면 K2 배선이
 *   먼저 들어와야 하고, 그것은 조율자의 커밋이다.
 */
/**
 * ★ 2026-09-24 — **배선이 왔다.** 직전까지 이 자리에는 「아직 채널을 바꾸지 않습니다」가
 *   있었고, 그것은 그때의 사실이었다. 조율자가 K2 발송 경로에 한 자리를 이었고
 *   (`kernels/k2_notify/services._send_one`), `DrillIsWiredToChannelsTest` 가 그것을 잰다.
 *   ⚠ 문구를 안 고치면 화면이 **없는 결함을 있다고 말한다** — 그 거짓말은 조용하고,
 *     관제요원은 스위치를 믿지 않게 된다.
 */
/**
 * ★ [UX-20 · 2026-09-26] 이 문단에 마크다운 별표(`**`)와 채널 이름(`log`)이 백틱째로
 *   들어 있었다 — 둘 다 렌더되지 않고 **그대로 화면에 보인다**(GX-COPY §4).
 *   무엇이 어디로 나가는가는 사실이지만 당직자의 말이 아니다. 당직자에게 뜻이 있는
 *   것은 셋뿐이다: 문자가 안 간다 · 아래 수가 0이 아니면 훈련 밖이다 · 끄는 것을
 *   잊으면 진짜 경보도 안 간다.
 *   (내부 사실 · 화면에 적지 않는다: 훈련 중 발송은 로그 어댑터로만 나가고,
 *    채널 이름은 가장하지 않고 `log` 로 그대로 남는다.)
 */
const WIRED_NOTE =
  '켜져 있는 동안 이 기관의 알림은 실제로 나가지 않습니다 — 소방·팀장에게 문자가 ' +
  '가지 않습니다. 아래 「실채널 발송」 수가 0이 아니면 그것은 훈련 밖에서 난 ' +
  '발송입니다. 끄는 것을 잊으면 진짜 경보도 사람에게 가지 않습니다.';

export default function DrillModePage() {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  /** 마지막으로 시도한 전환. 「다시 시도」가 **그 요청을** 다시 내기 위한 값이다. */
  const [lastIntent, setLastIntent] = useState<boolean | null>(null);

  const state = useDsmResource<DrillState>(() => dsmGet(dsmEndpoint.drill), [], {
    refreshMs: 30_000,
  });
  const report = useDsmResource<DrillReport>(
    () => dsmGet(dsmEndpoint.drillReport),
    [],
    { refreshMs: 30_000 },
  );

  const toggle = useCallback(
    async (next: boolean) => {
      setBusy(true);
      setError('');
      // ★ [UX-31′ · 턴 S] **무엇을 다시 할지 기억한다.** 실패 상자의 「다시 시도」가
      //   누를 것이 되려면 화면이 「방금 무슨 요청이었나」를 들고 있어야 한다.
      setLastIntent(next);
      try {
        // ★ 질의로 보낸다 — 본문이면 422(인자 없음). [실측 2026-09-05]
        await dsmPostQuery(dsmEndpoint.drill, { enabled: next, reason });
        setReason('');
        state.reload();
        report.reload();
      } catch (err) {
        // 400(사유 없음) · 403(남의 테넌트) 를 **그대로 보여 준다.** 하나로 묶으면
        // 무엇을 고쳐 다시 보낼지 화면이 말하지 못한다 (D-290).
        setError(userFacingError('DrillMode', err, '요청이 실패했습니다.'));
      } finally {
        setBusy(false);
      }
    },
    [reason, state, report],
  );

  const current = state.data;
  const r = report.data;
  const realSends = r?.real_channel_sends ?? 0;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Title level={4} style={{ margin: 0 }}>
          {HEADLINE}
        </Title>

        <Alert type="warning" showIcon message="이 스위치는 알림을 끕니다 — 배선됨(2026-09-24)." description={WIRED_NOTE} />

        {/* ★ [UX-31′] 네 문장 + **살아 있는 단추**. 누르면 방금 그 전환을 다시 보낸다. */}
        {error ? (
          <FailureNotice
            title="훈련 모드를 바꾸지 못했습니다."
            detail={error}
            busy={busy}
            onRetry={lastIntent === null ? undefined : () => toggle(lastIntent)}
          />
        ) : null}

        <StateBoundary state={state.state} reason={state.reason} status={state.status} onRetry={state.reload}>
          {current ? (
            <Card
              title={
                <Space>
                  <span>현재 상태</span>
                  <Tag color={current.drill_mode ? 'red' : 'green'}>
                    {current.drill_mode ? '훈련 중 — 알림이 사람에게 가지 않습니다' : '실운영'}
                  </Tag>
                  {/*
                    ★ [P-78 · 턴 H] 종전에는 여기에 「data_source = live」가 그대로
                      떴다 — 사전이 §2·§4 두 곳에서 금지한 영문 열거값이다.
                      **시드·훈련일 때만** 사람의 말로 그린다(실운영은 평상이다).
                  */}
                  {dataSourceBadge(current.data_source) ? (
                    <Tag>{dataSourceBadge(current.data_source)}</Tag>
                  ) : null}
                </Space>
              }
            >
              <Descriptions column={1} size="small">
                <Descriptions.Item label="언제부터">
                  {current.since
            ? `${absolute(current.since)} · ${stamp(current.since)}`
            : '켠 적이 없습니다 — 위에서 훈련 모드를 켜는 단추를 누르십시오'}
                </Descriptions.Item>
                <Descriptions.Item label="누가">{current.by || '—'}</Descriptions.Item>
                <Descriptions.Item label="왜">{current.reason || '—'}</Descriptions.Item>
                <Descriptions.Item label="훈련 중 채널">
                  {current.channel_while_drilling} (사람이 아니라 로그에 도달합니다)
                </Descriptions.Item>
              </Descriptions>

              <Space direction="vertical" style={{ width: '100%', marginTop: 12 }}>
                <Input.TextArea
                  rows={2}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="사유 (필수) — 사후에 「그 시각에 왜 안 갔나」를 묻는 사람이 반드시 생깁니다."
                />
                <Space>
                  <Switch
                    checked={current.drill_mode}
                    loading={busy}
                    // 사유가 비면 **누를 수 없다.** 눌리는데 400 이 나는 버튼은
                    // 「안 먹는 버튼」으로 읽힌다.
                    disabled={!reason.trim()}
                    onChange={toggle}
                  />
                  <Text type="secondary">
                    {reason.trim() ? '' : '사유를 적어야 스위치가 열립니다.'}
                  </Text>
                </Space>
              </Space>
            </Card>
          ) : null}
        </StateBoundary>

        <StateBoundary state={report.state} reason={report.reason} status={report.status} onRetry={report.reload}>
          {r ? (
            <Card title="훈련 종료 보고서 1장">
              {!r.measurable ? (
                <Alert type="info" showIcon message="아직 보고서가 없습니다. 훈련을 끝내면 이 자리에 만들어집니다." description={r.reason} />
              ) : (
                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                  <Row gutter={24}>
                    <Col>
                      <Statistic
                        title="실채널 발송 (0이어야 합니다)"
                        value={realSends}
                        valueStyle={{ color: realSends === 0 ? '#389e0d' : '#cf1322' }}
                      />
                    </Col>
                    <Col>
                      <Statistic title="창 안 발송 전건 (분모)" value={r.sends_total ?? 0} />
                    </Col>
                    <Col>
                      <Statistic title="창 안 이벤트" value={r.events_total ?? 0} />
                    </Col>
                  </Row>
                  {(r.sends_total ?? 0) === 0 ? (
                    <Alert
                      type="warning"
                      showIcon
                      message="분모가 0입니다 — 위의 0은 아무것도 증명하지 않습니다."
                      description="창 안에 발송 시도 자체가 없었습니다. 스위치가 걸린 것과 아무 일도 없던 밤은 이 수로 구별되지 않습니다."
                    />
                  ) : null}
                  <Descriptions column={1} size="small" bordered>
                    <Descriptions.Item label="훈련 창">
                      {absolute(r.started_at)} ~{' '}
                      {r.ended_at ? absolute(r.ended_at) : '진행 중'}
                    </Descriptions.Item>
                    <Descriptions.Item label="채널별 발송">
                      {Object.entries(r.sends_by_channel ?? {})
                        .map(([c, n]) => `${c}: ${n}건`)
                        .join(' · ') || '없음'}
                    </Descriptions.Item>
                    <Descriptions.Item label="유형별 이벤트">
                      {Object.entries(r.events_by_type ?? {})
                        .map(([t, n]) => `${t}: ${n}건`)
                        .join(' · ') || '없음'}
                    </Descriptions.Item>
                    <Descriptions.Item label="스위치">
                      {r.switch_by || '—'} — {r.switch_reason || '—'}
                    </Descriptions.Item>
                  </Descriptions>
                  {/* ★ [UX-20] 이 자리에 감사 채널 이름과 `data_source` 칸 이름이
                      백틱째로 떠 있었다 — 내부 이름은 사용자에게 뜻이 없다(GX-COPY §4).
                      (내부 사실 · 화면에 적지 않는다: 훈련 창은 감사에서 왔고, 이벤트에
                       `data_source` 칸을 새로 만들지 않았다 — 새 칸은 태어나는 순간
                       과거가 비어 있고, 빈 과거는 「전부 실사건이었다」로 읽힌다.) */}
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    이 보고서의 훈련 구간은 스위치를 켜고 끈 기록에서 세웠습니다 —
                    훈련 표시를 이벤트에 새로 붙이지 않았으므로, 훈련 전에 난 이벤트가
                    뒤늦게 훈련으로 바뀌는 일은 없습니다.
                  </Paragraph>
                </Space>
              )}
            </Card>
          ) : null}
        </StateBoundary>
      </Space>
    </Main>
  );
}
