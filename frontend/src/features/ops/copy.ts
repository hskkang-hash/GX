/**
 * 플랫폼 운영(U0) 화면 문구 사전 — 턴 AO · 차선 N3.
 *
 * `features/dsm/copy.ts` 머리말과 같은 규칙: **사전에 없는 문구는 화면에 만들지
 * 않는다.** 개발 용어·절 번호(`O-01`)·영문 라벨은 화면에 내지 않는다(§0.4 규약
 * 셋째 조건) — 여기서 사람이 읽을 한국어로만 옮긴다.
 */

export const OPS_TITLE = '플랫폼 운영';

export const OPS_SECTION_LABEL = {
  tenants: '테넌트',
  health: '건강 보드',
  incidents: '인시던트',
  backups: '백업·복구',
  onboarding: '온보딩 관제',
  releases: '릴리스·배포',
};

export const OPS_HEALTH_COLOR_LABEL: Record<string, string> = {
  green: '정상',
  red: '점검 필요',
};

export const OPS_INCIDENT_STATUS_LABEL: Record<string, string> = {
  open: '접수',
  acknowledged: '조치 중',
  escalated: '에스컬레이션',
  closed: '종결',
};

export const OPS_SEVERITY_LABEL: Record<string, string> = {
  critical: '긴급',
  major: '중요',
  minor: '경미',
};

export const OPS_EMPTY = '표시할 데이터가 없습니다.';
export const OPS_LOADING = '불러오는 중입니다…';
export const OPS_ERROR_PREFIX = '불러오지 못했습니다: ';
export const OPS_FORBIDDEN = '플랫폼 운영자만 볼 수 있는 화면입니다.';
