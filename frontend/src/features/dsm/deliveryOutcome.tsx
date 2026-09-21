/**
 * P-123 · UX-31 ① — **「성공」이라 적혀 있는데 아무도 못 받았다.** (턴 O · 차선 C2)
 *
 * 무엇을 쟀나 [실측 2026-09-10 · 턴 O]
 * -----------------------------------
 *   · 알림 이력 **13행 전부 초록 「성공」**
 *   · 그 13행의 `channel` 이 **전부 `log`**
 *   · `recipient` 칸은 **전 행 빈칸**
 *   · 같은 시각 메일함(mailpit) 메시지 **0통**
 *
 * 즉 화면이 「성공」이라고 적은 열세 번 동안 **사람에게 간 것은 0건**이다.
 * 그리고 그 사실은 제품이 이미 다른 자리에서 글자로 적어 두고 있었다:
 *
 *     `backend/kernels/k2_notify/channels.py::LogChannel`
 *         「로그 — **사람이 아니라 로그에 도달한다**」
 *     `features/dsm/pages/DrillMode.tsx`
 *         「{채널} (사람이 아니라 로그에 도달합니다)」
 *
 * 한 화면은 알고 적는데 **알림 이력만 모른 척했다.** 화재 경보 제품에서 초록 한 줄과
 * 「사람이 받았다」 사이의 틈이 곧 위험의 전부다 — 당직자는 그 초록을 보고
 * 「통보됐다」로 읽고 전화를 걸지 않는다.
 *
 * 무엇을 바꿨나 — **글자만 바꿨다. 실제 SMTP 는 대표 결정 사항이다.**
 * ------------------------------------------------------------------
 *   결과 칸:  「성공」            →  「기록만 · 사람에게 안 갔습니다」   (channel === 'log')
 *                                    (턴 O 에는 「로그에 기록됨(사람에게 안 감)」이었다 —
 *                                     턴 AA 에 U3 의 모바일 말로 맞췄다 · 아래 상수 참조)
 *             「성공」            →  「성공」                          (그 밖의 채널)
 *   수신자 칸: 빈칸               →  「(수신자 없음)」 + 채널이 log 면 그 뜻을 한 줄
 *
 * ★★ **채널을 고치지 않았다.** 고치면 화면이 다시 거짓말한다 — 이번에는 반대 방향으로.
 *   실채널을 붙이는 것은 대표 승인 사항이고, **그때까지 화면은 정직해야 한다.**
 *
 * ⚠ 이 파일은 **말만 쥔다.** 표를 그리는 것은 화면이다 — 열 정의(`deliveryColumns`)를
 *   함께 내주는 이유는 데스크·휴대전화 두 화면이 **같은 말**을 쓰기 위해서다.
 *   두 벌이 되면 한쪽만 고치는 날 나머지가 옛말이 된다(D-212).
 */
import { Tooltip, Typography } from 'antd';

import type { DeliveryRow } from './types';

const { Text } = Typography;

/**
 * 사람에게 **안 가는** 채널. 정본은 뒷단(`k2_notify.channels.LogChannel`)이고
 * 여기는 그 이름 하나만 안다 — 이름이 늘면 이 배열에 더한다.
 */
export const NON_HUMAN_CHANNELS = ['log'] as const;

/** 이 발송이 **사람에게 갈 수 있는** 채널이었나. */
export function reachesAPerson(channel: string | undefined): boolean {
  return !NON_HUMAN_CHANNELS.includes(
    String(channel || '').trim().toLowerCase() as (typeof NON_HUMAN_CHANNELS)[number],
  );
}

/**
 * 결과 한 마디. **이 말이 이 티켓의 전부다.**
 *
 * ★★ [턴 AA · 2026-09-21 · 조율자 판정 · 차선 U1 이 고침] **말이 바뀌었다.**
 *
 *   종전: 「로그에 기록됨(사람에게 안 감)」
 *   지금: 「기록만 · 사람에게 안 갔습니다」
 *
 *   왜: **「로그에 기록됨」은 우리 저장소 이야기다.** 관제요원에게 필요한 사실은
 *   「어디에 남았나」가 아니라 **「사람에게 갔나」**이고, 앞머리에 우리 낱말을 두면
 *   그 사실이 괄호 뒤로 밀린다. U3 가 모바일(`MobileInbox`)에서 먼저 고쳤고
 *   (「기록만」 배지 + 「사람에게 안 갔습니다」), **데스크가 옛말을 쓰는 동안 두 화면의
 *   말이 갈려 있었다** — U3 가 갈린 줄을 이름으로 적어 조율자에게 올렸고, 조율자가
 *   *「배지는 사건이 아니라 **발송**을 말해야 한다」* 로 판정했다.
 *
 * ★ **정본은 여기 하나다.** 이 상수 한 줄을 고치면 데스크 표(`OutcomeCell` ·
 *   `deliveryOutcomeColumns`)가 따라온다 — 그것이 이 파일이 존재하는 이유다(머리말).
 *   ★ [턴 AB · 차선 U3] 모바일이 따로 들고 있던 상수 둘도 **이 파일로 왔다**
 *     (아래 「사람에게 안 감 계열 — 정본 한 벌」 묶음). 이제 두 화면이 **한 파일**을 본다.
 */
export const OUTCOME_LOG_ONLY = '기록만 · 사람에게 안 갔습니다';
export const OUTCOME_SENT = '성공';
export const OUTCOME_FAILED = '실패';

/**
 * 왜 사람에게 안 갔는가 — 제품이 이미 쓰고 있는 말을 그대로 쓴다.
 *
 * ★ [턴 O 병합] 첫 판에는 채널 이름을 **백틱**으로 감싸 적었다가 `verify_ui_copy` 에
 *   잡혔다(잔여 0 → 1). 정당한 적발이다: 백틱은 대장의 표기이지 손님의 표기가 아니고,
 *   손님 화면에서 그것은 그냥 **깨진 글자**로 보인다. 채널 이름 자체도 뺐다 —
 *   관제요원에게 필요한 사실은 「log 라는 채널」이 아니라 **「사람에게 안 갔다」**다.
 */
export const LOG_CHANNEL_NOTE =
  '기록으로만 남았습니다. 사람에게 가는 발송 수단(메일·문자)은 아직 연결되지 않았습니다.';

/* ═══════════════════════════════════════════════════════════════════════════
 * 「사람에게 안 감」 계열 — **정본 한 벌** (턴 AB · 차선 U3)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 턴 AA 끝에 이 말은 **세 파일에 흩어져** 있었다(U3 가 줄번호로 적어 올렸다):
 *   `deliveryOutcome.tsx`(여기) · `MobileInbox.tsx`(제 상수 둘 + 함수 둘) ·
 *   `pages/NotifySettings.tsx`(U56 의 파일 — 손대지 않는다 · 쪽지로 넘긴다).
 * 흩어진 말은 **한쪽만 고치는 날** 나머지가 옛말이 된다(D-212). 턴 AA 에 실제로
 * 그렇게 갈렸고(데스크 「로그에 기록됨」 vs 모바일 「기록만」) 한 턴을 다시 맞추는 데 썼다.
 *
 * ★★ **그런데 더 깊은 병은 말이 아니라 판정이었다.** [턴 AA · 차선 U56 실측]
 *   같은 응답을 **두 벌의 식**으로 읽고 있었다 —
 *       배지   : `critical.recipient_count == 0`   (**사람 수만** 본다)
 *       등급표 : `reaches_people`                  (사람 > 0 **그리고** 사람에게 닿는 채널)
 *   사람은 있는데 채널이 `log` 뿐인 기관에서 **배지만 초록**이 됐다.
 *   ⇒ 그러므로 이 묶음은 말만이 아니라 **판정도 한 벌**로 둔다. 아래 상수·함수는
 *     전부 `reachesAPerson()` **하나**를 부른다. **두 벌째를 만들지 않는다** —
 *     새 화면이 「사람에게 갔나」를 묻고 싶으면 여기에 식을 더하는 것이 아니라
 *     **이 함수를 부른다.**
 */

/**
 * 채널 배지에 적는 **고객의 말**. 사람에게 가는 채널은 **제 이름 그대로**다.
 *
 * ★ 「훈련」이 아니다. `backend/kernels/k2_notify/rule_admin.py` 가 `log` 를
 *   「훈련 채널」이라 부르는 것은 맞지만, 그 낱말을 **발송 줄**에 붙이면 사람은 그것을
 *   **사건에 붙은 말**로 읽고 「이건 진짜가 아니었구나」로 읽는다(턴 AA 조율자 판정).
 *       사건 배지 「훈련」  … 이 **사건**이 훈련이다        (사건의 성질)
 *       채널 배지 「기록만」 … 이 **발송**이 사람에게 안 갔다 (발송이 간 곳)
 *   한 카드에 둘이 같이 서는 날 **절대 같은 낱말로 그리지 않는다.**
 */
export const LOG_ONLY_CHANNEL_LABEL = '기록만';

/** 결과 한 마디 — 모바일 카드의 「기록만」 줄에 적는 말. 시각이 뒤에 붙는다. */
export const OUTCOME_NOT_DELIVERED = '사람에게 안 갔습니다 — 기록에만 남았습니다';

/**
 * 받는 사람 칸이 **비어 있을 때** 발송 줄 뒤에 붙는 꼬리말.
 *
 * ⚠ `recipientLabel` 의 「(수신자 없음)」 과 **같은 사실을 다른 말로** 하던 자리다
 *   (표의 칸 vs 한 줄의 꼬리) — 그래서 둘을 나란히 둔다. 말이 둘인 것은 괜찮지만
 *   **어디에 무엇이 쓰이는지 한 파일에서 보여야** 한쪽만 고치는 날이 안 온다.
 */
export const RECIPIENT_NONE_SUFFIX = '받는 사람 없음';

/**
 * 고객이 읽을 **채널 이름**. 판정은 `reachesAPerson` 하나다.
 *
 * ★ 계약 값(`d.channel`)은 **안 바꾼다** — 화면의 말이 바뀌었다고 술어가 읽는
 *   `data-gx-channel` 까지 바꾸면 게이트가 제 것을 못 찾는다(GX-COPY 규칙 2).
 */
export function channelDisplayLabel(channel: string): string {
  return reachesAPerson(channel) ? channel : LOG_ONLY_CHANNEL_LABEL;
}

/**
 * **원인과 다음 손이 한 줄.** 카드에 사람에게 안 간 발송이 하나라도 있을 때
 * **카드마다 한 번** 선다.
 *
 * ★ 왜 채널 줄마다가 아니라 **카드마다 한 번**인가 — 턴 AA 조율자 판정은
 *   「그 줄의 설명 + 다음 손」이었고, U3 가 **다음 손만** 줄에서 떼어 카드 머리로
 *   올렸다. 사유 둘:
 *     ① **다음 손은 발송의 성질이 아니라 기관의 성질**이다. 「알림 채널을 등록하라」는
 *        이 발송 한 건에 대한 손이 아니라 **기관 전체에 대한 손**이라, 발송마다
 *        되풀이하면 **같은 부탁을 열여섯 번** 하게 된다.
 *     ② [실측] 한 사건 카드 안에 `log` 줄이 **16줄**인 자료가 실재한다
 *        (`evidence/U3-Y/05_tenant_built.png` · 사건 #295402). 거기 한 문장을
 *        열여섯 벌 깔면 **카드가 사과문으로 덮인다.**
 *   ⇒ 원인(「사람에게 안 갔습니다」)은 **줄마다** 남고, 원인+다음 손 한 줄은
 *     **카드마다 한 번** 선다. 어느 쪽에서도 사실이 빠지지 않는다.
 * ⚠ 이 줄의 다음 손을 받는 화면은 U56 의 `NotifySettings.tsx` 다 — 그 화면의
 *   말이 바뀌면 이 줄이 사람을 **막다른 곳**으로 보낸다. 쪽지로 묶어 두었다.
 */
export function logOnlyNextHand(count: number): string {
  return `이 사건의 알림 ${count}건이 기록에만 남았습니다 — 관리자에게 알림 채널 등록을 요청하십시오.`;
}

/**
 * ⚠⚠ **안 고친 자리 — 이름만 단다**(턴 AB · U3 · 색을 칠하지 않는다).
 *
 *   `outcomeLabel` 과 모바일 배지는 **채널만** 본다(`succeeded && reachesAPerson`).
 *   U56 이 잰 정본 판정(`reaches_people`)의 나머지 반쪽 — **받는 사람이 있나** — 는
 *   여기서 **결과 색을 못 바꾼다**. 사람이 없는 채로 사람 채널로 나간 줄은
 *   지금도 **초록 「성공」** 에 꼬리말 하나(`RECIPIENT_NONE_SUFFIX`)만 붙는다.
 *
 *   [U3 실측 2026-09-21 · ORM 직독] 그런 줄은 **오늘 0행**이다 — 사람 채널 3행
 *   (email 2 · webpush 1)의 `recipient_id` 가 **전부 차 있다**. 그러므로 이것은
 *   **살아 있는 거짓이 아니라 잠든 자리**다.
 *   **안 고친 이유**: 고치려면 「보냈는데 받는 사람이 없다」를 위한 **세 번째 말**이
 *   필요하고(그건 「기록만」 과 다른 사실이다), 없는 자료로 새 말을 지으면
 *   그 순간 **두 벌째 판정**이 된다 — 이 묶음이 없애려던 바로 그 모양이다.
 *   ⇒ 다음 턴 후보. 자료(사람 채널 + 수신자 없음 1행)가 생기는 날 함께 잰다.
 */

/** 한 행의 결과를 **글자로**. 실패가 먼저다 — 실패는 채널과 무관하게 실패다. */
export function outcomeLabel(row: Pick<DeliveryRow, 'channel' | 'succeeded'>): string {
  if (!row.succeeded) return OUTCOME_FAILED;
  return reachesAPerson(row.channel) ? OUTCOME_SENT : OUTCOME_LOG_ONLY;
}

/**
 * 수신자 칸. **빈칸으로 두지 않는다** — 빈칸은 「이름을 못 받았다」와
 * 「받는 사람이 없다」를 구별하지 않는다.
 */
export function recipientLabel(row: Pick<DeliveryRow, 'recipient'>): string {
  const v = String(row.recipient ?? '').trim();
  return v || '(수신자 없음)';
}

/** 결과 칸의 그림. 사람에게 안 간 줄은 **초록으로 그리지 않는다.** */
export function OutcomeCell({ row }: { row: Pick<DeliveryRow, 'channel' | 'succeeded'> }) {
  const label = outcomeLabel(row);
  if (label === OUTCOME_FAILED) return <Text type="danger">{label}</Text>;
  if (label === OUTCOME_SENT) return <Text type="success">{label}</Text>;
  return (
    <Tooltip title={LOG_CHANNEL_NOTE}>
      {/* 경고색이다 — 초록도 빨강도 아니다. 「보내려 했고, 사람에게는 안 갔다」. */}
      <Text type="warning">{label}</Text>
    </Tooltip>
  );
}

/**
 * 발송 이력 표의 **결과·수신자 두 칸**. 데스크 화면(`pages/EventDetail.tsx`)이
 * 자기 표에 끼워 쓰라고 여기 둔다 — 그 화면은 이번 턴 다른 차선이 들고 있어
 * 이 파일이 **먼저 서고 나중에 이어진다**(P-123 인계 메모 참조).
 */
export const deliveryOutcomeColumns = [
  {
    title: '수신자',
    dataIndex: 'recipient',
    ellipsis: true,
    render: (_: unknown, row: DeliveryRow) => recipientLabel(row),
  },
  {
    title: '결과',
    dataIndex: 'succeeded',
    width: 220,
    render: (_: unknown, row: DeliveryRow) => <OutcomeCell row={row} />,
  },
];
