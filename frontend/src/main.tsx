// ★ [P-118 · 턴 O · 2026-09-10] **이 한 줄이 확인창 층 전체를 살린다.**
//
//   react 19 는 `ReactDOM.render` 를 지웠고, antd v5 의 **정적 메서드**
//   (`Modal.confirm` · `message.*`)는 그것으로 포털을 만든다. 그래서 이 줄이 없으면
//   확인창도 토스트도 **한 번도 뜨지 않는다** — 오류도 없이 조용히.
//
//   09-08 사용자 점검이 잰 것: 「실제로 판정」 3번 클릭 → API 호출 **0건** ·
//   문서 전체 `.ant-modal` 0 · `[role=dialog]` 0 · `document.body.children` 1
//   (포털 컨테이너가 생기지도 않았다) · React 오류 0. 그 옆에서 확인창을 안 지나는
//   「접수하기」는 200 이었다 — **클릭은 닿았고 확인창 길만 죽어 있었다.**
//
//   죽어 있던 것: 진위 판정(실제·오탐) · 되돌리기(데스크·모바일) · 성공 안내 11곳.
//   ⚠ 부수 효과가 아니라 **전제**다 — 지우면 위 셋이 같이 죽는다. 지우기 전에
//     `scripts/verify_click_completes.py` 가 빨강을 낸다.
import '@ant-design/v5-patch-for-react-19';

import { createRoot } from 'react-dom/client';

// import { scan } from 'react-scan';

import '../node_modules/rj-core/dist/style.css';
import App from './App.tsx';
import './Global.scss';
import './i18n';
import './index.css';

// scan({
//   enabled: true,
// });

createRoot(document.getElementById('root')!).render(
  // <StrictMode>
  <App />,
  // </StrictMode>
);
