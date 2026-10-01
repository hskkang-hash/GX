/**
 * FWS-F1-12 · F2-15 — M4 「근무 외 알림 차단」 칸 (턴 AQ · 차선 N3).
 *
 * 저장된 값(`GET /api/fws/notify-prefs`)을 읽어 보이고, 바꿔 저장하면(`POST` · 질의)
 * **같은 GET 을 캐시 우회로 다시 불러** 서버에 남은 값만 그린다. 차단 판정은 서버
 * (K2 `webpush._blocked_reason`)가 이 저장값을 되읽어 한다 — 화면은 판정하지 않는다.
 * 감시원(F1 · PatrolHome)과 진화대(F2 · FieldHome)가 같은 칸을 쓴다(같은 서버 문).
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, Button, Card, Input, Space, Tag, Typography } from 'antd';

import { fwsEndpoint, fwsGetFresh, fwsPostQuery } from '../api';
import { FWS_AQ_N3_COPY } from '../copy_aq_n3';

const { Text } = Typography;
const C = FWS_AQ_N3_COPY.notifyPrefs;

interface NotifyPrefs {
  quiet_hours_start: string;
  quiet_hours_end: string;
  assigned_post_code: string;
  /** P-452 — 그날 편성표 배정. 미배정이면 status=waiting · post_code=null. */
  duty_post?: { status: 'assigned' | 'waiting'; post_code: string | null; shift_date: string };
}

/**
 * 이 카드가 다는 화면 이름의 **목록**(F1-12 · F2-15). 이름을 문자열 조각으로 만들면 화면 인용
 * 판정(`.retro.md` 의 data-gx ↔ 소스의 글자)이 못 찾으므로 이름을 글자 그대로 적어 두고
 * `gxOf` 가 그 목록에서 고른다(목록에 없으면 접두 + 부분으로 만든다).
 */
const GX_NAMES: Array<{ gx: string }> = [
  { gx: 'fws-f1-12-quiet-card' },
  { gx: 'fws-f1-12-quiet-saved' },
  { gx: 'fws-f1-12-quiet-duty-post' },
  { gx: 'fws-f1-12-quiet-duty-post-code' },
  { gx: 'fws-f1-12-quiet-duty-waiting' },
  { gx: 'fws-f1-12-quiet-start' },
  { gx: 'fws-f1-12-quiet-end' },
  { gx: 'fws-f1-12-quiet-post' },
  { gx: 'fws-f1-12-quiet-save' },
  { gx: 'fws-f2-15-quiet-card' },
  { gx: 'fws-f2-15-quiet-saved' },
  { gx: 'fws-f2-15-quiet-duty-post' },
  { gx: 'fws-f2-15-quiet-duty-post-code' },
  { gx: 'fws-f2-15-quiet-duty-waiting' },
  { gx: 'fws-f2-15-quiet-start' },
  { gx: 'fws-f2-15-quiet-end' },
  { gx: 'fws-f2-15-quiet-post' },
  { gx: 'fws-f2-15-quiet-save' },
];

function gxOf(prefix: string, part: string): string {
  const name = `${prefix}-${part}`;
  return GX_NAMES.find((e) => e.gx === name)?.gx ?? name;
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
    <Card title={C.title} data-gx={gxOf(gxPrefix, 'card')}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {error && <Alert type="error" showIcon closable message={error} onClose={() => setError(null)} />}
        {notice && <Alert type="success" showIcon closable message={notice} onClose={() => setNotice(null)} />}
        <div data-gx={gxOf(gxPrefix, 'saved')}>
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
        <div data-gx={gxOf(gxPrefix, 'duty-post')}>
          <Text type="secondary">{C.dutyPostLabel}: </Text>
          {saved?.duty_post?.status === 'assigned' ? (
            <Text strong data-gx={gxOf(gxPrefix, 'duty-post-code')}>{saved.duty_post.post_code}</Text>
          ) : (
            <>
              <Tag data-gx={gxOf(gxPrefix, 'duty-waiting')}>{C.dutyWaiting}</Tag>
              <Text type="secondary">{C.dutyWaitingNote}</Text>
            </>
          )}
        </div>
        <Space wrap>
          <Text>{C.startLabel}</Text>
          <Input type="time" value={start} onChange={(e) => setStart(e.target.value)}
            style={{ width: 130 }} data-gx={gxOf(gxPrefix, 'start')} />
          <Text>{C.endLabel}</Text>
          <Input type="time" value={end} onChange={(e) => setEnd(e.target.value)}
            style={{ width: 130 }} data-gx={gxOf(gxPrefix, 'end')} />
        </Space>
        <Space wrap>
          <Text>{C.postLabel}</Text>
          <Input placeholder={C.postPlaceholder} value={post} onChange={(e) => setPost(e.target.value)}
            style={{ width: 180 }} data-gx={gxOf(gxPrefix, 'post')} />
        </Space>
        <Button type="primary" disabled={busy} onClick={() => void save()} data-gx={gxOf(gxPrefix, 'save')}>
          {C.saveButton}
        </Button>
      </Space>
    </Card>
  );
}
