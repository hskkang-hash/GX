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
 * ★★ [P-121 · 2026-09-10 턴 O · 실측] **사진을 그린다. 문은 이미 서 있었다.**
 *
 *   앞판의 주석은 「스냅샷 바이트를 내보내는 라우트가 없다」였다(2026-09-04).
 *   그 뒤 P-25 가 `GET /api/dsm/events/{id}/snapshot` 을 세웠고 — 인증 뒤에 서고
 *   소인이 찍혀 나오는, 무계정 링크가 아닌 문이다 — 그런데 **이 화면은 그 사실을
 *   모른 채로 남았다.** 그래서 화면에는 이렇게 떠 있었다:
 *
 *       「휴대전화 화면에서 여는 길이 아직 열리지 않았습니다 —
 *         관제 화면에서 확인하십시오.」
 *
 *   두 문장 다 거짓이었다. 길은 열려 있었고, **관제 화면도 같은 이유로 사진을
 *   못 그리고 있었다**(P-121 ① — `res.data` 가 Blob 이 아니었다). 즉 이 안내는
 *   고장 하나를 가리키며 **다른 고장으로 사람을 보내는 표지판**이었다.
 *   현장으로 가는 사람이 차를 세우고 관제에 전화를 건다 — 거기서도 못 본다.
 *
 *   지운 것은 문장이고, 그 자리에 선 것은 `EventSnapshot` — 관제 화면과 **같은
 *   부품**이다. 두 벌로 두지 않는다: 갈리는 쪽은 언제나 오류 처리다.
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
 *
 * ★★ **지도 앱 링크를 그렸다** [P-141 · 2026-09-15 턴 Q · 차선 U3].
 *
 *   UX-45 원문: 「주소 · 지도 앱 링크(`geo:`/카카오맵 URL)」. 전화 버튼과 달리
 *   이 칸은 **있는 칸으로만** 선다 — `e.lat`·`e.lng`(좌표, F-09 상세가 이미 낸다)와
 *   `e.address`(사람이 읽는 위치, FX-5)가 그것이다. 새 서버 칸을 열지 않았다.
 *
 *   ★ `geo:` 를 안 쓰고 **카카오맵 웹 링크**로 갔다. `geo:` 는 iOS Safari 가
 *     알아듣지 못한다(지도 앱이 없으면 그냥 죽은 링크) — 이동 중인 사람의 기기가
 *     무엇인지 화면은 모른다. 카카오맵 링크는 앱이 있으면 앱을, 없으면 웹을 연다 —
 *     두 플랫폼에서 **똑같이 산다.**
 *   ★ 좌표가 있으면 지도에 **정확한 점**을 찍는다(`map/link/map`). 좌표가 없고
 *     주소만 있으면 **검색**으로 연다(`map/link/search`) — 검색은 점보다 부정확하지만
 *     주소마저 없는 것보다는 낫다. 둘 다 없으면 링크 자체를 그리지 않는다
 *     (`address_status` 문장이 이미 그 부재를 적고 있다 — 두 번 말하지 않는다).
 *   ★ 새 탭/외부 앱으로 연다(`target="_blank"`) — 이 화면을 잃지 않는다. 이동 중인
 *     사람이 지도를 본 뒤 다시 돌아와 다음 버튼을 눌러야 한다.
 */
import { Button, Card, Collapse, Descriptions, Input, Modal, Space, Tag, Typography, message } from 'antd';
import { useCallback, useState } from 'react';
import { useParams } from 'react-router-dom';

import EventSnapshot from '../../dsm/components/EventSnapshot';
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
import {
  dsmGet,
  DsmApiError,
  intentKey,
  mobileEndpoint,
  mobilePostWithQueryOnce,
} from '../api';
import { userFacingError } from '@/features/dsm/copy';
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

/** 지도 버튼의 말. GX-COPY_v1.md §5 「2026-09-15 턴 Q 추가」와 같은 문구다. */
export const MAP_LINK_LABEL = '지도에서 보기';

/**
 * 사건 위치를 여는 카카오맵 링크를 만든다. **있는 칸만** 쓴다 — 지어내지 않는다.
 * 좌표가 있으면 점(`map/link/map`), 좌표는 없고 주소만 있으면 검색(`map/link/search`),
 * 둘 다 없으면 `null`(화면은 아무것도 그리지 않는다).
 */
export function mapLinkUrl(
  lat: number | null | undefined,
  lng: number | null | undefined,
  address: string | null | undefined,
): string | null {
  if (lat != null && lng != null) {
    return `https://map.kakao.com/link/map/사건위치,${lat},${lng}`;
  }
  const trimmed = address?.trim();
  if (trimmed) {
    return `https://map.kakao.com/link/search/${encodeURIComponent(trimmed)}`;
  }
  return null;
}

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
          // ★ **접수·처리 단계 — 멱등 키를 싣는 문 ②**(휴대전화 쪽).
          //   이동 중인 사람의 화면이라 두 번 눌릴 확률이 가장 높은 자리다.
          await mobilePostWithQueryOnce(
            mobileEndpoint.response(id),
            { to_state: toState, reason },
            intentKey(`m.response:${id}:${toState}`),
          );
          message.success(`「${labelOf(RESPONSE_STATE_LABEL, toState)}」 단계로 옮겼습니다.`);
          event.reload();
        } catch (err) {
          message.error(
            userFacingError('MobileEventDetail.advance', err, '처리 단계를 옮기지 못했습니다.'),
          );
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
      // ★ **현장 회신 — 멱등 키를 싣는 문 ③.**
      await mobilePostWithQueryOnce(
        mobileEndpoint.fieldReply(id),
        { text },
        intentKey(`m.field-reply:${id}:${text}`),
      );
      setReplyText('');
      message.success('회신을 보냈습니다.');
      replies.reload();
    } catch (err) {
      message.error(
        userFacingError('MobileEventDetail.fieldReply', err, '회신을 보내지 못했습니다.'),
      );
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
        reason={event.reason} status={event.status}
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
              {/* ★ [P-141 · 턴 Q] 좌표 또는 주소가 있을 때만 그린다 — 없는 칸에
                  손잡이를 그리지 않는다(이 화면이 전화 버튼에서 이미 지킨 규약). */}
              {(() => {
                const href = mapLinkUrl(e.lat, e.lng, e.address);
                return href ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    <Button block style={{ minHeight: TOUCH_MIN, marginTop: 8 }}>
                      {MAP_LINK_LABEL}
                    </Button>
                  </a>
                ) : null;
              })()}
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
                  {/* ★★ [P-121] **거짓 표지판을 지우고 사진을 그린다.**
                      「관제 화면에서 확인하십시오」는 열려 있는 문을 닫혔다고 말하면서
                      **같이 고장 나 있던 화면**으로 사람을 보내고 있었다.
                      ★ 부품은 관제 화면과 **한 벌**이다(`EventSnapshot`). 없다 · 못 받았다 ·
                        받았다 셋을 가르는 규율도 거기 한 곳에 있다.
                      ★ 경로 문자열은 **접었다.** 이동 중인 사람의 화면에서 첫 자리는
                        사진이지 객체 키가 아니다 — 키는 인계·문의에 쓰이므로 버리지 않고
                        「참조 보기」 아래에 둔다. */}
                  {e.snapshot_path ? (
                    <>
                      <div style={{ marginTop: 6 }}>
                        <EventSnapshot
                          eventId={e.event_id}
                          snapshotPath={e.snapshot_path}
                          compact
                          alt="현장 스냅샷"
                        />
                      </div>
                      <Collapse
                        ghost
                        size="small"
                        items={[{
                          key: 'ref',
                          label: <Text style={{ fontSize: 12 }}>참조 보기</Text>,
                          children: (
                            <Paragraph
                              copyable={{ text: e.snapshot_path }}
                              style={{ fontSize: 12, marginBottom: 0, wordBreak: 'break-all' }}
                            >
                              {e.snapshot_path}
                            </Paragraph>
                          ),
                        }]}
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
                    reason={clip.reason} status={clip.status}
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
                      reason={replies.reason} status={replies.status}
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
