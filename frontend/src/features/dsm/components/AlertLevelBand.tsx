/**
 * DSM-U4-06 — **위기경보·비상 단계 띠** (턴 AQ · 차선 W2B).
 *
 * `GET /api/dsm/alert-level?limit=1` 의 첫 행(= 지금 단계, `alert_level_service.latest`
 * 와 같은 줄)을 한 줄 띠로 그린다. 접수·회의 결정이 단계를 바꾸면
 * `ALERT_LEVEL_CHANGED` 를 듣고 **다시 GET** 한다 — 쓰기 응답으로 띠를 고치지 않는다.
 *
 * ★ `global` 이면 DSM 화면(`/dsm`)에서만 화면 위에 붙는다(상단바 자리 · App 한 줄로 끼운다).
 *   접수가 없으면 아무것도 안 그린다 — 빈 띠는 「없다」와 「못 읽었다」를 가르지 못한다.
 */
import { Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';

import {
  ALERT_LEVEL_CHANGED,
  ALERT_LEVEL_COLOR,
  type AlertLevelRow,
  w2bDsmEndpoint,
  w2bFreshGet,
} from './w2bDecisionApi';

const { Text } = Typography;

export default function AlertLevelBand({ global = false }: { global?: boolean }) {
  const location = useLocation();
  const onDsm = location.pathname.startsWith('/dsm');
  const [row, setRow] = useState<AlertLevelRow | null>(null);
  const [failed, setFailed] = useState(false);

  const load = useCallback(async () => {
    try {
      const rows = await w2bFreshGet<AlertLevelRow[]>(w2bDsmEndpoint.alertLevel, { limit: 1 });
      setRow(rows[0] ?? null);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, []);

  useEffect(() => {
    if (global && !onDsm) return undefined;
    void load();
    const on = () => void load();
    window.addEventListener(ALERT_LEVEL_CHANGED, on);
    return () => window.removeEventListener(ALERT_LEVEL_CHANGED, on);
  }, [global, onDsm, load]);

  if (global && !onDsm) return null;
  if (!row || !row.level) {
    return failed && !global ? (
      <Text type="secondary" data-gx="dsm-u4-06-band">
        위기경보 단계를 불러오지 못했습니다.
      </Text>
    ) : null;
  }

  const color = ALERT_LEVEL_COLOR[row.level] ?? 'default';
  return (
    <div
      data-gx="dsm-u4-06-band"
      role="status"
      style={{
        ...(global
          ? { position: 'fixed', top: 0, left: '50%', transform: 'translateX(-50%)', zIndex: 1000 }
          : {}),
        display: 'flex',
        gap: 8,
        alignItems: 'center',
        padding: '4px 12px',
        borderRadius: 4,
        background: 'rgba(255, 77, 79, 0.08)',
        border: '1px solid rgba(255, 77, 79, 0.35)',
      }}
    >
      <Text strong>위기경보</Text>
      <Tag color={color} data-gx="dsm-u4-06-band-level">
        {row.level}
      </Tag>
      <Text type="secondary">
        {row.received_at ? `${row.received_at} 접수` : ''}
        {row.doc_no ? ` · ${row.doc_no}` : ''}
        {row.staffing !== null ? ` · 비상 근무 ${row.staffing}명` : ''}
      </Text>
    </div>
  );
}
