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

//: ★ [UX-22 · 2026-09-26] **표시 이름을 계약 3등급에 맞췄다.** 앞판은
//:   「위험 · 경고 · 정보」였는데 계약(DA-01 F-04)의 세 낱말은 **심각 · 경계 · 주의**다.
//:   화면과 계약이 다른 낱말을 쓰면 검수에서 「그 등급이 없다」가 된다.
//:   ⚠ 바꾼 것은 **표시 이름뿐**이다. 왼쪽 열쇠(`critical`/`warning`/`info`)는
//:     계약 스키마이고 그대로 둔다 — 값을 바꾸면 계약이 바뀐다 (GX-COPY §1-2).
export const SEVERITY_LABEL: Record<string, string> = {
  critical: '심각',
  warning: '경계',
  info: '주의',
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
  //: ★ [2026-09-24 · 차선 Q · OPS-15] 마이그레이션 0027 이 열거에 더한 값이다.
  //:   ⚠ **`SYSTEM_EVENT_TYPES` 에 넣지 않는다.** 단일 카메라의 죽음은 시스템 신호지만
  //:     **구역이 한꺼번에 죽는 것은 재난 징후**다 — 하천이 넘치면 하천변 카메라가
  //:     동시에 죽는다. 「시스템」 프리셋으로 접으면 그 신호가 운영 화면으로 새고
  //:     관제요원은 못 본다. 그 구별이 이 절(OPS-15)의 요점이다.
  camera_cluster_down: '카메라 군집 두절',
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

/**
 * 진위 축(`status`) 의 표시 이름.
 *
 * ★ [UX-22 · 2026-09-26] **이 축은 사용자 화면에 나란히 세우지 않는다.** 앞판은
 *   목록에 「대응 · 상태 · 판정」 세 열을, 상세에 넷을 세웠다 — 사람이 어느 축을
 *   보는지 모른다(GX-COPY §1-4). 사용자에게 보이는 것은 **처리 단계 한 줄 +
 *   판정 배지** 둘뿐이고, 이 표는 관리자 자리·내부 대조용으로만 남는다.
 * ★ 「기각」을 쓰지 않는다. 같은 뜻을 두 낱말로 부르면(상태 「기각」 · 판정 「오탐」)
 *   같은 건이 화면에서 두 이름을 갖는다 — 사전은 **오탐** 하나로 적었다.
 */
export const STATUS_LABEL: Record<string, string> = {
  new: '신규',
  confirmed: '실제',
  rejected: '오탐',
  closed: '종결',
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
//: ★ [UX-22 · 2026-09-26] 사전(GX-COPY §3)의 네 낱말로 맞췄다 —
//:   **미처리 → 접수 → 조치 중 → 종결**. 앞판의 「발생 (미처리)」는 한 칸에 두 말이
//:   들어 있어 단계 줄에 세우면 화살표가 무엇 사이인지 흐려진다.
export const RESPONSE_STATE_LABEL: Record<string, string> = {
  occurred: '미처리',
  acknowledged: '접수',
  in_progress: '조치 중',
  closed: '종결',
};

/**
 * **처리 단계 한 줄** 의 순서 (UX-22). 화면이 이 순서로 네 칸을 그린다.
 *
 * ★ 이것은 「무엇을 그릴 것인가」이지 **「무엇이 가능한가」가 아니다.** 다음에 갈 수
 *   있는 칸은 서버가 `allowed_next` 로 말한다 — 화면이 전이표를 들면 서버가 거절하는
 *   버튼을 그리게 된다 (D-399).
 */
export const RESPONSE_STEPS = ['occurred', 'acknowledged', 'in_progress', 'closed'] as const;

/**
 * 단추에 쓰는 **동사꼴**. 앞판은 라벨 뒤에 「(으)로」를 붙여 화면에 「종결(으)로」가
 * 떴다 — 프로그램이 만든 조사는 사람의 말이 아니다(GX-COPY §2). 조사를 붙이지 않고
 * 낱말 자체를 동사로 적는다.
 */
export const ADVANCE_LABEL: Record<string, string> = {
  acknowledged: '접수하기',
  in_progress: '조치 시작',
  closed: '종결하기',
};

export function advanceLabel(next: string): string {
  return ADVANCE_LABEL[next] ?? RESPONSE_STATE_LABEL[next] ?? next;
}

/** 처리 단계가 몇 번째 칸인가. 모르는 값이면 `-1` — 그때는 줄을 그리지 않는다. */
export function responseStepIndex(state: string | null | undefined): number {
  if (!state) return -1;
  return (RESPONSE_STEPS as readonly string[]).indexOf(state);
}

export function severityLabel(severity: string): string {
  return SEVERITY_LABEL[severity] ?? severity;
}

export function labelOf(table: Record<string, string>, key: string | null | undefined) {
  if (!key) return '—';
  return table[key] ?? key;
}
