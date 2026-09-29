/**
 * FWS F3 산림과 상황 — `/fws/office`.
 *
 * 턴 AN · WO-17 · 차선 N2 단독 소유(조율자가 빈 화면으로 세워 `App.tsx` 에 등록해 둠).
 * ★ 문구는 이 차선의 `../copy_office.ts` 에서 온다 — 공용 `../copy.ts` 는 이 턴에 고치지 않는다.
 */
import { Typography } from 'antd';

export default function OfficeHome() {
  return <Typography.Title level={3}>산림과 상황</Typography.Title>;
}
