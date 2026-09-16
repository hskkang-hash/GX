/**
 * CH-03 웹푸시 — 등록 골격 (2026-09-16 · 턴 R · 차선 U3).
 *
 * ★ 이번 턴은 **골격까지만**이다: 서비스워커를 설치해 둔다. **구독은 다음 턴이다** —
 *   `POST /api/dsm/push-subscriptions` 문이 아직 서 있지 않다(WO-GX-20260915-01 §5).
 *   그래서 이 파일에는 권한 요청(`Notification.requestPermission`)도, 구독
 *   (`pushManager.subscribe`)도 **없다** — 할 수 없는 일을 하는 척하는 단추를
 *   만들지 않는다(`MobileEventDetail.tsx` 머리말의 「없는 것에 손잡이를 그리지 않는다」와
 *   같은 규율).
 *
 * ★ 왜 등록만 먼저 하나 — 서비스워커 등록은 되돌릴 수 있고(구독 없이 그냥 대기만
 *   한다) 사람에게 아무것도 묻지 않는다. 권한 팝업(다음 턴)은 사람이 「알림 받기」를
 *   직접 눌렀을 때만 뜨는 것이 옳다 — 화면을 열자마자 뜨는 권한 팝업은 그 자체로
 *   신뢰를 깎는다(브라우저 알림 UX 의 공통 값).
 */

/** 이 SW 가 응답할 스코프. `frontend/public/field-push-sw.js` 와 짝이다. */
const SW_URL = '/field-push-sw.js';

export type PushSkeletonState =
  | { supported: false; reason: string }
  | { supported: true; registered: true }
  | { supported: true; registered: false; reason: string };

/**
 * 서비스워커를 등록해 둔다. **실패해도 화면을 막지 않는다** — 이 화면의 본업은
 * 사건 상세이지 알림 설정이 아니다. 지원하지 않는 브라우저(오래된 웹뷰 등)에서는
 * 조용히 `supported: false` 를 돌려준다.
 */
export async function ensureFieldPushServiceWorker(): Promise<PushSkeletonState> {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) {
    return { supported: false, reason: '이 브라우저는 서비스워커를 지원하지 않습니다.' };
  }
  try {
    await navigator.serviceWorker.register(SW_URL);
    return { supported: true, registered: true };
  } catch (err) {
    return {
      supported: true,
      registered: false,
      reason: err instanceof Error ? err.message : String(err),
    };
  }
}
