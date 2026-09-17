/**
 * 화면 — **감사 기록** 첫 판 (차선 U24 · 턴 T · P-164 U24 ③).
 *
 * 무엇을 보이나
 * -------------
 *   `audit.py` 가 남긴 것 — 설정 변경(F-12 · `guardianx.f12.settings`)과 사건 행위
 *   (상급 보고 체크·해제 · `guardianx.u24.events`). **성공도 실패도** 한 표에 있다.
 *   서버가 요청자의 테넌트로 좁혀 준다 — 화면이 다시 거르지 않는다.
 *
 * 필터 셋 + 쪽 — 전부 **서버가 거른다**(`GET /api/dsm/audit`). 화면이 받은 쪽을 자기가
 *   거르면 「쪽 밖의 행」은 없는 것이 된다.
 *     ① 기간(`since`·`until`) ② 행위자(`actor_id`) ③ 행위 종류(`action` 앞머리)
 *
 * 「60초 안 도달」 — **계측이지 토스트가 아니다.**
 *   첫 응답이 올 때까지 걸린 초를 상태 칸에 적는다. 60초를 넘으면 그 칸이 빨강이다
 *   (`LOAD_TIMEOUT_MS` 10초에 걸리면 오류 상자가 먼저 뜬다 — 그때도 초를 적는다).
 *   V 가 보는 것은 이 칸 하나다: 「첫 응답 N.N초 · 60초 안」.
 *
 * ★ 누가 보나 — 관제팀장(U2) · 지자체 담당관(U4) · 운영자(U5). 관제요원은 403 을 받고
 *   그 사실이 상태 상자에 적힌다(`StateBoundary` 의 forbidden).
 * ★ 사람 이름은 서버가 준 `actor`(username)만 적는다 — 지어내지 않는다.
 */
import {
  Button,
  Card,
  DatePicker,
  Input,
  InputNumber,
  Segmented,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import dayjs, { type Dayjs } from 'dayjs';
import { useMemo, useRef, useState } from 'react';

import { dsmGet, dsmU24StatsEndpoint } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { absolute, stamp } from '../time';
import type { AuditItem, AuditPage } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/** 정본 문턱 — 「60초 안 도달」. 화면이 이 수를 재지 않는다 — 지시서(P-164)가 정한 수다. */
const REACH_LIMIT_SECONDS = 60;

/** 행위 종류 단추 — 서버 `api_name` 의 앞머리. 「전부」는 필터를 안 보낸다. */
const ACTION_KINDS: { key: string; label: string; prefix: string | null }[] = [
  { key: 'all', label: '전부', prefix: null },
  { key: 'upper', label: '상급 보고', prefix: 'upper_report' },
  { key: 'write', label: '설정 변경', prefix: 'write:' },
];

const PAGE_SIZE = 50;

export default function AuditLog() {
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [actorId, setActorId] = useState<number | null>(null);
  const [actionKey, setActionKey] = useState<string>('all');
  const [actionText, setActionText] = useState<string>('');
  const [page, setPage] = useState(1);

  /** 계측 — 요청을 보낸 순간과 첫 응답(성공이든 실패든)까지의 초. */
  const startedAt = useRef<number | null>(null);
  const [reachSeconds, setReachSeconds] = useState<number | null>(null);
  const [reachOutcome, setReachOutcome] = useState<'ok' | 'fail' | null>(null);

  const query = useMemo(() => {
    const q: Record<string, unknown> = { page, page_size: PAGE_SIZE };
    if (range) {
      q.since = range[0].toISOString();
      q.until = range[1].toISOString();
    }
    if (actorId !== null) q.actor_id = actorId;
    const prefix = ACTION_KINDS.find((k) => k.key === actionKey)?.prefix ?? null;
    const typed = actionText.trim();
    if (typed) q.action = typed;
    else if (prefix) q.action = prefix;
    return q;
  }, [range, actorId, actionKey, actionText, page]);

  const audit = useDsmResource<AuditPage>(
    async () => {
      startedAt.current = performance.now();
      try {
        const out = await dsmGet<AuditPage>(dsmU24StatsEndpoint.audit, query);
        setReachSeconds((performance.now() - startedAt.current) / 1000);
        setReachOutcome('ok');
        return out;
      } catch (err) {
        setReachSeconds((performance.now() - (startedAt.current ?? performance.now())) / 1000);
        setReachOutcome('fail');
        throw err;
      }
    },
    [query],
    { isEmpty: (v) => (v?.items?.length ?? 0) === 0 },
  );

  const rows = audit.data?.items ?? [];
  const reached = reachSeconds !== null && reachOutcome === 'ok' && reachSeconds <= REACH_LIMIT_SECONDS;

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        감사 기록
      </Title>

      <Card size="small">
        <Space wrap align="center">
          <Text type="secondary">기간</Text>
          <RangePicker
            showTime
            value={range}
            onChange={(v) => {
              setPage(1);
              setRange(v && v[0] && v[1] ? [v[0], v[1]] : null);
            }}
            presets={[
              { label: '오늘', value: [dayjs().startOf('day'), dayjs()] },
              { label: '7일', value: [dayjs().subtract(7, 'day'), dayjs()] },
              { label: '30일', value: [dayjs().subtract(30, 'day'), dayjs()] },
            ]}
          />
          <Text type="secondary">행위자 번호</Text>
          <InputNumber
            min={1}
            placeholder="사번(pk)"
            value={actorId}
            onChange={(v) => {
              setPage(1);
              setActorId(typeof v === 'number' ? v : null);
            }}
          />
          <Text type="secondary">행위 종류</Text>
          <Segmented
            value={actionKey}
            onChange={(v) => {
              setPage(1);
              setActionKey(String(v));
            }}
            options={ACTION_KINDS.map((k) => ({ value: k.key, label: k.label }))}
          />
          <Input
            style={{ width: 200 }}
            placeholder="행위 앞머리 직접 입력"
            value={actionText}
            onChange={(e) => {
              setPage(1);
              setActionText(e.target.value);
            }}
            allowClear
          />
          <Button onClick={audit.reload}>새로고침</Button>
        </Space>
      </Card>

      {/* ── 「60초 안 도달」 상태 칸 — 계측. 토스트가 아니다. ─────────────────── */}
      <Card size="small">
        <Space wrap>
          <Text type="secondary">첫 응답</Text>
          {reachSeconds === null ? (
            <Tag>아직 재는 중</Tag>
          ) : reached ? (
            <Tag color="green">{reachSeconds.toFixed(1)}초 · {REACH_LIMIT_SECONDS}초 안</Tag>
          ) : (
            <Tag color="red">
              {reachSeconds.toFixed(1)}초 ·{' '}
              {reachOutcome === 'fail' ? '응답이 실패' : `${REACH_LIMIT_SECONDS}초를 넘음`}
            </Tag>
          )}
          {audit.data && (
            <Text type="secondary">
              전체 {audit.data.total}건 · {audit.data.page}/{audit.data.pages || 1}쪽
            </Text>
          )}
        </Space>
      </Card>

      <Card size="small">
        <StateBoundary
          state={audit.state}
          reason={audit.reason}
          status={audit.status}
          onRetry={audit.reload}
          where="AuditLog/표"
          emptyText="조건에 맞는 감사 기록이 없습니다. (요청은 성공했고 0건입니다)"
        >
          <Table<AuditItem>
            size="small"
            rowKey="audit_id"
            dataSource={rows}
            pagination={{
              current: audit.data?.page ?? page,
              pageSize: PAGE_SIZE,
              total: audit.data?.total ?? 0,
              showSizeChanger: false,
              onChange: (p) => setPage(p),
            }}
            columns={[
              {
                title: '시각',
                dataIndex: 'at',
                width: 170,
                render: (v: string | null) =>
                  v ? <span title={absolute(v)}>{stamp(v)}</span> : '—',
              },
              {
                title: '결과',
                dataIndex: 'outcome',
                width: 90,
                render: (v: string) =>
                  v === 'allowed' ? <Tag color="green">성공</Tag> : <Tag color="orange">막힘</Tag>,
              },
              { title: '행위', dataIndex: 'action', ellipsis: true },
              {
                title: '행위자',
                dataIndex: 'actor',
                width: 160,
                render: (v: string, r) => (v ? `${v} (${r.actor_id ?? '—'})` : `번호 ${r.actor_id ?? '—'}`),
              },
              { title: '사유', dataIndex: 'reason', ellipsis: true },
              {
                title: '채널',
                dataIndex: 'channel',
                width: 190,
                render: (v: string) =>
                  v.endsWith('.events') ? '사건 행위' : v.endsWith('.settings') ? '설정 변경' : v,
              },
              { title: 'HTTP', dataIndex: 'status_http', width: 70 },
            ]}
          />
        </StateBoundary>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        이 표는 서버가 우리 조직의 행위자로 좁혀 준 것입니다. 성공과 막힌 시도가 함께
        있습니다 — 막힌 시도가 안 보이면 「시도가 없었다」와 「막혔다」를 가를 수 없습니다.
      </Text>
    </Space>
  );
}
