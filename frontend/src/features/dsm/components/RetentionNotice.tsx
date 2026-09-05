/**
 * 영상 보관 기간 고지 — **제품이 선언한 수를 화면이 그대로 읽는다** (차선 L · LAW-02a).
 *
 * ★ 이 조각은 수를 **가지고 있지 않다.** 서버가 선언한 값을 받아 그린다 —
 *   화면에 수를 적어 두면 설정이 바뀐 날 화면만 옛 수를 말하고, 그 화면은
 *   고지의 얼굴을 하고 거짓말을 한다.
 *
 * ★ 「자동으로 지워집니다」는 **주기가 걸려 있을 때만** 참이다. 서버가 그 사실을
 *   함께 주고(`enforced`), 거짓일 때 이 조각은 **그 문장을 그리지 않는다** —
 *   지우지 않으면서 지운다고 적는 것이 이 절에서 가장 나쁜 실패다.
 */
import { Descriptions, Skeleton, Typography } from 'antd';

import { dsmEndpoint, dsmGet } from '../api';
import { useDsmResource } from '../hooks/useDsmResource';

const { Text } = Typography;

/** 사전의 말. **여기서 고치지 않는다.** */
export const RETENTION_LABEL = '영상 보관 기간';
export const RETENTION_SWEEP_LINE = '보관 기간이 지난 영상은 자동으로 지워집니다';

interface RetentionPolicy {
  retention_days: number;
  enforced: boolean;
}

export default function RetentionNotice() {
  const policy = useDsmResource<RetentionPolicy>(
    () => dsmGet(dsmEndpoint.lawRetention),
    [],
  );

  if (policy.state === 'loading') return <Skeleton active paragraph={{ rows: 1 }} />;
  if (!policy.data) return null;

  return (
    <Descriptions size="small" column={1} bordered>
      <Descriptions.Item label={RETENTION_LABEL}>
        <Text strong>{policy.data.retention_days}일</Text>
        {policy.data.enforced ? (
          <div>
            <Text type="secondary">{RETENTION_SWEEP_LINE}</Text>
          </div>
        ) : null}
      </Descriptions.Item>
    </Descriptions>
  );
}
