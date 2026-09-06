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
import { dsm2Routes } from '../routes';
import { EVENT_TYPE_LABEL, labelOf, SEVERITY_COLOR, SEVERITY_ICON, SEVERITY_LABEL } from '../severity';
import { linkStatusBadge, linkStatusLabel } from '../copy';
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

  const events = useDsmResource<{ total: number; events: EventRow[] }>(
    () => dsmGet(dsmEndpoint.events, { limit: 10 }),
    [],
    { refreshMs: REFRESH_MS, isEmpty: (v) => (v?.events?.length ?? 0) === 0 },
  );

  /**
   * UX-08 — 새 탐지가 나면 **새로고침 없이** 목록이 다시 읽힌다.
   * ★ 덤이지 바닥이 아니다: 소켓이 안 붙어도 주기 갱신이 화면을 계속 살린다.
   */
  useDetectionPing(() => {
    frame.reload();
    events.reload();
  });

  const openEvent = useCallback(
    (id: number) => navigate(`/dsm/events/${id}`),
    [navigate],
  );

  const link = frame.data?.link;

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

        <StateBoundary state={frame.state} reason={frame.reason} status={frame.status} onRetry={frame.reload}>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={6}>
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
            <Col xs={24} md={18}>
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

        <Card
          size="small"
          title="최근 이벤트"
          extra={<a onClick={() => navigate('/dsm/events')}>전체 목록</a>}
        >
          <StateBoundary
            state={events.state}
            reason={events.reason} status={events.status}
            onRetry={events.reload}
            emptyText="최근 이벤트가 없습니다. (요청은 성공했고 0건입니다)"
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
                  width: 90,
                  render: (v: string) => labelOf(EVENT_TYPE_LABEL, v),
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
