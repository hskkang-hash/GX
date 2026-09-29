/**
 * 플랫폼 운영(U0) 화면이 부르는 면 — O-01·02·05·06·07·08·09·12 (턴 AO · 차선 N3).
 *
 * `unwrap()` 은 `features/dsm/adapter.ts` 를 **그대로 재사용**한다(D-212 — 서버 봉투
 * 해석은 한 곳에서만 정한다. dsm 전용 로직이 아니라 이 앱의 axios 응답 모양 전체를
 * 다루는 일반 함수다).
 *
 * 이 저장소의 Ninja 라우트는 원시 인자를 **질의(query)** 로 받는다(백엔드
 * `api_ops_an.py` 머리말과 같은 관례) — `opsPostQuery` 가 그 모양으로 보낸다.
 */
import API from '@/services/API';

import { unwrap } from '@/features/dsm/adapter';

async function opsGet<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const res = unwrap<T>(await API.get(url, { params }));
  if (!res.ok || res.data === null) {
    throw new Error(res.message || `요청이 실패했습니다(${url})`);
  }
  return res.data;
}

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '');
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

async function opsPostQuery<T>(
  url: string,
  query: Record<string, string | number | boolean | undefined> = {},
): Promise<T> {
  const qs = toQuery(query);
  const full = qs ? `${url}?${qs}` : url;
  const res = unwrap<T>(await API.post(full, {}));
  if (!res.ok || res.data === null) {
    throw new Error(res.message || `요청이 실패했습니다(${url})`);
  }
  return res.data;
}

export const opsEndpoint = {
  tenants: '/api/dsm/ops/tenants',
  health: '/api/dsm/ops/health',
  incidents: '/api/dsm/ops/incidents',
  backups: '/api/dsm/ops/backups',
  onboarding: '/api/dsm/ops/onboarding',
  releases: '/api/dsm/ops/releases',
};

export interface OpsTenantRow {
  tenant_code: string;
  name: string;
  member_count: number;
  public_url: string;
  domain: string;
  created_at: string | null;
}

export interface OpsHealthRow {
  tenant_code: string;
  name: string;
  cameras: { active: number; total: number };
  color: 'green' | 'red';
  auto_incident_id: string | null;
  backup_receipt_at: string | null;
}

export interface OpsIncidentRow {
  incident_id: string;
  tenant_code: string;
  app_code: string;
  severity: string;
  status: string;
  summary: string;
  opened_at: string;
}

export function fetchTenants(): Promise<{ tenants: OpsTenantRow[]; count: number }> {
  return opsGet(opsEndpoint.tenants);
}

export function fetchHealthBoard(): Promise<{ tenants: OpsHealthRow[]; tenant_count: number }> {
  return opsGet(opsEndpoint.health);
}

export function fetchIncidents(status?: string): Promise<{ incidents: OpsIncidentRow[]; count: number }> {
  return opsGet(opsEndpoint.incidents, status ? { status } : undefined);
}

export function fetchBackupBoard(): Promise<Record<string, unknown>> {
  return opsGet(opsEndpoint.backups);
}

export function fetchOnboardingBoard(): Promise<Record<string, unknown>> {
  return opsGet(opsEndpoint.onboarding);
}

export function fetchReleaseBoard(): Promise<Record<string, unknown>> {
  return opsGet(opsEndpoint.releases);
}

export function issueTenant(input: {
  code: string;
  name: string;
  admin_username: string;
  admin_email: string;
  admin_password: string;
}): Promise<OpsTenantRow> {
  return opsPostQuery(opsEndpoint.tenants, input);
}
