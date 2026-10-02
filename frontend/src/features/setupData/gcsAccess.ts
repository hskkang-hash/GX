/**
 * GCS(드론 비행 제어) 화면이 들고 가는 자격 — WO-GRDX-20261002-10 AC-2·AC-3 (S1 GRDX-FIRST-010).
 *
 * 무엇이 문제였나 [실측 2026-10-02 · `-06` AC-5]
 *   두 화면이 `import.meta.env.VITE_CGS_APIKEY` 를 읽었다. `VITE_` 이름은 빌드 때 번들에 **원문으로**
 *   박힌다 — GCS bearer 키가 배포 번들에 4벌, 로그인 없이 `/login` 만 열어도 받았다.
 *
 * 이제는: 화면은 **우리 로그인 토큰**을 GCS 라이브러리에 넘기고, 라이브러리는 빌드 설정
 * `VITE_GCS_API_URL=/api/gcs`(같은 출처 경유)로 부른다. 경유(`backend/apps/gcs/api.py`)가 사람·역할을
 * 확인한 뒤 서버 환경의 `GCS_APIKEY` 로 GCS 를 부른다. 그래서 이 파일에는 GCS 키가 없다.
 *
 * ⚠ 주소 쿼리 `accessKey` 로 키를 넘기던 길은 닫았다 — 주소에 실린 자격은 기록·공유로 샌다.
 * ⚠ 토큰 자리: 인수 부품(rj-core)이 쿠키 `token` 에 둔다 [실측 · 배포 번들 `getToken(){return hu.get("token")}`].
 */
export function gcsAccessKey(): string | undefined {
  const hit = document.cookie
    .split('; ')
    .find((row) => row.startsWith('token='));
  const value = hit ? decodeURIComponent(hit.slice('token='.length)) : '';
  return value || undefined;
}
