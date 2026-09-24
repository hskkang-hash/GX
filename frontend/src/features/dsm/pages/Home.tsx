/**
 * S-01b·c·d **역할 홈** — 한 라우트(`/dsm/home`), 역할마다 다른 띠 (P-147 · 턴 R · 차선 F).
 *
 * 왜 이 화면이 생겼나 — **목록은 홈이 아니다**
 * ---------------------------------------------
 * 턴 Q 는 U2·U4·U5 의 첫 화면을 목록·대시보드로 **보냈다**. 1단계로는 옳았다(아무 데도
 * 안 가던 사람이 자기 화면으로 갔다). 그러나 정본이 말하는 홈은 **띠의 수와 카드**이고,
 * 목록은 거기서 1클릭으로 가는 곳이다. 목록을 홈으로 두면 「무슨 일 있었나」를 사람이
 * 표에서 세어야 한다 — 세는 일을 사람에게 돌려주는 화면은 홈이 아니다.
 *
 * ★★ **띠의 수는 목록의 수와 같아야 한다.** 그래서 이 화면은 자기 수를 만들지 않는다:
 *   띠가 그리는 세 수는 전부 `GET /api/dsm/events/summary` 가 낸 값이고, 그 라우트는
 *   목록(`GET /api/dsm/events`)과 **같은 함수**(`services.recent_events`)를 부른다.
 *   화면이 목록을 받아 자기가 세면 페이지 밖의 사건이 없는 것이 되고(DA-04), 그 순간
 *   「미처리 2건」이 거짓말이 된다. 수를 만드는 자리는 서버 하나다.
 *
 * ★ 각 수 옆에는 **그 수를 다시 세는 자리로 가는 링크**가 있다. 같은 서버 필터를 건
 * 목록이고, 두 수가 갈리면 사람이 곧바로 본다 — 대조가 화면 안에 있다.
 *
 * ★ 역할 판정은 **새 표를 만들지 않는다** — 사이드바·첫 화면이 쓰는
 *   `features/nav/roleNav.ts` 의 `bucketOf` 를 그대로 쓴다(두 벌은 반드시 어긋난다).
 *
 * ★ 못 재는 칸은 **비워 두지 않고 그렇게 적는다.** 「시끄러운 카메라」처럼 아직 서버에
 *   내주는 자리가 없는 칸은 빈 카드가 아니라 한 줄의 사실로 남는다 — 빈 카드는
 *   「없다」와 「못 읽었다」를 구별하지 못한다.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Progress,
  Row,
  Segmented,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main, useUserInfo } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmHomeEndpoint } from '../api';
import StateBoundary from '../components/StateBoundary';
import {
  HANDOVER_COPY,
  METERING_COPY,
  ONBOARDING_COPY,
  linkStatusBadge,
  linkStatusLabel,
} from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
// ★ [턴 AB · 조율자] 「처음이세요」 첫 카드 셋은 **차선 K 의 컴포넌트를 그대로 부른다.**
//   여기서 다시 그리면 **판정이 두 벌**이 되고, 두 벌은 언젠가 갈라진다.
import { FirstCards, type KickView } from './Onboarding';
import { CustomRoutes } from '@/services/API';
import { bucketOf, type NavBucket } from '@/features/nav/roleNav';
import { homeRoleCodes } from '@/features/nav/roleHome';
import { dsm2Routes } from '../routes';
import { EVENT_TYPE_LABEL, labelOf } from '../severity';
import { stamp, TIMEZONE_NOTE } from '../time';
import type { EventSummary } from '../types';

const { Text, Title, Paragraph } = Typography;

/** 관제 화면은 사람이 새로고침을 누르고 있을 수 없다. 다른 DSM 화면과 같은 간격이다. */
const REFRESH_MS = 15_000;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '역할 홈 — 지금 우리 관제';

/** 띠의 창. 표에 적힌 둘만 둔다(부속서 A S-01b 입력 칸). */
const WINDOWS = [
  { label: '지난 12시간', value: 12 },
  { label: '지난 7일', value: 168 },
] as const;

interface OnboardingCardRow {
  key: string;
  title: string;
  link: string;
  done: boolean;
  /** 무엇이 이 카드를 닫았는가 — **관리자 자리의 값이다.** 본문에 그리지 않는다. */
  source_ref: string;
  completed_at: string | null;
}

interface OnboardingBlockedRow {
  key: string;
  title: string;
  link: string;
  why: string;
}

interface OnboardingProgressView {
  role: string | null;
  /** ★ [턴 AB] 첫 카드 셋. 서버가 같은 응답에 실어 보낸다 — 홈은 문을 다시 안 두드린다. */
  kick?: KickView;
  role_known: boolean;
  measured_at: string;
  total: number;
  done: number;
  /** 분모 0이면 `null` — 0% 도 100% 도 아니다. */
  percent: number | null;
  measurable: boolean;
  complete: boolean;
  cards: OnboardingCardRow[];
  blocked: OnboardingBlockedRow[];
  blocked_total: number;
}

interface StatsSummaryView {
  since: string;
  until: string;
  /** 같은 기간 목록의 건수와 **같은 수**다(서버가 같은 함수를 부른다). */
  total: number;
  by_event_type: Record<string, number>;
  capped: boolean;
  row_cap: number;
}

interface ReviewerRow {
  reviewer_id: number;
  reviewer_name?: string;
  reviewed_total: number;
  closed_total: number;
  false_positive_total: number;
  avg_response_seconds: number | null;
}

interface ByReviewerView {
  reviewers: ReviewerRow[];
  capped?: boolean;
}

interface PulseView {
  counts: { alive: number; total: number; never_seen: number };
  cluster: { outage_count: number };
}

interface AddressGapView {
  total: number;
  without_address: number;
  measurable: boolean;
}

/** 오탐률 한 줄. **비율만 적지 않는다** — 분자·분모를 함께 적는다. */
function falsePositiveLine(s: EventSummary | null): string {
  if (!s) return '—';
  if (!s.measurable || s.false_positive_rate === null) {
    return '아직 판정한 사건이 없습니다 — 사건을 판정한 뒤 다시 보십시오';
  }
  return `${Math.round(s.false_positive_rate * 100)}% (${s.false_positive}/${s.reviewed})`;
}

/** 「N건」과 「N건 이상」은 다른 사실이다 — 세는 데에도 상한이 있다. */
function unhandledLine(s: EventSummary | null): string {
  if (!s) return '—';
  return s.unhandled_capped ? `${s.unhandled}건 이상` : `${s.unhandled}건`;
}

/**
 * 카드 한 장 — 제목 · 수(있으면) · **누르면 그 화면으로 간다.**
 *
 * ★★ [턴 S · 차선 F] **카드 전체가 누를 것이다.** 종전에는 카드 안의 작은 단추 하나만
 *   눌렸다. 사람은 카드를 누르고, 아무 일도 안 일어나면 그 카드를 **장식**으로 읽는다 —
 *   홈이 「무슨 일 있었나」를 말하고도 다음 걸음을 못 주는 자리가 거기였다.
 *
 * ★ 마우스가 없어도 간다: `role`·`tabIndex` 를 주고 Enter·Space 를 받는다. 관제실에는
 *   키보드만 쓰는 자리가 있고, 갈 수 없는 카드는 그 사람에게 없는 카드다.
 *
 * ★ **갈 곳이 없으면 누를 것도 없다**(`onAction` 없음) — 카드는 그대로 두되 눌리는
 *   시늉을 하지 않는다. 누르면 아무 일도 안 나는 카드는 죽은 단추와 같은 거짓말이다.
 */
function HomeCard({
  title,
  value,
  note,
  actionLabel,
  onAction,
}: {
  title: string;
  value?: string;
  note?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const clickable = Boolean(onAction);
  return (
    <Card
      size="small"
      title={title}
      hoverable={clickable}
      style={{ height: '100%', cursor: clickable ? 'pointer' : 'default' }}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onClick={onAction}
      onKeyDown={(ev) => {
        if (!onAction) return;
        if (ev.key === 'Enter' || ev.key === ' ') {
          ev.preventDefault();
          onAction();
        }
      }}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        {value ? (
          <Text strong style={{ fontSize: 18 }}>
            {value}
          </Text>
        ) : null}
        {note ? <Text type="secondary">{note}</Text> : null}
        {actionLabel && onAction ? (
          <Button
            size="small"
            // 카드가 이미 그 일을 하므로 단추는 **같은 일을 한 번만** 시킨다.
            onClick={(ev) => {
              ev.stopPropagation();
              onAction();
            }}
          >
            {actionLabel}
          </Button>
        ) : null}
      </Space>
    </Card>
  );
}

/**
 * 「처음 시작하기」 — **완료는 서버 기록이 닫는다.** 여기에 체크 상자가 없는 이유다.
 * 100%면 접는다(정본: 100%면 카드 숨김).
 */
function OnboardingBand({ onOpen }: { onOpen: (path: string) => void }) {
  const [open, setOpen] = useState(false);
  const progress = useDsmResource<OnboardingProgressView>(
    () => dsmGet(dsmHomeEndpoint.onboardingProgress),
    [],
  );
  const data = progress.data;

  return (
    <StateBoundary
      state={progress.state}
      reason={progress.reason}
      status={progress.status}
      onRetry={progress.reload}
      where="Home/온보딩"
    >
      {data && data.measurable && !data.complete ? (
        <Card size="small">
          <Space direction="vertical" size={6} style={{ width: '100%' }}>
            <Space
              wrap
              align="center"
            >
              <Text strong>{ONBOARDING_COPY.start}</Text>
              <Progress
                percent={data.percent ?? 0}
                size="small"
                style={{ width: 160 }}
              />
              {/* ★ [턴 S] **수를 글자로도 적는다.** 막대만 있으면 「어디까지 왔나」를
                  눈대중으로 읽게 되고, 눈대중은 보고에 못 쓴다. */}
              <Text type="secondary">
                {ONBOARDING_COPY.progress(data.done, data.total, data.percent ?? 0)}
              </Text>
              <Button
                size="small"
                type="link"
                onClick={() => setOpen((v) => !v)}
              >
                {open ? ONBOARDING_COPY.collapse : ONBOARDING_COPY.expand}
              </Button>
            </Space>
            {open ? (
              <Space
                direction="vertical"
                size={2}
                style={{ width: '100%' }}
              >
                {data.cards.map((c) => (
                  <Space
                    key={c.key}
                    size={6}
                  >
                    <Tag color={c.done ? 'green' : 'default'}>{c.done ? '끝' : '아직'}</Tag>
                    <Button
                      size="small"
                      type="link"
                      onClick={() => onOpen(c.link)}
                    >
                      {c.title}
                    </Button>
                  </Space>
                ))}
                {data.blocked.length ? (
                  <Text type="secondary">
                    {ONBOARDING_COPY.blockedLine(data.blocked_total)}:{' '}
                    {data.blocked.map((b) => b.title).join(' · ')}
                  </Text>
                ) : null}
              </Space>
            ) : null}
          </Space>
        </Card>
      ) : null}

      {/* ★ 첫 카드 셋 — 이미 받은 응답의 `kick` 칸을 넘긴다.
          넘기면 K 의 컴포넌트가 **제 요청을 아예 안 부른다**(`enabled: !kick`) —
          홈 한 장이 같은 문을 두 번 두드리지 않는다.
          ★ 「첫 진입 1회」로 숨기지 않는다 — 그 1회는 브라우저 기억이지 서버 기록이 아니고,
          표시이지 판정이 아니다. 카드가 닫혔는지는 언제나 서버가 말한다(닫히면 K 가 스스로 안 그린다). */}
      <FirstCards kick={data?.kick} />
    </StateBoundary>
  );
}

export default function RoleHome() {
  const navigate = useNavigate();
  const userInfo = useUserInfo();
  const [hours, setHours] = useState<number>(WINDOWS[0].value);

  /** 역할 판정 — **새 표를 만들지 않는다.** 사이드바·첫 화면과 같은 함수다. */
  const bucket: NavBucket | null = useMemo(
    () => bucketOf(homeRoleCodes(userInfo)),
    [userInfo],
  );

  const windowHours = bucket === 'U4' ? 168 : hours;

  /** 띠의 세 수. **목록과 같은 함수**가 낸 값이다(화면이 세지 않는다). */
  const summary = useDsmResource<EventSummary>(
    () => dsmGet(dsmEndpoint.eventsSummary, { hours: windowHours }),
    [windowHours],
    { refreshMs: REFRESH_MS },
  );

  const stats = useDsmResource<StatsSummaryView>(
    () => dsmGet(dsmHomeEndpoint.statsSummary, { since: summary.data?.since }),
    [summary.data?.since],
    { enabled: bucket === 'U4' && Boolean(summary.data?.since) },
  );

  // ★ 「요원별」의 주소는 차선 U24 가 올린 `dsmEndpoint.statsByReviewer` 를 **그대로** 쓴다 —
  //   같은 주소의 상수를 두 벌로 두지 않는다(한쪽만 고쳐지는 날 화면이 갈린다).
  const byReviewer = useDsmResource<ByReviewerView>(
    () => dsmGet(dsmEndpoint.statsByReviewer, { since: summary.data?.since }),
    [summary.data?.since],
    { enabled: bucket === 'U2' && Boolean(summary.data?.since) },
  );

  const pulse = useDsmResource<PulseView>(
    () => dsmGet(dsmEndpoint.cameraPulse),
    [],
    { enabled: bucket === 'U5', refreshMs: REFRESH_MS },
  );

  const gap = useDsmResource<AddressGapView>(
    () => dsmGet(dsmEndpoint.cameraAddressGap),
    [],
    { enabled: bucket === 'U5' },
  );

  const link = useDsmResource<{ status: string; detail?: string }>(
    () => dsmGet(dsmEndpoint.linkState),
    [],
    { enabled: bucket === 'U5', refreshMs: REFRESH_MS },
  );

  const go = (path: string) => navigate(path);

  /**
   * 같은 서버 필터를 건 목록 — **띠의 수를 다시 세는 자리**다.
   * 화면이 거르지 않는다: 이 주소를 열면 서버가 같은 조건으로 다시 센다.
   */
  const unhandledList = '/dsm/events?preset=unhandled';

  /**
   * 인계가 사는 자리. **문자열을 화면 코드에 흩지 않는다** — 라우트 상수에서 읽는다.
   * 종전에는 이 카드가 `/handover` 를 손으로 적고 있었고, 그 주소가 바뀌는 날
   * 카드만 옛말이 된다(옛말이 된 것은 안 보인다 · D-212).
   */
  const handoverPath = CustomRoutes.handover.path;

  const title =
    bucket === 'U2'
      ? '무슨 일 있었나'
      : bucket === 'U4'
        ? '지난 7일'
        : bucket === 'U5'
          ? '관리자 홈'
          : HEADLINE;

  return (
    <Main>
      <Space
        direction="vertical"
        size="middle"
        style={{ width: '100%' }}
      >
        <Row
          justify="space-between"
          align="middle"
        >
          <Col>
            <Space
              size={8}
              align="center"
            >
              <Title
                level={4}
                style={{ margin: 0 }}
              >
                {title}
              </Title>
              {bucket === 'U2' ? (
                <Segmented
                  size="small"
                  value={hours}
                  onChange={(v) => setHours(Number(v))}
                  options={WINDOWS.map((w) => ({ label: w.label, value: w.value }))}
                />
              ) : null}
            </Space>
          </Col>
          <Col>
            <Text type="secondary">
              {summary.loadedAt ? `${stamp(summary.loadedAt)} 기준` : ''} {TIMEZONE_NOTE}
            </Text>
          </Col>
        </Row>

        <OnboardingBand onOpen={go} />

        {bucket === null ? (
          <Alert
            type="info"
            showIcon
            message="이 계정의 자리를 아직 읽지 못했습니다."
            description="관리자에게 역할을 요청하십시오. 주소로 가던 화면은 그대로 열립니다."
          />
        ) : null}

        {/* ── U1 본문 — **띠만 서고 비어 있던 자리** (턴 S · 차선 F) ─────────
            관제요원의 홈은 `/dsm/queue` 그대로다(이미 초록인 자리를 옮기지 않는다).
            그러나 주소로 이 화면에 온 관제요원에게 **안내 한 줄만** 주던 것이 종전이고,
            안내는 화면이 아니다. 네 장을 준다 — 넷 다 **눌리고, 실재하는 화면으로 간다.** */}
        {bucket === 'U1' ? (
          <>
            <Alert
              type="info"
              showIcon
              message="관제요원의 홈은 지금 처리할 것입니다."
              action={
                <Button
                  size="small"
                  onClick={() => go(dsm2Routes.focusQueue.path)}
                >
                  지금 처리할 것 열기
                </Button>
              }
            />
            <Row gutter={[12, 12]}>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="지금 처리할 것"
                  value={unhandledLine(summary.data)}
                  note="가장 급한 하나부터 봅니다."
                  actionLabel="큐 열기"
                  onAction={() => go(dsm2Routes.focusQueue.path)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title={HANDOVER_COPY.title}
                  note={HANDOVER_COPY.lead}
                  actionLabel={HANDOVER_COPY.read}
                  onAction={() => go(handoverPath)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="카메라 격자"
                  note="응답 없는 카메라를 한눈에 봅니다."
                  actionLabel="격자 열기"
                  onAction={() => go(dsm2Routes.cameraGrid.path)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="사건 찾기"
                  note="기간과 카메라, 유형으로 찾습니다."
                  actionLabel="사건 목록 열기"
                  onAction={() => go('/dsm/events')}
                />
              </Col>
            </Row>
          </>
        ) : null}

        {/* ── 띠 — 세 수. 화면이 세지 않는다 ─────────────────────────── */}
        {bucket === 'U2' || bucket === 'U4' ? (
          <Card size="small">
            <StateBoundary
              state={summary.state}
              reason={summary.reason}
              status={summary.status}
              onRetry={summary.reload}
              where="Home/요약"
            >
              <Row gutter={[16, 8]}>
                <Col
                  xs={12}
                  md={6}
                >
                  <Statistic
                    title="미처리"
                    value={unhandledLine(summary.data)}
                  />
                  <Button
                    size="small"
                    type="link"
                    style={{ paddingLeft: 0 }}
                    onClick={() => go(unhandledList)}
                  >
                    목록에서 다시 세기
                  </Button>
                </Col>
                <Col
                  xs={12}
                  md={6}
                >
                  <Statistic
                    title="미판정"
                    value={summary.data ? `${summary.data.unreviewed}건` : '—'}
                  />
                </Col>
                <Col
                  xs={12}
                  md={6}
                >
                  <Statistic
                    title="오탐률"
                    value={falsePositiveLine(summary.data)}
                  />
                </Col>
                <Col
                  xs={12}
                  md={6}
                >
                  <Statistic
                    title="판정한 사건"
                    value={summary.data ? `${summary.data.reviewed}건` : '—'}
                  />
                </Col>
              </Row>
            </StateBoundary>
          </Card>
        ) : null}

        {/* ── U2 카드 넷 ─────────────────────────────────────────────── */}
        {bucket === 'U2' ? (
          <Row gutter={[12, 12]}>
            <Col
              xs={24}
              md={6}
            >
              <HomeCard
                title="미처리"
                value={unhandledLine(summary.data)}
                note="서버가 걸러 준 목록입니다."
                actionLabel="미처리 보기"
                onAction={() => go(unhandledList)}
              />
            </Col>
            <Col
              xs={24}
              md={6}
            >
              <HomeCard
                title="요원별 처리"
                value={
                  byReviewer.data ? `${byReviewer.data.reviewers.length}명` : '—'
                }
                note={
                  byReviewer.data && byReviewer.data.reviewers.length === 0
                    ? '이 기간에 판정한 사람이 없습니다. 기간을 넓혀 보십시오.'
                    : '판정한 사람과 건수입니다.'
                }
                actionLabel="현황 보기"
                onAction={() => go(dsm2Routes.teamStatus.path)}
              />
            </Col>
            <Col
              xs={24}
              md={6}
            >
              <HomeCard
                title="시끄러운 카메라"
                note="카메라별 오탐률을 내주는 자리가 아직 없습니다. 임계값은 설정에서 고칩니다."
                actionLabel="설정 열기"
                onAction={() => go(dsm2Routes.systemSettings.path)}
              />
            </Col>
            <Col
              xs={24}
              md={6}
            >
              <HomeCard
                title={HANDOVER_COPY.title}
                note={HANDOVER_COPY.lead}
                actionLabel={HANDOVER_COPY.read}
                onAction={() => go(handoverPath)}
              />
            </Col>
          </Row>
        ) : null}

        {/* ── U4 카드 넷 (읽기 전용) ─────────────────────────────────── */}
        {bucket === 'U4' ? (
          <>
            <Card size="small">
              <StateBoundary
                state={stats.state}
                reason={stats.reason}
                status={stats.status}
                onRetry={stats.reload}
                where="Home/통계"
              >
                <Space
                  wrap
                  size={16}
                >
                  <Statistic
                    title="지난 7일 사건"
                    value={stats.data ? `${stats.data.total}건` : '—'}
                  />
                  {stats.data
                    ? Object.entries(stats.data.by_event_type)
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 3)
                        .map(([type, n]) => (
                          <Tag key={type}>
                            {labelOf(EVENT_TYPE_LABEL, type)} {n}건
                          </Tag>
                        ))
                    : null}
                </Space>
              </StateBoundary>
            </Card>
            <Row gutter={[12, 12]}>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="기간별 통계"
                  value={stats.data ? `${stats.data.total}건` : '—'}
                  note="같은 기간 목록의 건수와 같은 수입니다."
                  actionLabel="목록에서 다시 세기"
                  onAction={() => go('/dsm/events?period=d7')}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                {/* ★ [턴 S] **갈 곳 없는 카드를 하나 없앴다.** 「자동본을 여는 화면이
                    아직 없습니다」는 참이었지만, 같은 물음(이번 달 우리 센터가 얼마나
                    썼나)에 답하는 화면은 이미 서 있다 — 카드가 그리로 간다. */}
                <HomeCard
                  title={METERING_COPY.title}
                  note="카메라 대수 · 쓰는 사람 수 · 사건 수 · 보낸 알림 수 · 저장 용량을 셉니다."
                  actionLabel="사용량 열기"
                  onAction={() => go(dsm2Routes.metering.path)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="사건 찾기"
                  note="기간과 카메라, 유형으로 찾습니다."
                  actionLabel="사건 목록 열기"
                  onAction={() => go('/dsm/events')}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="열람·삭제 청구"
                  note="접수하고 회신을 기록합니다."
                  actionLabel="청구 화면 열기"
                  onAction={() => go(dsm2Routes.privacyRequests.path)}
                />
              </Col>
            </Row>
          </>
        ) : null}

        {/* ── U5 건강 띠 + 카드 ──────────────────────────────────────── */}
        {bucket === 'U5' ? (
          <>
            <Card size="small">
              <StateBoundary
                state={pulse.state}
                reason={pulse.reason}
                status={pulse.status}
                onRetry={pulse.reload}
                where="Home/건강"
              >
                <Space
                  wrap
                  size={16}
                >
                  <Statistic
                    title="카메라 정상"
                    value={
                      pulse.data
                        ? `${pulse.data.counts.alive}/${pulse.data.counts.total}`
                        : '—'
                    }
                  />
                  <Statistic
                    title="주소 미입력"
                    value={
                      gap.data && gap.data.measurable
                        ? `${gap.data.without_address}대`
                        : '아직 잴 수 없습니다 — 카메라를 등록하십시오'
                    }
                  />
                  <div>
                    <Text type="secondary">연계</Text>
                    <div>
                      <Tag color={linkStatusBadge(link.data?.status) === 'error' ? 'red' : 'blue'}>
                        {linkStatusLabel(link.data?.status)}
                      </Tag>
                    </div>
                  </div>
                  <Statistic
                    title="구역 두절"
                    value={pulse.data ? `${pulse.data.cluster.outage_count}곳` : '—'}
                  />
                </Space>
              </StateBoundary>
              <Paragraph
                type="secondary"
                style={{ marginTop: 8, marginBottom: 0 }}
              >
                저장 용량과 백업 회수증은 아직 이 띠에 올리지 못합니다 — 서버가 내주는 자리가
                없습니다. 보존·백업 설정 화면에서 선언 상태를 봅니다.
              </Paragraph>
            </Card>
            <Row gutter={[12, 12]}>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="사람"
                  note="계정과 역할을 관리합니다."
                  actionLabel="사람 열기"
                  onAction={() => go('/users')}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="카메라"
                  value={
                    gap.data && gap.data.measurable ? `${gap.data.total}대` : '—'
                  }
                  note="이름·코드·주소를 붙여넣고 표를 먼저 봅니다."
                  actionLabel="카메라 등록 열기"
                  onAction={() => go(dsm2Routes.cameraImport.path)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="보존·백업"
                  note="보관 기간과 백업 상태를 선언합니다."
                  actionLabel="설정 열기"
                  onAction={() => go(dsm2Routes.systemSettings.path)}
                />
              </Col>
              <Col
                xs={24}
                md={6}
              >
                <HomeCard
                  title="훈련 모드"
                  note="켜면 사람에게 알림이 나가지 않습니다."
                  actionLabel="훈련 모드 열기"
                  onAction={() => go(dsm2Routes.drill.path)}
                />
              </Col>
            </Row>
          </>
        ) : null}
      </Space>
    </Main>
  );
}
