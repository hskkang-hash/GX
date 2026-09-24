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
import { Alert, Button, Empty, Skeleton, Space, Typography } from 'antd';
import { ReactNode, useEffect } from 'react';

import {
  NOT_FOUND_TITLE,
  emptySpeech,
  failureSpeech,
  isNotFound,
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
  /**
   * 404 상자의 제목 — **무엇이 없는지는 부르는 쪽만 안다.**
   *
   * 안 주면 「없는 항목입니다.」다. 사건 상세라면 `NOT_FOUND_TITLE_EVENT`
   * (「없는 사건입니다.」)를 준다. 여기서 짐작하지 않는다(P-123 · UX-31 ③).
   */
  notFoundTitle?: string;
  emptyText?: string;
  /**
   * 0건일 때의 **「그래서 지금 무엇을 하면 되나」** — 한 줄.
   *
   * ★ [P-185 ㉣ · 턴 W · 차선 U24] 안 주면 사전의 「새 자료가 생기면 이 자리에
   *   나타납니다.」다. 그 말이 맞는 자리가 대부분이지만 **아닌 자리가 있다** —
   *   보고서는 사람이 「만들기」를 눌러야 생기고, 재시작 요청은 사람이 적어야 생긴다.
   *   그런 자리에 「기다리면 나타난다」를 적으면 **화면이 거짓말을 한다.**
   * ⚠ 안 주면 **종전 그대로다.** 스물세 군데를 한 번에 바꾸지 않는다 —
   *   바꾸는 자리는 0건을 실제로 만들어 눈으로 본 자리뿐이다.
   */
  emptyNext?: string;
  /** 이 상자가 어느 화면의 어느 칸인가 — 콘솔 줄에 붙는다. */
  where?: string;
  children: ReactNode;
}

const { Text } = Typography;

/**
 * UX-31′ 의 ②와 ③ — **왜 그런가**와 **지금 무엇을 하면 되나**를 두 줄로.
 *
 * ★ 한 줄로 이어 붙이지 않는 이유: 사람은 두 번째 문장에서 「그래서 내가 뭘 하나」를
 *   찾는다. 한 덩어리면 그 문장이 사유에 묻힌다.
 */
function TwoLines({ why, next }: { why: string; next: string }) {
  return (
    <Space direction="vertical" size={2}>
      <span>{why}</span>
      <span>{next}</span>
    </Space>
  );
}

/**
 * UX-31′ 의 ④ — **누를 것.** 죽은 단추를 만들지 않는 규율이 이 조각 하나에 있다:
 *
 *   · 사전이 「이 갈래에는 단추가 없다」고 하면(없는 것 · 404) **안 그린다**
 *   · 부르는 쪽이 다시 부를 방법을 안 줬으면(`onRetry` 없음) **안 그린다**
 *   · 그린 단추는 누르면 **실제로 요청이 한 번 더 나간다** (`onRetry` 가 곧 재요청이다)
 *
 * ★ `<a onClick>` 이 아니라 `<Button>` 이다. 앵커는 href 가 없으면 키보드 초점을 안 받고
 *   Enter 로도 안 눌린다 — 관제실에는 마우스를 안 쓰는 자리가 있다.
 */
function Retry({ label, onRetry }: { label: string | null; onRetry?: () => void }) {
  if (!label || !onRetry) return null;
  return (
    <Button size="small" onClick={onRetry}>
      {label}
    </Button>
  );
}

export default function StateBoundary({
  state,
  reason,
  status,
  onRetry,
  notFoundTitle = NOT_FOUND_TITLE,
  emptyText = '표시할 항목이 없습니다. 조건을 넓히거나 잠시 뒤 다시 보십시오.',
  emptyNext,
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
    const said = failureSpeech(status ?? 403);
    return (
      <Alert
        type="warning"
        showIcon
        message={said.what}
        description={<TwoLines why={said.why} next={said.next} />}
        // ★ 권한 자리에도 **누를 것**을 준다. 다시 로그인한 뒤 이 화면에서 곧장
        //   다시 물어볼 수 있어야 하고, 이 단추는 실제로 요청을 한 번 더 낸다.
        action={<Retry label={said.retryLabel} onRetry={onRetry} />}
      />
    );
  }

  /*
   * ★★ [P-123 · UX-31 ③ · 턴 O] **404 는 오류 상자가 아니다.**
   *
   *   before: 「불러오지 못했습니다. 잠시 뒤 다시 시도해 주십시오.」 + 「다시 시도」
   *   after : 「없는 사건입니다.(부르는 쪽이 준 말) 주소를 확인해 주십시오. …」
   *
   *   빨강(`error`)이 아니라 안내(`info`)이고, **「다시 시도」를 그리지 않는다** —
   *   `onRetry` 를 받았어도 안 그린다. 없는 것을 다시 부르는 단추는 거짓말이다.
   *   `state` 는 여전히 `error` 다(부르는 쪽의 5상태 계약을 안 바꾼다). 갈리는 것은
   *   **그리는 그림**뿐이고, 그래서 이 갈래는 부르는 쪽 스물세 곳을 안 고치고 산다.
   */
  if (state === 'error' && isNotFound(status)) {
    const said = failureSpeech(status, notFoundTitle);
    return (
      <Alert
        type="info"
        showIcon
        message={said.what}
        description={<TwoLines why={said.why} next={said.next} />}
        // ★ `retryLabel` 이 `null` 인 유일한 갈래다 — 아래 `Retry` 가 **아무것도 안 그린다.**
        action={<Retry label={said.retryLabel} onRetry={onRetry} />}
      />
    );
  }

  if (state === 'error') {
    const said = failureSpeech(status);
    return (
      <Alert
        type="error"
        showIcon
        message={said.what}
        description={<TwoLines why={said.why} next={said.next} />}
        action={<Retry label={said.retryLabel} onRetry={onRetry} />}
      />
    );
  }

  if (state === 'empty') {
    // ★ 빈 것은 **오류가 아니다.** 「요청은 성공했고 0건」을 한 줄 더 적어 둔다 —
    //   그 한 줄이 없으면 빈 화면과 못 가져온 화면이 같아 보인다(DA-03 §2-5).
    const said = emptySpeech(emptyText);
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={2}>
            <Text>{said.what}</Text>
            <Text type="secondary">
              {said.why} {emptyNext ?? said.next}
            </Text>
          </Space>
        }
      />
    );
  }

  return <>{children}</>;
}
