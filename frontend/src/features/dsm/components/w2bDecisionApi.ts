/**
 * 턴 AQ · 차선 W2B — DSM 판단·인계 화면(U2-03 · U2-04 · U2-05 · U4-06)이 부르는 경로.
 *
 * ★ 공용 `../api.ts` 는 고치지 않는다 — 경로 문자열은 이 파일 한 곳에서 정하고,
 *   쓰기는 `../api.ts::dsmPostOnce`, 재조회는 N3 의 `aqFreshGet`(캐시 건너뜀)을 그대로 쓴다.
 */
export { aqFreshGet as w2bFreshGet } from './aqScreensApi';

export const w2bDsmEndpoint = {
  /** DSM-U2-03 상황판단회의 — GET 목록 · POST 기록. */
  situationMeetings: '/api/dsm/situation-meetings',
  /** DSM-U2-04 도달 카드 목록(GET). */
  thresholdAlerts: '/api/dsm/thresholds/alerts',
  /** DSM-U2-04 도달 카드의 「결정」. */
  thresholdDecide: (observationId: number) =>
    `/api/dsm/thresholds/observe/${observationId}/decide`,
  /** DSM-U2-05 최신 인계 메모(홈 카드). */
  handoverLatest: '/api/dsm/handover/latest',
  /** DSM-U2-05 「인계 확인」. */
  handoverAck: (handoverId: number) => `/api/dsm/handover/${handoverId}/ack`,
  /** DSM-U4-06 위기경보·비상 단계 — GET 이력(첫 행이 지금 단계) · POST 접수. */
  alertLevel: '/api/dsm/alert-level',
};

/** 국가 위기경보 4단계 — 서버 `alert_level_service.LEVELS` 와 같은 글자·순서. */
export const ALERT_LEVELS = ['관심', '주의', '경계', '심각'] as const;

/** 단계 색 — 낮은 것에서 높은 것. */
export const ALERT_LEVEL_COLOR: Record<string, string> = {
  관심: 'blue',
  주의: 'gold',
  경계: 'orange',
  심각: 'red',
};

/** 단계가 바뀌었다 — 띠가 다시 읽는다(같은 화면 · 상단바 둘 다). */
export const ALERT_LEVEL_CHANGED = 'gx:dsm-alert-level-changed';

export function announceAlertLevelChanged(): void {
  try {
    window.dispatchEvent(new Event(ALERT_LEVEL_CHANGED));
  } catch {
    /* 알림이 안 가도 띠는 다음 진입에 다시 읽는다 */
  }
}

export interface AlertLevelRow {
  alert_id: number;
  text: string;
  actor_id: number | null;
  level: string;
  received_at: string;
  doc_no: string;
  staffing: number | null;
}
