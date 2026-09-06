/**
 * UX-13 **단일 초점 큐** — W1 최상단은 목록이 아니라 **가장 급한 하나**다.
 *
 * 무엇이 문제였나
 * ---------------
 * 지금 W1 은 최신순 목록이다. 최신순이면 새 이벤트가 계속 최상단을 밀어내고,
 * **가장 오래 방치된 사건이 영원히 안 보인다.** 그리고 같은 카메라가 3분 사이 7번
 * 울리면 그 7장이 화면을 채워, 밀려난 자리에 있던 **다른 카메라의 첫 발생**이 사라진다.
 * 이 화면이 막는 것이 정확히 그 두 자리다.
 *
 * 무엇을 그리나
 * -------------
 *   ① **초점 카드 하나** — 대응 시계(UX-14) · 스냅샷 · 버튼 셋.
 *   ② 나머지를 5분 창 `stream+type` 으로 묶은 카드들. 각 카드에 **「×N」 배지**.
 *
 * ★ **이벤트를 접는 것이 아니다.** 원본 건수(`total_events`)를 화면에 **그대로 적는다** —
 *   카드 수(`card_total`)와 다른 수이고, 다른 것이 요점이다. F-14 통계는 원본을 세고
 *   접히는 것은 화면이지 기록이 아니다. 두 수를 나란히 두는 것이 그 약속의 증거다.
 *
 * ★ 「가장 급한」은 **서버가 정한다.** 화면이 정하면 화면마다 다른 하나가 최상단에
 *   오고, 교대 인계에서 두 사람이 다른 사건을 이야기하게 된다.
 *   이 파일에 `sort(` 도 `filter(` 도 없다 — 없는 것이 이 화면의 성질이다.
 *
 * ★ 버튼 셋은 **서버가 준 `allowed_next`** 로 그린다. 화면이 전이표를 따로 들면
 *   **서버가 거절하는 버튼**을 그리게 된다 (D-399).
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-15 **키보드 · 소리** (차선 C1 · 2026-09-05)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 무엇이 문제였나: 판정 경로가 **클릭뿐**이고 소리는 **0종**이었다. 관제요원은
 * 8시간 마우스를 쥐지 않는다.
 *
 * 1 · 2 · 3 을 **무엇에 붙였나** [판단과 그 사유]
 * ---------------------------------------------
 * 이 저장소의 축은 둘이다 — **판정**(실제 / 오탐)과 **처리 단계**(미처리 → 접수 →
 * 조치 중 → 종결). 사전 규칙 4 는 「한 화면에 축은 하나」이고, **이 화면이 이미 가진
 * 축은 처리 단계 하나뿐**이다(단추가 `allowed_next` 로만 그려진다 · 판정 단추는
 * 이 화면에 없다). 그래서 단축키도 **처리 단계**에 붙였다. 판정 단축키를 여기 붙이면
 * 축이 둘이 되고, 축이 둘이면 사람이 어느 축을 눌렀는지 모른다.
 *
 * 붙인 자리는 **고정**이다: 1=접수하기 · 2=조치 시작 · 3=종결하기.
 * ★ `allowed_next` 의 **순서**에 붙이지 않았다. 순서에 붙이면 카드마다 1 의 뜻이
 *   달라진다 — 미처리 카드에서 1 은 접수인데 접수된 카드에서 1 은 조치 시작이 된다.
 *   관제실에서 **뜻이 흔들리는 키**는 오조작을 만든다. 고정으로 두고, 서버가 허락한
 *   칸만 살린다(D-399 는 그대로다 — 화면은 여전히 자기 전이표를 갖지 않는다).
 *
 * ★ 숫자 키는 **가장 급한 하나**에만 든다. 대기 카드에는 서버가 `allowed_next` 를
 *   주지 않으므로(그 필드는 `focus` 에만 온다) 화면이 지어낼 수 없다. J·K·Enter 는
 *   대기 카드에도 든다 — 그것은 **읽는 일**이지 쓰는 일이 아니기 때문이다.
 *
 * ★ **심각만 소리가 난다.** 묶인 반복(×N)은 **1회**다. 그 두 문지기는
 *   `useCriticalAlarm` 에 있다. 음소거이거나 브라우저가 소리를 잠가 두었으면
 *   화면이 **먼저** 「소리가 꺼져 있습니다」로 말한다 — 안 울리는 이유를 모르면
 *   사용자는 조용한 화면을 「사건이 없다」로 읽는다.
 */
import { Alert, Badge, Button, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmPostQueryOnce, intentKey } from '../api';
import { userFacingError } from '../copy';
import EventSnapshot from '../components/EventSnapshot';
import ResponseClock from '../components/ResponseClock';
import ShortcutHelp from '../components/ShortcutHelp';
import StateBoundary from '../components/StateBoundary';
import { KICK_SENTENCE } from '../constants/kick';
import { useAlertSound } from '../hooks/useAlertSound';
import { useCriticalAlarm } from '../hooks/useCriticalAlarm';
import { useDsmResource } from '../hooks/useDsmResource';
import { useDetectionPing } from '../hooks/useDetectionPing';
import { useQueueKeys } from '../hooks/useQueueKeys';
import { dsm2Routes } from '../routes';
import {
  advanceLabel,
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../severity';
import { FALLBACK_TIER_THRESHOLDS_SEC, stamp, TIMEZONE_NOTE } from '../time';
import type { FocusQueue as FocusQueueView, QueueCard } from '../types';

const { Text, Title, Paragraph } = Typography;

const REFRESH_MS = 15_000;

/**
 * 숫자 키 → 처리 단계. **고정이다** (위 머리말의 판단).
 * 값은 계약 스키마의 것이고 화면 표시 이름은 `RESPONSE_STATE_LABEL` 이 따로 든다.
 */
const STEP_SLOTS = ['acknowledged', 'in_progress', 'closed'] as const;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '지금 처리할 것 — 가장 급한 하나';

function eventPath(id: number): string {
  return `/dsm/events/${id}`;
}

function CardHead({ card }: { card: QueueCard }) {
  return (
    <Space wrap size={6}>
      <Tag color={SEVERITY_COLOR[card.severity] ?? 'default'}>
        {SEVERITY_ICON[card.severity] ?? '•'}{' '}
        {labelOf(SEVERITY_LABEL, card.severity)}
      </Tag>
      <Text strong>{labelOf(EVENT_TYPE_LABEL, card.event_type)}</Text>
      <Text type="secondary">{card.stream_monitor_name || '이름 없는 카메라'}</Text>
      <Tag>{labelOf(RESPONSE_STATE_LABEL, card.response_state)}</Tag>
      {card.count > 1 ? (
        // ★ 「×1」은 배지를 안 단다 — 정보가 아니라 소음이다.
        <Badge
          count={`×${card.count}`}
          style={{ backgroundColor: '#fa541c' }}
          title={
            `같은 카메라·같은 유형이 ${Math.round(card.window_seconds / 60)}분 창 안에 ` +
            `${card.count}번 났습니다. 카드만 묶였고 이벤트 ${card.count}건은 그대로 있습니다 ` +
            `(id: ${card.member_event_ids.join(', ')}).`
          }
        />
      ) : null}
    </Space>
  );
}

export default function FocusQueuePage() {
  const navigate = useNavigate();
  const [acting, setActing] = useState(false);
  const [actionError, setActionError] = useState<string>('');
  const [showKeys, setShowKeys] = useState(false);
  /** 0 은 초점 카드, 1 부터가 대기 카드다. **선택은 읽는 일**이다. */
  const [selected, setSelected] = useState(0);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const sound = useAlertSound();

  const queue = useDsmResource<FocusQueueView>(
    () => dsmGet(dsmEndpoint.eventsQueue, { limit: 200 }),
    [],
    {
      refreshMs: REFRESH_MS,
      isEmpty: (v) => (v?.total_events ?? 0) === 0,
    },
  );

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(queue.reload);

  const data = queue.data;
  const focus = data?.focus ?? null;

  /** 초점 하나 + 대기 카드들. **여기서 거르지도 정렬하지도 않는다** — 서버 순서 그대로다. */
  const cards = useMemo<QueueCard[]>(
    () => (focus ? [focus, ...(data?.queue ?? [])] : [...(data?.queue ?? [])]),
    [focus, data],
  );

  const thresholds = data?.tier_thresholds_sec ?? [...FALLBACK_TIER_THRESHOLDS_SEC];

  // ★ 심각만 · 묶음은 1회. 문지기는 훅 안에 있다.
  useCriticalAlarm({
    cards,
    thresholds,
    play: sound.play,
    ready: queue.state === 'data' || queue.state === 'empty',
  });

  // 선택이 목록 밖으로 나가지 않게 한다. 카드가 줄면 선택도 줄어야 한다.
  useEffect(() => {
    setSelected((n) => (cards.length === 0 ? 0 : Math.min(n, cards.length - 1)));
  }, [cards.length]);

  // 골라 놓은 줄이 화면 밖에 있으면 고른 것이 아니다.
  useEffect(() => {
    rowRefs.current[selected]?.scrollIntoView({ block: 'nearest' });
  }, [selected]);

  const advance = useCallback(
    async (eventId: number, toState: string) => {
      setActing(true);
      setActionError('');
      try {
        // ★ 질의로 보낸다 — 본문이면 **422(인자 없음)** 다.
        //   [실측 2026-09-05 · 없는 id 999999999 로 두드림 · 아무것도 안 씀]
        //       본문 → 422 loc:["query","to_state"] · 질의 → 404 (행이 없다)
        //   이 자리는 관제요원이 **미처리를 접수로 넘기는** 단추다. 422 면 넘길 수
        //   없는데 화면은 멀쩡히 떠 있다 — 가장 늦게 발견되는 종류의 고장이다.
        // ★ **접수 — 멱등 키를 싣는 문 ②**(키보드로 일하는 화면). 여기가 두 번 눌리는
        //   확률이 가장 높다: 숫자 키는 사람이 「먹었나?」 싶으면 곧바로 다시 누른다.
        await dsmPostQueryOnce(
          dsmEndpoint.response(eventId),
          { to_state: toState },
          intentKey(`q.response:${eventId}:${toState}`),
        );
        // 키보드로 일하는 사람은 **눌린 것을 눈으로 확인할 시간이 없다.**
        // 이 한 음이 없으면 같은 키를 두 번 누른다.
        sound.play('actionEcho');
        queue.reload();
      } catch (err) {
        // ★ 거절은 4xx 로 온다. **서버가 쓴 한국어 사유는 그대로 낸다** — 서버가 왜
        //   거절했는지가 화면에 안 닿으면 사용자는 「버튼이 안 먹는다」로 읽는다.
        // ★★ [P-78 ① · 턴 H] 그런데 응답이 없으면 이 자리에 axios 원문이 들어온다.
        //   서버가 쓴 문장과 전송 계층이 만든 문장을 가르는 것이 `userFacingError` 다.
        setActionError(userFacingError('FocusQueue.act', err, '요청이 처리되지 않았습니다.'));
      } finally {
        setActing(false);
      }
    },
    [queue, sound],
  );

  /**
   * 숫자 키 한 번. **서버가 허락한 칸이 아니면 아무 일도 안 한다** —
   * 화면이 전이표를 들지 않기 때문이고, 안 드는 것이 이 화면의 성질이다.
   */
  const onStep = useCallback(
    (slot: number) => {
      const target = STEP_SLOTS[slot];
      if (!target || !focus || acting) return;
      if (!(focus.allowed_next ?? []).includes(target)) return;
      void advance(focus.event_id, target);
    },
    [focus, acting, advance],
  );

  useQueueKeys({
    onNext: () => setSelected((n) => Math.min(n + 1, Math.max(cards.length - 1, 0))),
    onPrev: () => setSelected((n) => Math.max(n - 1, 0)),
    onOpen: () => {
      const card = cards[selected];
      if (card) navigate(eventPath(card.event_id));
    },
    onStep,
    onToggleSound: sound.toggle,
    onReload: queue.reload,
  });

  const selectedRing = (index: number) =>
    index === selected ? '2px solid #1677ff' : '2px solid transparent';

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/*
          P-52 킥 문장 — **둘째 자리.** 로그인 화면과 **같은 상수**에서 온다
          (`../constants/kick`). 여기 손으로 다시 적으면 두 자리가 갈리고, 갈린
          문장 둘은 제품 소개가 아니라 장식 둘이다.

          ★ 제목 위에 둔다. 이 화면은 관제요원이 하루 종일 켜 두는 화면이고, 제목
            아래로 내려가면 「가장 급한 하나」와 섞여 사건 정보처럼 읽힌다 —
            이 문장은 사건이 아니라 **제품이 무엇을 하는 물건인지**를 말한다.
          ★ 작고 흐리다. 관제 화면의 주인공은 언제나 카드다.
        */}
        <Text type="secondary" style={{ fontSize: 12 }}>
          {KICK_SENTENCE}
        </Text>

        <Row justify="space-between" align="middle">
          <Col>
            <Space size={4} align="center">
              <Title level={4} style={{ margin: 0 }}>
                {HEADLINE}
              </Title>
              {/* UX-03 — 역할 첫 화면의 「?」. 처음 온 사람이 여기서 시작한다. */}
              <Button
                type="text"
                size="small"
                aria-label="처음 시작하기"
                onClick={() => navigate(`${dsm2Routes.onboarding.path}?role=OPERATOR`)}
              >
                ?
              </Button>
            </Space>
          </Col>
          <Col>
            <Space size={8} wrap>
              <Button size="small" onClick={() => setShowKeys((v) => !v)}>
                단축키
              </Button>
              {/* 상태가 아니라 **누르면 일어나는 일**을 적는다 (사전 §5). */}
              <Button size="small" onClick={sound.audible ? sound.toggle : sound.enable}>
                {sound.audible ? '소리 끄기' : '소리 켜기'}
              </Button>
              <Text type="secondary">
                {queue.loadedAt ? `갱신 ${stamp(queue.loadedAt)}` : ''} · {TIMEZONE_NOTE}
              </Text>
            </Space>
          </Col>
        </Row>

        {/* ★ 안 울리는 이유를 **먼저** 말한다. 조용한 화면은 평온과 구별되지 않는다. */}
        {!sound.audible ? (
          <Alert type="warning" showIcon message="소리가 꺼져 있습니다" />
        ) : null}

        {showKeys ? (
          <ShortcutHelp targetNote="숫자 키는 가장 급한 하나에만 듭니다." />
        ) : null}

        <StateBoundary
          state={queue.state}
          reason={queue.reason} status={queue.status}
          onRetry={queue.reload}
          emptyText="지금 열려 있는 이벤트가 없습니다 — 평온합니다."
        >
          {data ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* ★ 두 수를 **나란히** 둔다. 접힌 것은 카드이지 기록이 아니다. */}
              <Card size="small">
                <Row gutter={16}>
                  <Col>
                    <Statistic title="이벤트(원본 건수)" value={data.total_events} />
                  </Col>
                  <Col>
                    <Statistic title="카드(5분 창 묶음)" value={data.card_total} />
                  </Col>
                  <Col flex="auto">
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      같은 카메라·같은 유형이{' '}
                      {Math.round(data.window_seconds / 60)}분 창 안에 연속으로 나면
                      카드 한 장에 「×N」으로 묶입니다. <b>이벤트는 접지 않습니다</b> —
                      위 두 수가 다른 것이 그 약속의 증거이고, F-14 통계는 왼쪽 수를 봅니다.
                      {data.sample_capped
                        ? ' ⚠ 표본 상한에 닿았습니다 — 더 오래된 이벤트가 이 화면 밖에 있습니다.'
                        : ''}
                    </Paragraph>
                  </Col>
                </Row>
              </Card>

              {actionError ? (
                <Alert type="error" showIcon message="거절되었습니다." description={actionError} />
              ) : null}

              {focus ? (
                <div
                  ref={(el) => {
                    rowRefs.current[0] = el;
                  }}
                  style={{ border: selectedRing(0), borderRadius: 8 }}
                  onClick={() => setSelected(0)}
                >
                  <Card
                    title={<CardHead card={focus} />}
                    extra={
                      <Button type="link" onClick={() => navigate(eventPath(focus.event_id))}>
                        상세 열기
                      </Button>
                    }
                  >
                    <Row gutter={16}>
                      <Col xs={24} md={10}>
                        <EventSnapshot
                          eventId={focus.event_id}
                          snapshotPath={focus.snapshot_path}
                          height={240}
                        />
                      </Col>
                      <Col xs={24} md={14}>
                        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                          <div>
                            <Text type="secondary">대응 시계 · 발생 {stamp(focus.occurred_at)}</Text>
                            <ResponseClock
                              occurredAt={focus.occurred_at}
                              closedAt={focus.closed_at}
                              thresholds={data.tier_thresholds_sec}
                            />
                          </div>

                          {/* ★ 버튼은 서버가 준 `allowed_next` 로만 그린다 —
                              화면이 전이표를 들면 서버가 거절하는 버튼을 그리게 된다.
                              숫자는 **고정 자리**다: 접수 1 · 조치 시작 2 · 종결 3. */}
                          <Space wrap>
                            {(focus.allowed_next ?? []).map((next) => {
                              const slot = (STEP_SLOTS as readonly string[]).indexOf(next);
                              return (
                                <Button
                                  key={next}
                                  type="primary"
                                  loading={acting}
                                  onClick={() => advance(focus.event_id, next)}
                                >
                                  {advanceLabel(next)}
                                  {slot >= 0 ? ` (${slot + 1})` : ''}
                                </Button>
                              );
                            })}
                            {(focus.allowed_next ?? []).length === 0 ? (
                              <Text type="secondary">
                                더 갈 곳이 없습니다 — 이 사건은 마지막 단계입니다.
                              </Text>
                            ) : null}
                          </Space>

                          {focus.count > 1 ? (
                            <Alert
                              type="info"
                              showIcon
                              message={`이 카드에 ${focus.count}건이 묶여 있습니다.`}
                              description={`이벤트 id: ${focus.member_event_ids.join(', ')} — 카드만 묶였고 기록은 그대로입니다.`}
                            />
                          ) : null}
                        </Space>
                      </Col>
                    </Row>
                  </Card>
                </div>
              ) : (
                <Alert
                  type="success"
                  showIcon
                  message="지금 가장 급한 사건이 없습니다."
                  description="열려 있는 이벤트가 0건입니다 — 못 가져온 것이 아니라 없습니다."
                />
              )}

              {/* 나머지 큐. 초점 하나 아래에 **작게** 둔다 — 여기가 커지면 다시 목록이 된다. */}
              <Card size="small" title={`대기 카드 ${data.queue.length}장`}>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {data.queue.length === 0 ? (
                    <Text type="secondary">대기 중인 카드가 없습니다.</Text>
                  ) : null}
                  {data.queue.map((card, i) => {
                    const index = focus ? i + 1 : i;
                    return (
                      <div
                        key={`${card.stream_monitor_id}-${card.event_type}-${card.event_id}`}
                        ref={(el) => {
                          rowRefs.current[index] = el;
                        }}
                        style={{ border: selectedRing(index), borderRadius: 6 }}
                        onClick={() => setSelected(index)}
                      >
                        <Row
                          align="middle"
                          gutter={12}
                          style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}
                        >
                          <Col flex="auto">
                            <CardHead card={card} />
                            <div>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                발생 {stamp(card.occurred_at)}
                              </Text>
                            </div>
                          </Col>
                          <Col>
                            <ResponseClock
                              occurredAt={card.occurred_at}
                              closedAt={card.closed_at}
                              thresholds={data.tier_thresholds_sec}
                              compact
                            />
                          </Col>
                          <Col>
                            <Button size="small" onClick={() => navigate(eventPath(card.event_id))}>
                              열기
                            </Button>
                          </Col>
                        </Row>
                      </div>
                    );
                  })}
                </Space>
              </Card>
            </Space>
          ) : null}
        </StateBoundary>
      </Space>
    </Main>
  );
}
