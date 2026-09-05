/**
 * UX-22 **처리 단계 한 줄** — 미처리 → 접수 → 조치 중 → 종결.
 *
 * 무엇이 문제였나 [실측 2026-09-25 · PRD v2.6]
 * -------------------------------------------
 * 목록에 「대응」 「상태」 「판정」 **세 열**이 나란히 섰고 상세에는 넷이 섰다.
 * 셋 다 「이 사건이 어디까지 왔나」처럼 읽히지만 서로 다른 것을 묻는다 —
 * 사람이 **어느 축을 보는지 모른다**(GX-COPY §1-4).
 *
 * 그래서 사용자 화면에는 축을 **둘만** 세운다:
 *   ① **처리 단계** — 사람이 어디까지 했나. 이 줄이 그것이다.
 *   ② **판정 배지** — 이 탐지가 진짜였나(실제 / 오탐). 아래 `VerdictBadge`.
 * 진위 축(`status`)은 관리자 자리로 물러난다 — 판정과 같은 것을 두 이름으로 부르던
 * 열이었고, 두 이름은 같은 건을 두 번 세게 만든다.
 *
 * ★ **이 줄은 그림이지 전이표가 아니다.** 다음에 갈 수 있는 칸은 서버가
 *   `allowed_next` 로 말한다. 여기서 「다음은 접수」라고 읽고 버튼을 그리면
 *   서버가 거절하는 버튼이 생긴다 (D-399).
 *
 * ★ 색을 쓰지 않는다. 색은 등급(ISA-101)이 이미 쓰고 있고, 한 화면에서 색이 두 축을
 *   뜻하면 진짜 빨강이 왔을 때 아무도 안 본다.
 */
import { Steps, Tag, Typography } from 'antd';

import {
  labelOf,
  RESPONSE_STATE_LABEL,
  RESPONSE_STEPS,
  responseStepIndex,
  VERDICT_LABEL,
} from '../severity';

const { Text } = Typography;

interface Props {
  /** 서버가 준 `response_state`. 모르는 값이면 줄을 그리지 않고 그 사실을 적는다. */
  state?: string | null;
  size?: 'default' | 'small';
}

export default function ResponseSteps({ state, size = 'small' }: Props) {
  const current = responseStepIndex(state);

  //: 모르는 값을 네 칸 중 하나로 **끼워 맞추지 않는다.** 끼워 맞추면 서버가 늘린
  //: 새 단계가 화면에서 「미처리」로 보이고, 그 거짓은 조용하다 (D-286).
  if (current < 0) {
    return (
      <Text type="secondary">
        처리 단계를 아직 알 수 없습니다.
      </Text>
    );
  }

  return (
    <Steps
      size={size}
      current={current}
      responsive={false}
      items={RESPONSE_STEPS.map((key) => ({
        title: RESPONSE_STATE_LABEL[key],
      }))}
    />
  );
}

/**
 * **판정 배지** — 실제 / 오탐. 처리 단계와 **다른 것을 묻는다**(D-293):
 * 종결된 뒤에도 「그 탐지가 오탐이었다」는 남는다.
 *
 * ★ 아직 판정이 없으면 「미판정」이라고 적는다. 빈칸으로 두면 「판정할 것이 없다」로
 *   읽히고, 오탐률의 분모가 왜 안 차는지 아무도 모르게 된다.
 * ★ 빨강을 쓰지 않는다 — 빨강은 `critical` 등급 전용이다(ISA-101).
 */
export function VerdictBadge({ verdict }: { verdict?: string | null }) {
  if (!verdict) return <Tag>미판정</Tag>;
  return <Tag color={verdict === 'rejected' ? 'default' : 'blue'}>{labelOf(VERDICT_LABEL, verdict)}</Tag>;
}
