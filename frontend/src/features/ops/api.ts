/**
 * 플랫폼 운영(U0) 화면이 부르는 면 — O-01·02·05~12 (턴 AO · 차선 N3 · 턴 AQ · 차선 N2
 * 보드 배선).
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
  apps: '/api/dsm/ops/apps',
  appsInstall: '/api/dsm/ops/apps/install',
  appsStatus: '/api/dsm/ops/apps/status',
  health: '/api/dsm/ops/health',
  incidents: '/api/dsm/ops/incidents',
  backups: '/api/dsm/ops/backups',
  onboarding: '/api/dsm/ops/onboarding',
  audit: '/api/dsm/ops/audit',
  auditAccessRequests: '/api/dsm/ops/audit/access-requests',
  keys: '/api/dsm/ops/keys',
  keysRotate: '/api/dsm/ops/keys/rotate',
  releases: '/api/dsm/ops/releases',
  seed: '/api/dsm/ops/seed',
  seedToggle: '/api/dsm/ops/seed/toggle',
};

/** 서버가 준 거절 사유(HttpError detail)를 사람이 읽을 문장으로 꺼낸다. */
export function opsErrorText(e: unknown): string {
  const data = (e as { response?: { data?: { detail?: unknown; message?: unknown } } })
    ?.response?.data;
  if (data && typeof data.detail === 'string') return data.detail;
  if (data && typeof data.message === 'string') return data.message;
  return e instanceof Error ? e.message : String(e);
}

export function opsErrorStatus(e: unknown): number | undefined {
  return (e as { response?: { status?: number } })?.response?.status;
}

// ── O-01 테넌트 발급 ────────────────────────────────────────────────────
export interface OpsTenantRow {
  tenant_code: string;
  name: string;
  member_count: number;
  public_url: string;
  domain: string;
  region?: string;
  departments?: string[];
  issued_via_ops?: boolean;
  created_at: string | null;
}

export function fetchTenants(): Promise<{ tenants: OpsTenantRow[]; count: number }> {
  return opsGet(opsEndpoint.tenants);
}

export function issueTenant(input: {
  code: string;
  name: string;
  admin_username: string;
  admin_email: string;
  admin_password: string;
  region?: string;
  public_url?: string;
  domain?: string;
  departments?: string;
}): Promise<Record<string, unknown>> {
  return opsPostQuery(opsEndpoint.tenants, input);
}

// ── O-02 앱 설치·버전 ──────────────────────────────────────────────────
export interface OpsAppInstallRow {
  tenant_code: string;
  app_code: string;
  version: string;
  status: string;
  installed_at?: string;
  updated_at?: string;
  upgraded_from?: string | null;
}

export function fetchAppInstalls(): Promise<{ installs: OpsAppInstallRow[]; count: number }> {
  return opsGet(opsEndpoint.apps);
}

export function installApp(input: {
  tenant_code: string;
  app_code: string;
  version: string;
}): Promise<OpsAppInstallRow> {
  return opsPostQuery(opsEndpoint.appsInstall, input);
}

export function setAppStatus(input: {
  tenant_code: string;
  app_code: string;
  status: 'active' | 'inactive';
}): Promise<OpsAppInstallRow> {
  return opsPostQuery(opsEndpoint.appsStatus, input);
}

// ── O-05 건강 보드 ─────────────────────────────────────────────────────
export interface OpsHealthRow {
  tenant_code: string;
  name: string;
  cameras: { active: number; total: number };
  queue_lag_sec: number | null;
  storage_used_pct: number | null;
  backup_receipt_at: string | null;
  backup_verdict: string | null;
  survival_alert_late: unknown;
  color: 'green' | 'red';
  auto_incident_id: string | null;
}

export interface OpsHealthBoard {
  tenants: OpsHealthRow[];
  tenant_count: number;
  monitor_read: boolean;
  backup_read: boolean;
  not_measured?: Record<string, string>;
}

export function fetchHealthBoard(): Promise<OpsHealthBoard> {
  return opsGet(opsEndpoint.health);
}

// ── O-06 인시던트 ──────────────────────────────────────────────────────
export interface OpsIncidentRow {
  incident_id: string;
  tenant_code: string;
  app_code: string;
  severity: string;
  status: string;
  summary: string;
  opened_at: string;
  sla_first_response_due?: string;
  sla_escalation_due?: string;
  acknowledged_at?: string | null;
  escalated_at?: string | null;
  closed_at?: string | null;
  cause?: string;
  closing_report?: string;
}

export function fetchIncidents(
  status?: string,
): Promise<{ incidents: OpsIncidentRow[]; count: number }> {
  return opsGet(opsEndpoint.incidents, status ? { status } : undefined);
}

export function openIncident(input: {
  tenant_code: string;
  app_code: string;
  severity: string;
  summary?: string;
}): Promise<OpsIncidentRow> {
  return opsPostQuery(opsEndpoint.incidents, input);
}

export function respondIncident(id: string, note?: string): Promise<OpsIncidentRow> {
  return opsPostQuery(`${opsEndpoint.incidents}/${encodeURIComponent(id)}/respond`, { note });
}

export function escalateIncident(id: string, note?: string): Promise<OpsIncidentRow> {
  return opsPostQuery(`${opsEndpoint.incidents}/${encodeURIComponent(id)}/escalate`, { note });
}

export function closeIncident(
  id: string,
  cause: string,
  prevention?: string,
): Promise<OpsIncidentRow> {
  return opsPostQuery(`${opsEndpoint.incidents}/${encodeURIComponent(id)}/close`, {
    cause,
    prevention,
  });
}

// ── O-07 백업·복구 ─────────────────────────────────────────────────────
export interface OpsBackupBoard {
  backup: {
    read: boolean;
    measured_at: string | null;
    verdict: string | null;
    db_bytes: number | null;
    destination: string | null;
    fresh_within_24h: boolean | null;
  };
  restore_drill: {
    read: boolean;
    measured_at: string | null;
    verdict: string | null;
    rto_seconds: number | null;
    tables_restored: number | null;
    fresh_within_31d: boolean | null;
  };
}

export function fetchBackupBoard(): Promise<OpsBackupBoard> {
  return opsGet(opsEndpoint.backups);
}

// ── O-08 온보딩 관제 ───────────────────────────────────────────────────
export interface OpsRoleProgress {
  green: number;
  half: number;
  red: number;
  total: number;
  ratio: number;
}

export interface OpsOnboardingBoard {
  read: boolean;
  why?: string;
  denominator?: number;
  score_over_denominator?: string | number | null;
  green?: number;
  half?: number;
  red?: number;
  role_progress_6?: Record<string, OpsRoleProgress>;
  blocked_cards?: { row: string; why: string }[];
  tenants?: { tenant_code: string; name: string; day_n: number | null; stage: string }[];
}

export function fetchOnboardingBoard(): Promise<OpsOnboardingBoard> {
  return opsGet(opsEndpoint.onboarding);
}

// ── O-09 감사(플랫폼) ──────────────────────────────────────────────────
export interface OpsAuditEntry {
  logger: string;
  _audit_id: number;
  _actor: string;
  _at: string | null;
  _action: string;
  tenant_code?: string;
  request_id?: string;
  status?: string;
  reason?: string;
  [key: string]: unknown;
}

export function fetchAuditLog(): Promise<{ entries: OpsAuditEntry[]; total: number }> {
  return opsGet(opsEndpoint.audit);
}

export function requestTenantAccess(input: {
  tenant_code: string;
  reason: string;
}): Promise<Record<string, unknown>> {
  return opsPostQuery(opsEndpoint.auditAccessRequests, input);
}

export function approveTenantAccess(requestId: string): Promise<Record<string, unknown>> {
  return opsPostQuery(
    `${opsEndpoint.auditAccessRequests}/${encodeURIComponent(requestId)}/approve`,
  );
}

export function fetchTenantMembers(tenantCode: string): Promise<{
  tenant_code: string;
  members: { name: string; employee_id: string }[];
  expires_at: string | null;
}> {
  return opsGet(`${opsEndpoint.tenants}/${encodeURIComponent(tenantCode)}/members`);
}

// ── O-10 키·자격 회전 ──────────────────────────────────────────────────
export interface OpsKeyRow {
  key_id: number;
  prefix?: string;
  owner?: string;
  age_days?: number;
  days_left?: number;
  why?: string;
  next_rotation_due_at: string | null;
  [key: string]: unknown;
}

export interface OpsKeyBoard {
  read: boolean;
  measured_at: string | null;
  policy_days: number | null;
  due_count: number | null;
  keys: OpsKeyRow[];
  last_rotation_audit: Record<string, unknown> | null;
  rotation_audit_count: number;
}

export function fetchKeyBoard(): Promise<OpsKeyBoard> {
  return opsGet(opsEndpoint.keys);
}

export function rotateKey(input: {
  tenant_code: string;
  key_id: number;
}): Promise<Record<string, unknown>> {
  return opsPostQuery(opsEndpoint.keysRotate, input);
}

// ── O-11 릴리스·배포 ───────────────────────────────────────────────────
export interface OpsDeployRow {
  at?: string;
  commit?: string;
  exit?: number;
  smoke_exit?: number;
  drill_ok?: boolean;
  [key: string]: unknown;
}

export interface OpsReleaseBoard {
  read: boolean;
  deploys: OpsDeployRow[];
  count: number;
  latest_deploy_exit_ok: boolean | null;
  latest_smoke_ok: boolean | null;
  latest_rollback_drill_ok: boolean | null;
  deploy_gate_passed: boolean | null;
}

export function fetchReleaseBoard(): Promise<OpsReleaseBoard> {
  return opsGet(opsEndpoint.releases);
}

// ── O-12 시드·훈련 데이터 ──────────────────────────────────────────────
export interface OpsSeedToggleRow {
  tenant_code: string;
  scenario_code: string;
  action: string;
  note?: string;
  data_source: string;
  at: string;
  drill_mode?: boolean;
}

export interface OpsDrillRow {
  tenant_code: string;
  name: string;
  drill_mode: boolean;
  since: string | null;
  by: string;
  reason: string;
}

export interface OpsSeedBoard {
  toggles: OpsSeedToggleRow[];
  count: number;
  contamination_by_data_source: { seed: number; unknown_or_live: number } | null;
  drill_by_tenant?: OpsDrillRow[];
}

export function fetchSeedBoard(): Promise<OpsSeedBoard> {
  return opsGet(opsEndpoint.seed);
}

export type OpsSeedAction = 'plant' | 'hide' | 'deploy_scenario' | 'end_scenario';

export function toggleSeed(input: {
  tenant_code: string;
  action: OpsSeedAction;
  scenario_code?: string;
  note?: string;
}): Promise<OpsSeedToggleRow> {
  return opsPostQuery(opsEndpoint.seedToggle, input);
}
