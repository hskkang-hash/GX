/**
 * UX-31′ — **쓰기가 거절된 자리의 네 문장과 살아 있는 단추** (2026-09-16 턴 S · 차선 F).
 *
 * 무엇이 이 조각을 만들었나 [실측 2026-09-16 · 소스 전수]
 * -------------------------------------------------------
 * `StateBoundary` 는 **읽기**가 실패한 자리를 한 곳에서 그린다. 그런데 **쓰기**가 거절된
 * 자리는 화면마다 손으로 짠 상자였고, 여섯 곳이 같은 모양이었다:
 *
 *     {error ? <Alert type="error" message="거절되었습니다." description={error} /> : null}
 *
 * 이 상자에는 **누를 것이 없다.** 사람이 할 수 있는 일은 같은 단추를 스스로 다시 찾아
 * 누르는 것뿐이고, 그 단추가 화면 밖으로 밀려 있으면(표 아래·접힌 카드) 아무것도 못 한다.
 * 「다시 시도」가 **없는 것**은 죽은 단추가 아니지만, 사람에게는 같은 막다른 길이다.
 *
 * 그래서 규약을 한 곳에 둔다 — 읽기는 `StateBoundary`, **쓰기는 여기.**
 *
 *   ① 무슨 일이 일어났나   `title`  — 무엇을 못 했는지는 **부르는 쪽만** 안다
 *   ② 왜 그런가            `detail` (서버가 쓴 한국어 사유) 또는 사전의 갈래별 한 줄
 *   ③ 지금 무엇을 하면 되나 사전이 갈래로 정한다
 *   ④ 누를 것              `onRetry` — **그 요청을 그대로 한 번 더 낸다**
 *
 * ★★ **죽은 단추를 만들지 않는다.** `onRetry` 를 안 주면 단추를 **안 그린다.**
 *   그리고 주는 쪽은 「방금 실패한 그 동작」을 그대로 다시 부르는 함수를 준다 —
 *   화면을 새로 고치는 함수가 아니다. 새로 고침은 사용자가 이미 아는 길이고,
 *   이 단추가 약속하는 것은 **그 일을 다시 한다**는 것이다.
 *
 * ★ 사유 원문은 여기서도 화면에 못 나온다. 부르는 쪽이 `userFacingError()` 를 지나 온
 *   문장만 `detail` 로 준다 — 그 함수가 서버의 한국어와 axios 의 영문을 가르는 칸이다.
 */
import { Alert, Button, Space } from 'antd';

import { failureSpeech } from '../copy';

interface Props {
  /** ① 무엇을 못 했나. 예: 「훈련 모드를 바꾸지 못했습니다.」 */
  title: string;
  /** ② 왜. `userFacingError()` 가 돌려준 한 줄. 없으면 사전의 갈래별 문장을 쓴다. */
  detail?: string;
  /** 갈래를 가르는 상태 코드. 없으면 「알 수 없음」 갈래로 말한다. */
  status?: number;
  /** ④ 누르면 **그 요청이 다시 나간다.** 없으면 단추를 그리지 않는다. */
  onRetry?: () => void;
  /** 다시 부르는 중. 두 번 눌리는 것을 막는다(요청 자리의 멱등 규약과 한 짝이다). */
  busy?: boolean;
  /** 단추의 말. 기본은 사전의 「다시 시도」다. */
  retryLabel?: string;
}

export default function FailureNotice({
  title,
  detail,
  status,
  onRetry,
  busy = false,
  retryLabel,
}: Props) {
  const said = failureSpeech(status, title);
  const label = retryLabel ?? said.retryLabel;
  return (
    <Alert
      type="error"
      showIcon
      message={said.what}
      description={
        <Space direction="vertical" size={2}>
          <span>{detail ?? said.why}</span>
          <span>{said.next}</span>
        </Space>
      }
      action={
        label && onRetry ? (
          <Button size="small" loading={busy} onClick={onRetry}>
            {label}
          </Button>
        ) : undefined
      }
    />
  );
}
