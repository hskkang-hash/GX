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
import { Alert, Skeleton, Typography } from 'antd';
import { useEffect, useState } from 'react';

import { DsmApiError, fetchSnapshotUrl } from '../api';

const { Text } = Typography;

interface Props {
  eventId: number | string;
  /** 서버가 준 저장 경로. **비어 있으면 부르지 않는다** — 없는 것은 없다고 적는다. */
  snapshotPath?: string;
  height?: number;
  alt?: string;
}

export default function EventSnapshot({
  eventId,
  snapshotPath,
  height = 220,
  alt = '이벤트 스냅샷',
}: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<{ message: string; status: number } | null>(null);
  const [loading, setLoading] = useState(false);

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
  }, [eventId, snapshotPath]);

  if (!snapshotPath) {
    return (
      <Text type="secondary">
        이 이벤트에는 저장된 스냅샷 경로가 없습니다 — 못 가져온 것이 아니라 없습니다.
      </Text>
    );
  }
  if (loading && !url) return <Skeleton.Image active style={{ width: '100%', height }} />;
  if (error) {
    // ★ 503 은 **저장소가 죽은 것**이다(UX-10). 「스냅샷이 없다」와 다른 사실이므로
    //   다른 문장으로 적는다 — 하나로 묶으면 장애가 데이터 부재로 위장된다.
    const storageDown = error.status === 503;
    return (
      <Alert
        type={storageDown ? 'warning' : 'error'}
        showIcon
        message={storageDown ? '저장소 연결 안 됨' : '스냅샷을 받지 못했습니다.'}
        description={
          storageDown
            ? `이벤트는 정상입니다 — 이미지 저장소에 닿지 못했습니다. (${error.message})`
            : error.message
        }
      />
    );
  }
  return (
    <figure style={{ margin: 0 }}>
      <img
        src={url ?? ''}
        alt={alt}
        style={{ width: '100%', height, objectFit: 'contain', background: '#000' }}
      />
      <figcaption>
        <Text type="secondary" style={{ fontSize: 12 }}>
          인증된 경로로 받은 프레임입니다. 이미지에는 테넌트명과 열람 시각 소인이
          찍혀 있습니다 (P-25).
        </Text>
      </figcaption>
    </figure>
  );
}
