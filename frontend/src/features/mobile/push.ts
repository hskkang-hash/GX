/**
 * CH-03 웹푸시 — **구독까지** (2026-09-16 · 턴 S · 차선 U3).
 *
 * 앞판(턴 R)은 서비스워커 **등록까지**였고, 그 머리말은 이렇게 적혀 있었다:
 *
 *     "구독은 다음 턴이다 — `POST /api/dsm/push-subscriptions` 문이 아직 서 있지
 *      않다. 그래서 이 파일에는 권한 요청도 구독도 **없다** — 할 수 없는 일을
 *      하는 척하는 단추를 만들지 않는다."
 *
 * 그 문이 이번 턴에 섰다(`apps/dsm/api_u3.py`). 그래서 손잡이를 단다 — **문이
 * 선 뒤에** 다는 것이 이 파일이 지켜 온 순서다.
 *
 * ★ 권한 팝업은 **사람이 「알림 받기」를 누른 뒤에만** 뜬다. 화면을 열자마자 뜨는
 *   권한 팝업은 그 자체로 신뢰를 깎고, 한 번 거절당하면 브라우저가 그 결정을
 *   **기억해서** 다음에 물어보지도 않는다 — 그 한 번이 그 사람의 알림을 영영 끈다.
 * ★ 실패를 **사유와 함께** 던진다. 「알림을 켜지 못했습니다」만 남기면 사람은
 *   자기 기기 설정을 봐야 하는지 서버를 기다려야 하는지 모른다(D-290).
 * ★ 이 파일은 **값을 화면에 그리지 않는다.** 구독 엔드포인트·키는 서버로 갈 뿐이고,
 *   화면이 받는 것은 지문 12자와 기기 이름이다(서버가 그것만 돌려준다).
 */
import { dsmDelete, dsmGet, dsmPost, dsmPostQuery, mobileEndpoint } from './api';

/** 이 SW 가 응답할 스코프. `frontend/public/field-push-sw.js` 와 짝이다. */
const SW_URL = '/field-push-sw.js';

export type PushSkeletonState =
  | { supported: false; reason: string }
  | { supported: true; registered: true }
  | { supported: true; registered: false; reason: string };

/** 서버가 내는 VAPID 상태. **값은 `public_key` 하나뿐**이고 그것은 공개키다. */
export interface VapidKeyView {
  configured: boolean;
  public_key: string;
  public_key_sha12: string;
  missing_env: string[];
  env_names: string[];
  reason: string;
}

/** 등록된 기기 한 줄. **엔드포인트도 키도 없다** — 서버가 안 보낸다. */
export interface PushDeviceRow {
  subscription_id: number;
  endpoint_sha12: string;
  label: string;
  created_at: string | null;
}

export interface PushDevicePage {
  total: number;
  subscriptions: PushDeviceRow[];
}

/** 시험 발송 결과. **0 을 모수와 함께 읽는다** — 서버가 그렇게 낸다(D-301). */
export interface TestSendResult {
  devices: number;
  sent: number;
  drill_mode: boolean;
  title: string;
  /**
   * [턴 T · P-160 ③] 이제 **행이 남는다** — `deliveries` `channel=webpush`. 첫 기기의
   * 셋을 위로 올린 것이고, 기기마다의 값은 `results[]` 에 있다.
   * `failure_reason` 은 사유 **이름·문장**이지 값이 아니다.
   */
  event_id: number | null;
  channel: 'webpush';
  delivery_id: number | null;
  succeeded: boolean;
  failure_reason: string | null;
  results: {
    endpoint_sha12: string;
    label: string;
    sent: boolean;
    reason: string;
    delivery_id: number | null;
    succeeded: boolean;
    failure_reason: string | null;
  }[];
}

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

/**
 * 이 기기가 웹푸시를 **할 수 있는가.** 못 하면 사유를 사람의 말로 돌려준다.
 *
 * ★ 셋을 따로 본다 — 고치는 방법이 다르다: 서비스워커가 없는 브라우저(바꿀 수
 *   없다) · 푸시 API 가 없는 브라우저(같다) · 알림 권한이 **거부됨**(기기 설정에서
 *   사람이 되돌려야 한다 · 우리가 다시 물어볼 수 없다).
 */
export function pushSupport(): { ok: boolean; reason: string } {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') {
    return { ok: false, reason: '이 환경에서는 알림을 켤 수 없습니다.' };
  }
  if (!('serviceWorker' in navigator)) {
    return { ok: false, reason: '이 브라우저는 서비스워커를 지원하지 않습니다.' };
  }
  if (!('PushManager' in window)) {
    return { ok: false, reason: '이 브라우저는 웹푸시를 지원하지 않습니다.' };
  }
  if (typeof Notification === 'undefined') {
    return { ok: false, reason: '이 브라우저는 알림을 지원하지 않습니다.' };
  }
  if (Notification.permission === 'denied') {
    return {
      ok: false,
      reason:
        '이 기기에서 알림이 차단돼 있습니다 — 브라우저 설정에서 이 사이트의 알림을 '
        + '허용으로 바꾼 뒤 다시 눌러 주십시오. (한 번 거부하면 브라우저가 그 결정을 '
        + '기억해 다시 묻지 않습니다.)',
    };
  }
  return { ok: true, reason: '' };
}

/** 서버가 내는 VAPID 상태 · 공개키. */
export function fetchVapidKey(): Promise<VapidKeyView> {
  return dsmGet<VapidKeyView>(mobileEndpoint.pushVapidKey);
}

/** 내 기기 목록. **내 것만** 나온다 — 같은 기관 동료의 기기도 안 나온다. */
export function listFieldPushDevices(): Promise<PushDevicePage> {
  return dsmGet<PushDevicePage>(mobileEndpoint.pushSubscriptions);
}

/** 이 기기를 끈다. 서버는 행을 지우지 않고 **끈 사실을 한 줄 더 적는다.** */
export function disableFieldPush(subscriptionId: number): Promise<unknown> {
  return dsmDelete(mobileEndpoint.pushSubscription(subscriptionId));
}

/** 내 기기로 훈련 알림 한 번. **잠금화면 도달을 사람이 눈으로 본다.** */
export function sendTestPush(): Promise<TestSendResult> {
  return dsmPostQuery<TestSendResult>(mobileEndpoint.pushTestSend, {});
}

/**
 * base64url(서버·브라우저가 쓰는 모양) → `Uint8Array`(`applicationServerKey` 가
 * 요구하는 모양). **브라우저가 이 변환을 해 주지 않는다** — 문자열을 그대로 넣으면
 * `InvalidCharacterError` 로 죽는다.
 */
function base64UrlToBytes(value: string): Uint8Array {
  const padding = '='.repeat((4 - (value.length % 4)) % 4);
  const base64 = (value + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = window.atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) out[i] = raw.charCodeAt(i);
  return out;
}

/** `ArrayBuffer` → base64url. 구독 키 둘을 서버로 보내는 모양이다. */
function bytesToBase64Url(buffer: ArrayBuffer | null): string {
  if (!buffer) return '';
  const bytes = new Uint8Array(buffer);
  let binary = '';
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return window.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * **이 기기**의 지문 12자. 서버가 목록에 내는 `endpoint_sha12` 와 같은 셈이다
 * (sha256 앞 12자 · `apps/dsm/notify_prefs.py::endpoint_fingerprint`).
 *
 * ★ 왜 필요한가: 목록은 「등록된 기기 N대」인데, 사람이 정말로 알고 싶은 것은
 *   **「지금 손에 든 이것이 켜져 있나」**다. 지문을 맞춰 보지 않으면 화면은 그 질문에
 *   답하지 못하고, 답하지 못하는 목록은 사람을 「N대 중 어느 것이 내 것이지」에
 *   세워 둔다.
 * ★ 구독이 없으면 **빈 문자열**이다 — 「없다」와 「못 읽었다」를 섞지 않는다.
 *   지문을 못 구하는 환경(구형 브라우저 · 비보안 출처)에서도 빈 문자열이고,
 *   화면은 그때 「이 기기인지 가릴 수 없습니다」라고 적는다.
 */
export async function currentDeviceFingerprint(): Promise<string> {
  try {
    if (!pushSupport().ok) return '';
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    if (!subscription?.endpoint) return '';
    const digest = await window.crypto.subtle.digest(
      'SHA-256',
      new TextEncoder().encode(subscription.endpoint),
    );
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')
      .slice(0, 12);
  } catch {
    // 지문을 못 구하는 것은 고장이 아니다 — 화면이 「가릴 수 없다」고 적으면 된다.
    return '';
  }
}

/**
 * 이 기기로 알림을 받겠다 — **권한 → 구독 → 서버 등록** 세 걸음.
 *
 * 걸음마다 **다른 사유로** 실패한다. 하나로 묶지 않는 이유는 사람이 할 일이 다르기
 * 때문이다: 브라우저를 바꿔야 하는가 · 기기 설정을 고쳐야 하는가 · 서버에 자격이
 * 없어 **우리가** 고쳐야 하는가(D-290).
 */
export async function enableFieldPush(label: string): Promise<PushDeviceRow> {
  const support = pushSupport();
  if (!support.ok) throw new Error(support.reason);

  // ① 서버에 자격이 있는가 — **권한을 묻기 전에** 확인한다. 자격이 없는데 권한부터
  //    물으면, 사람이 허락한 뒤에 「그래도 못 켭니다」를 보게 된다.
  const vapid = await fetchVapidKey();
  if (!vapid.configured || !vapid.public_key) {
    throw new Error(
      vapid.reason
        || '서버에 웹푸시 자격이 아직 없습니다 — 관리자가 키를 넣은 뒤 다시 눌러 주십시오.',
    );
  }

  // ② 서비스워커가 실제로 **준비됐는가**. 등록만으로는 부족하다 — `ready` 를 기다려야
  //    `pushManager` 가 선다.
  const registered = await ensureFieldPushServiceWorker();
  if (!registered.supported || registered.registered !== true) {
    throw new Error(
      'registered' in registered && registered.registered === false
        ? registered.reason
        : '이 브라우저에서 알림 워커를 세우지 못했습니다.',
    );
  }
  const registration = await navigator.serviceWorker.ready;

  // ③ 권한 — **사람이 누른 뒤**에만 여기 온다.
  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    throw new Error(
      permission === 'denied'
        ? '알림이 거부됐습니다 — 브라우저 설정에서 허용으로 바꾼 뒤 다시 눌러 주십시오.'
        : '알림 권한을 받지 못했습니다.',
    );
  }

  // ④ 구독. 이미 구독돼 있으면 그것을 그대로 쓴다 — 두 번 구독하면 기기가 둘로 센다.
  const existing = await registration.pushManager.getSubscription();
  const subscription =
    existing
    ?? (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: base64UrlToBytes(vapid.public_key),
    }));

  const p256dh = bytesToBase64Url(subscription.getKey('p256dh'));
  const auth = bytesToBase64Url(subscription.getKey('auth'));
  if (!p256dh || !auth) {
    throw new Error(
      '구독 키를 읽지 못했습니다 — 키 없이 등록하면 보낼 수 없는 구독이 됩니다.',
    );
  }

  // ⑤ 서버에 등록. 인자 이름 `auth_secret` 은 서버와 같아야 한다
  //    (`api_u3.py::create_push_subscription` — 문지기 인자 `auth` 와 헷갈리지
  //    않으려고 서버가 일부러 다른 이름을 쓴다).
  //
  //    ★★ [P-166 · D-486] **본문(JSON)으로 보낸다 — 쿼리가 아니다.** 턴 T 에 이
  //      호출이 `dsmPostQuery` 를 썼고, 구독 비밀 셋이 주소에 실려 접근 로그에
  //      남았다(실측 2줄). 서버가 `endpoint`·`p256dh`·`auth_secret` 을 `Schema`
  //      본문(`PushSubscriptionIn`)으로만 받게 바뀌었고(같은 턴 · 같은 커밋),
  //      쿼리에 그 이름이 보이면 본문이 옳아도 400 을 낸다 — 그래서 이 자리도
  //      `dsmPost`(본문)로 바꾼다. `dsmPostQuery` 로 두면 쿼리 없이도 400 이 난다.
  return dsmPost<PushDeviceRow>(mobileEndpoint.pushSubscriptions, {
    endpoint: subscription.endpoint,
    p256dh,
    auth_secret: auth,
    label,
  });
}
