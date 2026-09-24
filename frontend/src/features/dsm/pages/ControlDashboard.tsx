/**
 * 화면 ① **관제 대시보드** — E2E-1 의 첫 칸 (D-371 ①).
 *
 * ★ 이 화면이 하는 일은 셋이다. 그 밖의 것을 여기서 하지 않는다:
 *     ① 이 사람이 **어느 프리셋으로 떨어졌는지** 보여 준다 (K3 · U3)
 *     ② **5상태의 분모와 분자**를 보여 준다 (F-09 AC-09 ①)
 *     ③ **연계 상태 3표시**를 상단에 늘 띄운다 (계약 §2.2-2 장애격리)
 *
 * ★ 왜 프리셋을 **화면에 적나.** 「매핑을 못 찾아 가장 좁은 화면으로 떨어졌다」는
 *   상태는 서버만 알고 사용자는 모른다. 그러면 「원래 이런 화면인가 보다」가 되고,
 *   설정 누락이 영원히 안 보인다 — `preset_matched=false` 를 **눈에 보이게** 둔다 (D-290).
 *
 * ★ 「끊김」이어도 **이 화면은 계속 동작한다** (DA-03 §2-3). SDN 표시만 낮춘다.
 *   그것이 계약 §2.2-2 「일방 장애 시 타방 단독 동작」을 사람이 눈으로 보는 자리다.
 */
import { Alert, Badge, Button, Card, Col, Popover, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Main } from 'rj-core';

import { dsmEndpoint, dsmGet } from '../api';
import AutoAnalysisNotice from '../components/AutoAnalysisNotice';
import StateBoundary from '../components/StateBoundary';
import { useDsmResource } from '../hooks/useDsmResource';
import { useDetectionPing } from '../hooks/useDetectionPing';
import type { CameraPulse } from '../hooks/useCameraGrid';
import { dsm2Routes } from '../routes';
import { EVENT_TYPE_LABEL, labelOf, SEVERITY_COLOR, SEVERITY_ICON, SEVERITY_LABEL } from '../severity';
import { CAMERA_COPY, dataSourceBadge, linkStatusBadge, linkStatusLabel } from '../copy';
import { stamp, TIMEZONE_NOTE } from '../time';
import type { DashboardFrame, EventRow } from '../types';

const { Text, Title } = Typography;

/** 부분 갱신 간격. 재난 화면은 사람이 새로고침을 누르고 있을 수 없다. */
const REFRESH_MS = 15_000;

/* ★ 표시 이름은 **사전 한 곳**에서만 온다 (P-27 · `../copy`). 화면마다 자기 표를 들면
   같은 상태가 화면마다 다른 말로 불리고, 그중 하나는 반드시 늙는다. */

/**
 * F-09 다섯 상태의 **표시 이름**. 서버가 내는 열거값을 그대로 그리면 화면에
 * 「data」 「loading」 이 뜬다 — 영문 열거값은 사용자 본문의 자리가 아니다(GX-COPY §4).
 *
 * ★ 모르는 값이 오면 **원문을 그린다.** 여기 없는 상태가 생겼다는 사실이 안 보이는
 *   것보다 낫다 — 표가 열거보다 짧다는 사실 자체는 아무도 못 본다(D-286).
 */
const PANEL_STATE_LABEL: Record<string, string> = {
  data: '정상',
  loading: '불러오는 중',
  empty: '비어 있음',
  error: '오류',
  forbidden: '권한 없음',
};

/**
 * K3 프리셋의 **표시 이름**. 앞판은 서버 값(`OPERATOR` · `MANAGER` · `BOSS`)을
 * 첫 화면 큰 글씨로 그대로 그렸다 — 영문 열거값이다(GX-COPY §4).
 * ⚠ 값은 계약 쪽이고 여기서는 **표시만** 바꾼다.
 */
const PRESET_LABEL: Record<string, string> = {
  OPERATOR: '관제요원 화면',
  MANAGER: '관제팀장 화면',
  BOSS: '기관장 화면',
};

export default function ControlDashboard() {
  const navigate = useNavigate();

  const frame = useDsmResource<DashboardFrame>(
    () => dsmGet<DashboardFrame>(dsmEndpoint.dashboardFrame),
    [],
    { refreshMs: REFRESH_MS },
  );

  /**
   * ★★ P-220 (2026-09-21 · 턴 AA) — **이 표는 탐침을 안 본다.**
   *
   * 세종이 고객 자리에 앉아 적었다: *「최근 이벤트 10줄이 전부 `gxprobe-…` 캡처용
   * 카메라. 첫 화면의 첫 줄이 우리 탐침이다.」* P-193 이 요약·큐·발송을 걸렀는데
   * 이 표만 남아 있었다 — D-497(운영자 목록은 열어 둔다)의 **그늘**이다.
   *
   * ★ **거르는 일은 서버가 한다.** 이 화면이 10줄을 받아 자기가 걸러 내면 상한 밖의
   *   사건이 **없는 것**이 되고, 「최근 10건」이 「탐침을 뺀 나머지 중 10건」이 아니라
   *   「10건 중 탐침을 뺀 몇 건」이 된다(DA-04 「필터는 전부 서버에서」).
   *   그래서 여기 있는 것은 **한 줄의 부재**다: `include_probe` 를 **안 청한다.**
   *   서버(`apps/dsm/api.py::events`)의 기본값이 「안 준다」이고, 거르는 실행은
   *   커널의 `common.probe_marker.exclude_probe` **정의 하나**다.
   * ★ 탐침을 봐야 하는 자리는 **남아 있다** — `GET /api/dsm/events?include_probe=true`
   *   (운영자 전용 목록). 감춘 것이 아니라 **고객 화면에서 세지 않는 것**이다.
   */
  const events = useDsmResource<{ total: number; events: EventRow[] }>(
    () => dsmGet(dsmEndpoint.events, { limit: 10 }),
    [],
    { refreshMs: REFRESH_MS, isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
  );

  /**
   * ★★ 온보딩 U1#2 (2026-09-21 · 턴 AB) — **카메라 정상/이상 수.**
   *
   * 이 행은 네 턴 동안 ◐ 상한이었고 사유는 늘 같은 한 줄이었다:
   * *「프레임·5상태·연계 상태는 실재. **카메라 정상/이상 수는 프레임에 없다** —
   * 패널 상태이지 카메라 상태가 아니다」*(`onboarding_48.md` U1#2).
   * 「화면 점검 3/3」은 **우리 화면이 그려졌는가**이지 **현장이 보이는가**가 아니다.
   * 당직을 시작하는 사람이 첫 화면에서 물어야 하는 것은 뒤쪽이다.
   *
   * ★ **새 문을 만들지 않았다.** 그 수는 이미 서 있는 문이 낸다 —
   *   `GET /api/dsm/cameras/pulse`(UX-23 · 카메라 격자가 쓰는 그 문)의 `counts`.
   *   프레임에 칸을 더하면 「카메라 상태」가 두 곳에서 나고, 두 곳은 어긋난다(D-212).
   * ★ **문턱은 화면에 없다.** 살았는지 죽었는지는 서버의 `alive` 한 칸이 말하고,
   *   몇 분이 문턱인지도 서버가 `rules.pulse_timeout_seconds` 로 말해 준다.
   *   화면이 제 문턱(예: 5분)을 들면 규칙이 바뀌는 날 화면만 옛말이 된다.
   * ★ 못 부르면 **0이 아니라 회색**이다 — `StateBoundary` 가 그 자리를 지킨다.
   *   「이상 0대」와 「못 물어봤다」를 같은 글자로 그리면 두절이 안 보인다.
   */
  const pulse = useDsmResource<CameraPulse>(
    () => dsmGet<CameraPulse>(dsmEndpoint.cameraPulse),
    [],
    { refreshMs: REFRESH_MS },
  );

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(() => {
    frame.reload();
    events.reload();
    pulse.reload();
  });

  const openEvent = useCallback(
    (id: number) => navigate(`/dsm/events/${id}`),
    [navigate],
  );

  const link = frame.data?.link;

  /* ★ 셋을 **세 값으로** 든다 (서버 `camera_pulse` 머리말과 같은 가름):
       정상        맥박이 문턱 안에 왔다
       이상        맥박이 문턱을 넘겨 안 왔다  = 전체 − 정상
       아직 응답 없음  한 장도 온 적이 없다     ⊂ 이상
     셋을 한 값으로 접으면 **방금 등록한 카메라와 케이블이 끊긴 카메라**가 같은
     그림이 된다(D-290). 그래서 셋째 줄은 지우지 않고 「그중 N대」로 적는다.
     ⚠ 여기에 뺄셈 말고 **판정은 없다.** 문턱은 서버가 이미 적용해 `alive` 로 준다. */
  const counts = pulse.data?.counts;
  const cameraTotal = counts?.total ?? 0;
  const cameraAlive = counts?.alive ?? 0;
  const cameraDown = Math.max(cameraTotal - cameraAlive, 0);
  const cameraNeverSeen = counts?.never_seen ?? 0;
  const pulseTimeoutMin = Math.round(
    (pulse.data?.rules?.pulse_timeout_seconds ?? 0) / 60,
  );

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        {/* ★ 자동 분석 고지 — 로그인 뒤 첫 화면에서 **먼저** 읽힌다 (차선 L · LAW-06).
            문장은 한 곳에서만 정한다: 여기 복사하면 알림 본문과 갈린다. */}
        <AutoAnalysisNotice />
        <Row justify="space-between" align="middle">
          <Col>
            <Space size={4} align="center">
              <Title level={4} style={{ margin: 0 }}>
                관제 대시보드
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
            <Space size="large">
              {/* ③ 연계 상태 — **끊김이어도 아래는 계속 동작한다**

                  ★ [P-27 · 2026-09-25 사고] 앞판은 `title={link.reason}` 으로 서버가 준
                    사유를 **툴팁에** 걸었다. 그 문단에는 상대사명·계약번호·조항이 들어
                    있었고, 마우스를 얹으면 그대로 떴다. 지금 화면이 받는 것은 상태 하나다. */}
              {link && (
                <Badge status={linkStatusBadge(link.status)} text={linkStatusLabel(link.status)} />
              )}
              <Text type="secondary">
                {frame.loadedAt ? `갱신 ${stamp(frame.loadedAt)}` : ''}
              </Text>
            </Space>
          </Col>
        </Row>

        {/* ① 프리셋 — 못 찾아 떨어진 상태를 **눈에 보이게** 둔다
            ★ [UX-20/UX-21 · 2026-09-26] 앞판은 설정 상수 이름(`K3_ROLE_PRESET_MAP`)을
              본문에 적었다. 그것은 관리자의 말이고 첫 로그인한 당직자의 말이 아니다 —
              사전(GX-COPY §2)이 이 문장을 이미 정해 두었다. 상수 이름은 관리자 자리로
              물러난다(설정 이름을 아는 사람은 이 경고 없이도 찾아간다). */}
        {frame.data && !frame.data.preset_matched && (
          <Alert
            type="warning"
            showIcon
            message="화면 구성이 아직 정해지지 않았습니다."
            description="관리자에게 문의하십시오. 지금 보이는 것이 이 계정의 전부가 아닐 수 있습니다."
          />
        )}

        {/* ★ 장애격리를 **배치로** 지킨다 (계약 §2.2-2 · DA-03 §2-3).
            프레임 칸과 카메라 칸은 **서로 다른 문**에서 온다. 한 울타리에 넣으면
            프레임이 죽는 날 카메라 수까지 같이 회색이 되고, 그때 당직자는
            「현장이 안 보인다」와 「화면 한 칸이 안 그려졌다」를 못 가른다. */}
        <Row gutter={[16, 16]}>
          <Col xs={24} md={15}>
            <StateBoundary state={frame.state} reason={frame.reason} status={frame.status} onRetry={frame.reload}>
              <Row gutter={[16, 16]}>
                <Col xs={24} md={10}>
                  <Card size="small">
                    <Statistic
                      title="화면 구성"
                      value={
                        frame.data?.preset
                          ? (PRESET_LABEL[frame.data.preset] ?? frame.data.preset)
                          : '—'
                      }
                      valueStyle={{ fontSize: 20 }}
                      suffix={
                        <Tag color={frame.data?.preset_matched ? 'green' : 'orange'}>
                          {frame.data?.preset_matched ? '역할에 맞춰 설정됨' : '기본값'}
                        </Tag>
                      }
                    />
                  </Card>
                </Col>
                {/* ② 5상태 — **분모를 함께 낸다.** 「정상 3칸」만 보면 전체가 3인지 30인지 모른다
                    ★ [UX-20 · 2026-09-26] 앞판은 이 계수기를 **첫 화면 본문에 크게** 폈고,
                      칸 이름이 서버 열거값 그대로라 화면에 「data 0/0 · loading 0/0 …」이
                      떴다(결함 #4). 이것은 **우리가 화면을 점검하는 수**이지 당직자가
                      읽을 수가 아니다 — 사전은 「사용자 화면에서 제거 · 관리자 자리로」라고
                      적었다(GX-COPY §2).
                      ⚠ **버리지 않는다.** F-09 AC-09 ①이 요구하는 분자·분모는 그대로 있고,
                        「?」 뒤로 한 칸 물러났을 뿐이다 — 없애면 그 조항을 못 보인다. */}
                <Col xs={24} md={14}>
                  <Card size="small" title="화면 점검">
                    <Space size="small" wrap>
                      <Text type="secondary">
                        화면 {frame.data?.panel_total ?? 0}칸이 정상적으로 그려졌습니다.
                      </Text>
                      <Popover
                        title="화면 점검 내역"
                        content={
                          <Space direction="vertical" size={2} style={{ maxWidth: 320 }}>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              각 칸이 다섯 상태 중 어디에 있는지 셉니다. 분모는 전체 칸 수
                              {' '}{frame.data?.panel_total ?? 0}입니다.
                            </Text>
                            {(frame.data?.five_states ?? []).map((s) => (
                              <Text key={s} style={{ fontSize: 12 }}>
                                {PANEL_STATE_LABEL[s] ?? s}{' '}
                                {frame.data?.state_counts?.[s] ?? 0} / {frame.data?.panel_total ?? 0}
                              </Text>
                            ))}
                          </Space>
                        }
                      >
                        <Button type="text" size="small" aria-label="화면 점검 설명">
                          ?
                        </Button>
                      </Popover>
                    </Space>
                  </Card>
                </Col>
              </Row>
            </StateBoundary>
          </Col>

          {/* ★★ 온보딩 U1#2 — **카메라 정상 / 이상** (2026-09-21 · 턴 AB · 차선 U1)
              이 칸이 이 행의 ◐ 상한이었다. 위 「화면 점검」은 우리 화면이 그려졌는지를
              세고, 이 칸은 **현장이 보이는지**를 센다 — 다른 질문이다. */}
          <Col xs={24} md={9}>
            <Card
              size="small"
              title="카메라 정상 / 이상"
              extra={
                <a onClick={() => navigate(dsm2Routes.cameraGrid.path)}>카메라 격자</a>
              }
            >
              <StateBoundary
                state={pulse.state}
                reason={pulse.reason}
                status={pulse.status}
                onRetry={pulse.reload}
                emptyText="등록된 카메라가 없습니다."
              >
                {cameraTotal === 0 ? (
                  /* ★ 분모 0을 「정상 0 · 이상 0」으로 그리지 않는다 — 그 그림은
                     「전부 멀쩡하다」로 읽힌다. 0대일 때는 **0대라고 적는다.** */
                  <Text type="secondary">등록된 카메라가 없습니다.</Text>
                ) : cameraAlive === 0 ? (
                  /**
                   * ★★ P-316(2026-09-24 · 턴 U온) — **카메라는 있는데 응답이 0대.**
                   *
                   * 탐침을 걸러내니 남은 진짜 카메라는 전부 `never_seen` 이었다
                   * (실카메라 연결은 현장 뒤). 「0 정상 · N 이상」 계수기만 보이면
                   * 당직자는 **문 하나가 죽은 것**으로 읽지, **아직 아무 카메라도
                   * 안 붙었다**로 읽지 않는다 — 다른 사실이다. 그래서 이 갈래는
                   * 계수기 대신 **정직한 빈 화면 + 다음 손**을 그린다(P-312 부품).
                   * 다음 손은 「카메라 주소 채우기」(`dsm2Routes.cameraAddress`) —
                   * 응답 없음의 가장 흔한 원인이 주소 미설정이기 때문이다.
                   * ⚠ 수(N)는 이 응답의 `cameraTotal` 에서 읽는다 — 화면에 5를
                   *   박아 적지 않는다.
                   */
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    <Text>
                      카메라 {cameraTotal}대 중 응답 0 — 카메라 연결 확인으로
                    </Text>
                    <Text type="secondary">
                      {cameraNeverSeen === cameraTotal
                        ? '설치한 뒤 아직 한 번도 화면이 오지 않았습니다.'
                        : '카메라가 아직 화면을 보내지 않았습니다.'}{' '}
                      아래에서 카메라 주소를 확인하십시오.
                    </Text>
                    <Button
                      size="small"
                      onClick={() => navigate(dsm2Routes.cameraAddress.path)}
                    >
                      {CAMERA_COPY.fillAddress}
                    </Button>
                  </Space>
                ) : (
                  <Space direction="vertical" size={4} style={{ width: '100%' }}>
                    <Space size="middle" align="baseline" wrap>
                      <Space size={4} align="baseline">
                        <Text style={{ fontSize: 26, fontWeight: 600, color: '#389e0d' }}>
                          {cameraAlive}
                        </Text>
                        <Text type="secondary">정상</Text>
                      </Space>
                      <Space size={4} align="baseline">
                        <Text
                          style={{
                            fontSize: 26,
                            fontWeight: 600,
                            color: cameraDown > 0 ? '#cf1322' : undefined,
                          }}
                        >
                          {cameraDown}
                        </Text>
                        <Text type="secondary">이상</Text>
                      </Space>
                      {/* 분모를 **함께** 낸다 (D-301). 「이상 2대」만 보면 전체가
                          3대인지 300대인지 모른다. */}
                      <Text type="secondary">전체 {cameraTotal}대</Text>
                      <Popover
                        title="정상과 이상을 무엇으로 가르나"
                        content={
                          <Space direction="vertical" size={2} style={{ maxWidth: 340 }}>
                            <Text style={{ fontSize: 12 }}>
                              카메라가 보낸 화면이 마지막으로 도착한 시각으로 가릅니다.
                              {pulseTimeoutMin > 0
                                ? ` ${pulseTimeoutMin}분 넘게 아무것도 오지 않으면 「이상」입니다.`
                                : ''}
                            </Text>
                            <Text style={{ fontSize: 12 }}>
                              「이상」은 카메라가 꺼졌을 수도, 회선이 끊겼을 수도
                              있습니다. 어느 카메라인지는 「카메라 격자」에서 한 대씩
                              보입니다.
                            </Text>
                          </Space>
                        }
                      >
                        <Button type="text" size="small" aria-label="정상과 이상의 기준">
                          ?
                        </Button>
                      </Popover>
                    </Space>
                    {cameraNeverSeen > 0 && (
                      /* ★ 「끊겼다」와 「아직 한 번도 안 왔다」는 다른 사실이다.
                         접으면 어제 설치한 카메라가 오늘 끊긴 카메라로 보인다. */
                      <Text type="secondary">
                        그중 {cameraNeverSeen}대는 설치한 뒤 아직 한 번도 화면이 오지
                        않았습니다.
                      </Text>
                    )}
                  </Space>
                )}
              </StateBoundary>
            </Card>
          </Col>
        </Row>

        <Card
          size="small"
          title="최근 이벤트"
          extra={<a onClick={() => navigate('/dsm/events')}>전체 목록</a>}
        >
          <StateBoundary
            state={events.state}
            reason={events.reason} status={events.status}
            onRetry={events.reload}
            emptyText="최근 이벤트가 없습니다. 새 사건이 오면 바로 뜨니 기다리시면 됩니다."
          >
            <Table<EventRow>
              size="small"
              rowKey="event_id"
              pagination={false}
              dataSource={events.data?.events ?? []}
              onRow={(row) => ({ onClick: () => openEvent(row.event_id) })}
              columns={[
                {
                  title: '등급',
                  dataIndex: 'severity',
                  width: 110,
                  render: (v: string) => (
                    <Tag color={SEVERITY_COLOR[v] ?? 'default'}>
                      {SEVERITY_ICON[v] ?? '●'} {SEVERITY_LABEL[v] ?? v}
                    </Tag>
                  ),
                },
                {
                  title: '유형',
                  dataIndex: 'event_type',
                  width: 150,
                  /**
                   * ★★ P-227 (2026-09-21 · 턴 AB · 차선 U1) — **훈련 배지가 여기
                   *   없었다.**
                   *
                   * 실측: `exclude_probe` 가 탐침 12줄을 이 표에서 뺀 **뒤에도**
                   * 게이트 카메라 이름(`gxprobe-…`)이 붙은 줄 넷이 남는다. 그 넷은
                   * 탐침이 아니라 **훈련 표식**(`data_source=drill`)이고, 제품은
                   * 훈련을 **센다**(P-201) — 그래서 표식으로 걸러도 안 빠지고,
                   * 빠져서도 안 된다.
                   *
                   * ★ **이름으로 거르지 않는다**(D-280). 이름으로 세면 ① 이름을
                   *   바꾸는 날 수가 바뀌고 ② 같은 카메라로 심은 **다른 종류**가
                   *   전부 탐침이 된다 — ②는 턴 Z 에 실제로 일어났다.
                   * ★ 그래서 **거르는 대신 말한다.** 서버는 이미 줄마다
                   *   `data_source` 를 보내고 있었고(`api.py::events`),
                   *   `copy.ts::dataSourceBadge` 도 「훈련」이라는 말을 들고 있었다.
                   *   없던 것은 **첫 화면에서 그 둘을 잇는 한 줄**이다 —
                   *   목록(`EventList`)과 큐(`FocusQueue`)는 이미 그리고 있었는데
                   *   **대시보드만 안 그렸다**[실측 grep]. 첫 화면이 마지막으로
                   *   남은 자리였다.
                   * ★ 실운영이면 `dataSourceBadge` 가 `null` 을 낸다 — 평상에는
                   *   아무것도 안 붙는다. 평상에 배지를 붙이면 배지가 뜻을 잃는다.
                   */
                  render: (v: string, row: EventRow) => (
                    <Space size={4} wrap>
                      <span>{labelOf(EVENT_TYPE_LABEL, v)}</span>
                      {dataSourceBadge(row.data_source) ? (
                        <Tag color="blue" data-gx="event-data-source">
                          {dataSourceBadge(row.data_source)}
                        </Tag>
                      ) : null}
                    </Space>
                  ),
                },
                { title: '카메라', dataIndex: 'stream_monitor_name', ellipsis: true },
                {
                  title: '발생',
                  dataIndex: 'occurred_at',
                  width: 170,
                  render: (v: string) => stamp(v),
                },
              ]}
            />
          </StateBoundary>
        </Card>

        <Text type="secondary">{TIMEZONE_NOTE}</Text>
      </Space>
    </Main>
  );
}
