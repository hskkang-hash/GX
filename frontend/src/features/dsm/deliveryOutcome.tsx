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
 *   ⚠ 모바일은 제 상수를 따로 들고 있다(`MobileInbox::LOG_ONLY_CHANNEL_LABEL` ·
 *     `OUTCOME_NOT_DELIVERED`). 그 둘을 여기로 모으는 일은 **그 화면의 차선(U3)**
 *     몫이다 — 남의 파일을 고치면 「한 파일은 한 차선」이 깨진다. 쪽지로 넘겼다.
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
