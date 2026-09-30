/**
 * 플랫폼 운영(U0) — `/ops`. 턴 AO · WO-18 · 차선 N3 → 턴 AQ · 차선 N2 보드 배선.
 *
 * 보드 열 개를 탭으로 둔다(테넌트 발급 · 앱 설치·버전 · 건강 · 인시던트 · 백업·복구 ·
 * 온보딩 관제 · 플랫폼 감사 · 키·자격 회전 · 릴리스·배포 · 시드·훈련). 각 보드는
 * `components/*Board.tsx` 에 있고, 이미 있는 장부를 **읽어 그리고** 제목이 부르는 누르는
 * 자리를 서버 문에 잇는다 — 누른 뒤에는 같은 보드의 GET 을 다시 불러 새 값을 그린다.
 *
 * U0 아닌 계정이 오면 서버가 403 을 준다 — 이 화면은 먼저 테넌트 목록 한 번으로 그것을
 * 확인하고, 거절이면 보드를 하나도 그리지 않는다(대리 판정을 화면에서 다시 하지 않는다).
 */
import { Alert, Spin, Tabs, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { fetchTenants, opsErrorStatus, opsErrorText } from '../api';
import AppsBoard from '../components/AppsBoard';
import AuditBoard from '../components/AuditBoard';
import BackupBoard from '../components/BackupBoard';
import HealthBoard from '../components/HealthBoard';
import IncidentsBoard from '../components/IncidentsBoard';
import KeysBoard from '../components/KeysBoard';
import OnboardingBoard from '../components/OnboardingBoard';
import ReleasesBoard from '../components/ReleasesBoard';
import SeedBoard from '../components/SeedBoard';
import TenantsBoard from '../components/TenantsBoard';
import { OPS_ERROR_PREFIX, OPS_FORBIDDEN, OPS_TAB_LABEL, OPS_TITLE } from '../copy';

const { Title } = Typography;

type Gate = 'checking' | 'open' | 'forbidden' | 'error';

export default function OpsHome() {
  const [gate, setGate] = useState<Gate>('checking');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchTenants()
      .then(() => {
        if (alive) setGate('open');
      })
      .catch((e) => {
        if (!alive) return;
        const status = opsErrorStatus(e);
        if (status === 401 || status === 403) {
          setGate('forbidden');
        } else {
          setError(opsErrorText(e));
          setGate('error');
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div style={{ padding: 24 }} data-gx="ops-home">
      <Title level={3}>{OPS_TITLE}</Title>
      {gate === 'checking' && <Spin />}
      {gate === 'forbidden' && <Alert type="warning" showIcon message={OPS_FORBIDDEN} />}
      {gate === 'error' && <Alert type="error" showIcon message={`${OPS_ERROR_PREFIX}${error}`} />}
      {gate === 'open' && (
        <Tabs
          data-gx="ops-tabs"
          items={[
            { key: 'o-01', label: OPS_TAB_LABEL.tenants, children: <TenantsBoard /> },
            { key: 'o-02', label: OPS_TAB_LABEL.apps, children: <AppsBoard /> },
            { key: 'o-05', label: OPS_TAB_LABEL.health, children: <HealthBoard /> },
            { key: 'o-06', label: OPS_TAB_LABEL.incidents, children: <IncidentsBoard /> },
            { key: 'o-07', label: OPS_TAB_LABEL.backups, children: <BackupBoard /> },
            { key: 'o-08', label: OPS_TAB_LABEL.onboarding, children: <OnboardingBoard /> },
            { key: 'o-09', label: OPS_TAB_LABEL.audit, children: <AuditBoard /> },
            { key: 'o-10', label: OPS_TAB_LABEL.keys, children: <KeysBoard /> },
            { key: 'o-11', label: OPS_TAB_LABEL.releases, children: <ReleasesBoard /> },
            { key: 'o-12', label: OPS_TAB_LABEL.seed, children: <SeedBoard /> },
          ]}
        />
      )}
    </div>
  );
}
