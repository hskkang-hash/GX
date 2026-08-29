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
  //: ★ [실측 2026-09-23 · 차선 C] **빠져 있었다.** 서버 열거(`DetectionEvent.EventType`)
  //:   에는 `sos` 가 있고 이 표에는 없었다 — 그 유형의 이벤트가 목록에 오면 화면이
  //:   원문 `sos` 를 그대로 그렸다. 「모르는 값을 원문으로 그린다」는 안전한 기본값이지만
  //:   **표가 열거보다 짧다는 사실 자체는 아무도 못 본다.**
  sos: '구조요청',
  //: ★ [실측 2026-09-23] **시스템 신호 둘** — 마이그레이션 0026(P-20 · 차선 E2)이
  //:   열거에 더한 값이다. 현장 탐지가 아니라 **설비 자신의 상태**이고, W1 「시스템」
  //:   프리셋이 이 둘로 거른다(온보딩 U2 #19 「장애 판단 — 시스템인가 현장인가」).
  camera_down: '카메라 무응답',
  storage_high: '저장 용량 임계',
};

/**
 * W1 「시스템」 프리셋이 서버에 보내는 유형들.
 *
 * ★ **화면이 이 목록으로 거르지 않는다.** 질의로 보내고 서버가 거른다 —
 *   이 배열은 「무엇을 물을 것인가」이지 「무엇을 남길 것인가」가 아니다.
 * ★ 정본은 `DetectionEvent.EventType` 의 시스템 값들이다. 서버가 하나를 더하면
 *   이 줄도 같은 커밋에서 늘어야 한다 — 안 늘리면 새 신호가 「시스템」에서 조용히 빠진다.
 */
export const SYSTEM_EVENT_TYPES = ['camera_down', 'storage_high'] as const;

/** 상태는 **형태**로 구분한다 — 여기에 색이 없는 것이 요점이다. */
export const STATUS_LABEL: Record<string, string> = {
  new: '신규',
  confirmed: '확인',
  rejected: '기각',
  closed: '종료',
};

/**
 * 판정(오탐 여부). `status` 와 **따로** 온다 (D-293).
 *
 * ★ [실측 2026-09-23 · 차선 C] **키가 서버와 어긋나 있었다.** 이 표는
 *   `unreviewed` · `true_positive` · `false_positive` 를 들고 있었는데 서버가 내는
 *   `EventView.verdict` 는 `confirmed` · `rejected` · `null` 이다
 *   (`DetectionEvent.VERDICT_CHOICES` = Status.CONFIRMED / Status.REJECTED).
 *   그래서 「판정」 칸은 한 번도 한국어를 그린 적이 없다 — `labelOf` 가 못 찾은 키를
 *   **원문 그대로** 내보내 `confirmed` 라고 적혀 있었고, 아무 오류도 나지 않았다.
 *   ⚠ 이것이 D-286 이 말한 그 모양이다: **화면만 옛말이 되고, 옛말이 된 것이 안 보인다.**
 *   열거의 정본은 `backend/stream_monitors/models.py::DetectionEvent.VERDICT_CHOICES` 다.
 */
export const VERDICT_LABEL: Record<string, string> = {
  confirmed: '실제',
  rejected: '오탐',
};

/**
 * 대응 진행 축 (D-399). **판정 축과 다른 것을 묻는다** — 「사람이 어디까지 했나」.
 *
 * 색을 주지 않는다. 색은 이미 등급(ISA-101)이 쓰고 있고, 한 화면에서 색이 두 축을
 * 뜻하면 진짜 빨강이 왔을 때 아무도 안 본다.
 * 정본: `backend/stream_monitors/models.py::DetectionEvent.ResponseState`.
 */
export const RESPONSE_STATE_LABEL: Record<string, string> = {
  occurred: '발생 (미처리)',
  acknowledged: '접수 확인',
  in_progress: '조치중',
  closed: '종결',
};

export function severityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? severity;
}

export function labelOf(table: Record<string, string>, key: string | null | undefined) {
  if (!key) return '—';
  return table[key] ?? key;
}
