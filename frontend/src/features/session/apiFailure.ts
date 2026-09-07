/**
 * SEC-11a ② — **거절이 예외가 되는 날을 위한 한 줄.** (2026-09-07 턴 J · 차선 C)
 *
 * 왜 이 파일이 생겼나 [실측 2026-09-06 · 차선 S · `evidence/SEC-11a/턴G…md` §3]
 * ------------------------------------------------------------------------------
 * `features/Handover` · `features/otherEquipments` 에서 `await` 가 있는 파일 19개 중
 * **`try` 가 하나도 없는 파일이 11개**였다. 그 자리들은 전부 이 모양이다:
 *
 *     const { success, message } = await 어떤API(...);   // ← 거절되면 여기서 끝난다
 *     if (success) { … } else { ToastTopHelper.error(message); }
 *
 * 지금은 훅(`useHandover` 등)이 axios 예외를 잡아 `{success:false, message}` 로
 * 바꿔 주기 때문에 **대개** 거절이 여기까지 예외로 오지 않는다. 그런데 그 훅에도
 * 안 잡히는 갈래가 있고(`Promise.all`·폴링·훅 밖의 직접 호출), 무엇보다
 * **접두 승격이 켜지는 순간** 200 봉투로 오던 거절이 **진짜 예외**가 된다.
 * 그때 `try` 가 없는 자리는:
 *
 *   ① `setLoading(true)` 를 켜 놓고 **끄지 못한다** → 스피너 고착 (W0-18 §2-1)
 *   ② 아무 말도 안 한다 → 사람은 **자기가 안 눌렀다고 생각하고 또 누른다**
 *
 * 전역 `unhandledrejection` 처리기는 이 저장소에 **0건**이다 — 즉 삼킨 채로 조용하다.
 *
 * ★ **낱말을 만들지 않았다** (GX-COPY 규칙 1)
 * -------------------------------------------
 * 이 파일은 문장을 **한 줄도 새로 짓지 않는다.** 전부
 * `features/dsm/copy.ts` 가 이미 사전(`docs/design/GX-COPY_v1.md` §「불러오지 못한 자리」)
 * 에서 옮겨 온 줄이다. 여기서 하는 일은 **axios 의 예외 모양을 그 함수가 아는 모양으로
 * 옮기는 것**뿐이다. 사전에 없는 자리를 만들면 화면과 사전이 갈라진다.
 *
 * ⚠ **원문을 화면에 그리지 않는다.** `Network Error` · `Request failed with status code 403`
 *   같은 axios 원문은 사용자의 말이 아니다 — `userFacingError` 안의 `looksRaw` 가 거른다.
 */
import { FORBIDDEN_TITLE, FAILURE_TITLE, userFacingError } from '@/features/dsm/copy';

/** 서버가 보낸 사유. dj-core 는 문자열로도, 다국어 객체로도 보낸다. */
function serverSentence(data: unknown): string | null {
  const raw = (data as { message?: unknown; detail?: unknown } | null) ?? null;
  const cand = raw?.message ?? raw?.detail;
  if (typeof cand === 'string' && cand.trim()) return cand;
  if (cand && typeof cand === 'object') {
    const m = cand as Record<string, unknown>;
    for (const key of ['ko', 'en']) {
      const v = m[key];
      if (typeof v === 'string' && v.trim()) return v;
    }
  }
  return null;
}

/**
 * 잡은 예외 하나를 **화면에 그려도 되는 한 줄**로 옮긴다.
 *
 * @param where 어디서 났나. 콘솔에만 나간다(`reportFailure`) — 화면에는 안 나간다.
 */
export function failureLine(where: string, error: unknown): string {
  const status = (error as { response?: { status?: number } } | null)?.response?.status;
  const sentence = serverSentence(
    (error as { response?: { data?: unknown } } | null)?.response?.data,
  );

  //: `userFacingError` 는 「서버가 쓴 문장인가」를 `fromServer` 로 묻고,
  //: 원문 표식이 섞이면 버린다. 그 판정을 여기서 다시 짓지 않고 **그대로 쓴다.**
  const shaped = Object.assign(new Error(sentence ?? ''), {
    status,
    fromServer: Boolean(sentence),
  });
  //: 제목은 갈래로 갈린다 — 403·401 은 「오류」가 아니라 **권한**이다(DA-03 §2-5).
  const title = status === 403 || status === 401 ? FORBIDDEN_TITLE : FAILURE_TITLE;
  return userFacingError(where, shaped, title);
}
