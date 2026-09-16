/**
 * S-16 「알림 받는 사람·채널」 — **골격** (UX-43 · 턴 R · 차선 U56).
 *
 * ★ 이번 턴은 골격까지다 — 지시서 원문: 「알림 규칙 화면 골격(UX-43) — 골격까지만」.
 *   PRD 부속서 A 는 이 화면이 `GET /settings/notify-rules`(등급별 수신 역할·사람·
 *   채널 표) · `POST /settings/notify-rules`(저장) · `POST …/test`(시험 발송)
 *   셋을 요구하지만(§4-2 표 9·10), **그 세 문은 아직 이 저장소 어디에도 없다**
 *   (`grep -rn "notify-rules" backend/` = 0건, 이 화면을 만들며 실측했다). 없는
 *   문을 있는 척 부르지 않는다 — 이 화면은 자료를 하나도 부르지 않고, 그 사실을
 *   화면에 그대로 적는다(`SystemSettings.tsx` 의 「백엔드 신호 대기」와 같은 정직).
 *
 * ★ 다음 턴이 채울 자리 — 이 화면이 표로 남긴다
 * ------------------------------------------------------------------------
 *   ① `GET /settings/notify-rules` — 등급(critical·warning·info) × 역할 × 채널
 *   ② 「심각 수신자 0명」 저장 금지(PRD AC) — 저장 버튼은 그 검사가 서기 전엔 없다
 *   ③ `POST …/test` — 시험 발송 1건
 * 이 파일은 그 세 자리를 **입력칸이 아니라 빈 틀**로만 그린다 — 누르면 아무 일도
 * 안 일어나는 단추를 만들지 않는다(그것은 "저장했다"는 착각을 만든다).
 */
import { Alert, Card, Descriptions, Space, Tag, Typography } from 'antd';

const { Title, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '알림 받는 사람·채널';

/** 아직 서버 문이 없는 자리의 글자. `SystemSettings.tsx::NO_SIGNAL` 과 같은 낱말 —
 * 「미선언」과 「아직 못 읽는다」를 같은 화면 관례로 가른다. */
export const NO_ROUTE_YET = '서버 문 대기';

const SEVERITY_ROWS = [
  { key: 'critical', label: '심각(critical)' },
  { key: 'warning', label: '경고(warning)' },
  { key: 'info', label: '안내(info)' },
] as const;

export default function NotifySettingsPage() {
  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          등급별로 누가 · 무슨 채널로 받는지 정하는 화면입니다. 이번 턴은 골격만
          섭니다 — 아래 표는 아직 서버에서 값을 받지 않습니다.
        </Paragraph>
      </div>

      <Card title="등급별 수신 역할·채널">
        <Descriptions column={1} bordered size="small">
          {SEVERITY_ROWS.map((row) => (
            <Descriptions.Item key={row.key} label={row.label}>
              <Tag>{NO_ROUTE_YET}</Tag>
            </Descriptions.Item>
          ))}
        </Descriptions>
        <Alert
          style={{ marginTop: 12 }}
          type="warning"
          showIcon
          message="이 표를 채우는 문(GET /settings/notify-rules)이 아직 없습니다."
          description="이 칸이 회색인 동안에는 규칙이 없는 것인지 못 읽는 것인지 이
            화면이 답하지 못합니다 — 그래서 빨강이 아니라 이 문구입니다."
        />
      </Card>

      <Card title="시험 발송">
        <Paragraph type="secondary">
          규칙을 저장하기 전에 실제로 한 건 보내 보는 자리입니다. 이 문
          (<code>POST /settings/notify-rules/test</code>)도 아직 없어 단추를 두지
          않았습니다 — 눌러도 아무 일 없는 단추는 「보냈다」는 착각을 만듭니다.
        </Paragraph>
      </Card>
    </Space>
  );
}
