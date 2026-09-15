/**
 * P-141 · P-131 · UX-32 — **로그인 뒤 첫 화면은 역할의 홈이다.** (턴 Q · 차선 F)
 *
 * 정본 사양: `docs/agent/evidence/P-131/역할_홈_사양.md` — 재검토하지 않는다(WO-01 §2).
 * 이 파일은 그 사양의 §3 규칙을 **한 곳에** 적는다. 부르는 자리는 셋이고 셋 다 이것만 부른다:
 *   ① `features/login/LoginDesktop.tsx` (로그인 직후)
 *   ② `App.tsx` 의 `RootRedirect`       (`/` 로 들어온 사람)
 *   ③ `features/LoginMobile/LoginMobile.tsx` (휴대전화 로그인 직후)
 * 종전에는 ①②가 같은 판단을 두 벌로 했다(사양 §1). 두 벌은 반드시 어긋난다(D-212·D-369).
 *
 * 규칙 (사양 §3)
 * --------------
 *   ① 사람이 손으로 고른 홈이 있으면 그것이 이긴다
 *        `settings.home_screen_setting__path` + `home_screen_setting_id` — 지금 규칙 그대로
 *   ② 없으면 역할의 홈 (아래 `ROLE_HOME`)
 *   ③ 역할을 못 읽으면 부르는 쪽이 준 기본값 — 지금 가던 곳(`/profile` · 휴대전화는 QR)
 *
 * ★ **역할 코드를 어디서 읽나 — 가장 흔한 실패가 여기다** [실측 · 코드]
 *   로그인 응답의 `user` 에는 역할이 **없다.** dj-core `core/api/v1/auth.py` 의
 *   `login_data`(토큰 · user_id · username · email · theme · timezone · language)에
 *   `roles` 가 없고, `roles` 는 보안 기록용 `success_payload` 에만 들어간다(같은 파일 792-797).
 *   역할은 로그인 직후 부르는 `getProfileAPI` = `GET /api/v1/user/get-user-detail/{id}`
 *   (rj-core `V1.profile` → `{success, data: body.user}`)에 실린다 — 그 응답의 스키마
 *   `UserDetailSchema` 가 `fields="__all__", depth=2` 라 `roles`(객체 배열 · `code`)가 오고,
 *   같은 값이 `permissions`(역할 코드 문자열 배열 · `ArrayAgg('roles__code')`)로 한 번 더 온다
 *   (dj-core `core/api/v1/user.py:800-875` · `schemas.py` `UserDetailSchema`).
 *   그래서 부르는 쪽은 **로그인 응답이 아니라 프로필 응답**을 먼저 넘긴다.
 *   ⚠ 휴대전화 로그인은 프로필을 받고도 **저장소에 올리지 않는다**(`updateUserInfo` 없음) —
 *     저장소의 `userInfo` 는 역할 없는 로그인 응답이다. 그래서 휴대전화는 받은 프로필을
 *     **직접** 넘긴다(저장소를 믿지 않는다).
 *
 * ★ 역할 판정 표는 **새로 만들지 않는다** — `roleNav.ts` 의 `bucketOf`/`roleCodesOf` 를 쓴다.
 *   사이드바 표와 두 벌이 되면 반드시 어긋난다(사양 §2).
 *
 * ★★ **이것은 자물쇠가 아니다.** 첫 화면을 정할 뿐이고 다른 주소는 그대로 열린다.
 *   여는 권한은 서버가 판정한다(SEC-11a · P-105 · `roleNav.ts:25-29` 와 같은 규율).
 *
 * ★ 모르면 **지어내지 않는다.** `bucketOf()` 가 `null` 이면(모르는 역할 · 역할 0) 부르는 쪽의
 *   기본값으로 간다 — 자기 것이 아닌 홈을 보여 주는 것보다 지금 가던 곳이 낫다(사양 §3).
 *   역할 0 은 어차피 `App.tsx` 의 `PrivateLayout` 이 `RolePendingScreen` 으로 가린다.
 */
import { CustomRoutes } from '@/services/API';
import { dsm2Routes } from '@/features/dsm/routes';
import { mobileRoutes } from '@/features/mobile/routes';

import { bucketOf, roleCodesOf, type NavBucket } from './roleNav';

/**
 * 역할의 홈 (사양 §2 표). 경로는 **라우트 상수에서** 읽는다 — 문자열을 여기서 짓지 않는다.
 *
 *   U1 관제요원    지금 처리할 것         `/dsm/queue`             등록 `App.tsx:681`
 *   U2 관제팀장    무슨 일 있었나(밤사이)  `/dsm/events`            등록 `App.tsx:676`
 *   U4 재난안전과  무슨 일 있었나(7일)     `/dsm/events?period=d7`  같은 화면 · `EventList.tsx:221`
 *   U5 관리자      관제 대시보드          `/dsm/dashboard`         등록 `App.tsx:673`
 *
 * ⚠ 사양 §5 의 미정 셋은 **표대로 둔다**(선언이다 · 면제가 아니다):
 *   U2 의 「밤사이」 창(12h ↔ 24h) · U4 에 `?preset=` 도 걸 것인가 · U5 홈이 대시보드가 맞는가.
 */
export const ROLE_HOME: Readonly<Record<NavBucket, string>> = {
  U1: dsm2Routes.focusQueue.path,
  U2: CustomRoutes.dsm.events.path,
  U4: `${CustomRoutes.dsm.events.path}?period=d7`,
  U5: CustomRoutes.dsm.dashboard.path,
};

/**
 * 휴대전화의 역할 홈. **U1 만 있다** — U3(현장)은 역할이 아니라 기기다(사양 §2 「U3 는 표에 없다」).
 * 나머지 역할은 휴대전화에서 지금 가던 곳(부르는 쪽의 기본값)으로 간다.
 */
export const MOBILE_ROLE_HOME: Readonly<Partial<Record<NavBucket, string>>> = {
  U1: mobileRoutes.inbox.path,
};

export type HomeDevice = 'desktop' | 'mobile';

/** 첫 화면을 **왜** 골랐는가. 증거·시험이 이 칸을 읽는다. */
export type HomeSource = 'setting' | 'role' | 'fallback';

export interface HomeDecision {
  path: string;
  source: HomeSource;
  /** 역할로 판정한 사람. 못 읽었으면 `null`. */
  bucket: NavBucket | null;
}

export interface ResolveHomeOptions {
  device: HomeDevice;
  /** ③ 모를 때 가는 곳 — **지금 가던 곳**을 부르는 쪽이 준다(`/profile` · QR). */
  fallback: string;
  /**
   * ① 사람이 고른 홈을 볼 것인가. 기본 참.
   * 휴대전화 로그인은 종전에 이 값을 **안 봤다**(언제나 QR 로 갔다) — 그 자리의 「지금 규칙」을
   * 바꾸지 않으려고 `false` 를 준다. 고른 홈은 데스크톱 메뉴 경로라 휴대전화 화면이 아니다.
   */
  honorSetting?: boolean;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

/**
 * 역할 코드를 꺼낸다 — `roleCodesOf`(`.roles`)가 먼저, 비었으면 `permissions`.
 *
 * `permissions` 는 `get-user-detail` 이 같은 역할을 **코드 문자열로** 한 번 더 싣는 칸이다
 * (`ArrayAgg(F('roles__code'))`). 새 표가 아니라 같은 값의 다른 모양이다.
 * ⚠ 역할이 0개면 `ArrayAgg` 는 `[null]` 을 준다 — 문자열만 거른다.
 */
export function homeRoleCodes(userInfo: unknown): string[] {
  const codes = roleCodesOf(userInfo);
  if (codes.length) return codes;
  const perms = asRecord(userInfo)?.permissions;
  if (!Array.isArray(perms)) return [];
  return perms.filter((p): p is string => typeof p === 'string' && p.trim() !== '');
}

/** ① 사람이 고른 홈 — **지금 규칙 그대로**(`LoginDesktop.tsx` 종전 124-130 · `App.tsx` 종전 465-474). */
function chosenHome(userInfo: unknown): string | null {
  const settings = asRecord(asRecord(userInfo)?.settings);
  const home = settings?.home_screen_setting__path;
  const homeId = settings?.home_screen_setting_id;
  if (typeof home === 'string' && home && home !== '/' && homeId) {
    return `${home}?menuId=${homeId}`;
  }
  return null;
}

/**
 * 첫 화면을 고른다. **순수 함수다** — 시험이 이것만으로 규칙 전부를 잰다.
 *
 * @param sources 사용자 정보 후보들. **앞의 것이 먼저다** — 프로필 응답(역할 있음)을
 *                로그인 응답(역할 없음)보다 앞에 둔다. 하나만 넘겨도 된다.
 */
export function resolveHome(
  sources: unknown | readonly unknown[],
  options: ResolveHomeOptions,
): HomeDecision {
  const list: readonly unknown[] = Array.isArray(sources) ? sources : [sources];
  const honorSetting = options.honorSetting ?? true;

  // ① 사람이 고른 홈
  if (honorSetting) {
    for (const s of list) {
      const chosen = chosenHome(s);
      if (chosen) {
        let bucket: NavBucket | null = null;
        for (const t of list) {
          bucket = bucketOf(homeRoleCodes(t));
          if (bucket) break;
        }
        return { path: chosen, source: 'setting', bucket };
      }
    }
  }

  // ② 역할의 홈 — 역할을 실은 첫 후보에서 읽는다
  let bucket: NavBucket | null = null;
  for (const s of list) {
    bucket = bucketOf(homeRoleCodes(s));
    if (bucket) break;
  }
  if (bucket) {
    const table = options.device === 'mobile' ? MOBILE_ROLE_HOME : ROLE_HOME;
    const path = table[bucket];
    if (path) return { path, source: 'role', bucket };
  }

  // ③ 모르면 지금 가던 곳
  return { path: options.fallback, source: 'fallback', bucket };
}
