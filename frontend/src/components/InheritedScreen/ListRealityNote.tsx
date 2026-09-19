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
 *
 * ── 턴 V · 차선 U56 — `/roles` 표 0 의 **마지막 갈래를 닫는다** ──────────────────
 *
 * 턴 U 가 두 갈래로 갈라 놓았다: ㉠ 서버가 0행을 냈다 · ㉡ 서버는 냈는데 화면이
 * 못 그렸다. 이번 턴에 **실제 계정으로** 갈랐다 [실측 2026-09-18 · 개발 DB · dj-core 의
 * 판정식을 그대로 불러서]:
 *
 *     Role.objects.filter(deleted__isnull=True).count()            → **16**
 *     _check_path_permission(gxseed_u5_sysop, "/roles", "read")    → **True**
 *     _check_path_permission(gxseed_u4_official, "/roles", "read") → False
 *     _check_path_permission(gxprobe_v, "/roles", "read")          → False
 *
 * ⇒ U5 시드 계정은 **문을 지나고 16행을 받는다.** 그러므로 그 계정이 본 0행은 ㉡ 이고,
 *   그 자리는 rj-core 인수 화면 안이라 **우리 층에 고칠 것이 없다**(§0.4 · 등재 요청).
 * ⇒ 남은 진짜 갈래는 **권한 없는 계정**이었고, 그 갈래를 이 파일이 이번에 닫는다:
 *   거절이 **200 봉투 안에** 오기 때문에(`/api/roles/` 는 승격 목록 밖) 종전 코드는
 *   그것을 8초 뒤 「세지 못했습니다」로 적었다 — **고장과 권한을 뭉친 문장**이다.
 *   이제 「볼 권한이 없습니다」로 즉시 말한다. **분모 없이 답하지 않는다.**
 */
import { Alert, Button, Space } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { COPY_PERMISSION_DENIED } from '@/features/session/permissionDenied';
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

type Counted =
  | { kind: 'loading' }
  | { kind: 'count'; n: number }
  | { kind: 'denied'; status: number }
  | { kind: 'unknown' };

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

          /*
            ★★ [턴 V · 차선 U56] **거절이 200 봉투 안에 들어 있다** [실측 2026-09-18].

            `/api/roles/` 는 `API_CONTRACT_PROMOTE_PATHS` 에 **없다**(settings.py 의
            그 자리에 사유가 적혀 있다 — rj-core 화면의 오류 처리를 이 저장소에서
            읽을 수 없어 SEC-11b 로 남겼다). 그래서 dj-core 의 권한 거절은
            HTTP 403 이 아니라 이렇게 온다:

                HTTP 200  { "success": false, "status_code": 403, "message": "Permission denied." }

            이 모양은 `count` 칸이 없으므로 종전 코드에서는 **그냥 빠져나가** 8초 뒤
            「세지 못했습니다」가 됐다. 즉 **「볼 권한이 없다」가 「고장났다」로 읽혔다**
            (D-349 착시 ⑧ 이 앞단에 남긴 마지막 갈래). 그래서 봉투를 편다.
            ⚠ 서버를 고치는 것이 아니다 — 승격(`API_CONTRACT_PROMOTE_PATHS`)은 반경이
              큰 결정이고 이 차선의 것이 아니다. 여기서는 **읽고 말한다.**
          */
          const envelope = body as
            | { count?: unknown; success?: unknown; status_code?: unknown }
            | null;
          const denied =
            envelope?.success === false &&
            (envelope?.status_code === 403 || envelope?.status_code === 401);
          if (denied) {
            settled = true;
            setState({ kind: 'denied', status: Number(envelope?.status_code) });
            return;
          }

          const n = envelope?.count;
          if (typeof n !== 'number') return; // 모양이 다르면 아래 시계가 판정한다
          settled = true;
          setState({ kind: 'count', n });
        })
        .catch((err: unknown) => {
          /*
            ★★ [턴 V · 차선 U56] **「못 읽었다」와 「볼 권한이 없다」를 뭉치지 않는다.**

            [실측 2026-09-18] `/api/roles/` 앞에는 메뉴 권한 문지기가 하나 더 있다
            (`core/role/permission.py::path_permission("read", "/roles")`). 권한이 없는
            계정은 **403** 을 받는다 — 그때 이 조각은 8초를 기다렸다가 「세지 못했습니다」
            로 떨어졌다. 그 문장은 **고장**을 가리키는 말인데 실제로는 **권한**이다.
            빈 표 밑에 그 말이 붙으면 사람은 시스템이 죽은 줄 안다.

            ⚠ 그래서 **확정된 거절은 즉시 확정한다**(시계를 기다리지 않는다). 확정할 수
              없는 실패(그물망·모양 다름)만 아래 시계가 「세지 못했습니다」로 판정한다 —
              회색은 회색으로 남긴다(D-301).
            ★ 낱말을 만들지 않았다 — 사전의 `COPY_PERMISSION_DENIED` 를 그대로 쓴다
              (GX-COPY 규칙 1 · `permissionDenied.ts` 와 같은 규율).
          */
          const status = (err as { response?: { status?: number } } | null)?.response
            ?.status;
          if (status === 401 || status === 403) {
            if (!alive || settled) return;
            settled = true;
            setState({ kind: 'denied', status });
          }
          /* 그 밖에는 여기서 0을 만들지 않는다. 판정은 아래 시계 한 곳이 한다. */
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

  if (state.kind === 'denied') {
    return (
      <Alert
        type="error"
        showIcon
        style={{ marginBottom: 8 }}
        message={`${noun} 목록 — ${COPY_PERMISSION_DENIED}.`}
        description={
          <span>
            아래 표가 비어 있는 것은 「{noun}이(가) 없다」가 아니라{' '}
            <strong>이 계정이 목록을 읽지 못한 것</strong>입니다 (서버 응답 {state.status}).
            권한이 필요하면 관리자에게 요청하십시오.
          </span>
        }
      />
    );
  }

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
