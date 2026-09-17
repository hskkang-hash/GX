/**
 * 2파 DSM 화면들의 경로 — **한 곳에서만 정한다** (차선 C · 2026-09-24).
 *
 * ★ `services/API.ts` 의 `CustomRoutes` 에 넣지 않은 이유: 그 파일은 여러 차선이
 *   같이 쓰는 공용 자리다. 이번 파에 S·Q·E3·C 넷이 동시에 도니까 그 파일을 고치면
 *   병합에서 충돌하고, 충돌한 쪽은 대개 **경로 문자열**이며 그 충돌은 **라우팅 침묵**으로
 *   나타난다 — 화면이 안 뜨는데 오류도 안 난다. 차선 D 가 `features/mobile/routes.ts` 로
 *   같은 판단을 이미 했고, 여기서도 같게 한다.
 *
 * ★ **무계정 링크 금지**(불변 제약). 이 셋은 전부 `PrivateLayout` + `Sidebar` 아래에
 *   등록한다 — 토큰이 없으면 `/login` 으로 튕긴다.
 *
 * ⚠ 기존 `/dsm/events/:id` 보다 **뒤에 오지 않게** 한다. `:id` 는 변수 조각이라
 *   `/dsm/events/queue` 같은 리터럴을 삼킬 수 있다 — 그래서 큐는 `/dsm/queue` 로
 *   **다른 가지**에 둔다. 삼킬 수 없는 자리에 두는 것이 순서를 외우는 것보다 안전하다.
 */
export const dsm2Routes = {
  /** UX-13 단일 초점 큐. W1 최상단이 목록이 아니라 「가장 급한 하나」가 되는 화면. */
  focusQueue: { title: '단일 초점 큐', path: '/dsm/queue' },
  /** UX-17 훈련 모드 스위치 + 종료 보고서. */
  drill: { title: '훈련 모드', path: '/dsm/drill' },
  /** UX-18 벌크 등록 (dry-run 먼저). */
  cameraImport: { title: '카메라 벌크 등록', path: '/dsm/cameras/import' },
  /**
   * UX-02 관리 화면 — 카메라 한 대의 설치 주소를 **화면에서** 채운다.
   * ⚠ `/dsm/cameras/import` 와 형제다. 변수 조각이 없으므로 서로 삼키지 않는다.
   */
  cameraAddress: { title: '카메라 주소 채우기', path: '/dsm/cameras/address' },
  /**
   * UX-03 온보딩 — 「처음 시작하기」.
   *
   * ★ 이 하나만 **관문 밖**에 선다. 로그인 화면의 「처음이세요?」가 여기로 오기
   *   때문이다 — 관문 안에 두면 처음 오는 사람이 못 본다.
   *   그래도 규약을 안 깬다: 이 화면은 **사용자 자료를 한 건도 부르지 않는다**
   *   (서버 호출 0건 · 정적 글자뿐). 무계정 금지는 자료를 보이는 링크의 규약이다.
   */
  onboarding: { title: '처음 시작하기', path: '/start' },
  /**
   * UX-16 월(Wall) 모드 — 관제실 대형 화면.
   *
   * ★ 이 하나만 **사이드바 밖**에 선다(관문은 그대로 안). 대형 화면에는 마우스가 없고,
   *   사이드바는 마우스를 전제한 물건이다. 관문 밖으로 내보내지는 않는다 —
   *   화면에 실제 사건이 뜨기 때문이다(무계정 링크 금지).
   * ⚠ 최상위 리터럴이라 `/dsm/...` 어느 변수 조각도 삼키지 못한다.
   */
  wall: { title: '월 모드', path: '/wall' },
  /**
   * UX-23 카메라 격자 — 자동 순회 · 응답 없는 카메라 표시.
   * ⚠ `/dsm/cameras/import` · `/dsm/cameras/address` 와 형제다(변수 조각 없음).
   */
  cameraGrid: { title: '카메라 격자', path: '/dsm/cameras/grid' },
  /**
   * S-10 카메라 오탐률·임계값 — 차선 U24 가 `routes.u24.ts` 로 넘긴 조각을
   * 조율자가 여기 병합했다 (턴 S · WO-01 §4.2).
   *
   * ⚠ `/dsm/cameras/import` · `/dsm/cameras/address` · `/dsm/cameras/grid` 와
   *   **형제다**(변수 조각 없음 — 서로 삼키지 않는다). 이 가지 아래에
   *   `/dsm/cameras/:id` 같은 변수 경로를 만들지 말 것: 그 순간 순서가 곧
   *   라우팅이 되고, 삼켜진 경로는 **조용한 404** 로 나타난다(D-410).
   * ⚠ 조각 파일만으로는 화면이 안 열린다 — `App.tsx` 등록이 짝이다. 둘 다 서야
   *   주소가 산다.
   */
  cameraTuning: { title: '카메라 오탐률·임계값', path: '/dsm/cameras/tuning' },
  /**
   * LAW-07 개인정보 열람·삭제 청구 — 접수 → 마스킹본 조회 → 회신 기록.
   * ★ 원본은 이 화면을 통해 나가지 않는다. 화면이 부르는 것은 **마스킹본**뿐이다.
   */
  privacyRequests: { title: '열람·삭제 청구', path: '/dsm/privacy-requests' },
  /**
   * OPS-16 계량 표 — 이번 달 우리 센터가 얼마나 썼나. 관리자 자리.
   * ★ 세는 화면이지 만드는 화면이 아니다 — 여기서 아무것도 생성하지 않는다.
   */
  metering: { title: '이번 달 사용량', path: '/dsm/metering' },
  /**
   * P-67 보존·백업 선언 — **U5 관리자 자리.** 선언하지 않은 항목에 빨강 배지가 뜨고,
   * 그 상태에서는 파기도 백업도 돌지 않는다.
   * ⚠ `/dsm/metering` 과 형제다(변수 조각 없음 — 서로 삼키지 않는다).
   */
  systemSettings: { title: '보존·백업 설정', path: '/dsm/system' },
  /**
   * UX-35 요원별 처리 현황 — **골격** (차선 U24 · 턴 R). `stats.by-reviewer` 를 그대로 연다.
   * ⚠ `/dsm/metering` · `/dsm/system` 과 형제다(변수 조각 없음 — 서로 삼키지 않는다).
   */
  teamStatus: { title: '요원별 현황', path: '/dsm/team-status' },
  /**
   * P-147 역할 홈 2단계 — **홈은 목록이 아니다** (턴 R · 차선 F).
   * 한 라우트이고 역할마다 다른 띠를 그린다(부속서 A S-01b·c·d 가 셋 다 이 경로로 적었다).
   *
   * ⚠ `/dsm/events/:id` 의 변수 조각 밑이 아니다 — 다른 가지라 서로 삼키지 않는다.
   * ★ U1 의 홈은 여기가 아니라 `/dsm/queue` 그대로다 — 이미 선 자리를 옮기지 않는다.
   */
  roleHome: { title: '역할 홈', path: '/dsm/home' },
  /**
   * S-14 「사람·역할」 — 계정 만들기 · 비활성화 (턴 R · 차선 U56 · UX-42).
   * ⚠ `/dsm/system` · `/dsm/team-status` 와 형제다(변수 조각 없음 — 서로 삼키지 않는다).
   */
  people: { title: '사람·역할', path: '/dsm/people' },
  /**
   * S-16 「알림 받는 사람·채널」 (턴 R 골격 → **턴 S 실자료** · 차선 U56 · UX-43).
   * 등급 × 역할 × 채널 · 심각 0명 저장 금지 · 시험 발송(훈련 채널).
   * ⚠ 위와 같은 이유로 형제 경로들과 삼키지 않는다.
   */
  notifySettings: { title: '알림 받는 사람·채널', path: '/dsm/notify' },
  /**
   * S-15 「내 정보」 — 나는 누구이고 무엇을 받는가 (턴 S · 차선 U56 · UX-42-me).
   *
   * ⚠ `/dsm/notify` · `/dsm/people` 과 형제다(변수 조각 없음 — 서로 삼키지 않는다).
   * ★ 인수 자산의 `/profile` 을 **대신하지 않는다.** 그 화면은 그대로 두고, 이것은
   *   우리 층의 「내 정보」다 — 역할 홈이 못 정할 때 가는 기본값이 여전히 `/profile`
   *   이므로(`features/nav/roleHome.ts`) 그 자리를 옮기면 첫 화면 규칙이 바뀐다.
   */
  me: { title: '내 정보', path: '/dsm/me' },
} as const;
