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
import { Alert, Card, Descriptions, Space, Tag, Typography } from 'antd';

import { DsmApiError, dsmGet, dsmSystemEndpoint } from '../api';
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
          reason={retention.reason}
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
          reason={backup.reason}
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
          </Descriptions>
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
    </Space>
  );
}
