/**
 * P-67 U5 시스템 설정 — **선언하지 않은 것을 빨갛게 말한다** (2026-09-06 · 차선 C).
 *
 * 세종 판정 P-67 원문:
 *   "보존 일수·백업 목적지·일정에 **코드 기본값 없음.** 미선언 테넌트 =
 *    「미선언」 상태로 화면(U5 시스템)에 빨강 배지 · 파기·백업 **돌지 않음**."
 *
 * 무엇이 문제였나 — **90일은 아무도 정한 적이 없는 수였다**
 * ---------------------------------------------------------
 * 코드에 적힌 수는 「기본값」이라 불렸지만 사실은 **정한 사람이 없는 수**였다.
 * 그 수를 안내판이 인쇄하면 그 안내판은 법적 효력을 가진 거짓말이 되고,
 * 그 수를 파기가 읽으면 우리가 남의 자료에 대해 내린 명령이 된다.
 * 그래서 기본값을 없앴고, 없앤 자리에 **이 화면**이 선다.
 *
 * ★ **세 상태를 절대 뭉치지 않는다** (D-290 · D-301 의 화면 판)
 * -----------------------------------------------------------
 *     선언됨       값과 **출처**를 함께 적는다 — 값만 보이면 누가 정했는지 못 되짚는다
 *     미선언       빨강. 그리고 **무슨 일이 안 일어나는지**를 같이 적는다
 *     신호 대기    우리가 **못 읽는** 것이다. 「아무도 안 정했다」가 아니다
 *
 *   셋을 두 칸으로 접으면 신호가 끊긴 날 화면이 「미선언」이라 적고, 관리자는
 *   이미 정해 둔 값을 다시 정하러 간다. 그 다음에도 화면은 여전히 빨갛다.
 *
 * ★ **읽기 전용이다.** 이 화면은 선언을 받지 않는다 — 받는 문이 아직 없다.
 *   있는 척하는 입력칸은 눌러도 아무 일도 안 일어나는 단추이고, 그것은
 *   「선언했다」는 착각을 만든다. 값을 넣는 자리가 생기는 날 그 자리를 여기 붙인다.
 */
import { Alert, Button, Card, Descriptions, Input, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useState } from 'react';

import {
  DsmApiError,
  dsmGet,
  dsmPostQuery,
  dsmSystemEndpoint,
  dsmU56AdminEndpoint,
  type DsmBackupReceipts,
  type DsmStorageDeclaration,
  type DsmSystemRequestRow,
  type DsmSystemRequests,
} from '../api';
import { userFacingError } from '../copy';
import FailureNotice from '../components/FailureNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';

const { Title, Text, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '보존·백업 설정 — 선언하지 않으면 돌지 않습니다';

/** 빨강 배지의 글자. 판정문의 낱말 그대로다 — 옮겨 적으며 바꾸지 않는다. */
export const UNDECLARED = '미선언';

/**
 * 서버가 아직 안 내주는 자리의 글자. **미선언과 다른 말이어야 한다.**
 *
 * ⚠ 안쪽 보고서에는 이 상태를 「백엔드 신호 대기」라 적지만, 화면에는 그 낱말을
 *   쓰지 않는다 — 「백엔드」는 우리가 우리 서랍을 부르는 이름이다(사전 §4).
 *   U5 는 서버를 아는 사람이므로 「서버」까지는 그의 말이고, 그 앞은 아니다.
 */
export const NO_SIGNAL = '서버 신호 대기';

/**
 * 회수증이 한 장도 없을 때의 글자. **「백업 0건」이라 적지 않는다** — 이 화면이
 * 아는 것은 「여기서 안 읽힌다」뿐이고, 둘은 다른 사실이다(D-301).
 */
export const NO_RECEIPT = '회수증 없음 — 여기서 읽히지 않습니다';

interface RetentionPolicy {
  retention_days: number | null;
  declared: boolean;
  source: string;
  enforced: boolean;
}

interface BackupDeclaration {
  /** 이 문이 실재하는가. 거짓이면 **못 읽은 것**이지 미선언이 아니다. */
  present: boolean;
  declared?: boolean;
  destination?: string | null;
  schedule?: string | null;
  retention_days?: number | null;
  restore_drill?: string | null;
  source?: string;
  /**
   * ★ [턴 W] **고칠 자리의 이름들.** 「미선언」 배지만 보여 주면 관리자는 어디를
   * 고쳐야 하는지 코드를 읽어야 한다 — 설정은 기본값이 아니라 선언이고,
   * 선언에는 **이름이 있다**.
   */
  env_names?: string[];
  schedule_enabled?: boolean;
  restore_drill_enabled?: boolean;
  reason?: string;
}

/** 선언되지 않은 칸. **빨강 하나로만 말하지 않는다** — 무엇이 안 도는지 함께 적는다. */
function Undeclared({ consequence }: { consequence: string }) {
  return (
    <Space
      direction="vertical"
      size={2}
    >
      <Tag color="red">{UNDECLARED}</Tag>
      <Text type="secondary">{consequence}</Text>
    </Space>
  );
}

/** 아직 서버가 안 내주는 칸. 회색이다 — **빨강으로 그리면 거짓말이 된다.** */
function NoSignal() {
  return (
    <Space
      direction="vertical"
      size={2}
    >
      <Tag>{NO_SIGNAL}</Tag>
      <Text type="secondary">
        이 값을 읽는 자리가 아직 없습니다. 선언되지 않았다는 뜻이 아닙니다.
      </Text>
    </Space>
  );
}

export default function SystemSettings() {
  const retention = useDsmResource<RetentionPolicy>(
    () => dsmGet<RetentionPolicy>(dsmSystemEndpoint.retention),
    [],
  );

  /**
   * ★ 404 를 **오류로 그리지 않는다.** 이 문은 아직 없고, 없는 것은 고장이 아니다.
   *   그 밖의 실패는 그대로 빨갛게 둔다 — 「없다」와 「못 가져왔다」를 뭉치면
   *   서버가 죽은 날에도 화면이 「아직 안 만들었습니다」라고 적는다.
   */
  const backup = useDsmResource<BackupDeclaration>(async () => {
    try {
      const body = await dsmGet<BackupDeclaration>(
        dsmSystemEndpoint.backupDeclaration,
      );
      return { ...body, present: true };
    } catch (err) {
      if (err instanceof DsmApiError && (err.status === 404 || err.status === 405)) {
        return { present: false };
      }
      throw err;
    }
  }, []);

  /* ══════════════════════════════════════════════════════════════════════
   * 턴 U · 차선 U56 — 저장 상한 · 백업 회수증 · 재시작 **요청**
   * ══════════════════════════════════════════════════════════════════════
   *
   * ★ 이 셋은 **처음부터 상태 칸으로** 짓는다 — 읽기는 `StateBoundary`, 쓰기 실패는
   *   `FailureNotice`(「다시 시도」가 그 요청을 그대로 다시 낸다). 토스트 하나로
   *   끝내면 사람이 눈을 뗀 사이에 사라지고, 사라진 뒤에는 무엇이 실패했는지 화면에
   *   아무 자국이 없다(UX-31′).
   */
  const storage = useDsmResource<DsmStorageDeclaration>(
    () => dsmGet<DsmStorageDeclaration>(dsmU56AdminEndpoint.storage),
    [],
  );
  const receipts = useDsmResource<DsmBackupReceipts>(
    () => dsmGet<DsmBackupReceipts>(dsmU56AdminEndpoint.backupReceipts),
    [],
  );
  /**
   * ★ [턴 W · 조율자 요청 2 · 문안은 차선 U24] **0건을 antd 기본에 맡기지 않는다.**
   *   `isEmpty` 를 안 주면 이 자원은 `empty` 상태로 가지 않고, 표가 제 기본 문구
   *   (「데이터 없음」)를 그린다 — 그 말은 **요청이 0건인 것**과 **표가 못 읽은 것**을
   *   같은 그림으로 만든다.
   * ★ 왜 「기다리면 나타납니다」가 아닌가 [실측 2026-09-19]: 이 표의 행을 만드는
   *   자리는 저장소 전체에서 **하나**다 — `api_u56.py` 의 `restart_request` 안
   *   `DsmSystemRequest.objects.create(...)`. 배치도 크론도 이 표에 행을 만들지
   *   않는다(F 의 `api_f_ops.py` 는 **있는 행을 고칠** 뿐이다).
   *   그러므로 **가만히 두면 영원히 0건**이다. 사전 기본 문구
   *   「새 자료가 생기면 이 자리에 나타납니다」는 이 자리에서 **거짓말**이 된다
   *   (차선 U24 가 「보고서 0건」에서 잡은 것과 같은 뿌리).
   */
  const requests = useDsmResource<DsmSystemRequests>(
    () => dsmGet<DsmSystemRequests>(dsmU56AdminEndpoint.systemRequests),
    [],
    { isEmpty: (v) => (v?.requests?.length ?? 0) === 0 },
  );

  const [restartReason, setRestartReason] = useState('');
  const [restartBusy, setRestartBusy] = useState(false);
  const [restartError, setRestartError] = useState('');
  /** 누른 뒤의 **상태 칸**. 서버가 준 문장 그대로다 — 화면이 다시 쓰지 않는다. */
  const [restartAck, setRestartAck] = useState('');

  const sendRestartRequest = useCallback(async () => {
    const reason = restartReason.trim();
    if (!reason) {
      setRestartError('사유가 비어 있습니다. 사유 없는 재시작 요청은 다음 사람에게 「왜 내렸는지 모르는 정지」입니다.');
      return;
    }
    setRestartBusy(true);
    setRestartError('');
    try {
      const body = await dsmPostQuery<{ message: string; executed: boolean }>(
        dsmU56AdminEndpoint.restartRequest,
        { reason },
      );
      setRestartAck(body.message);
      setRestartReason('');
      requests.reload();
    } catch (err) {
      setRestartError(
        userFacingError('SystemSettings.restart', err, '요청을 기록하지 못했습니다.'),
      );
    } finally {
      setRestartBusy(false);
    }
  }, [restartReason, requests]);

  const policy = retention.data;
  const videoDeclared = policy?.declared === true;
  const back = backup.data;
  const backupReadable = back?.present === true;

  return (
    <Space
      direction="vertical"
      size="large"
      style={{ width: '100%' }}
    >
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          보존 일수와 백업은 코드가 정하지 않습니다. 선언한 사람과 환경이 있어야
          돌아갑니다. 아래에 빨강 배지가 있으면 그 항목은 아직 아무도 정하지
          않았고, 그 상태에서는 파기도 백업도 실행되지 않습니다.
        </Paragraph>
      </div>

      <Card title="영상 보관 기간">
        <StateBoundary
          state={retention.state}
          reason={retention.reason} status={retention.status}
          onRetry={retention.reload}
        >
          <Descriptions
            column={1}
            bordered
            size="small"
          >
            <Descriptions.Item label="보관 기간">
              {videoDeclared ? (
                <Text strong>{policy?.retention_days}일</Text>
              ) : (
                <Undeclared consequence="보관 기간이 지난 영상 지우기가 실행되지 않습니다." />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="누가 정했나">
              {policy?.source || UNDECLARED}
            </Descriptions.Item>
            <Descriptions.Item label="자동으로 도는가">
              {policy?.enforced ? (
                <Tag color="green">매일 자동으로 지웁니다</Tag>
              ) : (
                <Tag color="red">돌지 않습니다</Tag>
              )}
            </Descriptions.Item>
          </Descriptions>
          {videoDeclared ? null : (
            <Alert
              style={{ marginTop: 12 }}
              type="error"
              showIcon
              message="보관 기간이 선언되지 않았습니다."
              description="선언하기 전에는 아무것도 지우지 않습니다. 지우는 쪽으로 틀리지 않기 위해서입니다."
            />
          )}
        </StateBoundary>
      </Card>

      <Card title="백업">
        <StateBoundary
          state={backup.state}
          reason={backup.reason} status={backup.status}
          onRetry={backup.reload}
        >
          <Descriptions
            column={1}
            bordered
            size="small"
          >
            <Descriptions.Item label="백업 목적지">
              {backupReadable ? (
                back?.destination || (
                  <Undeclared consequence="백업이 저장될 자리가 없어 백업이 실행되지 않습니다." />
                )
              ) : (
                <NoSignal />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="백업 일정">
              {backupReadable ? (
                back?.schedule || (
                  <Undeclared consequence="언제 뜰지 정해지지 않아 백업이 실행되지 않습니다." />
                )
              ) : (
                <NoSignal />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="백업 보관 기간">
              {backupReadable ? (
                back?.retention_days ? (
                  <Text strong>{back.retention_days}일</Text>
                ) : (
                  <Undeclared consequence="오래된 백업을 언제 지울지 정해지지 않았습니다." />
                )
              ) : (
                <NoSignal />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="복구 시험">
              {backupReadable ? (
                back?.restore_drill || (
                  <Undeclared consequence="복구되는지 확인한 적이 없습니다. 뜬 백업은 복구해 봐야 백업입니다." />
                )
              ) : (
                <NoSignal />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="누가 정했나">
              {backupReadable ? back?.source || UNDECLARED : NO_SIGNAL}
            </Descriptions.Item>
            {/*
              ★ [턴 W · WS-26 과 같은 원칙] **어디를 고치면 되는지 이름으로 적는다.**
              「미선언」만 보여 주면 관리자는 코드를 읽어야 한다 — 설정은 기본값이
              아니라 선언이고, 선언에는 이름이 있다. 이름은 서버가 준 것을 그대로
              쓴다(화면이 목록을 들고 있으면 서버가 이름을 바꾼 날 둘이 갈린다).
            */}
            <Descriptions.Item label="어디서 선언하나">
              {backupReadable && back?.env_names?.length
                ? <Text code>{back.env_names.join(' · ')}</Text>
                : NO_SIGNAL}
            </Descriptions.Item>
          </Descriptions>
          {backupReadable && back?.declared === false && back?.reason ? (
            <Alert
              style={{ marginTop: 12 }}
              type="error"
              showIcon
              message="백업 선언이 완전하지 않습니다."
              description={back.reason}
            />
          ) : null}
          {backupReadable ? null : (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="백업 선언을 읽는 자리가 아직 없습니다."
              description="이 칸이 회색인 동안에는 백업이 선언되었는지 이 화면이 답하지 못합니다. 빨강이 아닌 이유가 그것입니다."
            />
          )}
        </StateBoundary>
      </Card>

      {/* ── 턴 U ① 백업 회수증 — 뜬 것이 아니라 **남은 것**을 본다 ────────── */}
      <Card title="백업 회수증 — 마지막으로 남은 것">
        <StateBoundary
          state={receipts.state}
          reason={receipts.reason}
          status={receipts.status}
          onRetry={receipts.reload}
        >
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="마지막 회수증">
              {receipts.data?.last?.created_at || (
                <Tag>{NO_RECEIPT}</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="파일">
              {receipts.data?.last?.db_file || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="복구를 판정할 수 있는가">
              {receipts.data?.last ? (
                receipts.data.last.verifiable ? (
                  <Tag color="green">증인 표 행 수가 있습니다</Tag>
                ) : (
                  <Tag color="red">행 수가 없어 복구 성공을 판정할 수 없습니다</Tag>
                )
              ) : (
                <Tag>{NO_RECEIPT}</Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="다음 예정">
              {receipts.data?.next_run || '—'}
            </Descriptions.Item>
            <Descriptions.Item label="찾은 회수증">
              {receipts.data?.receipts_found ?? 0}장
            </Descriptions.Item>
          </Descriptions>
          {receipts.data && receipts.data.verdict !== 'OK' && (
            <Alert
              style={{ marginTop: 12 }}
              type="warning"
              showIcon
              message="회수증을 한 장도 못 찾았습니다."
              description={receipts.data.reason}
            />
          )}
        </StateBoundary>
      </Card>

      {/* ── 턴 U ② 저장 용량 — 상한이 없으면 % 를 지어내지 않는다 ────────── */}
      <Card title="저장 용량">
        <StateBoundary
          state={storage.state}
          reason={storage.reason}
          status={storage.status}
          onRetry={storage.reload}
        >
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="상한">
              {storage.data?.declared ? (
                <Space direction="vertical" size={2}>
                  <Text strong>{storage.data.capacity_gb} GB</Text>
                  {/*
                    ★★ [P-177 · 턴 V · 차선 U56] **분모를 화면이 선언한다.**
                    [실측] 상한은 `GX_STORAGE_CAPACITY_GB` 에 사람이 적은 **선언값**이고,
                    사용량은 객체저장 버킷 합계다 — 둘은 같은 그릇이 아니다. 그런데 화면은
                    그 둘로 나눈 `0.0%` 만 굵게 보여 줬다. 0.0% 는 「거의 안 찼다」로
                    읽히지만 실제로는 「다른 것을 나눴다」이다.
                    문장은 서버가 보낸 것을 그대로 쓴다 — 여기서 지어내지 않는다.
                  */}
                  {storage.data.capacity_note ? (
                    <Text type="secondary">{storage.data.capacity_note}</Text>
                  ) : null}
                </Space>
              ) : (
                <Undeclared consequence="상한이 없으면 「몇 % 찼나」에 답하지 않습니다. 분모를 코드가 지어내면 그 추측이 초록이 됩니다." />
              )}
            </Descriptions.Item>
            <Descriptions.Item label="쓰는 중">
              {storage.data?.used_gb === null || storage.data?.used_gb === undefined
                ? <Tag>{NO_SIGNAL}</Tag>
                : <Text strong>{storage.data.used_gb} GB</Text>}
            </Descriptions.Item>
            <Descriptions.Item label="사용률">
              {storage.data?.used_pct === null || storage.data?.used_pct === undefined ? (
                <Space direction="vertical" size={2}>
                  <Tag>판정 불가</Tag>
                  <Text type="secondary">{storage.data?.reason}</Text>
                </Space>
              ) : (
                <Space direction="vertical" size={2}>
                  <Text strong>{storage.data.used_pct}%</Text>
                  {/*
                    ★ 수 옆에 **무엇을 셌는지**를 같이 둔다. 종전에는 `used_note`
                    (「객체저장 버킷 합계」)가 **판정 불가일 때만** 떴다 — 즉 수가
                    나오는 순간 분모·분자의 정체가 화면에서 사라졌다.
                  */}
                  {storage.data.used_note ? (
                    <Text type="secondary">센 것: {storage.data.used_note}</Text>
                  ) : null}
                </Space>
              )}
            </Descriptions.Item>
            <Descriptions.Item label="어디서 선언하나">
              {/*
                ★★ [WS-26 · P-177 · 턴 W] **설정은 기본값이 아니라 선언이다.**
                종전에는 이름(`GX_STORAGE_CAPACITY_GB`)만 한 줄로 떴다 — 이름만으로는
                그 수가 **누가 적은 선언**인지 **코드가 지어낸 기본값**인지 갈리지
                않는다. `capacity_source` 가 그 한 칸을 메운다(서버가 준 문장 그대로).
                ⚠ 값은 이 턴에 **바꾸지 않았다** — 실측 50 그대로다(세종 이의 #2).
                200 은 문서 값이고, 분모는 손으로 적지 않는다.
              */}
              <Space direction="vertical" size={2}>
                <Text code>{storage.data?.env_name || '—'}</Text>
                {storage.data?.capacity_source ? (
                  <Text type="secondary">{storage.data.capacity_source}</Text>
                ) : null}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        </StateBoundary>
      </Card>

      {/* ── 턴 U ③ 재시작 **요청** — 이 단추는 서버를 내리지 않는다 ───────── */}
      <Card title="재시작 요청 — 기록만 남습니다">
        <Paragraph type="secondary">
          이 단추는 서버를 내리지 않습니다. 누가·언제·왜 재시작이 필요하다고 했는지를
          기록할 뿐이고, 실제 재시작은 점검 창에서 사람이 합니다. 「눌렀다」와
          「일어났다」를 한 칸에 두지 않기 위해서입니다.
        </Paragraph>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input.TextArea
            rows={2}
            value={restartReason}
            onChange={(e) => setRestartReason(e.target.value)}
            placeholder="왜 재시작이 필요한지 한 줄 (예: 앞단 기동 순서 확인 뒤 잔존 연결 정리)"
          />
          <Button
            type="primary"
            loading={restartBusy}
            disabled={restartReason.trim().length === 0}
            onClick={sendRestartRequest}
          >
            재시작을 요청합니다
          </Button>
          {restartAck && (
            <Alert type="success" showIcon message={restartAck} />
          )}
          {restartError && (
            <FailureNotice
              title="요청을 기록하지 못했습니다."
              detail={restartError}
              busy={restartBusy}
              onRetry={sendRestartRequest}
            />
          )}
        </Space>

        <StateBoundary
          state={requests.state}
          reason={requests.reason}
          status={requests.status}
          onRetry={requests.reload}
          emptyText="아직 올린 재시작 요청이 없습니다."
          emptyNext="위 칸에 사유를 적고 「재시작 요청」을 누르면 여기에 한 줄이 생깁니다. 사유 없는 요청은 다음 사람에게 「왜 내렸는지 모르는 정지」입니다."
        >
          <Table<DsmSystemRequestRow>
            style={{ marginTop: 16 }}
            size="small"
            rowKey={(r) => r.request_id}
            pagination={false}
            dataSource={requests.data?.requests ?? []}
            columns={[
              { title: '언제', dataIndex: 'created_at' },
              { title: '누가', dataIndex: 'requested_by' },
              { title: '사유', dataIndex: 'reason' },
              { title: '상태', dataIndex: 'status_label' },
            ]}
          />
          {/*
            ★ [턴 W · 차선 U56] **분모를 화면이 말한다.** 이 표는 서버가 `limit`(기본 20)
              으로 잘라 준 것을 `pagination={false}` 로 그린다 — 그래서 21건째부터는
              **화면에서 조용히 사라진다.** 수를 안 적으면 보는 사람은 그 20줄이 전부인
              줄 안다(「분모는 손으로 적지 않는다」의 짝: 분모를 **숨기지도** 않는다).
            ⚠ 0건 갈래는 여기까지 오지 않는다 — 위 `isEmpty` 가 빈 상태로 보낸다.
              그래서 이 줄은 **언제나 1 이상**을 말하고, 0 을 초록으로 적지 않는다.
          */}
          {requests.data && requests.data.total > (requests.data.requests?.length ?? 0) ? (
            <Text type="secondary">
              전체 {requests.data.total}건 중 최근 {requests.data.requests.length}건만
              보입니다.
            </Text>
          ) : null}
        </StateBoundary>
      </Card>
    </Space>
  );
}
