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
