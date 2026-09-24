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
import { useEffect, useMemo, useRef, useState } from 'react';

import { ownDenialPaths } from '@/features/session/permissionDenied';

import {
  downloadAuditCsv,
  dsmGet,
  dsmU24StatsEndpoint,
  type AuditChainColumns,
  type AuditChainCounts,
} from '../api';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { CHANNEL_NAME_UNKNOWN, channelLabel, hasChannelLabel, userFacingError } from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
import { absolute, stamp } from '../time';
import type { AuditItem, AuditPage } from '../types';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

/**
 * 턴 U — 서버가 세 칸을 더 낸다(`api_u24._with_chain_columns`): `prev_hash` · `hash` ·
 * `chain`. **`types.ts` 를 넓히지 않는다** — 그 파일은 이번 턴 U24 소유가 아니다
 * (한 파일은 한 차선). 여기서 교차로 넓혀 쓴다.
 */
type AuditRow = AuditItem & AuditChainColumns & { target?: AuditTarget | null };
type AuditPageWithChain = AuditPage & {
  chain_states?: AuditChainCounts;
  chain_scan_capped?: boolean;
  /** 턴 Y — 대상 갈래의 **분모**. 0 건인 갈래도 그대로 적는다(D-301). */
  target_states?: Record<string, number>;
  /** 턴 AA — 이 쪽에서 대상을 **다 못 물어봤는가**(상한에 닿음). 잘린 표본은 잘렸다고 말한다. */
  target_scan_capped?: boolean;
};

/** 해시를 화면에 적는 길이 — **앞 12자**. 자르는 것은 화면의 몫이고 서버는 전체를 낸다. */
const HASH_HEAD = 12;

/** 체인 상태 넷의 우리말. 「모름」을 지우지 않는다 — 회색은 초록이 아니다. */
const CHAIN_WORD: Record<string, { label: string; color: string }> = {
  linked: { label: '체인 이어짐', color: 'green' },
  broken: { label: '체인 끊김', color: 'red' },
  unchained: { label: '체인 이전 행', color: 'default' },
  unknown: { label: '체인 모름', color: 'orange' },
};

/**
 * ★★ [턴 Y · P-208 U24 ①] **「대상」 칸 — 삭제된 사건을 「없음」이라고 적지 않는다.**
 *
 * 대표 결정으로 09-19~20 에 씨앗 177행이 지워졌고, 그 사건들을 가리키는 감사 행은
 * **그대로 남아 있다**(지우지 않는다 — 감사는 줄지 않는다). 차선 S 가 적었듯 해시
 * 체인은 「이 행이 안 고쳐졌다」만 증명하고 **「가리키는 대상이 아직 있다」는 증명하지
 * 않는다.** 그런데 화면은 그 사실을 한 자도 말하지 않고 `upper_report:set:231073` 만
 * 적어 두었다 — 묻지 않으면 사람은 **아직 있는 것으로 읽는다.** 그것이 거짓말이다.
 *
 * ★ **수는 한 건도 안 바뀐다.** 전체 N건 · 쪽 수 · 이 표의 행 수 전부 그대로다.
 *   바뀌는 것은 **그 0 이 무엇인지 말하는 것**뿐이다.
 *
 * ★ 갈래가 **셋**이다 — 둘로 줄이면 또 거짓말이 된다:
 *     live                 아직 있다
 *     deleted_by_decision  없다 **그리고** 09-20 스냅샷에 그 id 가 있다  ← 여기만 「대표 결정」
 *     gone                 없다 **그리고** 스냅샷에 없다  ← 회색이다. 「대표가 지웠다」가 아니다
 *   「없으면 삭제된 것」으로 적으면 기록 없이 사라진 행까지 대표 결정의 근거로 읽힌다.
 *
 * ★★ [턴 AA · U24] **갈래가 넷이 됐고, 그리는 행이 2 에서 273 이 됐다.**
 *   [실측 2026-09-21 · 재난안전과 계정 · 2,194행] 사건을 가리키는 행 **273** 중 화면이
 *   이름을 붙이던 것은 **2** 뿐이었다 — 나머지 271 은 사건 번호를 「행위」 글자가 아니라
 *   기록 본문에 들고 있었고, 화면은 그 칸을 안 읽었다. 그 칸이 이제 함께 온다.
 *   ★ 넷째 갈래 `denied_attempt` 는 **없어진 사건이 아니다**: 그 행 자신이 그때 막혔고
 *     (결과 「막힘」 · 서버 404) 그 번호로는 사건이 열리지 않았다. 「사라졌다」로 적으면
 *     있지도 않았던 사건이 있었던 것이 된다.
 *   ★ 다섯째 `unknown` 은 갈래가 아니라 **「못 쟀다」**다 — 이 쪽의 대상 확인이 상한에
 *     닿아 안 물어본 행이다. 안 물어본 것을 「사라짐」으로 적지 않는다.
 */
type AuditTarget = {
  kind: string;
  event_id: number;
  state: 'live' | 'deleted_by_decision' | 'denied_attempt' | 'gone' | 'unknown';
  /** 이 행이 사건 번호를 어디서 얻었나 — `action` | `payload`. 화면은 안 그린다. */
  via?: string;
  decision: string | null;
  decided_on: string | null;
  snapshot: string | null;
};

/** 대상 갈래 넷의 우리말. **「모른다」를 지우지 않는다**(체인 칸과 같은 규율). */
const TARGET_WORD: Record<
  AuditTarget['state'],
  { label: string; color: string; note: (t: AuditTarget) => string }
> = {
  live: { label: '사건', color: 'default', note: () => '' },
  deleted_by_decision: {
    label: '삭제된 사건',
    color: 'purple',
    /**
     * ★ [턴 Z · U24] **해를 자르지 않는다.** 종전엔 `slice(5)` 로 「09-20」만 적었다 —
     * 감사 종이는 해를 넘겨 읽히고, 그때 「09-20」은 어느 해인지 말하지 않는다.
     * ⚠ 스냅샷의 **이름**(증거 번호·파일 경로)은 여기 적지 않는다 — 사전 §4 가 금한다.
     *   종이에 필요한 것은 「스냅샷이 있다」는 사실이고, 그 파일이 어디 있는지는
     *   읽는 공무원에게 뜻이 없다(우리 서랍의 지도다).
     */
    note: (t) => `${t.decision ?? '대표 결정'} ${t.decided_on ?? ''} · 스냅샷 있음`,
  },
  /**
   * ★ [턴 AA] **없는 번호를 가리킨 시도.** 그 행이 그때 막혔고(결과 「막힘」 · 404)
   *   가리킨 번호는 그 시각에도 없었다. 이것을 「사라진 사건」으로 적으면 **있지도
   *   않았던 사건이 있었던 것**이 되고, 그 줄은 나중에 「무언가 지워졌다」의 근거로 읽힌다.
   */
  denied_attempt: {
    label: '열리지 않은 사건 번호',
    color: 'default',
    /**
     * ⚠ 「그때도 없는 번호였다」고까지 적지 않는다. 서버가 그때 낸 404 는 「없다」와
     *   「남의 조직 것이다」를 **같은 답으로** 낸다(존재 여부가 새지 않게 하려고
     *   일부러 그렇게 돼 있다). 우리가 아는 사실은 **그 번호로 열리지 않았다**까지다.
     */
    note: () => '막힌 시도 — 그 번호로 열리지 않았습니다',
  },
  gone: { label: '사라진 사건', color: 'orange', note: () => '기록된 결정 없음' },
  /**
   * ★ 갈래가 아니라 **「못 쟀다」**다. 이 쪽에 사건이 너무 많아 상한에 닿은 행 —
   *   안 물어본 것을 「사라짐」으로 적으면 **없어지지 않은 사건이 사라진 것**이 된다.
   */
  unknown: { label: '확인 못 함', color: 'orange', note: () => '이 쪽에서 확인하지 못했습니다' },
};

/**
 * ★★ [턴 Z · U24] **채널의 우리말** — 서버가 여는 채널이 2 에서 15 가 됐다(U56 · 대표 결정 ⑤).
 *
 * 넓힌 뒤 재난안전과 담당관 한 사람의 화면에서만 **368 행**이 기계 이름으로 떨어졌다
 * [실측 2026-09-21 · 테넌트 좁힌 2,076 행 중]. 감사 화면이 우리 폴더 구조를 읽어 주는
 * 자리였고, 사전 §4 가 금한 자리다.
 *
 * ★ [턴 AA · U24] 표를 **`copy.ts` 로 옮겼다**(`CHANNEL_LABEL`). 낱말은 한 글자도 안
 *   바뀌었다 — 옮긴 까닭은 판정기가 표시명 사전을 찾는 자리가 그 파일이기 때문이다.
 *   화면 파일 안에 있으면 **사전이 있는데도 「없다」로 읽힌다.** 두 벌을 만들지 않는다.
 */

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

  /**
   * ★★ [턴 V] **이 문의 403 은 이 화면이 적는다.** 표가 막히면 `StateBoundary` 의
   * forbidden 상자가, 표 내려받기가 막히면 아래 상태 칸이 말한다 — 둘 다 이 화면 안이다.
   * 화면 맨 위 고정 띠가 같은 말을 한 번 더 하면 그 상자들을 덮는다.
   * ⚠ 숨기는 것이 아니다. 거절은 그대로 뜨고, 정하는 것은 **누가 말하는가**뿐이다.
   */
  useEffect(() => ownDenialPaths(['/api/dsm/audit']), []);

  /** CSV — 진행 중 · 실패 사유 · 받은 바이트. **토스트를 쓰지 않는다**(P-173 · 상태 칸). */
  const [csvBusy, setCsvBusy] = useState(false);
  const [csvError, setCsvError] = useState<{ text: string; status: number } | null>(null);
  const [csvDone, setCsvDone] = useState<string>('');

  const audit = useDsmResource<AuditPageWithChain>(
    async () => {
      startedAt.current = performance.now();
      try {
        const out = await dsmGet<AuditPageWithChain>(dsmU24StatsEndpoint.audit, query);
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

  const rows = (audit.data?.items ?? []) as AuditRow[];
  const reached = reachSeconds !== null && reachOutcome === 'ok' && reachSeconds <= REACH_LIMIT_SECONDS;
  const chain = audit.data?.chain_states ?? null;
  /**
   * 턴 Y — 「대상」의 **분모**. 0 건인 갈래를 지우지 않는다: 「이 쪽에는 삭제된 사건을
   * 가리키는 행이 없었다」와 「그런 행을 세지 않았다」는 다른 사실이다 (D-301).
   */
  const targets = audit.data?.target_states ?? null;
  /** 턴 AA — 대상 확인이 이 쪽에서 상한에 닿았나. 닿았으면 **닿았다고 적는다**. */
  const targetsCapped = audit.data?.target_scan_capped === true;

  /**
   * 「표 내려받기」 — **서버 라우트**가 같은 필터로 낸다(`GET /api/dsm/audit/export.csv`).
   * 화면이 자기 표를 파일로 적지 않는다: 그 순간 파일의 수와 화면의 수가 갈린다.
   */
  const downloadCsv = async () => {
    setCsvBusy(true);
    setCsvError(null);
    try {
      const { bytes } = await downloadAuditCsv(query);
      setCsvDone(`${bytes.toLocaleString()}바이트`);
    } catch (err) {
      setCsvError({
        text: userFacingError('AuditLog.csv', err, '표를 내려받지 못했습니다.'),
        status: (err as { status?: number })?.status ?? 0,
      });
    } finally {
      setCsvBusy(false);
    }
  };

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
          {/* 같은 필터를 그대로 서버에 넘긴다 — 파일과 표가 다른 질의를 타지 않는다. */}
          <Button loading={csvBusy} onClick={() => void downloadCsv()}>
            표 내려받기
          </Button>
        </Space>
      </Card>

      {/* ── CSV 실패 — 상태 칸이다(토스트가 아니다 · P-173) ─────────────────── */}
      {csvError && (
        <FailureNotice
          title="감사 기록 표를 내려받지 못했습니다."
          detail={csvError.text}
          status={csvError.status}
          busy={csvBusy}
          onRetry={() => void downloadCsv()}
        />
      )}
      {csvDone && !csvError && (
        <Card size="small">
          <Space wrap>
            <Tag color="green">표를 내려받았습니다</Tag>
            <Text type="secondary">{csvDone}</Text>
          </Space>
        </Card>
      )}

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
          {/* ── 해시 체인 요약 — 이 쪽의 행들이 앞 행과 이어져 있는가 ─────────── */}
          {chain && (
            <>
              <Text type="secondary">해시 체인</Text>
              <Tag color={chain.broken > 0 ? 'red' : 'green'}>
                이어짐 {chain.linked} · 끊김 {chain.broken}
              </Tag>
              {(chain.unchained > 0 || chain.unknown > 0) && (
                <Tag>
                  체인 이전 {chain.unchained} · 모름 {chain.unknown}
                </Tag>
              )}
            </>
          )}
          {/* ── 대상 분모 — 사건을 가리키는 행이 이 쪽에 몇이고, 그중 몇이 사라졌나 ── */}
          {targets && (
            <>
              <Text type="secondary">대상</Text>
              {/*
                ★ [턴 AA] 갈래를 **다섯 다** 적는다. 「사건 가리킴 273 · 사라짐 153」처럼
                  둘로 줄이면 「열리지 않은 번호를 가리킨 시도」와 「대표 결정으로 지운 사건」이
                  한 수에 섞이고, 섞인 수는 감사 앞에서 못 쓴다. 0 인 갈래도 지우지 않는다.
              */}
              <Tag color={(targets.gone ?? 0) > 0 ? 'orange' : 'green'}>
                사건 가리킴{' '}
                {(targets.live ?? 0) +
                  (targets.deleted_by_decision ?? 0) +
                  (targets.denied_attempt ?? 0) +
                  (targets.gone ?? 0) +
                  (targets.unknown ?? 0)}{' '}
                · 살아 있음 {targets.live ?? 0} · 삭제된 사건 {targets.deleted_by_decision ?? 0} ·
                {' '}열리지 않은 번호 {targets.denied_attempt ?? 0} · 사라짐 {targets.gone ?? 0} ·
                {' '}확인 못 함 {targets.unknown ?? 0}
              </Tag>
              {targetsCapped && (
                <Tag color="orange">이 쪽의 대상 확인이 상한에 닿았습니다</Tag>
              )}
            </>
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
          emptyText="조건에 맞는 감사 기록이 없습니다. 기간이나 조건을 넓혀 보십시오."
        >
          <Table<AuditRow>
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
                /**
                 * 「대상」 — 이 행이 가리키는 사건이 **아직 있는가.**
                 * 가리키는 것이 없는 행(설정 변경 등)은 `—` 다: 「대상이 사라졌다」와
                 * 「대상이 애초에 없다」를 같은 글자로 적지 않는다.
                 */
                title: '대상',
                width: 210,
                render: (_: unknown, r) => {
                  const t = r.target;
                  if (!t) return <Text type="secondary">—</Text>;
                  const word = TARGET_WORD[t.state] ?? TARGET_WORD.gone;
                  const note = word.note(t);
                  return (
                    <Space direction="vertical" size={0}>
                      <Tag color={word.color}>
                        {word.label} #{t.event_id}
                      </Tag>
                      {note && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {note}
                        </Text>
                      )}
                    </Space>
                  );
                },
              },
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
                render: (v: string) => {
                  //: 표에 없는 채널 — **지어내지 않는다.** 원래 이름은 `title` 에 남는다.
                  return hasChannelLabel(v) ? (
                    <span title={v}>{channelLabel(v)}</span>
                  ) : (
                    <Text type="secondary" title={v}>
                      {CHANNEL_NAME_UNKNOWN}
                    </Text>
                  );
                },
              },
              { title: 'HTTP', dataIndex: 'status_http', width: 70 },
              {
                /**
                 * 해시 체인 — **앞 12자 두 개와 이어짐**. 전체 값은 서버가 주고
                 * (`title` 에 그대로 있다), 자르는 것은 화면의 몫이다.
                 * ⚠ 이 칸이 말하는 것은 **이어짐**뿐이다. 위조 여부는
                 *   `evidence_chain.verify_chain` 이 판정한다 — 화면이 그 판정을 흉내내지 않는다.
                 */
                title: '해시 체인',
                width: 260,
                render: (_: unknown, r) => {
                  const word = CHAIN_WORD[r.chain ?? 'unknown'] ?? CHAIN_WORD.unknown;
                  return (
                    <Space direction="vertical" size={0}>
                      <Tag color={word.color}>{word.label}</Tag>
                      <Text type="secondary" style={{ fontSize: 11 }} title={r.hash ?? ''}>
                        {(r.prev_hash ?? '').slice(0, HASH_HEAD) || '—'}
                        {' → '}
                        {(r.hash ?? '').slice(0, HASH_HEAD) || '—'}
                      </Text>
                    </Space>
                  );
                },
              },
            ]}
          />
        </StateBoundary>
      </Card>

      {/**
        * ★★ [턴 Z · U24] **주황을 고장으로 읽지 않게 한다.**
        *
        * 턴 Y 가 「사라진 사건 · 기록된 결정 없음」이라는 글자를 세웠고, 그 글자는 옳다.
        * 그런데 그 줄만 보면 사람은 **「화면이 망가졌나」**로 읽는다 — 주황 딱지 하나가
        * 제 뜻을 스스로 말하지 않기 때문이다. 그래서 그 딱지가 **실제로 떠 있는 쪽에서만**
        * 한 줄로 뜻을 적는다.
        *
        * ★ 0 건일 때는 안 적는다 — 없는 것을 설명하는 문장은 「이 화면에는 늘 사라진
        *   사건이 있다」로 읽힌다. 분모는 위 상태 칸이 **0 이어도** 그대로 말한다.
        */}
      {targets && ((targets.gone ?? 0) > 0 || (targets.deleted_by_decision ?? 0) > 0) && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          「사라진 사건」·「삭제된 사건」은 그 사건이 지금 조회되지 않는다는 뜻입니다.
          감사 기록은 지우지 않으므로 그 행은 그대로 남아 있습니다 — 화면 오류가 아닙니다.
        </Text>
      )}
      {/*
        ★ [턴 AA] 「없는 사건 번호」도 **그 딱지가 실제로 뜬 쪽에서만** 뜻을 적는다.
          위 문장과 합치지 않는다 — 사라진 것과 처음부터 없던 것은 다른 사실이고,
          한 문장에 담으면 읽는 사람이 둘을 같은 일로 읽는다.
      */}
      {targets && (targets.denied_attempt ?? 0) > 0 && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          「열리지 않은 사건 번호」는 그 번호로 사건을 열지 못해 서버가 요청을 막은
          기록입니다. 있던 사건이 없어진 것과는 다른 일입니다.
        </Text>
      )}
      {targetsCapped && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          이 쪽에는 사건을 가리키는 행이 많아 일부 행의 대상을 확인하지 못했습니다.
          「확인 못 함」은 그 사건이 없다는 뜻이 아닙니다 — 기간을 좁혀 다시 보십시오.
        </Text>
      )}

      <Text type="secondary" style={{ fontSize: 12 }}>
        이 표는 서버가 우리 조직의 행위자로 좁혀 준 것입니다. 성공과 막힌 시도가 함께
        있습니다 — 막힌 시도가 안 보이면 「시도가 없었다」와 「막혔다」를 가를 수 없습니다.
      </Text>
    </Space>
  );
}
