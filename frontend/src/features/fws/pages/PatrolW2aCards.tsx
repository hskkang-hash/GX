/**
 * 감시원(F1) 화면 칸 셋 — 턴 AQ · 2물결 차선 W2A.
 *
 *   FWS-F1-11  내 근무 기록·순찰 실적(일·주) 표     GET  /api/fws/patrol/mine
 *   FWS-F1-02  순찰 경로 기록(GPS 트랙 · 순찰함)    POST /api/fws/patrol/track
 *   FWS-F1-06  현장 확인 회신(3택 · 사진 1)         GET/POST /api/fws/verifications/{id}[/reply]
 *
 * ★ 누른 뒤에는 **같은 화면의 조회 GET 을 캐시 우회로 다시 불러** 서버에 남은 값만 그린다
 *   (`fwsGetFresh` — 캐시 적중 본문은 누르기 전 값을 되살린다).
 * ★ 지도는 그리지 않는다(§0.4 인접) — 위치는 값으로만 보낸다.
 * ★ NFC 실기기 읽기는 이 칸에 없다 — 순찰함 번호를 입력해 보낸다.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, Button, Card, Input, Radio, Space, Typography, Upload } from 'antd';

import { fwsEndpoint, fwsGetFresh, fwsPostQuery, newFwsIdempotencyKey } from '../api';
import { currentPosition, uploadFieldPhoto } from '../api_w2a';
import { FWS_COPY, FWS_UNKNOWN } from '../copy';
import { FWS_W2A_COPY } from '../copy_w2a';

const { Text } = Typography;
const M = FWS_W2A_COPY.patrolMine;
const T = FWS_W2A_COPY.track;
const V = FWS_W2A_COPY.verify;

interface Counts {
  checkins: number;
  tracks: number;
  checkpoints: number;
}

interface PatrolMine {
  today: Counts;
  week: Counts;
  as_of: string;
}

interface VerificationReply {
  reply_id: number;
  result: string;
  photo_id: number | null;
}

interface Verification {
  verification_id: number;
  address: string | null;
  occurred_at: string | null;
  verdict: string | null;
  replies: VerificationReply[];
}

const RESULT_LABEL: Record<string, string> = {
  fire_confirmed: FWS_COPY.verification.fireConfirmed,
  false_alarm: FWS_COPY.verification.falseAlarm,
  cannot_access: FWS_COPY.verification.cannotAccess,
};

function verdictLabel(verdict: string | null): string {
  if (verdict === 'confirmed') return V.verdictConfirmed;
  if (verdict === 'rejected') return V.verdictRejected;
  if (verdict === null) return V.verdictNone;
  return FWS_UNKNOWN;
}

export default function PatrolW2aCards({ refreshKey }: { refreshKey: number }): JSX.Element {
  const [mine, setMine] = useState<PatrolMine | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reloadMine = useCallback(async (): Promise<void> => {
    try {
      setMine(await fwsGetFresh<PatrolMine>(fwsEndpoint.patrolMine));
    } catch {
      setError(FWS_COPY.error.generic);
    }
  }, []);

  useEffect(() => {
    void reloadMine();
  }, [reloadMine, refreshKey]);

  return (
    <>
      {error && <Alert type="error" message={error} showIcon closable onClose={() => setError(null)} />}
      <PatrolMineCard mine={mine} onRefresh={reloadMine} />
      <PatrolTrackCard onSaved={reloadMine} onError={setError} />
      <VerificationReplyCard onError={setError} />
    </>
  );
}

// ── FWS-F1-11 내 근무 기록·순찰 실적(일·주) ─────────────────────────────
function PatrolMineCard({
  mine,
  onRefresh,
}: {
  mine: PatrolMine | null;
  onRefresh: () => Promise<void>;
}): JSX.Element {
  const rows = mine
    ? [
        { key: 'today', label: M.today, c: mine.today },
        { key: 'week', label: M.week, c: mine.week },
      ]
    : [];
  return (
    <Card
      title={M.title}
      extra={
        <Button size="small" data-gx="fws-f1-11-refresh" onClick={() => void onRefresh()}>
          {M.refresh}
        </Button>
      }
    >
      <table data-gx="fws-f1-11-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>{M.colPeriod}</th>
            <th style={{ textAlign: 'right' }}>{M.colCheckins}</th>
            <th style={{ textAlign: 'right' }}>{M.colTracks}</th>
            <th style={{ textAlign: 'right' }}>{M.colCheckpoints}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.key}>
              <td>{r.label}</td>
              <td style={{ textAlign: 'right' }}>{r.c.checkins}</td>
              <td style={{ textAlign: 'right' }}>{r.c.tracks}</td>
              <td style={{ textAlign: 'right' }}>{r.c.checkpoints}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!mine && <Text type="secondary">{FWS_UNKNOWN}</Text>}
    </Card>
  );
}

// ── FWS-F1-02 순찰 경로 기록(GPS 트랙 · 순찰함 통과) ─────────────────────
function PatrolTrackCard({
  onSaved,
  onError,
}: {
  onSaved: () => Promise<void>;
  onError: (msg: string) => void;
}): JSX.Element {
  const [post, setPost] = useState('');
  const [checkpoint, setCheckpoint] = useState('');
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(query: Record<string, string | number>): Promise<void> {
    setBusy(true);
    try {
      await fwsPostQuery(fwsEndpoint.patrolTrack, { post_code: post, ...query }, newFwsIdempotencyKey());
      await onSaved();
      setNotice(T.savedNotice);
    } catch {
      onError(FWS_COPY.error.generic);
    } finally {
      setBusy(false);
    }
  }

  async function sendGps(): Promise<void> {
    if (!post.trim()) {
      onError(T.needPost);
      return;
    }
    let pos: { lat: number; lng: number };
    try {
      pos = await currentPosition();
    } catch {
      onError(T.noPosition);
      return;
    }
    await send({ lat: pos.lat, lng: pos.lng });
  }

  async function sendCheckpoint(): Promise<void> {
    if (!post.trim()) {
      onError(T.needPost);
      return;
    }
    if (!checkpoint.trim()) return;
    await send({ checkpoint_code: checkpoint.trim() });
    setCheckpoint('');
  }

  return (
    <Card title={T.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}
        <Input
          data-gx="fws-f1-02-post"
          placeholder={T.postPlaceholder}
          value={post}
          onChange={(e) => setPost(e.target.value)}
          style={{ width: 200 }}
        />
        <Button type="primary" data-gx="fws-f1-02-gps" loading={busy} onClick={() => void sendGps()}>
          {T.gpsButton}
        </Button>
        <Space wrap>
          <Input
            data-gx="fws-f1-02-checkpoint-code"
            placeholder={T.checkpointPlaceholder}
            value={checkpoint}
            onChange={(e) => setCheckpoint(e.target.value)}
            style={{ width: 200 }}
          />
          <Button data-gx="fws-f1-02-checkpoint" loading={busy} onClick={() => void sendCheckpoint()}>
            {T.checkpointButton}
          </Button>
        </Space>
      </Space>
    </Card>
  );
}

// ── FWS-F1-06 현장 확인 회신(산불 맞음 · 소각·오인 5택 · 접근 불가 + 사진 1) ──
function VerificationReplyCard({ onError }: { onError: (msg: string) => void }): JSX.Element {
  const [id, setId] = useState('');
  const [item, setItem] = useState<Verification | null>(null);
  const [reason, setReason] = useState('agri_burning');
  const [photo, setPhoto] = useState<File | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(targetId: string): Promise<void> {
    if (!targetId) return;
    try {
      setItem(await fwsGetFresh<Verification>(fwsEndpoint.verification(targetId)));
    } catch {
      onError(FWS_COPY.error.generic);
    }
  }

  async function reply(result: 'fire_confirmed' | 'false_alarm' | 'cannot_access'): Promise<void> {
    if (!item) return;
    setBusy(true);
    try {
      const photoId = photo ? await uploadFieldPhoto(item.verification_id, photo) : undefined;
      await fwsPostQuery(
        fwsEndpoint.verificationReply(item.verification_id),
        {
          result,
          reason_code: result === 'false_alarm' ? reason : undefined,
          photo_id: photoId,
        },
        newFwsIdempotencyKey(),
      );
      setPhoto(null);
      await load(String(item.verification_id));
      setNotice(V.sentNotice);
    } catch {
      onError(FWS_COPY.error.generic);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card title={V.title}>
      <Space direction="vertical" style={{ width: '100%' }}>
        {notice && <Alert type="success" message={notice} showIcon closable onClose={() => setNotice(null)} />}
        <Space>
          <Input
            data-gx="fws-f1-06-id"
            placeholder={V.idPlaceholder}
            value={id}
            onChange={(e) => setId(e.target.value)}
            style={{ width: 160 }}
          />
          <Button data-gx="fws-f1-06-lookup" onClick={() => void load(id)}>
            {V.lookupButton}
          </Button>
        </Space>
        {item && (
          <>
            <Text data-gx="fws-f1-06-verdict">
              #{item.verification_id} · {item.address ?? FWS_UNKNOWN} · {V.verdictPrefix}:{' '}
              <strong>{verdictLabel(item.verdict)}</strong>
            </Text>
            <Upload
              accept="image/jpeg,image/png,image/webp"
              maxCount={1}
              beforeUpload={(file) => {
                setPhoto(file);
                return false;
              }}
              onRemove={() => setPhoto(null)}
              fileList={photo ? [{ uid: '1', name: photo.name, status: 'done' }] : []}
            >
              <Button data-gx="fws-f1-06-photo">{V.photoLabel}</Button>
            </Upload>
            <Space wrap>
              <Button
                danger
                data-gx="fws-f1-06-fire-confirmed"
                loading={busy}
                onClick={() => void reply('fire_confirmed')}
              >
                {FWS_COPY.verification.fireConfirmed}
              </Button>
              <Button data-gx="fws-f1-06-cannot-access" loading={busy} onClick={() => void reply('cannot_access')}>
                {FWS_COPY.verification.cannotAccess}
              </Button>
            </Space>
            <Text type="secondary">{V.reasonLabel}</Text>
            <Radio.Group value={reason} onChange={(e) => setReason(e.target.value)}>
              {Object.entries(FWS_COPY.falseAlarmReason).map(([code, label]) => (
                <Radio.Button key={code} value={code}>
                  {label}
                </Radio.Button>
              ))}
            </Radio.Group>
            <Button data-gx="fws-f1-06-false-alarm" loading={busy} onClick={() => void reply('false_alarm')}>
              {FWS_COPY.verification.falseAlarm}
            </Button>
            <div data-gx="fws-f1-06-replies">
              <Text strong>{V.repliesTitle}</Text>
              {item.replies.length === 0 ? (
                <div>
                  <Text type="secondary">{V.noReplies}</Text>
                </div>
              ) : (
                item.replies.map((r) => (
                  <div key={r.reply_id}>
                    {RESULT_LABEL[r.result] ?? FWS_UNKNOWN}
                    {r.photo_id !== null && ` · ${V.withPhoto}`}
                  </div>
                ))
              )}
            </div>
          </>
        )}
      </Space>
    </Card>
  );
}
