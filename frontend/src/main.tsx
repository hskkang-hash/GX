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
