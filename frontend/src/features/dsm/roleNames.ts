/**
 * 역할 **표시명 사전** — 영문 내부 코드를 고객 화면에서 한국어로 부른다
 * (턴 AA · 차선 U56 · P-220 · P-221).
 *
 * 무엇이 문제였나 [세종 실측 2026-09-21 · 고객 자리]
 * --------------------------------------------------
 * 「알림 받는 사람·채널」의 규칙 표에 역할 이름이 `fire_user` · `view_only_-_anyang`
 * 로 떠 있었다. 그것은 `role.Role.code` 의 값 그대로다 — **우리 개발 어휘가 고객
 * 화면에 그대로 나온 것**이고, 고객은 그것을 제 조직의 직함으로 읽을 수 없다.
 *
 * ★★ **사전에 없는 코드는 지어내지 않는다**
 * ------------------------------------------
 * 턴 Z 에 U24 가 채널 이름으로 같은 일을 했고 그 방식이 옳았다. 모르는 코드에
 * 그럴듯한 한국어를 붙이면 그 한국어가 **틀렸다는 것이 안 보인다** — 화면은
 * 언제나 말끔하고, 틀린 직함으로 당직 배정을 읽는 사람만 생긴다(D-280 · D-301).
 * 그래서 모르는 코드는 「표시명 없음」으로 두고 **원래 코드는 `title` 에만** 둔다:
 *   · 고객 화면에는 영문 코드가 안 보인다
 *   · 운영자가 마우스를 올리면 원래 코드가 나온다 — 조치할 수 있다
 *   · **사전에 빈 자리가 있다는 사실이 화면에 남는다** (조용히 메워지지 않는다)
 *
 * ⚠ **사전 넷은 CPO 가 준 그대로다. 한 줄도 더하지 않았다** (턴 AA 본 일 ②).
 *   그런데 실측하면 이 저장소의 `role.Role.code` 에 **`view_only` 도 `sysop` 도
 *   없다**:
 *
 *     [실측 2026-09-21 17:5x · ORM · role.Role 전수 16종]
 *       superuser · user · admin · operator · order · delivery_operation ·
 *       delivery_order · view_only_-_anyang · drone_robot_user ·
 *       drone_robot_admin · fire_user · fire_admin · surveillance_order ·
 *       surveillance_operation · delivery_admin · tenant_admin_4
 *
 *   즉 사전 넷 중 **둘(`fire_user`·`fire_admin`)만 실재하는 코드**이고,
 *   고객이 실제로 본 `view_only_-_anyang` 은 **사전에 없다.** `view_only` 와
 *   `view_only_-_anyang` 은 다른 문자열이고, 「비슷하니 같은 것」은 추측이다 —
 *   추측이 직함이 되는 것이 이 사전이 막으려는 바로 그 일이다. 그래서 이 파일은
 *   **안 잇는다.** 그 자리는 `docs/agent/checkpoints/turn-aa/조율자.inbox/U56.md`
 *   에 판정 청구로 올렸다. 판정이 오면 아래 표에 **한 줄**이 는다.
 */

/**
 * ① 사전 — **CPO 가 준 넷.** 순서는 조직의 위아래가 아니라 준 순서다.
 *
 * ★ 문구의 정본은 `docs/design/GX-COPY_v1.md` 이고 그 파일은 **조율자가 병합**한다.
 *   이 표는 그 문구를 화면에 대는 자리이고, 두 곳이 어긋나면 사전이 정본이다.
 */
export const ROLE_DISPLAY_NAMES: Readonly<Record<string, string>> = {
  fire_user: '관제요원',
  fire_admin: '관제팀장',
  view_only: '지자체 담당',
  sysop: '기관 관리자',
};

/** 표시명이 없을 때 화면에 뜨는 말. **코드가 아니다.** */
export const ROLE_NAME_UNKNOWN = '표시명 없음';

/**
 * ② 표시명 하나. **모르면 「표시명 없음」** — 코드를 그대로 내보내지 않는다.
 *
 * 대소문자와 앞뒤 공백만 눕힌다. 그 이상(접두 일치 · 밑줄 제거 · 유사도)은
 * **하지 않는다** — 그 순간 `view_only_-_anyang` 이 `view_only` 로 읽히고,
 * 그것이 바로 이 파일이 막으려는 추측이다.
 */
export function roleDisplayName(code: string | null | undefined): string {
  const key = String(code ?? '').trim().toLowerCase();
  return ROLE_DISPLAY_NAMES[key] ?? ROLE_NAME_UNKNOWN;
}

/** 표시명을 아는 코드인가. 화면이 「표시명 없음」을 흐리게 그릴 때 쓴다. */
export function hasRoleDisplayName(code: string | null | undefined): boolean {
  return roleDisplayName(code) !== ROLE_NAME_UNKNOWN;
}

/**
 * ③ `title` 에 넣을 한 줄 — **원래 코드는 여기에만 있다.**
 *
 * 빈 코드에는 `title` 을 달지 않는다(빈 풍선은 고장으로 읽힌다) — 그래서
 * 빈 문자열을 돌려주고, 화면은 그것을 `undefined` 로 눕혀 속성을 안 단다.
 */
export function roleCodeTitle(code: string | null | undefined): string {
  const raw = String(code ?? '').trim();
  if (!raw) return '';
  return hasRoleDisplayName(raw)
    ? `역할 코드 ${raw}`
    : `역할 코드 ${raw} — 이 코드의 표시명이 사전에 없습니다`;
}
