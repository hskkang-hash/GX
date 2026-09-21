/**
 * UX-13 **단일 초점 큐** — W1 최상단은 목록이 아니라 **가장 급한 하나**다.
 *
 * 무엇이 문제였나
 * ---------------
 * 지금 W1 은 최신순 목록이다. 최신순이면 새 이벤트가 계속 최상단을 밀어내고,
 * **가장 오래 방치된 사건이 영원히 안 보인다.** 그리고 같은 카메라가 3분 사이 7번
 * 울리면 그 7장이 화면을 채워, 밀려난 자리에 있던 **다른 카메라의 첫 발생**이 사라진다.
 * 이 화면이 막는 것이 정확히 그 두 자리다.
 *
 * 무엇을 그리나
 * -------------
 *   ① **초점 카드 하나** — 대응 시계(UX-14) · 스냅샷 · 버튼 셋.
 *   ② 나머지를 5분 창 `stream+type` 으로 묶은 카드들. 각 카드에 **「×N」 배지**.
 *
 * ★ **이벤트를 접는 것이 아니다.** 원본 건수(`total_events`)를 화면에 **그대로 적는다** —
 *   카드 수(`card_total`)와 다른 수이고, 다른 것이 요점이다. F-14 통계는 원본을 세고
 *   접히는 것은 화면이지 기록이 아니다. 두 수를 나란히 두는 것이 그 약속의 증거다.
 *
 * ★ 「가장 급한」은 **서버가 정한다.** 화면이 정하면 화면마다 다른 하나가 최상단에
 *   오고, 교대 인계에서 두 사람이 다른 사건을 이야기하게 된다.
 *   이 파일에 `sort(` 도 `filter(` 도 없다 — 없는 것이 이 화면의 성질이다.
 *
 * ★ 버튼 셋은 **서버가 준 `allowed_next`** 로 그린다. 화면이 전이표를 따로 들면
 *   **서버가 거절하는 버튼**을 그리게 된다 (D-399).
 *
 * ★ 자료 읽기·쓰기는 이제 `useFocusQueue()`(같은 폴더 `hooks/`)가 진다 — 이 화면은
 *   그 훅이 낸 값을 **그리기만** 한다(WO-01 §4.1 U1 소유 · 턴 Q).
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-15 **키보드 · 소리** (차선 C1 · 2026-09-05)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 무엇이 문제였나: 판정 경로가 **클릭뿐**이고 소리는 **0종**이었다. 관제요원은
 * 8시간 마우스를 쥐지 않는다.
 *
 * 1 · 2 · 3 을 **무엇에 붙였나** [판단과 그 사유]
 * ---------------------------------------------
 * 이 저장소의 축은 둘이다 — **판정**(실제 / 오탐)과 **처리 단계**(미처리 → 접수 →
 * 조치 중 → 종결). 붙인 자리는 **고정**이다: 1=실제로 확인·접수 · 2=조치 시작 ·
 * 3=종결하기.
 *
 * ★★ [WO-01 §5 · AC-2 · 턴 Q] **키 1 의 뜻이 바뀌었다.** 종전에는 접수(대응 진행
 *   한 칸)만이었다. 이제는 **판정(확인) + 접수를 한 트랜잭션으로 묶는 문**
 *   (`review-and-acknowledge`)을 부른다 — 「이 탐지는 진짜다, 그리고 내가
 *   접수한다」가 사람에게는 한 번의 행동이기 때문이고, 두 번 왕복하면 첫 호출만
 *   성공했을 때 반쪽짜리 사건(판정은 됐는데 접수는 안 됨)이 생긴다. 2·3 은 그대로
 *   대응 진행만 옮긴다 — 이미 판정된 사건에 다시 판정을 얹을 이유가 없다.
 *
 * ★ 오탐(이 탐지는 가짜다)은 **숫자 키에 없다.** 판정 단추를 셋째 축으로 얹으면
 *   「1·2·3」이 어떤 턴에는 처리 단계이고 어떤 턴에는 판정이 되어 뜻이 흔들린다 —
 *   관제실에서 뜻이 흔들리는 키는 오조작을 만든다. 오탐은 **이름 붙은 단추**로만 연다.
 *
 * ★ 숫자 키는 **가장 급한 하나**에만 든다. J·K·Enter 는 대기 카드에도 든다 —
 *   그것은 **읽는 일**이지 쓰는 일이 아니기 때문이다.
 *
 *   ★★ [턴 W · P-188] 종전에 이 자리에는 「대기 카드에는 서버가 `allowed_next` 를
 *     주지 않으므로 화면이 지어낼 수 없다」고 적혀 있었다. **그 문장은 이제 낡았다** —
 *     `GET /api/dsm/queue/field-signals`(턴 S · U1)가 물은 사건마다 `allowed_next` 를
 *     **함께 낸다**(`queue_signals.py:192`). 그래서 대기 카드의 **단추**는 선다.
 *     숫자 키는 **여전히 초점 하나에만** 든다 — 키가 「지금 고른 카드」를 따라다니면
 *     1·2·3 의 대상이 화면 위에서 움직이고, 움직이는 대상의 키는 관제실에서
 *     오조작을 만든다. 대기 카드는 **눈으로 보고 누르는** 자리다.
 *
 *
 * ★ **심각만 소리가 난다.** 묶인 반복(×N)은 **1회**다. 그 두 문지기는
 *   `useCriticalAlarm` 에 있다. 음소거이거나 브라우저가 소리를 잠가 두었으면
 *   화면이 **먼저** 「소리가 꺼져 있습니다」로 말한다 — 안 울리는 이유를 모르면
 *   사용자는 조용한 화면을 「사건이 없다」로 읽는다.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-25 **토스트를 쓰지 않는다** (턴 Q)
 * ═══════════════════════════════════════════════════════════════════════════
 * 쓰기 성공을 알리는 `message.success(...)` 를 이 화면에 두지 않는다. 결과는
 * 카드의 상태 칸(`response_state` 태그)이 스스로 「접수」 등으로 보인다 —
 * **상태는 칸으로**(불변). 소리(`actionEcho`)만 「눌린 것을 먹었다」는 즉각 신호를 준다.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * UX-33 **큐 카드 1클릭 판정 3 — 상세로 들어가지 않는다** (턴 W · 차선 U1 · P-188)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * 무엇이 문제였나 [갤러리 관찰 · 온보딩 U1#11]
 * -------------------------------------------
 * 단추 셋은 **초점 카드 한 장에만** 있었다. 대기 카드에는 「열기」밖에 없어서,
 * 두 번째로 급한 사건을 처리하려면 **상세로 들어갔다 나와야** 했다 — UX-33 이
 * 없애기로 한 바로 그 왕복이다. 온보딩 U1#11 이 ○ 로 찍힌 것도 같은 자리다.
 *
 * 어떻게 고쳤나
 * -------------
 * 대기 카드도 **서버가 준 `allowed_next` 로만** 단추를 그린다. 출처가 초점과
 * 다를 뿐이다 — 초점은 큐 응답의 `focus.allowed_next`, 대기 카드는
 * `/queue/field-signals` 의 `signals[].allowed_next`(`queue_signals.py:192` ·
 * **기존 문이다. 새 라우트를 만들지 않았다**). 화면이 전이표를 들지 않는다는 규약은
 * 그대로다(D-399).
 *
 * ★ 서버가 허락하지 않은 갈래는 **아예 안 그린다**(누를 수 있게 두고 막지 않는다).
 *   회색으로 남겨 두면 사람이 그것을 「지금은 안 되지만 곧 될 것」으로 읽고 누른다.
 * ★ 서버가 **아직 말하지 않은** 카드(신호를 못 읽었거나 상한 30 밖)는 단추 0 개이고
 *   그 자리에 **「서버가 아직 말하지 않았습니다」**라고 적는다 — 「없음」이 아니다.
 *   회색은 초록이 아니고, 모르는 것을 「안 된다」로 적지도 않는다.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * P-188 **경과 순위 — 고정 문구를 뗐다** (턴 W · 차선 U1)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * `time.ts` 의 단계 4 이름이 **「8분 경과 — 가장 오래 기다린 사건」** 이었다. 단계 4 인
 * 카드가 열 장이면 **열 장 전부**가 자기가 가장 오래 기다렸다고 적었고, 서버 문턱이
 * 8분이 아니어도 「8분」이라고 적었다. 둘 다 거짓이다.
 *
 * 이제 단계 이름은 서버 문턱이 짓고(`tierLabel`), **순위는 이 화면이 센다** —
 * 카드를 전부 보는 자리가 여기뿐이기 때문이다. 세는 값은 서버가 준
 * `elapsed_seconds` 다(화면 시계가 아니다 — 카드마다 다른 순간에 잰 수를 견주면
 * 순위가 깜박인다).
 *
 * ★ **정렬이 아니라 세기다.** 이 파일에 `sort(` 도 `filter(` 도 없다는 성질은
 *   그대로다 — 순위는 「나보다 오래 기다린 카드가 몇 장인가」를 **센** 수이고,
 *   화면에 그려지는 **순서는 서버가 준 그대로**다.
 * ★ **분모를 손으로 적지 않는다.** 「N건 중 k번째」의 N 은 시계가 도는 카드를 센
 *   수다. 동률이면 동률이라고 적는다 — 한 장에만 붙는 사실을 두 장에 붙이지 않는다.
 */
import {
  Alert, Badge, Button, Card, Col, Input, Row, Space, Statistic, Tag, Typography,
} from 'antd';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import {
  CLOSE_CONFIRM_EMPTY,
  CLOSE_CONFIRM_EMPTY_ONE_LINE,
  CLOSE_CONFIRM_TITLE,
  dataSourceBadge,
  FALSE_POSITIVE_REASONS,
  REJECT_LABEL,
  REVIEW_AND_ACK_LABEL,
  SUPPORT_BADGE_LABEL,
  SUPPORT_WAITING_NOTE,
  WIRING_WAITING_LABEL,
} from '../copy';
import EventSnapshot from '../components/EventSnapshot';
import ResponseClock from '../components/ResponseClock';
import ShortcutHelp from '../components/ShortcutHelp';
import StateBoundary from '../components/StateBoundary';
import { KICK_SENTENCE } from '../constants/kick';
import { useAlertSound } from '../hooks/useAlertSound';
import { useCriticalAlarm } from '../hooks/useCriticalAlarm';
import { useDetectionPing } from '../hooks/useDetectionPing';
import { useFocusQueue } from '../hooks/useFocusQueue';
import { useQueueKeys } from '../hooks/useQueueKeys';
import { useQueueSignals } from '../hooks/useQueueSignals';
import type { QueueFieldSignal } from '../hooks/useQueueSignals';
import { cancelMetric, countClick, finishMetric, startMetric } from '../metrics';
import { dsm2Routes } from '../routes';
import {
  advanceLabel,
  EVENT_TYPE_LABEL,
  labelOf,
  RESPONSE_STATE_LABEL,
  SEVERITY_COLOR,
  SEVERITY_ICON,
  SEVERITY_LABEL,
} from '../severity';
import { rankNoteOf, stamp, TIMEZONE_NOTE, waitRanks } from '../time';
import type { QueueCard } from '../types';

const { Text, Title, Paragraph } = Typography;

/**
 * 숫자 키 → 처리 단계. **고정이다** (위 머리말의 판단).
 * 값은 계약 스키마의 것이고 화면 표시 이름은 `RESPONSE_STATE_LABEL` 이 따로 든다.
 */
const STEP_SLOTS = ['acknowledged', 'in_progress', 'closed'] as const;

/** 종결 확인 카드의 단추 — 「확인」 한 번이 서버 기록을 닫는다(턴 T). */
export const CLOSE_CONFIRM_BUTTON = '확인 — 종결';

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '지금 처리할 것 — 가장 급한 하나';

/**
 * 현장 신호를 물어볼 카드 수의 천장. **서버의 상한과 같은 수**다 —
 * 화면이 더 물으면 서버가 잘라서 답하고, 잘린 줄은 아무도 못 본다.
 */
const SIGNAL_ASK_CAP = 30;

/** 서버가 아직 허용 단계를 말해 주지 않은 카드에 적는 말. **「없음」이 아니다.** */
export const ALLOWED_UNKNOWN_NOTE =
  '서버가 이 카드의 다음 단계를 아직 말하지 않았습니다 — 「열기」로 상세에서 처리하세요.';

/** 갈 곳이 없다고 **서버가 말한** 카드. 위와 다른 사실이라 다른 글자다. */
export const ALLOWED_NONE_NOTE = '더 갈 곳이 없습니다 — 이 사건은 마지막 단계입니다.';


function eventPath(id: number): string {
  return `/dsm/events/${id}`;
}


function CardHead({ card, signal }: { card: QueueCard; signal?: QueueFieldSignal }) {
  return (
    <Space wrap size={6}>
      <Tag color={SEVERITY_COLOR[card.severity] ?? 'default'}>
        {SEVERITY_ICON[card.severity] ?? '•'}{' '}
        {labelOf(SEVERITY_LABEL, card.severity)}
      </Tag>
      {/*
        ★ [턴 S] **지원 요청은 등급 바로 옆이다.** 현장이 「혼자 못 한다」고 한 사건은
          큐에서 가장 먼저 눈에 띄어야 한다 — 뒤쪽에 달면 등급·유형·카메라 이름에
          묻힌다. 현장이 적은 말은 **손댈 때 보이게** 제목에 얹는다(본문은 종결 확인
          칸이 그린다 — 카드 머리가 문단이 되면 큐가 목록으로 돌아간다).
      */}
      {signal?.support_requested ? (
        <Tag color="error" title={signal.support_text}>
          {SUPPORT_BADGE_LABEL}
        </Tag>
      ) : null}
      {/*
        ★★ [P-201 · 턴 Y] **「훈련」 배지.** 훈련 사건은 이제 큐에 **선다** —
          제품이 세는 것이 P-201 의 요점이고(`data_source=probe` 와 갈리는 자리),
          서면 그 카드가 무엇인지를 **카드가 스스로 말해야** 한다. 안 말하면
          관제요원은 훈련을 재난으로 읽고 사람을 보낸다.
        ★ 말은 새로 지지 않는다 — `copy.ts::dataSourceBadge` 가 이미 들고 있는
          「훈련」(GX-COPY §2 「실운영 / 시드(검수용) / 훈련」)을 그대로 부른다.
        ★ **등급 바로 옆**이다. 뒤쪽에 달면 카메라 이름에 묻히고, 묻힌 배지는
          「없는 것」과 같다. `live` 면 `dataSourceBadge` 가 `null` 을 낸다 — 평상엔 안 그린다.
      */}
      {dataSourceBadge(card.data_source) ? (
        <Tag color="purple" title="훈련으로 심긴 사건입니다 — 실제 사고가 아닙니다.">
          {dataSourceBadge(card.data_source)}
        </Tag>
      ) : null}
      <Text strong>{labelOf(EVENT_TYPE_LABEL, card.event_type)}</Text>
      <Text type="secondary">{card.stream_monitor_name || '이름 없는 카메라'}</Text>
      <Tag>{labelOf(RESPONSE_STATE_LABEL, card.response_state)}</Tag>
      {card.count > 1 ? (
        // ★ 「×1」은 배지를 안 단다 — 정보가 아니라 소음이다.
        <Badge
          count={`×${card.count}`}
          style={{ backgroundColor: '#fa541c' }}
          title={
            `같은 카메라·같은 유형이 ${Math.round(card.window_seconds / 60)}분 창 안에 ` +
            `${card.count}번 났습니다. 카드만 묶였고 이벤트 ${card.count}건은 그대로 있습니다 ` +
            `(id: ${card.member_event_ids.join(', ')}).`
          }
        />
      ) : null}
    </Space>
  );
}

export default function FocusQueuePage() {
  const navigate = useNavigate();
  const [showKeys, setShowKeys] = useState(false);
  /**
   * 오탐 사유 3택을 **어느 카드에서** 펼쳤는가 — 토스트 대신 **칸 하나를 펼치는**
   * 가벼운 확인. [턴 W] 종전에는 `boolean` 이라 초점 카드 하나에만 들었다. 대기
   * 카드에도 오탐 단추가 서면서 **어느 카드인지**를 들어야 한다 — 참/거짓으로
   * 들면 한 장을 펼쳤을 때 모든 카드의 사유 칸이 함께 열리고, 사람은 자기가 어느
   * 사건에 사유를 붙이는지 모른 채 누른다.
   */
  const [rejectingId, setRejectingId] = useState<number | null>(null);
  /**
   * 되돌림 사유 초안. **서버가 400 으로 「사유를 채워 다시」라고 한 뒤에만** 쓰인다 —
   * 화면이 「이 칸은 사유가 필요하다」를 미리 알고 있으면 그것이 두 번째 전이표다.
   */
  const [reasonDraft, setReasonDraft] = useState('');
  /**
   * ★★ [턴 W · P-188] **서버가 「이 계정으로는 안 된다」(403)고 말한 칸.**
   *
   * `allowed_next` 는 「그 전이가 표에 있는가」를 말하지 **누가 할 수 있는가**를
   * 말하지 않는다. 종결된 사건의 되돌림(`closed → in_progress`)은 표에 있지만
   * **관제팀장만** 한다 — 관제요원 계정으로는 누를 때마다 403 이다
   * [실측 2026-09-19 17:4x · `gxseed_u1_operator` · 사건 268497:
   *  사유 없이 400 「되돌림에는 사유가 필수다」 → 사유를 채워 **403** 「관제팀장(K3
   *  MANAGER 이상)만 한다」 · 재조회 `closed` 그대로].
   *
   * 화면은 그 표를 **미리 들지 않는다.** 대신 **서버가 방금 한 말**을 기억해서 그
   * 칸을 더는 누를 수 없게 한다 — 같은 403 을 열 번 받게 두는 것은 사람의 시간을
   * 쓰는 일이고, 그 열 번이 전부 감사에 남는다.
   *
   * 지우지 않는다(새로고침이면 다시 묻는다) — 권한은 바뀔 수 있고, 화면이 그것을
   * 영원히 「안 된다」로 박아 두면 그것이 또 하나의 거짓 표가 된다.
   */
  const [denied403, setDenied403] = useState<Record<string, string>>({});
  /**
   * 편리성 계측 #1 의 시계를 **다시 걸기 위한 눈금.** 대기 카드를 누르면 측정 대상이
   * 그 카드로 갈아타므로(아래 `actOn`), 끝난 뒤 초점의 측정을 다시 걸어야 한다.
   */
  const [metricEpoch, setMetricEpoch] = useState(0);
  /** 0 은 초점 카드, 1 부터가 대기 카드다. **선택은 읽는 일**이다. */
  const [selected, setSelected] = useState(0);
  const rowRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const sound = useAlertSound();

  // ★ [UX-15] 키보드로 일하는 사람은 눌린 것을 눈으로 확인할 시간이 없다 — 쓰기가
  //   성공한 직후 한 음(`actionEcho`)을 울린다. 이 한 음이 없으면 같은 키를 두 번 누른다.
  const { queue, cards, focus, thresholds, acting, actionError, actionStatus,
    actionOn, clearActionError, advance, reviewAndAcknowledge, reject } = useFocusQueue({
    onActionSuccess: (what) => {
      sound.play('actionEcho');
      // ★ 편리성 계측 #1 의 시계는 **접수에서 멈춘다** — 재는 것이 「판정에서 접수까지」라서다.
      //   오탐이나 조치 시작에서 멈추면 그것은 다른 지표가 된다.
      if (what === 'review-ack') finishMetric('u1_handle_event');
      // ★ [턴 W] 측정 대상이 대기 카드로 갈아탔을 수 있다 — 초점의 시계를 다시 건다.
      setMetricEpoch((n) => n + 1);
    },
  });

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(queue.reload);

  const data = queue.data;

  // ★ 심각만 · 묶음은 1회. 문지기는 훅 안에 있다.
  useCriticalAlarm({
    cards,
    thresholds,
    play: sound.play,
    ready: queue.state === 'data' || queue.state === 'empty',
  });

  // 선택이 목록 밖으로 나가지 않게 한다. 카드가 줄면 선택도 줄어야 한다.
  useEffect(() => {
    setSelected((n) => (cards.length === 0 ? 0 : Math.min(n, cards.length - 1)));
  }, [cards.length]);

  // 골라 놓은 줄이 화면 밖에 있으면 고른 것이 아니다.
  useEffect(() => {
    rowRefs.current[selected]?.scrollIntoView({ block: 'nearest' });
  }, [selected]);

  // 카드가 바뀌면 열어 둔 오탐 사유 칸을 닫는다 — 다른 카드에 잘못 적용되는 것을 막는다.
  useEffect(() => {
    setRejectingId(null);
  }, [focus?.event_id]);

  /*
   * ★ [턴 S] **현장 신호** — 「지원 요청」 배지와 「종결 확인」 카드가 이 값으로 선다.
   *   화면이 지금 그린 카드의 번호만 묻는다(서버도 같은 수에서 자른다).
   */
  const signalIds = useMemo(
    () => cards.slice(0, SIGNAL_ASK_CAP).map((c) => c.event_id),
    [cards],
  );
  const signals = useQueueSignals(signalIds);

  /*
   * 편리성 계측 #1 — **사건 1건 처리.** 초점 카드가 뜬 때 시계가 걸리고, 판정+접수가
   * 성공한 때 멈춘다(위 `onActionSuccess`). 초점이 바뀌면 앞 사건의 측정은 **버린다** —
   * 하다 만 것은 수가 아니다.
   */
  useEffect(() => {
    if (focus) startMetric('u1_handle_event', String(focus.event_id));
    else cancelMetric('u1_handle_event');
  }, [focus?.event_id, metricEpoch]);

  /**
   * 경과 순위 — 서버가 준 `elapsed_seconds` 로 **센다**(정렬하지 않는다 · 머리말 참조).
   * 초점 + 대기 카드를 **함께** 본다: 순위는 화면 전체의 사실이지 대기 목록만의
   * 사실이 아니다.
   */
  // ★ 서버가 403 으로 「이 계정으로는 안 된다」고 말한 칸을 적어 둔다(위 머리말).
  useEffect(() => {
    if (actionStatus === 403 && actionOn) {
      const key = `${actionOn.eventId}:${actionOn.toState}`;
      setDenied403((m) => (m[key] ? m : { ...m, [key]: actionError }));
    }
  }, [actionStatus, actionOn, actionError]);

  const ranks = useMemo(() => waitRanks(cards), [cards]);
  /** 순위의 **분모** — 시계가 도는 카드 수. 센 수다(손으로 적지 않는다). */
  const rankTotal = useMemo(() => {
    for (const r of ranks.values()) return r.total;
    return 0;
  }, [ranks]);

  /**
   * ★ [턴 W · P-188] **어느 카드의 눌림인지를 계측이 알아야 한다.**
   *
   * 편리성 #1 은 「사건 **1건** 처리에 몇 번 눌렀나」다. 시계는 초점 카드에 걸려
   * 있는데 사람이 대기 카드를 누르면, 그 누름을 초점의 수에 더하는 순간 **두 사건의
   * 클릭이 한 줄에 섞인다.** 그래서 대상이 다르면 **측정을 그 카드로 갈아탄다** —
   * `startMetric` 은 대상이 다르면 새로 걸고, 같으면 처음 것을 지킨다.
   *
   * 갈아타면서 버려지는 것은 **끝나지 않은 측정**이다. 하다 만 것은 수가 아니므로
   * 버리는 것이 맞다(`cancelMetric` 과 같은 뜻).
   */
  const countClickOn = useCallback((eventId: number) => {
    startMetric('u1_handle_event', String(eventId));
    countClick('u1_handle_event');
  }, []);

  const onReject = useCallback(
    (eventId: number, reasonLabel: string) => {
      if (acting) return;
      setRejectingId(null);
      countClickOn(eventId);
      void reject(eventId, reasonLabel);
    },
    [acting, reject, countClickOn],
  );

  /**
   * 이 카드에 **서버가 허락한 다음 단계**. 출처는 둘이고 둘 다 서버다:
   *   · 초점 카드 — 큐 응답의 `focus.allowed_next`
   *   · 대기 카드 — `/queue/field-signals` 의 `signals[].allowed_next`
   *
   * `known` 이 거짓인 것은 **「없다」가 아니라 「아직 못 들었다」**이다(상한 30 밖 ·
   * 첫 응답 전 · 남의 테넌트라 목록에서 빠진 것). 화면은 그 셋을 **같은 말**로 적는다 —
   * 어느 쪽인지 화면이 알 수 없고, 모르는 것을 갈라 적으면 그것이 지어낸 것이다.
   */
  const allowedFor = useCallback(
    (card: QueueCard): { known: boolean; allowed: string[] } => {
      if (Array.isArray(card.allowed_next)) {
        return { known: true, allowed: card.allowed_next };
      }
      const signal = signals.byEvent.get(card.event_id);
      if (signal && Array.isArray(signal.allowed_next)) {
        return { known: true, allowed: signal.allowed_next };
      }
      return { known: false, allowed: [] };
    },
    [signals.byEvent],
  );

  /** 카드 한 장의 한 누름 — 초점이든 대기든 **같은 길**로 간다. */
  const actOn = useCallback(
    (card: QueueCard, next: string) => {
      if (acting) return;
      countClickOn(card.event_id);
      if (next === 'acknowledged') void reviewAndAcknowledge(card.event_id);
      else void advance(card.event_id, next);
    },
    [acting, advance, reviewAndAcknowledge, countClickOn],
  );

  /**
   * 숫자 키 한 번. **서버가 허락한 칸이 아니면 아무 일도 안 한다** —
   * 화면이 전이표를 들지 않기 때문이고, 안 드는 것이 이 화면의 성질이다.
   *
   * ★ 슬롯 0(`acknowledged`)만 **판정+접수 한 트랜잭션**을 부른다 — 위 머리말 참조.
   */
  const onStep = useCallback(
    (slot: number) => {
      const target = STEP_SLOTS[slot];
      if (!target || !focus || acting) return;
      if (!(focus.allowed_next ?? []).includes(target)) return;
      // ★ 실제로 요청이 나가는 누름만 센다 — 서버가 허락하지 않은 칸의 키는
      //   아무 일도 안 하므로 「액션」이 아니다.
      actOn(focus, target);
    },
    [focus, acting, actOn],
  );


  useQueueKeys({
    onNext: () => setSelected((n) => Math.min(n + 1, Math.max(cards.length - 1, 0))),
    onPrev: () => setSelected((n) => Math.max(n - 1, 0)),
    onOpen: () => {
      const card = cards[selected];
      if (card) navigate(eventPath(card.event_id));
    },
    onStep,
    onToggleSound: sound.toggle,
    onReload: queue.reload,
  });

  const selectedRing = (index: number) =>
    index === selected ? '2px solid #1677ff' : '2px solid transparent';

  /**
   * 카드 한 장의 **단추 셋** — 초점 카드와 대기 카드가 **같은 것을 그린다.**
   *
   * 한 자리에 모은 이유: 종전에는 초점 카드 안에만 있었고, 대기 카드에 같은 것을 손으로
   * 다시 적으면 다음 턴에 한쪽만 고쳐진다. 두 자리가 갈리면 「큐에서 1클릭」이 카드에
   * 따라 다른 뜻이 된다.
   *
   * ★ 그리는 것은 **서버가 준 `allowed_next` 에 있는 값뿐**이다. 없는 갈래는 회색으로
   *   남기지 않고 **아예 안 그린다** — 못 누르는 단추는 「곧 될 것」으로 읽힌다.
   * ★ 숫자 `(1)(2)(3)` 은 **초점 카드에만** 붙는다. 키가 드는 자리가 거기뿐이라,
   *   대기 카드에 숫자를 적으면 그 숫자가 거짓말이 된다.
   */
  const renderActions = (card: QueueCard, isFocus: boolean) => {
    const { known, allowed } = allowedFor(card);
    return (
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        <Space wrap size={6} data-gx="card-actions" data-gx-event={card.event_id}>
          {allowed.map((next) => {
            const slot = (STEP_SLOTS as readonly string[]).indexOf(next);
            const isAck = next === 'acknowledged';
            //: ★ 서버가 **방금** 403 이라고 한 칸은 더는 안 눌린다(위 머리말).
            //:   회색으로 남기되 **왜 회색인지를 서버의 말로** 옆에 적는다 —
            //:   이유 없는 회색이 「곧 될 것」으로 읽히는 것이지, 이유가 붙은 회색은
            //:   「이 계정으로는 안 되는 일」로 읽힌다.
            const denied = denied403[`${card.event_id}:${next}`];
            return (
              <Button
                key={next}
                type="primary"
                size={isFocus ? 'middle' : 'small'}
                loading={acting}
                disabled={Boolean(denied)}
                title={denied || undefined}
                data-gx="card-action"
                data-gx-next={next}
                data-gx-denied={denied ? '403' : undefined}
                onClick={(ev) => {
                  // 대기 카드는 줄 전체가 「고르기」를 먹는다 — 누름이 위로 퍼지면
                  // 고른 카드가 바뀌면서 사람이 무엇을 눌렀는지 모르게 된다.
                  ev.stopPropagation();
                  actOn(card, next);
                }}
              >
                {isAck ? REVIEW_AND_ACK_LABEL : advanceLabel(next)}
                {isFocus && slot >= 0 ? ` (${slot + 1})` : ''}
              </Button>
            );
          })}

          {/* ★ 오탐은 **이름 붙은 단추**로만 연다 — 숫자 키에 얹으면 1·2·3 의 뜻이
              처리 단계와 판정 사이에서 흔들린다(머리말). 이미 판정된 사건에는
              다시 판정을 묻지 않는다. */}
          {!card.verdict ? (
            <Button
              danger
              size={isFocus ? 'middle' : 'small'}
              loading={acting}
              data-gx="card-action"
              data-gx-next="rejected"
              onClick={(ev) => {
                ev.stopPropagation();
                setRejectingId((id) => (id === card.event_id ? null : card.event_id));
              }}
            >
              {REJECT_LABEL}
            </Button>
          ) : null}

          {/* 「아직 못 들었다」와 「서버가 갈 곳이 없다고 했다」는 **다른 사실**이다. */}
          {!known ? (
            <Text type="secondary" data-gx="allowed-unknown">{ALLOWED_UNKNOWN_NOTE}</Text>
          ) : allowed.length === 0 ? (
            <Text type="secondary" data-gx="allowed-none">{ALLOWED_NONE_NOTE}</Text>
          ) : null}
        </Space>

        {/*
          ★★ [턴 W · P-188] **거절을 그 카드 옆에 적는다.**

            큐 응답의 `allowed_next` 는 「갈 수 있는 곳」이지 「그냥 눌러도 되는 곳」이
            아니다 — 종결된 사건에는 **되돌림**(`closed → in_progress`)이 들어 있고,
            그 칸은 사유가 있어야(400) 열리고 관제팀장만(403) 할 수 있다. 시험
            `test_u1_queue_card_actions.py` 가 이 자리를 잡았다.

            화면은 그 표를 **들지 않는다.** 대신 서버가 낸 **상태코드에 따라 다른 일**을
            한다(D-290 이 셋을 나눠 둔 이유가 이것이다):
              400 → 사유 칸을 열고 **같은 칸으로 다시** 보낸다
              403 → 「팀장이 해야 한다」를 그대로 적는다 (다시 보내 봐야 같다)
              409 → 「그 길은 없다」 — 큐를 다시 읽는다(표가 바뀌었을 수 있다)
        */}
        {actionOn && actionOn.eventId === card.event_id ? (
          <Alert
            type={actionStatus === 400 ? 'warning' : 'error'}
            showIcon
            data-gx="card-refusal"
            data-gx-status={actionStatus}
            message={
              actionStatus === 400
                ? '사유가 있어야 넘어갑니다.'
                : actionStatus === 403
                  ? '이 계정으로는 안 됩니다.'
                  : '거절되었습니다.'
            }
            description={
              <Space direction="vertical" size={6} style={{ width: '100%' }}>
                <Text>{actionError}</Text>
                {actionStatus === 400 ? (
                  <Space.Compact style={{ width: '100%' }}>
                    <Input
                      size="small"
                      placeholder="사유 (기록에 그대로 남습니다)"
                      value={reasonDraft}
                      onChange={(ev) => setReasonDraft(ev.target.value)}
                      onClick={(ev) => ev.stopPropagation()}
                    />
                    <Button
                      size="small"
                      type="primary"
                      loading={acting}
                      disabled={!reasonDraft.trim()}
                      data-gx="card-refusal-retry"
                      onClick={(ev) => {
                        ev.stopPropagation();
                        const reason = reasonDraft.trim();
                        setReasonDraft('');
                        countClickOn(card.event_id);
                        void advance(card.event_id, actionOn.toState, reason);
                      }}
                    >
                      사유를 적고 다시
                    </Button>
                  </Space.Compact>
                ) : (
                  <Button
                    size="small"
                    onClick={(ev) => {
                      ev.stopPropagation();
                      clearActionError();
                      queue.reload();
                    }}
                  >
                    다시 읽기
                  </Button>
                )}
              </Space>
            }
          />
        ) : null}

        {rejectingId === card.event_id ? (
          <Card size="small" title={`오탐 사유 — 사건 ${card.event_id}`}>
            <Space wrap onClick={(ev) => ev.stopPropagation()}>
              {FALSE_POSITIVE_REASONS.map((r) => (
                <Button
                  key={r.code}
                  size="small"
                  loading={acting}
                  onClick={() => onReject(card.event_id, r.label)}
                >
                  {r.label}
                </Button>
              ))}
            </Space>
          </Card>
        ) : null}
      </Space>
    );
  };

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/*
          P-52 킥 문장 — **둘째 자리.** 로그인 화면과 **같은 상수**에서 온다
          (`../constants/kick`). 여기 손으로 다시 적으면 두 자리가 갈리고, 갈린
          문장 둘은 제품 소개가 아니라 장식 둘이다.

          ★ 제목 위에 둔다. 이 화면은 관제요원이 하루 종일 켜 두는 화면이고, 제목
            아래로 내려가면 「가장 급한 하나」와 섞여 사건 정보처럼 읽힌다 —
            이 문장은 사건이 아니라 **제품이 무엇을 하는 물건인지**를 말한다.
          ★ 작고 흐리다. 관제 화면의 주인공은 언제나 카드다.
        */}
        <Text type="secondary" style={{ fontSize: 12 }}>
          {KICK_SENTENCE}
        </Text>

        <Row justify="space-between" align="middle">
          <Col>
            <Space size={4} align="center">
              <Title level={4} style={{ margin: 0 }}>
                {HEADLINE}
              </Title>
              {/* UX-03 — 역할 첫 화면의 「?」. 처음 온 사람이 여기서 시작한다. */}
              <Button
                type="text"
                size="small"
                aria-label="처음 시작하기"
                onClick={() => navigate(`${dsm2Routes.onboarding.path}?role=OPERATOR`)}
              >
                ?
              </Button>
            </Space>
          </Col>
          <Col>
            <Space size={8} wrap>
              <Button size="small" onClick={() => setShowKeys((v) => !v)}>
                단축키
              </Button>
              {/* 상태가 아니라 **누르면 일어나는 일**을 적는다 (사전 §5). */}
              <Button size="small" onClick={sound.audible ? sound.toggle : sound.enable}>
                {sound.audible ? '소리 끄기' : '소리 켜기'}
              </Button>
              <Text type="secondary">
                {queue.loadedAt ? `갱신 ${stamp(queue.loadedAt)}` : ''} · {TIMEZONE_NOTE}
              </Text>
            </Space>
          </Col>
        </Row>

        {/* ★ 안 울리는 이유를 **먼저** 말한다. 조용한 화면은 평온과 구별되지 않는다. */}
        {!sound.audible ? (
          <Alert type="warning" showIcon message="소리가 꺼져 있습니다" />
        ) : null}

        {showKeys ? (
          <ShortcutHelp targetNote="숫자 키는 가장 급한 하나에만 듭니다." />
        ) : null}

        <StateBoundary
          state={queue.state}
          reason={queue.reason} status={queue.status}
          onRetry={queue.reload}
          emptyText="지금 열려 있는 이벤트가 없습니다 — 평온합니다."
        >
          {data ? (
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              {/* ★ 두 수를 **나란히** 둔다. 접힌 것은 카드이지 기록이 아니다. */}
              <Card size="small">
                <Row gutter={16}>
                  <Col>
                    <Statistic title="이벤트(원본 건수)" value={data.total_events} />
                  </Col>
                  <Col>
                    <Statistic title="카드(5분 창 묶음)" value={data.card_total} />
                  </Col>
                  <Col flex="auto">
                    <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                      같은 카메라·같은 유형이{' '}
                      {Math.round(data.window_seconds / 60)}분 창 안에 연속으로 나면
                      카드 한 장에 「×N」으로 묶입니다. <b>이벤트는 접지 않습니다</b> —
                      위 두 수가 다른 것이 그 약속의 증거이고, 통계는 왼쪽 수(이벤트 원본 건수)를 셉니다.
                      {data.sample_capped
                        ? ' ⚠ 표본 상한에 닿았습니다 — 더 오래된 이벤트가 이 화면 밖에 있습니다.'
                        : ''}
                    </Paragraph>
                  </Col>
                </Row>
              </Card>

              {/* ★ [턴 W] 거절은 **그 카드 옆**에 적는다(`renderActions`). 이 띠는
                  어느 카드의 것인지 서버가 말해 주지 않은 거절만 받는다 — 두 자리에
                  같은 말을 두면 사람이 둘을 다른 사건으로 읽는다. */}
              {actionError && !actionOn ? (
                <Alert type="error" showIcon message="거절되었습니다." description={actionError} />
              ) : null}

              {focus ? (
                <div
                  ref={(el) => {
                    rowRefs.current[0] = el;
                  }}
                  style={{ border: selectedRing(0), borderRadius: 8 }}
                  onClick={() => setSelected(0)}
                >
                  <Card
                    title={
                      <CardHead card={focus} signal={signals.byEvent.get(focus.event_id)} />
                    }
                    extra={
                      <Button type="link" onClick={() => navigate(eventPath(focus.event_id))}>
                        상세 열기
                      </Button>
                    }
                  >
                    <Row gutter={16}>
                      <Col xs={24} md={10}>
                        <EventSnapshot
                          eventId={focus.event_id}
                          snapshotPath={focus.snapshot_path}
                          height={240}
                        />
                      </Col>
                      <Col xs={24} md={14}>
                        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                          <div>
                            <Text type="secondary">대응 시계 · 발생 {stamp(focus.occurred_at)}</Text>
                            <ResponseClock
                              occurredAt={focus.occurred_at}
                              closedAt={focus.closed_at}
                              thresholds={data.tier_thresholds_sec}
                              // ★ 순위는 **화면이 센 값**이다(머리말 P-188). 초점이
                              //   곧 「가장 오래 기다린 것」은 아니다 — 서버의 「가장
                              //   급한」은 등급·단계를 함께 보는 다른 질문이다.
                              rankNote={rankNoteOf(ranks.get(focus.event_id))}
                            />
                          </div>

                          {/* ★ 버튼은 서버가 준 `allowed_next` 로만 그린다 —
                              화면이 전이표를 들면 서버가 거절하는 버튼을 그리게 된다.
                              숫자는 **고정 자리**다: 실제로 확인·접수 1 · 조치 시작 2 ·
                              종결 3. `acknowledged` 로 가는 단추만 판정+접수 한
                              트랜잭션을 부른다(WO-01 §5 AC-2 · 머리말 참조).
                              [턴 W] 대기 카드와 **같은 것**을 그린다 — `renderActions`. */}
                          {renderActions(focus, true)}

                          {focus.count > 1 ? (
                            <Alert
                              type="info"
                              showIcon
                              message={`이 카드에 ${focus.count}건이 묶여 있습니다.`}
                              description={`이벤트 id: ${focus.member_event_ids.join(', ')} — 카드만 묶였고 기록은 그대로입니다.`}
                            />
                          ) : null}
                        </Space>
                      </Col>
                    </Row>
                  </Card>
                </div>
              ) : (
                <Alert
                  type="success"
                  showIcon
                  message="지금 가장 급한 사건이 없습니다."
                  description="열려 있는 이벤트가 0건입니다 — 못 가져온 것이 아니라 없습니다."
                />
              )}

              {/*
                ★ [턴 S → 턴 T] **종결 확인 카드** — 현장이 「조치를 마쳤다」고 알린 사건을
                  모아 관제가 **「확인」 한 번으로 종결**한다.

                ★ 실자료다. U3 의 `POST …/field-reply?kind=done` 이 저장한 회신을 서버
                  (`/queue/field-signals`)가 되읽어 낸다 — 시드 예시는 뗐다(턴 T).
                  회신이 없으면 빈 상태 문구다. 회신은 오는데 종류 표시가 0건이면 그 수를
                  적는다 — 「없음」과 「못 읽음」은 다른 사실이다.

                ★ 「확인」은 `POST …/confirm-done` 이고 **서버 기록이 닫는다**(K1 전이표
                  대로 `acknowledged → in_progress → closed` · 화면은 전이표를 들지
                  않는다). 접수 전(`occurred`)이면 서버가 409 로 거절하고 그 말을 그대로
                  적는다 — 그 사건은 먼저 접수(키 1)해야 한다.
              */}
              {/*
                ★★ P-222 (2026-09-21 · 턴 AA · 세종 실사용 점검) — **0건이면 한 줄이다.**

                  세종이 고객 자리에서 적었다: *「「조치를 마쳤다고 알려 온 사건이
                  없습니다」가 화면 절반을 차지한다.」* 제목 · 테두리 · 빈 본문으로
                  한 화면을 먹는 0건 칸은, **있는 일감보다 없는 일감을 먼저 보게 한다.**

                ★ **지우지 않는다. 접는다.** 칸을 없애면 「조치 완료 회신이 오는 자리가
                  있다」는 사실이 화면에서 사라지고, 회신이 처음 왔을 때 아무도 그
                  자리를 모른다. 그래서 한 줄은 남고 **0 이라고 적는다.**
                ★ **진짜 0 일 때만 접는다.** 「배선 대기」(회신은 오는데 종류 표시가
                  0건)와 거절 경고는 **다른 사실**이라 접지 않는다 — 접는 순간
                  「없음」과 「못 읽음」이 한 줄이 된다(`WIRING_WAITING_NOTE` 의 그 자리).
              */}
              {signals.doneSignals.length === 0 && !signals.confirmError
                && !(!signals.wired && signals.replyTotal > 0) ? (
                <Text type="secondary" data-gx="close-confirm-empty">
                  {CLOSE_CONFIRM_EMPTY_ONE_LINE}
                </Text>
              ) : (
              <Card size="small" title={CLOSE_CONFIRM_TITLE} data-gx="close-confirm-card">
                {signals.confirmError ? (
                  <Alert
                    type="error"
                    showIcon
                    message="종결 확인이 거절되었습니다."
                    description={signals.confirmError}
                    style={{ marginBottom: 8 }}
                  />
                ) : null}
                {signals.doneSignals.length === 0 ? (
                  <Space direction="vertical" size={4}>
                    <Text type="secondary" data-gx="close-confirm-empty">{CLOSE_CONFIRM_EMPTY}</Text>
                    {!signals.wired && signals.replyTotal > 0 ? (
                      <Space size={8} wrap>
                        <Tag color="processing">{WIRING_WAITING_LABEL}</Tag>
                        <Text type="secondary">
                          회신 {signals.replyTotal}건이 왔지만 「지원 요청」·「조치 완료」 표시가
                          붙은 것은 0건입니다. {SUPPORT_WAITING_NOTE}
                        </Text>
                      </Space>
                    ) : null}
                  </Space>
                ) : (
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    {signals.doneSignals.map((s) => (
                      <Row
                        key={s.event_id}
                        align="middle"
                        gutter={12}
                        style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}
                        data-gx="close-confirm-row"
                        data-gx-event={s.event_id}
                      >
                        <Col flex="auto">
                          <Space size={6} wrap>
                            <Text strong>사건 {s.event_id}</Text>
                            <Tag>{labelOf(RESPONSE_STATE_LABEL, s.response_state)}</Tag>
                            <Text type="secondary">{s.last_author}</Text>
                            <Text>{s.action_done_text}</Text>
                          </Space>
                        </Col>
                        <Col>
                          <Button
                            type="primary"
                            loading={signals.confirming}
                            disabled={acting}
                            data-gx="close-confirm-button"
                            onClick={() => {
                              countClick('u1_handle_event');
                              void signals.confirmDone(s.event_id).then((out) => {
                                if (out) {
                                  if (focus?.event_id === s.event_id) finishMetric('u1_handle_event');
                                  queue.reload();
                                }
                              });
                            }}
                          >
                            {CLOSE_CONFIRM_BUTTON}
                          </Button>
                        </Col>
                      </Row>
                    ))}
                  </Space>
                )}
              </Card>
              )}

              {/* 나머지 큐. 초점 하나 아래에 **작게** 둔다 — 여기가 커지면 다시 목록이 된다. */}
              <Card size="small" title={`대기 카드 ${data.queue.length}장`}>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {/*
                    ★ [턴 W · P-188] **순위의 분모를 여기서 말한다.** 카드마다 「N건 중
                      k번째」라고 적는데 그 N 이 어디서 온 수인지 화면이 안 적으면,
                      사람은 그것을 「대기 카드 수」로 읽는다 — 다른 수다(종결된 카드는
                      시계가 멈춰 순위에 들지 않는다). 0 이면 **0 이라고 적는다.**
                  */}
                  <Text type="secondary" style={{ fontSize: 12 }} data-gx="rank-denominator">
                    {rankTotal === 0
                      ? '시계가 도는 사건이 0건입니다 — 경과 순위를 매기지 않습니다.'
                      : `경과 순위는 시계가 도는 ${rankTotal}건(초점 카드 포함) 중에서 셉니다.`}
                  </Text>
                  {data.queue.length === 0 ? (
                    <Text type="secondary">대기 중인 카드가 없습니다.</Text>
                  ) : null}
                  {data.queue.map((card, i) => {
                    const index = focus ? i + 1 : i;
                    return (
                      <div
                        key={`${card.stream_monitor_id}-${card.event_type}-${card.event_id}`}
                        ref={(el) => {
                          rowRefs.current[index] = el;
                        }}
                        style={{ border: selectedRing(index), borderRadius: 6 }}
                        onClick={() => setSelected(index)}
                      >
                        <Row
                          align="middle"
                          gutter={12}
                          style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}
                        >
                          <Col flex="auto">
                            <CardHead card={card} signal={signals.byEvent.get(card.event_id)} />
                            <div>
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                발생 {stamp(card.occurred_at)}
                              </Text>
                            </div>
                            {/* ★★ [턴 W · UX-33 · P-188] **상세로 들어가지 않고 여기서 누른다.**
                                초점 카드와 같은 것을 그린다 — 다만 숫자 (1)(2)(3) 은 안 붙는다
                                (키는 초점 하나에만 든다 · 머리말). */}
                            <div style={{ marginTop: 6 }}>
                              {renderActions(card, false)}
                            </div>
                          </Col>
                          <Col>
                            <ResponseClock
                              occurredAt={card.occurred_at}
                              closedAt={card.closed_at}
                              thresholds={data.tier_thresholds_sec}
                              compact
                              rankNote={rankNoteOf(ranks.get(card.event_id))}
                            />
                          </Col>
                          <Col>
                            <Button size="small" onClick={() => navigate(eventPath(card.event_id))}>
                              열기
                            </Button>
                          </Col>
                        </Row>
                      </div>
                    );
                  })}
                </Space>
              </Card>
            </Space>
          ) : null}
        </StateBoundary>
      </Space>
    </Main>
  );
}
