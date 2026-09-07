/**
 * 화면 ③ **이벤트 상세** — E2E-1 의 마지막 칸 (D-371 ①).
 *
 * 이 화면이 E2E-1 전 구간을 닫는다: 탐지 → 목록 → **상세 → 알림 확인**.
 *
 * ★ 발송 이력을 같은 화면에 둔다. 계약 F-10 이 재는 두 점(발생 시각 · 발송 기록)이
 *   **한 화면에서 눈으로** 대조돼야 「30초 안에 나갔다」가 사람에게 사실이 된다.
 *
 * ★ **실패한 발송도 행으로 보인다.** K2 는 실패에 `sent_at` 을 찍지 않는다 —
 *   찍으면 F-10 이 거짓으로 달성된다. 화면도 그 규약을 따라야 하므로
 *   실패 행의 시각 칸을 「—」로 두고 **사유를 옆에 적는다.** 숨기지 않는다 (D-284).
 *
 * ★ 「없는 것은 없다고 적는다」 (D-290): `address_status` 가 `disabled` 면
 *   「조회 대상 아님」이라고 적는다. 빈칸으로 두면 「아직 조회 중」과 같아진다.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  Modal,
  Row,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Main } from 'rj-core';

import {
  dsmEndpoint,
  dsmGet,
  dsmPostOnce,
  dsmPostQuery,
  dsmPostQueryOnce,
  intentKey,
} from '../api';
import { userFacingError } from '../copy';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  advanceLabel,
} from '../severity';
import EventSnapshot from '../components/EventSnapshot';
import ResponseClock from '../components/ResponseClock';
import ResponseSteps, { VerdictBadge } from '../components/ResponseSteps';
import { absolute, durationOrAbsent, relative, stamp, TIMEZONE_NOTE } from '../time';
import type { DeliveryRow, EventDetailView, ResponseTimeline } from '../types';

const { Text, Title } = Typography;

const ADDRESS_STATUS_LABEL: Record<string, string> = {
  resolved: '조회됨',
  pending: '조회 대기',
  disabled: '조회 대상 아님 (좌표 없음)',
};

/**
 * ★ 대응 진행 버튼의 라벨은 **사전(`severity.ts`)에서 온다** (UX-22 · 2026-09-26).
 *   두 벌을 두면 목록·상세·큐가 같은 칸을 서로 다른 말로 부른다.
 *   **전이표는 여전히 화면이 들지 않는다** — 서버가 준 `allowed_next` 에 있는 값만
 *   그린다. 이 표는 「값 → 사람이 읽는 말」일 뿐이고 **무엇이 가능한가는 여기 없다**(D-399).
 */

export default function EventDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [busy, setBusy] = useState('');

  const event = useDsmResource<EventDetailView>(
    () => dsmGet<EventDetailView>(dsmEndpoint.eventDetail(id!)),
    [id],
    { enabled: Boolean(id) },
  );

  const deliveries = useDsmResource<{ total: number; deliveries: DeliveryRow[] }>(
    () => dsmGet(dsmEndpoint.deliveries, { event_id: id }),
    [id],
    {
      enabled: Boolean(id),
      isEmpty: (v) => (v?.deliveries?.length ?? 0) === 0,
    },
  );

  /**
   * UX-14 **네 시각 타임라인.**
   *
   * ★ 착수 전 실측이 지시서를 고쳤다 [2026-09-24]: 넷 중 모델에 있는 것은
   *   `occurred_at` 하나뿐이고, 나머지 셋은 대응 전이 **감사**에서 세운다
   *   (D-399 가 그 칸 주석에 「어떻게 왔는지는 감사가 안다」라고 적어 둔 그대로).
   *   그래서 목록 응답에서 골라 쓸 수 없고 **따로 묻는다.**
   */
  const timeline = useDsmResource<ResponseTimeline>(
    () => dsmGet<ResponseTimeline>(dsmEndpoint.timeline(id!)),
    [id],
    { enabled: Boolean(id) },
  );

  const notify = useCallback(async () => {
    if (!id) return;
    setSending(true);
    try {
      // ★ **마지막으로 남아 있던 이중 제출의 문** (P-87 · 턴 I · 차선 C).
      //   판정·접수·회신 셋은 턴 H 에 멱등 키를 받았는데 **발송만 맨몸이었다.**
      //   그리고 이 문은 누를 때마다 `DeliveryRecord` **행을 만든다** — 두 번 누르면
      //   같은 사람에게 두 통이 가고, 발송 이력에 같은 발송이 두 줄로 남는다.
      //   창 안의 같은 의도는 같은 답을 받는다. 서버도 이 키를 읽는다
      //   (`backend/common/idempotency.py` · `dsm.events.notify`).
      await dsmPostOnce(dsmEndpoint.notify(id), {}, intentKey(`notify:${id}`));
      // ★ 「보냈다」가 아니라 **「발송을 요청했다」**고 말한다. 성공 여부는 아래
      //   이력이 말한다 — 실패도 200 이고, 실패는 행으로 보인다 (F-10).
      message.info('발송을 요청했습니다. 결과는 아래 발송 이력에서 확인하십시오.');
      deliveries.reload();
    } catch (err) {
      message.error(userFacingError('EventDetail.notify', err, '발송 요청이 실패했습니다.'));
    } finally {
      setSending(false);
    }
  }, [id, deliveries]);

  /**
   * ★ 이 화면의 쓰기는 **질의**로 보낸다 — 본문으로 보내면 422 가 나고,
   *   그 422 는 「값이 틀렸다」가 아니라 「인자가 없다」다.
   *
   * ★★ [2026-09-05] **감싸는 함수를 없앴다.** 이 화면은 원래 맞게 짰지만, 조립을
   *   화면마다 손으로 짜는 동안 **세 자리가 빠졌다**(카메라 일괄 등록 · 훈련 모드 ·
   *   「지금 처리할 것」의 처리 단계 넘기기). 맞게 짠 사본이 하나 있다는 사실이
   *   오히려 「손으로 짜도 된다」로 읽혔다. 이제 부르는 이름은 `dsmPostQuery`
   *   하나뿐이고, 게이트가 그 이름 하나만 지키면 된다 —
   *   **판정기가 믿어야 할 이름이 적을수록 판정기가 덜 틀린다.**
   */

  /**
   * U1 #11 「진위 판단 — 진짜인가 오탐인가」.
   *
   * ★ 이 버튼이 없어서 09-20 에 열린 문(`POST /events/{id}/review`)을 **아무도 못
   *   눌렀다** — 착시 ⑨(함수는 문이 아니다)의 이웃, 「문은 있는데 손잡이가 없다」다.
   *
   * ★ 오탐은 **사유를 받는다.** 사유 없는 오탐은 F-14 의 환류에서 「왜」를 잃고,
   *   그러면 다음 달에 같은 오탐이 다시 온다. 서버는 사유를 강제하지 않지만
   *   화면이 먼저 묻는다 — 물어 두면 적힌다.
   *
   * ★ `rejected` 면 **대응 축도 함께 닫힌다**(P-16). 그 일을 화면이 하지 않는다:
   *   서버가 같은 응답에 결과를 실어 준다. 화면이 두 번 부르면 그 사이에
   *   두 종류의 종결이 보인다.
   */
  const review = useCallback(
    (verdict: 'confirmed' | 'rejected') => {
      if (!id) return;
      const isFalsePositive = verdict === 'rejected';
      let reason = '';
      Modal.confirm({
        title: isFalsePositive ? '이 탐지를 오탐으로 판정합니다' : '이 탐지를 실제로 판정합니다',
        content: (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary">
              {isFalsePositive
                ? '오탐으로 판정하면 처리 단계도 함께 종결됩니다. 되돌릴 수 없습니다 — 나중에 실제로 다시 판정해도 처리 단계는 열리지 않습니다.'
                : '판정은 종결한 뒤에도 지워지지 않습니다. 오탐률을 셀 때 이 건이 분모에 들어갑니다.'}
            </Text>
            <Input.TextArea
              rows={2}
              placeholder="사유 (개선 기록에 그대로 실립니다)"
              onChange={(ev) => {
                reason = ev.target.value;
              }}
            />
          </Space>
        ),
        okText: isFalsePositive ? '오탐으로 판정' : '실제로 판정',
        cancelText: '취소',
        onOk: async () => {
          setBusy('review');
          try {
            // ★ **판정 — 멱등 키를 싣는 문 ①.** 같은 판정을 두 번 누르면
            //   요청은 하나이고, 두 번째 누름은 첫 번째의 결과를 받는다.
            await dsmPostQueryOnce(
              dsmEndpoint.review(id),
              { verdict, reason },
              intentKey(`review:${id}:${verdict}`),
            );
            message.success('판정을 기록했습니다.');
            event.reload();
          } catch (err) {
            message.error(userFacingError('EventDetail.review', err, '판정이 실패했습니다.'));
            throw err;   // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
          } finally {
            setBusy('');
          }
        },
      });
    },
    [id, event],
  );

  /** 대응 진행 한 칸 (D-399). 되돌림(종결 → 조치중)은 **사유가 필수**다. */
  const advance = useCallback(
    async (toState: string, backward: boolean) => {
      if (!id) return;
      const send = async (reason: string) => {
        setBusy(toState);
        try {
          // ★ **접수·처리 단계 — 멱등 키를 싣는 문 ②.**
          await dsmPostQueryOnce(
            dsmEndpoint.response(id),
            { to_state: toState, reason },
            intentKey(`response:${id}:${toState}`),
          );
          message.success(`처리 단계를 「${labelOf(RESPONSE_STATE_LABEL, toState)}」 단계로 옮겼습니다.`);
          event.reload();
        } catch (err) {
          message.error(
            userFacingError('EventDetail.advance', err, '처리 단계를 옮기지 못했습니다.'),
          );
          throw err;
        } finally {
          setBusy('');
        }
      };
      if (!backward) {
        await send('');
        return;
      }
      let reason = '';
      Modal.confirm({
        title: '되돌립니다 — 사유가 필요합니다',
        content: (
          <Space direction="vertical" style={{ width: '100%' }}>
            <Text type="secondary">
              되돌림은 「종결 → 조치 중」 하나뿐이고 관제팀장만 할 수 있습니다. 사유가 비면
              서버가 400 으로 거절합니다 — 무엇에서 무엇으로는 표가 알고 「왜」는 여기서만
              들어옵니다.
            </Text>
            <Input.TextArea
              rows={2}
              placeholder="되돌리는 사유 (필수)"
              onChange={(ev) => {
                reason = ev.target.value;
              }}
            />
          </Space>
        ),
        okText: '되돌리기',
        cancelText: '취소',
        onOk: () => send(reason),
      });
    },
    [id, event],
  );

  const e = event.data;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Space>
              <Button onClick={() => navigate('/dsm/events')}>← 목록</Button>
              <Title level={4} style={{ margin: 0 }}>
                이벤트 상세 #{id}
              </Title>
            </Space>
          </Col>
          <Col>
            {/* ★ [UX-20] 「규칙대로 발송」 → 「알림 보내기」. 「규칙대로」가 무엇인지는
                이 화면 앞에서 알 수 없다 (GX-COPY §2). */}
            <Button type="primary" loading={sending} onClick={notify}>
              알림 보내기
            </Button>
          </Col>
        </Row>

        <StateBoundary state={event.state} reason={event.reason} status={event.status} onRetry={event.reload}>
          {e && (
            <Card size="small">
              <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }} bordered>
                <Descriptions.Item label="등급">
                  <Tag color={SEVERITY_COLOR[e.severity] ?? 'default'}>
                    {SEVERITY_ICON[e.severity] ?? '●'} {SEVERITY_LABEL[e.severity] ?? e.severity}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="유형">
                  {labelOf(EVENT_TYPE_LABEL, e.event_type)}
                </Descriptions.Item>
                {/* ★ [UX-22 · 2026-09-26] **넷이던 축을 둘로 줄였다.** 앞판은 「상태 ·
                    판정 · 대응 진행」을 나란히 세웠고, 「상태」는 판정과 같은 것을 다른
                    이름(「기각」)으로 부르던 칸이었다 — 같은 건이 화면에서 두 이름을
                    갖는다. 사용자에게 남기는 축은 **처리 단계**와 **판정** 둘이고,
                    진위 축은 관리자 자리로 물러난다(값·라우트는 그대로 · GX-COPY §1-2). */}
                <Descriptions.Item label="처리 단계">
                  {labelOf(RESPONSE_STATE_LABEL, e.response_state)}
                </Descriptions.Item>
                <Descriptions.Item label="판정">
                  <VerdictBadge verdict={e.verdict} />
                </Descriptions.Item>
                <Descriptions.Item label="발생 시각">
                  {absolute(e.occurred_at)} · {relative(e.occurred_at)}
                </Descriptions.Item>
                <Descriptions.Item label="마지막 관측">
                  {e.last_seen_at ? stamp(e.last_seen_at) : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="카메라">
                  {e.stream_monitor_name || '—'}
                </Descriptions.Item>
                <Descriptions.Item label="확신도">
                  {e.confidence === null || e.confidence === undefined
                    ? '—'
                    : `${(e.confidence * 100).toFixed(1)}%`}
                </Descriptions.Item>
                <Descriptions.Item label="좌표">
                  {e.lat !== null && e.lng !== null ? `${e.lat}, ${e.lng}` : '—'}
                </Descriptions.Item>
                <Descriptions.Item label="주소" span={2}>
                  {e.address || '—'}{' '}
                  <Text type="secondary">
                    ({labelOf(ADDRESS_STATUS_LABEL, e.address_status)})
                  </Text>
                </Descriptions.Item>
                <Descriptions.Item label="영상 구간">
                  {e.clip_path ? '있음' : '없음'}
                </Descriptions.Item>
                <Descriptions.Item label="판정자">
                  {e.reviewed_by_id ? `#${e.reviewed_by_id}` : '아직 아무도 판정하지 않음'}
                  {e.reviewed_at ? ` · ${stamp(e.reviewed_at)}` : ''}
                </Descriptions.Item>
                <Descriptions.Item label="판정 사유" span={2}>
                  {e.reject_reason || '—'}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </StateBoundary>

        {/* ── UX-14 대응 시계 · 네 시각 타임라인 (차선 C · 2026-09-24) ────────
            ★ 「—」와 「0초」를 가른다(D-290): `null` 은 **그 일이 아직 안 일어났다**
              이고 0 은 **즉시 일어났다**이다. 둘을 같은 글자로 그리면
              「아무도 접수 안 함」이 「즉시 접수」로 보인다. */}
        {e && (
          <Card
            size="small"
            title="대응 시계 — 미처리 → 접수 → 조치 중 → 종결"
          >
            <StateBoundary
              state={timeline.state}
              reason={timeline.reason} status={timeline.status}
              onRetry={timeline.reload}
            >
              {timeline.data ? (
                <Row gutter={16}>
                  <Col xs={24} md={8}>
                    {/* P-25 — 인증 헤더가 실리는 경로로 받는다. `<img src>` 직결이 아니다. */}
                    <EventSnapshot
                      eventId={e.event_id}
                      snapshotPath={e.snapshot_path}
                      height={180}
                    />
                  </Col>
                  <Col xs={24} md={16}>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <ResponseClock
                        occurredAt={timeline.data.occurred_at}
                        closedAt={timeline.data.closed_at}
                      />
                      {timeline.data.auto_closed ? (
                        <Alert
                          type="warning"
                          showIcon
                          /* ★ [UX-20] 절 ID(P-16)와 마크다운 별표를 뺐다 — 별표는
                             렌더되지 않고 화면에 그대로 보인다. 통계 이야기(p50/p95
                             분모)는 관리자 자리로 옮기고, 당직자에게 뜻이 있는
                             「사람이 닫은 것이 아니다」만 남긴다 (GX-COPY §4). */
                          message="이 이벤트는 사람이 닫은 것이 아닙니다."
                          description={
                            '오탐으로 판정하여 자동으로 종결된 건입니다. ' +
                            '대응 시간 통계에는 이 건을 넣지 않습니다.'
                          }
                        />
                      ) : null}
                      {timeline.data.reopened > 0 ? (
                        <Alert
                          type="info"
                          showIcon
                          message={`한 번 닫혔다가 다시 열렸습니다 (${timeline.data.reopened}회).`}
                          description="종결 시각은 마지막 종결이고, 아직 안 닫혔으면 비어 있습니다."
                        />
                      ) : null}
                      <Descriptions size="small" column={{ xs: 1, sm: 2 }} bordered>
                        <Descriptions.Item label="① 발생">
                          {absolute(timeline.data.occurred_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="② 접수 확인">
                          {timeline.data.acknowledged_at
                            ? `${absolute(timeline.data.acknowledged_at)} · +${durationOrAbsent(timeline.data.acknowledge_seconds)}`
                            : '아직 아무도 접수하지 않았습니다'}
                        </Descriptions.Item>
                        <Descriptions.Item label="③ 조치 착수">
                          {timeline.data.arrived_at
                            ? `${absolute(timeline.data.arrived_at)} · +${durationOrAbsent(timeline.data.arrive_seconds)}`
                            : '아직 조치가 시작되지 않았습니다'}
                        </Descriptions.Item>
                        <Descriptions.Item label="④ 종결">
                          {timeline.data.closed_at
                            ? `${absolute(timeline.data.closed_at)} · +${durationOrAbsent(timeline.data.close_seconds)}`
                            : '아직 열려 있습니다'}
                        </Descriptions.Item>
                      </Descriptions>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        전이 {timeline.data.transitions.length}건 —{' '}
                        {timeline.data.transitions.length === 0
                          ? '아직 한 칸도 움직이지 않았습니다.'
                          : timeline.data.transitions
                              .map(
                                (t) =>
                                  `${absolute(t.at)} ${t.from}→${t.to}` +
                                  (t.automatic ? ' (규칙)' : ` (${t.by || '알 수 없음'})`),
                              )
                              .join(' · ')}
                      </Text>
                      {/* ★ [UX-20] 이 자리에 감사 채널 이름(`guardianx.dsm.response`)이
                          백틱째로 떠 있었다. 「어디에서 왔는가」는 사실이지만 당직자에게
                          뜻이 없고, 읽는 사람에게는 우리 서랍의 지도다 (GX-COPY §1-3).
                          (내부 사실 · 화면에 적지 않는다: 네 시각은 대응 전이 감사에서
                           세운다 — 모델에 칸을 새로 만들지 않았다. 새 칸은 태어나는 순간
                           과거가 비어 있고, 빈 과거는 「대응이 빨랐다」로 읽힌다.) */}
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        네 시각은 실제로 기록된 처리 이력에서 세웠습니다 — 기록이 없는
                        칸은 비어 있고, 비어 있는 것은 「빨랐다」가 아니라 「아직」입니다.
                      </Text>
                    </Space>
                  </Col>
                </Row>
              ) : null}
            </StateBoundary>
          </Card>
        )}

        {/* ── W2 진위 판정 · 대응 진행 (U1 #11 · U2 #3 · D-399/D-414) ─────────
            ★ 이 칸이 이 화면에만 있는 글자다 — 검수 촬영이 이것으로 단언한다. */}
        {e && (
          <Card size="small" title="처리 단계 · 진위 판정">
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* ★ [UX-22] **처리 단계 한 줄.** 네 칸을 한 줄로 세워 「지금 어디까지
                  왔나」를 한 눈에 낸다 — 앞판은 이 정보가 세 열에 흩어져 있었다. */}
              <ResponseSteps state={e.response_state} />
              <Space wrap>
                <Text strong>진위 판정</Text>
                <Button
                  loading={busy === 'review'}
                  onClick={() => review('confirmed')}
                >
                  실제로 판정
                </Button>
                {/* ⚠ 빨강을 쓰지 않는다 — 빨강은 `critical` 등급 전용이다(ISA-101).
                    오탐 버튼이 빨강이면 관제 화면에서 빨강이 두 뜻을 갖는다. */}
                <Button
                  loading={busy === 'review'}
                  onClick={() => review('rejected')}
                >
                  오탐으로 판정
                </Button>
                <Text type="secondary">현재 판정</Text>
                <VerdictBadge verdict={e.verdict} />
              </Space>

              <Space wrap>
                <Text strong>다음 단계</Text>
                {(e.allowed_next ?? []).length === 0 ? (
                  <Text type="secondary">
                    여기서 옮길 수 있는 다음 단계가 없습니다.
                  </Text>
                ) : (
                  (e.allowed_next ?? []).map((next) => {
                    // 되돌림은 「종결 → 조치중」 하나뿐이다. 그 판정도 서버가 이미 했고
                    // 화면은 **사유를 물어야 하는가**만 안다.
                    const backward = e.response_state === 'closed' && next === 'in_progress';
                    return (
                      <Button
                        key={next}
                        loading={busy === next}
                        onClick={() => advance(next, backward)}
                      >
                        {backward ? '되돌리기 (사유 필수)' : advanceLabel(next)}
                      </Button>
                    );
                  })
                )}
              </Space>

              {/* ★ 없는 것은 없다고 적는다 (D-284 · D-290). 전이 **이력**은 감사에 있고
                  읽는 라우트가 아직 없다 — 빈 표를 그리면 「이력이 없다」로 읽힌다. */}
              {/* ★ [P-27] 없는 것을 없다고 적는 일은 그대로 둔다. 바꾼 것은 **어디에
                  없는지**다 — 감사 채널 이름·커널 경로·표식은 사용자에게 뜻이 없고,
                  그것을 읽는 사람에게는 우리 서랍의 지도가 된다. */}
              <Text type="secondary">
                처리 단계가 바뀐 기록은 남습니다. 다만 이 화면에서는 아직 볼 수 없어
                지금 단계와 다음에 할 수 있는 것만 보여 줍니다 — 지난 기록은 여기 없습니다.
              </Text>
              <Text type="secondary">
                유관기관 통보를 적는 화면은 아직 없습니다. 아래 「발송 이력」은
                알림 발송이지 유관기관 통보가 아닙니다.
              </Text>
            </Space>
          </Card>
        )}

        <Card size="small" title="발송 이력">
          {/* ★ F-10 은 「심각 등급 발생 후 30초 내 발송 기록」이다.
              위의 발생 시각과 아래의 발송 시각이 **한 화면에** 있어야 사람이 잰다.
              ★ [UX-20] 제목에서 절 ID(F-10)를 뺐다 — 절 이름은 제목이 아니다. */}
          <StateBoundary
            state={deliveries.state}
            reason={deliveries.reason} status={deliveries.status}
            onRetry={deliveries.reload}
            emptyText="발송 기록이 없습니다. (요청은 성공했고 0건입니다)"
          >
            <Table<DeliveryRow>
              size="small"
              rowKey={(r, i) => String(r.delivery_id ?? i)}
              pagination={false}
              dataSource={deliveries.data?.deliveries ?? []}
              columns={[
                { title: '채널', dataIndex: 'channel', width: 110 },
                { title: '수신자', dataIndex: 'recipient', ellipsis: true },
                {
                  title: '결과',
                  dataIndex: 'succeeded',
                  width: 90,
                  render: (v: boolean) => (v ? '성공' : '실패'),
                },
                {
                  // 실패에는 시각이 없다 — K2 가 찍지 않는다. 그 사실을 그대로 그린다.
                  title: '발송 시각',
                  dataIndex: 'sent_at',
                  width: 190,
                  render: (v: string | null) => (v ? `${absolute(v)} · ${relative(v)}` : '—'),
                },
                {
                  title: '실패 사유',
                  dataIndex: 'failure_reason',
                  ellipsis: true,
                  render: (v?: string) => v || '',
                },
              ]}
            />
          </StateBoundary>
        </Card>

        {e && e.severity === 'critical' && (
          <Alert
            type="info"
            showIcon
            /* ★ [UX-20] 절 ID(계약 F-10)를 문장에서 뺐다. 「30초」라는 약속은
               당직자에게 뜻이 있으므로 남기고, 그 약속의 이름만 뺀다. */
            message="심각 등급은 발생 후 30초 안에 발송 기록이 남아야 합니다."
            description="위 발생 시각과 아래 발송 시각을 대조하십시오. 실패한 발송에는 시각이 찍히지 않습니다 — 그래야 30초를 지킨 것처럼 보이는 일이 없습니다."
          />
        )}

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
