/**
 * 플랫폼 운영(U0) — `/ops`. 턴 AO · WO-18 · 차선 N3 단독 소유.
 *
 * 테넌트 목록·건강 보드·인시던트·온보딩 요약을 **읽어서 그린다**(P-415 — 새 저장
 * 0, 이미 있는 장부를 읽는다). U0 아닌 계정이 오면 서버가 403 을 주고, 이 화면은
 * 그 사실을 그대로 보여 준다(대리 판정을 화면에서 다시 하지 않는다).
 */
import { Alert, Card, Col, Row, Spin, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';

import {
  fetchHealthBoard,
  fetchIncidents,
  fetchOnboardingBoard,
  fetchTenants,
  type OpsHealthRow,
  type OpsIncidentRow,
  type OpsTenantRow,
} from '../api';
import {
  OPS_ERROR_PREFIX,
  OPS_FORBIDDEN,
  OPS_HEALTH_COLOR_LABEL,
  OPS_INCIDENT_STATUS_LABEL,
  OPS_SECTION_LABEL,
  OPS_SEVERITY_LABEL,
  OPS_TITLE,
} from '../copy';

const { Title } = Typography;

interface Loaded {
  tenants: OpsTenantRow[];
  health: OpsHealthRow[];
  incidents: OpsIncidentRow[];
  onboarding: Record<string, unknown> | null;
}

export default function OpsHome() {
  const [data, setData] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [tenants, health, incidents, onboarding] = await Promise.all([
          fetchTenants(),
          fetchHealthBoard(),
          fetchIncidents('open'),
          fetchOnboardingBoard().catch(() => null),
        ]);
        if (!alive) return;
        setData({
          tenants: tenants.tenants,
          health: health.tenants,
          incidents: incidents.incidents,
          onboarding,
        });
      } catch (e) {
        if (!alive) return;
        const status = (e as { response?: { status?: number } })?.response?.status;
        if (status === 401 || status === 403) {
          setForbidden(true);
        } else {
          setError(e instanceof Error ? e.message : String(e));
        }
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (forbidden) {
    return (
      <div style={{ padding: 24 }}>
        <Title level={3}>{OPS_TITLE}</Title>
        <Alert type="warning" showIcon message={OPS_FORBIDDEN} />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={3}>{OPS_TITLE}</Title>

      {loading && <Spin />}
      {error && <Alert type="error" showIcon message={`${OPS_ERROR_PREFIX}${error}`} />}

      {data && (
        <Row gutter={[16, 16]}>
          <Col span={24}>
            <Card title={`${OPS_SECTION_LABEL.tenants} (${data.tenants.length})`}>
              <Table
                rowKey="tenant_code"
                size="small"
                pagination={false}
                dataSource={data.tenants}
                columns={[
                  { title: '테넌트', dataIndex: 'name' },
                  { title: '코드', dataIndex: 'tenant_code' },
                  { title: '구성원', dataIndex: 'member_count' },
                ]}
              />
            </Card>
          </Col>

          <Col span={12}>
            <Card title={OPS_SECTION_LABEL.health}>
              <Table
                rowKey="tenant_code"
                size="small"
                pagination={false}
                dataSource={data.health}
                columns={[
                  { title: '테넌트', dataIndex: 'name' },
                  {
                    title: '카메라',
                    render: (_: unknown, row: OpsHealthRow) =>
                      `${row.cameras.active}/${row.cameras.total}`,
                  },
                  {
                    title: '상태',
                    dataIndex: 'color',
                    render: (color: string) => (
                      <Tag color={color === 'red' ? 'red' : 'green'}>
                        {OPS_HEALTH_COLOR_LABEL[color] ?? color}
                      </Tag>
                    ),
                  },
                ]}
              />
            </Card>
          </Col>

          <Col span={12}>
            <Card title={`${OPS_SECTION_LABEL.incidents} (${data.incidents.length})`}>
              <Table
                rowKey="incident_id"
                size="small"
                pagination={false}
                dataSource={data.incidents}
                columns={[
                  { title: '테넌트', dataIndex: 'tenant_code' },
                  {
                    title: '심각도',
                    dataIndex: 'severity',
                    render: (s: string) => OPS_SEVERITY_LABEL[s] ?? s,
                  },
                  {
                    title: '상태',
                    dataIndex: 'status',
                    render: (s: string) => OPS_INCIDENT_STATUS_LABEL[s] ?? s,
                  },
                  { title: '요약', dataIndex: 'summary' },
                ]}
              />
            </Card>
          </Col>

          {data.onboarding && (
            <Col span={24}>
              <Card title={OPS_SECTION_LABEL.onboarding}>
                {String(data.onboarding.score_over_denominator ?? '')}
              </Card>
            </Col>
          )}
        </Row>
      )}
    </div>
  );
}
