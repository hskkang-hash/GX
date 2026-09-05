/**
 * 인수 화면 위에 **한국어 헤더 한 줄**을 얹는다 — UX-21 (P-40 집행).
 *
 * 왜 감싸는가
 * -----------
 * 관제 역할(U1·U2·U4)에서는 이 화면들의 **메뉴 연결을 끊었다.** 그러나 시스템
 * 관리자(U5)에게는 남는다 — 장비를 등록할 자리가 실제로 거기이기 때문이다.
 * 남기되 **화면이 무엇인지 우리말로 먼저 말한다.**
 *
 * ★ 인수 화면을 **고치지 않는다.** 감싸는 것은 우리 층이고, 안쪽은 한 줄도 안 바뀐다.
 *   고치면 그 순간 그 화면은 인수 자산이 아니라 우리 빚이 된다.
 * ★ 한 줄이다. 두 줄이 되면 그것은 헤더가 아니라 안내문이고, 안내문은 아무도 안 읽는다.
 */
import type { ReactNode } from 'react';

interface Props {
  /** 이 화면이 무엇인지 — **우리말 이름 하나.** */
  title: string;
  children: ReactNode;
}

export default function InheritedScreen({ title, children }: Props) {
  return (
    <div>
      <div
        role="note"
        style={{
          padding: '8px 16px',
          marginBottom: 8,
          borderLeft: '3px solid #1677ff',
          background: 'rgba(22, 119, 255, 0.08)',
          fontSize: 13,
          lineHeight: '20px',
        }}
      >
        <strong>{title}</strong>
        {' · 관리자 전용 화면입니다. 아래 표기는 아직 영문입니다.'}
      </div>
      {children}
    </div>
  );
}
