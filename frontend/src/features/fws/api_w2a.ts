/**
 * 턴 AQ · 2물결 차선 W2A — 감시원(F1)·진화대(F2) 화면이 새로 부르는 면.
 *
 * 공용 `./api.ts` 는 고치지 않는다(한 파일은 한 차선) — 경로·조립 함수는 거기 것을
 * 그대로 쓰고, 이 파일은 **새 경로 둘과 파일 두 갈래**(사진 올리기 · CSV 받기)만 더한다.
 * 응답 해석은 `../dsm/adapter::unwrap` 한 곳이다(P-129 · D-212).
 */
import API from '@/services/API';

import { unwrap } from '../dsm/adapter';
import { fwsGetBlob } from './api';

export const fwsW2aEndpoint = {
  /** F2-12 내 임무 이력 CSV(수당 근거) — `apps/fws/api.py::my_missions_export`. */
  missionsMineExport: '/api/fws/missions/mine/export',
  /** F1-06 「+ 사진 1」 — DSM 현장 사진 문을 그대로 쓴다(`apps/dsm/api_u3.py::upload_field_photo`). */
  fieldPhoto: (eventId: number | string) => `/api/dsm/events/${eventId}/field-photo`,
};

/** 사진 한 장을 올리고 서버가 준 번호를 돌려준다. `Content-Type` 은 손으로 적지 않는다(boundary). */
export async function uploadFieldPhoto(eventId: number | string, file: File): Promise<number> {
  const form = new FormData();
  form.append('photo', file);
  const res = unwrap<{ photo_id: number }>(await API.post(fwsW2aEndpoint.fieldPhoto(eventId), form));
  if (!res.ok || res.data === null) {
    throw new Error(res.message ?? '사진을 올리지 못했습니다');
  }
  return res.data.photo_id;
}

/** 내 임무 이력 CSV 를 받아 이 기기에 저장한다. */
export async function downloadMyMissionsCsv(): Promise<void> {
  const blob = await fwsGetBlob(fwsW2aEndpoint.missionsMineExport);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'my-missions.csv';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** 이 기기의 지금 위치 한 점 — 못 얻으면 던진다(값을 지어내지 않는다). */
export function currentPosition(): Promise<{ lat: number; lng: number }> {
  return new Promise((resolve, reject) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      reject(new Error('no-geolocation'));
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => reject(err),
      { enableHighAccuracy: true },
    );
  });
}
