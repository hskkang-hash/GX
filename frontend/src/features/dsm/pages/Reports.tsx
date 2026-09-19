/**
 * 화면 — **보고서** (차선 U24 · 턴 U · P-173 U24 ①⑤).
 *
 * 무엇을 하나
 * -----------
 *   서식 셋을 카드 셋으로 두고, 「만들기」를 누르면 서버가 **실행 기록 한 행**을 남긴다
 *   (`POST /api/dsm/reports/runs`). 그 행에서 **DOCX 정본**(결정 ⑤ · HWP 가 연다)과
 *   PDF 병행본을 내려받는다. 파일은 누를 때마다 서버가 **다시 그린다** — 저장된 파일이
 *   없다는 것이 요점이다: 「특이사항」을 고치면 다음 내려받기가 그것을 담는다.
 *
 * 실패는 **상태 칸**이다 — 토스트가 아니다 (P-173 · 조율자 지시 · 새 토스트 0)
 * ------------------------------------------------------------------------
 *   만들기·내려받기가 거절되면 `FailureNotice` 가 ① 무엇을 못 했나 ② 왜 ③ 무엇을 하면
 *   되나 ④ **그 요청을 그대로 다시 내는 단추**를 그린다. 토스트는 3초 뒤 사라지고,
 *   사라진 문장은 「안 눌렸다」와 구별되지 않는다.
 *
 * 자동본은 이 화면이 만들지 않는다
 * --------------------------------
 *   「이번 달 우리 센터」의 **자동본**(`trigger=auto`)은 매월 1일 배치가 만든다
 *   (`apps/dsm/monthly_report.run_monthly_all`). 이 화면의 「만들기」는 언제나
 *   `trigger=manual` 이고, 실행 목록의 「자동/사람」 칸이 그 둘을 가른다 —
 *   사람이 누른 것을 자동이라고 적으면 PRD §7.4 의 수가 거짓이 된다.
 *
 * ⚠ 읽기 전용 계정(U4 담당관)의 「만들기」는 **403** 이다(플랫폼 문지기 `read_only_role`).
 *   그것이 옳다 — 그 사람의 자리는 **내려받기**이고, 자동본은 배치가 만들어 둔다.
 *   403 은 상태 칸에 그대로 적힌다(숨기지 않는다 · 단추를 지우지도 않는다).
 */
import { Button, Card, Col, Input, Row, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { ownDenialPaths } from '@/features/session/permissionDenied';

import {
  createReportRun,
  downloadReportFile,
  listReportRuns,
  type ReportKind,
  type ReportRunPage,
  type ReportRunRow,
} from '../api';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { userFacingError } from '../copy';
import { useDsmResource } from '../hooks/useDsmResource';
import { absolute, stamp } from '../time';

const { Title, Text, Paragraph } = Typography;

/**
 * 카드 셋 — **서버의 서식 이름과 같은 글자**(`monthly_report.KIND_LABEL`).
 * 화면이 자기 이름을 지으면 사람이 「그 보고서」라고 부를 수 없다.
 */
const FORMS: { kind: ReportKind; label: string; what: string; needsEvent: boolean }[] = [
  {
    kind: 'incident',
    label: '사건 보고서',
    what: '사건 한 건을 1쪽으로 — 개요 · 대응 시계 네 시각 · 판정 · 조치 이력.',
    needsEvent: true,
  },
  {
    kind: 'monthly',
    label: '이번 달 우리 센터',
    what: '이번 달 1일부터 지금까지 — 등급별 · 유형별 · 카메라별 · 시간대별 · 대응 진행.',
    needsEvent: false,
  },
  {
    kind: 'upper',
    label: '상급기관 제출용',
    what: '상급 보고로 체크한 사건만 모아 — 제출 요약과 사건 목록.',
    needsEvent: false,
  },
];

export default function Reports() {
  /** 사건 보고서가 물어보는 한 칸. 비어 있으면 그 카드의 단추는 눌리지 않는다. */
  const [eventId, setEventId] = useState<string>('');
  /** 「특이사항」 — 자동본을 사람이 고치는 칸(부속서 A U2#7). 종이의 마지막 절이 된다. */
  const [note, setNote] = useState<string>('');
  const [busyKind, setBusyKind] = useState<ReportKind | null>(null);
  const [makeError, setMakeError] = useState<{ text: string; status: number } | null>(null);
  const [lastRun, setLastRun] = useState<ReportRunRow | null>(null);

  const [busyFile, setBusyFile] = useState<string | null>(null);
  const [fileError, setFileError] = useState<{ text: string; status: number } | null>(null);
  const [lastFile, setLastFile] = useState<string>('');
  /**
   * 마지막으로 **시도한** 파일. 「다시 시도」가 약속하는 것은 「그 일을 다시 한다」이므로
   * (FailureNotice 머리말 ④), 진행 중 표시(`busyFile`)가 아니라 시도 자체를 기억한다 —
   * `busyFile` 은 실패한 순간 이미 비어 있다.
   */
  const [lastTry, setLastTry] = useState<{ runId: number; fmt: 'docx' | 'pdf' } | null>(null);

  const runs = useDsmResource<ReportRunPage>(
    () => listReportRuns({ limit: 50 }),
    [],
    { isEmpty: (v) => (v?.runs?.length ?? 0) === 0 },
  );

  const make = useCallback(
    async (kind: ReportKind) => {
      setBusyKind(kind);
      setMakeError(null);
      try {
        const row = await createReportRun({
          kind,
          event_id: kind === 'incident' ? Number(eventId) : null,
          note: note.trim(),
        });
        setLastRun(row);
        runs.reload();
      } catch (err) {
        setMakeError({
          text: userFacingError('Reports.make', err, '보고서를 만들지 못했습니다.'),
          status: (err as { status?: number })?.status ?? 0,
        });
      } finally {
        setBusyKind(null);
      }
    },
    [eventId, note, runs],
  );

  const download = useCallback(async (runId: number, fmt: 'docx' | 'pdf') => {
    const key = `${runId}:${fmt}`;
    setBusyFile(key);
    setLastTry({ runId, fmt });
    setFileError(null);
    try {
      const { bytes } = await downloadReportFile(runId, fmt);
      // 받은 바이트 수를 **상태 칸에 남긴다** — 0바이트는 성공이 아니고, 사라지는
      // 토스트는 「받았다」를 증명하지 못한다.
      setLastFile(`실행 ${runId} · ${fmt.toUpperCase()} · ${bytes.toLocaleString()}바이트`);
    } catch (err) {
      setFileError({
        text: userFacingError('Reports.download', err, '파일을 받지 못했습니다.'),
        status: (err as { status?: number })?.status ?? 0,
      });
    } finally {
      setBusyFile(null);
    }
  }, []);

  /**
   * ★★ [턴 V] **이 문들의 403 은 이 화면이 적는다** — 위에서 내려오는 띠가 아니라.
   *
   * [실측 2026-09-17 턴 U · V · U4 로 「만들기」] 서버가 403 을 주면 두 가지가
   * 동시에 떴다: 아래 상태 칸(네 문장 + 「다시 시도」)과 화면 맨 위 고정 띠.
   * 띠는 덮개라 상태 칸의 **단추를 가린다.** 같은 사실을 두 번 말하면서 값 있는
   * 쪽을 덮는 것이다. 그래서 이 화면이 임자를 선언한다.
   *
   * ⚠ **숨기는 것이 아니다.** 403 은 아래 상태 칸에 그대로 적히고 단추도 그대로다.
   *   여기서 정하는 것은 **누가 말하는가**뿐이다.
   */
  useEffect(() => ownDenialPaths(['/api/dsm/reports/']), []);

  const rows = runs.data?.runs ?? [];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Title level={4} style={{ margin: 0 }}>
        보고서
      </Title>

      {/* ── 서식 3 카드 ──────────────────────────────────────────────────── */}
      <Row gutter={[12, 12]}>
        {FORMS.map((f) => (
          <Col key={f.kind} xs={24} md={8}>
            <Card size="small" title={f.label} style={{ height: '100%' }}>
              <Paragraph type="secondary" style={{ fontSize: 12 }}>
                {f.what}
              </Paragraph>
              {f.needsEvent && (
                <Input
                  style={{ marginBottom: 8 }}
                  placeholder="사건번호"
                  value={eventId}
                  onChange={(e) => setEventId(e.target.value.replace(/[^0-9]/g, ''))}
                  allowClear
                />
              )}
              <Button
                type="primary"
                loading={busyKind === f.kind}
                disabled={f.needsEvent && !eventId}
                onClick={() => make(f.kind)}
              >
                만들기
              </Button>
            </Card>
          </Col>
        ))}
      </Row>

      <Card size="small" title="특이사항 (자동본에 사람이 더하는 한 줄)">
        <Input.TextArea
          rows={2}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="이 달에 남길 말이 있으면 적으십시오. 비워도 종이의 칸은 남습니다."
        />
      </Card>

      {/* ── 만들기 실패 — 상태 칸(토스트 아님) ───────────────────────────── */}
      {makeError && (
        <FailureNotice
          title="보고서를 만들지 못했습니다."
          detail={makeError.text}
          status={makeError.status}
          busy={busyKind !== null}
          onRetry={() => (lastRun ? make(lastRun.kind) : make('monthly'))}
        />
      )}
      {lastRun && !makeError && (
        <Card size="small">
          <Space wrap>
            <Tag color="green">만들었습니다</Tag>
            <Text>
              {lastRun.kind_label} · 실행 {lastRun.run_id} · {lastRun.trigger_label}
            </Text>
            <Button size="small" loading={busyFile === `${lastRun.run_id}:docx`}
                    onClick={() => download(lastRun.run_id, 'docx')}>
              DOCX 내려받기
            </Button>
            <Button size="small" loading={busyFile === `${lastRun.run_id}:pdf`}
                    onClick={() => download(lastRun.run_id, 'pdf')}>
              PDF 내려받기
            </Button>
          </Space>
        </Card>
      )}

      {/* ── 파일 상태 칸 — 받은 바이트 · 실패 사유 ────────────────────────── */}
      {fileError && (
        <FailureNotice
          title="파일을 받지 못했습니다."
          detail={fileError.text}
          status={fileError.status}
          busy={busyFile !== null}
          onRetry={lastTry ? () => void download(lastTry.runId, lastTry.fmt) : undefined}
        />
      )}
      {lastFile && !fileError && (
        <Card size="small">
          <Space wrap>
            <Tag color="green">내려받았습니다</Tag>
            <Text type="secondary">{lastFile}</Text>
          </Space>
        </Card>
      )}

      {/* ── 실행 목록 ────────────────────────────────────────────────────── */}
      <Card size="small" title="실행 기록" extra={<Button onClick={runs.reload}>새로고침</Button>}>
        <StateBoundary
          state={runs.state}
          reason={runs.reason}
          status={runs.status}
          onRetry={runs.reload}
          where="Reports/실행 목록"
          emptyText="아직 만든 보고서가 없습니다. (요청은 성공했고 0건입니다)"
        >
          <Table<ReportRunRow>
            size="small"
            rowKey="run_id"
            dataSource={rows}
            pagination={false}
            columns={[
              { title: '서식', dataIndex: 'kind_label', width: 150 },
              {
                title: '만든 쪽',
                dataIndex: 'trigger_label',
                width: 90,
                // 「자동」과 「사람」을 다른 색으로 — PRD §7.4 가 묻는 그 수다.
                render: (v: string, r) => (
                  <Tag color={r.trigger === 'auto' ? 'blue' : 'default'}>{v}</Tag>
                ),
              },
              {
                title: '결과',
                dataIndex: 'status_label',
                width: 100,
                render: (v: string, r) =>
                  r.status === 'succeeded' ? (
                    <Tag color="green">{v}</Tag>
                  ) : (
                    <Tag color="red">{v}</Tag>
                  ),
              },
              {
                title: '시각',
                dataIndex: 'created_at',
                width: 170,
                render: (v: string | null) =>
                  v ? <span title={absolute(v)}>{stamp(v)}</span> : '—',
              },
              {
                title: '집계 구간 / 사건',
                render: (_: unknown, r) =>
                  r.kind === 'incident'
                    ? `사건 ${r.event_id ?? '—'}`
                    : r.period_start && r.period_end
                      ? `${stamp(r.period_start)} ~ ${stamp(r.period_end)}`
                      : '—',
              },
              {
                title: '파일',
                width: 200,
                render: (_: unknown, r) =>
                  r.status === 'succeeded' ? (
                    <Space size="small">
                      <Button size="small" loading={busyFile === `${r.run_id}:docx`}
                              onClick={() => download(r.run_id, 'docx')}>
                        DOCX
                      </Button>
                      <Button size="small" loading={busyFile === `${r.run_id}:pdf`}
                              onClick={() => download(r.run_id, 'pdf')}>
                        PDF
                      </Button>
                    </Space>
                  ) : (
                    // 실패한 실행은 파일을 못 낸다 — 죽은 단추를 그리지 않고 사유를 적는다.
                    <Text type="danger" style={{ fontSize: 12 }}>
                      {r.failure_reason || '사유 미기재'}
                    </Text>
                  ),
              },
            ]}
          />
        </StateBoundary>
      </Card>

      <Text type="secondary" style={{ fontSize: 12 }}>
        정본은 DOCX 입니다(한글에서 열립니다). PDF 는 같은 글자를 찍은 병행본입니다.
        파일은 누를 때마다 서버가 이 실행 기록에서 다시 만듭니다 — 「특이사항」을 고치면
        다음 내려받기부터 반영됩니다.
      </Text>
    </Space>
  );
}
