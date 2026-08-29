/**
 * 모바일 화면이 읽는 값의 모양. **서버가 정한 이름을 그대로 쓴다** (D-286).
 *
 * ★ `EventRow`·`EventDetailView`·`DeliveryRow` 는 `features/dsm/types.ts` 의 것을
 *   그대로 쓴다. 모바일용으로 베껴 두면 서버가 필드를 고치는 날 **모바일만 옛말**이
 *   되고, 옛말이 된 것이 화면에서는 안 보인다.
 */
import type { DeliveryRow, EventDetailView, EventRow } from '../dsm/types';

export type { DeliveryRow, EventDetailView, EventRow };

/** `GET /api/dsm/deliveries` 의 응답 봉투. `total` 은 **이 페이지의 수**다. */
export interface DeliveryPage {
  total: number;
  deliveries: MobileDeliveryRow[];
}

/**
 * 발송 기록 한 줄 — 라우트가 실제로 내보내는 일곱 칸.
 *
 * ★ `occurred_at` 이 **없다** [실측 2026-09-04]. 라우트는 `sent_at` 만 낸다.
 *   그래서 M1 은 「언제 일어난 일인가」를 발송 기록이 아니라 **이벤트 쪽**에서 받는다.
 * ★ 실패 행도 그대로 온다(`succeeded=false` · `sent_at=null`). 숨기지 않는다 —
 *   K2 는 실패에 `sent_at` 을 찍지 않고, 찍으면 F-10 이 거짓으로 달성된다.
 */
export interface MobileDeliveryRow {
  delivery_id: number;
  event_id: number;
  recipient_id: number | null;
  channel: string;
  succeeded: boolean;
  failure_reason: string | null;
  sent_at: string | null;
}

/**
 * M1 한 줄. 발송 기록이 **뼈대**이고 이벤트 속성은 **살**이다.
 *
 * ★ `event` 가 `null` 일 수 있다 — 발송 기록은 있는데 그 이벤트가 이번에 받아 온
 *   이벤트 페이지 안에 없는 경우다. 그때 화면은 「없음」이 아니라 **「이 페이지에서
 *   못 찾음」**이라고 적는다. 둘은 다른 사실이다(D-290).
 */
export interface InboxRow {
  delivery: MobileDeliveryRow;
  event: EventRow | null;
}

/**
 * 구간 티켓 (`GET /api/dsm/events/{id}/clip`).
 *
 * ★ **재생 가능한 클립이 아니다** — 계약 11조 잠금. `playable=false` 면 `reason` 이
 *   함께 온다. 화면은 그 사유를 그대로 적고 **재생기를 그리지 않는다.**
 */
export interface ClipTicket {
  event_id: number;
  start_offset: number;
  duration: number;
  expires_at: string;
  token: string;
  playable: boolean;
  reason: string;
}
