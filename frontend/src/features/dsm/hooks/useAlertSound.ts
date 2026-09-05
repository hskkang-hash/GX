/**
 * UX-15 **소리 3종** — 관제요원은 8시간 마우스를 쥐지 않는다. 화면도 안 본다.
 *
 * 왜 파일이 아니라 WebAudio 인가
 * -----------------------------
 * 소리 파일을 넣으면 번들이 커지고 저작권이 따라붙고, 무엇보다 **잘못 나가면
 * 되돌릴 수 없는 것이 자산이다.** 여기 세 소리는 서른 줄짜리 진동수 표이고,
 * 표를 고치면 소리가 고쳐진다. 외부 파일이 없으므로 사설망에서도 그대로 운다.
 *
 * 세 소리를 **무엇으로 갈랐나** [판단 근거 · 2026-09-05]
 * ---------------------------------------------------
 * 등급은 셋(심각·경계·주의)인데 **소리는 심각에서만 난다** — 그러면 등급으로
 * 가른 소리 셋 중 둘은 영원히 울리지 않는다. 없는 소리를 만드는 셈이다.
 * 그래서 등급이 아니라 **관제요원이 알아야 할 세 가지 사건**으로 갈랐다:
 *
 *   ① newCritical      심각이 **새로 들어왔다**            (두 음 올라감)
 *   ② overdueCritical  심각이 **가장 오래 기다린 단계**를 넘었다 (세 음 내려감)
 *   ③ actionEcho       **사람이 누른 것**의 되울림          (짧은 한 음)
 *
 * ★ ①②는 사건 소리다 — **심각에서만** 난다(그 문지기는 `useCriticalAlarm` 에 있다).
 *   ③은 사건 소리가 아니라 **자기 손가락의 되울림**이다. 키보드로만 일하는 사람은
 *   「눌렸나」를 화면 갱신이 오기 전까지 알 수 없고, 그 반 초가 같은 키를 두 번
 *   누르게 만든다. 그래서 ③은 등급을 묻지 않는다 — 등급의 소리가 아니기 때문이다.
 *
 * ★ 브라우저는 **사람이 한 번 만지기 전까지 소리를 잠근다**(자동재생 정책).
 *   그래서 `audible` 이 따로 있다: 음소거가 아닌데도 안 들리는 상태가 실재하고,
 *   그것을 화면이 「소리가 꺼져 있습니다」로 **먼저 말해야** 한다. 안 그러면
 *   관제요원은 조용한 화면을 「사건이 없다」로 읽는다.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export type AlertSound = 'newCritical' | 'overdueCritical' | 'actionEcho';

/** 음소거는 새로고침을 건너 살아남는다 — 밤새 켜 둔 화면이 아침에 다시 울면 안 된다. */
const MUTE_KEY = 'gx.dsm.queue.muted';

interface Blip {
  hz: number;
  ms: number;
  gain: number;
  wave: OscillatorType;
}

/** 세 소리의 전부. 소리를 고치려면 이 표만 고친다. */
const SCORE: Record<AlertSound, Blip[]> = {
  //: 올라가는 두 음 — 「무엇이 들어왔다」.
  newCritical: [
    { hz: 880, ms: 130, gain: 0.18, wave: 'triangle' },
    { hz: 1320, ms: 170, gain: 0.18, wave: 'triangle' },
  ],
  //: 내려가는 세 음 — 「기다리고 있다」. 새 것과 **귀로 갈려야** 한다.
  overdueCritical: [
    { hz: 1200, ms: 150, gain: 0.22, wave: 'sawtooth' },
    { hz: 900, ms: 150, gain: 0.22, wave: 'sawtooth' },
    { hz: 660, ms: 280, gain: 0.22, wave: 'sawtooth' },
  ],
  //: 짧고 낮은 한 음 — 경보로 들리면 안 된다. 그래서 가장 작고 가장 짧다.
  actionEcho: [{ hz: 620, ms: 70, gain: 0.1, wave: 'sine' }],
};

type Ctor = new () => AudioContext;

function makeContext(): AudioContext | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { AudioContext?: Ctor; webkitAudioContext?: Ctor };
  const C = w.AudioContext ?? w.webkitAudioContext;
  if (!C) return null;
  try {
    return new C();
  } catch {
    // 소리를 못 만드는 것은 화면의 고장이 아니다. 조용히 없는 채로 산다.
    return null;
  }
}

function readMuted(): boolean {
  try {
    return window.localStorage.getItem(MUTE_KEY) === '1';
  } catch {
    return false;
  }
}

function writeMuted(value: boolean): void {
  try {
    window.localStorage.setItem(MUTE_KEY, value ? '1' : '0');
  } catch {
    // 저장을 못 해도 이번 근무 동안은 지켜진다.
  }
}

export interface SoundBox {
  /** 사람이 끈 것인가. */
  muted: boolean;
  /**
   * 지금 **실제로 들리는가.** 음소거가 아니어도 거짓일 수 있다 —
   * 브라우저가 아직 소리를 잠가 두었거나, 이 브라우저에 소리 장치가 없다.
   */
  audible: boolean;
  toggle: () => void;
  /** 켜면서 브라우저의 잠금도 함께 푼다. **사람의 조작 안에서** 불러야 풀린다. */
  enable: () => void;
  play: (name: AlertSound) => void;
}

export function useAlertSound(): SoundBox {
  const [muted, setMuted] = useState<boolean>(() =>
    typeof window === 'undefined' ? false : readMuted(),
  );
  const [running, setRunning] = useState(false);
  const ctxRef = useRef<AudioContext | null>(null);
  const mutedRef = useRef(muted);
  mutedRef.current = muted;

  const ctx = useCallback((): AudioContext | null => {
    if (!ctxRef.current) ctxRef.current = makeContext();
    return ctxRef.current;
  }, []);

  const unlock = useCallback(() => {
    const c = ctx();
    if (!c) {
      setRunning(false);
      return;
    }
    if (c.state === 'running') {
      setRunning(true);
      return;
    }
    void c
      .resume()
      .then(() => setRunning(c.state === 'running'))
      .catch(() => setRunning(false));
  }, [ctx]);

  //: ★ 사람이 처음 만질 때 잠금이 풀린다. 큐 화면은 키보드로 도니까 첫 키가
  //:   곧 첫 조작이다 — 그래서 마우스를 안 쥐어도 소리가 살아난다.
  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const once = () => unlock();
    window.addEventListener('keydown', once);
    window.addEventListener('pointerdown', once);
    unlock();
    return () => {
      window.removeEventListener('keydown', once);
      window.removeEventListener('pointerdown', once);
    };
  }, [unlock]);

  useEffect(
    () => () => {
      const c = ctxRef.current;
      ctxRef.current = null;
      if (c) void c.close().catch(() => undefined);
    },
    [],
  );

  const play = useCallback(
    (name: AlertSound) => {
      if (mutedRef.current) return;
      const c = ctx();
      if (!c || c.state !== 'running') {
        // 못 울린 것을 조용히 삼키지 않는다 — 다음 렌더에서 배지가 그 사실을 말한다.
        setRunning(false);
        return;
      }
      let at = c.currentTime + 0.01;
      for (const blip of SCORE[name]) {
        const osc = c.createOscillator();
        const amp = c.createGain();
        osc.type = blip.wave;
        osc.frequency.setValueAtTime(blip.hz, at);
        const end = at + blip.ms / 1000;
        amp.gain.setValueAtTime(0.0001, at);
        amp.gain.exponentialRampToValueAtTime(blip.gain, at + 0.012);
        amp.gain.exponentialRampToValueAtTime(0.0001, end);
        osc.connect(amp);
        amp.connect(c.destination);
        osc.start(at);
        osc.stop(end + 0.02);
        at = end + 0.03;
      }
    },
    [ctx],
  );

  const toggle = useCallback(() => {
    setMuted((prev) => {
      const next = !prev;
      writeMuted(next);
      if (!next) unlock();
      return next;
    });
  }, [unlock]);

  const enable = useCallback(() => {
    setMuted(false);
    writeMuted(false);
    unlock();
  }, [unlock]);

  return { muted, audible: !muted && running, toggle, enable, play };
}
