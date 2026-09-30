/**
 * 산불 설정(U5) — 안전경보 문턱(기관 설정값) 호출 (턴 AQ · 차선 N4 · P-434).
 *
 * `../api.ts` 는 다른 차선 소유라 고치지 않고, 그 공개 함수만 부른다.
 * 저장 뒤 재조회는 캐시를 우회하는 `fwsGetFresh` 로 — 적중 캐시가 옛 값을 200 으로
 * 돌려주면 「저장됐는데 안 바뀐 것처럼」 보인다.
 */
import { fwsGetFresh, fwsPostQuery } from './api';

export const SAFETY_THRESHOLDS = '/api/fws/admin/safety-thresholds';

export type SafetyThresholdName =
  | 'wind_shift_angle_deg'
  | 'wind_shift_window_minutes'
  | 'drop_zone_exit_radius_m';

export interface SafetyThresholdField {
  name: SafetyThresholdName;
  value: number | null;
  unit: string;
  min_exclusive: number;
  max_inclusive: number | null;
  status: string;
}

export interface SafetyThresholdsBody {
  fields: SafetyThresholdField[];
  all_set: boolean;
  saved_at: string | null;
}

export function getSafetyThresholds(): Promise<SafetyThresholdsBody> {
  return fwsGetFresh<SafetyThresholdsBody>(SAFETY_THRESHOLDS);
}

export function saveSafetyThresholds(
  values: Record<SafetyThresholdName, number | null>,
): Promise<SafetyThresholdsBody> {
  const q: Record<string, string> = {};
  (Object.keys(values) as SafetyThresholdName[]).forEach((k) => {
    const v = values[k];
    q[k] = v == null ? '' : String(v);
  });
  return fwsPostQuery<SafetyThresholdsBody>(SAFETY_THRESHOLDS, q);
}
