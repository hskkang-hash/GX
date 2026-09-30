/**
 * DSM-U4-07 영상 열람·제공(반출) 대장 · 연간 통계 + DSM-U4-08 평가·감사 자료 묶음
 * (턴 AQ · 차선 N3).
 *
 * ★ 대장 표: 요청 접수(공문번호·목적·범위) → 승인 → 마스킹본 제공 기록. 누를 때마다
 *   **대장 GET 과 연간 통계 GET 을 다시 불러** 그린다(쓰기 응답으로 그리지 않는다).
 *   원본은 이 화면으로 나가지 않는다 — 제공 문은 원본 경로 인자가 없다(서버 구조).
 * ★ 연간 통계: 연도 칸을 바꾸면 `annual-stats?year=` 를 다시 부른다.
 * ★ 평가 묶음: 기간(시작·끝)을 고르고 누르면 ZIP 을 내려받는다(인증 헤더가 실리는
 *   경로 `downloadDsmFile` — `<a href>` 로 붙이면 토큰이 안 실린다).
 */
import { Alert, Button, Card, Col, Input, InputNumber, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { downloadDsmFile, dsmPostOnce, newIdempotencyKey } from '../api';
import { aqDsmEndpoint, aqFreshGet } from './aqScreensApi';

const { Text } = Typography;

interface LedgerRow {
  request_id: number;
  text: string;
  status: string;
}
interface AnnualStats {
  year: number;
  requested: number;
  approved: number;
  provided: number;
  by_month: Record<string, number>;
}

const STATUS_COLOR: Record<string, string> = { 요청: 'orange', 승인: 'blue', 제공: 'green' };

export default function VideoAccessLedgerPanel() {
  const [year, setYear] = useState<number>(new Date().getFullYear());
  const [stats, setStats] = useState<AnnualStats | null>(null);
  const [ledger, setLedger] = useState<LedgerRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [org, setOrg] = useState('');
  const [docNo, setDocNo] = useState('');
  const [purpose, setPurpose] = useState('');
  const [scopeDesc, setScopeDesc] = useState('');
  const [since, setSince] = useState('');
  const [until, setUntil] = useState('');

  const loadStats = useCallback(async (y: number) => {
    try {
      setStats(await aqFreshGet<AnnualStats>(aqDsmEndpoint.videoAccessAnnualStats, { year: y }));
    } catch (e) {
      setStats(null);
      setError(`연간 통계를 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  const loadLedger = useCallback(async () => {
    try {
      setLedger(await aqFreshGet<LedgerRow[]>(aqDsmEndpoint.videoAccess));
    } catch (e) {
      setError(`대장을 불러오지 못했습니다 — ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => {
    void loadStats(year);
  }, [year, loadStats]);

  useEffect(() => {
    void loadLedger();
  }, [loadLedger]);

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
      await Promise.all([loadLedger(), loadStats(year)]);
      setBusy(false);
    }
  }

  async function downloadBundle(): Promise<void> {
    setBusy(true);
    try {
      const params: Record<string, string> = {};
      if (since) params.since = since;
      if (until) params.until = until;
      await downloadDsmFile(
        aqDsmEndpoint.evaluationBundle,
        `평가자료묶음_${since || '처음'}_${until || '오늘'}.zip`,
        '평가·감사 자료 묶음',
        params,
      );
      setNotice('평가·감사 자료 묶음을 내려받았습니다');
    } catch (e) {
      setError(`묶음을 내려받지 못했습니다 — ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      {error && <Alert type="error" showIcon closable message={error} onClose={() => setError(null)} />}
      {notice && <Alert type="success" showIcon closable message={notice} onClose={() => setNotice(null)} />}

      <Card size="small" title="영상 제공 연간 통계" data-gx="dsm-u4-07-stats-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space>
            <Text>연도</Text>
            <InputNumber
              min={2000}
              max={2100}
              value={year}
              onChange={(v) => typeof v === 'number' && setYear(v)}
              data-gx="dsm-u4-07-year"
            />
          </Space>
          <Row gutter={16} data-gx="dsm-u4-07-stats">
            <Col xs={8}>
              <Statistic title="요청" value={stats?.requested ?? '-'} />
            </Col>
            <Col xs={8}>
              <Statistic title="승인" value={stats?.approved ?? '-'} />
            </Col>
            <Col xs={8}>
              <Statistic title="제공(마스킹본)" value={stats?.provided ?? '-'} />
            </Col>
          </Row>
          {stats && (
            <Text type="secondary" data-gx="dsm-u4-07-by-month">
              월별 요청:{' '}
              {Object.entries(stats.by_month)
                .map(([m, n]) => `${Number(m)}월 ${n}`)
                .join(' · ')}
            </Text>
          )}
        </Space>
      </Card>

      <Card size="small" title="개인영상정보 제공 대장" data-gx="dsm-u4-07-ledger-card">
        <Space direction="vertical" style={{ width: '100%' }}>
          <Space wrap>
            <Input placeholder="요청 기관" value={org} onChange={(e) => setOrg(e.target.value)}
              style={{ width: 150 }} data-gx="dsm-u4-07-org" />
            <Input placeholder="공문 번호" value={docNo} onChange={(e) => setDocNo(e.target.value)}
              style={{ width: 140 }} data-gx="dsm-u4-07-doc-no" />
            <Input placeholder="목적" value={purpose} onChange={(e) => setPurpose(e.target.value)}
              style={{ width: 160 }} data-gx="dsm-u4-07-purpose" />
            <Input placeholder="범위(카메라·시간)" value={scopeDesc} onChange={(e) => setScopeDesc(e.target.value)}
              style={{ width: 180 }} data-gx="dsm-u4-07-scope" />
            <Button
              type="primary"
              disabled={busy || !org.trim() || !docNo.trim() || !purpose.trim()}
              data-gx="dsm-u4-07-create"
              onClick={() =>
                act(
                  aqDsmEndpoint.videoAccess,
                  { requester_org: org, doc_no: docNo, purpose, scope_desc: scopeDesc },
                  '요청을 대장에 올렸습니다',
                )
              }
            >
              요청 접수
            </Button>
          </Space>
          <Table<LedgerRow>
            size="small"
            rowKey="request_id"
            dataSource={ledger}
            pagination={false}
            data-gx="dsm-u4-07-ledger"
            locale={{ emptyText: '대장에 기록이 없습니다. 위에서 열람 요청을 등록하십시오' }}
            columns={[
              {
                title: '상태',
                dataIndex: 'status',
                width: 80,
                render: (v: string) => <Tag color={STATUS_COLOR[v] ?? 'default'}>{v}</Tag>,
              },
              { title: '내용', dataIndex: 'text' },
              {
                title: '누르기',
                width: 200,
                render: (_: unknown, r) => (
                  <Space>
                    <Button size="small" disabled={busy || r.status !== '요청'} data-gx="dsm-u4-07-approve"
                      onClick={() => act(aqDsmEndpoint.videoAccessApprove(r.request_id), {}, '승인했습니다')}>
                      승인
                    </Button>
                    <Button size="small" type="primary" disabled={busy || r.status !== '승인'}
                      data-gx="dsm-u4-07-provide"
                      onClick={() =>
                        act(aqDsmEndpoint.videoAccessProvide(r.request_id), { method: '마스킹본' },
                          '마스킹본 제공을 기록했습니다')
                      }>
                      마스킹본 제공
                    </Button>
                  </Space>
                ),
              },
            ]}
          />
        </Space>
      </Card>

      <Card size="small" title="재난관리평가·감사 자료 묶음" data-gx="dsm-u4-08-card">
        <Space wrap>
          <Text>기간</Text>
          <Input type="date" value={since} onChange={(e) => setSince(e.target.value)}
            style={{ width: 160 }} data-gx="dsm-u4-08-since" />
          <Text>~</Text>
          <Input type="date" value={until} onChange={(e) => setUntil(e.target.value)}
            style={{ width: 160 }} data-gx="dsm-u4-08-until" />
          <Button type="primary" disabled={busy} onClick={downloadBundle} data-gx="dsm-u4-08-download">
            묶음 내려받기(ZIP)
          </Button>
        </Space>
      </Card>
    </Space>
  );
}
