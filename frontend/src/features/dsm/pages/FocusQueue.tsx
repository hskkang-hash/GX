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
 * ★ 자료 읽기·쓰기는 이제 `useFocusQueue()`(같은 폴더 `hooks/`)가 진다 — 이 화면은
 *   그 훅이 낸 값을 **그리기만** 한다(WO-01 §4.1 U1 소유 · 턴 Q).
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
 * 조치 중 → 종결). 붙인 자리는 **고정**이다: 1=실제로 확인·접수 · 2=조치 시작 ·
 * 3=종결하기.
 *
 * ★★ [WO-01 §5 · AC-2 · 턴 Q] **키 1 의 뜻이 바뀌었다.** 종전에는 접수(대응 진행
 *   한 칸)만이었다. 이제는 **판정(확인) + 접수를 한 트랜잭션으로 묶는 문**
 *   (`review-and-acknowledge`)을 부른다 — 「이 탐지는 진짜다, 그리고 내가
 *   접수한다」가 사람에게는 한 번의 행동이기 때문이고, 두 번 왕복하면 첫 호출만
 *   성공했을 때 반쪽짜리 사건(판정은 됐는데 접수는 안 됨)이 생긴다. 2·3 은 그대로
 *   대응 진행만 옮긴다 — 이미 판정된 사건에 다시 판정을 얹을 이유가 없다.
 *
 * ★ 오탐(이 탐지는 가짜다)은 **숫자 키에 없다.** 판정 단추를 셋째 축으로 얹으면
 *   「1·2·3」이 어떤 턴에는 처리 단계이고 어떤 턴에는 판정이 되어 뜻이 흔들린다 —
 *   관제실에서 뜻이 흔들리는 키는 오조작을 만든다. 오탐은 **이름 붙은 단추**로만 연다.
 *
 * ★ 숫자 키는 **가장 급한 하나**에만 든다. 대기 카드에는 서버가 `allowed_next` 를
 *   주지 않으므로(그 필드는 `focus` 에만 온다) 화면이 지어낼 수 없다. J·K·Enter 는
 *   대기 카드에도 든다 — 그것은 **읽는 일**이지 쓰는 일이 아니기 때문이다.
 *
 * ★ **심각만 소리가 난다.** 묶인 반복(×N)은 **1회**다. 그 두 문지기는
 *   `useCriticalAlarm` 에 있다. 음소거이거나 브라우저가 소리를 잠가 두었으면
 *   화면이 **먼저** 「소리가 꺼져 있습니다」로 말한다 — 안 울리는 이유를 모르면
 *   사용자는 조용한 화면을 「사건이 없다」로 읽는다.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-25 **토스트를 쓰지 않는다** (턴 Q)
 * ═══════════════════════════════════════════════════════════════════════════
 * 쓰기 성공을 알리는 `message.success(...)` 를 이 화면에 두지 않는다. 결과는
 * 카드의 상태 칸(`response_state` 태그)이 스스로 「접수」 등으로 보인다 —
 * **상태는 칸으로**(불변). 소리(`actionEcho`)만 「눌린 것을 먹었다」는 즉각 신호를 준다.
 */
import { Alert, Badge, Button, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { FALSE_POSITIVE_REASONS, REJECT_LABEL, REVIEW_AND_ACK_LABEL } from '../copy';
import EventSnapshot from '../components/EventSnapshot';
import ResponseClock from '../components/ResponseClock';
import ShortcutHelp from '../components/ShortcutHelp';
import StateBoundary from '../components/StateBoundary';
import { KICK_SENTENCE } from '../constants/kick';
import { useAlertSound } from '../hooks/useAlertSound';
import { useCriticalAlarm } from '../hooks/useCriticalAlarm';
import { useDetectionPing } from '../hooks/useDetectionPing';
import { useFocusQueue } from '../hooks/useFocusQueue';
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
import { stamp, TIMEZONE_NOTE } from '../time';
import type { QueueCard } from '../types';

const { Text, Title, Paragraph } = Typography;

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
  const [showKeys, setShowKeys] = useState(false);
  /** 오탐 사유 3택을 펼쳤는가 — 토스트 대신 **칸 하나를 펼치는** 가벼운 확인. */
  const [pickingReject, setPickingReject] = useState(false);
  /** 0 은 초점 카드, 1 부터가 대기 카드다. **선택은 읽는 일**이다. */
  const [selected, setSelected] = useState(0);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const sound = useAlertSound();

  // ★ [UX-15] 키보드로 일하는 사람은 눌린 것을 눈으로 확인할 시간이 없다 — 쓰기가
  //   성공한 직후 한 음(`actionEcho`)을 울린다. 이 한 음이 없으면 같은 키를 두 번 누른다.
  const { queue, cards, focus, thresholds, acting, actionError, advance,
    reviewAndAcknowledge, reject } = useFocusQueue({
    onActionSuccess: () => sound.play('actionEcho'),
  });

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(queue.reload);

  const data = queue.data;

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

  // 카드가 바뀌면 열어 둔 오탐 사유 칸을 닫는다 — 다른 카드에 잘못 적용되는 것을 막는다.
  useEffect(() => {
    setPickingReject(false);
  }, [focus?.event_id]);

  /**
   * 숫자 키 한 번. **서버가 허락한 칸이 아니면 아무 일도 안 한다** —
   * 화면이 전이표를 들지 않기 때문이고, 안 드는 것이 이 화면의 성질이다.
   *
   * ★ 슬롯 0(`acknowledged`)만 **판정+접수 한 트랜잭션**을 부른다 — 위 머리말 참조.
   */
  const onStep = useCallback(
    (slot: number) => {
      const target = STEP_SLOTS[slot];
      if (!target || !focus || acting) return;
      if (!(focus.allowed_next ?? []).includes(target)) return;
      if (target === 'acknowledged') {
        void reviewAndAcknowledge(focus.event_id);
      } else {
        void advance(focus.event_id, target);
      }
    },
    [focus, acting, advance, reviewAndAcknowledge],
  );

  const onReject = useCallback(
    (reasonLabel: string) => {
      if (!focus || acting) return;
      setPickingReject(false);
      void reject(focus.event_id, reasonLabel);
    },
    [focus, acting, reject],
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
                      위 두 수가 다른 것이 그 약속의 증거이고, 통계는 왼쪽 수(이벤트 원본 건수)를 셉니다.
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
                              숫자는 **고정 자리**다: 실제로 확인·접수 1 · 조치 시작 2 ·
                              종결 3. `acknowledged` 로 가는 단추만 판정+접수 한
                              트랜잭션을 부른다(WO-01 §5 AC-2 · 머리말 참조). */}
                          <Space wrap>
                            {(focus.allowed_next ?? []).map((next) => {
                              const slot = (STEP_SLOTS as readonly string[]).indexOf(next);
                              const isAck = next === 'acknowledged';
                              return (
                                <Button
                                  key={next}
                                  type="primary"
                                  loading={acting}
                                  onClick={() =>
                                    isAck
                                      ? reviewAndAcknowledge(focus.event_id)
                                      : advance(focus.event_id, next)
                                  }
                                >
                                  {isAck ? REVIEW_AND_ACK_LABEL : advanceLabel(next)}
                                  {slot >= 0 ? ` (${slot + 1})` : ''}
                                </Button>
                              );
                            })}
                            {(focus.allowed_next ?? []).length === 0 ? (
                              <Text type="secondary">
                                더 갈 곳이 없습니다 — 이 사건은 마지막 단계입니다.
                              </Text>
                            ) : null}
                            {/* ★ 오탐은 **이름 붙은 단추**로만 연다 — 숫자 키에 얹으면
                                1·2·3 의 뜻이 처리 단계와 판정 사이에서 흔들린다(머리말).
                                이미 판정된 사건에는 다시 판정을 묻지 않는다. */}
                            {!focus.verdict ? (
                              <Button danger loading={acting}
                                onClick={() => setPickingReject((v) => !v)}>
                                {REJECT_LABEL}
                              </Button>
                            ) : null}
                          </Space>

                          {pickingReject ? (
                            <Card size="small" title="오탐 사유">
                              <Space wrap>
                                {FALSE_POSITIVE_REASONS.map((r) => (
                                  <Button key={r.code} size="small" loading={acting}
                                    onClick={() => onReject(r.label)}>
                                    {r.label}
                                  </Button>
                                ))}
                              </Space>
                            </Card>
                          ) : null}

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
