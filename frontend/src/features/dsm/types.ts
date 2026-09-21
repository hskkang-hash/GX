/**
 * DSM 화면이 읽는 값의 모양. **서버가 정한 이름을 그대로 쓴다.**
 *
 * ★ 이름을 화면에서 바꾸지 않는다 — 바꾸면 서버가 그 필드를 고치는 날
 *   화면만 옛말이 되고, 옛말이 된 것이 안 보인다 (D-286).
 */

/** K3 가 정의한 다섯. 화면이 여섯째를 만들지 않는다 (F-09 AC-09 ①). */
export type WidgetState = 'data' | 'loading' | 'empty' | 'error' | 'forbidden';

/** K3 프리셋 셋. **넷째를 만들지 않는다** — 재난용을 따로 만들면 U3 수렴이 깨진다. */
export type Preset = 'OPERATOR' | 'MANAGER' | 'EXECUTIVE';

export interface PanelView {
  panel_id: number;
  dashboard_id: number;
  title: string;
  panel_type: string;
  state: WidgetState;
  reason: string;
  config: Record<string, unknown> | null;
}

export interface DashboardFrame {
  preset: Preset;
  /** ★ 매핑을 **찾은 것**과 **못 찾아 떨어진 것**을 가른다 (D-290). */
  preset_matched: boolean;
  five_states: WidgetState[];
  state_counts: Record<string, number>;
  /** 분모. 「정상 3칸」만 보면 전체가 3인지 30인지 모른다 (D-301). */
  panel_total: number;
  panels: PanelView[];
  /**
   * 연계 상태. **사유는 없다** (P-27) — 서버가 관제요원에게는 상태 하나만 준다.
   * `detail` 은 **관리자에게만** 오는 한 줄이고, 그 한 줄도 서버 사전에서 온다.
   */
  link: { status: string; detail?: string };
}

export interface EventRow {
  event_id: number;
  event_type: string;
  severity: string;
  status: string;
  /** ★ `status` 와 **따로** 온다 (D-293) — 종료된 이벤트도 오탐이었음을 말한다. */
  verdict: string;
  occurred_at: string;
  last_seen_at: string | null;
  stream_monitor_id: number | null;
  stream_monitor_name: string;
  lat: number | null;
  lng: number | null;
  snapshot_path: string;
  /**
   * ★ 대응 진행 축 — `status`(탐지 판정)와 **다른 것을 묻는다** (D-399).
   *   「사람이 어디까지 했나」다. 2026-09-21 에 목록 응답으로 나오기 시작했고,
   *   그전까지 W1 「미처리」 프리셋을 **서버가 걸러 줄 수 없었다**(온보딩 U2 #2).
   */
  response_state: string;
  /**
   * ★ P-201 (2026-09-20) — 이 사건의 **출처** (`live` · `drill`).
   *
   *   종전엔 상세에만 있었다. 그래서 목록과 큐는 훈련 사건을 실사건과 **같은
   *   카드**로 그렸고, 관제요원은 한 건씩 열어봐야 가를 수 있었다.
   *   그리는 말은 `copy.ts::dataSourceBadge` 가 정한다 — 화면이 영문 열거값을
   *   그대로 찍지 않는다(GX-COPY §2 · 「실운영 / 시드(검수용) / 훈련」).
   *   서버가 안 보내는 응답도 있었으므로(옵션) 화면은 없으면 **그리지 않는다.**
   */
  data_source?: string;
}

export interface EventDetailView extends EventRow {
  confidence: number | null;
  bbox: Record<string, unknown> | null;
  clip_path: string;
  address: string;
  /** `resolved` · `pending` · `disabled` — **없는 것은 없다고 적는다** (D-284). */
  address_status: string;
  reviewed_by_id: number | null;
  reviewed_at: string | null;
  reject_reason: string;
  /**
   * ★ 갈 수 있는 다음 칸. **서버가 준다** — 화면이 전이표를 따로 들면
   *   서버가 거절하는 버튼을 그리게 된다. 표는 서버에 하나만 둔다 (D-399).
   */
  allowed_next: string[];
}

/**
 * W1 요약 한 줄 (`GET /api/dsm/events/summary`).
 *
 * ★ **비율만 받지 않는다 — 분자·분모를 함께 받는다** (D-271 ③ · D-301).
 *   「오탐 4건」만 그리면 그것이 12건 중 4인지 400건 중 4인지 화면이 모른다.
 * ★ `false_positive_rate` 가 `null` 인 것과 `0` 인 것은 **다른 사실**이다.
 *   앞은 「잴 수 없다(판정 0건)」이고 뒤는 「재 봤더니 0이다」다. `measurable` 이 가른다.
 */
export interface EventSummary {
  hours: number;
  since: string;
  until: string;
  unhandled: number;
  /** 세는 데에도 상한이 있다. 참이면 화면은 「N건」이 아니라 「N건 이상」이라 적는다. */
  unhandled_capped: boolean;
  unhandled_cap: number;
  false_positive: number;
  reviewed: number;
  unreviewed: number;
  closed_without_verdict: number;
  false_positive_rate: number | null;
  measurable: boolean;
}

export interface DeliveryRow {
  delivery_id?: number;
  event_id: number;
  channel: string;
  recipient: string;
  succeeded: boolean;
  sent_at: string | null;
  failure_reason?: string;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * UX-35 요원별 처리 현황 — `GET /api/dsm/stats/by-reviewer` (차선 U24 · 턴 R)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * ★ 서버(`apps/dsm/stats.py::stats_by_reviewer`)는 아직 **이름을 붙이지 않는다** —
 *   판정자는 `reviewed_by_id` 하나뿐이고 사람 이름은 이 집계에 없다(가정 · 골격).
 *   화면이 이름을 지어내면 그 이름은 서버가 준 적 없는 값이라 D-286 을 어긴다.
 */
export interface ReviewerRow {
  reviewer_id: number;
  reviewed_total: number;
  closed_total: number;
  false_positive_total: number;
  /** `null` = 아직 아무것도 못 쟀다(판정에 시각이 없던 행). 0으로 지어내지 않는다. */
  avg_response_seconds: number | null;
}

export interface ByReviewerResponse {
  since: string;
  until: string;
  reviewers: ReviewerRow[];
  total_reviewed: number;
  capped: boolean;
  row_cap: number;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * UX-13 단일 초점 큐 · UX-14 대응 시계 (차선 C · 2026-09-24)
 * ═══════════════════════════════════════════════════════════════════════════ */

/**
 * 큐 카드 한 장 — **5분 창 `stream+type` 으로 묶인 것**.
 *
 * ★ `count` 는 묶인 **원본 건수**다. 접힌 것은 카드이지 기록이 아니다 —
 *   F-14 통계는 여전히 원본을 세고, `total_events` 가 그 수다.
 */
export interface QueueCard {
  event_id: number;
  event_type: string;
  severity: string;
  status: string;
  verdict: string;
  response_state: string;
  occurred_at: string;
  last_seen_at: string | null;
  stream_monitor_id: number | null;
  stream_monitor_name: string;
  lat: number | null;
  lng: number | null;
  snapshot_path: string;
  /** 아직 도는 시계(초). 닫혔으면 `null` — 시계가 멈췄다는 뜻이다. */
  elapsed_seconds: number | null;
  /** 서버가 잰 단계 0~4. 화면은 이것으로 **첫 그림**을 그리고 이후 스스로 센다. */
  urgency_tier: number;
  acknowledged_at: string | null;
  arrived_at: string | null;
  closed_at: string | null;
  /** ×N 배지. 1이면 배지를 안 단다 — 「×1」은 정보가 아니라 소음이다. */
  count: number;
  member_event_ids: number[];
  window_seconds: number;
  /** `focus` 에만 있다. 서버가 주는 전이표 — 화면이 자기 표를 들지 않는다(D-399). */
  allowed_next?: string[];
  /**
   * ★ P-201 — **훈련 사건은 큐에 선다**(제품이 센다). 그래서 그 카드가
   *   「훈련」이라고 **말해야** 한다 — 안 말하면 관제요원은 훈련을 재난으로 읽고
   *   사람을 보낸다. `live` 면 배지를 안 단다 — 평상에 배지를 붙이면 배지가 뜻을 잃는다.
   */
  data_source?: string;
}

export interface FocusQueue {
  now: string;
  /** ★ 원본 건수. `card_total` 과 **다른 수**이고, 다른 것이 요점이다. */
  total_events: number;
  card_total: number;
  sample_capped: boolean;
  window_seconds: number;
  /** 서버가 정한 문턱 표. 화면이 자기 표를 들면 통계와 글자가 갈린다. */
  tier_thresholds_sec: number[];
  /** 지금 **가장 급한 하나**. 0건이면 `null` — 평온이다. */
  focus: QueueCard | null;
  queue: QueueCard[];
}

/** 대응 전이 한 줄. `automatic` 이면 사람이 아니라 규칙이 한 일이다. */
export interface ResponseTransition {
  at: string;
  from: string;
  to: string;
  by: string;
  automatic: boolean;
}

/**
 * 네 시각 타임라인 (`GET /api/dsm/events/{id}/timeline`).
 *
 * ★ `null` 은 「아직 안 일어났다」이지 `0` 이 아니다 (D-290).
 * ★ `auto_closed` 가 참이면 이 이벤트는 **사람이 닫은 것이 아니다** — 대응 시간
 *   통계의 분모에서 빠져 있고, 화면도 그 사실을 적는다.
 */
export interface ResponseTimeline {
  event_id: number;
  response_state: string;
  stream_monitor_name: string;
  occurred_at: string;
  acknowledged_at: string | null;
  arrived_at: string | null;
  closed_at: string | null;
  acknowledge_seconds: number | null;
  arrive_seconds: number | null;
  close_seconds: number | null;
  auto_closed: boolean;
  /** 「종결 → 조치중」 되돌림 횟수. 0이 아니면 이 사건은 한 번 닫혔다 다시 열렸다. */
  reopened: number;
  elapsed_seconds: number | null;
  urgency_tier: number;
  transitions: ResponseTransition[];
}

/** 한 구간의 백분위. **분모(`n`)를 함께 받는다** — 없으면 7건과 700건이 같아 보인다. */
export interface LatencyBand {
  n: number;
  p50: number | null;
  p95: number | null;
  /** 거짓이면 p50·p95 는 `null` 이다. 「즉시 대응」이 아니라 「잴 수 없다」. */
  measurable: boolean;
}

export interface ResponseLatency {
  since: string | null;
  until: string | null;
  sampled: number;
  sample_cap: number;
  sample_capped: boolean;
  events: number;
  /** 자동 종결을 뺀 뒤 남은 분모. */
  counted: number;
  /** ★ 뺀 건수. 빼지 않으면 오탐이 많은 달일수록 대응이 빨라 보인다 (§3-4). */
  excluded_auto_closed: number;
  acknowledge: LatencyBand;
  arrive: LatencyBand;
  close: LatencyBand;
  tier_thresholds_sec: number[];
}

/* ═══════════════════════════════════════════════════════════════════════════
 * UX-17 훈련 모드 · UX-18 벌크 등록
 * ═══════════════════════════════════════════════════════════════════════════ */

export interface DrillState {
  group_id: number | null;
  /** 참이면 이 테넌트의 알림이 **사람에게 가지 않는다.** */
  drill_mode: boolean;
  since: string | null;
  by: string;
  reason: string;
  last_action: string;
  channel_while_drilling: string;
  /** `drill` 또는 `live`. 화면 캡처 메타의 다섯째 칸이 이 값을 쓴다 (D-347). */
  data_source: string;
}

export interface DrillReport {
  group_id: number | null;
  measurable: boolean;
  reason?: string;
  started_at: string | null;
  ended_at: string | null;
  in_progress?: boolean;
  data_source?: string;
  /** ★ 첫 증거. **0이어야 한다.** */
  real_channel_sends?: number;
  real_channel_breakdown?: Record<string, number>;
  /** 분모 — 창 안 발송 전건. 이것이 0이면 위의 0은 아무것도 증명하지 않는다. */
  sends_total?: number;
  sends_by_channel?: Record<string, number>;
  events_total?: number;
  events_by_type?: Record<string, number>;
  switch_by?: string;
  switch_reason?: string;
}

export interface ImportRow {
  line: number;
  name: string;
  /** `create` · `update` · `unchanged` · `error`. 넷을 합치지 않는다 (D-290). */
  action: string;
  reason: string;
  changes: Record<string, [unknown, unknown]>;
  camera_id: number | null;
  source: string;
  address_lookup: string;
}

export interface ImportPlan {
  dry_run: boolean;
  /** 있으면 **한 행도 쓰지 않는다.** 부분 성공을 만들지 않는다. */
  fatal: string;
  total: number;
  counts: Record<string, number>;
  will_write: number;
  rows: ImportRow[];
  applied?: number;
  created?: number;
  updated?: number;
}

export interface AddressGap {
  total: number;
  with_address: number;
  /** 「주소 없는 카메라 N대」 배지의 N. */
  without_address: number;
  marked_but_blank: number;
  /** 분모 0이면 `null` — 카메라가 없는 것과 전부 주소가 있는 것은 다른 사실이다. */
  coverage: number | null;
  measurable: boolean;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * UX-36 카메라 오탐률 · 임계값 (차선 U24 · 턴 S · 부속서A U2 #10·#11)
 * ═══════════════════════════════════════════════════════════════════════════ */

/**
 * 카메라 한 대의 오탐률 한 줄.
 *
 * ★ `false_positive_rate` 가 `null` 인 것과 `0` 인 것은 **다른 사실**이다 —
 *   앞은 「그 카메라를 한 번도 판정한 적이 없다」이고 뒤는 「재 봤더니 0이다」다.
 *   `measurable` 이 그 둘을 가르고, 서버는 못 재는 행을 정렬 맨 뒤로 보낸다.
 */
export interface CameraFalsePositiveRow {
  stream_monitor_id: number;
  stream_monitor_name: string;
  false_positive: number;
  reviewed: number;
  unreviewed: number;
  false_positive_rate: number | null;
  measurable: boolean;
  /** 서버가 매긴 상위 N. **화면이 세지 않는다** — 세면 두 곳이 갈린다. */
  top: boolean;
}

export interface CameraFalsePositiveResponse {
  since: string;
  until: string;
  cameras: CameraFalsePositiveRow[];
  /** 분모 — 이 창에 사건을 낸 카메라 수. 상한에 닿으면 `camera_capped` 가 참이다. */
  camera_total: number;
  top_n: number;
  capped: boolean;
  row_cap: number;
  camera_capped: boolean;
  camera_cap: number;
}

/**
 * 슬라이더 시뮬 결과 — 「최근 N일 기준 시간당 몇 건」.
 *
 * ★ `events_per_hour` 가 `null` 이면 **잴 수 없다**(확신도가 있는 사건이 0건).
 *   0.0 으로 그리면 「문턱을 올렸더니 알림이 사라졌다」는 거짓 안심이 된다.
 * ★ 「많다」의 문턱은 `noisy_per_hour` 로 **서버가 준다.** 화면이 6 을 들지 않는다.
 */
export interface ThresholdSimulation {
  since: string;
  until: string;
  days: number;
  camera_id: number;
  confidence_min: number;
  events_total: number;
  graded_total: number;
  /** 확신도가 비어 있어 어떤 문턱으로도 가를 수 없는 사건 수. */
  unknown_confidence: number;
  kept: number;
  dropped: number;
  window_hours: number;
  events_per_hour: number | null;
  current_per_hour: number | null;
  measurable: boolean;
  noisy_per_hour: number;
  noisy: boolean;
  /** 참이면 표본 상한에 닿았다 — 그 카메라의 옛 사건이 이 셈 밖에 있다. */
  sample_capped: boolean;
  row_cap: number;
}

/** 카메라별로 고칠 수 있는 임계값의 이름표. **값은 여기 없다.** */
export interface CameraThresholdKey {
  key: string;
  title: string;
  unit: string;
  /** 표 ①이 정한 기본값. `null` 이면 **기본값이 아직 없다**(0 이 아니다). */
  default: number | null;
  applies_to: string;
}

/** 「저장 → 재조회」의 재조회 결과. `set` 이 거짓이면 값이 **없는** 것이다. */
export interface CameraThresholdValue {
  key: string;
  camera_id: number;
  value: number | null;
  set: boolean;
}

/* ═══════════════════════════════════════════════════════════════════════════
 * 턴 T · 차선 U24 — 통계 축 5 · 상급 보고 체크 · 감사 읽기 (P-164 U24)
 * ═══════════════════════════════════════════════════════════════════════════ */

/** 축 하나의 행 — 서버가 준 키·이름·건수. **화면이 세지 않는다.** */
export interface StatsAxisRow {
  key: string;
  label: string;
  count: number;
}

/**
 * `GET /api/dsm/stats/axes` — 축 이름은 서버가 준다(`axis_order` · `axis_titles`).
 * 화면이 축 이름을 손으로 들면 행에 축이 늘거나 줄 때 화면만 옛말이 된다.
 *
 * ★ `total` 은 같은 창의 `GET /events` 목록 수와 같아야 한다 — 화면이 둘을 나란히
 *   적고 다르면 빨강으로 말한다(`TeamStatus` 의 「합계 = 행 합」과 같은 규약).
 */
export interface StatsAxesResponse {
  since: string;
  until: string;
  total: number;
  axes: Record<string, StatsAxisRow[]>;
  axis_titles: Record<string, string>;
  axis_order: string[];
  /** 시간대 축이 어느 시간대의 시인가 — 서버 시간대. 화면이 다시 접지 않는다. */
  hour_tz: string;
  capped: boolean;
  row_cap: number;
}

/** 상급 보고 체크 한 건. `flagged` 가 거짓이면 체크가 **없는** 것이다. */
export interface UpperReportFlag {
  event_id: number;
  flagged: boolean;
  reported_at: string | null;
  checked_at: string | null;
  checked_by_id: number | null;
  audit_id?: number;
  created?: boolean;
}

/** `GET /api/dsm/events/upper-report/flags` — 체크된 사건만 돌아온다(키는 event_id 문자열). */
export interface UpperReportFlags {
  flags: Record<string, UpperReportFlag>;
  total: number;
  capped: boolean;
}

/** 감사 한 줄 — `audit.py` 가 남긴 것을 읽은 모양. `outcome` 은 allowed | denied 둘뿐. */
export interface AuditItem {
  audit_id: number;
  at: string | null;
  channel: string;
  outcome: 'allowed' | 'denied' | string;
  action: string;
  method: string;
  actor_id: number | null;
  actor: string;
  reason: string;
  status_http: number | null;
}

export interface AuditPage {
  items: AuditItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  channels: string[];
}

// ── S-17 「외부 연계」 (턴 T · 차선 U56) — 비밀 값을 담는 타입은 응답 한 번뿐이다 ──

/** 인바운드 API 키 한 줄 — **값 칸이 없다**(`GET /settings/api_keys`). */
export interface InboundApiKeyRow {
  key_id: number;
  name: string;
  prefix: string;
  /** 기계 어휘(표 ② 5값) — `typed` · `verified` · `absent` · `rotated`. */
  status: string;
  /**
   * ④ [턴 AA · U56] 고객의 말 — 「사용 중 / 만료 / 폐기 / 교체됨」.
   * 서버가 옳긴다. 화면이 제 손으로 옳기면 판정식이 두 벌이 된다(D-212).
   */
  status_label?: string;
  /** ③ [턴 AA · U56] 출처 표식. 표식이 없으면 `live` 다. */
  data_source?: string;
  is_active: boolean;
  created_at?: string | null;
  last_used?: string | null;
  expires_at?: string | null;
}

/** `GET /api/dsm/settings/api_keys` — 범위(capability)는 키마다가 아니라 **한 벌**이다. */
export interface ApiKeysOverview {
  inbound: InboundApiKeyRow[];
  inbound_api_type: string;
  inbound_capability: string;
  /**
   * ③ [턴 AA · U56 · P-220] 고객 표에서 **미리 뺀** 시험 키의 수.
   * 0이면 0이라고 말한다 — 조용히 빼면 「3건」과 「3건인데 18건을
   * 숨겼다」가 같은 그림이 된다.
   */
  inbound_hidden_by_marker?: number;
  inbound_hidden_reason?: string;
  outbound?: unknown[];
}

/** 발급 응답 — `secret` 은 이 응답에만 있다. 화면은 지문·길이만 남긴다. */
export interface ApiKeyIssued extends InboundApiKeyRow {
  secret: string;
  audit_id: number;
}

/** WS-17 구독 필터 — 빈 객체는 「거르지 않는다」. */
export interface WebhookFilters {
  type?: string[];
  severity?: string[];
  camera?: string[];
}

/** 구독 한 줄(`GET /webhook-subscriptions`) — 서명키는 **이름**뿐. filters 는 따로 GET 한다. */
export interface WebhookSubscriptionRow {
  subscription_id: number;
  endpoint_url: string;
  signing_key_ref: string;
  event_types: string[];
  min_severity: string;
  payload_format: string;
  is_active: boolean;
  last_delivered_at?: string | null;
}

/** 발급 응답 — `signing_key_secret` 은 이 응답에만 있다. */
export interface WebhookIssued extends WebhookSubscriptionRow {
  signing_key_name: string;
  signing_key_secret: string;
  filters: WebhookFilters;
  audit_id: number;
}

export interface WebhookFiltersView {
  subscription_id: number;
  filters: WebhookFilters;
  is_active: boolean;
  audit_id?: number;
}

/** `GET /api/dsm/health` — 이름과 상태 이름뿐. */
export interface DsmHealth {
  status: 'ok' | 'fail';
  schema: string;
  checks: Record<string, 'ok' | 'fail'>;
  failed: string[];
}
