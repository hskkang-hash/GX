/**
 * P-25 스냅샷 — **인증 헤더가 실리는 경로로** 받는다 (2026-09-24).
 *
 * 왜 `<img src="/api/dsm/events/1/snapshot">` 이 아닌가
 * ----------------------------------------------------
 * 브라우저의 이미지 요청은 이 앱의 axios 인터셉터를 **지나지 않는다.** 토큰이 안 실리고,
 * 401 이 오고, 화면에는 깨진 이미지 아이콘이 뜬다. 그 아이콘은 「스냅샷이 없다」와
 * 구별되지 않는다(D-290) — 사용자는 「이 이벤트는 화면이 없구나」로 읽는다.
 *
 * 서명 URL(무계정 링크)로 여는 길은 **불변 제약으로 막혀 있다.** 한 번 새면 회수할 수
 * 없기 때문이고, 조율자가 P-25 를 서명 URL 없이 낸 이유가 그것이다.
 *
 * ★ 나가는 바이트에는 **소인**이 있다(테넌트명 · 열람 시각). 저장은 못 막지만 출처는
 *   남는다 — 그래서 이 화면은 캐시를 지나지 않게 부른다(`X-No-Cache`). 캐시된 바이트는
 *   **남의 열람 시각**을 보여 주고, 그러면 소인이 뜻을 잃는다.
 *
 * ★ 세 상태를 **가른다**: 없다(경로 자체가 빈 문자열) · 못 받았다 · 받았다.
 *   셋을 한 그림으로 그리면 저장소 장애가 「스냅샷 없는 이벤트」로 보인다.
 */
import { Alert, Button, Skeleton, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';

import { DsmApiError, fetchSnapshotUrl } from '../api';

const { Text } = Typography;

interface Props {
  eventId: number | string;
  /** 서버가 준 저장 경로. **비어 있으면 부르지 않는다** — 없는 것은 없다고 적는다. */
  snapshotPath?: string;
  height?: number;
  alt?: string;
  /**
   * 손바닥 화면. **높이를 화면이 정하게 둔다** — 이동 중인 사람의 화면에서
   * 220px 고정은 사진을 우표로 만든다 (P-121 · 모바일도 같은 사진을 본다).
   */
  compact?: boolean;
  /**
   * [P-148 · 턴 R] `<img>` 에 다는 `data-gx` 표식. **판정기가 찾는 자리다** —
   * `scripts/verify_click_completes.py` 의 사진 술어(U3#3)가
   * `img[data-gx="snapshot"]` 하나를 찾아 `naturalWidth` 를 잰다. 지정하지
   * 않으면 속성을 안 단다 — 다른 화면(관제 상세·초점 큐)은 영향이 없다.
   */
  dataGx?: string;
}

export default function EventSnapshot({
  eventId,
  snapshotPath,
  height = 220,
  alt = '이벤트 스냅샷',
  compact = false,
  dataGx,
}: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; status: number } | null>(null);
  const [loading, setLoading] = useState(false);
  /** 「다시 시도」가 누를 것이 되게 하는 값. 늘면 아래 effect 가 다시 돈다. */
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (!snapshotPath) {
      setUrl(null);
      setError(null);
      return;
    }
    let revoke: (() => void) | null = null;
    let alive = true;
    setLoading(true);
    setError(null);

    fetchSnapshotUrl(eventId)
      .then(({ url: objectUrl, revoke: undo }) => {
        revoke = undo;
        if (!alive) {
          undo();               // 이미 떠난 화면에 blob 을 남기지 않는다
          return;
        }
        setUrl(objectUrl);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        const status = err instanceof DsmApiError ? err.status : 0;
        setError({
          message: err instanceof Error ? err.message : String(err),
          status,
        });
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
      // ★ 반드시 되돌린다 — 안 하면 15초 갱신마다 blob 이 쌓여 관제 화면이 밤새 먹는다.
      if (revoke) revoke();
    };
  }, [eventId, snapshotPath, nonce]);

  const retry = useCallback(() => setNonce((n) => n + 1), []);

  if (!snapshotPath) {
    return (
      <Text type="secondary">
        이 이벤트에는 저장된 스냅샷 경로가 없습니다 — 못 가져온 것이 아니라 없습니다.
      </Text>
    );
  }
  if (loading && !url) {
    return <Skeleton.Image active style={{ width: '100%', height: compact ? 180 : height }} />;
  }
  if (error) {
    // ★ 503 은 **저장소가 죽은 것**이다(UX-10). 「스냅샷이 없다」와 다른 사실이므로
    //   다른 문장으로 적는다 — 하나로 묶으면 장애가 데이터 부재로 위장된다.
    //
    // ★ [UX-20 · 2026-09-26] **원문 오류를 그리지 않는다.** 앞판은 `error.message` 를
    //   그대로 냈고, 화면에 「Network Error」가 떴다 — 그것은 axios 의 말이지
    //   당직자의 말이 아니다(GX-COPY §2). 원문은 콘솔·관리자 자리에 남기고 화면에는
    //   사용자 언어 한 줄과 **누를 것**(다시 시도)을 낸다.
    //
    // ★★ [P-121 · 2026-09-10 턴 O] **「불러오지 못했습니다」는 서버가 거절했을 때만
    //   쓴다.** 앞판은 상태를 안 가리고 그 한 문장을 냈고, 서버가 **200 으로 37KB 를
    //   보낸 화면**에도 그 빨강이 떠 있었다 — 앞단이 바이트를 못 꺼낸 것인데 화면은
    //   **서버 탓**으로 적었다. 거짓 사유는 없는 사유보다 나쁘다: 사람이 저장소를
    //   보러 간다.
    //
    //   이제 셋을 가른다.
    //     503        저장소가 죽었다 (UX-10) — 이벤트 자체는 정상이다
    //     그 밖 4xx/5xx  서버가 **거절했다** — 여기서만 「불러오지 못했습니다」
    //     상태 0     HTTP 대답이 아예 없었다(끊김) — 서버 탓으로 적지 않는다
    const storageDown = error.status === 503;
    const serverRefused = error.status >= 400 && !storageDown;
    const message = storageDown
      ? '저장소에 연결할 수 없습니다. 잠시 뒤 다시 시도하십시오'
      : serverRefused
        ? '사진을 불러오지 못했습니다'
        : '사진을 받는 중에 연결이 끊겼습니다';
    const description = storageDown
      ? '이벤트 자체는 정상입니다 — 사진을 보관하는 저장소에 닿지 못했습니다.'
      : serverRefused
        ? '잠시 뒤 다시 시도해 주십시오.'
        : '서버가 거절한 것이 아닙니다 — 대답이 오기 전에 끊겼습니다. 다시 시도해 주십시오.';
    return (
      <Alert
        type={serverRefused ? 'error' : 'warning'}
        showIcon
        message={message}
        description={description}
        action={
          // ★ [P-121] `<a onClick>` 을 **누를 것**으로 바꿨다. 앵커는 href 가 없으면
          //   키보드 초점을 안 받고 Enter 로도 안 눌린다 — 관제실에는 마우스를 안 쓰는
          //   자리가 있다. 누름은 `nonce` 를 올리고, 그 값이 아래 effect 의 인자라
          //   **요청이 실제로 한 번 더 나간다**(검수는 요청 수로 잰다).
          <Button size="small" onClick={retry}>
            다시 시도
          </Button>
        }
      />
    );
  }
  return (
    <figure style={{ margin: 0 }}>
      <img
        src={url ?? ''}
        alt={alt}
        data-gx={dataGx}
        style={{
          width: '100%',
          // ★ 손바닥 화면에서는 높이를 **고정하지 않는다** — 가로에 맞춰 접힌다.
          height: compact ? 'auto' : height,
          maxHeight: compact ? '60vh' : undefined,
          objectFit: 'contain',
          background: '#000',
          display: 'block',
        }}
      />
      <figcaption>
        {/* ★ [UX-20] 절 ID(P-25)를 뺐다 — 절 이름은 사용자 본문의 자리가 아니다. */}
        <Text type="secondary" style={{ fontSize: 12 }}>
          이 사진에는 기관명과 열람 시각이 찍혀 있습니다.
        </Text>
      </figcaption>
    </figure>
  );
}
