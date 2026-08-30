/**
 * 등급 색 규약 — **ISA-101** (DA-03 §2-2).
 *
 * ★ **빨강은 `critical` 전용이다.** 삭제 단추·필수 표시 등 다른 용도에 빨강을 쓰지 않는다.
 *   관제 화면에서 빨강이 두 뜻을 가지면, 진짜 빨강이 왔을 때 아무도 안 본다.
 *
 * ★ 색으로만 구분하지 않는다 — **아이콘·라벨 텍스트를 함께** 낸다(색각 이상 대응).
 *   그래서 이 표는 색과 **라벨**을 한 줄에 둔다. 색만 쓰는 자리를 만들지 않는다.
 *
 * ★ 상태(`new`/`confirmed`/`rejected`/`closed`)는 **색이 아니라 형태**로 구분한다.
 *   색을 두 축에 동시에 쓰면 판독이 무너진다 — 그래서 상태 표는 색을 갖지 않는다.
 *
 * 열거값의 정본은 `backend/stream_monitors/models.py::DetectionEvent` 와
 * `docs/contracts/detection-event.md` 다. 늘리려면 **같은 커밋에서** 셋을 함께 고친다.
 */

export const SEVERITY_LABEL: Record<string, string> = {
  critical: '위험',
  warning: '경고',
  info: '정보',
};

/** AntD `Tag` 의 색 이름. `critical` 만 빨강이다. */
export const SEVERITY_COLOR: Record<string, string> = {
  critical: 'red',
  warning: 'orange',
  info: 'blue',
};

/** 색을 못 보는 사람에게 등급을 말하는 두 번째 통로. */
export const SEVERITY_ICON: Record<string, string> = {
  critical: '■',
  warning: '▲',
  info: '●',
};

export const EVENT_TYPE_LABEL: Record<string, string> = {
  fire: '화재',
  smoke: '연기',
  flood: '침수',
  person: '사람',
  vehicle: '차량',
  intrusion: '침입',
};

/** 상태는 **형태**로 구분한다 — 여기에 색이 없는 것이 요점이다. */
export const STATUS_LABEL: Record<string, string> = {
  new: '신규',
  confirmed: '확인',
  rejected: '기각',
  closed: '종료',
};

/** 판정(오탐 여부). `status` 와 **따로** 온다 (D-293). */
export const VERDICT_LABEL: Record<string, string> = {
  unreviewed: '미판정',
  true_positive: '실제',
  false_positive: '오탐',
};

export function severityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? severity;
}

export function labelOf(table: Record<string, string>, key: string | null | undefined) {
  if (!key) return '—';
  return table[key] ?? key;
}
