/**
 * LAW-07 열람·삭제 청구 — **접수 → 마스킹본 조회 → 회신 기록** (차선 L · 2026-09-05).
 *
 * 이 화면의 불변 하나
 * -------------------
 *   ★ **원본은 이 화면을 통해 나가지 않는다.** 누르는 단추의 이름이 「마스킹본 보기」이고,
 *     그 아래 한 줄이 **누르기 전에** 「원본 영상은 제공되지 않습니다」라고 말한다.
 *     막는 곳은 화면이 아니라 서버다(서버가 경로를 아예 주지 않는다) — 화면은
 *     그 사실을 사람에게 **먼저** 말하는 자리다.
 *
 * 순서가 곧 규약이다
 * ------------------
 *   ① 접수한다 → **접수 번호**가 나온다(청구인에게 불러 줄 수 있는 번호)
 *   ② 그 번호로 마스킹본을 본다 → 몇 건이 있었는지가 분모와 함께 나온다
 *   ③ 회신을 기록한다 → 이력은 **덧붙기만 한다**
 *
 * ★ 쓰기는 질의로 보낸다 — 본문으로 보내면 422(인자 없음)다. 그 422 는 「값이 틀렸다」가
 *   아니라 「인자가 없다」이고, 둘을 헷갈리면 한나절이 간다. 조립은 `dsmPostQuery` 하나.
 */
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  List,
  Radio,
  Row,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Main } from 'rj-core';

import { ownDenialPaths } from '@/features/session/permissionDenied';

import { dsmEndpoint, dsmGet, dsmPostQuery } from '../api';
import { userFacingError } from '../copy';
import AutoAnalysisNotice from '../components/AutoAnalysisNotice';
import RetentionNotice from '../components/RetentionNotice';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';

const { Paragraph, Text, Title } = Typography;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '열람·삭제 청구';

/** 누르기 전에 읽는 한 줄. **단추 아래에 붙는다.** */
export const NO_ORIGINAL_LINE = '원본 영상은 제공되지 않습니다';

interface RequestRow {
  receipt_no: string;
  kind: string;
  status: string;
  subject_name: string;
  contact_masked: string;
  accepted_at: string | null;
}

interface RequestList {
  items: RequestRow[];
  total: number;
  unanswered: number;
  kinds: string[];
}

interface ReplyRow {
  audit_id: number;
  at: string | null;
  text: string;
  outcome: string;
}

interface RequestDetail {
  request: RequestRow;
  replies: ReplyRow[];
  original_video_released: boolean;
}

interface MaskedItem {
  event_id: number;
  occurred_at: string | null;
  camera: string;
  masked: boolean;
  image: string | null;
  why_not: string;
}

interface MaskedView {
  receipt_no: string;
  items: MaskedItem[];
  matched: number;
  shown: number;
  capped: boolean;
}

export default function PrivacyRequestsPage() {
  const [selected, setSelected] = useState<string>('');
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [masked, setMasked] = useState<MaskedView | null>(null);
  const [receipt, setReceipt] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [form] = Form.useForm();
  const [replyText, setReplyText] = useState('');
  /**
   * ★ [UX-31′ · 턴 S] **방금 실패한 그 일**을 들고 있는 자리.
   *
   * 이 화면에는 쓰는 문이 넷이고(조회 · 접수 · 마스킹본 · 회신) 실패 상자는 하나다.
   * 상자가 「다시 시도」를 그리려면 **어느 일이 실패했는지**를 알아야 한다 —
   * 모르면 그 단추는 아무 일도 안 하거나 엉뚱한 일을 하고, 둘 다 거짓말이다.
   * 실패한 자리에서 자기를 다시 부르는 함수를 여기 넣는다.
   */
  const retry = useRef<(() => void) | null>(null);

  /**
   * ★★ [P-185 · 턴 W · 차선 U24] **403 은 한 자리에서만 말한다 — 여기다.**
   *
   * 무엇이 있었나 [실측 2026-09-17 턴 U · 2026-09-19 턴 W · U4 로 이 화면]
   * ---------------------------------------------------------------------
   * 서버가 403 을 주면 이 화면에 **같은 사실이 두 장** 떴다:
   *   ① 아래 상태 칸 — 목록은 `StateBoundary`(네 문장 + 「다시 시도」),
   *      누른 일은 `FailureNotice`(네 문장 + **방금 실패한 그 일을 다시 부르는 단추**)
   *   ② 화면 맨 위 고정 띠 — `PermissionDeniedNotice`
   * ②는 **덮개**라 ①의 단추를 가린다. 두 장 중 값이 있는 쪽은 ①이다.
   *
   * **어느 쪽을 남겼나 — ①(상태 칸). 왜:**
   *   · **남는다.** 띠는 사람이 닫을 수 있고 화면을 옮기면 사라진다 — 나중에 보면
   *     증거가 아니다. 상태 칸은 그 자리에 계속 있고 검수 촬영에 찍힌다.
   *   · **누를 것이 있다.** 「다시 시도」가 ①에만 있고, 그 단추는 실제로 요청을
   *     한 번 더 낸다(`retry.current`). 덮개는 누를 것이 없다.
   *   · **막힌 자리에 붙어 있다.** 접수가 막혔는지 회신이 막혔는지가 칸의 위치로
   *     보인다. 맨 위 띠는 「이 화면 어딘가」까지만 말한다.
   *
   * ⚠ **숨기는 것이 아니다.** 403 은 상태 칸에 그대로 적히고 `deniedPaths()` 에도
   *   그대로 남는다. 여기서 정하는 것은 **누가 말하는가**뿐이다.
   * ⚠ 앞머리 하나로 다섯 문을 다 덮는다 — 상세·마스킹본·회신은 이 앞머리 밑에 있다.
   */
  useEffect(() => ownDenialPaths([dsmEndpoint.privacyRequests]), []);

  const list = useDsmResource<RequestList>(
    () => dsmGet(dsmEndpoint.privacyRequests),
    [],
    { isEmpty: (v) => (v?.items?.length ?? 0) === 0 },
  );

  const openDetail = useCallback(async (receiptNo: string) => {
    setSelected(receiptNo);
    setMasked(null);
    setError('');
    try {
      setDetail(await dsmGet<RequestDetail>(
        dsmEndpoint.privacyRequestDetail(receiptNo)));
    } catch (err) {
      setDetail(null);
      retry.current = () => {
        void openDetail(receiptNo);
      };
      setError(userFacingError('PrivacyRequests', err, '청구를 불러오지 못했습니다.'));
    }
  }, []);

  const submit = useCallback(async (values: any) => {
    setBusy(true);
    setError('');
    try {
      const created = await dsmPostQuery<{ receipt_no: string }>(
        dsmEndpoint.privacyRequests,
        {
          subject_name: values.subject_name ?? '',
          contact: values.contact ?? '',
          kind: values.kind ?? '열람',
          note: values.note ?? '',
        },
      );
      setReceipt(created.receipt_no);
      form.resetFields();
      list.reload();
      openDetail(created.receipt_no);
    } catch (err) {
      retry.current = () => {
        void submit(values);
      };
      setError(userFacingError('PrivacyRequests', err, '청구를 접수하지 못했습니다.'));
    } finally {
      setBusy(false);
    }
  }, [form, list, openDetail]);

  const loadMasked = useCallback(async () => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      setMasked(await dsmGet<MaskedView>(
        dsmEndpoint.privacyRequestMasked(selected)));
    } catch (err) {
      retry.current = () => {
        void loadMasked();
      };
      setError(userFacingError('PrivacyRequests', err, '마스킹본을 불러오지 못했습니다.'));
    } finally {
      setBusy(false);
    }
  }, [selected]);

  const sendReply = useCallback(async () => {
    if (!selected || !replyText.trim()) return;
    setBusy(true);
    setError('');
    try {
      await dsmPostQuery(dsmEndpoint.privacyRequestReply(selected), {
        text: replyText.trim(),
      });
      setReplyText('');
      await openDetail(selected);
      list.reload();
    } catch (err) {
      retry.current = () => {
        void sendReply();
      };
      setError(userFacingError('PrivacyRequests', err, '회신을 보내지 못했습니다.'));
    } finally {
      setBusy(false);
    }
  }, [list, openDetail, replyText, selected]);

  return (
    <Main>
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <AutoAnalysisNotice />

        <Title level={3} style={{ marginBottom: 0 }}>{HEADLINE}</Title>

        {/* 청구인이 가장 먼저 묻는 것 — 얼마나 보관하는가. 수는 서버가 선언한다. */}
        <RetentionNotice />

        {/* ★ [UX-31′] 네 문장 + **살아 있는 단추** — 방금 실패한 그 일을 다시 부른다. */}
        {error ? (
          <FailureNotice
            title="요청이 처리되지 않았습니다."
            detail={error}
            busy={busy}
            onRetry={retry.current ?? undefined}
          />
        ) : null}

        <Row gutter={16}>
          <Col xs={24} lg={10}>
            <Card title="청구 접수" size="small">
              <Form form={form} layout="vertical" onFinish={submit} disabled={busy}>
                <Form.Item
                  name="subject_name"
                  label="청구인"
                  rules={[{ required: true, message: '청구인을 적어 주십시오.' }]}
                >
                  <Input placeholder="청구인 이름" />
                </Form.Item>
                <Form.Item
                  name="contact"
                  label="연락처"
                  rules={[{ required: true, message: '회신할 연락처를 적어 주십시오.' }]}
                >
                  <Input placeholder="회신받을 연락처" />
                </Form.Item>
                <Form.Item name="kind" label="청구 종류" initialValue="열람">
                  <Radio.Group>
                    <Radio.Button value="열람">열람</Radio.Button>
                    <Radio.Button value="삭제">삭제</Radio.Button>
                  </Radio.Group>
                </Form.Item>
                <Form.Item name="note" label="청구 내용">
                  <Input.TextArea rows={3} placeholder="언제 · 어디를 찍은 영상인지" />
                </Form.Item>
                <Button type="primary" htmlType="submit" loading={busy}>
                  청구 접수
                </Button>
              </Form>

              {receipt ? (
                <Alert
                  style={{ marginTop: 12 }}
                  type="success"
                  showIcon
                  message="접수 번호"
                  description={<Text strong>{receipt}</Text>}
                />
              ) : null}
            </Card>
          </Col>

          <Col xs={24} lg={14}>
            <Card title="접수된 청구" size="small">
              <StateBoundary
                state={list.state}
                reason={list.reason} status={list.status}
                onRetry={list.reload}
                emptyText="접수된 청구가 없습니다. 청구가 들어오면 쌓이니 기다리시면 됩니다."
              >
                <Table<RequestRow>
                  size="small"
                  rowKey="receipt_no"
                  dataSource={list.data?.items ?? []}
                  pagination={false}
                  onRow={(row) => ({ onClick: () => openDetail(row.receipt_no) })}
                  columns={[
                    { title: '접수 번호', dataIndex: 'receipt_no' },
                    {
                      title: '청구 종류',
                      dataIndex: 'kind',
                      render: (v: string) => <Tag>{v}</Tag>,
                    },
                    { title: '청구인', dataIndex: 'subject_name' },
                    { title: '연락처', dataIndex: 'contact_masked' },
                    { title: '상태', dataIndex: 'status' },
                  ]}
                />
              </StateBoundary>
            </Card>
          </Col>
        </Row>

        {detail ? (
          <Card
            size="small"
            title={`${detail.request.receipt_no} · ${detail.request.subject_name}`}
          >
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <div>
                <Button onClick={loadMasked} loading={busy}>
                  마스킹본 보기
                </Button>
                {/* ★ 안 되는 일을 **누르기 전에** 적는다. */}
                <Paragraph type="secondary" style={{ marginTop: 6, marginBottom: 0 }}>
                  {NO_ORIGINAL_LINE}
                </Paragraph>
              </div>

              {masked ? (
                <Card size="small" type="inner" title={`찾은 영상 ${masked.matched}건 중 ${masked.shown}건`}>
                  {masked.items.length === 0 ? (
                    <Empty description="이 기간에 남아 있는 영상이 없습니다. 기간을 넓혀 보십시오." />
                  ) : (
                    <Row gutter={[12, 12]}>
                      {masked.items.map((item) => (
                        <Col key={item.event_id} xs={12} md={8} lg={6}>
                          {item.image ? (
                            <img
                              src={item.image}
                              alt="마스킹본"
                              style={{ width: '100%', borderRadius: 4 }}
                            />
                          ) : (
                            <Alert type="warning" showIcon message={item.why_not} />
                          )}
                          <Text type="secondary">
                            {item.camera}
                            {' · '}
                            {item.occurred_at ?? ''}
                          </Text>
                        </Col>
                      ))}
                    </Row>
                  )}
                </Card>
              ) : null}

              <Card size="small" type="inner" title="회신 기록">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Input.TextArea
                    rows={3}
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder="청구인에게 무엇이라고 답했는지 적습니다."
                  />
                  <Button onClick={sendReply} loading={busy} disabled={!replyText.trim()}>
                    회신 기록
                  </Button>
                  {detail.replies.length === 0 ? (
                    <Empty description="아직 회신하지 않았습니다." />
                  ) : (
                    <List
                      size="small"
                      dataSource={detail.replies}
                      renderItem={(row) => (
                        <List.Item>
                          <List.Item.Meta
                            title={row.at ?? ''}
                            description={row.text}
                          />
                        </List.Item>
                      )}
                    />
                  )}
                </Space>
              </Card>
            </Space>
          </Card>
        ) : null}
      </Space>
    </Main>
  );
}
