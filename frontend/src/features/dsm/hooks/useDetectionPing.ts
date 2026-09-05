/**
 * UX-08 — **새로고침 없이 카드가 붙게 하는 한 줄.**
 *
 * 무엇을 하나
 * -----------
 * 서버가 「무엇인가 늘었다」를 두드리면 화면이 **자기 목록 문을 다시 부른다.**
 * 받는 것은 신호뿐이고 **카드가 아니다** — 무엇이 한 장인지(5분 이어붙이는 창의
 * 묶음, 알림 억제)는 서버의 목록 문 한 곳이 정한다. 화면이 카드를 직접 끼워 넣으면
 * 목록이 두 벌이 되고, 두 벌은 반드시 어긋난다.
 *
 * 왜 주기 갱신을 없애지 않았나
 * ---------------------------
 * 이 연결은 **바닥이 아니라 덤**이다. 소켓이 안 붙어도(사설망 · 프록시 · 세션 방식
 * 차이) 화면은 주기 갱신으로 계속 산다. 소켓을 바닥으로 삼으면 안 붙는 그날
 * 화면이 **조용히 멈춘다** — 멈춘 화면은 「사건이 없다」와 구별되지 않는다.
 *
 * ★ 그래서 실패를 삼키지 않되 사용자에게 빨강을 띄우지도 않는다. 연결 여부를
 *   돌려주므로 부르는 쪽이 필요하면 배지로 쓸 수 있다.
 */
import { useEffect, useRef, useState } from 'react';

/** 이 자리에서만 정한다 — 경로 문자열을 화면에 흩지 않는다. */
export const DETECTION_WS_PATH = '/ws/surveillance/profiles/';

/** 끊기면 이만큼 뒤에 한 번 더 붙어 본다. 무한 즉시 재시도는 서버를 때린다. */
const RETRY_MS = 15_000;

function wsUrl(): string {
  const base = (import.meta.env.VITE_API_URL as string | undefined) ?? '';
  try {
    const u = new URL(base || window.location.origin, window.location.origin);
    u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
    u.pathname = DETECTION_WS_PATH;
    u.search = '';
    return u.toString();
  } catch {
    return '';
  }
}

/**
 * @param onPing 두드림을 받았을 때 부를 것 — 대개 목록의 `reload`.
 * @param enabled 꺼 두고 싶을 때(예: 훈련 화면)를 위한 스위치.
 */
export function useDetectionPing(onPing: () => void, enabled = true): boolean {
  const [connected, setConnected] = useState(false);
  // 최신 콜백을 잡아 둔다 — 의존성에 넣으면 렌더마다 소켓을 다시 연다.
  const cb = useRef(onPing);
  cb.current = onPing;

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      return undefined;
    }
    const url = wsUrl();
    if (!url) return undefined;

    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    const open = () => {
      if (closed) return;
      try {
        socket = new WebSocket(url);
      } catch {
        return; // 못 열어도 주기 갱신이 바닥으로 남는다
      }
      socket.onopen = () => setConnected(true);
      socket.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data as string) as { type?: string };
          if (payload.type === 'detection_message') cb.current();
        } catch {
          // 모르는 모양은 무시한다. 두드림을 못 알아들은 것이지 오류가 아니다.
        }
      };
      socket.onclose = () => {
        setConnected(false);
        if (!closed) retry = setTimeout(open, RETRY_MS);
      };
      socket.onerror = () => setConnected(false);
    };

    open();
    return () => {
      closed = true;
      if (retry) clearTimeout(retry);
      socket?.close();
    };
  }, [enabled]);

  return connected;
}
