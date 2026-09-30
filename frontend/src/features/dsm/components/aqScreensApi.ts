/**
 * 턴 AQ · 차선 N3 — DSM 잔여 화면(U3-01 · U3-02 · U4-07 · U4-08)이 부르는 경로와
 * 재조회 GET 한 벌.
 *
 * ★ 공용 `../api.ts` 는 고치지 않는다(여러 차선이 같이 쓰는 자리) — 경로 문자열은
 *   이 파일 한 곳에서 정하고, 쓰기는 `../api.ts::dsmPostOnce` 를 그대로 부른다.
 * ★ 누른 뒤 재조회는 응답 캐시를 건너뛴다(`X-No-Cache`) — 캐시 적중 본문은 언제나
 *   200 으로 되살아나 **누르기 전 값**을 다시 그릴 수 있다.
 */
import API from '@/services/API';

import { unwrap } from '../adapter';

export const aqDsmEndpoint = {
  /** DSM-U3-01 역할별 M2 문안 — `?role=police|119|facility|duty`. */
  m2Brief: (eventId: number | string) => `/api/dsm/events/${eventId}/m2-brief`,
  /** DSM-U4-04 통제 지점 표(GET 현황판 · POST 등록 = 도달). */
  controlPoints: '/api/dsm/control-points',
  /** 결정·해제 단계 전진. */
  controlAdvance: (pointId: number | string) => `/api/dsm/control-points/${pointId}/advance`,
  /** DSM-U3-02 「통제 완료」 — 실행 시각. */
  controlExecuted: (pointId: number | string) => `/api/dsm/controls/${pointId}/executed`,
  /** DSM-U4-07 영상 제공 대장(GET) · 요청 접수(POST). */
  videoAccess: '/api/dsm/video-access-requests',
  videoAccessApprove: (id: number | string) => `/api/dsm/video-access-requests/${id}/approve`,
  videoAccessProvide: (id: number | string) => `/api/dsm/video-access-requests/${id}/provide`,
  /** DSM-U4-07 연간 통계 — `?year=YYYY`. */
  videoAccessAnnualStats: '/api/dsm/video-access-requests/annual-stats',
  /** DSM-U4-08 평가·감사 자료 묶음 — `?since=&until=`. */
  evaluationBundle: '/api/dsm/evaluation-bundle.zip',
};

/** 재조회 GET — 캐시를 건너뛴다. 실패는 서버가 준 사유 한 줄로 던진다. */
export async function aqFreshGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = unwrap<T>(await API.get(url, { params, headers: { 'X-No-Cache': 'true' } }));
  if (!res.ok || res.data === null) {
    throw new Error(res.message ?? '불러오지 못했습니다');
  }
  return res.data;
}
