/**
 * UX-23 **카메라 격자** — 여러 대를 한눈에 · 자동 순회 · 응답 없는 카메라 표시
 * (차선 C2 · 2026-09-05).
 *
 * 무엇이 문제였나
 * ---------------
 * 이 자리에는 인수 자산인 **드론 기체용 멀티스트림 화면**이 서 있었다. 그 화면이
 * 그리는 것은 기체 3대이고, 관제요원이 봐야 하는 것은 **현장에 걸린 카메라 전부**다.
 * 고치지 않고 **우리 층에 새로 세운다** — 그 화면은 그 화면의 일을 계속 한다.
 *
 * 무엇을 그리나
 * -------------
 *   ① 카메라 타일 격자. 응답이 없는 카메라는 **한눈에 다르다.**
 *   ② 자동 순회 — 대수가 한 화면을 넘으면 쪽을 넘겨 가며 보여 준다.
 *   ③ 「응답 없음」 수를 **분모와 함께** 머리에 적는다.
 *
 * ★ **문턱이 이 파일에 없다.** 어느 카메라가 응답 없음인지는 서버가 정한다
 *   (`alive` 한 칸). 화면이 자기 문턱을 들면 규칙이 바뀌는 날 화면만 옛말이 되고,
 *   옛말이 된 화면은 아무 소리도 내지 않는다.
 *
 * ★ 「없다」와 「언제부터 없다」는 다른 사실이다. 마지막 응답 시각이 있는 카메라에는
 *   그 한 줄을 적고, **한 번도 응답이 없던 카메라에는 적지 않는다** — 없는 것을
 *   0분 전으로 그리면 방금 등록한 카메라가 방금 끊긴 카메라로 보인다.
 *
 * ⚠ **영상 바이트는 아직 이 화면에 없다.** 우리 카메라의 원본은 브라우저가 바로
 *   못 여는 주소이고, 그것을 여는 길은 이 턴에 재지 못했다. 없는 것을 있는 척
 *   그리지 않는다 — 타일은 카메라의 **상태**를 말하고, 그 이상을 말하지 않는다.
 */
import { Alert, Button, Card, Col, Row, Space, Tag, Typography } from 'antd';
import { Main } from 'rj-core';

import StateBoundary from '../components/StateBoundary';
import { useCameraGrid } from '../hooks/useCameraGrid';
import type { CameraPulseRow } from '../hooks/useCameraGrid';
import { relative, TIMEZONE_NOTE } from '../time';

const { Text, Title } = Typography;

/** 이 화면에만 있는 글자 — 검수 촬영의 단언 대상이다. */
export const HEADLINE = '카메라 격자';

/** 응답 없는 타일의 색. **색만으로 구분하지 않는다** — 글자를 함께 둔다. */
const DOWN_COLOR = '#cf1322';

function CameraTile({ row, now }: { row: CameraPulseRow; now: Date }) {
  const down = !row.alive;
  return (
    <Card
      size="small"
      style={{
        height: '100%',
        borderColor: down ? DOWN_COLOR : undefined,
        borderWidth: down ? 2 : 1,
        background: down ? '#fff1f0' : undefined,
      }}
      styles={{ body: { padding: 12 } }}
    >
      <Space direction="vertical" size={4} style={{ width: '100%' }}>
        <Text strong ellipsis={{ tooltip: row.name }}>
          {row.name || '이름 없는 카메라'}
        </Text>
        {down ? (
          <Tag color="error" style={{ marginInlineEnd: 0 }}>
            응답 없음
          </Tag>
        ) : null}
        {/* 「없다」와 「언제부터 없다」를 가른다 — 한 번도 응답이 없으면 이 줄이 없다.
            없는 것을 「0분 전」으로 그리면 방금 등록한 카메라가 방금 끊긴 카메라가 된다. */}
        {row.last_seen_at ? (
          <Text type="secondary" style={{ fontSize: 12 }}>
            마지막 응답 {relative(row.last_seen_at, now)}
          </Text>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>
            응답을 받은 적이 없습니다.
          </Text>
        )}
      </Space>
    </Card>
  );
}

export default function CameraGridPage() {
  const grid = useCameraGrid();
  const { pulse } = grid;
  const now = pulse.loadedAt ?? new Date();
  const counts = pulse.data?.counts;

  return (
    <Main>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <Row justify="space-between" align="middle" gutter={[8, 8]}>
          <Col>
            <Title level={4} style={{ margin: 0 }}>
              {HEADLINE}
            </Title>
          </Col>
          <Col>
            <Space size={8} wrap>
              <Text type="secondary">
                {grid.pageIndex + 1} / {grid.pageCount}
              </Text>
              {/* ★ 쪽이 하나뿐이면 **누를 수 없게** 둔다. 감추지 않는 이유: 감추면
                  「이 화면에 순회가 없다」와 「지금은 넘길 쪽이 없다」가 같은 그림이
                  되고, 그 둘은 다른 사실이다(D-290). 누를 수 없는 이유는 아래
                  안내에 적는다 — 이유 없는 회색 단추는 고장으로 읽힌다. */}
              <Button
                onClick={grid.toggleRotate}
                disabled={grid.pageCount <= 1}
                title={
                  grid.pageCount <= 1
                    ? '카메라가 모두 한 화면에 들어와 넘길 쪽이 없습니다.'
                    : undefined
                }
              >
                {/* 상태가 아니라 **누르면 일어나는 일**을 적는다. */}
                {grid.rotating ? '순회 멈춤' : '자동 순회'}
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 머리 한 줄. **분모와 함께** 적는다 — 「2대」만 보면 전체가 3인지 300인지 모른다. */}
        {counts ? (
          <Alert
            type={grid.downCount > 0 ? 'warning' : 'success'}
            showIcon
            message={
              grid.downCount > 0
                ? `응답 없음 ${grid.downCount}대 (전체 ${counts.total}대)`
                : `전체 ${counts.total}대가 응답하고 있습니다.`
            }
            description={
              counts.never_seen > 0
                ? `그중 ${counts.never_seen}대는 응답을 받은 적이 없습니다.`
                : undefined
            }
          />
        ) : null}

        <StateBoundary
          state={pulse.state}
          reason={pulse.reason} status={pulse.status}
          onRetry={pulse.reload}
          emptyText="등록된 카메라가 없습니다."
        >
          <Row gutter={[12, 12]}>
            {grid.page.map((row) => (
              <Col key={row.id} xs={12} sm={8} md={6} lg={4}>
                <CameraTile row={row} now={now} />
              </Col>
            ))}
          </Row>
        </StateBoundary>

        <Text type="secondary" style={{ fontSize: 12 }}>
          {/* 멈춘 화면은 「사건이 없다」와 구별되지 않는다 — 화면이 스스로 말한다. */}
          자동 갱신 중 · 마지막 갱신 {relative(pulse.loadedAt)} · {TIMEZONE_NOTE}
        </Text>
      </Space>
    </Main>
  );
}
