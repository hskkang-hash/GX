/**
 * 사용자 언어 사전 — **화면 본문에 쓰는 말은 여기서만 나온다** (P-27 · P-29).
 *
 * 왜 사전인가 (사고 · 2026-09-25)
 * -------------------------------
 * 「연계 상태」 상자가 서버가 준 사유를 **그대로** 그렸다. 그 사유는 우리 언어였고,
 * 상대사명 · 계약번호 · 조항이 관제요원 화면에 문단으로 떴다. 정직하려던 것이 누출이 됐다.
 *
 * 뿌리는 「사유를 화면에 적어라」였다. 정정: **사유·출처·판정 근거는 관리자 자리와
 * 문서의 자리에 산다.** 사용자 본문에는 사용자 언어만.
 *
 * 규칙 하나
 * ---------
 * **사전에 없는 문구는 만들지 않는다.** 없으면 사전에 먼저 넣고 쓴다.
 * 정본은 `docs/design/GX-COPY_v1.md` 이고, 이 파일은 그 사전의 **코드 쪽 반쪽**이다.
 *
 * ⚠ 서버 열거값을 화면이 다시 정하지 않는다. 여기 있는 것은 **표시 이름**뿐이고,
 *   계약 스키마의 값(`waiting` · `critical` …)은 그대로 둔다 — 이름을 바꾸면
 *   계약이 바뀐다.
 */

/** 연계 상태 세 값의 **표시 이름**. 모르는 값이 오면 원문을 그리지 않는다 (아래 참조). */
export const LINK_STATUS_LABEL: Record<string, string> = {
  normal: '연계 정상',
  ok: '연계 정상',
  healthy: '연계 정상',
  waiting: '연계 대기',
  pending: '연계 대기',
  down: '연계 끊김',
  disconnected: '연계 끊김',
};

/** 표시 이름에 딸린 배지 색. 색만으로 구분하지 않으므로 **라벨과 한 줄에** 둔다. */
export const LINK_STATUS_BADGE: Record<string, 'success' | 'processing' | 'error'> = {
  normal: 'success',
  ok: 'success',
  healthy: 'success',
  waiting: 'processing',
  pending: 'processing',
  down: 'error',
  disconnected: 'error',
};

/**
 * 모르는 상태값이 왔을 때 그릴 말.
 *
 * ★ 원문(`link.status`)을 그리지 않는다. 앞판은 `연계 ${status}` 로 **영문 열거값을
 *   화면에 흘렸다** — 모르는 값을 원문으로 그리는 것은 안전한 기본값처럼 보이지만,
 *   그 자리는 사용자가 읽을 수 없는 말이 나오는 문이다.
 */
export const LINK_STATUS_UNKNOWN = '연계 상태 확인 중';

export function linkStatusLabel(status: string | undefined): string {
  if (!status) return LINK_STATUS_UNKNOWN;
  return LINK_STATUS_LABEL[status] ?? LINK_STATUS_UNKNOWN;
}

export function linkStatusBadge(status: string | undefined): 'success' | 'processing' | 'error' {
  if (!status) return 'processing';
  return LINK_STATUS_BADGE[status] ?? 'processing';
}
