/**
 * **M1 — 내게 온 이벤트** (U3 #1 · #19).
 *
 * 이 화면의 정본은 **발송 기록**이다(`GET /api/dsm/deliveries` → K2 `list_deliveries`).
 * 이벤트 목록이 아니다 — 「내게 온 것」은 「일어난 것」의 부분집합이고, 그 부분집합을
 * 정하는 것은 알림 규칙이지 화면이 아니다.
 *
 * ★★ 범위에 대한 정직한 진술 [갱신 2026-09-19 · 턴 W · 차선 U3 — 아래 ㉠]
 *
 *   서버가 **테넌트까지** 거르고(`@tenant_scoped` + K2 의 `filter_by_group_field`),
 *   이제 **수신자까지도** 거른다 — `GET /api/dsm/deliveries` 의 `mine=true` 다
 *   (`apps/dsm/api.py:750` → `services.delivery_history` → 커널의 `recipient_id`).
 *
 *   ⚠ **이 자리에 2026-09-04 자 실측이 「그런 인자는 없다」로 남아 있었고, 그
 *     낡은 문장이 화면에 노랑 경고로까지 떠 있었다** — 「아직 나에게 온 것만 골라
 *     보여 주지 못합니다」. 서버는 그 사이에 열렸는데(차선 D 가 넘긴 한 줄이
 *     들어갔다) 화면만 옛말을 하고 있었다. 못 하는 것이 아니라 **안 쓰던 것**이다.
 *     낡은 실측은 지우지 않고 **날짜와 함께 갱신한다** — 이것이 그 갱신이다.
 *
 *   화면은 여전히 **자기가 거르지 않는다.** `mine` 은 질의로 나가고 서버가 좁힌
 *   페이지를 받는다. 받아 온 페이지를 자기가 걸러 「내 것」인 척하면 **페이지 밖
 *   발송은 없는 것이 된다**(DA-04 「필터는 전부 서버에서」). 그리고 범위 띠는
 *   지금 무엇을 보고 있는지 **늘** 적는다 (D-284 · D-290).
 *
 * ★ [㉡ 턴 W · P-188] **사건 하나에 카드 한 장, 채널은 배지다.** 종전에는 같은
 *   사건의 발송이 채널마다 카드 한 장씩이라 목록이 부풀었다. 묶되 **정보를 잃지
 *   않는다** — 채널 줄을 접지 않고, 실패를 맨 위에 두고, 머리줄에 「발송 실패 N」을
 *   단다. 묶는 일이 실패를 숨기는 일이 되면 조용한 실패를 새로 만든 것이다.
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
import type { DeliveryPage, EventRow, MobileDeliveryRow } from '../types';

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

/**
 * ㉡ 사건 하나 = 카드 한 장. `deliveries` 는 **그 사건에 나간 발송 전부**다
 * (채널마다 한 줄) — 줄여서 담지 않는다. `failedCount` 는 그중 실패한 수다.
 */
interface EventGroup {
  eventId: number;
  event: EventRow | null;
  deliveries: MobileDeliveryRow[];
  failedCount: number;
}

/**
 * 채널 한 줄의 **결과 색**. 셋을 다른 색으로 둔다 — 「성공」과 「로그에만 남음」을
 * 같은 색으로 그리면 F-10 이 거짓으로 달성된다(`deliveryOutcome.tsx` 머리말).
 */
function channelTone(d: MobileDeliveryRow): { color: string; mark: string } {
  if (!d.succeeded) return { color: 'red', mark: '✕' };
  if (!reachesAPerson(d.channel)) return { color: 'orange', mark: '▲' };
  return { color: 'green', mark: '✓' };
}

export default function MobileInbox() {
  const navigate = useNavigate();

  /**
   * ㉠ **「나만 거르기」 — 서버가 거른다** (턴 W · 차선 U3 · P-188).
   *
   * ★★ [실측 2026-09-19] 이 화면은 **있는 문을 안 쓰고 있었다.** 위 머리말과
   *   `features/mobile/api.ts` 머리말이 「`GET /api/dsm/deliveries` 에 `mine` 이 없다」고
   *   적어 둔 것은 **2026-09-04 의 실측**이고, 그 뒤 서버가 열렸다:
   *     `backend/apps/dsm/api.py:750`   `mine: bool = False`
   *     `backend/apps/dsm/services.py`  `recipient_id = actor.pk if mine else None`
   *   낡은 실측이 화면에 경고 상자로 남아 「못 한다」고 사용자에게 말하고 있었다.
   *
   * ★ **읽기 질의 인자다** — 새 라우트도, 새 쓰기 문도 만들지 않았다. method·path 가
   *   그대로이므로 진입면이 늘지 않는다.
   * ★ 「나」가 누구인지는 **서버가 안다.** 사번을 보내지 않는다 — 보내면 남의 사번으로
   *   남의 수신 이력을 물을 수 있고, 그 라우트의 사유(「수신자 주소가 새면 안 된다」)가
   *   막으려는 것이 바로 그것이다.
   * ★ 화면은 여전히 **자기가 거르지 않는다.** `mine` 은 질의로 나가고 서버가 좁힌
   *   페이지를 받는다 — 화면이 걸렀다면 페이지 밖 발송이 없는 것이 된다(DA-04).
   *
   * 기본값이 `true` 인 이유: 이 화면의 이름이 「내게 온 이벤트」다. 기관 전체는
   *   한 번 눌러서 넓히고, **지금 무엇을 보고 있는지는 범위 띠가 늘 적는다.**
   */
  const [mine, setMine] = useState(true);

  const deliveries = useDsmResource<DeliveryPage>(
    () => dsmGet<DeliveryPage>(mobileEndpoint.deliveries, { limit: DELIVERY_LIMIT, mine }),
    //: ⚠ `mine` 이 의존성에 없으면 토글이 **그림만 바뀌고 다시 안 묻는다** —
    //:   그것이 바로 「회색을 초록으로 그리는」 자리다.
    [mine],
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

  /**
   * ㉡ **사건 하나에 한 장** (턴 W · 차선 U3 · P-188).
   *
   * 종전에는 같은 사건의 발송이 채널마다 **카드 한 장씩**이었다 — 문자·메일·웹푸시·
   * 로그 넷이 나간 사건 하나가 목록에서 네 줄을 먹었고, 스무 건이면 여든 줄이었다.
   * 이동 중에 엄지로 스크롤하는 화면에서 그것은 「못 보는 목록」이다.
   *
   * ⚠⚠ **줄을 합치면서 정보를 잃지 않는다.** 실패한 채널이 성공한 채널 뒤에 숨으면
   *   그건 조용한 실패를 **새로 만든 것**이다. 그래서 세 가지를 못 박는다:
   *
   *     ① 채널 줄을 **접지 않는다.** 한 장 안에 그 사건의 발송이 **전부** 한 줄씩 있다
   *        — 배지만 그리고 나머지를 감추지 않는다.
   *     ② **실패를 맨 위로** 올린다(아래 `sort`). 성공 뒤에 오지 않는다.
   *     ③ 카드 머리에 **「발송 실패 N」 빨강 배지**를 단다 — 카드를 안 읽어도
   *        실패가 있다는 사실이 먼저 보인다.
   *
   * ★ 묶는 열쇠는 `event_id` 다. 이벤트 속성(`event`)은 **부수적**이라 `null` 이어도
   *   묶음은 선다 — 「이 페이지에서 못 찾음」이라고 적을 뿐이다.
   * ★ 서버가 준 **순서를 뒤집지 않는다.** 처음 나온 사건이 먼저다(Map 의 삽입 순서).
   */
  const groups: EventGroup[] = useMemo(() => {
    const byEvent = new Map<number, EventGroup>();
    (deliveries.data?.deliveries ?? []).forEach((d) => {
      let group = byEvent.get(d.event_id);
      if (!group) {
        group = {
          eventId: d.event_id,
          event: eventById.get(d.event_id) ?? null,
          deliveries: [],
          failedCount: 0,
        };
        byEvent.set(d.event_id, group);
      }
      group.deliveries.push(d);
      if (!d.succeeded) group.failedCount += 1;
    });
    //: ② 실패가 먼저다. `succeeded` 는 boolean 이라 `Number()` 로 0/1 을 만든다
    //:   — 실패(false→0)가 성공(true→1)보다 앞선다.
    byEvent.forEach((group) => {
      group.deliveries.sort((a, b) => Number(a.succeeded) - Number(b.succeeded));
    });
    return [...byEvent.values()];
  }, [deliveries.data, eventById]);

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
  //: ⚠ **발송 수로 센다 — 카드 수가 아니다.** ㉡ 이 사건을 한 장으로 묶었으므로
  //:   카드로 세면 한 사건에서 채널 셋이 실패해도 「1건」이 된다. 실패의 분모는
  //:   언제나 발송이다.
  const failed = (deliveries.data?.deliveries ?? []).filter((d) => !d.succeeded).length;

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
          {/* ★ [UX-20 · 2026-09-26] 앞판은 서버 인자 이름(`mine`)과 라우트를 백틱째로
              화면에 적었다 — 백틱은 렌더되지 않고 그대로 보인다(GX-COPY §4).
              **범위를 먼저 적는다**는 규율은 그대로 두고 말만 쓴다. */}
          {/* ㉠ [턴 W · U3] 종전 이 자리에는 노랑 경고가 있었다 —
              「아직 나에게 온 것만 골라 보여 주지 못합니다」. 그 문장은 **2026-09-04
              의 실측**이었고 그 뒤 서버가 열렸다. 못 하는 것이 아니라 **안 쓰고
              있던 것**이라, 경고를 지우고 손잡이를 단다. */}
          <Segmented
            block
            value={mine ? 'mine' : 'tenant'}
            onChange={(v) => setMine(v === 'mine')}
            options={[
              { label: '내게 온 것만', value: 'mine' },
              { label: '기관 전체', value: 'tenant' },
            ]}
            data-gx="inbox-mine"
          />
          <Text
            style={{ fontSize: 12 }}
            data-gx="inbox-scope"
          >
            {mine
              ? '지금 보는 것: 나에게 간 발송만 (서버가 골라 줍니다).'
              : '지금 보는 것: 우리 기관에 나간 발송 전부 (내게 오지 않은 것도 있습니다).'}
          </Text>
          <Space size={8} wrap>
            <Badge
              count={total}
              showZero
              style={{ backgroundColor: total > 0 ? '#1677ff' : '#999' }}
            />
            {/* ★ `total` 은 **이 페이지의 수**다 [실측] — 라우트가 `len(rows)` 를 낸다.
                전체 수라고 적으면 51번째 발송이 없는 것이 된다.
              ★ [㉡] 이제 **사건 수**도 함께 적는다 — 카드 수와 발송 수가 다르므로,
                사건 수만 적으면 「발송이 그만큼만 나갔다」로 읽힌다(분모가 바뀐다). */}
            <Text style={{ fontSize: 13 }}>
              사건 {groups.length}건 · 발송 기록 {total}건 (이 페이지 · 최대 {DELIVERY_LIMIT})
            </Text>
            {/*
              ★★ [P-200 · 턴 X · U3] **이 배지가 거짓말을 하고 있었다 — 수가 아니라 단서가 없어서.**

                [실측 2026-09-20 · 눌러서] 기관 전체에 발송 실패가 **하나 있는데**
                (사건 #4819 · `email` · `-occurred_at` 정렬에서 **228위/229**)
                화면은 **「발송 실패 0건」**이라고 적고 있었다. 화면이 묻는 것은
                `limit=50` 한 쪽뿐이고 그 쪽 안에는 실패가 없기 때문이다.

                ⚠ 그 0 은 **틀린 수가 아니다. 다른 질문의 답이다** —
                  「이 페이지에 실패가 몇 건인가」의 답이 0 이고,
                  사람은 그것을 「우리 기관에 실패가 몇 건인가」로 읽는다.
                  바로 윗줄(셈 줄)은 이미 「이 페이지 · 최대 50」이라 **정직한데**
                  배지만 그 단서를 안 달고 있었다. 그래서 **단서를 단다** —
                  수를 바꾸는 것이 아니라 **그 수가 무엇을 센 것인지 말하게 한다.**

              ★ 두 살림을 가른다 — 한 문장으로 덮으면 이번엔 **반대쪽이 거짓말**이 된다:
                · `total < DELIVERY_LIMIT` … 이 쪽이 **전부**다. 뒤에 아무것도 없으므로
                  「실패 0건」은 이 범위에 대한 **온전한 답**이고, 거기에 「이 페이지」를
                  붙이면 있지도 않은 뒷장을 암시해 멀쩡한 초록을 흐린다.
                · `total >= DELIVERY_LIMIT` … 쪽이 **꽉 찼다**. 뒤가 있는지 화면은 모른다.
                  이때만 범위를 밝히고 **못 본 것이 있다고 말한다.**

              ★ **기능은 안 넣었다** (조율자 판정 2026-09-20). 서버에는 이미
                `succeeded=false` 인자가 있고 [실측] 그 1건을 정확히 내주지만,
                화면이 그것을 보내게 하는 것은 **다음 턴 몫**이다 — 회귀를 재는 턴에
                새 변수를 얹지 않는다. 지금 닫는 것은 **거짓말 하나**뿐이다.
            */}
            {total >= DELIVERY_LIMIT ? (
              <Tag
                color={failed > 0 ? 'red' : 'orange'}
                data-gx="inbox-failed-summary"
                data-gx-scope="page"
              >
                이 페이지에 발송 실패 {failed}건 · 뒤쪽은 아직 못 봤습니다
              </Tag>
            ) : (
              <Tag
                color={failed > 0 ? 'red' : 'green'}
                data-gx="inbox-failed-summary"
                data-gx-scope="all"
              >
                발송 실패 {failed}건
              </Tag>
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
        emptyText={
          mine
            ? '내게 온 발송이 이 페이지에 0건입니다. (기관 전체에는 더 있을 수 있습니다 — 위의 「기관 전체」를 눌러 보십시오.)'
            : '이 테넌트에 남은 발송 기록이 0건입니다. (알림이 실패한 것이 아니라, 나간 알림이 없습니다.)'
        }
      >
        <Space
          direction="vertical"
          size={8}
          style={{ width: '100%' }}
          data-gx="inbox-list"
        >
          {groups.length === 0 ? (
            <Empty
              description={mine ? '내게 온 발송 0건' : '발송 기록 0건'}
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : null}

          {/*
            ㉡ **사건 하나에 카드 한 장 · 채널은 배지.**
            한 장 안에 그 사건의 발송이 **전부** 한 줄씩 있다 — 실패가 맨 위다.
          */}
          {groups.map((group) => {
            const { event } = group;
            const severity = event?.severity ?? '';
            return (
              <Card
                key={group.eventId}
                size="small"
                hoverable
                role="button"
                tabIndex={0}
                onClick={() => navigate(mobileEventDetailPath(group.eventId))}
                onKeyDown={(ev) => {
                  if (ev.key === 'Enter' || ev.key === ' ') {
                    navigate(mobileEventDetailPath(group.eventId));
                  }
                }}
                style={{ minHeight: TOUCH_MIN * 1.6, cursor: 'pointer' }}
                styles={{ body: { padding: 12 } }}
                data-gx="inbox-event-card"
                data-gx-failed={group.failedCount}
              >
                <Space
                  direction="vertical"
                  size={4}
                  style={{ width: '100%' }}
                >
                  <Space size={6} wrap>
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
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      #{group.eventId}
                    </Text>
                    {/*
                      ⚠⚠ ③ **실패는 카드를 안 읽어도 먼저 보인다.** 줄을 묶는 일이
                        실패를 성공 뒤에 숨기는 일이 되면 안 된다 — 그건 조용한 실패를
                        새로 만든 것이다. 그래서 머리줄에 빨강 배지를 단다.
                    */}
                    {group.failedCount > 0 ? (
                      <Tag color="red" data-gx="inbox-failed-badge">
                        발송 실패 {group.failedCount}건
                      </Tag>
                    ) : null}
                  </Space>

                  <Space size={6} wrap>
                    <Text style={{ fontSize: 13 }}>
                      {event?.stream_monitor_name || '카메라 미상'}
                    </Text>
                    {event ? (
                      <Tag>{labelOf(RESPONSE_STATE_LABEL, event.response_state)}</Tag>
                    ) : (
                      // ★ 「없음」이 아니라 「이 페이지에서 못 찾음」이다 — 다른 사실이다.
                      <Tag color="default">이벤트 속성 미조회</Tag>
                    )}
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      발생 {event ? relative(event.occurred_at) : '—'}
                      {event ? ` (${shortAbsolute(event.occurred_at)})` : ''}
                    </Text>
                  </Space>

                  {/*
                    ⚠ ① **채널 줄을 접지 않는다.** 배지만 그리고 나머지를 감추면
                      실패 사유가 한 번 더 숨는다. 채널 수만큼 줄이 있고, 각 줄은
                      「배지 + 무슨 일이 있었는지」다. 사건 수가 줄었지 정보가 준 게 아니다.
                    ★ 모수를 적는다 — 이 사건에 나간 발송이 몇 건인지 먼저 말한다.
                  */}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    이 사건에 나간 발송 {group.deliveries.length}건
                  </Text>
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    {group.deliveries.map((d) => {
                      const tone = channelTone(d);
                      return (
                        <Space
                          key={d.delivery_id}
                          size={6}
                          wrap
                          data-gx="inbox-channel-row"
                          data-gx-channel={d.channel}
                          data-gx-succeeded={d.succeeded ? '1' : '0'}
                        >
                          <Tag color={tone.color} style={{ marginInlineEnd: 0 }}>
                            {tone.mark} {d.channel}
                          </Tag>
                          {!d.succeeded ? (
                            /*
                              ★ 실패는 시각 칸이 「—」다. 0초가 아니다 — 못 보낸 것은
                                빠른 것이 아니다. 사유를 **그대로** 적는다.
                            */
                            <Text type="danger" style={{ fontSize: 12 }}>
                              발송 실패 — {d.failure_reason || '사유 없음'}
                            </Text>
                          ) : !reachesAPerson(d.channel) ? (
                            /*
                              ★★ [P-123 · UX-31 ①] 여기 「발송 12:03」이라고 적혀
                                있었다. 채널이 `log` 인 줄에도 그렇게 적었고, 그 시각은
                                「사람이 받은 시각」으로 읽힌다. 실제로는 로그 한 줄이
                                남은 시각이다 — [실측 2026-09-10] 같은 시각 메일함 0통.
                            */
                            <Text
                              type="warning"
                              style={{ fontSize: 12 }}
                              title={LOG_CHANNEL_NOTE}
                            >
                              {OUTCOME_LOG_ONLY} {shortAbsolute(d.sent_at)}
                            </Text>
                          ) : (
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {/* ★ 이 라우트는 이름이 아니라 `recipient_id` 만 낸다 —
                                  없으면 「받는 사람 없음」이라 적고, 이름을 지어내지 않는다. */}
                              발송 {shortAbsolute(d.sent_at)}
                              {d.recipient_id === null ? ' · 받는 사람 없음' : ''}
                            </Text>
                          )}
                        </Space>
                      );
                    })}
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
