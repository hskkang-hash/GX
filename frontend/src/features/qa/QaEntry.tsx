/**
 * QA 진입 화면 자리 — WO-GRDX-20261002-09 · 규격 09 M1(이중 잠금)의 앞단 자리.
 *
 * 이 파일은 `VITE_QA_BUILD=true` 로 지은 번들에만 실린다(`App.tsx` 의 상수 분기 + 동적 import —
 * 스위치가 없으면 Vite 가 분기를 지우고 이 모듈은 산출물에 없다 · 검증: 운영 번들 `qa/as` 0건).
 * 사용자키로 들어가는 일(M2)과 QA 바(M4)는 AC-2·4 몫 — 지금은 자리만 있다. 인증을 건너뛰는 코드 0.
 */
export default function QaEntry() {
  return (
    <main style={{ padding: 32 }}>
      <h1 style={{ fontSize: 18 }}>QA 진입 — 준비 중</h1>
      <p style={{ fontSize: 14 }}>/qa/as/&lt;사용자키&gt; 는 다음 단계(AC-2)에서 열린다.</p>
    </main>
  );
}
