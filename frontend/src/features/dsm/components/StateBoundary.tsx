/**
 * F-09 의 **5상태를 한 곳에서** 그린다 (DA-04 §2 K3 · DA-03 §2-5).
 *
 * ★ 위젯마다 5상태를 손으로 짜지 않는다. 손으로 짜면 「5상태 100%」라는 수가
 *   위젯 수만큼 늘어나고, 그 수는 언제나 100% 가 나온다 — 부착률을 완결로 착각한
 *   착시 ①(D-249)의 화면 판이다. **프레임이 상태를 주입하고, 여기가 그린다.**
 *
 * ★ 「빈」과 「오류」를 같은 그림으로 그리지 않는다 (DA-03 §2-5 규칙 1):
 *     빈   = 요청은 성공했고 데이터가 0건이다 → **기다릴 것이 없다**
 *     오류 = 가져오지 못했다                  → **다시 시도할 것이 있다**
 *   둘이 같아 보이면 사용자가 「없구나」로 읽고, 실제로는 못 가져온 것이다.
 */
import { Alert, Empty, Skeleton } from 'antd';
import { ReactNode } from 'react';

import type { WidgetState } from '../types';

interface Props {
  state: WidgetState;
  /** 왜 이 상태인가. 오류·권한없음에서 **반드시** 보인다 — 원인 없는 빨강은 못 고친다. */
  reason?: string;
  /** 오류에서만 쓴다. 없으면 재시도 단추를 그리지 않는다(누를 것이 없는 단추는 거짓말). */
  onRetry?: () => void;
  emptyText?: string;
  children: ReactNode;
}

export default function StateBoundary({
  state,
  reason,
  onRetry,
  emptyText = '표시할 항목이 없습니다.',
  children,
}: Props) {
  if (state === 'loading') {
    // 부분 갱신 규약(DA-03 §4-5): 갱신 때 스켈레톤을 다시 그리지 않는다 —
    // 그것은 부르는 쪽이 `loading` 을 언제 켜는가로 지킨다.
    return <Skeleton active paragraph={{ rows: 3 }} />;
  }

  if (state === 'forbidden') {
    return (
      <Alert
        type="warning"
        showIcon
        message="이 항목에 대한 권한이 없습니다."
        description={reason}
      />
    );
  }

  if (state === 'error') {
    return (
      <Alert
        type="error"
        showIcon
        message="불러오지 못했습니다."
        description={reason}
        action={
          onRetry ? (
            <a onClick={onRetry} role="button">
              다시 시도
            </a>
          ) : undefined
        }
      />
    );
  }

  if (state === 'empty') {
    return <Empty description={emptyText} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return <>{children}</>;
}
