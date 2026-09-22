/**
 * 인수(외부) 6종 판정 — **순수 함수만** (턴 AD · 차선 U56 · P-238).
 *
 * `RoleNavFilter.tsx` 에서 쓰던 것을 **여기로 옮겼다** — 그 파일은 `react` ·
 * `react-router-dom` · `rj-core` 를 끌고 오는 `.tsx` 라 node 의 타입 벗기기
 * (`node --experimental-strip-types` 없이 `.ts` 만 되는 24 의 기본 동작)로 못 읽는다.
 * 순수 함수를 **JSX 가 없는 `.ts` 로 따로** 둬야 `scripts/repro_u5_2_roles_zero_rows.mjs`
 * 가 브라우저·빌드 없이 이 자리를 그대로 잰다(같은 규율 — roleNav.ts 머리말 「순수
 * 함수다 — 시험이 이것만으로 전부 잰다」). **정본은 여기 하나뿐이다** — `RoleNavFilter.tsx`
 * 는 이 모듈을 다시 내보낼 뿐, 규칙을 복사하지 않는다(D-212·D-369 — 두 벌이면 갈린다).
 */

/**
 * 인수(외부) 6종 — order · delivery_operation · delivery_order · delivery_admin ·
 * drone_robot_user · drone_robot_admin. [P-238 · 턴 AD · 차선 U56]
 *
 * ⚠ `surveillance_order` · `surveillance_operation` 은 **여기 없다** — P-239 로
 *   `roleNav.ts::NAV_ROLE_CODES` 의 정본 코드가 됐다(관제팀장 · 관제요원). 이 표에
 *   넣으면 이미 GX 역할인 계정을 다시 최소 메뉴로 깎는 사고가 난다.
 * ⚠ `superuser` · `user` · `tenant_admin_4` 도 여기 없다 — 이번 턴의 실측 범위는
 *   ETRI-Group·GeumSan-ETRI 의 표 밖 여덟(집행)과 **인수 6종**(최소 메뉴)뿐이다.
 *   그 셋을 섞으면 손 안 댄 계정까지 갈린다 — 재서 가른 뒤에만 손댄다.
 */
export const ACQUIRED_ONLY_ROLE_CODES: ReadonlySet<string> = new Set([
  'order', 'delivery_operation', 'delivery_order', 'delivery_admin',
  'drone_robot_user', 'drone_robot_admin',
]);

/**
 * 이 역할 코드 목록이 **인수 6종뿐인가.** 순수 함수다 — 시험이 이것만으로 전부 잰다.
 *
 * ★ 코드가 하나도 없으면(`length===0`) `false` — 「모른다」와 「인수뿐이다」를 가른다.
 * ★ 인수 6종에 GX 표 코드가 **하나라도** 섞이면 `false` 다. 그 계정은 이미
 *   `bucketOf` 가 사람을 정해 위 갈래(표대로 자름)를 타므로 이 함수를 볼 일이 없다 —
 *   그래도 섞인 입력에 안전하게 `false` 를 돌려주는 것이 이 함수의 계약이다.
 */
export function isAcquiredOnlyRoles(codes: readonly string[]): boolean {
  const norm = codes.map((c) => String(c || '').trim().toLowerCase()).filter(Boolean);
  if (norm.length === 0) return false;
  return norm.every((c) => ACQUIRED_ONLY_ROLE_CODES.has(c));
}
