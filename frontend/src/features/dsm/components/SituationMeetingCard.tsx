/**
 * DSM-U2-03 — **상황판단회의 기록** 한 화면 (턴 AQ · 차선 W2B).
 *
 * 회의 시각 · 참석 · 결정(통제·대피·비상 단계) · 근거 값(수위·강우) 네 칸을 한 폼에서 받아
 * `POST /api/dsm/situation-meetings` 한 번 → **`GET /api/dsm/situation-meetings` 를 다시
 * 불러** 기록 표를 그린다.
 *
 * ★ 완결 조건 「결정 → 테넌트 상태 축 변경」 — 회의가 비상 단계를 정했으면 같은 요청의
 *   `alert_level` 칸으로 보낸다. 서버가 위기경보·비상 단계 축에 한 줄을 더하고
 *   (`situation_meeting_service.record_meeting`), 띠·위기경보 카드가 다시 읽는다.
 */
import { FONT_SM } from '@/configs/fontTokens';
import { Alert, Button, Card, Input, Select, Space, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { dsmPostOnce, newIdempotencyKey } from '../api';
import {
  ALERT_LEVELS,
  announceAlertLevelChanged,
  w2bDsmEndpoint,
  w2bFreshGet,
} from './w2bDecisionApi';

const { Text } = Typography;

interface MeetingRow {
  meeting_id: number;
  text: string;
  actor_id: number | null;
}

export default function SituationMeetingCard() {
  const [rows, setRows] = useState<MeetingRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [occurredAt, setOccurredAt] = useState('');
  const [attendees, setAttendees] = useState('');
  const [decision, setDecision] = useState('');
  const [basis, setBasis] = useState('');
  const [level, setLevel] = useState<string | undefined>(undefined);

  const reload = useCallback(async () => {
    try {
      setRows(await w2bFreshGet<MeetingRow[]>(w2bDsmEndpoint.situationMeetings, { limit: 5 }));
    } catch (e) {
      setError(`회의 기록을 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const submit = async () => {
    if (!decision.trim()) {
      setError('결정을 적으십시오.');
      return;
    }
    setBusy(true);
    try {
      await dsmPostOnce(
        w2bDsmEndpoint.situationMeetings,
        {
          occurred_at: occurredAt || null,
          attendees,
          decision,
          basis,
          alert_level: level ?? '',
        },
        newIdempotencyKey(),
      );
      setError(null);
      setNotice(
        level
          ? `회의 기록을 남기고 비상 단계를 「${level}」(으)로 바꿨습니다.`
          : '회의 기록을 남겼습니다.',
      );
      setOccurredAt('');
      setAttendees('');
      setDecision('');
      setBasis('');
      if (level) announceAlertLevelChanged();
      setLevel(undefined);
    } catch (e) {
      setError(`기록하지 못했습니다 — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  };

  return (
    <Card size="small" title="상황판단회의 기록" data-gx="dsm-u2-03-card">
      <Space direction="vertical" size={8} style={{ width: '100%' }}>
        <Input
          data-gx="dsm-u2-03-occurred-at"
          type="datetime-local"
          value={occurredAt}
          onChange={(ev) => setOccurredAt(ev.target.value)}
          placeholder="회의 시각(비우면 지금)"
        />
        <Input
          data-gx="dsm-u2-03-attendees"
          value={attendees}
          onChange={(ev) => setAttendees(ev.target.value)}
          placeholder="참석(예: 상황실장·팀장)"
        />
        <Input.TextArea
          data-gx="dsm-u2-03-decision"
          value={decision}
          onChange={(ev) => setDecision(ev.target.value)}
          placeholder="결정(통제·대피·비상 단계)"
          autoSize={{ minRows: 2 }}
        />
        <Select
          data-gx="dsm-u2-03-alert-level"
          allowClear
          placeholder="비상 단계를 바꾸면 고르십시오(안 바꾸면 비움)"
          value={level}
          onChange={setLevel}
          options={ALERT_LEVELS.map((l) => ({ label: l, value: l }))}
          style={{ width: '100%' }}
        />
        <Input
          data-gx="dsm-u2-03-basis"
          value={basis}
          onChange={(ev) => setBasis(ev.target.value)}
          placeholder="근거 값(수위·강우)"
        />
        <Button
          type="primary"
          data-gx="dsm-u2-03-submit"
          loading={busy}
          onClick={() => void submit()}
        >
          회의 기록 남기기
        </Button>
        {error ? <Alert type="error" showIcon message={error} /> : null}
        {notice ? <Alert type="success" showIcon message={notice} /> : null}
        {rows.length > 0 ? (
          <Space direction="vertical" size={2} data-gx="dsm-u2-03-list">
            {rows.map((r) => (
              <Text key={r.meeting_id} type="secondary" style={{ fontSize: FONT_SM }}>
                {r.text}
              </Text>
            ))}
          </Space>
        ) : (
          <Text type="secondary">아직 회의 기록이 없습니다. 위 칸을 채워 등록하십시오.</Text>
        )}
      </Space>
    </Card>
  );
}
