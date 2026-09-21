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
 *   없었다**:
 *
 *     [실측 2026-09-21 17:5x · ORM · role.Role 전수 16종]
 *       superuser · user · admin · operator · order · delivery_operation ·
 *       delivery_order · view_only_-_anyang · drone_robot_user ·
 *       drone_robot_admin · fire_user · fire_admin · surveillance_order ·
 *       surveillance_operation · delivery_admin · tenant_admin_4
 *
 *   즉 사전 넷 중 **둘(`fire_user`·`fire_admin`)만 실재하는 코드**였고,
 *   고객이 실제로 본 `view_only_-_anyang` 은 **사전에 없었다.** 그래서 이 파일은
 *   **안 이었다** — 판정을 청했다.
 *
 * ══════════════════════════════════════════════════════════════════════════
 * ★★ 턴 AB — **정정판이 왔다** (WO-GX-20260921-04 §4-2 · P-233 · 세종 오기 인정)
 * ══════════════════════════════════════════════════════════════════════════
 *
 * 세종이 `view_only`·`sysop` 오기를 인정하고 **실측 코드로 정정판**을 냈다. 그
 * 정정판을 여기 등재한다. **등재하기 전에 다시 쟀다** — 지시서도 입력이지 측정이
 * 아니기 때문이다(턴 AB 규약):
 *
 *     [실측 2026-09-21 · ORM · `role.Role` 전수 **16종** · `id / role_name / code`]
 *        1 SuperUser              superuser
 *        3 User                   user
 *        4 admin                  admin
 *        5 operator_etri          operator
 *        6 order_etri             order
 *        7 delivery operation     delivery_operation
 *        8 delivery order         delivery_order
 *        9 View Only - Anyang     view_only_-_anyang
 *       10 drone_robot_user       drone_robot_user
 *       11 drone_robot_admin      drone_robot_admin
 *       12 fire_user              fire_user
 *       13 fire_admin             fire_admin
 *       17 Surveillance Order     surveillance_order
 *       18 Surveillance Operation surveillance_operation
 *       22 delivery admin         delivery_admin
 *       28 tenant_admin_4         tenant_admin_4
 *
 *   ⇒ **§4-2 의 코드 여덟은 `code` 칸과 한 자도 안 틀린다.** 등재한다.
 *   ⚠ 다만 **`role_name` 은 `code` 가 아니다** — `operator_etri` · `order_etri` ·
 *     `View Only - Anyang` · `Surveillance Order` 처럼 다르다. 이 사전의 열쇠는
 *     **`code`** 이고, `role_name` 을 여기에 대면 전부 「표시명 없음」이 된다.
 *     부르는 쪽이 무엇을 넘기는지가 이 사전의 정확도를 정한다.
 *
 * ★ **표 밖 여덟은 그대로 비운다**(`order` · `delivery_operation` ·
 *   `delivery_order` · `delivery_admin` · `drone_robot_user` ·
 *   `drone_robot_admin` · `surveillance_order` · `surveillance_operation`).
 *   16 − 8(등재) = **8**이다. §4-2 는 이 묶음을 「인수 9종」이라 적었으나
 *   **세면 여덟**이다 — 수를 옮기지 않고 센 수를 적는다.
 *
 * ⚠ **`surveillance_*` 둘은 이 저장소에서 이미 사람이 정해져 있다** — 그런데
 *   §4-2 는 그 둘을 「표시명 없음 · GX 테넌트 배정 금지」 묶음에 넣었다:
 *     · `features/nav/roleNav.ts` `NAV_ROLE_CODES` — `surveillance_operation`→U1 ·
 *       `surveillance_order`→U2 (사이드바 5줄·7줄 · 영어 칸 0)
 *     · `backend/config/k3_roles.py` — `K3_ROLE_OPERATORS` · `K3_ROLE_MANAGERS`
 *   **두 말이 갈린다.** 이 파일은 §4-2 를 따르고(표시명 없음), 갈린 사실을
 *   보고와 쪽지에 적는다 — 조용히 한쪽으로 맞추면 다음 사람이 어느 쪽이 정본인지
 *   모른다(D-212).
 */

/**
 * ① 사전 — **§4-2 정정판 여덟.** 순서는 조직의 위아래가 아니라 §4-2 의 줄 순서다.
 *
 * ★ 문구의 정본은 `docs/design/GX-COPY_v1.md` 이고 그 파일은 **조율자가 병합**한다.
 *   이 표는 그 문구를 화면에 대는 자리이고, 두 곳이 어긋나면 사전이 정본이다.
 * ★ 열쇠는 **`role.Role.code`** 다(위 실측 표의 오른쪽 칸). `role_name` 이 아니다.
 */
export const ROLE_DISPLAY_NAMES: Readonly<Record<string, string>> = {
  fire_user: '관제요원',
  fire_admin: '관제팀장',
  'view_only_-_anyang': '지자체 담당',
  admin: '기관 관리자',
  tenant_admin_4: '기관 관리자(테넌트)',
  superuser: '플랫폼 운영자',
  operator: '운영 담당',
  user: '일반 사용자',
};

/**
 * ★ **표시명을 일부러 비운 코드** — 「깜빡했다」와 「안 붙이기로 했다」를 가른다.
 *
 * 값은 **왜 비웠는가**다. 화면은 이 표를 읽지 않는다(읽으면 그 사유가 고객 화면에
 * 뜬다) — 이것은 **다음 사람을 위한 선언**이고, 시험이 「사전 + 이 표 = 16종」을
 * 잴 수 있게 하는 자리다. 면제가 아니라 선언이다(`roleNav.NAV_NO_SCREEN_YET` 규율).
 */
export const ROLE_NAMES_BLANK_BY_DECISION: Readonly<Record<string, string>> = {
  order: '인수 자산(배송 주문) — 이 제품의 역할이 아니다 (§4-2 · P-229)',
  delivery_operation: '인수 자산(배송 운용) — 위와 같다',
  delivery_order: '인수 자산(배송 주문) — 위와 같다',
  delivery_admin: '인수 자산(배송 관리) — 위와 같다',
  drone_robot_user: '인수 자산(드론·로봇) — 위와 같다',
  drone_robot_admin: '인수 자산(드론·로봇) — 위와 같다',
  surveillance_order:
    '§4-2 가 「표시명 없음」으로 두었다. ⚠ roleNav·k3_roles 는 이 코드를 U2(관제팀장)로 잇는다 — 갈린 자리',
  surveillance_operation:
    '§4-2 가 「표시명 없음」으로 두었다. ⚠ roleNav·k3_roles 는 이 코드를 U1(관제요원)으로 잇는다 — 갈린 자리',
};

/** 표시명이 없을 때 화면에 뜨는 말. **코드가 아니다.** */
export const ROLE_NAME_UNKNOWN = '표시명 없음';

/**
 * ② 표시명 하나. **모르면 「표시명 없음」** — 코드를 그대로 내보내지 않는다.
 *
 * 대소문자와 앞뒤 공백만 눕힌다. 그 이상(접두 일치 · 밑줄 제거 · 유사도)은
 * **하지 않는다** — 그 순간 `tenant_admin_4` 가 `tenant_admin` 으로, `admin` 이
 * `delivery_admin` 으로 읽히고, 그것이 바로 이 파일이 막으려는 추측이다.
 *
 * ★ 턴 AB 정정판 뒤에도 이 규칙은 **그대로다.** 정정으로 사라진 것은 틀린 줄
 *   (`view_only`·`sysop`)이지 규칙이 아니다. 실제로 이 규칙이 없었다면
 *   `view_only_-_anyang` 이 턴 AA 에 `view_only` 의 표시명을 달고 나갔을 것이고,
 *   그때 세종의 오기는 **화면에서 안 보였을 것**이다. 규칙이 오기를 드러냈다.
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
