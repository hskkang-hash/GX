/**
 * FWS F4 통합지휘본부장 · 상황실 — `/fws/command` (WO-GX-20260930-18 §5 P-414 ·
 * 턴 AO 차선 N2).
 *
 * 턴 AO · WO-18 · 차선 N2 단독 소유(조율자가 빈 화면으로 세워 `App.tsx` 에
 * 등록해 둠). ★ 문구는 이 차선의 `../copy_command.ts` 에서 온다 — 공용
 * `../copy.ts` 는 이 턴에 고치지 않는다. 서버 호출은 공용 `../api.ts` 의
 * `fwsGet`(그 파일도 고치지 않는다 — 이 화면 전용 경로 상수만 이 파일 안에 둔다,
 * `OfficeHome.tsx` 와 같은 관례).
 * ★ 지도·화선 렌더는 이 화면에 없다 — §0.4 인접 금지구역(MapForRoute*·
 *   FormRoute.tsx) 밖에 남긴다. 위치는 주소 문자열로만 보인다(F4-03).
 * ★ F4-01 의 완결조건(§5.4 표)은 "한 화면" — 이 화면이 사건 하나(단계·자원·
 *   대응 시계·대피 현황·지휘본부)를 한 응답으로 묶어 보여 준다
 *   (`GET /command/incidents/{id}/command`). 나머지 F4 절(헬기 승인·협조
 *   기록·회의 기록 등)은 이 턴에서 HTTP 실측(`backend/tests/test_fws_f4.py`)
 *   으로 증명하고, 이 화면은 조회 카드에 그친다 — 빈 화면에서 시작한다.
 */
import { useState } from 'react';

import { Alert, Button, Card, Col, Descriptions, Input, Row, Space, Typography } from 'antd';

import { fwsGet } from '../api';
import { FWS_COMMAND_COPY } from '../copy_command';

const { Title, Text } = Typography;

const COMMAND = {
  screen: (eventId: string) => `/api/fws/command/incidents/${eventId}/command`,
};

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

export default function CommandHome(): JSX.Element {
  const [eventId, setEventId] = useState('');
  const [screen, setScreen] = useState<CommandScreenBody | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadScreen(): Promise<void> {
    if (!eventId.trim()) return;
    try {
      const body = await fwsGet<CommandScreenBody>(COMMAND.screen(eventId.trim()));
      setScreen(body);
      setError(null);
    } catch {
      setScreen(null);
      setError(FWS_COMMAND_COPY.home.loadFailed);
    }
  }

  return (
    <Space direction="vertical" size="large" style={{ width: '100%', padding: 16 }}>
      <Title level={3}>{FWS_COMMAND_COPY.home.title}</Title>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}

      <Card>
        <Space>
          <Input
            placeholder={FWS_COMMAND_COPY.home.eventIdLabel}
            value={eventId}
            onChange={(e) => setEventId(e.target.value)}
            style={{ width: 200 }}
          />
          <Button type="primary" onClick={loadScreen}>
            {FWS_COMMAND_COPY.home.loadButton}
          </Button>
        </Space>
      </Card>

      {screen && (
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card title={FWS_COMMAND_COPY.screen.incidentTitle}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="주소">
                  {screen.incident.address ?? FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label="등급">{screen.incident.severity}</Descriptions.Item>
                <Descriptions.Item label="대응 상태">
                  {screen.incident.response_state}
                </Descriptions.Item>
                <Descriptions.Item label="발생 시각">
                  {screen.incident.occurred_at}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
          <Col span={12}>
            <Card title={FWS_COMMAND_COPY.screen.stageTitle}>
              {screen.stage ? (
                <Text>
                  {screen.stage.stage}
                  {screen.stage.command_level ? ` · ${screen.stage.command_level}` : ''}
                </Text>
              ) : (
                <Text type="secondary">{FWS_COMMAND_COPY.screen.noneYet}</Text>
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Card title={FWS_COMMAND_COPY.screen.commandPostTitle}>
              {screen.command_post ? (
                <Text>
                  {screen.command_post.address} · {screen.command_post.org_composition}
                </Text>
              ) : (
                <Text type="secondary">{FWS_COMMAND_COPY.screen.noneYet}</Text>
              )}
            </Card>
          </Col>
          <Col span={12}>
            <Card title={FWS_COMMAND_COPY.screen.resourcesTitle}>
              {screen.resources.length === 0 && (
                <Text type="secondary">{FWS_COMMAND_COPY.screen.noneYet}</Text>
              )}
              {screen.resources.map((r, i) => (
                <div key={i}>
                  {r.kind} · {r.resource_name}
                </div>
              ))}
            </Card>
          </Col>
          <Col span={12}>
            <Card title={FWS_COMMAND_COPY.screen.evacuationTitle}>
              <Text>
                {screen.evacuation.total_villages}곳 중{' '}
                {screen.evacuation.percent_complete ?? 0}% 완료
              </Text>
            </Card>
          </Col>
          <Col span={24}>
            <Card title={FWS_COMMAND_COPY.screen.clockTitle}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="신고">
                  {screen.response_clock.reported_at ?? FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label="확인">
                  {screen.response_clock.acknowledged_at ?? FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label="헬기 투하">
                  {screen.response_clock.helicopter_dropped_at ??
                    FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label="주불">
                  {screen.response_clock.main_fire_out_at ?? FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
                <Descriptions.Item label="진화완료">
                  {screen.response_clock.extinguished_at ?? FWS_COMMAND_COPY.screen.noneYet}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        </Row>
      )}
    </Space>
  );
}
