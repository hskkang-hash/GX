/**
 * 재현 시험 — **U5#2 `/roles` 표 0행**의 뿌리 (턴 AB · 차선 U56).
 *
 * 왜 이 파일이 있나
 * -----------------
 * 지시서는 U5#2 를 「제품 결함 후보 — **재현 시험을 먼저 세우고** 고쳐라」로 냈다.
 * 이 저장소의 앞판에는 시험 달리개가 없다(`frontend/package.json` 에 vitest·jest 0).
 * 그래서 **순수 함수만으로 재현되는 부분**을 node 로 직접 돌린다. node 24 가
 * `.ts` 를 형만 벗겨 그대로 읽는다 — 새 도구도 새 의존성도 안 들인다.
 *
 *     PYTHONIOENCODING=utf-8 node scripts/repro_u5_2_roles_zero_rows.mjs
 *     rc 0 = 재현 + 고침 확인 · rc 1 = 어긋남
 *
 * ⚠ **이 시험이 재는 것과 못 재는 것을 가른다.**
 *   잰다  — 「사이드바 목록에서 뗀 줄은 그 주소의 메뉴로 못 찾힌다」(뿌리의 ㉣)
 *           「되돌린 뒤에는 찾힌다」 · 「끝나지 않는 갱신이 안 난다」
 *   못 잰다 — 인수 표가 실제로 목록을 부르는지(브라우저 · 번들 안). 그것은
 *           창에서 **누른 뒤**로 본다. 이 파일만으로는 **초록이 아니다.**
 *
 * 무엇이 뿌리인가 [실측 2026-09-21 · `rj-core/dist/rj-core.es.js`]
 * ----------------------------------------------------------------
 *   ㉠ `RoleManagement` 의 목록 호출  `useEffect(() => { E && !zn(z) && y(); })`
 *   ㉡ `E`(pageSize) 는 표 설정이 온 뒤   `u0?.pagination_size && f && W(...)`
 *   ㉢ 그 설정은  `x0 && ... && (activeSubItemSession || activeItemSession)
 *                 && userInfo?.id && k1?.id`  아래에서만 불린다
 *   ㉣ `k1 = getMenuByMainIdAndSubId(...)` → **`useMenuData()` 목록에서 찾는다**
 *   ⇒ 목록에 없으면 `k1 = null` → 설정 없음 → `pageSize` 없음 → **목록 호출 0회**
 *      → 표 **0행**. 「없다」와 같은 그림이 된다.
 *
 * 시각 [정본 `docs/agent/onboarding_48.md`]
 *   2026-09-07  `admin` 으로 `/roles` → 15개 역할 · `Add New Role` 보임   ●
 *   2026-09-10  턴 O — `roleNav.ts` 가 서고 U5 표에 `/roles` 가 없다
 *   2026-09-17  `admin` 으로 `/roles` → 표 행 0 · `Add New Role` 없음      ○
 */
import {
  bucketOf,
  filterNav,
  hideAcquired,
  menuForPath,
  navSignature,
  withCurrentPath,
} from '../frontend/src/features/nav/roleNav.ts';

/* ── 표본 — dj-core `menu.Menu` 의 모양을 그대로 흉내 낸다 ──────────────────
 *
 * ★ id 는 **실측한 행의 것**이다(지어낸 수가 아니다):
 *     #2 `Admin ` (마디 · 제 경로 없음) · #3 `User Management` `/users`
 *     #5 『역할 관리』 `/roles` · #6 `/configuration-management`
 *     #82 `/operation-settings` · #95 `/report-template`
 *     #133 `/dsm/events` · #134 `/dsm/cameras/grid`
 *   ⚠ 이것은 **표본이지 서버 응답이 아니다.** 서버가 이 역할에 무엇을 주는지는
 *     창에서 잰다 — 여기서 재는 것은 「주어진 목록을 우리가 어떻게 자르는가」다.
 */
const SERVER_MENUS = [
  { id: 133, menu_name: 'DSM Events', path: '/dsm/events', sub_menus: [] },
  { id: 134, menu_name: 'DSM Camera Grid', path: '/dsm/cameras/grid', sub_menus: [] },
  { id: 140, menu_name: 'DSM Camera Import', path: '/dsm/cameras/import', sub_menus: [] },
  { id: 141, menu_name: 'DSM Metering', path: '/dsm/metering', sub_menus: [] },
  { id: 142, menu_name: 'DSM System', path: '/dsm/system', sub_menus: [] },
  { id: 136, menu_name: 'Start', path: '/start', sub_menus: [] },
  {
    id: 2,
    menu_name: 'Admin ',
    path: '',
    sub_menus: [
      { id: 3, menu_name: 'User Management', path: '/users', upper_id: 2, sub_menus: [] },
      { id: 5, menu_name: '역할 관리', path: '/roles', upper_id: 2, sub_menus: [] },
      { id: 6, menu_name: 'Configuration', path: '/configuration-management', upper_id: 2, sub_menus: [] },
    ],
  },
  { id: 82, menu_name: 'Operation Settings', path: '/operation-settings', sub_menus: [] },
  { id: 95, menu_name: 'Report Template', path: '/report-template', sub_menus: [] },
];

const U5_HOME = '/dsm/events';
const ROLES = '/roles';

let failed = 0;
const ok = (name, cond, note) => {
  console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}${note ? `  — ${note}` : ''}`);
  if (!cond) failed += 1;
};

console.log('== 0. 역할 → 사람 ==');
ok('admin 은 U5 다', bucketOf(['admin']) === 'U5', `bucketOf=${bucketOf(['admin'])}`);

console.log('');
console.log('== 1. 재현 — 뗀 줄은 그 주소의 메뉴로 못 찾힌다 (턴 O~AA 의 상태) ==');
const cutOnly = filterNav(SERVER_MENUS, 'U5');
ok('U5 사이드바는 일곱 줄', cutOnly.length === 7, `줄=${cutOnly.length}`);
ok(
  '★ `/roles` 는 잘린 목록에 없다 → 인수 표가 제 설정을 못 찾는다 → 0행',
  menuForPath(cutOnly, ROLES) === null,
  'menuForPath(cut, "/roles") === null',
);
ok(
  '대조군 — 같은 인수 표인 `/users` 는 표에 있어 **찾힌다**(09-07·턴 AA 에 실제로 그려졌다)',
  menuForPath(cutOnly, '/users')?.id === 3,
  `id=${menuForPath(cutOnly, '/users')?.id}`,
);

console.log('');
console.log('== 2. 고침 — 서 있는 자리만 되돌린다 ==');
const atRoles = withCurrentPath(cutOnly, SERVER_MENUS, ROLES);
ok('되돌린 주소를 말한다', atRoles.restored === ROLES, `restored=${atRoles.restored}`);
ok('★ 이제 `/roles` 가 찾힌다 — `k1` 이 선다', menuForPath(atRoles.menus, ROLES)?.id === 5,
  `id=${menuForPath(atRoles.menus, ROLES)?.id}`);
ok('되돌린 줄은 **DB 에 실재하는 id** 를 쓴다(지어낸 수 0)', menuForPath(atRoles.menus, ROLES)?.id === 5);
ok('되돌린 줄은 뿌리다(마디를 안 끌고 온다)',
  menuForPath(atRoles.menus, ROLES)?.upper_id === null
  && (menuForPath(atRoles.menus, ROLES)?.sub_menus ?? []).length === 0);
ok('⚠ 값 — 그 화면에 서 있는 동안 사이드바가 7 → 8', atRoles.menus.length === 8,
  `줄=${atRoles.menus.length}`);
ok('자식 주소(`/roles/5`)도 같은 줄로 찾힌다', menuForPath(SERVER_MENUS, '/roles/5')?.id === 5);

console.log('');
console.log('== 3. 떠나면 다시 일곱 ==');
const atHome = withCurrentPath(filterNav(SERVER_MENUS, 'U5'), SERVER_MENUS, U5_HOME);
ok('역할 홈에서는 되돌릴 것이 없다', atHome.restored === null);
ok('★ 「메뉴 ≤ 7」 은 그대로다', atHome.menus.length === 7, `줄=${atHome.menus.length}`);

console.log('');
console.log('== 4. 끝나지 않는 갱신이 안 난다 (고정점) ==');
let cur = SERVER_MENUS;
let rounds = 0;
for (; rounds < 10; rounds += 1) {
  const next = withCurrentPath(filterNav(cur, 'U5'), cur, ROLES).menus;
  if (navSignature(cur) === navSignature(next)) break;
  cur = next;
}
ok('두 회차 안에 멈춘다', rounds <= 2, `회차=${rounds}`);
ok('멈춘 자리에도 `/roles` 가 있다', menuForPath(cur, ROLES)?.id === 5);

console.log('');
console.log('== 5. 사람 못 정한 역할(hideAcquired) 갈래도 같다 ==');
let unk = SERVER_MENUS;
let unkRounds = 0;
for (; unkRounds < 10; unkRounds += 1) {
  const next = withCurrentPath(hideAcquired(unk).menus, unk, ROLES).menus;
  if (navSignature(unk) === navSignature(next)) break;
  unk = next;
}
ok('두 회차 안에 멈춘다 (종전 `pruned.changed` 판정이면 안 멈춘다)', unkRounds <= 2,
  `회차=${unkRounds}`);
ok('`/roles` 는 서 있는 동안 남는다', menuForPath(unk, ROLES)?.id === 5);
const away = withCurrentPath(hideAcquired(SERVER_MENUS).menus, SERVER_MENUS, U5_HOME);
ok('떠나면 인수 넷은 도로 떼어진다',
  menuForPath(away.menus, ROLES) === null
  && menuForPath(away.menus, '/operation-settings') === null
  && menuForPath(away.menus, '/report-template') === null
  && menuForPath(away.menus, '/configuration-management') === null);

console.log('');
console.log('== 6. 없는 주소를 지어내지 않는다 ==');
const nowhere = withCurrentPath(cutOnly, SERVER_MENUS, '/dsm/notify');
ok('서버가 안 준 주소는 되돌릴 것이 없다 — 가짜 id 를 만들지 않는다',
  nowhere.restored === null && nowhere.menus.length === 7);

console.log('');
console.log(failed === 0 ? 'rc 0 — 전부 맞다' : `rc 1 — 어긋남 ${failed}건`);
process.exit(failed === 0 ? 0 : 1);
