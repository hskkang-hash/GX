/**
 * 턴 AQ · 차선 W2B — 팀장(U2)·U4 홈의 **판단·인계 줄**.
 *
 * 홈(`pages/Home.tsx`)에는 이 컴포넌트 한 줄만 끼운다. 역할마다 보이는 카드:
 *   U2(팀장) — 위기경보 띠 · 임계값 도달(DSM-U2-04) · 인계 확인(U2-05) ·
 *              상황판단회의(U2-03) · 위기경보 접수(U4-06)
 *   U4        — 위기경보 띠 · 임계값 도달(U2-04 — 명세가 「팀장·U4에게」라 적었다) ·
 *              위기경보 접수(U4-06)
 */
import { Col, Row } from 'antd';

import AlertLevelBand from './AlertLevelBand';
import AlertLevelCard from './AlertLevelCard';
import HandoverAckCard from './HandoverAckCard';
import SituationMeetingCard from './SituationMeetingCard';
import ThresholdAlertCard from './ThresholdAlertCard';

export default function DecisionHandoverRow({ bucket }: { bucket: string | null }) {
  if (bucket !== 'U2' && bucket !== 'U4') return null;
  return (
    <>
      <AlertLevelBand />
      <Row gutter={[12, 12]}>
        <Col xs={24} md={bucket === 'U2' ? 6 : 12}>
          <ThresholdAlertCard />
        </Col>
        {bucket === 'U2' ? (
          <Col xs={24} md={6}>
            <HandoverAckCard />
          </Col>
        ) : null}
        {bucket === 'U2' ? (
          <Col xs={24} md={6}>
            <SituationMeetingCard />
          </Col>
        ) : null}
        <Col xs={24} md={bucket === 'U2' ? 6 : 12}>
          <AlertLevelCard />
        </Col>
      </Row>
    </>
  );
}
