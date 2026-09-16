/**
 * CH-03 웹푸시 — 서비스워커 골격 (2026-09-16 · 턴 R · 차선 U3).
 *
 * ★ 이번 턴은 **골격까지만**이다. 실제 발송(구독 등록 → 서버 저장 → 훈련 사건 발생 →
 *   `push` 이벤트 도달)은 다음 턴 — 백엔드 `push-subscriptions` 문이 아직 없다
 *   (WO-GX-20260915-01 §5 「모바일」 표). 그래서 이 파일은 **받았을 때 무엇을 하는가**
 *   만 정한다 — 아직 아무도 구독하지 않으므로 지금은 아무 사건도 안 받는다.
 *
 * ★ 왜 별도 파일(`field-push-sw.js`)인가 — 이 저장소에 이미 서 있는 서비스워커가
 *   없다(2026-09-16 실측 · `frontend/public/` 에 sw 파일 0개). 새 이름을 쓰면
 *   기존 캐싱 전략과 충돌할 일이 없다 — 나중에 CRA/PWA 플러그인이 자기 SW를
 *   등록해도 스코프(`/`)만 겹치지 않으면 공존한다.
 *
 * ★ 사람의 말로 — 알림 하나를 못 받은 사람은 신고 전화를 기다리는 중이다.
 *   그래서 payload 파싱은 **무엇이 와도 죽지 않는다**(JSON 이 아니어도, 칸이 없어도).
 */

/** 페이로드가 없거나 깨졌을 때도 사람이 알아볼 수 있는 말. */
const FALLBACK_TITLE = 'GuardianX 알림';
const FALLBACK_BODY = '새 소식이 있습니다 — 앱에서 확인하십시오.';

self.addEventListener('install', (event) => {
  // ★ 새 버전을 **바로** 켠다 — 대기 중인 옛 워커가 남아 있으면 알림이 옛 규칙으로 간다.
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  // ★ 이미 열려 있는 탭도 즉시 이 워커의 관할로 옮긴다 — 새로고침을 기다리지 않는다.
  event.waitUntil(self.clients.claim());
});

/**
 * 푸시 payload → 화면에 보일 값. **셋 중 하나라도 없으면 지어내지 않고 자리표로 채운다**
 * (D-284 「없는 것을 있다고 하지 않는다」와 같은 결) — 서버가 아직 아무 모양도 약속한
 * 적이 없으므로(다음 턴에 계약을 정한다) 여기서 모양을 하나로 못박지 않는다.
 */
function readPayload(event) {
  if (!event.data) {
    return { title: FALLBACK_TITLE, body: FALLBACK_BODY, url: '/m/inbox', eventId: null };
  }
  let raw = null;
  try {
    raw = event.data.json();
  } catch (err) {
    // JSON 이 아니면 텍스트로라도 받는다 — 통째로 버리지 않는다.
    try {
      raw = { body: event.data.text() };
    } catch (err2) {
      raw = null;
    }
  }
  raw = raw || {};
  return {
    title: typeof raw.title === 'string' && raw.title ? raw.title : FALLBACK_TITLE,
    body: typeof raw.body === 'string' && raw.body ? raw.body : FALLBACK_BODY,
    // ★ 사건 상세로 바로 연다 — 목록을 한 번 더 넘기지 않는다(UX-45 「1탭」과 같은 값).
    url: typeof raw.url === 'string' && raw.url ? raw.url : '/m/inbox',
    eventId: raw.event_id != null ? raw.event_id : null,
  };
}

self.addEventListener('push', (event) => {
  const { title, body, url, eventId } = readPayload(event);
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      // ★ 배지·아이콘은 다음 턴 자산이 정해지면 채운다 — 지금 없는 파일 경로를
      //   지어내지 않는다(깨진 아이콘은 「알림이 고장났다」로 읽힌다).
      tag: eventId != null ? `gx-event-${eventId}` : 'gx-push',
      data: { url },
      requireInteraction: true,
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/m/inbox';
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        for (const client of clients) {
          // ★ 이미 그 화면이 열려 있으면 새 탭을 또 열지 않는다 — 손에 든 화면을 그대로 쓴다.
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        if (self.clients.openWindow) {
          return self.clients.openWindow(url);
        }
        return undefined;
      }),
  );
});
