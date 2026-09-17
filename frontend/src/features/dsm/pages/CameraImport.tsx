/**
 * UX-18 **벌크 등록 · 주소 자동** — ★ dry-run 이 먼저다 (D-209).
 *
 * 이 화면의 순서가 곧 규약이다
 * ----------------------------
 *   ① CSV 를 붙인다 → ② **표를 본다**(무엇이 새로 생기고 무엇이 바뀌는지) →
 *   ③ 그 표를 본 사람이 다시 눌러야 쓴다.
 * 표를 건너뛰는 길이 이 화면에 없다 — 「적용」 버튼은 표가 없으면 그려지지 않는다.
 *
 * 왜: 한 건짜리 등록은 잘못 눌러도 한 건이 틀린다. 100행 일괄은 **한 번의 실수가
 * 100대의 이름·주소를 덮어쓰고**, 덮어쓴 뒤에는 원래 값이 어디에도 없다.
 *
 * 착수 전 실측이 지시서의 두 항목을 고쳤다 [2026-09-24] — 화면이 그것을 **말한다**
 * ------------------------------------------------------------------------------
 *   · **ONVIF 는 이 저장소에 없다** (`grep -ril onvif backend/` = 0건). 없는 프로토콜
 *     위에 탭을 만들지 않는다(P-15). CSV 한 갈래만 연다.
 *   · **좌표→도로명 역지오코딩은 「불가」로 판정돼 있다** (D-329 · `JUSO_REVERSE_SUPPORTED='no'`).
 *     게다가 `StreamMonitor` 에 위도·경도 칸이 **아예 없다** — 역지오코딩할 좌표가
 *     애초에 없다. 주소는 **CSV 의 `address` 칸**으로 들어온다(D-330 이 정한 길:
 *     *카메라는 고정 설치물이므로 설치할 때 주소를 안다*).
 *     CSV 에 좌표를 실으면 어댑터를 **정말 부르고** 그 답(`disabled`)을 표에 적는다 —
 *     「없는 척」과 「불러 봤더니 없다」는 다른 사실이다.
 */
import { Alert, Button, Card, Col, Input, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet, dsmPostQuery } from '../api';
import { userFacingError } from '../copy';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import type { AddressGap, ImportPlan, ImportRow } from '../types';

const { Text, Title, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '카메라 일괄 등록 — 표를 먼저 봅니다';

const SAMPLE = `name,code,ip_source,address,detail
정문카메라,GATE-01,rtsp://10.0.0.11/stream,경기도 안양시 만안구 안양로 123,정문
3층복도,F3-01,rtsp://10.0.0.12/stream,경기도 안양시 만안구 안양로 123,3층 복도`;

const ACTION_TAG: Record<string, { color: string; label: string }> = {
  create: { color: 'green', label: '새로 만듦' },
  update: { color: 'blue', label: '바뀜' },
  unchanged: { color: 'default', label: '변화 없음' },
  error: { color: 'red', label: '못 씀' },
};

export default function CameraImportPage() {
  const [csvText, setCsvText] = useState('');
  const [plan, setPlan] = useState<ImportPlan | null>(null);
  const [applied, setApplied] = useState<ImportPlan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  /**
   * ★ [UX-31′ · 턴 S] 마지막으로 보낸 것이 **표 보기(dry-run)였나 적용이었나.**
   * 실패 상자의 「다시 시도」가 그 둘을 헷갈리면 **표만 보려던 사람이 쓰기를 한다.**
   * 그래서 기억해 두고 그 요청만 그대로 다시 낸다.
   */
  const [lastDryRun, setLastDryRun] = useState<boolean | null>(null);

  const gap = useDsmResource<AddressGap>(() => dsmGet(dsmEndpoint.cameraAddressGap), []);

  const run = useCallback(
    async (dryRun: boolean) => {
      setBusy(true);
      setError('');
      setLastDryRun(dryRun);
      try {
        // ★ 질의로 보낸다. 본문으로 보내면 **422(인자 없음)** 다 —
        //   [실측 2026-09-05] 이 자리가 실제로 그렇게 죽어 있었고, 캡처는 제목만
        //   보므로 화면은 떠 있었다. 「떠 있다」와 「된다」는 다른 사실이다.
        const result = await dsmPostQuery<ImportPlan>(dsmEndpoint.cameraImport, {
          csv_text: csvText,
          dry_run: dryRun,
        });
        if (dryRun) {
          setPlan(result);
          setApplied(null);
        } else {
          setApplied(result);
          setPlan(result);
          gap.reload();
        }
      } catch (err) {
        setError(userFacingError('CameraImport', err, '요청이 실패했습니다.'));
      } finally {
        setBusy(false);
      }
    },
    [csvText, gap],
  );

  const columns = [
    { title: '행', dataIndex: 'line', width: 60 },
    { title: '이름', dataIndex: 'name' },
    {
      title: '판정',
      dataIndex: 'action',
      width: 110,
      render: (v: string) => {
        const t = ACTION_TAG[v] ?? { color: 'default', label: v };
        return <Tag color={t.color}>{t.label}</Tag>;
      },
    },
    {
      title: '무엇이 바뀌나',
      dataIndex: 'changes',
      render: (changes: ImportRow['changes']) => {
        const keys = Object.keys(changes ?? {});
        if (!keys.length) return <Text type="secondary">—</Text>;
        return (
          <Space direction="vertical" size={0}>
            {keys.map((k) => (
              <Text key={k} style={{ fontSize: 12 }}>
                <b>{k}</b>: {String(changes[k][0] ?? '(없음)')} → {String(changes[k][1] ?? '(없음)')}
              </Text>
            ))}
          </Space>
        );
      },
    },
    { title: '사유', dataIndex: 'reason' },
    {
      title: '주소 조회',
      dataIndex: 'address_lookup',
      width: 110,
      render: (v: string) =>
        v ? (
          <Tag color={v === 'resolved' ? 'green' : 'orange'} title="좌표를 준 행에 대해 FX-5 어댑터가 답한 상태">
            {v}
          </Tag>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
  ];

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Title level={4} style={{ margin: 0 }}>
          {HEADLINE}
        </Title>

        {/* 「주소 없는 카메라 N대」 배지 — **분모와 함께** 낸다 (D-301). */}
        <StateBoundary state={gap.state} reason={gap.reason} status={gap.status} onRetry={gap.reload}>
          {gap.data ? (
            <Card size="small">
              <Row gutter={24} align="middle">
                <Col>
                  <Statistic
                    title="주소 없는 카메라"
                    value={gap.data.without_address}
                    suffix={`/ ${gap.data.total}대`}
                    valueStyle={{
                      color: gap.data.without_address > 0 ? '#cf1322' : '#389e0d',
                    }}
                  />
                </Col>
                <Col flex="auto">
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    「{gap.data.without_address}대」만 보면 그것이 40 중 39인지 400 중 39인지
                    모릅니다 — 앞은 거의 전부이고 뒤는 10%입니다. 그래서 분모를 함께 냅니다.
                    {gap.data.measurable
                      ? ` 지금 채워진 비율 ${Math.round((gap.data.coverage ?? 0) * 100)}%.`
                      : ' 카메라가 한 대도 없어 비율은 잴 수 없습니다 — 0%가 아닙니다.'}
                    {gap.data.marked_but_blank > 0
                      ? ` ⚠ 「적었다고 표시됐는데 주소가 빈」 카메라 ${gap.data.marked_but_blank}대가 있습니다.`
                      : ''}
                  </Paragraph>
                </Col>
              </Row>
            </Card>
          ) : null}
        </StateBoundary>

        <Alert
          type="info"
          showIcon
          message="카메라는 CSV 파일로 한 번에 등록합니다."
          description={
            '카메라 주소는 CSV 의 「주소」 칸으로 들어옵니다. ' +
            '좌표만 있는 카메라는 주소를 자동으로 채울 수 없어 「주소 없음」으로 표시됩니다.'
          }
        />

        <Card
          title="① CSV 붙여넣기"
          extra={
            <Button size="small" onClick={() => setCsvText(SAMPLE)}>
              예시 채우기
            </Button>
          }
        >
          <Input.TextArea
            rows={8}
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={SAMPLE}
            style={{ fontFamily: 'monospace' }}
          />
          <Space style={{ marginTop: 12 }}>
            <Button type="primary" loading={busy} disabled={!csvText.trim()} onClick={() => run(true)}>
              ② 표 먼저 보기 (dry-run)
            </Button>
            {/* ★ 표가 없으면 적용 버튼이 **없다.** 순서가 규약이다. */}
            {plan && !plan.fatal && plan.will_write > 0 && !applied ? (
              <Button danger loading={busy} onClick={() => run(false)}>
                ③ 이 표대로 적용 ({plan.will_write}행)
              </Button>
            ) : null}
          </Space>
        </Card>

        {/* ★ [UX-31′] 네 문장 + **살아 있는 단추**. 표를 보려던 것인지 적용하려던 것인지
            기억한 그대로 다시 보낸다 — 단추가 하는 일이 바뀌지 않는다. */}
        {error ? (
          <FailureNotice
            title={
              lastDryRun === false
                ? '이 표를 적용하지 못했습니다.'
                : '표를 만들지 못했습니다.'
            }
            detail={error}
            busy={busy}
            onRetry={lastDryRun === null ? undefined : () => run(lastDryRun)}
          />
        ) : null}

        {plan ? (
          <Card
            title={
              applied
                ? `적용 완료 — 생성 ${applied.created ?? 0} · 수정 ${applied.updated ?? 0}`
                : `dry-run 표 — ${plan.total}행`
            }
          >
            {plan.fatal ? (
              <Alert
                type="error"
                showIcon
                message="한 행도 쓰지 않았습니다."
                description={`${plan.fatal} — 부분 성공을 만들지 않습니다. 100행 중 37행이 들어간 상태는 되돌릴 지점이 없습니다.`}
              />
            ) : (
              <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                <Row gutter={16}>
                  {Object.entries(plan.counts).map(([k, n]) => (
                    <Col key={k}>
                      <Statistic title={ACTION_TAG[k]?.label ?? k} value={n} />
                    </Col>
                  ))}
                </Row>
                <Table<ImportRow>
                  size="small"
                  rowKey="line"
                  dataSource={plan.rows}
                  columns={columns as never}
                  pagination={{ pageSize: 25, showSizeChanger: false }}
                />
                {/* ★ [UX-20] 내부 함수 이름(`bulk_register._plan`)을 백틱째로 화면에
                    적고 있었다 — 우리 서랍의 지도다(GX-COPY §1-3). 사용자에게 뜻이
                    있는 것은 「이 표가 곧 일어날 일이다」 하나다. */}
                <Text type="secondary">
                  이 표는 <b>실제로 저장될 내용 그대로</b>입니다. 표에 없던 일은
                  일어나지 않습니다.
                </Text>
              </Space>
            )}
          </Card>
        ) : null}
      </Space>
    </Main>
  );
}
