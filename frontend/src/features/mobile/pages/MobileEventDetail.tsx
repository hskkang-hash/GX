/**
 * **M2 — 현장 상세** (U3 #2 · #3 · #7).
 *
 * 이동 중인 사람이 묻는 넷에 답한다:
 *   ① 무엇이 일어났나   유형 · 등급 · 발생 시각 · 대응 진행
 *   ② 어디로 가나       카메라 이름 · 설치 주소(`address_status` 로 부재를 가른다)
 *   ③ 무엇을 보나       스냅샷 참조 · 구간 티켓(**참조까지만** — 계약 11조 잠금)
 *   ④ 무엇을 누르나     상태 전이 (접수 확인 / 조치 중 / 종결 / 오탐)
 *
 * ★ 목록에서 값을 물려받지 않고 **서버에 다시 묻는다.** 물려 쓰면 문지기가 목록에만
 *   서고 상세에는 안 선다 — 그 자리가 IDOR 이 태어나는 자리다.
 *
 * ★ 전이표를 화면이 들지 않는다. 서버가 준 `allowed_next` 만 그린다 — 화면이 표를
 *   따로 들면 **서버가 거절하는 버튼**을 그리게 된다 (D-399).
 *
 * ★★ [실측 2026-09-04 · 차선 D] **스냅샷 바이트를 내보내는 라우트가 없다.**
 *   `snapshot_path` 는 MinIO 객체 키 문자열이고(`guardianx-dev/detections/…jpg`),
 *   `/api/dsm/` 어느 문도 그 바이트를 내보내지 않는다. 프리사인드 URL 을 화면에서
 *   만들지 않았다 — 그것은 **무계정 링크**이고 불변 제약이 금지한다. 그래서 이 화면은
 *   그림을 그리지 않고 **참조가 있다는 사실과 키를** 적는다. 온보딩 U3 #3 은
 *   이 턴에도 ● 가 아니다.
 *
 * ★★ **M3 현장 회신이 이 화면에 섰다** [2026-09-05 · 차선 C].
 *   앞판의 주석은 「문이 없어서 손잡이를 안 그렸다」였는데, **문은 이미 서 있었다**
 *   (`POST /api/dsm/events/{id}/field-reply` · `GET …/field-replies`).
 *   즉 없던 것은 문이 아니라 **손잡이**였고, 그동안 화면은 「보낼 수 없습니다」라고
 *   사실과 다른 말을 하고 있었다 — 잠자는 기능의 화면판이다.
 *   ★ 회신은 **계정이 남긴다.** 무계정 링크로 부를 수 있는 자리를 만들지 않는다.
 *   ★ 한 줄이다. 사진 첨부는 이 문의 칸이 아니다 — 없는 칸에 손잡이를 그리지 않는다.
 *
 * ★★ **전화 버튼을 그리지 않았다** [실측 2026-09-05 · 차선 C].
 *
 *   청한 것은 「이동 중인 사람이 현장·관제에 한 번에 거는 자리」였고, 그 자리는
 *   옳다 — 차를 몰고 가는 사람에게 `tel:` 한 번은 화면 다섯 번보다 낫다.
 *   그런데 **걸 번호가 이 제품 어디에도 없다.** 어디를 봤는지 그대로 적는다:
 *
 *     ① 이 화면이 손에 쥔 값 — `GET /api/dsm/events/{id}` 의 응답. 커널의
 *        `EventView` 가 그 전부이고(유형·등급·판정·시각·카메라·좌표·주소·
 *        스냅샷·대응 단계·`allowed_next`), **연락처 칸이 없다.**
 *     ② 갈 곳의 주인 — `StreamMonitor`. `install_address` 와
 *        `install_address_detail` 은 있는데 **전화 칸이 없다.** 카메라는 자기가
 *        선 자리를 알지, 그 자리를 지키는 사람을 모른다.
 *     ③ 알림을 받는 사람 — K2 의 `Recipient`. `address` 는 있지만 그것은
 *        **채널 주소**(메일 주소 · 웹훅)이고 통화가 닿는 번호가 아니다.
 *        `channel` 에 통화가 없다.
 *     ④ 저장소 전체에서 전화 칸을 가진 모델은 **배송 쪽**뿐이다(수취인·발송인).
 *        그것은 이 제품의 사건과 아무 관계가 없고, 게다가 그 자리는 손대지 않는
 *        구역이다. **가까이 있다고 해서 맞는 번호가 되지 않는다.**
 *
 *   그래서 안 그렸다. 번호 없이 단추만 그리면 세 갈래로 나빠진다 —
 *   눌러도 아무 일이 없거나(죽은 손잡이), 빈 `tel:` 로 전화 앱만 열리거나,
 *   **화면이 어딘가에 번호가 있다고 사람을 믿게 만든다.** 셋째가 가장 나쁘다:
 *   현장으로 가는 사람이 「연락은 저기서 하면 되겠다」고 계획을 세우고, 그 계획이
 *   틀렸다는 것을 **차 안에서** 알게 된다. 이 파일이 스냅샷과 사진 첨부에서
 *   이미 지킨 규약이 그것이다 — **없는 것에 손잡이를 그리지 않는다.**
 *
 *   ⚠ 그러므로 이것은 「안 했다」가 아니라 **「걸 곳이 없다」**로 넘긴다.
 *     문이 서려면 번호가 먼저 있어야 한다. 번호가 살 자리의 후보는 둘이고,
 *     **어느 쪽인지가 제품 판단**이라 화면이 정할 것이 아니다:
 *       ⓐ 카메라마다 — 그 자리를 지키는 사람. 「현장에 건다」에 맞는다.
 *       ⓑ 테넌트마다 하나 — 관제 대표번호. 「관제에 건다」에 맞는다.
 *     ⓑ 가 한 칸으로 서고 ⓐ 는 카메라 수만큼 채워 넣어야 한다 — 비어 있는
 *     ⓐ 는 다시 「없는 것에 그린 손잡이」가 된다. 판단을 청한다.
 */
import { Alert, Button, Card, Descriptions, Input, Modal, Space, Tag, Typography, message } from 'antd';
import { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';

import StateBoundary from '../../dsm/components/StateBoundary';
import { useDsmResource } from '../../dsm/hooks/useDsmResource';
import ResponseSteps, { VerdictBadge } from '../../dsm/components/ResponseSteps';
import {
  advanceLabel,
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../../dsm/severity';
import { absolute, relative } from '../../dsm/time';
import { dsmGet, DsmApiError, mobileEndpoint, mobilePostWithQuery } from '../api';
import MobileShell, { TOUCH_MIN } from '../components/MobileShell';
import { mobileRoutes } from '../routes';
import type { ClipTicket, EventDetailView } from '../types';

const { Text, Paragraph } = Typography;

/**
 * ★ [UX-22 · 2026-09-26] **이름표를 사전(`dsm/severity.ts`)에서 가져온다.**
 *   여기 따로 든 표는 관제 화면과 다른 말을 쓰고 있었다 — 같은 칸이 관제에서는
 *   「종결」, 휴대전화에서는 「완료(종결)」였다. 한 사건을 두 사람이 다른 이름으로
 *   부르면 교대 인계에서 말이 어긋난다. **표 자체는 여전히 서버 것이다.**
 */

const ADDRESS_STATUS_LABEL: Record<string, string> = {
  resolved: '조회됨',
  pending: '조회 대기',
  disabled: '조회 대상 아님 (좌표 없음)',
};

/**
 * 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다.
 * ⚠ 이 상수를 고치면 `scripts/capture_screens.py` 의 사본도 **같은 커밋에서** 고친다.
 */
export const FIELD_REPLY_HEADLINE = '현장 회신 — 본 것을 한 줄로';

interface FieldReplyRow {
  reply_id: number;
  text: string;
  author_name: string;
}

export default function MobileEventDetail() {
  const { id } = useParams<{ id: string }>();
  const [busy, setBusy] = useState('');
  const [replyText, setReplyText] = useState('');

  const event = useDsmResource<EventDetailView>(
    () => dsmGet<EventDetailView>(mobileEndpoint.eventDetail(id!)),
    [id],
    { enabled: Boolean(id) },
  );

  /**
   * 구간 티켓은 **부수적**이다. 없어도 상세는 선다.
   *
   * ★★ [실측 2026-09-04] 구간 참조가 없는 이벤트에서 이 문은 **404** 를 낸다.
   *   404 를 그대로 오류로 그리면 화면이 「불러오지 못했습니다」라고 빨갛게 말하는데,
   *   실제로 일어난 일은 **「이 사건에는 녹화가 없다」는 정상 부재**다. 둘을 같은
   *   그림으로 그리는 것이 DA-03 §2-5 가 금지한 모양이다 — 빈 것은 기다릴 것이 없고
   *   오류는 다시 시도할 것이 있다. 그래서 404 만 **빈 것**으로 접는다.
   *   ⚠ 다른 상태 코드는 접지 않는다. 403·500 을 함께 접으면 「권한이 없다」와
   *     「서버가 죽었다」가 「없다」로 보인다.
   */
  const clip = useDsmResource<ClipTicket | null>(
    () =>
      dsmGet<ClipTicket>(mobileEndpoint.clip(id!)).catch((err: unknown) => {
        if (err instanceof DsmApiError && err.status === 404) return null;
        throw err;
      }),
    [id],
    { enabled: Boolean(id), isEmpty: (v) => v === null },
  );

  /** 대응 진행 한 칸. 되돌림(종결 → 조치중)은 **사유가 필수**다 — 서버가 400 으로 거절한다. */
  const advance = useCallback(
    async (toState: string, backward: boolean) => {
      if (!id) return;
      const send = async (reason: string) => {
        setBusy(toState);
        try {
          await mobilePostWithQuery(mobileEndpoint.response(id), {
            to_state: toState,
            reason,
          });
          message.success(`「${labelOf(RESPONSE_STATE_LABEL, toState)}」 단계로 옮겼습니다.`);
          event.reload();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '처리 단계를 옮기지 못했습니다.');
          throw err; // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
        } finally {
          setBusy('');
        }
      };

      if (!backward) {
        await send('');
        return;
      }

      let reason = '';
      Modal.confirm({
        title: '되돌립니다 — 사유가 필요합니다',
        content: (
          <Input.TextArea
            rows={3}
            placeholder="되돌리는 사유 (필수)"
            onChange={(ev) => {
              reason = ev.target.value;
            }}
          />
        ),
        okText: '되돌리기',
        cancelText: '취소',
        onOk: () => send(reason),
      });
    },
    [id, event],
  );

  /** M3 — 이 이벤트에 달린 현장 회신. 빈 것과 오류를 갈라 그린다. */
  const replies = useDsmResource<{ total: number; replies: FieldReplyRow[] }>(
    () => dsmGet(mobileEndpoint.fieldReplies(id!)),
    [id],
    { enabled: Boolean(id), isEmpty: (v) => (v?.replies?.length ?? 0) === 0 },
  );

  /**
   * M3 — 한 줄을 돌려준다.
   * ★ 질의로 보낸다(본문이면 422 · 인자 없음). 조립은 `mobilePostWithQuery` 한 곳이다.
   */
  const sendFieldReply = useCallback(async () => {
    if (!id) return;
    const text = replyText.trim();
    if (!text) return;
    setBusy('field-reply');
    try {
      await mobilePostWithQuery(mobileEndpoint.fieldReply(id), { text });
      setReplyText('');
      message.success('회신을 보냈습니다.');
      replies.reload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '회신을 보내지 못했습니다.');
    } finally {
      setBusy('');
    }
  }, [id, replyText, replies]);

  const e = event.data;

  return (
    <MobileShell
      title={e ? `#${e.event_id} 현장 상세` : '현장 상세'}
      loadedAt={event.loadedAt}
      onReload={event.reload}
      backTo={mobileRoutes.inbox.path}
    >
      <StateBoundary
        state={event.state}
        reason={event.reason}
        onRetry={event.reload}
        emptyText="이벤트를 찾지 못했습니다."
      >
        {e ? (
          <Space
            direction="vertical"
            size={10}
            style={{ width: '100%' }}
          >
            {/* ① 무엇이 일어났나 */}
            <Card
              size="small"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={6}
                style={{ width: '100%' }}
              >
                <Space
                  size={6}
                  wrap
                >
                  <Tag color={SEVERITY_COLOR[e.severity]}>
                    {SEVERITY_ICON[e.severity]} {labelOf(SEVERITY_LABEL, e.severity)}
                  </Tag>
                  <Text strong>{labelOf(EVENT_TYPE_LABEL, e.event_type)}</Text>
                  {/* ★ [UX-22 · 2026-09-26] 진위 축(`status`) 태그를 내렸다 — 판정과
                      같은 것을 다른 이름으로 부르던 칸이라 한 카드에 둘이 서면
                      사람이 어느 축을 보는지 모른다(GX-COPY §1-4).
                      남은 축은 **처리 단계**(아래 「현장 조치」)와 **판정** 둘이다. */}
                  <Tag>{labelOf(RESPONSE_STATE_LABEL, e.response_state)}</Tag>
                  <VerdictBadge verdict={e.verdict} />
                </Space>
                <Text style={{ fontSize: 13 }}>
                  발생 {relative(e.occurred_at)} ({absolute(e.occurred_at)})
                </Text>
              </Space>
            </Card>

            {/* ② 어디로 가나 */}
            <Card
              size="small"
              title="어디로 가나"
              styles={{ body: { padding: 12 } }}
            >
              <Descriptions
                column={1}
                size="small"
              >
                <Descriptions.Item label="카메라">
                  {e.stream_monitor_name || '이름 없음'}
                </Descriptions.Item>
                <Descriptions.Item label="설치 주소">
                  {/* ★ 없는 것은 없다고 적는다 (D-284) — 빈칸은 「조회 중」과 같아 보인다. */}
                  {e.address || (
                    <Text type="secondary">
                      미입력 — {labelOf(ADDRESS_STATUS_LABEL, e.address_status)}
                    </Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="좌표">
                  {e.lat != null && e.lng != null ? (
                    `${e.lat}, ${e.lng}`
                  ) : (
                    <Text type="secondary">없음</Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
            </Card>

            {/* ③ 무엇을 보나 — 스냅샷 참조 · 구간 티켓 */}
            <Card
              size="small"
              title="무엇을 보나"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={8}
                style={{ width: '100%' }}
              >
                <div>
                  <Text strong>스냅샷</Text>
                  {e.snapshot_path ? (
                    <>
                      <Paragraph
                        copyable={{ text: e.snapshot_path }}
                        style={{ fontSize: 12, marginBottom: 4, wordBreak: 'break-all' }}
                      >
                        {e.snapshot_path}
                      </Paragraph>
                      {/* ★ 그림을 그리지 않는 이유를 적는다. 빈 자리는 「사진이 없다」로 읽힌다.
                          ★ [UX-20 · 2026-09-26] 앞판은 저장소 제품 이름과 내부 경로
                            (`/api/dsm/`)를 백틱째로 화면에 적었다 — 「어디에 없는지」는
                            사용자에게 뜻이 없고, 읽는 사람에게는 우리 서랍의 지도다
                            (GX-COPY §1-3 · §4).
                          (내부 사실 · 화면에 적지 않는다: MinIO 객체 참조이고, 이 바이트를
                           내보내는 라우트가 `/api/dsm/` 에 아직 없다 [실측 2026-09-04].
                           화면이 직접 프리사인드 URL 을 만들면 무계정 링크가 되므로
                           만들지 않았다.) */}
                      <Alert
                        type="info"
                        showIcon
                        message="사진이 있지만 이 화면에서는 아직 볼 수 없습니다"
                        description={
                          <Text style={{ fontSize: 12 }}>
                            사진은 보관되어 있습니다. 휴대전화 화면에서 여는 길이 아직
                            열리지 않았습니다 — 관제 화면에서 확인하십시오.
                          </Text>
                        }
                      />
                    </>
                  ) : (
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      이 이벤트에는 스냅샷 참조가 없습니다.
                    </Paragraph>
                  )}
                </div>

                <div>
                  <Text strong>구간 티켓</Text>
                  <StateBoundary
                    state={clip.state}
                    reason={clip.reason}
                    onRetry={clip.reload}
                    emptyText="이 사건에는 영상 구간 참조가 없습니다 (서버가 404 로 답했습니다 — 고장이 아닙니다)."
                  >
                    {clip.data ? (
                      <Descriptions
                        column={1}
                        size="small"
                      >
                        <Descriptions.Item label="구간">
                          시작 {clip.data.start_offset}s · 길이 {clip.data.duration}s
                        </Descriptions.Item>
                        <Descriptions.Item label="만료">
                          {absolute(clip.data.expires_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="재생">
                          {/* ★ 계약 11조 잠금 — 재생기를 그리지 않는다. 사유를 그대로 적는다. */}
                          <Text type="secondary">
                            {clip.data.playable ? '가능' : '불가'} —{' '}
                            {clip.data.reason || '사유 없음'}
                          </Text>
                        </Descriptions.Item>
                      </Descriptions>
                    ) : null}
                  </StateBoundary>
                </div>
              </Space>
            </Card>

            {/* ④ 무엇을 누르나 — 상태 전이 */}
            <Card
              size="small"
              title="현장 조치"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={8}
                style={{ width: '100%' }}
              >
                {/* ★ [UX-22] 처리 단계 한 줄 — 미처리 → 접수 → 조치 중 → 종결 */}
                <ResponseSteps state={e.response_state} />

                {(e.allowed_next ?? []).length === 0 ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    지금 이 계정이 옮길 수 있는 다음 단계가 없습니다.
                  </Text>
                ) : (
                  <Space
                    direction="vertical"
                    size={8}
                    style={{ width: '100%' }}
                  >
                    {(e.allowed_next ?? []).map((next) => {
                      const backward = e.response_state === 'closed' && next === 'in_progress';
                      return (
                        <Button
                          key={next}
                          block
                          type={backward ? 'default' : 'primary'}
                          danger={backward}
                          loading={busy === next}
                          style={{ minHeight: TOUCH_MIN }}
                          onClick={() => advance(next, backward)}
                        >
                          {backward ? '되돌리기 → ' : ''}
                          {advanceLabel(next)}
                        </Button>
                      );
                    })}
                  </Space>
                )}

                {/* M3 — 현장 회신 한 줄. 「도착 · 사진 한 장 · 한 줄」 중 한 줄이다. */}
                <Card size="small" title={FIELD_REPLY_HEADLINE}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Input.TextArea
                      rows={2}
                      maxLength={500}
                      value={replyText}
                      placeholder="현장에서 본 것을 한 줄로 적습니다."
                      onChange={(ev) => setReplyText(ev.target.value)}
                    />
                    <Button
                      type="primary"
                      block
                      style={{ minHeight: TOUCH_MIN }}
                      loading={busy === 'field-reply'}
                      disabled={replyText.trim().length === 0}
                      onClick={sendFieldReply}
                    >
                      회신 보내기
                    </Button>
                    <StateBoundary
                      state={replies.state}
                      reason={replies.reason}
                      onRetry={replies.reload}
                      emptyText="아직 회신이 없습니다."
                    >
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {(replies.data?.replies ?? []).map((r) => (
                          <Text key={r.reply_id} style={{ fontSize: 12 }}>
                            {r.author_name || '이름 없음'} · {r.text}
                          </Text>
                        ))}
                      </Space>
                    </StateBoundary>
                  </Space>
                </Card>
              </Space>
            </Card>
          </Space>
        ) : null}
      </StateBoundary>
    </MobileShell>
  );
}
