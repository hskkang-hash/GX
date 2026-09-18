/**
 * 차선 **U24** 의 경로 조각 — 조율자가 `routes.ts` 로 병합한다 (WO-01 §4.2).
 *
 * ★ 왜 `routes.ts` 에 직접 쓰지 않나: 그 파일은 **조율자만 병합한다**(§4.2).
 *   같은 턴에 차선 다섯이 돌고, 다섯이 같은 상수 파일 끝에 각자 줄을 붙이면
 *   충돌한다 — 그리고 충돌하는 것은 대개 **경로 문자열**이며, 그 충돌은
 *   **라우팅 침묵**으로 나타난다(화면이 안 뜨는데 오류도 안 난다).
 *   그래서 차선은 조각을 만들고 조율자에게 「등록 요청 한 줄」을 보낸다.
 *
 * ⚠ **이 조각만으로는 화면이 안 열린다.** `routes.ts` 와 `App.tsx` 두 곳에
 *   등록돼야 주소가 산다. 등록 전까지 이 경로는 **회색이고, 회색은 초록이 아니다.**
 *
 * ★ 턴 T (P-164 U24 ⑤) — **정본 경로 이름**: 오탐률은 통계 축(`/dsm/stats/*`) 아래로,
 *   카메라 축(`/dsm/cameras/*`)에는 **튜닝만** 남긴다. 옛 경로 `/dsm/cameras/tuning` 은
 *   지우지 않는다 — 대장은 줄지 않는다. 화면 파일은 하나(`pages/CameraTuning.tsx`)이고
 *   두 경로가 그것을 **다른 mode 로** 가리킨다: `/dsm/stats/false-positive` 는
 *   `<CameraTuning mode="false-positive" />`(오탐률 표만) · `/dsm/cameras/tuning` 은
 *   `<CameraTuning mode="tuning" />`(표는 고르는 자리 · 시뮬·저장이 본문).
 *   부속서A 가 API 이름으로 적은 `/cameras/false-positive` 는 SPA 에서 정본으로 **redirect**.
 */

export const dsmU24Routes = {
  /**
   * S-10 「카메라 오탐률·임계값」 — **정본 경로**(턴 T · P-164 U24 ⑤): 통계 축 아래.
   * 오탐률은 집계이고, 집계는 `/dsm/stats/*` 에 산다(서버 `GET /api/dsm/stats/false-positive`
   * 와 같은 이름공간 — 화면 경로와 API 경로가 같은 말을 쓴다).
   */
  falsePositive: { title: '카메라 오탐률', path: '/dsm/stats/false-positive' },

  /**
   * 카메라 축에는 **튜닝만** 남긴다 — 같은 화면(`CameraTuning.tsx`)의 문턱·저장 절.
   * `/dsm/cameras/import` · `/dsm/cameras/address` · `/dsm/cameras/grid` 와 **형제다**
   * (변수 조각이 없다 — 서로 삼키지 않는다).
   */
  cameraTuning: { title: '카메라 임계값 튜닝', path: '/dsm/cameras/tuning' },

  /** UX-39 통계 — 축 5 · 합계 = 목록 수 · 표 내려받기(CSV). */
  stats: { title: '통계', path: '/dsm/stats' },

  /** 감사 기록 읽기 — 필터 3 · 해시 체인 · CSV · 「60초 안 도달」 계측 칸. U2·U4·U5 만. */
  auditLog: { title: '감사 기록', path: '/dsm/audit' },

  /**
   * S-18 「보고서」 — 서식 3(사건 1쪽 · 이번 달 우리 센터 · 상급 제출용) · 실행 기록 ·
   * **파일 2**(DOCX 정본 · PDF 병행) (턴 U · P-173 U24 ①⑤).
   *
   * ★ 경로가 `/dsm/reports` 인 이유: 서버의 이름공간(`/api/dsm/reports/*`)과 **같은 말**을
   *   쓴다 — 화면 경로와 API 경로가 갈리면 대장을 읽는 사람이 둘을 못 잇는다.
   * ⚠ 인수 화면 `/report-template`(서식 표 · dj-core)과 **다른 화면**이다. 그 화면은
   *   택배 운송장 19행이 사는 표이고(P-125 실측), 이 화면은 우리 서식 셋이다.
   *   경로가 달라 서로 삼키지 않는다(변수 조각 없음 · 형제).
   */
  reports: { title: '보고서', path: '/dsm/reports' },
} as const;

/**
 * **redirect 대장** — 옛 경로는 지우지 않는다(대장은 줄지 않는다).
 * App.tsx 배선(조율자): `{ path: from, element: <Navigate to={to} replace /> }` 한 줄씩.
 *
 * ⚠ `/dsm/cameras/tuning` 은 redirect 가 **아니다** — 그 경로는 튜닝 절로 살아 있다.
 *   여기 적는 것은 「오탐률 화면의 옛 주소」로 남아 있던 이름 하나다: 온보딩 대장·
 *   문서가 오탐률을 `/dsm/cameras/false-positive` 로 부른 자리를 정본으로 보낸다.
 */
export const dsmU24Redirects = [
  { from: '/dsm/cameras/false-positive', to: '/dsm/stats/false-positive' },
] as const;
