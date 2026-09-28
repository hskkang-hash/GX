/**
 * FWS(산불감시) 화면이 부르는 면 — `apps/fws/api.py` 의 화면 쪽 짝.
 *
 * `unwrap()` 은 `../dsm/adapter` 것을 그대로 쓴다(읽기만 — 그 파일을 고치지
 * 않는다) — 응답 해석은 이 앱 전체에서 **한 곳**이어야 한다(P-129 · D-212).
 * 두 벌을 두면 dj-core 봉투 판정이 화면마다 다시 갈린다.
 *
 * ★ 이 App 의 라우트는 원시 인자를 **질의(query)**로 받는다(`apps/dsm/api.ts::
 *   dsmPostQuery` 머리말과 같은 실측 — django-ninja 규약). 그래서 `fwsPostQuery`
 *   가 본문이 아니라 질의로 조립한다.
 */
import API from '@/services/API';

import { unwrap } from '../dsm/adapter';

export const fwsEndpoint = {
  patrolCheckin: '/api/fws/patrol/checkin',
  patrolTrack: '/api/fws/patrol/track',
  patrolMine: '/api/fws/patrol/mine',
  riskToday: '/api/fws/risk/today',
  emergencyContacts: '/api/fws/emergency-contacts',
  verification: (id: number | string) => `/api/fws/verifications/${id}`,
  verificationReply: (id: number | string) => `/api/fws/verifications/${id}/reply`,
  alerts: '/api/fws/alerts',
  alertAck: (deliveryId: number | string) => `/api/fws/alerts/${deliveryId}/ack`,
  notifyPrefs: '/api/fws/notify-prefs',
  // ── 턴 AL · F2 산림재난대응단·진화대 ──────────────────────────────────
  standbyStatus: '/api/fws/resources/me/status',
  trainingMission: '/api/fws/training/mission',
  equipmentChecks: '/api/fws/equipment/checks',
  equipmentChecksMine: '/api/fws/equipment/checks/mine',
  missionsMine: '/api/fws/missions/mine',
  mission: (id: number | string) => `/api/fws/missions/${id}`,
  missionResponse: (id: number | string) => `/api/fws/missions/${id}/response`,
  missionFieldReply: (id: number | string) => `/api/fws/missions/${id}/field-reply`,
  // ── 턴 AM · F5 드론 운용자(세종 판정 P-387 — 요청·상태·결과 세 축) ──────
  droneReconMine: '/api/fws/drone/missions/mine',
  droneRecon: (eventId: number | string) => `/api/fws/drone/missions/${eventId}/recon`,
  droneHotspots: (eventId: number | string) => `/api/fws/drone/missions/${eventId}/hotspots`,
  droneHotspotsMine: (eventId: number | string) =>
    `/api/fws/drone/missions/${eventId}/hotspots/mine`,
  droneVerificationReply: (eventId: number | string) =>
    `/api/fws/drone/verifications/${eventId}/reply`,
  droneFlights: '/api/fws/drone/flights',
  droneFlightsMine: '/api/fws/drone/flights/mine',
  droneFlightMinutes: '/api/fws/drone/flights/minutes',
};

export async function fwsGet<T>(url: string): Promise<T> {
  const res = unwrap<T>(await API.get(url));
  if (!res.ok || res.data === null) {
    throw new Error(res.message ?? '요청이 실패했습니다');
  }
  return res.data;
}

/** POST — 원시 인자를 질의로 조립한다(본문이 아니다 — 머리말 참조). */
export async function fwsPostQuery<T>(
  url: string,
  query: Record<string, string | number | boolean | undefined>,
  idempotencyKey?: string,
): Promise<T> {
  const live = Object.entries(query).filter(([, v]) => v !== undefined) as [
    string,
    string | number | boolean,
  ][];
  const qs = new URLSearchParams(live.map(([k, v]) => [k, String(v)])).toString();
  const headers = idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : undefined;
  const res = unwrap<T>(await API.post(`${url}?${qs}`, {}, { headers }));
  if (!res.ok || res.data === null) {
    throw new Error(res.message ?? '요청이 실패했습니다');
  }
  return res.data;
}

/** F1-13 오프라인 큐가 재전송 때 같은 키를 다시 쓸 수 있게 새 키를 하나 낸다. */
export function newFwsIdempotencyKey(): string {
  return `fws-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
