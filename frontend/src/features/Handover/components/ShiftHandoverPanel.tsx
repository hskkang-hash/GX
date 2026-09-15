/**
 * P-123 · UX-31 ② — **「인계 메모」를 눌렀는데 아무것도 없던 화면.** (턴 O · 차선 C2)
 *
 * 무엇을 쟀나 [실측 2026-09-10 · 턴 O]
 * -----------------------------------
 *   · 사이드바는 「인계 메모」라고 광고한다(U1·U2 의 다섯 줄 중 하나).
 *   · `GET /api/handover/handover/notice` → **200** · `total_items: 0` — 문은 살아 있다.
 *   · 그런데 `/handover` 본문은 **68바이트**였다. 빈 상태 글자도, 쓰는 단추도 없다.
 *   · 제품의 온보딩은 관제요원에게 교대 때 「말로」 인계하라고 적어 두었다
 *     (`features/dsm/pages/Onboarding.tsx`) — 화면이 그 자리를 비워 두었기 때문이다.
 *
 * 왜 68바이트였나 — **탭이 메뉴에서 온다**
 * ---------------------------------------
 * `HandoverPage` 의 탭은 `currentMenu?.tabs` 에서 온다. `currentMenu` 는 사이드바를
 * **눌러서** 들어왔을 때만 정해진다(`activeItem`/`activeSubItem`). 주소로 곧장 오거나
 * 그 역할에 탭 권한이 없으면 `availableTabKeys` 가 0이 되고, 그러면 페이지는
 * **탭도 본문도 없는 빈 상자**를 그린다. 빈 상자는 「인계가 없다」로 읽히지만
 * 실제로 일어난 일은 「이 화면이 자기가 무엇인지 모른다」다.
 *
 * 이 조각이 하는 일 셋
 * --------------------
 *   ① **빈 상태를 글자로 적는다.** 「없다」와 「못 불렀다」를 가른다(DA-03 §2-5).
 *   ② **「인계 메모 쓰기」** 단추를 준다 — 읽을 것이 없어도 **쓸 수는 있어야** 한다.
 *   ③ **교대 초안 한 줄**을 만든다: 미처리 N · 오늘 판정 N. 그 두 수는
 *      `GET /api/dsm/events/summary` 가 이미 내고 있다 — 사람이 세지 않아도 된다.
 *
 * ★★ **수를 지어내지 않는다.** 요약을 못 읽으면 초안에 0을 적지 않고 「못 읽었다」고
 *   적는다. 0은 「없었다」이고, 그 둘이 같아 보이면 인계받는 사람이 조용한 밤과
 *   고장난 화면을 구별하지 못한다(D-301).
 */
import { Alert, Button, Card, Empty, Space, Typography } from 'antd';
import { useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';

import { dsmEndpoint, dsmGet } from '@/features/dsm/api';
import { useDsmResource } from '@/features/dsm/hooks/useDsmResource';
import type { EventSummary } from '@/features/dsm/types';

const { Paragraph, Text } = Typography;

/** 초안이 세는 구간. 「오늘」이 아니라 **한 교대**다 — 교대는 24시간을 넘지 않는다. */
const SHIFT_HOURS = 24;

interface Props {
  /** 「인계 메모 쓰기」가 여는 자리. 라우트는 부르는 쪽이 안다. */
  composePath: string;
  /** 이 화면이 왜 비었는가 — 부르는 쪽만 아는 사실이라 글자로 받는다. */
  reasonLine?: string;
}

/** 두 자리 수를 한 줄로. **모르는 칸은 「—」다** — 0으로 채우지 않는다. */
function draftText(summary: EventSummary | null): string {
  const stamp = new Date().toLocaleString('ko-KR');
  if (!summary) {
    return [
      `[교대 인계 초안] ${stamp}`,
      '미처리: 못 읽었습니다 (숫자를 확인하고 손으로 적어 주십시오)',
      '오늘 판정: 못 읽었습니다',
      '',
      '넘기는 말:',
    ].join('\n');
  }
  const unhandled = summary.unhandled_capped
    ? `${summary.unhandled}건 이상`
    : `${summary.unhandled}건`;
  return [
    `[교대 인계 초안] ${stamp}`,
    `미처리: ${unhandled}`,
    `오늘 판정: ${summary.reviewed}건 (아직 안 본 것 ${summary.unreviewed}건)`,
    '',
    '넘기는 말:',
  ].join('\n');
}

export default function ShiftHandoverPanel({ composePath, reasonLine }: Props) {
  const navigate = useNavigate();

  const summary = useDsmResource<EventSummary>(
    () => dsmGet<EventSummary>(dsmEndpoint.eventsSummary, { hours: SHIFT_HOURS }),
    [],
  );

  const draft = useMemo(
    () => draftText(summary.state === 'data' ? (summary.data ?? null) : null),
    [summary.state, summary.data],
  );

  const compose = useCallback(() => navigate(composePath), [navigate, composePath]);

  return (
    <Space
      direction="vertical"
      size={16}
      style={{ width: '100%', padding: '8px 0' }}
    >
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={
          <Space direction="vertical" size={4}>
            <Text strong>아직 인계 메모가 없습니다.</Text>
            <Text type="secondary">
              {reasonLine ??
                '이 자리에 지난 교대가 남긴 말이 뜹니다. 지금은 남긴 말이 없습니다.'}
            </Text>
          </Space>
        }
      >
        <Button type="primary" onClick={compose}>
          인계 메모 쓰기
        </Button>
      </Empty>

      <Card size="small" title="교대 마무리 초안">
        {/*
          ★ 초안은 **제안**이다. 그대로 보내지 않는다 — 사람이 고쳐 쓰는 자리이고,
            그래서 편집 가능한 글상자가 아니라 **복사할 수 있는 글자**로 둔다.
        */}
        {summary.state === 'error' || summary.state === 'forbidden' ? (
          <Alert
            type="warning"
            showIcon
            message="미처리·판정 수를 읽지 못했습니다."
            description="초안의 숫자 자리는 비워 두었습니다. 화면에서 확인하고 손으로 적어 주십시오 — 못 읽은 것을 0으로 적지 않습니다."
            style={{ marginBottom: 12 }}
          />
        ) : null}
        <Paragraph
          copyable={{ text: draft, tooltips: ['초안 복사', '복사했습니다'] }}
          style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}
        >
          {draft}
        </Paragraph>
      </Card>
    </Space>
  );
}
