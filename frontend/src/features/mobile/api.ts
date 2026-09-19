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
 * ★★ [닫음 2026-09-19 · 턴 W · 차선 U3] **서버가 「내게 온 것」으로 걸러 준다.**
 *
 *   ⚠ 이 자리에는 2026-09-04 자 실측이 「`GET /api/dsm/deliveries` 에 `recipient_id`
 *     /`mine` 인자가 없다」로 남아 있었다. **그 뒤 서버가 열렸는데 이 문장만 남았고**,
 *     `MobileInbox` 는 그 문장을 믿고 인자를 안 보냈다(화면에는 「아직 못 한다」는
 *     노랑 경고까지 떠 있었다). 낡은 실측은 **날짜와 함께 갱신한다** — 지우면
 *     왜 그렇게 적혀 있었는지가 사라지고, 두면 거짓말이 된다.
 *
 *   지금 서 있는 것 [실측 2026-09-19 · 코드]:
 *     `backend/apps/dsm/api.py:750`        `mine: bool = False`
 *     `backend/apps/dsm/services.py`       `recipient_id = actor.pk if mine else None`
 *     `kernels/k2_notify/services.py`      `qs.filter(recipient_id=…)`
 *
 *   ★ **읽기 질의 인자다** — 새 라우트가 아니다. method·path 가 그대로이므로
 *     진입면이 늘지 않고, 「나」가 누구인지는 서버가 안다(사번을 보내지 않는다 —
 *     보내면 남의 사번으로 남의 수신 이력을 물을 수 있다).
 *   ★ 화면은 여전히 **자기가 거르지 않는다.** 거르면 **페이지 밖 발송은 없는 것이
 *     된다**(DA-04 「필터는 전부 서버에서」). `mine` 은 질의로 나간다.
 * ─────────────────────────────────────────────────────────────────────────────
 */
import {
  dsmDelete,
  dsmEndpoint,
  dsmGet,
  dsmPost,
  dsmPostForm,
  dsmPostQuery,
  dsmPostQueryOnce,
  dsmPut,
  intentKey,
  DsmApiError,
  LOAD_TIMEOUT_MS,
} from '../dsm/api';

export {
  dsmDelete,
  dsmGet,
  dsmPost,
  dsmPostForm,
  dsmPostQuery,
  dsmPut,
  DsmApiError,
  LOAD_TIMEOUT_MS,
  intentKey,
};

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
  /**
   * M3 현장 회신 — 「도착 · 사진 한 장 · 한 줄」의 **한 줄**.
   * ★ 문은 2026-09-27 부터 서 있었다(`POST …/field-reply`). 없던 것은 손잡이다.
   */
  fieldReply: dsmEndpoint.fieldReply,
  fieldReplies: dsmEndpoint.fieldReplies,
  /**
   * M3 「사진 한 장 올리기」(UX-45 · 2026-09-16 턴 R). 문은 이미 턴 Q 에 섰다
   * (`POST …/field-photo` · `apps/dsm/api_u3.py::upload_field_photo`) — 이번
   * 턴은 **화면 배선**이다(선택 → 업로드 → 완료 배지).
   */
  fieldPhoto: (id: number | string) => `/api/dsm/events/${id}/field-photo`,
  /**
   * M3 「오탐 회신 — 가 보니 아무것도 없다」(UX-45 5행). **새 문이 아니다** —
   * U1 이 이미 쓰는 그 `review` 다(`EventDetail.tsx` 「오탐으로 판정」과 같은 문).
   * M3 는 도착·접수가 이미 끝난 뒤에 부르므로 **`review` 단독 호출**만 쓴다 —
   * U1 큐 카드의 `review_and_acknowledge` 트랜잭션과 겹치지 않는다.
   */
  review: dsmEndpoint.review,
  /**
   * CH-03 웹푸시 구독 (2026-09-16 · 턴 S · WS-08) · M4 내 알림 설정 (WS-02).
   *
   * ★ 끝에 붙인다 — 이 파일을 여러 차선이 읽는 턴에 위쪽 줄 사이에 끼우면 충돌한다.
   * ★ 문자열을 화면 코드에 흩지 않는다. 다만 이 다섯은 `dsmEndpoint`(공용부 ·
   *   F 소유)가 아니라 **여기** 있다: 웹푸시와 M4 는 모바일만 쓰는 문이고,
   *   공용부에 두면 관제 화면이 안 쓰는 이름이 그 파일에 쌓인다.
   */
  pushSubscriptions: '/api/dsm/push-subscriptions',
  pushSubscription: (id: number | string) => `/api/dsm/push-subscriptions/${id}`,
  pushVapidKey: '/api/dsm/push-subscriptions/vapid-key',
  pushTestSend: '/api/dsm/push-subscriptions/test-send',
  notifyPrefs: '/api/dsm/me/notify-prefs',
  /**
   * M1 「처리함」(턴 T · P-164 U3) — 내가 현장 회신을 낸 사건들. **읽기뿐**이다.
   * 회신은 감사 한 줄이 정본이라 이벤트 표에 「내가 회신했다」 칸이 없고, 그래서
   * 기존 목록의 필터 인자로는 못 열어 라우트 하나가 섰다(`api_u3.py::my_handled_events`).
   */
  handledEvents: '/api/dsm/me/handled-events',
} as const;

/**
 * 쿼리로 POST 한다 — **본문이 아니라 질의다.**
 * 본문으로 보내면 422 가 나고, 그 422 는 「값이 틀렸다」가 아니라 「인자가 없다」다
 * (`features/dsm/pages/EventDetail.tsx` 가 이미 만난 자리).
 */
export function mobilePostWithQuery<T>(url: string, query: Record<string, string>): Promise<T> {
  // ★ 조립을 **두 벌 두지 않는다** — 같은 조립을 화면마다 손으로 짜다가 두 화면이
  //   빠뜨렸고, 그 둘은 422 로 죽어 있었다 [실측 2026-09-05]. 이제 한 곳이다.
  return dsmPostQuery<T>(url, query);
}

/**
 * 같은 조립에 **멱등 키**를 얹은 것 (P-78 ③). 접수·회신 두 문이 이것으로 나간다.
 * 두 번 눌려도 요청은 하나이고, 두 번째 누름은 첫 번째의 결과를 받는다.
 */
export function mobilePostWithQueryOnce<T>(
  url: string,
  query: Record<string, string>,
  idempotencyKey: string,
): Promise<T> {
  return dsmPostQueryOnce<T>(url, query, idempotencyKey);
}
