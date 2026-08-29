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

import { dsmEndpoint, dsmGet, dsmPost } from '../api';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import {
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
  STATUS_LABEL,
  VERDICT_LABEL,
} from '../severity';
import { absolute, relative, stamp, TIMEZONE_NOTE } from '../time';
import type { DeliveryRow, EventDetailView } from '../types';

const { Text, Title } = Typography;

const ADDRESS_STATUS_LABEL: Record<string, string> = {
  resolved: '조회됨',
  pending: '조회 대기',
  disabled: '조회 대상 아님 (좌표 없음)',
};

/**
 * ★ 대응 진행 버튼의 라벨. **전이표를 화면이 들지 않는다** — 서버가 준 `allowed_next`
 *   에 있는 값만 그린다. 화면이 자기 표를 들면 서버가 거절하는 버튼을 그리게 된다(D-399).
 *   이 표는 「값 → 사람이 읽는 말」일 뿐이고, **무엇이 가능한가는 여기 없다.**
 */
const ADVANCE_LABEL: Record<string, string> = {
  acknowledged: '접수 확인',
  in_progress: '조치 시작',
  closed: '종결',
};

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

  const notify = useCallback(async () => {
    if (!id) return;
    setSending(true);
    try {
      await dsmPost(dsmEndpoint.notify(id));
      // ★ 「보냈다」가 아니라 **「발송을 요청했다」**고 말한다. 성공 여부는 아래
      //   이력이 말한다 — 실패도 200 이고, 실패는 행으로 보인다 (F-10).
      message.info('발송을 요청했습니다. 결과는 아래 발송 이력에서 확인하십시오.');
      deliveries.reload();
    } catch (err) {
      message.error(err instanceof Error ? err.message : '발송 요청이 실패했습니다.');
    } finally {
      setSending(false);
    }
  }, [id, deliveries]);

  /**
   * ★ 질의문자열로 보낸다. 이 라우트들의 인자는 django-ninja 기본값에 따라
   *   **본문이 아니라 질의**다 — 본문으로 보내면 422 가 나고, 그 422 는
   *   「값이 틀렸다」가 아니라 「인자가 없다」다. 둘을 헷갈리면 한나절이 간다.
   */
  const postWith = useCallback(
    (url: string, query: Record<string, string>) => {
      const qs = new URLSearchParams(query).toString();
      return dsmPost(`${url}?${qs}`);
    },
    [],
  );

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
                ? '오탐으로 판정하면 대응 축도 함께 종결됩니다 (규칙이 닫습니다 · P-16). 되돌릴 수 없습니다 — 나중에 실제로 다시 판정해도 대응 축은 열리지 않습니다.'
                : '판정은 종료되어도 지워지지 않습니다 (D-293). 오탐률의 분모에 이 건이 들어갑니다.'}
            </Text>
            <Input.TextArea
              rows={2}
              placeholder="사유 (F-14 환류에 그대로 실립니다)"
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
            await postWith(dsmEndpoint.review(id), { verdict, reason });
            message.success('판정을 기록했습니다.');
            event.reload();
          } catch (err) {
            message.error(err instanceof Error ? err.message : '판정이 실패했습니다.');
            throw err;   // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
          } finally {
            setBusy('');
          }
        },
      });
    },
    [id, event, postWith],
  );

  /** 대응 진행 한 칸 (D-399). 되돌림(종결 → 조치중)은 **사유가 필수**다. */
  const advance = useCallback(
    async (toState: string, backward: boolean) => {
      if (!id) return;
      const send = async (reason: string) => {
        setBusy(toState);
        try {
          await postWith(dsmEndpoint.response(id), { to_state: toState, reason });
          message.success(`대응 진행을 「${ADVANCE_LABEL[toState] ?? toState}」로 옮겼습니다.`);
          event.reload();
        } catch (err) {
          message.error(err instanceof Error ? err.message : '대응 진행이 실패했습니다.');
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
              되돌림은 「종결 → 조치중」 하나뿐이고 관제팀장만 할 수 있습니다. 사유가 비면
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
    [id, event, postWith],
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
            <Button type="primary" loading={sending} onClick={notify}>
              규칙대로 발송
            </Button>
          </Col>
        </Row>

        <StateBoundary state={event.state} reason={event.reason} onRetry={event.reload}>
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
                <Descriptions.Item label="상태">
                  <span style={{ textDecoration: e.status === 'closed' ? 'line-through' : undefined }}>
                    {labelOf(STATUS_LABEL, e.status)}
                  </span>
                </Descriptions.Item>
                <Descriptions.Item label="판정">
                  {labelOf(VERDICT_LABEL, e.verdict)}
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
                {/* ★ 대응 진행은 **판정과 다른 축이다** (D-399). 같은 칸에 두지 않는다. */}
                <Descriptions.Item label="대응 진행">
                  {labelOf(RESPONSE_STATE_LABEL, e.response_state)}
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

        {/* ── W2 진위 판정 · 대응 진행 (U1 #11 · U2 #3 · D-399/D-414) ─────────
            ★ 이 칸이 이 화면에만 있는 글자다 — 검수 촬영이 이것으로 단언한다. */}
        {e && (
          <Card size="small" title="진위 판정 · 대응 진행">
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
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
                <Text type="secondary">
                  현재 판정: {labelOf(VERDICT_LABEL, e.verdict)}
                </Text>
              </Space>

              <Space wrap>
                <Text strong>대응 진행</Text>
                <Text>{labelOf(RESPONSE_STATE_LABEL, e.response_state)}</Text>
                {(e.allowed_next ?? []).length === 0 ? (
                  <Text type="secondary">
                    → 여기서 갈 수 있는 다음 칸이 없습니다 (서버가 그렇게 답했습니다)
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
                        {backward ? '되돌리기 (사유 필수)' : `→ ${ADVANCE_LABEL[next] ?? next}`}
                      </Button>
                    );
                  })
                )}
              </Space>

              {/* ★ 없는 것은 없다고 적는다 (D-284 · D-290). 전이 **이력**은 감사에 있고
                  읽는 라우트가 아직 없다 — 빈 표를 그리면 「이력이 없다」로 읽힌다. */}
              <Text type="secondary">
                상태 이력: 전이 한 줄 한 줄은 감사(guardianx.dsm.response)에 남습니다.
                다만 그것을 읽는 라우트가 아직 없어 이 화면은 현재 칸과 갈 수 있는
                다음 칸만 보여 줍니다 — 지난 전이는 여기 없습니다.
              </Text>
              <Text type="secondary">
                전파 기록: 대외 전파(유관기관 통보)를 적는 쓰기 면은 아직 없습니다
                (kernels.k1_event.record_dispatch 선등재 · WRITE_NO_PROBE).
                아래 「발송 이력」은 F-10 알림 발송이지 대외 전파가 아닙니다.
              </Text>
            </Space>
          </Card>
        )}

        <Card size="small" title="발송 이력 (F-10)">
          {/* ★ F-10 은 「심각 등급 발생 후 30초 내 발송 기록」이다.
              위의 발생 시각과 아래의 발송 시각이 **한 화면에** 있어야 사람이 잰다. */}
          <StateBoundary
            state={deliveries.state}
            reason={deliveries.reason}
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
            message="계약 F-10 — 심각 등급은 발생 후 30초 안에 발송 기록이 남아야 합니다."
            description="위 발생 시각과 아래 발송 시각을 대조하십시오. 실패한 발송에는 시각이 찍히지 않습니다 — 그것이 30초를 거짓으로 통과하지 못하게 하는 규약입니다."
          />
        )}

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
