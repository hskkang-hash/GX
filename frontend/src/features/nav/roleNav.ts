/**
 * P-122 · UX-28 — **사이드바에 서는 줄을 역할마다 CPO 의 표로 자른다.** (턴 O · 차선 C2)
 *
 * 무엇이 문제였나 — **위로 갈수록 나빠졌고, 계약을 갱신하는 사람이 가장 나쁜 화면을 봤다**
 * ---------------------------------------------------------------------------------
 * [실측 2026-09-10 · 턴 O · 실제 로그인 4계정 · 번들 `index-C2YT13PY.js`]
 *
 *     U1 관제요원   5줄 · 한글 5 · 영문  0   ← 이미 깨끗했다
 *     U2 관제팀장  13줄 · 한글 7 · 영문  6
 *     U4 재난안전과 10줄 · 한글 2 · 영문  8   ← **계약을 갱신하는 사람**
 *     U5 관리자    19줄 · 한글 4 · 영문 15
 *
 * U4 의 화면에 뜨던 영문 줄: `Dashboard` · `Delivery` · `Surveillance` · `GCS` ·
 * `Data Analysis` · `Asset` · `Operator` · `Admin`. 그 마디를 펴면 `AIP` ·
 * `Disabillity Dashboard`(인수 자산의 오타 그대로) · `Delivery Ops Dashboard` 가 나온다.
 * **재난안전과 공무원이 열 줄 중 여덟 줄에서 남의 제품을 본다.**
 *
 * 왜 여기서 자르나 — **정본은 DB 이고 우리는 그것을 못 고친다**
 * ------------------------------------------------------------
 * 메뉴 줄은 dj-core `menu.Menu` · `menu.RoleMenu` 행이다(§0.4 무수정). 행을 끊는
 * 데이터 작업은 `backend/common/menu_exposure.py` 가 이미 하고 있고, 그것이 U1 을
 * 깨끗하게 만든 일이다. 그러나 이번 턴 우리는 **`backend/**` 를 한 줄도 못 고친다**
 * (보안 차선이 인증 길목을 들고 있다). 그래서 **앞판 층에서 가린다.**
 *
 * ★★ **이것은 자물쇠가 아니다.** 줄을 안 그려도 라우트는 그대로 열려 있고 주소를
 *   치면 들어간다. 라우트 단 권한은 이미 **서버가** 닫았다(SEC-11a · P-105).
 *
 * ⚠⚠ **위 문장은 세 턴 동안 반만 참이었다** [실측 2026-09-21 · 턴 AB · U56].
 *   주소를 치면 **들어가기는** 한다. 그러나 목록에서 뗀 줄의 **인수 화면은 제
 *   표를 못 그린다** — 인수 표가 제 설정을 `useMenuData()` 의 그 줄로 찾기
 *   때문이다. 즉 이 파일은 권한을 안 막았지만 **화면을 막고 있었다.**
 *   U5#2 `/roles` 0행이 그 값이다. 사슬과 시각은 아래 **④** 에 실측으로 적었고,
 *   고친 것도 거기 있다. **머리말이 코드보다 착했던 자리이므로 지우지 않고 남긴다.**
 *   여기서 하는 일은 **화면 결정**이지 권한 결정이 아니다 — 그 둘을 같은 말로
 *   적으면 다음 사람이 「앞판이 막고 있다」고 읽고, 그것은 거짓이다
 *   (`features/session/rolePending.ts` 머리말과 같은 규율).
 *
 * ★ **행을 지우지 않는다.** DB 도 라우트도 그대로다. 이 표를 지우면 사이드바는
 *   즉시 원래대로 돌아온다 — 되돌릴 수 있는 화면 결정이다.
 *
 * 표가 이 파일 하나인 이유
 * ------------------------
 * 「무엇을 보이나」와 「무엇이라 부르나」가 두 벌이 되면 반드시 어긋난다(D-212·D-369).
 * 이름도 여기 있다 — 인수 자산의 영문 이름(`User Management`)을 **우리 층에서**
 * 한국어로 바꿔 부른다. DB 의 `menu_name` 은 건드리지 않는다.
 */

/** CPO 의 사람 넷. 코드는 `backend/config/k3_roles.py` 의 실측 매핑과 같은 말이다. */
export type NavBucket = 'U1' | 'U2' | 'U4' | 'U5';

/**
 * 역할 코드 ↔ 사람. **뒷단 `config/k3_roles.py` 와 같은 표다.**
 *
 * ⚠ 두 벌이라는 것을 안다. 앞판은 그 파이썬을 못 읽으므로 피할 수 없다 —
 *   대신 **어긋나면 화면이 곧바로 말한다**: 매핑이 안 되는 계정에서는 이 층이
 *   아무것도 하지 않고 인수 사이드바가 그대로 뜬다(아래 `bucketOf` 의 `null`).
 *   조용히 「빈 사이드바」가 되는 길을 만들지 않는다.
 */
export const NAV_ROLE_CODES: Record<NavBucket, readonly string[]> = {
  U1: ['fire_user', 'surveillance_operation', 'operator'],
  U2: ['fire_admin', 'surveillance_order'],
  U4: ['view_only_-_anyang'],
  U5: ['admin'],
};

/** 사이드바 한 줄. `path` 가 열쇠다 — 이름은 우리가 정하고 경로는 제품이 정한다. */
export interface NavRow {
  /** 라우트 경로. dj-core 행과 맞대는 열쇠이기도 하다. */
  path: string;
  /** 화면에 뜨는 이름. **한국어다.** */
  label: string;
  /**
   * 서버가 이 역할에 이 줄을 **안 줄 때** 쓰는 값들.
   *
   * `menuId` 는 **DB 에 실재하는 행의 id** 다(지어낸 수가 아니다). 인수 사이드바는
   * `to={path}?menuId={id}` 로 옮겨 가므로, 없는 수를 넣으면 그 주소가 거짓이 된다.
   */
  menuId?: number;
  /** 아이콘 이름 — 인수 아이콘 표(`react-icons/bs`)에 실재하는 이름만 쓴다. */
  iconName?: string;
}

/**
 * ① 표 — **CPO 가 정한 자리다.** 순서가 곧 사이드바 순서다.
 *
 * 열쇠는 `path` 다. 같은 경로의 dj-core 행이 있으면 **그 행을 쓰고 이름만 바꾼다**
 * (행을 새로 만들지 않는다). 없으면 아래 `menuId`·`iconName` 으로 한 줄을 세운다.
 */
const U1_ROWS: readonly NavRow[] = [
  { path: '/dsm/queue', label: '지금 처리할 것', menuId: 132, iconName: 'Bs1Square' },
  { path: '/dsm/events', label: '무슨 일 있었나', menuId: 133, iconName: 'BsColumnsGap' },
  { path: '/dsm/cameras/grid', label: '카메라 격자', menuId: 134, iconName: 'BsCameraVideo' },
  { path: '/handover', label: '인계 메모', menuId: 135, iconName: 'BsPeople' },
  { path: '/start', label: '처음이세요', menuId: 136, iconName: 'BsCompass' },
];

export const NAV_ALLOW: Record<NavBucket, readonly NavRow[]> = {
  /** 관제요원 5 — 이미 이 모양이었다. 표에 적어 두는 이유는 **지켜야 할 것**이기 때문이다. */
  U1: U1_ROWS,

  /** 관제팀장 7 — U1 의 다섯 + 관제 현황 + 훈련 모드. */
  U2: [
    ...U1_ROWS,
    { path: '/dsm/dashboard', label: '관제 현황', menuId: 137, iconName: 'BsBarChartLine' },
    { path: '/dsm/drill', label: '훈련 모드', menuId: 138, iconName: 'BsBinoculars' },
  ],

  /**
   * 재난안전과 4 — 무슨 일 있었나 · 보고서 · 처리 기록 · 열람·삭제 청구.
   *
   * ★★ **넷 중 둘은 화면이 없다** [실측 2026-09-10 · 턴 O].
   *   「보고서」와 「처리 기록」을 여는 우리 층 화면이 라우터에 **없다**
   *   (`backend/common/product_menus.py` 의 `P61_NO_SCREEN_YET` 이 두 자리를
   *   이미 그렇게 적어 두었다 — 「보고서(월간 1쪽·HWPX)」·「감사 기록」).
   *   없는 화면에 줄을 걸면 **눌러도 아무 데도 안 가는 줄**이 생기고, 그 줄은
   *   「메뉴가 있다」와 구별되지 않는다. 그래서 **안 건다.**
   *   ⚠ 이것은 면제가 아니라 **선언**이다 — 화면이 생기는 턴에 여기 두 줄을 더한다.
   */
  U4: [
    { path: '/dsm/events', label: '무슨 일 있었나', menuId: 133, iconName: 'BsColumnsGap' },
    { path: '/dsm/privacy-requests', label: '열람·삭제 청구', menuId: 139, iconName: 'BsSearch' },
  ],

  /**
   * 관리자 9 — U1 의 다섯 + 사람 + 카메라 등록 + 백업·보존 + 이번 달 사용량.
   *
   * ★ 「사람」은 인수 화면 `/users`(dj-core 행 #3 『User Management』)다. **행을 그대로
   *   쓰고 이름만 한국어로 부른다** — DB 의 `menu_name` 은 한 자도 안 고친다.
   * ★ U1 의 다섯 중 넷(`/dsm/queue` · `/dsm/events` · `/dsm/cameras/grid` · `/start`)은
   *   서버가 `admin` 역할에 **안 준다**(`RoleMenu` 연결이 없다 — 실측). 그 넷은 여기서
   *   세운다. 라우트는 이미 서 있고 서버 권한도 이미 열려 있다(같은 `/api/dsm/*` 문을
   *   `/dsm/drill`·`/dsm/metering` 이 이 역할로 이미 쓰고 있다).
   * ★★ 「알림 받는 사람」은 **화면이 없다** — `P61_NO_SCREEN_YET` 의 「알림 규칙·채널」.
   *   그래서 CPO 의 열 자리 중 아홉만 선다. 안 건 자리는 위 U4 와 같은 규율로 적는다.
   */
  U5: [
    // ★★ [턴 AA · U56] **아홉에서 일곱으로.** 뺀 둘은 관제요원의 일이다 —
    //   「지금 처리할 것」(단일 초점 큐)과 「인계 메모」는 교대 근무하는 사람의
    //   자리이지 기관 관리자의 자리가 아니다. 둘 다 **라우트는 그대로**이고
    //   주소를 치면 열린다 — 메뉴에서 떼는 것은 화면 결정이지 권한 결정이 아니다.
    //   목표는 **역할별 메뉴 ≤ 7 · 영어 칸 0** 이다(턴 AA 귀약).
    { path: '/dsm/events', label: '무슨 일 있었나', menuId: 133, iconName: 'BsColumnsGap' },
    { path: '/dsm/cameras/grid', label: '카메라 격자', menuId: 134, iconName: 'BsCameraVideo' },
    { path: '/dsm/cameras/import', label: '카메라 등록', menuId: 140, iconName: 'BsBoxes' },
    { path: '/users', label: '사람', menuId: 3, iconName: 'BsPeople' },
    { path: '/dsm/system', label: '백업·보존', menuId: 142, iconName: 'BsGear' },
    { path: '/dsm/metering', label: '이번 달 사용량', menuId: 141, iconName: 'BsDatabase' },
    { path: '/start', label: '처음이세요', menuId: 136, iconName: 'BsCompass' },
  ],
};

/**
 * ★★ ⑤ **인수 자산 화면 넷 — 메뉴에서 뗀다. 라우트는 남긴다**
 * (턴 AA · 차선 U56 · P-220).
 *
 * 왜 위 표(허용 목록)만으로는 모자라는가 — **안 걸리는 역할이 있다**
 * -------------------------------------------------------------------
 * `filterNav` 는 `bucketOf` 가 사람을 정했을 때만 돌고, 모르는 역할에서는
 * **아무 일도 안 한다**(빈 사이드바는 결정이 아니라 사고다 — `RoleNavFilter`
 * 머리말). 그리고 이 저장소의 역할은 넷이 아니다:
 *
 *     [실측 2026-09-21 17:5x · ORM · role.Role 전수 16종]
 *       표에 있는 것   fire_user · fire_admin · operator · surveillance_operation ·
 *                     surveillance_order · view_only_-_anyang · admin
 *       표에 없는 것   superuser · user · order · tenant_admin_4 ·
 *                     delivery_operation · delivery_order · delivery_admin ·
 *                     drone_robot_user · drone_robot_admin
 *
 * 그리고 **인수 메뉴 넷은 역할 전수의 `RoleMenu` 에 들어 있다**:
 *
 *     [실측 2026-09-21 17:5x · menu.RoleMenu · 역할 14종]
 *       /operation-settings        14/14 역할
 *       /report-template           14/14 역할
 *       /roles                      6/14 역할
 *       /configuration-management  (menu #6 · `Admin `(#2) 의 자식)
 *
 * 즉 표에 안 있는 역할로 들어오는 순간 인수 사이드바가 통째로 뜨고, 거기 넷이
 * 들어 있다. 그것이 세종이 고객 자리에서 본 그림이다 — 「운영 설정」의
 * **영어 칸 빈 표**(Menu Type · Step · Group · API URL · Updater).
 *
 * ★ 그래서 이 넷은 **사람을 정했든 아니든 가린다.** 모르는 역할에서도
 *   사이드바는 비지 않는다 — 줄 넷을 뗄 뿐이다. 사고가 아니라 결정이 된다.
 * ★ **지우는 것이 아니다.** dj-core `Menu`·`RoleMenu` 행도, 라우터의 라우트도
 *   그대로다. U0 은 주소로 그대로 들어간다. 권한은 서버가 판정한다(SEC-11a · P-105).
 * ⚠ `/device`(드론 장비 등록)는 **안 뗀다** — 그것은 FWS 쪽 자산이고
 *   이 제품의 시험 장치가 아니다(턴 AA 귀약).
 */
export const NAV_ACQUIRED_HIDDEN: Readonly<Record<string, string>> = {
  '/operation-settings': '운영 설정 — 인수 자산(menu #82 · `Admin ` 의 자식). 영어 칸 빈 표다',
  '/configuration-management': '구성 관리 — 인수 자산(menu #6)',
  '/roles': '역할 관리 — 인수 자산(menu #5). 우리층의 역할은 「사람」에서 정한다',
  '/report-template': '보고서 서식 — 인수 자산(menu #95·#106 · 택배 운송장 서식). 우리 보고서는 `/dsm/reports` 다',
};

/**
 * ⑤ 인수 넷을 **나무에서 뗀다.** 순수 함수다 — 시험이 이것만으로 전부 잰다.
 *
 * ★ **원본 배열을 안 건드린다.** 새 배열을 돌려주고, 바뀐 것이 없으면
 *   `changed=false` 로 말한다 — 부르는 쪽이 **다시 쓸지 말지**를 정할 수 있어야
 *   훅이 끝나지 않는 갱신으로 돌지 않는다(`filterNav` 쪽 `navSignature` 와 같은 이유).
 * ★ **자식을 다 뗀 마디도 뗀다** — 자식이 없고 제 화면도 없는 마디는 눌러도
 *   아무 데도 안 가는 줄이다. 그 줄은 「메뉴가 있다」와 구별되지 않는다.
 *   단, 제 경로가 있는 마디는 남긴다 — 그것은 화면이 있는 줄이다.
 */
export function hideAcquired(menus: readonly MenuNode[]): {
  menus: MenuNode[];
  changed: boolean;
  removed: number;
} {
  let removed = 0;

  const walk = (nodes: readonly MenuNode[]): MenuNode[] => {
    const out: MenuNode[] = [];
    for (const m of nodes) {
      if (!m) continue;
      if (typeof m.path === 'string' && m.path in NAV_ACQUIRED_HIDDEN) {
        removed += 1;
        continue;
      }
      const rawKids = (m.sub_menus || (m.children as MenuNode[] | undefined)) ?? [];
      const hadKids = Array.isArray(rawKids) && rawKids.length > 0;
      const kids = hadKids ? walk(rawKids) : [];
      if (hadKids && kids.length === 0 && !isOwnScreen(m)) {
        removed += 1;
        continue;
      }
      out.push(hadKids ? { ...m, sub_menus: kids, children: kids } : m);
    }
    return out;
  };

  const next = walk(menus);
  return { menus: next, changed: removed > 0, removed };
}

/**
 * 이 마디가 **제 화면을 가졌는가.** 인수 사이드바의 마디는 경로가 비거나
 * (`''`) 주소가 아닌 낱말(`'Asset'` · `'GCS'`)이다 — 둘 다 못 간다.
 * 슬래시로 시작하는 것만 주소로 본다. 추측이 아니라 **라우터의 규칙**이다.
 */
function isOwnScreen(m: MenuNode): boolean {
  return typeof m.path === 'string' && m.path.startsWith('/');
}

/* ══════════════════════════════════════════════════════════════════════════
 * ④ ★★ **가림이 자물쇠였다** — 지금 서 있는 화면의 줄은 못 뗀다
 *    (턴 AB · 차선 U56 · U5#2 `/roles` 0행의 뿌리)
 * ══════════════════════════════════════════════════════════════════════════
 *
 * 이 파일의 머리말은 세 턴 동안 「**가림이지 자물쇠가 아니다 — 주소를 치면
 * 들어간다**」라고 적어 왔다. **그 문장이 틀렸다.** 이번 턴에 뿌리까지 쟀다.
 *
 * 무엇을 쟀나 [실측 2026-09-21 · 턴 AB · 번들 `rj-core/dist/rj-core.es.js`]
 * -------------------------------------------------------------------------
 * 인수 표(`CustomizableTable`)는 **제 목록을 곧바로 부르지 않는다.** 이런 사슬이다:
 *
 *   ㉠ `RoleManagement` 의 목록 호출은 `useEffect(() => { E && !zn(z) && y(); })`
 *      안에 있다. `E` = 한 쪽에 몇 줄(`pageSize`) · `zn` = 「빈 객체인가」.
 *   ㉡ `E` 는 표가 **제 설정(grid config)** 을 받은 뒤에야 채워진다:
 *      `useEffect(() => { u0?.pagination_size && f && W(Number(u0.pagination_size)); })`
 *   ㉢ 그 설정은 `U2({activeSubItemSession, userId, menuId, activeTabSession})` 이
 *      가져오고, 그 호출은 이 조건 아래 있다:
 *        `x0 && !A1 && (activeSubItemSession || activeItemSession)
 *              && userInfo?.id && k1?.id`
 *   ㉣ `k1 = getMenuByMainIdAndSubId(activeItem, activeSub, activeTab)` 이고,
 *      그 함수는 **`useMenuData()` 의 목록에서 그 id 를 찾는다.** 못 찾으면 `null`.
 *
 * ⇒ **목록에서 뗀 줄은 `k1` 이 `null` 이 되고, 그러면 설정이 안 오고, 설정이
 *   안 오면 `pageSize` 가 안 서고, `pageSize` 가 없으면 표가 제 목록을 한 번도
 *   안 부른다.** 화면은 **0행**으로 뜬다 — 「없다」와 똑같은 그림이다.
 *
 * 시각이 그것을 그대로 말한다 [온보딩 정본 `docs/agent/onboarding_48.md`]
 * ----------------------------------------------------------------------
 *     2026-09-07  `admin` 으로 `/roles` → **15개 역할 · `Add New Role` 보임** (●)
 *     2026-09-10  턴 O — 이 파일이 서고 `admin` 의 표에 `/roles` 가 **없다**
 *     2026-09-17  `admin` 으로 `/roles` → **표 행 0 · `Add New Role` 없음** (○)
 *
 * ⇒ U5#2 는 인수 자산의 결함도 dj-core 의 결함도 아니다. **우리가 턴 O 에 낸
 *   퇴행**이고, 그 사실이 넉 달 동안 「빈 표」로만 보였다.
 *
 * ★ 같은 뿌리에 걸린 빨강이 U5#2 하나가 아니다(다른 차선 소유 · 쪽지로 알린다):
 *     U4#11 `/device`         — U4 표에 없다 → 0행  (턴 T 는 「권한」으로 적었다)
 *     U2#6  `/report-template` — 인수 넷에 들어 있다 → 0행
 * ★ 반대 증거도 같은 표가 준다: `/users`(menuId 3)는 **U5 표에 있어** 목록에
 *   남았고, 같은 인수 표인데 **29명 + `Add New User` 가 그려진다**(09-07 · 턴 AA
 *   재확인). 남긴 줄은 서고 뗀 줄은 안 선다 — 갈린 것은 표에 있느냐뿐이다.
 *
 * 그래서 무엇을 고쳤나 — **뗀 것을 되돌리지 않는다. 서 있는 자리만 남긴다**
 * ------------------------------------------------------------------------
 * 사이드바에서 넷을 떼는 결정은 그대로다(P-220 · 고객 화면에 인수 자산 0).
 * 다만 **지금 그 주소에 서 있는 동안에는** 그 줄을 목록에 남긴다. 그러면
 * `k1` 이 서고 표가 제 목록을 부른다.
 *
 * ⚠ **값을 치르는 것을 숨기지 않는다**: 그 화면에 서 있는 동안 사이드바에 줄이
 *   **하나 는다**(예: `/roles` 에서 U5 는 7 → 8). 서 있는 자리를 사이드바가
 *   보여 주는 것은 거짓이 아니고, 떠나면 다시 7 이 된다. 역할 홈에서 세는
 *   「메뉴 ≤ 7」은 그대로다.
 * ⚠ **권한을 열지 않는다.** 목록에 줄을 남기는 것은 화면 결정이고, 그 화면이
 *   부르는 문은 전부 서버가 판정한다(SEC-11a · P-105). 남의 테넌트 역할이
 *   보이는 일은 이 함수로 생기지 않는다 — 서버가 `path_permission` 으로 막는다
 *   (`core/role/permission.py` · 권한 없는 계정은 `ListRealityNote` 가 「볼
 *   권한이 없습니다」로 말한다).
 */

/** 주소 하나를 비교할 수 있는 모양으로. **주소가 아닌 것은 빈 문자열**이다. */
function normalizeNavPath(p: unknown): string {
  const s = String(p ?? '').trim();
  if (!s.startsWith('/')) return '';
  const cut = s.split('?')[0].split('#')[0];
  return cut.length > 1 && cut.endsWith('/') ? cut.slice(0, -1) : cut;
}

/**
 * 이 주소를 여는 **메뉴 줄**을 나무 전체에서 찾는다. 없으면 `null`.
 *
 * ★ 정확히 같은 주소를 **먼저** 본다. 없으면 `…/123` 같은 자식 주소를 위해
 *   **가장 긴 앞자리**를 쓴다 — 짧은 쪽부터 쓰면 `/` 가 모든 주소를 삼킨다.
 * ★ 유사도·밑줄 눕히기는 **안 한다**(`roleNames.ts` 와 같은 규율).
 */
export function menuForPath(
  menus: readonly MenuNode[],
  pathname: string,
): MenuNode | null {
  const want = normalizeNavPath(pathname);
  if (!want) return null;

  const flat: MenuNode[] = [];
  const walk = (nodes: readonly MenuNode[]) => {
    for (const m of nodes) {
      if (!m) continue;
      flat.push(m);
      const kids = (m.sub_menus || (m.children as MenuNode[] | undefined)) ?? [];
      if (Array.isArray(kids) && kids.length) walk(kids);
    }
  };
  walk(menus);

  let best: MenuNode | null = null;
  let bestLen = -1;
  for (const m of flat) {
    const p = normalizeNavPath(m.path);
    if (!p) continue;
    if (p === want) return m;
    if (want.startsWith(`${p}/`) && p.length > bestLen) {
      best = m;
      bestLen = p.length;
    }
  }
  return best;
}

/**
 * 잘라 낸 목록에 **지금 서 있는 주소의 줄**을 되돌려 놓는다.
 *
 * 순수 함수다 — 시험이 이것만으로 전부 잰다. 원본 배열을 안 건드린다.
 * 되돌린 줄은 **뿌리로 올린다**(`upper_id: null` · `depth: 0` · 마디 비움) —
 * `filterNav` 가 남긴 줄에 하는 것과 **같은 모양**이다. 그 모양이 실제로 서는
 * 것은 `/users`(menuId 3)가 이미 증명했다.
 *
 * @returns `restored` 는 되돌린 주소(없으면 `null`) — 부르는 쪽이 적을 수 있게.
 */
export function withCurrentPath(
  filtered: readonly MenuNode[],
  original: readonly MenuNode[],
  pathname: string,
): { menus: MenuNode[]; restored: string | null } {
  const out = filtered.slice();
  const here = menuForPath(original, pathname);
  // 서버가 이 주소의 줄을 애초에 안 줬다. **없는 줄을 지어내지 않는다** —
  // 지어낸 id 로는 인수 표가 제 설정을 못 찾고, 0행은 그대로 남는다.
  if (!here) return { menus: out, restored: null };
  // 이미 남아 있다. 표에 있는 줄이거나, 두 번 부른 것이다.
  if (menuForPath(out, pathname)) return { menus: out, restored: null };

  out.push({
    ...here,
    sub_menus: [],
    children: [],
    upper_id: null,
    depth: 0,
    // **맨 아래**에 둔다 — 표가 정한 순서를 이 줄이 밀지 않는다.
    ordering: 2000,
  });
  return { menus: out, restored: normalizeNavPath(here.path) };
}

/**
 * ② **안 건 자리** — CPO 표에 있으나 여는 화면이 없어서 못 건 줄들.
 *   선언이다. 세는 사람이 「깜빡했다」와 「안 걸기로 했다」를 갈라 읽어야 한다.
 */
export const NAV_NO_SCREEN_YET: Record<string, string> = {
  '보고서 (U4)': '월간 1쪽은 서버가 낸다. 그리는 화면이 라우터에 없다 (P61_NO_SCREEN_YET)',
  '처리 기록 (U4)': '감사·처리 이력을 읽는 화면이 없다 (P61_NO_SCREEN_YET 「감사 기록」)',
  // ★ [턴 AA · U56] **이 줄은 이제 사유가 다르다.** 화면은 섰다 —
  //   `/dsm/notify`(턴 S) · `/dsm/integrations`(턴 T) 둘 다 `App.tsx` 에 등록돼 있고
  //   주소로 열린다. 못 거는 이유는 **dj-core `Menu` 에 그 경로의 행이 없어서**다:
  //   `filterNav` 는 서버가 안 준 줄을 `menuId`(DB 에 실재하는 행의 id)로만 세우고,
  //   없는 수를 지어 넣으면 인수 사이드바가 `?menuId=` 로 옮겨 갈 때 그 주소가
  //   거짓이 된다. [실측 2026-09-21] 우리 층 행은 #132~#142 뿐이고 `/dsm/notify` ·
  //   `/dsm/integrations` 의 행은 **없다.**
  //   ⚠ 면제가 아니라 **선언**이다. 행이 서는 턴에 위 U5 표에 두 줄이 는다
  //     (그날에도 U5 는 ≤ 7 이어야 하므로 두 줄을 넣으며 두 줄을 더 뗀다).
  '알림 받는 사람 (U5)': '화면은 있다(`/dsm/notify` · 턴 S). dj-core Menu 에 그 경로의 행이 없어 못 건다',
  '외부 연계 (U5)': '화면은 있다(`/dsm/integrations` · 턴 T). dj-core Menu 에 그 경로의 행이 없어 못 건다',
};

/** 사이드바에서 **뺐지만 주소로는 그대로 열리는** 자리. 가림은 자물쇠가 아니다. */
export const NAV_HIDDEN_BUT_REACHABLE =
  '이 목록에 없는 화면도 주소로는 그대로 열립니다. 여는 권한은 서버가 판정합니다 (SEC-11a · P-105).';

/** 인수 사이드바가 읽는 한 줄의 모양. **우리가 만드는 것이 아니라 받는 것이다.** */
export interface MenuNode {
  id: number;
  menu_name: string;
  path: string;
  icon_name?: string;
  sub_menus?: MenuNode[];
  [k: string]: unknown;
}

/** 역할 코드 목록 하나를 사람 하나로. **모르면 `null`** — 모르는 것을 아는 척하지 않는다. */
export function bucketOf(roleCodes: readonly string[]): NavBucket | null {
  const codes = roleCodes.map((c) => String(c || '').trim().toLowerCase());
  // 넓은 쪽부터 본다: 한 계정이 여러 역할을 가지면 **더 넓은 자리**를 준다.
  const order: NavBucket[] = ['U5', 'U2', 'U4', 'U1'];
  for (const b of order) {
    if (NAV_ROLE_CODES[b].some((c) => codes.includes(c))) return b;
  }
  return null;
}

/**
 * `userInfo` 에서 역할 코드를 꺼낸다. **모양을 하나로 가정하지 않는다** —
 * dj-core 는 자리에 따라 문자열 배열로도, 객체 배열로도 준다.
 */
export function roleCodesOf(userInfo: unknown): string[] {
  if (!userInfo || typeof userInfo !== 'object') return [];
  const roles = (userInfo as { roles?: unknown }).roles;
  if (!Array.isArray(roles)) return [];
  const out: string[] = [];
  for (const r of roles) {
    if (typeof r === 'string') {
      out.push(r);
    } else if (r && typeof r === 'object') {
      const o = r as Record<string, unknown>;
      const v = o.code ?? o.role_code ?? o.name ?? o.role;
      if (typeof v === 'string') out.push(v);
    }
  }
  return out;
}

/**
 * 두 목록이 **같은 사이드바를 그리는가.** 같으면 다시 쓰지 않는다(무한 갱신 방지).
 *
 * ★★ [턴 AB · U56] **나무 끝까지 센다.** 종전 판은 뿌리 줄만 보고 자식은
 *   **수만** 셌다. 그러면 자식의 자식이 바뀐 것을 못 본다 — 「같다」로 읽고
 *   안 쓰면 `hideAcquired` 가 그 깊이에서는 **한 번도 안 걸린다.**
 *   이 함수는 이제 이 파일의 유일한 「끝났는가」 판정이므로(두 갈래가 모두
 *   이것만 본다) 못 보는 깊이가 있으면 안 된다.
 */
export function navSignature(menus: readonly MenuNode[]): string {
  const one = (m: MenuNode): string => {
    const kids = (m.sub_menus || (m.children as MenuNode[] | undefined)) ?? [];
    const inner = Array.isArray(kids) && kids.length
      ? `(${kids.map(one).join(',')})`
      : '';
    return `${m.id}:${m.menu_name}:${m.path}${inner}`;
  };
  return menus.map(one).join('|');
}

/**
 * ③ **표대로 자른다.** 순수 함수다 — 시험이 이것만으로 전부 잰다.
 *
 * 규칙 셋:
 *   ① 표에 있는 경로만 남긴다. 나머지는 **가린다**(지우지 않는다 — 원본 배열은 그대로다).
 *   ② 남긴 줄의 이름을 표의 한국어로 바꾼다. 마디(`sub_menus`)는 **비운다** —
 *      우리 줄은 전부 뿌리 줄이고, 인수 마디를 달고 오면 그 안이 다시 영문이 된다.
 *   ③ 표에 있는데 서버가 안 준 줄은 **세운다.** id 는 DB 에 실재하는 행의 것이다.
 */
export function filterNav(
  menus: readonly MenuNode[],
  bucket: NavBucket,
): MenuNode[] {
  const wanted = NAV_ALLOW[bucket];
  const byPath = new Map<string, MenuNode>();
  /*
   * ★★ **나무를 다 뒤진다 — 뿌리만 보면 남의 마디 밑에 있는 우리 줄을 못 찾는다.**
   *   [실측 2026-09-10 턴 O] `/users` 는 dj-core 에서 뿌리가 아니라 『Admin』(#2) 의
   *   **자식**이다. 뿌리만 훑던 첫 판은 그것을 못 찾아 같은 id 로 **새 줄을 세웠고**,
   *   새로 세운 줄에는 그 행의 `tabs` 도 `role_permissions` 도 없었다. 인수 화면 몇은
   *   그 두 칸을 보고 자기 표를 그린다 — 없으면 **아무것도 안 그린다**.
   *   즉 「못 찾았다」가 조용히 「빈 화면」이 된다.
   */
  const walk = (nodes: readonly MenuNode[]) => {
    for (const m of nodes) {
      if (!m) continue;
      if (typeof m.path === 'string' && !byPath.has(m.path)) byPath.set(m.path, m);
      const kids = (m.sub_menus || (m.children as MenuNode[] | undefined)) ?? [];
      if (Array.isArray(kids) && kids.length) walk(kids);
    }
  };
  walk(menus);

  const out: MenuNode[] = [];
  wanted.forEach((row, i) => {
    const found = byPath.get(row.path);
    if (found) {
      // 받은 행을 **그대로 쓰고** 이름과 마디만 바꾼다. 권한 칸은 서버 것이 남는다.
      out.push({
        ...found,
        menu_name: row.label,
        sub_menus: [],
        children: [],
        // 남의 마디 밑에 있던 줄을 **뿌리로 올린다.** 마디를 함께 끌고 오면
        // 그 마디(예: 『Admin』)까지 사이드바에 서고, 그 마디는 우리 것이 아니다.
        upper_id: null,
        depth: 0,
        // 순서는 표 순서다. 인수 정렬(`ordering`)이 우리 순서를 흔들지 않게 못 박는다.
        ordering: -2000 + i,
      });
      return;
    }
    if (row.menuId === undefined) return;
    // 서버가 안 준 줄. **DB 에 있는 행 하나를 이 역할의 화면에 세운다.**
    out.push({
      id: row.menuId,
      menu_name: row.label,
      path: row.path,
      icon_name: row.iconName,
      sub_menus: [],
      children: [],
      tabs: [],
      depth: 0,
      upper_id: null,
      ordering: -2000 + i,
      // 읽기만 켠다 — 사이드바에 서기 위한 최소값이고, 실제 판정은 서버가 한다.
      role_permissions: [
        {
          permit_read: true,
          permit_create: false,
          permit_update: false,
          permit_delete: false,
          permit_export: false,
          permit_import: false,
        },
      ],
    });
  });
  return out;
}
