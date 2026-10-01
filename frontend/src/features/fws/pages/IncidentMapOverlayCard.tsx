/**
 * FWS-F4-01 — 지도 겹침 (턴 AR · N1 · P-448).
 *
 * 새 지도 엔진 0 — 이미 있는 지도 컴포넌트(`components/maps` 의 `Map`)에 **F5 정찰 좌표**를
 * 점으로 얹는다. F6-04 확산예측 업로드 결과와 대피 구역(마을)은 이 저장소에 **기하(좌표·경계)가
 * 없다** — 업로드 참조·마을 이름이라 지도에 그리지 않고 곁 표로 보인다(화선을 지어내지 않는다:
 * 화선 자동 추정은 명세에 없고, 업로드된 화선만 다룬다).
 * 누르면 두 GET 을 캐시 우회로 다시 불러 서버에 남은 값만 그린다.
 */
import { useCallback, useEffect, useState } from 'react';

import { Button, Card, List, Space, Typography } from 'antd';

import { Map } from '../../../components/maps';
import { fwsGetFresh } from '../api';

const { Text } = Typography;

interface ReconCoords {
  event_id: number;
  lat: number | null;
  lng: number | null;
  radius_m: number | null;
  state: string | null;
}

interface SpreadResult {
  spread_id: number;
  image_ref: string | null;
  arrival_note: string | null;
  uploaded_at: string | null;
}

export default function IncidentMapOverlayCard({
  eventId,
  evacVillages,
}: {
  eventId: string;
  evacVillages: string[];
}): JSX.Element {
  const [recon, setRecon] = useState<ReconCoords | null>(null);
  const [spread, setSpread] = useState<SpreadResult[]>([]);
  const [failed, setFailed] = useState(false);

  const reload = useCallback(async (): Promise<void> => {
    try {
      const [r, s] = await Promise.all([
        fwsGetFresh<ReconCoords>(`/api/fws/ap/drone/missions/${eventId}/recon-coords`),
        fwsGetFresh<{ results: SpreadResult[] }>(`/api/fws/ap/incidents/${eventId}/spread-results`),
      ]);
      setRecon(r);
      setSpread(s.results ?? []);
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [eventId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const hasPoint = recon !== null && recon.lat !== null && recon.lng !== null;

  return (
    <Card
      title="지도 겹침"
      data-gx="fws-f4-01-map"
      extra={
        <Button size="small" onClick={() => void reload()} data-gx="fws-f4-01-map-refresh">
          지도 새로 보기
        </Button>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {failed ? <Text type="secondary">지도 자료를 불러오지 못했습니다</Text> : null}
        {hasPoint ? (
          <div data-gx="fws-f4-01-map-canvas">
            <Map
              center={{ lat: recon!.lat as number, lng: recon!.lng as number }}
              operatingMarkers={[{ lat: recon!.lat, lng: recon!.lng, name: '정찰 좌표' }]}
              style={{ height: '280px' }}
            />
          </div>
        ) : (
          <Text type="secondary" data-gx="fws-f4-01-map-nopoint">
            겹칠 정찰 좌표가 없습니다
          </Text>
        )}
        <div data-gx="fws-f4-01-map-recon">
          <Text strong>F5 정찰 좌표: </Text>
          {hasPoint ? (
            <Text>
              {recon!.lat}, {recon!.lng}
              {recon!.radius_m !== null ? ` · 반경 ${recon!.radius_m} m` : ''}
            </Text>
          ) : (
            <Text type="secondary">—</Text>
          )}
        </div>
        <div data-gx="fws-f4-01-map-spread">
          <Text strong>F6-04 확산예측 업로드 결과 (좌표 없음 — 참조만): </Text>
          <List
            size="small"
            dataSource={spread}
            locale={{ emptyText: '업로드된 결과가 없습니다' }}
            renderItem={(r) => (
              <List.Item>
                {r.image_ref}
                {r.arrival_note ? ` · ${r.arrival_note}` : ''}
                {r.uploaded_at ? ` · ${r.uploaded_at}` : ''}
              </List.Item>
            )}
          />
        </div>
        <div data-gx="fws-f4-01-map-evac">
          <Text strong>대피 구역 (마을 이름 — 경계 좌표 없음): </Text>
          <Text>{evacVillages.length > 0 ? evacVillages.join(', ') : '—'}</Text>
        </div>
      </Space>
    </Card>
  );
}
