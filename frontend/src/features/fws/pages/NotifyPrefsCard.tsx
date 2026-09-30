/**
 * FWS-F1-12 · F2-15 — M4 「근무 외 알림 차단」 칸 (턴 AQ · 차선 N3).
 *
 * 저장된 값(`GET /api/fws/notify-prefs`)을 읽어 보이고, 바꿔 저장하면(`POST` · 질의)
 * **같은 GET 을 캐시 우회로 다시 불러** 서버에 남은 값만 그린다. 차단 판정은 서버
 * (K2 `webpush._blocked_reason`)가 이 저장값을 되읽어 한다 — 화면은 판정하지 않는다.
 * 감시원(F1 · PatrolHome)과 진화대(F2 · FieldHome)가 같은 칸을 쓴다(같은 서버 문).
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, Button, Card, Input, Space, Typography } from 'antd';

import { fwsEndpoint, fwsGetFresh, fwsPostQuery } from '../api';
import { FWS_AQ_N3_COPY } from '../copy_aq_n3';

const { Text } = Typography;
const C = FWS_AQ_N3_COPY.notifyPrefs;

interface NotifyPrefs {
  quiet_hours_start: string;
  quiet_hours_end: string;
  assigned_post_code: string;
}

export default function NotifyPrefsCard({ gxPrefix }: { gxPrefix: string }): JSX.Element {
  const [saved, setSaved] = useState<NotifyPrefs | null>(null);
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [post, setPost] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async (): Promise<void> => {
    try {
      const p = await fwsGetFresh<NotifyPrefs>(fwsEndpoint.notifyPrefs);
      setSaved(p);
      setStart(p.quiet_hours_start);
      setEnd(p.quiet_hours_end);
      setPost(p.assigned_post_code);
    } catch {
      setError(C.loadFailed);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function save(): Promise<void> {
    setBusy(true);
    setNotice(null);
    try {
      await fwsPostQuery(fwsEndpoint.notifyPrefs, {
        quiet_hours_start: start,
        quiet_hours_end: end,
        assigned_post_code: post,
      });
      setError(null);
      setNotice(C.savedNotice);
    } catch (e) {
      setError(`${C.failed} — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  }

  const window =
    saved && saved.quiet_hours_start && saved.quiet_hours_end
      ? `${saved.quiet_hours_start} ~ ${saved.quiet_hours_end}`
      : null;

  return (
    <Card title={C.title} data-gx={`${gxPrefix}-card`}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {error && <Alert type="error" showIcon closable message={error} onClose={() => setError(null)} />}
        {notice && <Alert type="success" showIcon closable message={notice} onClose={() => setNotice(null)} />}
        <div data-gx={`${gxPrefix}-saved`}>
          <Text type="secondary">{C.currentLabel}: </Text>
          <Text strong>{window ?? C.notSet}</Text>
          {saved?.assigned_post_code ? (
            <Text> · {C.postLabel} {saved.assigned_post_code}</Text>
          ) : null}
          {window && (
            <div>
              <Text type="secondary">{C.blockNote}</Text>
            </div>
          )}
        </div>
        <Space wrap>
          <Text>{C.startLabel}</Text>
          <Input type="time" value={start} onChange={(e) => setStart(e.target.value)}
            style={{ width: 130 }} data-gx={`${gxPrefix}-start`} />
          <Text>{C.endLabel}</Text>
          <Input type="time" value={end} onChange={(e) => setEnd(e.target.value)}
            style={{ width: 130 }} data-gx={`${gxPrefix}-end`} />
        </Space>
        <Space wrap>
          <Text>{C.postLabel}</Text>
          <Input placeholder={C.postPlaceholder} value={post} onChange={(e) => setPost(e.target.value)}
            style={{ width: 180 }} data-gx={`${gxPrefix}-post`} />
        </Space>
        <Button type="primary" disabled={busy} onClick={() => void save()} data-gx={`${gxPrefix}-save`}>
          {C.saveButton}
        </Button>
      </Space>
    </Card>
  );
}
