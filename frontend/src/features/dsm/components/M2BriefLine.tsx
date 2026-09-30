/**
 * DSM-U3-01 — **역할별 M2 상단 한 줄** (턴 AQ · 차선 N3).
 *
 * 역할 분류 축(상주 경찰관 · 119 · 시설 · 당직)을 고르면 그 역할의 「지금 할 일」
 * 한 줄을 서버(`GET /api/dsm/events/{id}/m2-brief?role=`)에서 **다시 불러** 그린다.
 * 문안은 서버의 역할 × 유형 표 한 곳에서만 온다 — 화면은 받은 글자를 그대로 보인다.
 */
import { Alert, Card, Radio, Space, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { aqDsmEndpoint, aqFreshGet } from './aqScreensApi';

const { Text } = Typography;

/** 역할 값 ↔ 표시 이름 — 서버 `u36_an_service.ROLES`·`ROLE_LABELS` 와 같은 글자. */
export const M2_ROLES: Array<{ value: string; label: string }> = [
  { value: 'police', label: '상주 경찰관' },
  { value: '119', label: '119' },
  { value: 'facility', label: '시설' },
  { value: 'duty', label: '당직' },
];

interface M2Brief {
  event_id: number;
  role: string;
  role_label: string;
  event_type: string;
  text: string;
}

export default function M2BriefLine({ eventId }: { eventId: number | string }) {
  const [role, setRole] = useState<string>(M2_ROLES[0].value);
  const [brief, setBrief] = useState<M2Brief | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setError(null);
    aqFreshGet<M2Brief>(aqDsmEndpoint.m2Brief(eventId), { role })
      .then((b) => {
        if (alive) setBrief(b);
      })
      .catch((e: unknown) => {
        if (!alive) return;
        setBrief(null);
        setError(`지금 할 일을 불러오지 못했습니다 — ${(e as Error).message}`);
      });
    return () => {
      alive = false;
    };
  }, [eventId, role]);

  return (
    <Card size="small" title="지금 할 일 (역할별)" data-gx="dsm-u3-01-card">
      <Space direction="vertical" style={{ width: '100%' }}>
        <Radio.Group
          value={role}
          onChange={(e) => setRole(e.target.value)}
          optionType="button"
          data-gx="dsm-u3-01-role"
          options={M2_ROLES}
        />
        {error && <Alert type="warning" showIcon message={error} />}
        <div data-gx="dsm-u3-01-line">
          {brief ? (
            <Space wrap>
              <Tag color="blue">{brief.role_label}</Tag>
              <Text strong style={{ fontSize: 16 }}>
                {brief.text}
              </Text>
            </Space>
          ) : (
            !error && <Text type="secondary">불러오는 중</Text>
          )}
        </div>
      </Space>
    </Card>
  );
}
