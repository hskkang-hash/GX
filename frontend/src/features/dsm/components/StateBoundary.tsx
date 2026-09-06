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
 *
 * ★★ [P-78 · 2026-09-06 턴 H] **사유를 그리지 않는다.**
 *   ------------------------------------------------------------------
 *   종전 이 파일은 `description={reason}` 이었다. `reason` 은 부르는 쪽이
 *   `err.message` 에서 뽑아 넘긴 값이고, 응답이 없으면 그 자리에 axios 가 만든
 *   문장이 들어온다. [실측 · 직전 턴] 여섯 화면에서 사용자 자리에 이렇게 떴다:
 *
 *       Network Error
 *       Request failed with status code 500
 *
 *   사전(GX-COPY §2)이 **이름으로** 금지한 줄이고, 소스 게이트로는 영영 안 잡힌다 —
 *   그 글자는 우리 소스에 없다. 런타임에 들어온다.
 *
 *   그래서 이 파일이 **통로를 끊는다**: 사유는 인자로 계속 받되 **그리지 않고**
 *   콘솔로 보낸다. 화면에는 사전의 말과 「다시 시도」만 나간다.
 *   부르는 쪽 스물세 곳을 하나씩 고치는 길도 있었지만, 그 길은 **다음에 생길
 *   스물네 번째 자리를 못 막는다.** 좁은 문 하나가 넓은 규율보다 낫다.
 */
import { Alert, Empty, Skeleton } from 'antd';
import { ReactNode, useEffect } from 'react';

import {
  FAILURE_TITLE,
  FORBIDDEN_TITLE,
  failureHint,
  reportFailure,
} from '../copy';
import type { WidgetState } from '../types';

interface Props {
  state: WidgetState;
  /**
   * 왜 이 상태인가 — **관리자·개발자 자리의 값이다.**
   *
   * ⚠ 이 값은 **화면에 그려지지 않는다.** 콘솔로 간다. 서버 원문·상대사명·
   *   내부 사유가 이 자리로 들어오는 것을 막을 방법이 없기 때문이다(P-27).
   */
  reason?: string;
  /** 상태 코드가 있으면 사전 문구가 갈린다(연결 없음 · 늦음 · 서버 오류). */
  status?: number;
  /** 오류에서만 쓴다. 없으면 재시도 단추를 그리지 않는다(누를 것이 없는 단추는 거짓말). */
  onRetry?: () => void;
  emptyText?: string;
  /** 이 상자가 어느 화면의 어느 칸인가 — 콘솔 줄에 붙는다. */
  where?: string;
  children: ReactNode;
}

export default function StateBoundary({
  state,
  reason,
  status,
  onRetry,
  emptyText = '표시할 항목이 없습니다.',
  where = 'StateBoundary',
  children,
}: Props) {
  // 원문은 **여기서 끝난다.** 화면으로 안 가고 콘솔로 간다.
  useEffect(() => {
    if ((state === 'error' || state === 'forbidden') && reason) {
      reportFailure(where, reason, status);
    }
  }, [state, reason, status, where]);

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
        message={FORBIDDEN_TITLE}
        description={failureHint(403)}
      />
    );
  }

  if (state === 'error') {
    return (
      <Alert
        type="error"
        showIcon
        message={FAILURE_TITLE}
        description={failureHint(status)}
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
