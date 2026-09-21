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
  dsmDelete,
  dsmEndpoint,
  dsmGet,
  dsmPostOnce,
  dsmPostQuery,
  dsmPostQueryOnce,
  dsmU1Endpoint,
  intentKey,
} from '../api';
import {
  CLIP_MISSING_REASON,
  CLIP_PRESENT,
  dataSourceBadge,
  isNotFound,
  NOT_FOUND_TITLE_EVENT,
  RESPONSE_BACKWARD_NEEDS_REASON,
  userFacingError,
} from '../copy';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { deliveryOutcomeColumns } from '../deliveryOutcome';
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

  /**
   * UX-25′ **진위 판정이 거절된 자리** — 턴 U 넘김을 여기서 닫는다 (턴 V · 차선 U3).
   *
   * 무엇이 문제였나 [소스 실측 2026-09-18]
   * ---------------------------------------
   * 「오탐으로 판정」이 실패하면 이 화면이 하던 일은 **토스트 한 장**(`message.error`)과
   * 열린 채로 남는 확인 창이었다. 토스트는 몇 초 뒤 스스로 사라지고, 사라진 뒤에는
   * 화면에 **아무 자국도 없다** — 관제요원이 잠깐 눈을 돌리면 「눌렀는데 아무 일도
   * 안 일어났다」와 「실패했다」가 같은 그림이 된다. 그 자리에서 사람은 판정이 된
   * 줄 알고 다음 사건으로 넘어간다. 조용한 실패를 조용하게 두지 않는다.
   *
   * 그래서 같은 화면의 상급기관 제출 토글과 **같은 규약**으로 옮긴다 —
   * **상태는 칸으로**(`FocusQueue.tsx` 의 불변 · `FailureNotice`).
   *
   * ★ 실패하면 확인 창은 **닫는다.** 종전에는 「실패했는데 닫히면 성공처럼 보인다」는
   *   이유로 열어 두었는데, 그 이유가 성립한 것은 실패가 토스트뿐이던 때다. 이제
   *   실패가 칸으로 남으므로 창을 열어 두면 **그 칸을 창이 가린다** — 가려진 칸은
   *   없는 칸과 같다.
   * ★ 「다시 시도」는 **그 판정을 그대로 다시 낸다**(`FailureNotice` 규약 ④).
   *   그래서 마지막 시도(판정 + 사유)를 들고 있는다 — 화면을 새로 고치는 단추가 아니다.
   */
  const [reviewError, setReviewError] = useState('');
  const [lastReview, setLastReview] = useState<{
    verdict: 'confirmed' | 'rejected';
    reason: string;
  } | null>(null);

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
   * UX-47 **상급기관 제출 표시** — 턴 T 넘김을 여기서 닫는다.
   *
   * ★ 문은 U24 가 이미 열었다(`api_u24.py:292·301`). 이 화면이 새로 짓는 것은
   *   **손잡이**뿐이다(U1#11 의 진위 판정과 같은 결함 모양 — 「문은 있는데 손잡이가
   *   없다」).
   * ★ **상태는 칸으로**(FocusQueue.tsx 의 불변과 같다) — 토스트를 쓰지 않는다.
   *   눌린 뒤 서버가 돌려준 `flagged` 를 그대로 그린다. 성공을 화면이 지레짐작하지
   *   않는다.
   */
  const upperReport = useDsmResource<{
    flags: Record<string, { flagged: boolean; reported_at: string | null }>;
  }>(
    () => dsmGet(dsmU1Endpoint.upperReportFlags, { event_ids: id }),
    [id],
    { enabled: Boolean(id) },
  );
  const [upperReportBusy, setUpperReportBusy] = useState(false);
  const [upperReportError, setUpperReportError] = useState('');
  const flagged = Boolean(id && upperReport.data?.flags?.[String(id)]?.flagged);

  const toggleUpperReport = useCallback(async () => {
    if (!id) return;
    setUpperReportBusy(true);
    setUpperReportError('');
    try {
      if (flagged) {
        await dsmDelete(dsmU1Endpoint.upperReport(id));
      } else {
        await dsmPostQueryOnce(
          dsmU1Endpoint.upperReport(id), {}, intentKey(`upper-report:${id}`),
        );
      }
      upperReport.reload();
    } catch (err) {
      setUpperReportError(
        userFacingError('EventDetail.upperReport', err, '상급기관 제출 표시를 바꾸지 못했습니다.'),
      );
    } finally {
      setUpperReportBusy(false);
    }
  }, [id, flagged, upperReport]);

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
      const res = await dsmPostOnce<{ total?: number; deliveries?: { succeeded?: boolean }[] }>(
        dsmEndpoint.notify(id), {}, intentKey(`notify:${id}`),
      );
      // ★ 「보냈다」가 아니라 **「발송을 요청했다」**고 말한다. 성공 여부는 아래
      //   이력이 말한다 — 실패도 200 이고, 실패는 행으로 보인다 (F-10).
      // ★★ [턴 Q · P-141 · P-129 대조표] **조용한 0 을 없앤다.** 서버가 중복 억제(F-04
      //   5분)로 한 통도 안 만들면 200 에 `total: 0` 이 온다(`api.py::notify`). 이 자리는
      //   그 응답을 버리고 「요청했습니다」만 말했다 — 그래서 「눌렀는데 발송 수가 그대로」가
      //   원인 없이 보였다. 이제 0 이면 0 이라고 말한다(수신자 0명은 409 로 아래 catch 가 말한다).
      const total = typeof res?.total === 'number' ? res.total : null;
      const failed = (res?.deliveries ?? []).filter((d) => d?.succeeded === false).length;
      if (total === 0) {
        message.warning('새로 보낸 알림이 없습니다. 같은 사건의 알림은 5분 안에 다시 보내지 않습니다. 아래 발송 이력을 확인하십시오.');
      } else if (total !== null && failed > 0) {
        message.warning(`알림 ${total}건 중 ${failed}건이 실패했습니다. 아래 발송 이력에서 사유를 확인하십시오.`);
      } else {
        message.info(
          total !== null
            ? `알림 ${total}건 발송을 요청했습니다. 결과는 아래 발송 이력에서 확인하십시오.`
            : '발송을 요청했습니다. 결과는 아래 발송 이력에서 확인하십시오.',
        );
      }
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
  /**
   * 판정 하나를 **실제로 보낸다.** 확인 창과 「다시 시도」가 **같은 이 함수**를 부른다 —
   * 두 벌로 두면 한쪽만 고쳐지는 날 다시 시도가 다른 요청을 낸다(D-369 의 작은 판).
   */
  const submitReview = useCallback(
    async (verdict: 'confirmed' | 'rejected', reason: string) => {
      if (!id) return;
      setBusy('review');
      setReviewError('');
      setLastReview({ verdict, reason });
      try {
        // ★ **판정 — 멱등 키를 싣는 문 ①.** 같은 판정을 두 번 누르면
        //   요청은 하나이고, 두 번째 누름은 첫 번째의 결과를 받는다.
        //   그래서 「다시 시도」가 판정을 두 벌로 만들지 않는다.
        await dsmPostQueryOnce(
          dsmEndpoint.review(id),
          { verdict, reason },
          intentKey(`review:${id}:${verdict}`),
        );
        // ★ 성공은 **칸이 말한다** — 아래 「현재 판정」 배지가 서버가 준 값으로 다시
        //   그려진다(UX-25). 토스트를 얹으면 같은 사실을 두 곳이 말하고, 그 둘이
        //   어긋나는 날(되읽기 실패) 사라지는 쪽이 진실처럼 보인다.
        setLastReview(null);
        event.reload();
      } catch (err) {
        setReviewError(
          userFacingError('EventDetail.review', err, '진위 판정을 기록하지 못했습니다.'),
        );
      } finally {
        setBusy('');
      }
    },
    [id, event],
  );

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
        // ★ 실패해도 **던지지 않는다** — 창을 닫고 실패를 아래 칸에 남긴다.
        //   위 머리말 참조: 열어 둔 창이 그 칸을 가린다.
        onOk: async () => {
          await submitReview(verdict, reason);
        },
      });
    },
    [id, submitReview],
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
            {/*
              ★★ P-224 (2026-09-21 · 턴 AA · 조율자 쪽지 · `verify_error_body`) —
                **「서버가 400」은 고객 말이 아니다.**

                종전 문안: *「사유가 비면 **서버가 400 으로 거절합니다**」*. 정직하지만
                관제요원의 말이 아니다 — 400 은 우리 저장소의 낱말이고, 읽은 사람이
                할 수 있는 일을 **하나도** 말하지 않는다. U3 가 모바일에서 같은 자리를
                고쳤다(「서버가 404」 → 「저장된 구간이 없습니다」). 같은 규율이다.

              ★ **원인과 다음 손을 같은 줄에.** 원인은 「사유가 비어 있다」이고 다음 손은
                「한 줄 적는다」다. 상태 숫자는 없어져도 사실은 하나도 안 없어진다 —
                거절은 그대로 일어나고, 거절당한 사람이 **무엇을 하면 되는지**만 더해졌다.
              ★ 문구 정본은 `copy.ts::RESPONSE_BACKWARD_NEEDS_REASON`.
            */}
            <Text type="secondary">{RESPONSE_BACKWARD_NEEDS_REASON}</Text>
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
            {/* ★ [P-123 · 턴 O 병합] **없는 사건에 알림을 보낼 수는 없다.**
                404 화면에서도 이 단추가 살아 있었다(실측 count 1). 없는 번호로 알림을
                쏘게 두는 것은 「다시 시도해 보십시오」와 같은 종류의 거짓 안내다.
                경계 **밖**에 있어서 안 가려졌으므로, 여기서 상태를 보고 접는다. */}
            {!isNotFound(event.status) && (
              <Button type="primary" loading={sending} onClick={notify}>
                알림 보내기
              </Button>
            )}
          </Col>
        </Row>

        {/* ★ notFoundTitle — 이 화면은 **무엇이** 없는지 안다. 경계의 기본 문구는
            「없는 항목입니다」이고(같은 경계를 카메라·계량·열람청구도 쓴다),
            사건 상세에서만 「없는 사건입니다」로 좁힌다. */}
        <StateBoundary
          state={event.state} reason={event.reason} status={event.status}
          onRetry={event.reload} notFoundTitle={NOT_FOUND_TITLE_EVENT}
        >
          {e && (
            <Card size="small">
              <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }} bordered>
                <Descriptions.Item label="등급">
                  <Tag color={SEVERITY_COLOR[e.severity] ?? 'default'}>
                    {SEVERITY_ICON[e.severity] ?? '●'} {SEVERITY_LABEL[e.severity] ?? e.severity}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="유형">
                  {/* ★★ P-227 (2026-09-21 · 턴 AB · 차선 U1) — **훈련 배지가 상세에
                      없었다.**

                      목록(`EventList`)과 큐(`FocusQueue`)는 이미 그리고 있었는데
                      **상세와 대시보드만 안 그렸다**[실측 grep · 턴 AB]. 그래서
                      목록에서 「훈련」을 보고 열면 그 말이 **사라지는** 자리가
                      있었다 — 사라진 말은 「실사건이었나」로 읽힌다.
                      ★ 서버는 이미 `data_source` 를 보내고 있었고(상세 응답),
                        말은 `copy.ts::dataSourceBadge`(GX-COPY §2)가 들고 있었다.
                        없던 것은 둘을 잇는 한 줄뿐이다 — 새 말도 새 문도 없다.
                      ★ 실운영이면 `null` 이라 아무것도 안 붙는다. */}
                  <Space size={4} wrap>
                    <span>{labelOf(EVENT_TYPE_LABEL, e.event_type)}</span>
                    {dataSourceBadge(e.data_source) ? (
                      <Tag color="blue" data-gx="event-data-source">
                        {dataSourceBadge(e.data_source)}
                      </Tag>
                    ) : null}
                  </Space>
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
                {/*
                  ★★ P-221 (2026-09-21 · 턴 AA · 세종 실사용 점검) —
                    **「없음」은 참말이고 고객 말이 아니다.**

                    세종: *「고객에게 「영상 구간 없음」은 「CCTV 인데 영상이 없다」이다.」*
                    없는 것은 영상이 아니라 **설정**이다 — 그 카메라에 사건 구간 저장이
                    아직 안 켜졌다. 「없음」 두 글자는 **원인도 다음 손도** 말하지 않아서,
                    읽은 사람이 할 수 있는 일이 「고장 신고」밖에 없다.

                  ★ **원인과 다음 손을 같은 줄에** (이 턴의 불변 「정직한 회색을 고객
                    말로」). 문구 정본은 `copy.ts::CLIP_MISSING_REASON` 이고, 괄호 안은
                    **실재하는 자리**다(관리자 → 카메라 등록).
                  ★ 있을 때는 **아무 설명도 안 붙인다** — 있는 것에 설명을 붙이면
                    없는 것과 같은 무게가 된다.
                */}
                <Descriptions.Item label="영상 구간" span={2}>
                  {e.clip_path ? (
                    CLIP_PRESENT
                  ) : (
                    <Text type="secondary" data-gx="clip-missing">{CLIP_MISSING_REASON}</Text>
                  )}
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

              {/* ★ 눌렀는데 저장이 안 된 자리 — **여기 남는다.** 토스트처럼 사라지지
                  않고, 「다시 시도」가 방금 그 판정을 그대로 한 번 더 낸다. */}
              {reviewError && (
                <FailureNotice
                  title="진위 판정을 기록하지 못했습니다."
                  detail={reviewError}
                  onRetry={
                    lastReview
                      ? () => void submitReview(lastReview.verdict, lastReview.reason)
                      : undefined
                  }
                  busy={busy === 'review'}
                />
              )}

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
              <Space wrap align="center">
                <Text strong>상급기관 제출</Text>
                <Button
                  loading={upperReportBusy}
                  onClick={toggleUpperReport}
                  disabled={!upperReport.data}
                >
                  {flagged ? '제출 표시 해제' : '제출로 표시'}
                </Button>
                <Tag color={flagged ? 'blue' : 'default'}>
                  {flagged ? '상급기관에 제출함' : '아직 제출 표시 없음'}
                </Tag>
              </Space>
              {upperReportError && (
                <FailureNotice
                  title="상급기관 제출 표시를 바꾸지 못했습니다."
                  detail={upperReportError}
                  onRetry={toggleUpperReport}
                  busy={upperReportBusy}
                />
              )}
              <Text type="secondary">
                이 체크는 「우리가 상급기관에 이 사건을 알렸다」는 표시일 뿐입니다 —
                아래 「발송 이력」(알림 발송)과는 다른 사실입니다.
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
                // ★ [P-123 · 턴 O 병합] 「성공」이 **거짓말이었다.**
                //   실측 2026-09-10: `GET /api/dsm/deliveries?limit=200` → 165행 ·
                //   채널 `log` 163 · `succeeded=true` **164** · **수신자 칸 165/165 공백** ·
                //   메일함 **0건**. 즉 초록 「성공」 164줄 옆에서 받은 사람은 0명이었다.
                //   화재 알림에서 「화면이 초록인 것」과 「사람이 받은 것」의 차이는 사람의 목숨이다.
                //   실제 SMTP 는 대표 결정 대기 — 그때까지 **화면이 정직해야 한다**.
                //   두 열의 몸통은 `deliveryOutcome.tsx` 에 한 벌로 있다(모바일 수신함과 같은 말).
                ...deliveryOutcomeColumns,
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
