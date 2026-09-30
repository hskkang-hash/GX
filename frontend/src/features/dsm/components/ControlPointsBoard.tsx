/**
 * DSM-U3-02 · U4-04 — **통제·대피 현황판(통제 지점 표)** (턴 AQ · 차선 N3).
 *
 * 지점 등록(= 기준 도달 시각) → 「통제 결정」 → 「통제 완료」(U3-02 실행 회신 ·
 * `POST /api/dsm/controls/{id}/executed`) → 「해제」. 누를 때마다 쓰기 한 번 뒤
 * **현황판 GET(`/api/dsm/control-points`)을 다시 불러** 새 단계를 그린다 — 쓰기
 * 응답으로 표를 고치지 않는다. 순서 검사(도달→결정→실행→해제)는 서버 한 곳이 한다.
 */
import { Alert, Button, Card, Input, InputNumber, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { dsmPostOnce, newIdempotencyKey } from '../api';
import { aqDsmEndpoint, aqFreshGet } from './aqScreensApi';

const { Text } = Typography;

interface ControlPointRow {
  point_id: number;
  text: string;
  stage: string;
  evacuee_count: number | null;
  evacuation_site: string | null;
}

/** 단계 글자 — 서버 `u4_regulations.CONTROL_STAGE_ORDER` 와 같은 글자. */
const STAGE_COLOR: Record<string, string> = {
  도달: 'orange',
  결정: 'gold',
  실행: 'red',
  해제: 'green',
};
const STAGE_LABEL: Record<string, string> = {
  도달: '기준 도달',
  결정: '통제 결정',
  실행: '통제 중',
  해제: '해제',
};

export default function ControlPointsBoard() {
  const [rows, setRows] = useState<ControlPointRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [evacuees, setEvacuees] = useState<number | null>(null);
  const [site, setSite] = useState('');

  const reload = useCallback(async () => {
    try {
      setRows(await aqFreshGet<ControlPointRow[]>(aqDsmEndpoint.controlPoints));
    } catch (e) {
      setError(`통제 현황을 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  /** 쓰기 한 번 → 성공이든 실패든 현황판을 다시 불러 서버 값만 그린다. */
  async function act(url: string, body: unknown, done: string): Promise<void> {
    setBusy(true);
    setNotice(null);
    try {
      await dsmPostOnce(url, body, newIdempotencyKey());
      setError(null);
      setNotice(done);
    } catch (e) {
      setError(`처리하지 못했습니다 — ${(e as Error).message}`);
    } finally {
      await reload();
      setBusy(false);
    }
  }

  return (
    <Card size="small" title="통제·대피 현황판" data-gx="dsm-u3-02-card">
      <Space direction="vertical" style={{ width: '100%' }}>
        {error && <Alert type="error" showIcon closable message={error} onClose={() => setError(null)} />}
        {notice && <Alert type="success" showIcon closable message={notice} onClose={() => setNotice(null)} />}
        <Space wrap>
          <Input
            placeholder="통제 지점(예: ○○ 지하차도)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={{ width: 220 }}
            data-gx="dsm-u3-02-name"
          />
          <InputNumber
            placeholder="대피 인원"
            min={0}
            value={evacuees}
            onChange={(v) => setEvacuees(typeof v === 'number' ? v : null)}
            data-gx="dsm-u3-02-evacuees"
          />
          <Input
            placeholder="대피 장소"
            value={site}
            onChange={(e) => setSite(e.target.value)}
            style={{ width: 160 }}
            data-gx="dsm-u3-02-site"
          />
          <Button
            type="primary"
            disabled={busy || !name.trim()}
            data-gx="dsm-u3-02-create"
            onClick={() =>
              act(
                aqDsmEndpoint.controlPoints,
                { name, evacuee_count: evacuees ?? undefined, evacuation_site: site },
                '기준 도달을 기록했습니다',
              )
            }
          >
            기준 도달 기록
          </Button>
        </Space>
        <Table<ControlPointRow>
          size="small"
          rowKey="point_id"
          dataSource={rows}
          pagination={false}
          data-gx="dsm-u3-02-board"
          locale={{ emptyText: '등록된 통제 지점이 없습니다' }}
          columns={[
            {
              title: '지금 단계',
              dataIndex: 'stage',
              width: 110,
              render: (v: string) => (
                <Tag color={STAGE_COLOR[v] ?? 'default'} data-gx="dsm-u3-02-stage">
                  {STAGE_LABEL[v] ?? v}
                </Tag>
              ),
            },
            { title: '지점 · 도달 시각', dataIndex: 'text' },
            {
              title: '대피',
              render: (_: unknown, r) =>
                r.evacuee_count === null ? (
                  <Text type="secondary">미기재</Text>
                ) : (
                  `${r.evacuee_count}명${r.evacuation_site ? ` · ${r.evacuation_site}` : ''}`
                ),
            },
            {
              title: '누르기',
              width: 280,
              render: (_: unknown, r) => (
                <Space wrap>
                  <Button
                    size="small"
                    disabled={busy || r.stage !== '도달'}
                    data-gx="dsm-u3-02-decide"
                    onClick={() =>
                      act(aqDsmEndpoint.controlAdvance(r.point_id), { stage: '결정' }, '통제 결정을 기록했습니다')
                    }
                  >
                    통제 결정
                  </Button>
                  <Button
                    size="small"
                    type="primary"
                    danger
                    disabled={busy || r.stage !== '결정'}
                    data-gx="dsm-u3-02-executed"
                    onClick={() =>
                      act(aqDsmEndpoint.controlExecuted(r.point_id), {}, '통제 완료 시각을 기록했습니다')
                    }
                  >
                    통제 완료
                  </Button>
                  <Button
                    size="small"
                    disabled={busy || r.stage !== '실행'}
                    data-gx="dsm-u3-02-release"
                    onClick={() =>
                      act(aqDsmEndpoint.controlAdvance(r.point_id), { stage: '해제' }, '해제를 기록했습니다')
                    }
                  >
                    해제
                  </Button>
                </Space>
              ),
            },
          ]}
        />
      </Space>
    </Card>
  );
}
