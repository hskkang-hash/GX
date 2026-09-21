/**
 * **M2 — 현장 상세** (U3 #2 · #3 · #7).
 *
 * 이동 중인 사람이 묻는 넷에 답한다:
 *   ① 무엇이 일어났나   유형 · 등급 · 발생 시각 · 대응 진행
 *   ② 어디로 가나       카메라 이름 · 설치 주소(`address_status` 로 부재를 가른다)
 *   ③ 무엇을 보나       스냅샷 참조 · 구간 티켓(**참조까지만** — 계약 11조 잠금)
 *   ④ 무엇을 누르나     상태 전이 (접수 확인 / 조치 중 / 종결 / 오탐)
 *
 * ★ 목록에서 값을 물려받지 않고 **서버에 다시 묻는다.** 물려 쓰면 문지기가 목록에만
 *   서고 상세에는 안 선다 — 그 자리가 IDOR 이 태어나는 자리다.
 *
 * ★ 전이표를 화면이 들지 않는다. 서버가 준 `allowed_next` 만 그린다 — 화면이 표를
 *   따로 들면 **서버가 거절하는 버튼**을 그리게 된다 (D-399).
 *
 * ★★ [P-121 · 2026-09-10 턴 O · 실측] **사진을 그린다. 문은 이미 서 있었다.**
 *
 *   앞판의 주석은 「스냅샷 바이트를 내보내는 라우트가 없다」였다(2026-09-04).
 *   그 뒤 P-25 가 `GET /api/dsm/events/{id}/snapshot` 을 세웠고 — 인증 뒤에 서고
 *   소인이 찍혀 나오는, 무계정 링크가 아닌 문이다 — 그런데 **이 화면은 그 사실을
 *   모른 채로 남았다.** 그래서 화면에는 이렇게 떠 있었다:
 *
 *       「휴대전화 화면에서 여는 길이 아직 열리지 않았습니다 —
 *         관제 화면에서 확인하십시오.」
 *
 *   두 문장 다 거짓이었다. 길은 열려 있었고, **관제 화면도 같은 이유로 사진을
 *   못 그리고 있었다**(P-121 ① — `res.data` 가 Blob 이 아니었다). 즉 이 안내는
 *   고장 하나를 가리키며 **다른 고장으로 사람을 보내는 표지판**이었다.
 *   현장으로 가는 사람이 차를 세우고 관제에 전화를 건다 — 거기서도 못 본다.
 *
 *   지운 것은 문장이고, 그 자리에 선 것은 `EventSnapshot` — 관제 화면과 **같은
 *   부품**이다. 두 벌로 두지 않는다: 갈리는 쪽은 언제나 오류 처리다.
 *
 * ★★ **M3 현장 회신이 이 화면에 섰다** [2026-09-05 · 차선 C].
 *   앞판의 주석은 「문이 없어서 손잡이를 안 그렸다」였는데, **문은 이미 서 있었다**
 *   (`POST /api/dsm/events/{id}/field-reply` · `GET …/field-replies`).
 *   즉 없던 것은 문이 아니라 **손잡이**였고, 그동안 화면은 「보낼 수 없습니다」라고
 *   사실과 다른 말을 하고 있었다 — 잠자는 기능의 화면판이다.
 *   ★ 회신은 **계정이 남긴다.** 무계정 링크로 부를 수 있는 자리를 만들지 않는다.
 *   ★ 한 줄이다. 사진 첨부는 이 문의 칸이 아니다 — 없는 칸에 손잡이를 그리지 않는다.
 *
 * ★★ **전화 버튼을 그리지 않았다** [실측 2026-09-05 · 차선 C].
 *
 *   청한 것은 「이동 중인 사람이 현장·관제에 한 번에 거는 자리」였고, 그 자리는
 *   옳다 — 차를 몰고 가는 사람에게 `tel:` 한 번은 화면 다섯 번보다 낫다.
 *   그런데 **걸 번호가 이 제품 어디에도 없다.** 어디를 봤는지 그대로 적는다:
 *
 *     ① 이 화면이 손에 쥔 값 — `GET /api/dsm/events/{id}` 의 응답. 커널의
 *        `EventView` 가 그 전부이고(유형·등급·판정·시각·카메라·좌표·주소·
 *        스냅샷·대응 단계·`allowed_next`), **연락처 칸이 없다.**
 *     ② 갈 곳의 주인 — `StreamMonitor`. `install_address` 와
 *        `install_address_detail` 은 있는데 **전화 칸이 없다.** 카메라는 자기가
 *        선 자리를 알지, 그 자리를 지키는 사람을 모른다.
 *     ③ 알림을 받는 사람 — K2 의 `Recipient`. `address` 는 있지만 그것은
 *        **채널 주소**(메일 주소 · 웹훅)이고 통화가 닿는 번호가 아니다.
 *        `channel` 에 통화가 없다.
 *     ④ 저장소 전체에서 전화 칸을 가진 모델은 **배송 쪽**뿐이다(수취인·발송인).
 *        그것은 이 제품의 사건과 아무 관계가 없고, 게다가 그 자리는 손대지 않는
 *        구역이다. **가까이 있다고 해서 맞는 번호가 되지 않는다.**
 *
 *   그래서 안 그렸다. 번호 없이 단추만 그리면 세 갈래로 나빠진다 —
 *   눌러도 아무 일이 없거나(죽은 손잡이), 빈 `tel:` 로 전화 앱만 열리거나,
 *   **화면이 어딘가에 번호가 있다고 사람을 믿게 만든다.** 셋째가 가장 나쁘다:
 *   현장으로 가는 사람이 「연락은 저기서 하면 되겠다」고 계획을 세우고, 그 계획이
 *   틀렸다는 것을 **차 안에서** 알게 된다. 이 파일이 스냅샷과 사진 첨부에서
 *   이미 지킨 규약이 그것이다 — **없는 것에 손잡이를 그리지 않는다.**
 *
 *   ⚠ 그러므로 이것은 「안 했다」가 아니라 **「걸 곳이 없다」**로 넘긴다.
 *     문이 서려면 번호가 먼저 있어야 한다. 번호가 살 자리의 후보는 둘이고,
 *     **어느 쪽인지가 제품 판단**이라 화면이 정할 것이 아니다:
 *       ⓐ 카메라마다 — 그 자리를 지키는 사람. 「현장에 건다」에 맞는다.
 *       ⓑ 테넌트마다 하나 — 관제 대표번호. 「관제에 건다」에 맞는다.
 *     ⓑ 가 한 칸으로 서고 ⓐ 는 카메라 수만큼 채워 넣어야 한다 — 비어 있는
 *     ⓐ 는 다시 「없는 것에 그린 손잡이」가 된다. 판단을 청한다.
 *
 * ★★ **지도 앱 링크를 그렸다** [P-141 · 2026-09-15 턴 Q · 차선 U3].
 *
 *   UX-45 원문: 「주소 · 지도 앱 링크(`geo:`/카카오맵 URL)」. 전화 버튼과 달리
 *   이 칸은 **있는 칸으로만** 선다 — `e.lat`·`e.lng`(좌표, F-09 상세가 이미 낸다)와
 *   `e.address`(사람이 읽는 위치, FX-5)가 그것이다. 새 서버 칸을 열지 않았다.
 *
 *   ★ `geo:` 를 안 쓰고 **카카오맵 웹 링크**로 갔다. `geo:` 는 iOS Safari 가
 *     알아듣지 못한다(지도 앱이 없으면 그냥 죽은 링크) — 이동 중인 사람의 기기가
 *     무엇인지 화면은 모른다. 카카오맵 링크는 앱이 있으면 앱을, 없으면 웹을 연다 —
 *     두 플랫폼에서 **똑같이 산다.**
 *   ★ 좌표가 있으면 지도에 **정확한 점**을 찍는다(`map/link/map`). 좌표가 없고
 *     주소만 있으면 **검색**으로 연다(`map/link/search`) — 검색은 점보다 부정확하지만
 *     주소마저 없는 것보다는 낫다. 둘 다 없으면 링크 자체를 그리지 않는다
 *     (`address_status` 문장이 이미 그 부재를 적고 있다 — 두 번 말하지 않는다).
 *   ★ 새 탭/외부 앱으로 연다(`target="_blank"`) — 이 화면을 잃지 않는다. 이동 중인
 *     사람이 지도를 본 뒤 다시 돌아와 다음 버튼을 눌러야 한다.
 */
import { Button, Card, Collapse, Descriptions, Input, Modal, Space, Tag, Typography, message } from 'antd';
import type { ChangeEvent } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import EventSnapshot from '../../dsm/components/EventSnapshot';
import StateBoundary from '../../dsm/components/StateBoundary';
import { useDsmResource } from '../../dsm/hooks/useDsmResource';
import ResponseSteps, { VerdictBadge } from '../../dsm/components/ResponseSteps';
import {
  advanceLabel,
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../../dsm/severity';
import { absolute, relative } from '../../dsm/time';
import {
  dsmGet,
  dsmPostForm,
  DsmApiError,
  intentKey,
  mobileEndpoint,
  mobilePostWithQueryOnce,
} from '../api';
import { userFacingError } from '@/features/dsm/copy';
import MobileShell, { TOUCH_MIN } from '../components/MobileShell';
import { finishReceiveToAck, markOpened } from '../metrics';
import { mobileRoutes } from '../routes';
import { mobileEventDetailPath } from '../routes';
import type { ClipTicket, EventDetailView, EventRow } from '../types';

const { Text, Paragraph } = Typography;

/**
 * ★ [UX-22 · 2026-09-26] **이름표를 사전(`dsm/severity.ts`)에서 가져온다.**
 *   여기 따로 든 표는 관제 화면과 다른 말을 쓰고 있었다 — 같은 칸이 관제에서는
 *   「종결」, 휴대전화에서는 「완료(종결)」였다. 한 사건을 두 사람이 다른 이름으로
 *   부르면 교대 인계에서 말이 어긋난다. **표 자체는 여전히 서버 것이다.**
 */

const ADDRESS_STATUS_LABEL: Record<string, string> = {
  resolved: '조회됨',
  pending: '조회 대기',
  disabled: '조회 대상 아님 (좌표 없음)',
};

/**
 * 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다.
 * ⚠ 이 상수를 고치면 `scripts/capture_screens.py` 의 사본도 **같은 커밋에서** 고친다.
 */
export const FIELD_REPLY_HEADLINE = '현장 회신 — 본 것을 한 줄로';

/**
 * [P-148·UX-45 · 턴 R] M3 사진 섹션 표제. 캡처가 이 글자를 보고 찍는다 —
 * 고치면 `scripts/capture_screens.py` 사본도 같은 커밋에서 고친다.
 */
export const FIELD_PHOTO_HEADLINE = '현장 사진 — 한 장 올리기';

/** [턴 T] 「이 카메라 7일」 절의 표제와 창. 서버 필터(`stream_monitor_id` + `since`)로 좁힌다. */
export const SAME_CAMERA_HEADLINE = '이 카메라 7일';
const SAME_CAMERA_DAYS = 7;
const SAME_CAMERA_LIMIT = 20;

/** 사진이 받는 형식 셋 — `backend/apps/dsm/field.py::ALLOWED_CONTENT_TYPES` 와 같다. */
const FIELD_PHOTO_ACCEPT = 'image/jpeg,image/png,image/webp';

/** 지도 버튼의 말. GX-COPY_v1.md §5 「2026-09-15 턴 Q 추가」와 같은 문구다. */
export const MAP_LINK_LABEL = '지도에서 보기';

/**
 * ③ [턴 AA · U3 · 세종 §3 6번] **「서버가 404」는 고객 말이 아니다.**
 *
 * 종전 글자: 「이 사건에는 영상 구간 참조가 없습니다 (서버가 404 로 답했습니다 —
 * 고장이 아닙니다).」 — **정직하지만 우리 말이다.** `404` 는 우리 서랍의 번호이고
 * (GX-COPY 규칙 3), 「고장이 아닙니다」는 **고장을 먼저 떠올리게 하는 부정문**이다.
 * 현장에서 폰을 든 사람이 그 줄에서 알아야 할 것은 둘뿐이다 —
 * **왜 없는가**와 **그러면 지금 무엇을 하는가.** 이번 턴 불변이 그 둘을
 * **같은 줄에** 두라고 못 박았다.
 *
 * ★ 갈래가 둘인 이유 — **「실제 값이 없는 문구는 비표시」**(턴 AA 불변).
 *   스냅샷이 없는 사건에서 「위의 스냅샷으로 확인하십시오」는 **없는 것을 가리키는
 *   손가락**이다. 그것은 P-121 이 지운 「관제 화면에서 확인하십시오」와 같은 병이다 —
 *   고친 자리에 같은 병을 다시 심지 않는다. 그래서 다음 손은 **이 화면에 실제로
 *   서 있는 손잡이**만 가리킨다: 스냅샷이 있으면 스냅샷, 없으면 「현장 회신」.
 * ★ **접는 규율은 안 바꿨다.** 404 만 빈 것으로 접고 403·500 은 그대로 오류다
 *   (아래 `clip` 머리말). 바뀐 것은 **빈 자리에 적는 글자**뿐이다.
 * ★ GX-COPY 에 아직 없는 말이라 **조율자에게 등재를 청했다**
 *   (`docs/agent/checkpoints/turn-aa/조율자.inbox/U3.md`). 「저장된 구간이 없습니다」는
 *   세종 §3 6번이 지정한 낱말 그대로다.
 */
export const CLIP_EMPTY_HEAD = '저장된 구간이 없습니다';
export const CLIP_EMPTY_WITH_SNAPSHOT =
  `${CLIP_EMPTY_HEAD} — 이 사건은 영상이 저장되지 않았습니다. 위의 「스냅샷」으로 확인하십시오.`;
export const CLIP_EMPTY_NO_SNAPSHOT =
  `${CLIP_EMPTY_HEAD} — 이 사건은 영상이 저장되지 않았습니다. 현장에서 본 것을 아래 「현장 회신」에 적어 주십시오.`;

/**
 * 사건 위치를 여는 카카오맵 링크를 만든다. **있는 칸만** 쓴다 — 지어내지 않는다.
 * 좌표가 있으면 점(`map/link/map`), 좌표는 없고 주소만 있으면 검색(`map/link/search`),
 * 둘 다 없으면 `null`(화면은 아무것도 그리지 않는다).
 */
export function mapLinkUrl(
  lat: number | null | undefined,
  lng: number | null | undefined,
  address: string | null | undefined,
): string | null {
  if (lat != null && lng != null) {
    return `https://map.kakao.com/link/map/사건위치,${lat},${lng}`;
  }
  const trimmed = address?.trim();
  if (trimmed) {
    return `https://map.kakao.com/link/search/${encodeURIComponent(trimmed)}`;
  }
  return null;
}

/**
 * 회신 한 줄. **`kind` 는 서버가 실제로 내는 칸이다** (2026-09-16 · 턴 S).
 *
 * ★ [실측] `GET /api/dsm/events/{id}/field-replies` 가 줄마다 `kind`·`kind_label` 을
 *   싣고, 봉투에 `by_kind` 를 함께 낸다(`backend/apps/dsm/api.py::field_replies` ·
 *   `tests/test_u3_field_reply_kind.py::test_the_list_counts_by_kind_with_its_denominator`).
 *   그 사실을 **타입에 적는다** — 화면이 읽는 칸이 타입에 없으면 컴파일이 막히거나
 *   `any` 로 새고, 새면 서버가 그 칸을 지우는 날 화면이 조용히 `undefined` 를 센다.
 * ★ `text` 는 **접두가 걷힌 본문**이다. 접두(`[FIELD:support]`)는 서버가 떼고 보낸다.
 */
interface FieldReplyRow {
  reply_id: number;
  text: string;
  author_name: string;
  kind: string;
  kind_label: string;
}

/**
 * 회신 목록의 봉투. `by_kind` 가 M3 상태 칸의 출처다.
 *
 * ⚠ `total` 도 `by_kind` 도 **이 페이지의 수**다(서버가 `limit` 을 받는다) —
 *   모수와 함께 읽는다(D-301). 화면이 「지원 요청 0건」이라 적을 때 그것이
 *   「없음」인지 「이 페이지 밖」인지는 `total` 이 말한다.
 */
interface FieldReplyPage {
  total: number;
  by_kind: Record<string, number>;
  replies: FieldReplyRow[];
}

export default function MobileEventDetail() {
  const { id } = useParams<{ id: string }>();
  const [busy, setBusy] = useState('');
  const [replyText, setReplyText] = useState('');

  const event = useDsmResource<EventDetailView>(
    () => dsmGet<EventDetailView>(mobileEndpoint.eventDetail(id!)),
    [id],
    { enabled: Boolean(id) },
  );

  /**
   * 편리성 #5 — **「열었다」의 시각.** 상세가 실제로 뜬 순간이다.
   *
   * ★★ [턴 V] **여기서 시계를 멈추지 않는다.** 열기는 끝이 아니라 **탭 한 번**이고,
   *   시계는 아래 「접수하기」가 서버에 기록된 때 멈춘다 — PRD §6 의 5번이 재기로 한
   *   것이 「문자 수신 → 접수 회신」이기 때문이다(`metrics.ts` 머리말 ★★).
   *   열기에서 멈춘 시계는 언제나 더 작은 수를 내므로, 그 수로 5번 칸을 채우면
   *   목표를 쉬운 것으로 바꿔 초록을 만드는 일이 된다.
   */
  useEffect(() => {
    if (id && event.data) markOpened(id);
  }, [id, event.data]);

  /**
   * 구간 티켓은 **부수적**이다. 없어도 상세는 선다.
   *
   * ★★ [실측 2026-09-04] 구간 참조가 없는 이벤트에서 이 문은 **404** 를 낸다.
   *   404 를 그대로 오류로 그리면 화면이 「불러오지 못했습니다」라고 빨갛게 말하는데,
   *   실제로 일어난 일은 **「이 사건에는 녹화가 없다」는 정상 부재**다. 둘을 같은
   *   그림으로 그리는 것이 DA-03 §2-5 가 금지한 모양이다 — 빈 것은 기다릴 것이 없고
   *   오류는 다시 시도할 것이 있다. 그래서 404 만 **빈 것**으로 접는다.
   *   ⚠ 다른 상태 코드는 접지 않는다. 403·500 을 함께 접으면 「권한이 없다」와
   *     「서버가 죽었다」가 「없다」로 보인다.
   */
  const clip = useDsmResource<ClipTicket | null>(
    () =>
      dsmGet<ClipTicket>(mobileEndpoint.clip(id!)).catch((err: unknown) => {
        if (err instanceof DsmApiError && err.status === 404) return null;
        throw err;
      }),
    [id],
    { enabled: Boolean(id), isEmpty: (v) => v === null },
  );

  /** 대응 진행 한 칸. 되돌림(종결 → 조치중)은 **사유가 필수**다 — 서버가 400 으로 거절한다. */
  const advance = useCallback(
    async (toState: string, backward: boolean) => {
      if (!id) return;
      const send = async (reason: string) => {
        setBusy(toState);
        try {
          // ★ **접수·처리 단계 — 멱등 키를 싣는 문 ②**(휴대전화 쪽).
          //   이동 중인 사람의 화면이라 두 번 눌릴 확률이 가장 높은 자리다.
          await mobilePostWithQueryOnce(
            mobileEndpoint.response(id),
            { to_state: toState, reason },
            intentKey(`m.response:${id}:${toState}`),
          );
          // ★ 편리성 #5 — **시계는 여기서 멈춘다.** 「접수」가 서버에 기록된 뒤다.
          //   누른 때가 아니라 **성공한 뒤**여야 거절된 접수가 수에 안 들어간다.
          if (id && toState === 'acknowledged') finishReceiveToAck(id);
          message.success(`「${labelOf(RESPONSE_STATE_LABEL, toState)}」 단계로 옮겼습니다.`);
          event.reload();
        } catch (err) {
          message.error(
            userFacingError('MobileEventDetail.advance', err, '처리 단계를 옮기지 못했습니다.'),
          );
          throw err; // 모달을 닫지 않는다 — 실패했는데 닫히면 성공처럼 보인다
        } finally {
          setBusy('');
        }
      };

      if (!backward) {
        await send('');
        return;
      }

      let reason = '';
      Modal.confirm({
        title: '되돌립니다 — 사유가 필요합니다',
        content: (
          <Input.TextArea
            rows={3}
            placeholder="되돌리는 사유 (필수)"
            onChange={(ev) => {
              reason = ev.target.value;
            }}
          />
        ),
        okText: '되돌리기',
        cancelText: '취소',
        onOk: () => send(reason),
      });
    },
    [id, event],
  );

  /**
   * [턴 T · P-164 U3] 「이 카메라 7일」 — 같은 카메라의 지난 7일 사건.
   * **새 라우트가 아니다** — 기존 목록(`GET /api/dsm/events`)에 `stream_monitor_id` +
   * `since` 필터다. 서버가 좁힌다(화면이 받아 거르면 페이지 밖 사건이 없는 것이 된다).
   * 상세가 서기 전(카메라 번호를 모를 때)에는 부르지 않는다.
   */
  const cameraId = event.data?.stream_monitor_id ?? null;
  const sameCamera = useDsmResource<{ total: number; events: EventRow[] }>(
    () =>
      dsmGet<{ total: number; events: EventRow[] }>(mobileEndpoint.events, {
        stream_monitor_id: String(cameraId),
        since: new Date(Date.now() - SAME_CAMERA_DAYS * 24 * 3600 * 1000).toISOString(),
        limit: SAME_CAMERA_LIMIT,
      }),
    [cameraId],
    { enabled: cameraId !== null, isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
  );

  /** M3 — 이 이벤트에 달린 현장 회신. 빈 것과 오류를 갈라 그린다. */
  const replies = useDsmResource<FieldReplyPage>(
    () => dsmGet(mobileEndpoint.fieldReplies(id!)),
    [id],
    { enabled: Boolean(id), isEmpty: (v) => (v?.replies?.length ?? 0) === 0 },
  );

  /**
   * M3 — 회신 한 건. **종류(`kind`)가 곧 시트의 어느 칸인가**다 (UX-45 여섯 칸).
   *
   * ★ 질의로 보낸다(본문이면 422 · 인자 없음). 조립은 `mobilePostWithQuery` 한 곳이다.
   * ★ 종류마다 멱등 키가 다르다 — 「도착」을 눌러 놓고 「지원 요청」을 누르면 그것은
   *   **다른 의도**이고, 같은 키로 묶이면 두 번째 누름이 첫 번째의 답을 받는다.
   * ★ 참을 돌려주면 보낸 것이다 — 부르는 쪽이 그 뒤에 무엇을 할지 정한다(상태 전이 ·
   *   글상자 비우기). 실패했는데 다음 걸음이 일어나면 화면이 거짓말을 한다.
   */
  const postReply = useCallback(
    async (kind: string, text: string, busyKey: string): Promise<boolean> => {
      if (!id) return false;
      setBusy(busyKey);
      try {
        // ★ **현장 회신 — 멱등 키를 싣는 문 ③.**
        await mobilePostWithQueryOnce(
          mobileEndpoint.fieldReply(id),
          text ? { kind, text } : { kind },
          intentKey(`m.field-reply:${id}:${kind}:${text}`),
        );
        replies.reload();
        return true;
      } catch (err) {
        message.error(
          userFacingError('MobileEventDetail.fieldReply', err, '회신을 보내지 못했습니다.'),
        );
        return false;
      } finally {
        setBusy('');
      }
    },
    [id, replies],
  );

  /**
   * 서버가 **허락한 전이만** 태운다. 화면이 전이표를 들지 않는다 —
   * 들면 서버가 거절하는 버튼을 그리게 된다(D-399 · 이 파일 머리말).
   *
   * ★ 그래서 「도착」·「조치 완료」는 **두 가지 일**을 한다: 회신은 **언제나** 남고,
   *   상태 전이는 **허락될 때만** 일어난다. 이미 조치 중인 사건에서 「도착」을 눌러도
   *   회신은 남아야 한다 — 그것이 관제가 기다리는 사실이기 때문이다.
   */
  const advanceIfAllowed = useCallback(
    async (toState: string) => {
      if (!(event.data?.allowed_next ?? []).includes(toState)) return;
      try {
        await advance(toState, false);
      } catch {
        /* 사유는 `advance` 가 이미 사람의 말로 적었다 — 두 번 말하지 않는다. */
      }
    },
    [event.data, advance],
  );

  /** ③ 한 줄 — 본문이 필수인 칸이다(서버가 빈 본문을 거절한다). */
  const sendFieldReply = useCallback(async () => {
    const text = replyText.trim();
    if (!text) return;
    if (await postReply('note', text, 'field-reply')) {
      setReplyText('');
      message.success('회신을 보냈습니다.');
    }
  }, [postReply, replyText]);

  /**
   * ① 도착 — 「현장에 왔다」. 글상자에 적은 것이 있으면 **그것을 함께** 보낸다.
   *
   * ★ 글상자를 종류마다 따로 두지 않는 이유: 이동 중인 사람의 화면에 입력칸이 여섯이면
   *   어디에 적어야 할지가 새 장애물이 된다. 칸은 하나이고, **어느 단추를 누르는가**가
   *   그 글의 뜻을 정한다.
   */
  const reportArrived = useCallback(async () => {
    const text = replyText.trim();
    if (await postReply('arrived', text, 'arrived')) {
      setReplyText('');
      message.success('도착을 기록했습니다.');
      await advanceIfAllowed('in_progress');
    }
  }, [postReply, replyText, advanceIfAllowed]);

  /** ⑤ 지원 요청 — U1 큐가 받는 짝이다(배지는 관제 쪽에서 뜬다). */
  const requestSupport = useCallback(async () => {
    const text = replyText.trim();
    if (await postReply('support', text, 'support')) {
      setReplyText('');
      message.success('지원을 요청했습니다.');
    }
  }, [postReply, replyText]);

  /** ⑥ 조치 완료 — 회신을 남기고, 서버가 허락하면 종결까지 간다. */
  const reportDone = useCallback(async () => {
    const text = replyText.trim();
    if (await postReply('done', text, 'done')) {
      setReplyText('');
      message.success('조치 완료를 기록했습니다.');
      await advanceIfAllowed('closed');
    }
  }, [postReply, replyText, advanceIfAllowed]);

  /**
   * M3 — 사진 한 장 올리기 (UX-45 · 2026-09-16 턴 R). 문은 이미 턴 Q 에 섰다
   * (`POST …/field-photo`) — 이번 턴은 **화면 배선**이다. **선택**이다 — 실패해도
   * 다음 단계(한 줄 · 완료)로 그대로 간다(design 문서 §2 「강제하면 새 장애물」).
   */
  const photoInputRef = useRef<HTMLInputElement>(null);
  const [photoBusy, setPhotoBusy] = useState(false);
  const [photoCount, setPhotoCount] = useState(0);

  const pickFieldPhoto = useCallback(() => {
    photoInputRef.current?.click();
  }, []);

  const uploadFieldPhoto = useCallback(
    async (file: File) => {
      if (!id) return;
      setPhotoBusy(true);
      try {
        const form = new FormData();
        // ★ 필드 이름은 서버와 같아야 한다 — `api_u3.py::upload_field_photo` 의
        //   `photo: UploadedFile = File(...)`.
        form.append('photo', file);
        await dsmPostForm(mobileEndpoint.fieldPhoto(id), form);
        setPhotoCount((n) => n + 1);
        message.success('사진을 올렸습니다.');
        /*
          ★★ [턴 S] 사진이 올라간 **뒤에** 회신 한 줄을 남긴다(`kind=photo`).

          왜 필요한가: 사진 행(`dsm_field_photo`)은 섰지만 **그것을 읽는 문이 아직
          없다**(`apps/dsm/field.py` 머리말 — 읽기 문은 다음 파). 그래서 관제 쪽
          타임라인에는 「사진이 올라왔다」가 아무 데도 안 나타난다. 회신 한 줄이
          그 사실을 **지금 있는 문으로** 전한다.
          ⚠ 업로드가 성공한 뒤에만 남긴다 — 실패했는데 「사진을 올렸습니다」가
            타임라인에 남으면 관제가 없는 사진을 기다린다.
        */
        await postReply('photo', '', 'photo');
      } catch (err) {
        message.error(
          userFacingError('MobileEventDetail.fieldPhoto', err, '사진을 올리지 못했습니다.'),
        );
      } finally {
        setPhotoBusy(false);
      }
    },
    [id, postReply],
  );

  const onFieldPhotoChosen = useCallback(
    (ev: ChangeEvent<HTMLInputElement>) => {
      const file = ev.target.files?.[0];
      ev.target.value = ''; // 같은 파일을 다시 골라도 change 가 다시 뜨게 비운다
      if (file) void uploadFieldPhoto(file);
    },
    [uploadFieldPhoto],
  );

  /**
   * M3 — 오탐 회신 「가 보니 아무것도 없다」(UX-45 5행). **새 문이 아니다** —
   * 관제 화면(`EventDetail.tsx`)의 「오탐으로 판정」과 같은 `review` 다. 도착·접수는
   * 이미 별도 버튼으로 끝났으므로 U1 큐 카드의 트랜잭션과 겹치지 않게 **단독 호출**만 쓴다.
   */
  const reportFalsePositive = useCallback(async () => {
    if (!id) return;
    /*
      ★ 고정 사유 + **사람이 덧붙인 한 줄**(설계 1쪽 §1 5행 「고정 사유 버튼 하나」).
        글상자가 비어 있어도 눌리는 이유: 「가 보니 아무것도 없음」 자체가 사유이고,
        그것을 매번 손으로 적게 하면 이동 중인 사람 앞에 새 장애물이 선다.
    */
    const detail = replyText.trim();
    const reason = detail
      ? `현장 확인 — 가 보니 아무것도 없음 · ${detail}`
      : '현장 확인 — 가 보니 아무것도 없음';

    setBusy('false-positive');
    try {
      // ★ **오탐 회신 — 멱등 키를 싣는 문 ④.**
      await mobilePostWithQueryOnce(
        mobileEndpoint.review(id),
        { verdict: 'rejected', reason },
        intentKey(`m.review:${id}:rejected`),
      );
    } catch (err) {
      message.error(
        userFacingError('MobileEventDetail.falsePositive', err, '오탐 기록을 보내지 못했습니다.'),
      );
      setBusy('');
      return;
    }
    setBusy('');

    /*
      ★★ 판정(`review`)과 회신(`field-reply`)은 **다른 축**이다 — 판정은 K6 오탐률의
        분자로 가고, 회신은 관제 타임라인에 남는다. 둘 다 있어야 「현장이 가서 확인했다」가
        관제 화면에서 보인다(판정만 남기면 수는 움직이는데 **아무 말도 안 남는다**).
      ⚠ 판정이 실패하면 여기 오지 않는다 — 회신만 남아 「오탐이라 했는데 오탐률은
        그대로」가 되는 자리를 만들지 않는다.
    */
    if (await postReply('false_positive', reason, 'false-positive')) {
      setReplyText('');
    }
    message.success('오탐으로 기록했습니다.');
    event.reload();
  }, [id, event, replyText, postReply]);

  const e = event.data;

  return (
    <MobileShell
      title={e ? `#${e.event_id} 현장 상세` : '현장 상세'}
      loadedAt={event.loadedAt}
      onReload={event.reload}
      backTo={mobileRoutes.inbox.path}
    >
      <StateBoundary
        state={event.state}
        reason={event.reason} status={event.status}
        onRetry={event.reload}
        emptyText="이벤트를 찾지 못했습니다."
      >
        {e ? (
          <Space
            direction="vertical"
            size={10}
            style={{ width: '100%' }}
          >
            {/* ① 무엇이 일어났나 */}
            <Card
              size="small"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={6}
                style={{ width: '100%' }}
              >
                <Space
                  size={6}
                  wrap
                >
                  <Tag color={SEVERITY_COLOR[e.severity]}>
                    {SEVERITY_ICON[e.severity]} {labelOf(SEVERITY_LABEL, e.severity)}
                  </Tag>
                  <Text strong>{labelOf(EVENT_TYPE_LABEL, e.event_type)}</Text>
                  {/* ★ [UX-22 · 2026-09-26] 진위 축(`status`) 태그를 내렸다 — 판정과
                      같은 것을 다른 이름으로 부르던 칸이라 한 카드에 둘이 서면
                      사람이 어느 축을 보는지 모른다(GX-COPY §1-4).
                      남은 축은 **처리 단계**(아래 「현장 조치」)와 **판정** 둘이다. */}
                  <Tag>{labelOf(RESPONSE_STATE_LABEL, e.response_state)}</Tag>
                  <VerdictBadge verdict={e.verdict} />
                </Space>
                <Text style={{ fontSize: 13 }}>
                  발생 {relative(e.occurred_at)} ({absolute(e.occurred_at)})
                </Text>
              </Space>
            </Card>

            {/* ② 어디로 가나 */}
            <Card
              size="small"
              title="어디로 가나"
              styles={{ body: { padding: 12 } }}
            >
              <Descriptions
                column={1}
                size="small"
              >
                <Descriptions.Item label="카메라">
                  {e.stream_monitor_name || '이름 없음'}
                </Descriptions.Item>
                <Descriptions.Item label="설치 주소">
                  {/* ★ 없는 것은 없다고 적는다 (D-284) — 빈칸은 「조회 중」과 같아 보인다. */}
                  {e.address || (
                    <Text type="secondary">
                      미입력 — {labelOf(ADDRESS_STATUS_LABEL, e.address_status)}
                    </Text>
                  )}
                </Descriptions.Item>
                <Descriptions.Item label="좌표">
                  {e.lat != null && e.lng != null ? (
                    `${e.lat}, ${e.lng}`
                  ) : (
                    <Text type="secondary">없음</Text>
                  )}
                </Descriptions.Item>
              </Descriptions>
              {/* ★ [P-141 · 턴 Q] 좌표 또는 주소가 있을 때만 그린다 — 없는 칸에
                  손잡이를 그리지 않는다(이 화면이 전화 버튼에서 이미 지킨 규약). */}
              {(() => {
                const href = mapLinkUrl(e.lat, e.lng, e.address);
                return href ? (
                  <a href={href} target="_blank" rel="noreferrer">
                    <Button block style={{ minHeight: TOUCH_MIN, marginTop: 8 }}>
                      {MAP_LINK_LABEL}
                    </Button>
                  </a>
                ) : null;
              })()}
            </Card>

            {/* ③ 무엇을 보나 — 스냅샷 참조 · 구간 티켓 */}
            <Card
              size="small"
              title="무엇을 보나"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={8}
                style={{ width: '100%' }}
              >
                <div>
                  <Text strong>스냅샷</Text>
                  {/* ★★ [P-121] **거짓 표지판을 지우고 사진을 그린다.**
                      「관제 화면에서 확인하십시오」는 열려 있는 문을 닫혔다고 말하면서
                      **같이 고장 나 있던 화면**으로 사람을 보내고 있었다.
                      ★ 부품은 관제 화면과 **한 벌**이다(`EventSnapshot`). 없다 · 못 받았다 ·
                        받았다 셋을 가르는 규율도 거기 한 곳에 있다.
                      ★ 경로 문자열은 **접었다.** 이동 중인 사람의 화면에서 첫 자리는
                        사진이지 객체 키가 아니다 — 키는 인계·문의에 쓰이므로 버리지 않고
                        「참조 보기」 아래에 둔다. */}
                  {e.snapshot_path ? (
                    <>
                      <div style={{ marginTop: 6 }}>
                        <EventSnapshot
                          eventId={e.event_id}
                          snapshotPath={e.snapshot_path}
                          compact
                          alt="현장 스냅샷"
                          // [P-148 · 턴 R] 판정기가 찾는 표식 — img[data-gx=snapshot] 1개.
                          dataGx="snapshot"
                        />
                      </div>
                      <Collapse
                        ghost
                        size="small"
                        items={[{
                          key: 'ref',
                          label: <Text style={{ fontSize: 12 }}>참조 보기</Text>,
                          children: (
                            <Paragraph
                              copyable={{ text: e.snapshot_path }}
                              style={{ fontSize: 12, marginBottom: 0, wordBreak: 'break-all' }}
                            >
                              {e.snapshot_path}
                            </Paragraph>
                          ),
                        }]}
                      />
                    </>
                  ) : (
                    <Paragraph type="secondary" style={{ fontSize: 12 }}>
                      이 이벤트에는 스냅샷 참조가 없습니다.
                    </Paragraph>
                  )}
                </div>

                <div>
                  <Text strong>구간 티켓</Text>
                  <StateBoundary
                    state={clip.state}
                    reason={clip.reason} status={clip.status}
                    onRetry={clip.reload}
                    /* ③ [턴 AA] 원인과 다음 손이 **한 줄**에 있다. 다음 손은
                       이 화면에 **실제로 서 있는 손잡이**만 가리킨다(위 머리말). */
                    emptyText={e.snapshot_path ? CLIP_EMPTY_WITH_SNAPSHOT : CLIP_EMPTY_NO_SNAPSHOT}
                  >
                    {clip.data ? (
                      <Descriptions
                        column={1}
                        size="small"
                      >
                        <Descriptions.Item label="구간">
                          시작 {clip.data.start_offset}s · 길이 {clip.data.duration}s
                        </Descriptions.Item>
                        <Descriptions.Item label="만료">
                          {absolute(clip.data.expires_at)}
                        </Descriptions.Item>
                        <Descriptions.Item label="재생">
                          {/* ★ 계약 11조 잠금 — 재생기를 그리지 않는다. 사유를 그대로 적는다. */}
                          <Text type="secondary">
                            {clip.data.playable ? '가능' : '불가'} —{' '}
                            {clip.data.reason || '사유 없음'}
                          </Text>
                        </Descriptions.Item>
                      </Descriptions>
                    ) : null}
                  </StateBoundary>
                </div>
              </Space>
            </Card>

            {/* ③-b 이 카메라 7일 — 같은 자리에서 무엇이 반복되나 (턴 T · P-164 U3) */}
            <Card
              size="small"
              title={SAME_CAMERA_HEADLINE}
              styles={{ body: { padding: 12 } }}
              data-gx="same-camera-7d"
            >
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {e.stream_monitor_name || '카메라 미상'} · 지난 {SAME_CAMERA_DAYS}일 ·{' '}
                  {sameCamera.data ? `${sameCamera.data.total}건 (이 페이지 · 최대 ${SAME_CAMERA_LIMIT})` : '—'}
                </Text>
                <StateBoundary
                  state={sameCamera.state}
                  reason={sameCamera.reason}
                  status={sameCamera.status}
                  onRetry={sameCamera.reload}
                  emptyText={`이 카메라에서 지난 ${SAME_CAMERA_DAYS}일 동안 다른 사건이 0건입니다.`}
                >
                  <Space direction="vertical" size={2} style={{ width: '100%' }}>
                    {(sameCamera.data?.events ?? []).map((row) => (
                      <Space key={row.event_id} size={6} wrap>
                        {row.event_id === e.event_id ? (
                          <Tag color="blue">이 사건</Tag>
                        ) : (
                          <Link to={mobileEventDetailPath(row.event_id)}>#{row.event_id}</Link>
                        )}
                        <Tag color={SEVERITY_COLOR[row.severity]}>{labelOf(SEVERITY_LABEL, row.severity)}</Tag>
                        <Text style={{ fontSize: 12 }}>{labelOf(EVENT_TYPE_LABEL, row.event_type)}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {relative(row.occurred_at)} · {labelOf(RESPONSE_STATE_LABEL, row.response_state)}
                        </Text>
                      </Space>
                    ))}
                  </Space>
                </StateBoundary>
              </Space>
            </Card>

            {/* ④ 무엇을 누르나 — 상태 전이 */}
            <Card
              size="small"
              title="현장 조치"
              styles={{ body: { padding: 12 } }}
            >
              <Space
                direction="vertical"
                size={8}
                style={{ width: '100%' }}
              >
                {/* ★ [UX-22] 처리 단계 한 줄 — 미처리 → 접수 → 조치 중 → 종결 */}
                <ResponseSteps state={e.response_state} />

                {/*
                  ★★ M3 **상태 칸** (UX-45 여섯 칸 · 2026-09-16 턴 S).

                  이 표가 이 화면의 값이다 — 단추를 누른 사람이 **무엇이 남았는지**를
                  여기서 본다. 「보냈습니다」라는 한순간의 알림만으로는 다음 순간에
                  아무것도 안 남고, 이동 중인 사람은 방금 누른 것이 갔는지 다시 누를지를
                  화면에 물어야 한다.

                  ★ 수의 출처는 **서버**다(`GET …/field-replies` 의 `by_kind`).
                    화면이 자기가 센 수를 적으면 다른 기기에서 남긴 회신이 안 세어지고,
                    그러면 「지원 요청 0건」이 실은 「이 화면이 모르는 것」이 된다.
                  ⚠ 사진만 **이번 화면의 수**다 — 사진 목록을 내는 문이 아직 없다
                    (`field.py` 머리말: 읽기 문은 다음 파). 그래서 그 칸은 자기가
                    무엇을 세는지 이름으로 밝힌다.
                */}
                <Descriptions
                  column={1}
                  size="small"
                  bordered
                  styles={{ label: { width: 96 } }}
                >
                  <Descriptions.Item label="도착">
                    {(replies.data?.by_kind?.arrived ?? 0) > 0 ? (
                      <Tag color="green">기록됨 {replies.data?.by_kind?.arrived}건</Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="사진">
                    {photoCount > 0 ? (
                      <Tag color="green">이번 화면에서 {photoCount}장</Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="한 줄">
                    {(replies.data?.by_kind?.note ?? 0) > 0 ? (
                      <Tag color="green">{replies.data?.by_kind?.note}건</Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="오탐 사유">
                    {(replies.data?.by_kind?.false_positive ?? 0) > 0 ? (
                      <Tag color="orange">기록됨</Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="지원 요청">
                    {(replies.data?.by_kind?.support ?? 0) > 0 ? (
                      <Tag color="red">요청 {replies.data?.by_kind?.support}건</Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                  <Descriptions.Item label="조치 완료">
                    {(replies.data?.by_kind?.done ?? 0) > 0 ? (
                      <Tag color="green">
                        기록됨
                        {e.response_state === 'closed' ? ' · 종결됨' : ''}
                      </Tag>
                    ) : (
                      <Text type="secondary">아직</Text>
                    )}
                  </Descriptions.Item>
                </Descriptions>

                {(e.allowed_next ?? []).length === 0 ? (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    지금 이 계정이 옮길 수 있는 다음 단계가 없습니다.
                  </Text>
                ) : (
                  <Space
                    direction="vertical"
                    size={8}
                    style={{ width: '100%' }}
                  >
                    {(e.allowed_next ?? []).map((next) => {
                      const backward = e.response_state === 'closed' && next === 'in_progress';
                      return (
                        <Button
                          key={next}
                          block
                          type={backward ? 'default' : 'primary'}
                          danger={backward}
                          loading={busy === next}
                          style={{ minHeight: TOUCH_MIN }}
                          onClick={() => advance(next, backward)}
                        >
                          {backward ? '되돌리기 → ' : ''}
                          {advanceLabel(next)}
                        </Button>
                      );
                    })}
                  </Space>
                )}

                {/*
                  M3 — **도착 · 지원 요청 · 조치 완료** (UX-45 여섯 칸 중 셋 · 턴 S).

                  ★ 이 셋은 **회신을 남기는 단추**다. 위의 「접수하기·조치 시작·종결하기」는
                    서버가 준 `allowed_next` 를 그린 **상태 전이** 단추이고, 둘은 다른
                    일이다 — 전이는 지금 갈 수 있는 칸이 있을 때만 그려지지만, 회신은
                    언제나 남아야 한다(이미 조치 중인 사건에 도착해도 관제는 그 사실을
                    기다린다). 「도착」·「완료」는 회신을 남기고 **허락된 경우에만**
                    전이까지 태운다(`advanceIfAllowed`).
                  ★ 글상자는 아래 하나뿐이다 — 어느 단추를 누르는가가 그 글의 뜻을 정한다.
                */}
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  <Button
                    block
                    style={{ minHeight: TOUCH_MIN }}
                    loading={busy === 'arrived'}
                    onClick={reportArrived}
                  >
                    도착 보고
                  </Button>
                  <Button
                    block
                    danger
                    style={{ minHeight: TOUCH_MIN }}
                    loading={busy === 'support'}
                    onClick={requestSupport}
                  >
                    지원 요청
                  </Button>
                  <Button
                    block
                    style={{ minHeight: TOUCH_MIN }}
                    loading={busy === 'done'}
                    onClick={reportDone}
                  >
                    조치 완료
                  </Button>
                </Space>

                {/* M3 — 사진 한 장. 「도착 · 사진 · 한 줄 · 오탐 · 완료」 중 사진(선택). */}
                <Card size="small" title={FIELD_PHOTO_HEADLINE}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <input
                      ref={photoInputRef}
                      type="file"
                      accept={FIELD_PHOTO_ACCEPT}
                      capture="environment"
                      hidden
                      onChange={onFieldPhotoChosen}
                    />
                    <Button
                      block
                      style={{ minHeight: TOUCH_MIN }}
                      loading={photoBusy}
                      onClick={pickFieldPhoto}
                    >
                      사진 올리기
                    </Button>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {photoCount > 0
                        ? `이번 화면에서 ${photoCount}장을 올렸습니다.`
                        : '선택입니다 — 안 올려도 다음으로 갑니다.'}
                    </Text>
                  </Space>
                </Card>

                {/* M3 — 현장 회신 한 줄. 「도착 · 사진 한 장 · 한 줄」 중 한 줄이다. */}
                <Card size="small" title={FIELD_REPLY_HEADLINE}>
                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                    <Input.TextArea
                      rows={2}
                      maxLength={500}
                      value={replyText}
                      placeholder="현장에서 본 것을 한 줄로 적습니다."
                      onChange={(ev) => setReplyText(ev.target.value)}
                    />
                    <Button
                      type="primary"
                      block
                      style={{ minHeight: TOUCH_MIN }}
                      loading={busy === 'field-reply'}
                      disabled={replyText.trim().length === 0}
                      onClick={sendFieldReply}
                    >
                      회신 보내기
                    </Button>
                    <StateBoundary
                      state={replies.state}
                      reason={replies.reason} status={replies.status}
                      onRetry={replies.reload}
                      emptyText="아직 회신이 없습니다."
                    >
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {(replies.data?.replies ?? []).map((r) => (
                          <Text key={r.reply_id} style={{ fontSize: 12 }}>
                            {r.author_name || '이름 없음'} · {r.text}
                          </Text>
                        ))}
                      </Space>
                    </StateBoundary>
                  </Space>
                </Card>

                {/* M3 — 오탐 회신. 「가 보니 아무것도 없다」 · 완료(위 다음 단계)와 서로 배타. */}
                <Button
                  block
                  type="dashed"
                  style={{ minHeight: TOUCH_MIN }}
                  loading={busy === 'false-positive'}
                  onClick={reportFalsePositive}
                >
                  오탐 — 가 보니 아무것도 없음
                </Button>
              </Space>
            </Card>
          </Space>
        ) : null}
      </StateBoundary>
    </MobileShell>
  );
}
