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

// ── 턴 AQ · 차선 N1 · F4 지휘 화면(`/fws/command`)이 부르는 경로 ──────────
//   서버 쪽 짝은 `backend/apps/fws/api_command.py`(FwsCommandAPI) — 새 경로 0.
export const fwsCommandEndpoint = {
  screen: (id: number | string) => `/api/fws/command/incidents/${id}/command`,
  stage: (id: number | string) => `/api/fws/command/incidents/${id}/stage`,
  commandPost: (id: number | string) => `/api/fws/command/incidents/${id}/command-post`,
  aircraft: (id: number | string) => `/api/fws/command/incidents/${id}/aircraft-request`,
  evacApprove: (id: number | string) => `/api/fws/command/evacuations/${id}/approve`,
  evacRelease: (id: number | string) => `/api/fws/command/evacuations/${id}/release`,
  evacStatus: (id: number | string) => `/api/fws/command/evacuations/${id}/command-status`,
  agency: (id: number | string) => `/api/fws/command/incidents/${id}/agency-request`,
  mainFireOut: (id: number | string) => `/api/fws/command/incidents/${id}/main-fire-out`,
  extinguished: (id: number | string) => `/api/fws/command/incidents/${id}/extinguished`,
  fireDeclarations: (id: number | string) =>
    `/api/fws/command/incidents/${id}/fire-declarations`,
  hourlyApprove: (id: number | string) =>
    `/api/fws/command/incidents/${id}/hourly-report/approve`,
  timeline: (id: number | string) => `/api/fws/command/incidents/${id}/response-timeline`,
  goldenTimeReason: (id: number | string) =>
    `/api/fws/command/incidents/${id}/golden-time-reason`,
  sunset: (id: number | string) => `/api/fws/command/incidents/${id}/sunset`,
  nightStatus: (id: number | string) => `/api/fws/command/incidents/${id}/night-status`,
  meetings: (id: number | string) => `/api/fws/command/incidents/${id}/meetings`,
  postReportSummary: (id: number | string) =>
    `/api/fws/command/incidents/${id}/post-report/summary`,
  postReportPdf: (id: number | string) => `/api/fws/command/incidents/${id}/post-report.pdf`,
  // ── 턴 AQ · 차선 N3 — F4-09 연락처 · F4-13 우선순위(위험도) · F3-16 헬기 투하 시각 ──
  contacts: (id: number | string) => `/api/fws/command/incidents/${id}/contacts`,
  priority: '/api/fws/command/incidents?sort=risk',
  riskIndex: (id: number | string) => `/api/fws/command/incidents/${id}/risk-index`,
  helicopterDrop: (id: number | string) => `/api/fws/command/incidents/${id}/helicopter-drop`,
};

/**
 * 누른 뒤 재조회용 GET — 응답 캐시를 건너뛴다(`X-No-Cache`). 캐시 적중 본문은
 * 언제나 200 으로 되살아나 **누르기 전 값**을 다시 그릴 수 있다(P-19).
 */
export async function fwsGetFresh<T>(url: string): Promise<T> {
  const res = unwrap<T>(await API.get(url, { headers: { 'X-No-Cache': 'true' } }));
  if (!res.ok || res.data === null) {
    throw new Error(res.message ?? '요청이 실패했습니다');
  }
  return res.data;
}

/** 파일(PDF) 내려받기 — 인터셉터가 본문만 돌려주므로 Blob 이거나 {data: Blob} 이다. */
export async function fwsGetBlob(url: string): Promise<Blob> {
  const res: unknown = await API.get(url, {
    responseType: 'blob',
    headers: { 'X-No-Cache': 'true' },
  });
  if (res instanceof Blob) return res;
  const inner = (res as { data?: unknown } | null)?.data;
  if (inner instanceof Blob) return inner;
  throw new Error('파일을 받지 못했습니다');
}

/** F1-13 오프라인 큐가 재전송 때 같은 키를 다시 쓸 수 있게 새 키를 하나 낸다. */
export function newFwsIdempotencyKey(): string {
  return `fws-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

// ── 턴 AQ · 차선 N3 — F2-07 진화대 안전 경보 칸이 읽는 기준(기관 설정값) ──────
export const fwsAqEndpoint = {
  /** F2-07 경보 기준(기관 설정값 · P-434) — 기관 사용자면 누구나 읽는다. */
  safetyThresholds: '/api/fws/admin/safety-thresholds',
};
