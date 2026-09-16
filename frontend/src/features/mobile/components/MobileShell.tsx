/**
 * 이동 중(U3) 화면의 껍데기 — **한 손 · 한 화면**.
 *
 * ★ 왜 껍데기를 따로 두나: 관제실 화면(W1·W2)은 넓은 모니터를 전제로 짜였고,
 *   같은 컴포넌트를 폭만 줄여 쓰면 표가 옆으로 새고 버튼이 손가락보다 작아진다.
 *   여기서 정하는 것은 **폭 상한 · 최소 터치 크기 · 세로 흐름** 셋뿐이고,
 *   내용물은 전부 DSM 의 것을 그대로 쓴다(D-379 — 있는 것을 다시 만들지 않는다).
 *
 * ★ 「언제 것인가」를 머리에 적는다. 이동 중에는 화면이 오래 켜져 있고, 낡은 줄을
 *   모르는 화면은 **낡은 판단**을 만든다.
 */
import { Button, Space, Typography } from 'antd';
import { ReactNode, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { stamp, TIMEZONE_NOTE } from '../../dsm/time';
import { ensureFieldPushServiceWorker } from '../push';

const { Text, Title } = Typography;

interface Props {
  title: string;
  /** 마지막으로 성공한 시각. 없으면 「아직 못 받음」이라고 적는다 — 빈칸으로 두지 않는다. */
  loadedAt?: Date | null;
  onReload?: () => void;
  /** 참이면 뒤로 가기 단추를 그린다. */
  backTo?: string;
  /** 제목 아래 한 줄. 범위·경고 따위. */
  banner?: ReactNode;
  children: ReactNode;
}

/** 손가락 최소 크기. 44px 은 화면 지침이 공통으로 쓰는 값이다. */
export const TOUCH_MIN = 44;

export default function MobileShell({
  title,
  loadedAt,
  onReload,
  backTo,
  banner,
  children,
}: Props) {
  const navigate = useNavigate();

  useEffect(() => {
    // [CH-03 · 턴 R] 골격만 — 등록만 하고 아무것도 묻지 않는다(권한·구독은 다음 턴).
    // 실패해도 이 화면은 그대로 쓴다 — 알림은 부가 기능이지 이 화면의 본업이 아니다.
    void ensureFieldPushServiceWorker();
  }, []);

  return (
    <div
      style={{
        maxWidth: 480,
        margin: '0 auto',
        padding: '12px 12px 32px',
        boxSizing: 'border-box',
      }}
    >
      <Space
        direction="vertical"
        size={10}
        style={{ width: '100%' }}
      >
        <Space
          align="center"
          style={{ width: '100%', justifyContent: 'space-between' }}
        >
          <Space align="center">
            {backTo ? (
              <Button
                size="small"
                onClick={() => navigate(backTo)}
                style={{ minHeight: 32 }}
              >
                ← 목록
              </Button>
            ) : null}
            <Title
              level={4}
              style={{ margin: 0 }}
            >
              {title}
            </Title>
          </Space>
          {onReload ? (
            <Button
              size="small"
              onClick={onReload}
              style={{ minHeight: 32 }}
            >
              새로고침
            </Button>
          ) : null}
        </Space>

        <Text
          type="secondary"
          style={{ fontSize: 12 }}
        >
          {/* ★ 「아직 못 받음」과 「0건」을 가른다 — 빈칸은 둘을 같아 보이게 한다. */}
          {loadedAt ? `기준 ${stamp(loadedAt)}` : '아직 값을 받지 못했습니다'} · {TIMEZONE_NOTE}
        </Text>

        {banner}

        {children}
      </Space>
    </div>
  );
}
