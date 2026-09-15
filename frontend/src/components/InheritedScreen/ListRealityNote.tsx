/**
 * P-123 · UX-31 ④ — **빈 표는 「없다」가 아니었다.** (턴 O · 차선 C2)
 *
 * 무엇을 쟀나 [실측 2026-09-10 · 턴 O · U5 `gxseed_u5_sysop` · 번들 `index-CvGh2vJ2.js`]
 * ------------------------------------------------------------------------------
 *   서버:  `GET /api/v1/user/list/` → **200 · count=30** (25행)
 *          `GET /api/roles/`        → **200 · count=15** (15행)
 *   화면:  `/users` **90바이트** — 표 요소가 **아예 없다**(`<table>` 0개)
 *          `/roles` **160바이트** — 머리글 4칸 · **0행**
 *   브라우저가 그 두 문을 **한 번도 부르지 않았다** (요청 6건 추적 · 목록 호출 0건).
 *
 * 그리고 인수 코드가 실패를 **0행으로 삼킨다** [실측 · `rj-core` 번들]:
 *
 *     getListUserAPI: async (...) => { try { … } catch { return { data: [], totalPage: 0, totalItem: 0 } } }
 *
 * 즉 **「못 불렀다」와 「없다」가 같은 그림**이 된다 — DA-03 §2-5 가 금지한 바로 그 모양이고,
 * 이 화면에서는 그것이 기본값이다. 인수 코드는 §0.4 로 못 고친다.
 *
 * 그래서 이 조각이 하는 일 — **우리가 직접 세어서 한 줄로 말한다**
 * -------------------------------------------------------------
 *   · 서버에 N개가 있으면: 「서버에는 N개가 있습니다」 + 아래 표가 비었으면 그것은
 *     **없다가 아니라 못 그린 것**이라고 적는다.
 *   · 정말 0개면: 「아직 없습니다」 + **더하는 자리**를 준다.
 *   · 못 읽으면: 「세지 못했습니다」 — 0으로 적지 않는다(D-301).
 *
 * ★ 인수 화면을 한 줄도 안 고친다. 위에 한 줄을 얹을 뿐이다(`InheritedScreen` 규율).
 * ⚠ 이 줄은 **진단이지 수리가 아니다.** 표가 비는 원인은 인수 화면 안에 있고, 그것은
 *   dj-core 의 자리다. 덮지 않고 **보이게** 두는 것이 이 줄의 목적이다.
 */
import { Alert, Button, Space } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import API from '@/services/API';

interface Props {
  /** 세는 문. 본문의 `count` 한 칸만 읽는다. */
  countUrl: string;
  /** 「사용자」·「역할」 — 무엇을 세는가. */
  noun: string;
  /** 더하는 자리. 없으면 단추를 안 그린다(누를 것이 없는 단추는 거짓말). */
  addPath?: string;
  /** 더하는 단추의 이름. */
  addLabel?: string;
}

type Counted = { kind: 'loading' } | { kind: 'count'; n: number } | { kind: 'unknown' };

export default function ListRealityNote({ countUrl, noun, addPath, addLabel }: Props) {
  const [state, setState] = useState<Counted>({ kind: 'loading' });

  useEffect(() => {
    let alive = true;
    let settled = false;

    /**
     * ★★ [실측 2026-09-10 · 턴 O] **주소로 곧장 연 첫 판에서는 이 줄이 안 떴다.**
     *   화면 안에서 옮겨 왔을 때는 떴다(193바이트 · 30개). 갈린 것은 **찬 로딩**이다 —
     *   새로 고친 직후에는 토큰 복구·갱신이 아직 도는 중이고, 그 사이 나간 요청은
     *   인수 인터셉터의 갱신 대기줄에 들어가 **영영 안 돌아올 수 있다.**
     *   그때 이 조각이 `loading` 에 머물면 화면에는 **아무 말도 안 뜬다** —
     *   그것은 고치기 전과 똑같은 빈 화면이다.
     *   그래서 ① 한 번 더 물어보고 ② 그래도 안 오면 **「세지 못했습니다」로 떨어진다.**
     *   회색을 초록으로도, 빨강으로도 만들지 않는다 — 회색이라고 적는다(D-301).
     */
    const ask = () => {
      // ★ `page_size=1` 로 센다 — 세는 데에 목록 전부를 끌어오지 않는다.
      API.get(countUrl, { params: { page_size: 1, current_page: 1 } })
        .then((body: unknown) => {
          if (!alive || settled) return;
          const n = (body as { count?: unknown } | null)?.count;
          if (typeof n !== 'number') return; // 모양이 다르면 아래 시계가 판정한다
          settled = true;
          setState({ kind: 'count', n });
        })
        .catch(() => {
          /* 여기서 0을 만들지 않는다. 판정은 아래 시계 한 곳이 한다. */
        });
    };

    ask();
    const retry = setTimeout(ask, 3_000);
    const giveUp = setTimeout(() => {
      if (alive && !settled) setState({ kind: 'unknown' });
    }, 8_000);

    return () => {
      alive = false;
      clearTimeout(retry);
      clearTimeout(giveUp);
    };
  }, [countUrl]);

  if (state.kind === 'loading') return null;

  const add =
    addPath && addLabel ? (
      <Link to={addPath}>
        <Button size="small" type="primary">
          {addLabel}
        </Button>
      </Link>
    ) : null;

  if (state.kind === 'unknown') {
    return (
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 8 }}
        message={`${noun} 수를 세지 못했습니다.`}
        description="아래 표가 비어 있어도 그것이 「없다」는 뜻은 아닙니다."
        action={add}
      />
    );
  }

  if (state.n === 0) {
    return (
      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 8 }}
        message={`아직 ${noun}이(가) 없습니다.`}
        description={`서버에도 ${noun} 0개입니다. 아래에서 더할 수 있습니다.`}
        action={add}
      />
    );
  }

  return (
    <Alert
      type="warning"
      showIcon
      style={{ marginBottom: 8 }}
      message={`서버에는 ${noun} ${state.n}개가 있습니다.`}
      description={
        <Space direction="vertical" size={2}>
          <span>
            아래 표가 비어 있다면 그것은 「없다」가 아니라{' '}
            <strong>이 화면이 목록을 그리지 못한 것</strong>입니다. 새로 고쳐도 같으면
            관리자에게 알려 주십시오.
          </span>
        </Space>
      }
      action={add}
    />
  );
}
