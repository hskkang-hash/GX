/**
 * 모바일 화면이 부르는 면 — **새 면을 만들지 않는다** (D-379).
 *
 * ★ `dsmGet`/`dsmPost`/`dsmEndpoint` 를 그대로 쓴다. 모바일용 클라이언트를 따로
 *   만들면 봉투 판정(`unwrap`: HTTP 상태 + 본문 `status_code` 둘 다)과 10초 타임아웃이
 *   **두 벌**이 되고, 두 벌은 반드시 갈린다. 갈리는 쪽은 언제나 오류 처리다
 *   (D-349 착시 ⑧ · D-212 「판단은 한 곳에서만」).
 *
 * ★ 그러므로 이 파일에는 **URL 이 없다.** 있는 것은 「모바일이 어느 문을 쓰는가」의
 *   목록뿐이고, 문 자체는 `features/dsm/api.ts` 가 정한다.
 *
 * ─────────────────────────────────────────────────────────────────────────────
 * ★★ [실측 2026-09-04 · 차선 D] **서버가 「내게 온 것」으로 걸러 주지 않는다.**
 *
 *   `GET /api/dsm/deliveries` 의 질의 인자는 `event_id · since · until ·
 *   succeeded · limit · offset` 뿐이다. `recipient_id` 는 커널
 *   (`kernels.k2_notify.list_deliveries`)에 **이미 있으나** App 라우트가 넘기지
 *   않는다 — 그래서 이 목록은 지금 「내게 온 것」이 아니라 **「우리 관제에 나간 것」**이다.
 *
 *   화면이 받아서 스스로 거르지 않는다. 거르면 **페이지 밖 발송은 없는 것이 된다**
 *   (DA-04 「필터는 전부 서버에서」). 대신 화면이 그 사실을 **적는다** —
 *   `MobileInbox` 상단의 범위 띠가 그것이다. 덮지 않고 재고로 보고한다.
 *
 *   막힌 이유: `backend/apps/dsm/**` 는 이번 턴 차선 C 의 자리다. 넘길 한 줄은
 *   차선 D 보고서의 「조율자 조각」에 있다(`mine: bool = False`).
 * ─────────────────────────────────────────────────────────────────────────────
 */
import { dsmEndpoint, dsmGet, dsmPost, DsmApiError, LOAD_TIMEOUT_MS } from '../dsm/api';

export { dsmGet, dsmPost, DsmApiError, LOAD_TIMEOUT_MS };

/**
 * 모바일이 쓰는 문 넷. **전부 이미 서 있는 문이다** — 새로 뚫은 것이 하나도 없다.
 *
 *   deliveries   M1 목록의 정본. 「내게 온 이벤트」는 발송 기록이 정한다.
 *   events       M1 한 줄에 붙일 이벤트 속성(유형·등급·발생시각)의 출처.
 *   eventDetail  M2. 목록의 값을 물려 쓰지 않고 **서버에 다시 묻는다** —
 *                물려 쓰면 문지기가 목록에만 서고 상세에 안 선다(IDOR 이 나는 자리).
 *   response     M2 상태 전이(접수 확인 / 조치 중 / 종결). 되돌림은 사유 필수.
 *   clip         M2 구간 티켓. **참조까지만이다** — 계약 11조 잠금.
 */
export const mobileEndpoint = {
  deliveries: dsmEndpoint.deliveries,
  events: dsmEndpoint.events,
  eventDetail: dsmEndpoint.eventDetail,
  response: dsmEndpoint.response,
  clip: (id: number | string) => `/api/dsm/events/${id}/clip`,
} as const;

/**
 * 쿼리로 POST 한다 — **본문이 아니라 질의다.**
 * 본문으로 보내면 422 가 나고, 그 422 는 「값이 틀렸다」가 아니라 「인자가 없다」다
 * (`features/dsm/pages/EventDetail.tsx` 가 이미 만난 자리).
 */
export function mobilePostWithQuery<T>(url: string, query: Record<string, string>): Promise<T> {
  const qs = new URLSearchParams(query).toString();
  return dsmPost<T>(`${url}?${qs}`);
}
