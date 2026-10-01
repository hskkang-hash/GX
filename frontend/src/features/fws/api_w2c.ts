/**
 * 턴 AQ · 2물결 차선 W2C — 지휘(F2-01 자원 배치판 · F2-05 지원 요청 배지 · F1-10 철수
 * 지시)·드론(F5-08 비행 기록 재조회)이 부르는 경로.
 *
 * `./api.ts` 는 공용 파일이라 고치지 않는다 — 그 파일의 `fwsGetFresh`·`fwsPostQuery`
 * 를 그대로 쓴다(응답 해석은 한 곳).
 * 서버 짝: `backend/apps/fws/api.py::resource_board` · `api_command.py::order_withdrawal`
 * ·`withdrawal_orders` · `api.py::drone_flights_mine`.
 */
import { fwsGetFresh, fwsPostQuery } from './api';

export const fwsW2cEndpoint = {
  resourceBoard: (eventId: number | string) => `/api/fws/resources/board?event_id=${eventId}`,
  withdrawalOrder: (eventId: number | string) =>
    `/api/fws/command/incidents/${eventId}/withdrawal-order`,
  droneFlightsMine: '/api/fws/drone/flights/mine',
};

export type StandbyStatus = 'standby_day' | 'standby_night' | 'off_duty';

export interface ResourceBoardBody {
  standby: {
    people: Array<{
      user_id: number;
      name: string;
      status: StandbyStatus | null;
      location: { lat: number; lng: number } | null;
      set_at: string | null;
      /** F2-11 — 출동 중(deployed) · 철수해 해제됨(released) · 없음. */
      mission_state?: 'deployed' | 'released' | null;
      mission_event_id?: number | null;
      released_at?: string | null;
    }>;
    counts: Record<StandbyStatus, number>;
    on_standby: number;
    deployed?: number;
    released?: number;
  };
  support: {
    event_id: number;
    count: number;
    badges: Record<'personnel' | 'water' | 'helicopter' | 'heavy_equipment', number>;
    requests: Array<{ kind: string; amount: string | null; note: string | null; requested_at: string | null }>;
  } | null;
}

export interface WithdrawalOrdersBody {
  event_id: number;
  count: number;
  orders: Array<{ reason: string; delivered: number | null; ordered_at: string | null }>;
  latest: { reason: string; delivered: number | null; ordered_at: string | null } | null;
}

export interface DroneFlightRow {
  flight_id: number;
  event_id: number | null;
  source: string;
  airframe_code: string;
  battery_pct: number | null;
  flight_minutes: number | null;
  note: string;
  logged_at: string | null;
}

export function fetchResourceBoard(eventId: string): Promise<ResourceBoardBody> {
  return fwsGetFresh<ResourceBoardBody>(fwsW2cEndpoint.resourceBoard(eventId));
}

export function fetchWithdrawalOrders(eventId: string): Promise<WithdrawalOrdersBody> {
  return fwsGetFresh<WithdrawalOrdersBody>(fwsW2cEndpoint.withdrawalOrder(eventId));
}

export function sendWithdrawalOrder(eventId: string, reason: string, idempotencyKey: string) {
  return fwsPostQuery(fwsW2cEndpoint.withdrawalOrder(eventId), { reason }, idempotencyKey);
}

export function fetchMyFlights(): Promise<{ flights: DroneFlightRow[]; count: number }> {
  return fwsGetFresh<{ flights: DroneFlightRow[]; count: number }>(fwsW2cEndpoint.droneFlightsMine);
}
