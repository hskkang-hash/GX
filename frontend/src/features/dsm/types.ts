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
  link: { status: string; reason: string };
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
