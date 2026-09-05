/**
 * 자동 분석 고지 — **읽는 자리에 있어야 고지다** (차선 L · 2026-09-05).
 *
 * ★ 왜 조각으로 두나: 이 문장이 닿아야 하는 자리가 둘이다 — 로그인 뒤 첫 화면과
 *   알림 본문. 화면 쪽 자리가 늘 때마다 문장을 복사하면 두 벌이 되고, 두 벌이 된
 *   고지는 한쪽만 고쳐진다. 그 순간 「우리가 뭐라고 고지했는가」에 답이 둘이 된다.
 *
 * ★ 문안은 제품 언어 사전에 조율자가 넣어 둔 그대로다. 여기서 고쳐 쓰지 않는다 —
 *   고지는 대외 문서이고, 사전에 없는 말을 대외 문서에 쓰지 않는다.
 *
 * ★ 서버 쪽 정본은 `common/ai_act_notice.py` 한 곳이다. 알림 본문은 거기서 읽는다.
 *   두 자리가 같은 문장인지는 시험이 잰다(파일 원문을 읽어 대조한다).
 */
import { Alert } from 'antd';

/** 사전의 말. **여기서 고치지 않는다.** */
export const AUTO_ANALYSIS_TITLE = '자동 분석 안내';
export const AUTO_ANALYSIS_BODY =
  '이 알림은 자동 분석 결과이며, 관제요원이 최종 확인합니다.';

interface Props {
  /** 화면 위쪽에 붙일 때 아래 여백을 준다. */
  spaced?: boolean;
}

export default function AutoAnalysisNotice({ spaced = true }: Props) {
  return (
    <Alert
      type="info"
      showIcon
      message={AUTO_ANALYSIS_TITLE}
      description={AUTO_ANALYSIS_BODY}
      style={spaced ? { marginBottom: 16 } : undefined}
    />
  );
}
