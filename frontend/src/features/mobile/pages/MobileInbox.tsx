/**
 * **M1 — 내게 온 이벤트** (U3 #1 · #19).
 *
 * 이 화면의 정본은 **발송 기록**이다(`GET /api/dsm/deliveries` → K2 `list_deliveries`).
 * 이벤트 목록이 아니다 — 「내게 온 것」은 「일어난 것」의 부분집합이고, 그 부분집합을
 * 정하는 것은 알림 규칙이지 화면이 아니다.
 *
 * ★★ 범위에 대한 정직한 진술 [실측 2026-09-04 · 차선 D]
 *
 *   서버가 **테넌트까지는** 거른다(`@tenant_scoped` + K2 의 `filter_by_group_field`).
 *   그러나 **수신자까지는 못 거른다** — `GET /api/dsm/deliveries` 에 `recipient_id`
 *   /`mine` 인자가 없다. 커널(`list_deliveries`)에는 `recipient_id` 가 이미 있고,
 *   막힌 자리는 App 라우트 한 곳뿐이다.
 *
 *   그래서 이 화면은 **거르지 않는다.** 받아 온 페이지를 자기가 걸러 「내 것」인 척
 *   하면 **페이지 밖 발송은 없는 것이 된다**(DA-04 「필터는 전부 서버에서」). 대신
 *   범위 띠에 지금 무엇을 보고 있는지 적는다. 화면이 거짓말을 하지 않는 쪽이,
 *   화면이 예뻐 보이는 쪽보다 낫다 (D-284 · D-290).
 *
 * ★ 실패한 발송을 숨기지 않는다. K2 는 실패에 `sent_at` 을 찍지 않는다 — 찍으면
 *   F-10 이 거짓으로 달성된다. 화면도 같은 규약을 따라 시각 칸을 「—」로 두고
 *   **사유를 옆에 적는다.**
 *
 * ★ 한 줄을 누르면 목록의 값을 물려주지 않고 **상세를 서버에 다시 묻는다** —
 *   물려 쓰면 문지기가 목록에만 서고 상세에 안 선다(IDOR 이 나는 자리).
 */
import { Alert, Badge, Card, Empty, Segmented, Space, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import StateBoundary from '../../dsm/components/StateBoundary';
import { failureHint } from '../../dsm/copy';
/**
 * ★ [P-123 · UX-31 ① · 턴 O · 차선 C2] **「성공」이 사람에게 갔다는 뜻이 아니다.**
 *   말은 `features/dsm/deliveryOutcome.tsx` 한 곳에서 온다 — 데스크 표와 이 카드가
 *   같은 말을 써야 한 쪽만 고치는 날이 안 온다. 실측·근거는 그 파일 머리말에 있다.
 */
import {
  LOG_CHANNEL_NOTE,
  OUTCOME_LOG_ONLY,
  reachesAPerson,
} from '../../dsm/deliveryOutcome';
import { useDsmResource } from '../../dsm/hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../../dsm/severity';
import { relative, shortAbsolute } from '../../dsm/time';
import { dsmGet, mobileEndpoint } from '../api';
import MobileShell, { TOUCH_MIN } from '../components/MobileShell';
import { startReceiveToAck } from '../metrics';
import { mobileEventDetailPath } from '../routes';
import type { DeliveryPage, EventRow, InboxRow } from '../types';

const { Text } = Typography;

/** 한 화면에 담는 발송 기록 수. 이동 중에는 길게 스크롤하지 않는다. */
/**
 * 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다.
 * ⚠ 이 상수를 고치면 `scripts/capture_screens.py` 의 사본도 **같은 커밋에서** 고친다.
 */
export const HEADLINE = '내게 온 이벤트';

const DELIVERY_LIMIT = 50;

/**
 * 이벤트 속성을 붙이려고 함께 받는 페이지의 크기.
 *
 * ★ 이것은 **거르는 값이 아니라 붙이는 값**이다. 못 붙은 줄은 지우지 않고
 *   「이 페이지에서 못 찾음」이라고 적는다 — 지우면 발송 기록 수가 조용히 줄고,
 *   줄어든 화면은 「알림이 그만큼만 갔다」로 읽힌다.
 */
const EVENT_LOOKUP_LIMIT = 200;

interface EventPage {
  total?: number;
  events?: EventRow[];
}

/**
 * 「처리함」 한 줄 — 사건 속성 + 내 마지막 회신(종류·시각·앞 120자).
 * 서버(`GET /api/dsm/me/handled-events`)가 **내 회신**으로 좁혀 낸다 — 화면은 거르지 않는다.
 */
interface HandledRow extends EventRow {
  last_reply_at: string | null;
  last_reply_kind: string;
  last_reply_text: string;
}

interface HandledPage {
  total: number;
  events: HandledRow[];
}

type InboxTab = 'inbox' | 'handled';

export default function MobileInbox() {
  const navigate = useNavigate();

  const deliveries = useDsmResource<DeliveryPage>(
    () => dsmGet<DeliveryPage>(mobileEndpoint.deliveries, { limit: DELIVERY_LIMIT }),
    [],
    { isEmpty: (v) => (v?.deliveries?.length ?? 0) === 0 },
  );

  //: 이벤트 속성은 **부수적**이다. 못 받아도 M1 은 발송 기록으로 선다 —
  //: 그래서 이 자원의 오류가 화면 전체를 빨갛게 만들지 않는다.
  const events = useDsmResource<EventPage>(
    () => dsmGet<EventPage>(mobileEndpoint.events, { limit: EVENT_LOOKUP_LIMIT }),
    [],
  );

  const eventById = useMemo(() => {
    const map = new Map<number, EventRow>();
    (events.data?.events ?? []).forEach((e) => map.set(e.event_id, e));
    return map;
  }, [events.data]);

  const rows: InboxRow[] = useMemo(
    () =>
      (deliveries.data?.deliveries ?? []).map((d) => ({
        delivery: d,
        event: eventById.get(d.event_id) ?? null,
      })),
    [deliveries.data, eventById],
  );

  /**
   * 편리성 #5 — **「받았다」의 시각.** 발송 기록이 이 목록에 처음 뜨는 순간이 이
   * 사람에게 「받았다」다(`metrics.ts::startReceiveToAck` 머리말). 다시 읽혀도(폴링·
   * 새로고침) 같은 사건은 다시 시작하지 않는다 — 값은 이 브라우저 안에만 남고
   * 서버로 가지 않는다.
   */
  useEffect(() => {
    (deliveries.data?.deliveries ?? []).forEach((d) => {
      startReceiveToAck(String(d.event_id));
    });
  }, [deliveries.data]);

  // ★ [턴 T · P-164 U3] 「처리함」 — 내가 현장 회신을 낸 사건. **서버가 좁힌다.**
  const [tab, setTab] = useState<InboxTab>('inbox');
  const handled = useDsmResource<HandledPage>(
    () => dsmGet<HandledPage>(mobileEndpoint.handledEvents, { limit: DELIVERY_LIMIT }),
    [],
    { isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
  );

  const reload = useCallback(() => {
    deliveries.reload();
    events.reload();
    handled.reload();
  }, [deliveries, events, handled]);

  const total = deliveries.data?.total ?? 0;
  const failed = rows.filter((r) => !r.delivery.succeeded).length;

  return (
    <MobileShell
      title={HEADLINE}
      loadedAt={deliveries.loadedAt}
      onReload={reload}
      banner={
        <Space
          direction="vertical"
          size={6}
          style={{ width: '100%' }}
        >
          {/* ★ 탭 둘 — 「내게 온 것」과 「내가 처리한 것」. 처리함은 서버가 내 회신으로 좁힌다. */}
          <Segmented
            block
            value={tab}
            onChange={(v) => setTab(v as InboxTab)}
            options={[
              { label: '내게 온 이벤트', value: 'inbox' },
              { label: `처리함 ${handled.data?.total ?? 0}`, value: 'handled' },
            ]}
            data-gx="inbox-tabs"
          />
          {tab === 'handled' ? (
            <Text style={{ fontSize: 13 }} data-gx="handled-scope">
              내가 현장 회신을 낸 사건 {handled.data?.total ?? 0}건 (이 페이지 · 최대 {DELIVERY_LIMIT}) — 최근 회신 순
            </Text>
          ) : null}
          {tab === 'inbox' ? (
          <>
          {/* ★ 범위를 먼저 적는다 — 무엇을 보고 있는지 모르는 목록은 근거가 아니다. */}
          {/* ★ [UX-20 · 2026-09-26] 앞판은 서버 인자 이름(`mine`)과 라우트
              (`GET /api/dsm/deliveries`)를 백틱째로 화면에 적었다 — 백틱은 렌더되지
              않고 그대로 보이고, 라우트 이름은 사용자에게 뜻이 없다(GX-COPY §4).
              **범위를 먼저 적는다**는 규율은 그대로 두고 말만 바꿨다.
              (내부 사실 · 화면에 적지 않는다: 수신자까지 좁히는 인자 `mine` 이
               `GET /api/dsm/deliveries` 에 아직 없다 [실측 2026-09-04]. 화면이 받아서
               스스로 거르면 페이지 밖 발송이 없는 것이 되므로 거르지 않는다.) */}
          <Alert
            type="warning"
            showIcon
            message="이 목록은 우리 기관에 나간 발송 전부입니다"
            description={
              <Text style={{ fontSize: 12 }}>
                아직 「나에게 온 것」만 골라 보여 주지 못합니다. 화면이 임의로 줄이면
                안 보이는 발송이 생기므로, 줄이지 않고 전부 보여 드립니다.
              </Text>
            }
          />
          <Space size={8}>
            <Badge
              count={total}
              showZero
              style={{ backgroundColor: total > 0 ? '#1677ff' : '#999' }}
            />
            {/* ★ `total` 은 **이 페이지의 수**다 [실측] — 라우트가 `len(rows)` 를 낸다.
                전체 수라고 적으면 51번째 발송이 없는 것이 된다. */}
            <Text style={{ fontSize: 13 }}>
              발송 기록 {total}건 (이 페이지 · 최대 {DELIVERY_LIMIT})
            </Text>
            {failed > 0 ? (
              <Tag color="red">발송 실패 {failed}건</Tag>
            ) : (
              <Tag color="green">발송 실패 0건</Tag>
            )}
          </Space>
          {events.state === 'error' || events.state === 'forbidden' ? (
            /*
              ★★ [P-78 ① · 2026-09-06 턴 H] **여기가 여섯 번째 자리였다.**
                `StateBoundary` 를 고쳐도 이 상자는 안 고쳐졌다 — 상자를 손으로
                한 번 더 짠 자리이기 때문이다. [실측] 이 줄에 「Request failed with
                status code」가 그대로 떴다. 좁은 문 하나로 다 막았다고 믿은 순간
                문 밖에 서 있던 자리다.
              ★ 제목이 「불러오지 못했습니다」로 시작한다 — 이 화면은 발송 기록은
                그렸으므로 통째 실패가 아니고, 그래서 **무엇을 못 받았는지**를 잇는다.
            */
            <Alert
              type="info"
              showIcon
              message={
                events.state === 'forbidden'
                  ? '이벤트 속성에 대한 권한이 없습니다 — 발송 기록만 보입니다.'
                  : '이벤트 속성을 불러오지 못했습니다 — 발송 기록만 보입니다.'
              }
              description={failureHint(events.status)}
            />
          ) : null}
          </>
          ) : null}
        </Space>
      }
    >
      {tab === 'handled' ? (
        <StateBoundary
          state={handled.state}
          reason={handled.reason}
          status={handled.status}
          onRetry={handled.reload}
          emptyText="아직 내가 회신한 사건이 0건입니다. (사건 상세의 「현장 회신」을 보내면 여기에 쌓입니다.)"
        >
          <Space direction="vertical" size={8} style={{ width: '100%' }} data-gx="handled-list">
            {(handled.data?.events ?? []).map((e) => (
              <Card
                key={e.event_id}
                size="small"
                hoverable
                role="button"
                tabIndex={0}
                onClick={() => navigate(mobileEventDetailPath(e.event_id))}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') navigate(mobileEventDetailPath(e.event_id));
                }}
                style={{ minHeight: TOUCH_MIN * 1.6, cursor: 'pointer' }}
                styles={{ body: { padding: 12 } }}
              >
                <Space direction="vertical" size={4} style={{ width: '100%' }}>
                  <Space size={6} wrap>
                    <Tag color={SEVERITY_COLOR[e.severity]}>
                      {SEVERITY_ICON[e.severity]} {labelOf(SEVERITY_LABEL, e.severity)}
                    </Tag>
                    <Text strong>{labelOf(EVENT_TYPE_LABEL, e.event_type)}</Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>#{e.event_id}</Text>
                    <Tag>{labelOf(RESPONSE_STATE_LABEL, e.response_state)}</Tag>
                  </Space>
                  <Text style={{ fontSize: 13 }}>{e.stream_monitor_name || '카메라 미상'}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    발생 {relative(e.occurred_at)} ({shortAbsolute(e.occurred_at)})
                    {e.last_reply_at ? ` · 내 회신 ${shortAbsolute(e.last_reply_at)}` : ''}
                  </Text>
                  <Text style={{ fontSize: 12 }}>
                    [{e.last_reply_kind}] {e.last_reply_text || '(본문 없음)'}
                  </Text>
                </Space>
              </Card>
            ))}
          </Space>
        </StateBoundary>
      ) : (
      <StateBoundary
        state={deliveries.state}
        reason={deliveries.reason} status={deliveries.status}
        onRetry={deliveries.reload}
        emptyText="이 테넌트에 남은 발송 기록이 0건입니다. (알림이 실패한 것이 아니라, 나간 알림이 없습니다.)"
      >
        <Space
          direction="vertical"
          size={8}
          style={{ width: '100%' }}
        >
          {rows.length === 0 ? (
            <Empty
              description="발송 기록 0건"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : null}

          {rows.map(({ delivery, event }) => {
            const severity = event?.severity ?? '';
            return (
              <Card
                key={delivery.delivery_id}
                size="small"
                hoverable
                role="button"
                tabIndex={0}
                onClick={() => navigate(mobileEventDetailPath(delivery.event_id))}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') {
                    navigate(mobileEventDetailPath(delivery.event_id));
                  }
                }}
                style={{ minHeight: TOUCH_MIN * 1.6, cursor: 'pointer' }}
                styles={{ body: { padding: 12 } }}
              >
                <Space
                  direction="vertical"
                  size={4}
                  style={{ width: '100%' }}
                >
                  <Space
                    size={6}
                    wrap
                  >
                    {severity ? (
                      <Tag color={SEVERITY_COLOR[severity]}>
                        {SEVERITY_ICON[severity]} {labelOf(SEVERITY_LABEL, severity)}
                      </Tag>
                    ) : (
                      <Tag>등급 미상</Tag>
                    )}
                    <Text strong>
                      {event ? labelOf(EVENT_TYPE_LABEL, event.event_type) : '유형 미상'}
                    </Text>
                    <Text
                      type="secondary"
                      style={{ fontSize: 12 }}
                    >
                      #{delivery.event_id}
                    </Text>
                  </Space>

                  <Space
                    size={6}
                    wrap
                  >
                    <Text style={{ fontSize: 13 }}>
                      {event?.stream_monitor_name || '카메라 미상'}
                    </Text>
                    {event ? (
                      <Tag>{labelOf(RESPONSE_STATE_LABEL, event.response_state)}</Tag>
                    ) : (
                      // ★ 「없음」이 아니라 「이 페이지에서 못 찾음」이다 — 다른 사실이다.
                      <Tag color="default">이벤트 속성 미조회</Tag>
                    )}
                  </Space>

                  <Space
                    size={6}
                    wrap
                  >
                    <Text
                      type="secondary"
                      style={{ fontSize: 12 }}
                    >
                      발생 {event ? relative(event.occurred_at) : '—'}
                      {event ? ` (${shortAbsolute(event.occurred_at)})` : ''}
                    </Text>
                    <Text
                      type="secondary"
                      style={{ fontSize: 12 }}
                    >
                      · 채널 {delivery.channel}
                    </Text>
                    {delivery.succeeded && !reachesAPerson(delivery.channel) ? (
                      /*
                        ★★ [P-123 · UX-31 ①] **여기 「발송 12:03」이라고 적혀 있었다.**
                          채널이 `log` 인 줄에도 그렇게 적었고, 그 시각은 「사람이 받은
                          시각」으로 읽힌다. 실제로는 로그 한 줄이 남은 시각이다 —
                          [실측 2026-09-10] 같은 시각 메일함 0통. 그래서 시각 앞에
                          **무엇이 일어났는지**를 먼저 적는다.
                      */
                      <Text
                        type="warning"
                        style={{ fontSize: 12 }}
                        title={LOG_CHANNEL_NOTE}
                      >
                        · {OUTCOME_LOG_ONLY} {shortAbsolute(delivery.sent_at)}
                      </Text>
                    ) : delivery.succeeded ? (
                      <Text
                        type="secondary"
                        style={{ fontSize: 12 }}
                      >
                        {/* ★ 이 라우트는 이름이 아니라 `recipient_id` 만 낸다 —
                            없으면 「받는 사람 없음」이라 적고, 이름을 지어내지 않는다. */}
                        · 발송 {shortAbsolute(delivery.sent_at)}
                        {delivery.recipient_id === null ? ' · 받는 사람 없음' : ''}
                      </Text>
                    ) : (
                      // ★ 실패는 시각 칸이 「—」다. 0초가 아니다 — 못 보낸 것은 빠른 것이 아니다.
                      <Text
                        type="danger"
                        style={{ fontSize: 12 }}
                      >
                        · 발송 실패 — {delivery.failure_reason || '사유 없음'}
                      </Text>
                    )}
                  </Space>
                </Space>
              </Card>
            );
          })}
        </Space>
      </StateBoundary>
      )}
    </MobileShell>
  );
}
