/**
 * UX-14 **대응 시계** — 관제요원은 숫자를 읽지 않는다. **크기를 본다.**
 *
 * 이 컴포넌트가 하는 일 하나: 경과 시간이 문턱(30초 · 2분 · 5분 · 8분)을 넘을 때마다
 * **글자를 한 단계 키운다.** 야간 관제실에서 40인치 화면을 3m 밖에서 보는 사람에게
 * 「07:41」과 「12:03」은 같은 그림이고, 그래서 지금 화면은 「가장 오래 방치된 사건」을
 * 아무에게도 말하지 못한다.
 *
 * ★ 문턱 표는 **서버가 준다**(`tier_thresholds_sec`). 화면은 시계가 계속 도니까
 *   자기도 세야 하는데, 표를 화면이 따로 들면 서버 통계와 화면 글자가 다른 문턱을
 *   쓰게 된다 — `allowed_next` 를 서버가 주는 것과 같은 규약이다(D-399).
 *
 * ★ 크기만 쓰지 않는다. **글자 라벨도 함께** 낸다 — 크기는 스크린리더가 못 읽고,
 *   캡처 이미지에서는 「이 카드가 몇 단계인가」를 사람이 세야 한다.
 *   색은 **보조**다: 색만 지워도 이 카드는 그대로 읽혀야 한다 (DA-03 §2-2).
 *
 * ★ **닫힌 이벤트는 시계가 멈춘다.** 계속 커지면 화면이 「급한 것」을 잘못 가리킨다.
 *   멈춘 시계는 커지지 않고 **총 대응 시간**을 적는다 — 다른 사실이므로 다른 글자다.
 */
import { Space, Tooltip, Typography } from 'antd';
import { useEffect, useState } from 'react';

import {
  duration,
  FALLBACK_TIER_THRESHOLDS_SEC,
  TIER_COLOR,
  TIER_FONT_PX,
  TIER_LABEL,
  tierOf,
} from '../time';

const { Text } = Typography;

/** 1초마다 다시 센다. 시계는 도는 것이 요점이라 갱신 주기를 길게 두지 않는다. */
const TICK_MS = 1_000;

interface Props {
  /** 발생 시각(ISO). 이것 하나로 화면이 스스로 센다 — 서버 왕복을 기다리지 않는다. */
  occurredAt: string;
  /** 종결 시각. 있으면 **시계가 멈춘다.** */
  closedAt?: string | null;
  /** 서버가 준 문턱 표. 없으면 폴백을 쓰고, 폴백임을 툴팁에 적는다. */
  thresholds?: number[];
  /** 규칙이 닫은 것인가. 참이면 「사람이 닫았다」로 읽히지 않게 적는다. */
  autoClosed?: boolean;
  /** 작게 그린다(표 안 등). 문턱은 그대로이고 배율만 줄인다. */
  compact?: boolean;
}

export default function ResponseClock({
  occurredAt,
  closedAt,
  thresholds,
  autoClosed = false,
  compact = false,
}: Props) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (closedAt) return;                 // 멈춘 시계는 타이머를 걸지 않는다
    const id = setInterval(() => setNow(Date.now()), TICK_MS);
    return () => clearInterval(id);
  }, [closedAt]);

  const started = new Date(occurredAt).getTime();
  if (!Number.isFinite(started)) {
    // 「모른다」를 「0초」로 그리지 않는다 (D-290).
    return <Text type="secondary">발생 시각 없음</Text>;
  }

  const table = thresholds?.length ? thresholds : [...FALLBACK_TIER_THRESHOLDS_SEC];
  const usingFallback = !thresholds?.length;

  if (closedAt) {
    const total = (new Date(closedAt).getTime() - started) / 1000;
    return (
      <Space size={6}>
        <Text style={{ fontSize: compact ? 13 : 16 }}>
          총 {duration(total)}
        </Text>
        <Text type="secondary" style={{ fontSize: 12 }}>
          {autoClosed ? '자동 종결 — 대응 시간 통계에서 제외됨' : '종결됨 · 시계 멈춤'}
        </Text>
      </Space>
    );
  }

  const elapsed = Math.max(0, (now - started) / 1000);
  const tier = tierOf(elapsed, table);
  const scale = compact ? 0.55 : 1;

  return (
    <Tooltip
      title={
        `문턱 ${table.join('초 · ')}초 마다 한 단계씩 커집니다. ` +
        (usingFallback
          ? '⚠ 서버가 문턱 표를 주지 않아 화면 폴백 값을 쓰는 중입니다 — ' +
            '통계와 다른 문턱일 수 있습니다.'
          : '표는 서버가 준 것과 같습니다.')
      }
    >
      <Space direction="vertical" size={0}>
        <Text
          strong
          // ★ 크기가 정보다. 색은 보조 — 색을 지워도 이 줄은 그대로 읽힌다.
          style={{
            fontSize: Math.round(TIER_FONT_PX[tier] * scale),
            lineHeight: 1.1,
            color: TIER_COLOR[tier],
            fontVariantNumeric: 'tabular-nums',
          }}
          // 크기는 스크린리더가 못 읽는다 — 단계를 글자로도 남긴다.
          aria-label={`경과 ${duration(elapsed)} · ${TIER_LABEL[tier]} · 단계 ${tier}/4`}
        >
          {duration(elapsed)}
        </Text>
        <Text type="secondary" style={{ fontSize: compact ? 11 : 12 }}>
          {TIER_LABEL[tier]}
          {usingFallback ? ' · 폴백 문턱' : ''}
        </Text>
      </Space>
    </Tooltip>
  );
}
