/**
 * P-105 — **역할이 0개인 계정이 볼 수 있는 화면은 하나다.** (2026-09-07 턴 M · 차선 C)
 *
 * 무엇이 문제였나 [실측 2026-09-07 · 계정 `gxprobe_e2e` · `user.roles` = `[]`]
 * ---------------------------------------------------------------------------
 * 역할이 하나도 없는 계정으로 로그인해 28개 경로의 API 를 그대로 다시 두드렸다.
 * **거의 전부가 HTTP 200 이었다** — 그리고 그 200 안에는 실제 자료가 들어 있었다:
 *
 *     GET /api/dsm/events?limit=200          → 200 · 이벤트 **22건**
 *                                              (카메라 이름 · 발생 시각 · 스냅숏 경로)
 *     GET /api/stream-monitors/stream-monitors → 200 · 카메라 대장
 *                                              (RTSP 주소 · 소속 그룹 이름)
 *
 * 403 이 난 자리는 28개 중 **셋뿐**이었다(`surveillance-dashboard` 7건 ·
 * `configuration-management` 1건 · `flight-log-analysis` 1건).
 * 근거: `docs/agent/evidence/P-105/frontend/before_roleless_api.json` [실측].
 *
 * 즉 **막는 일은 서버가 해야 하고 아직 하지 않았다.** 이 파일은 그 일을 대신하지
 * 않는다 — 앞단의 가림은 자물쇠가 아니다. 이 파일이 하는 일은 **막힌 뒤에 사람이
 * 읽을 화면 하나**를 정하는 것이다. 서버가 403 을 내기 시작해도 사람이 보는 것이
 * 「빈 표 33장」이면 아무것도 나아지지 않는다.
 *
 * 제품 결정 (CPO · 온보딩 표 0행)
 * -------------------------------
 *   역할이 없는 계정이 볼 수 있는 화면은 **정확히 하나**다:
 *     「역할이 아직 없습니다 · 관리자(이름)에게 역할 부여를 요청했습니다」
 *   그리고 관리자에게 **알림이 한 번** 간다. 나머지는 전부 403 → 전역 거절 처리기.
 *
 * ★★ 이 파일이 지키는 규율 하나 — **모르는 것을 아는 척하지 않는다**
 * ------------------------------------------------------------------
 * 위 문장은 앞단이 모르는 사실을 **둘** 주장한다:
 *     ① 내 관리자가 **누구**인가 (이름)
 *     ② 그에게 요청이 **갔다**   (「요청했습니다」 — 완료된 과거다)
 * 둘 다 서버만 안다. 그래서 서버가 말해 줄 때만 그 문장을 쓴다.
 * 문이 아직 없거나(404) 답이 오지 않으면 **머리줄만** 쓰고 둘째 줄은
 * 「아직 요청이 가지 않았다」로 **내려 적는다** — 이름을 지어내거나
 * 「요청했습니다」를 조건 없이 적으면, 그것은 안내가 아니라 **거짓말**이다(D-284).
 * 안 간 알림을 갔다고 적으면 사람은 기다리기만 하고 아무도 부르지 않는다.
 *
 * ⚠ **이 가림은 권한이 아니다.** 앞단이 화면을 안 그려도 문은 그대로 열려 있고,
 *   브라우저 개발자도구로 `fetch` 한 줄이면 위의 22건이 그대로 나온다.
 *   서버가 403 을 내기 전까지 **자료는 새고 있다** — 이 파일은 그 사실을 덮지
 *   않는다. 덮으면 고칠 곳이 안 보인다(P-88 머리말과 같은 규율).
 */

/** 서버가 「나는 역할이 없다」를 말해 주는 문. 뒷단 계약은 아래 CONTRACT 참조. */
export const ROLE_PENDING_PATH = '/api/v1/auth/role-pending';

/**
 * 사전 문구 — CPO 가 정한 0행의 문장이다. **여기서 지은 것이 아니다.**
 * 화면은 이 둘을 위아래로 쓴다.
 */
export const COPY_ROLE_PENDING_HEADLINE = '역할이 아직 없습니다';

/**
 * 관리자 이름이 **왔을 때만** 쓰는 줄. `{name}` 자리에 서버가 준 이름이 들어간다.
 * 이름을 못 받으면 이 줄을 쓰지 않는다 — 「관리자()에게」는 문장이 아니다.
 */
export function copyRequestedTo(name: string): string {
  return `관리자(${name})에게 역할 부여를 요청했습니다`;
}

/**
 * 요청이 **가지 않았을 때**의 둘째 줄. 위 문장의 자리를 비워 두지 않되,
 * 가지도 않은 요청을 갔다고 적지 않는다.
 */
export const COPY_NOT_REQUESTED =
  '아직 역할 부여를 요청하지 못했습니다. 관리자에게 직접 알려 주세요.';

/** 「그래서 지금 무엇을 볼 수 있나」 — 결과를 한 줄로 적는다. */
export const COPY_CONSEQUENCE =
  '역할을 받기 전까지 이 계정으로 열 수 있는 화면은 이 화면뿐입니다.';

/** 서버가 준 관리자. **이름이 없으면 이 객체를 만들지 않는다.** */
export interface RolePendingAdmin {
  name: string;
  email?: string | null;
  department?: string | null;
}

export interface RolePendingState {
  /** 서버가 「이 계정은 역할 대기 중」이라고 답했나. */
  pending: boolean;
  /** 누구에게 요청했나. 서버가 못 정하면 `null` — 그때는 이름을 쓰지 않는다. */
  admin: RolePendingAdmin | null;
  /** 알림이 **실제로 나갔나.** 이 값이 참일 때만 「요청했습니다」를 쓴다. */
  notified: boolean;
}

/**
 * 이 계정에 역할이 **하나도 없는가.**
 *
 * ★ **모르는 동안에는 거짓이다.** `userInfo` 가 아직 안 왔을 때(로그인 직후·새로고침
 *   직후) `roles` 는 `undefined` 다. 그 자리를 「역할 없음」으로 읽으면 역할이 있는
 *   사람도 이 화면을 한 번 보고 지나간다 — 깜빡임이 아니라 **틀린 판정**이다.
 *   그래서 **배열이면서 길이가 0** 일 때만 참이다.
 *
 * ★ 로그인하지 않은 사람에게도 거짓이다. `userInfo` 가 없으면 판정하지 않는다 —
 *   그 사람은 관문(`PrivateRouter`)이 `/login` 으로 보낼 사람이고, 여기서
 *   가로채면 로그인 화면 대신 이 화면이 뜬다.
 */
export function hasNoRoles(userInfo: unknown): boolean {
  if (!userInfo || typeof userInfo !== 'object') return false;
  const roles = (userInfo as { roles?: unknown }).roles;
  if (!Array.isArray(roles)) return false;
  return roles.length === 0;
}

/** 서버의 답에서 화면이 쓸 것만 추린다. 모양이 어긋나면 **안전한 쪽**으로 떨어진다. */
export function readRolePending(body: unknown): RolePendingState {
  const safe: RolePendingState = { pending: true, admin: null, notified: false };
  if (!body || typeof body !== 'object') return safe;
  const b = body as Record<string, unknown>;

  const rawAdmin = b.administrator;
  let admin: RolePendingAdmin | null = null;
  if (rawAdmin && typeof rawAdmin === 'object') {
    const a = rawAdmin as Record<string, unknown>;
    const name = typeof a.name === 'string' ? a.name.trim() : '';
    // 이름이 없으면 관리자를 만들지 않는다 — 「관리자()에게」를 막는 자리다.
    if (name) {
      admin = {
        name,
        email: typeof a.email === 'string' ? a.email : null,
        department:
          typeof a.department === 'string' ? a.department : null,
      };
    }
  }

  return {
    pending: b.role_pending !== false,
    admin,
    // 알림이 **나갔다고 서버가 말할 때만** 참이다. 없으면 거짓 — 기본값이 거짓인
    // 것이 이 칸의 전부다(모르면 「안 갔다」로 적는다).
    notified: b.notified === true && admin !== null,
  };
}
