/**
 * 「첫 근무일에 혼자 시작하기」 — 온보딩 (UX-03 · 세종 초안 v0.1 을 화면에 잇는다).
 *
 * ★ **문서를 여기서 쓰지 않았다.** 정본은 세종이 쓴
 *   `docs/design/GX-UX-03_온보딩_첫근무일_초안_v0.1.md` 이고, 이 화면은 그것을
 *   **사용자가 닿을 수 있는 자리로 옮긴 것**이다. 문서가 저장소에만 있으면
 *   그것은 「있다」이지 「쓴다」가 아니다 — 첫 근무일의 사람은 저장소를 못 연다.
 *
 * ★ 관문 없이 선다. 이 화면은 **사용자 자료를 한 건도 부르지 않는다** —
 *   서버 호출 0건 · 정적 글자뿐이다. 그래서 로그인 화면의 「처음이세요?」가
 *   여기로 올 수 있다. (무계정 링크 금지는 **자료를 보이는 링크**의 규약이다.)
 *
 * ★ 화면 이름은 사전(GX-COPY v1)을 따른다 — 「지금 처리할 것」 · 「훈련 모드」 ·
 *   「카메라 일괄 등록」 · 「미처리 → 접수 → 조치 중 → 종결」 · 「실제 / 오탐」.
 */
import { Card, Space, Tabs, Typography } from 'antd';
import { useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const { Title, Text, Paragraph } = Typography;

/** 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다. */
export const HEADLINE = '처음 시작하기 — 첫 근무일에 혼자 시작하기';

interface Chapter {
  key: string;
  label: string;
  lead: string;
  steps: string[];
}

/**
 * 여섯 사람 × 한 쪽. 각 줄은 「어디서 → 무엇을 누르면 → 무엇이 된다」.
 * 한 쪽에 일곱 줄을 넘기지 않는다 — 넘기면 첫날에 아무도 안 읽는다.
 */
const CHAPTERS: Chapter[] = [
  {
    key: 'operator',
    label: '관제요원',
    lead: '교대 첫날',
    steps: [
      '로그인하면 「지금 처리할 것」 화면이 뜹니다. 가장 급한 이벤트 하나가 위에 있습니다.',
      '카드의 사진과 한 줄 사유를 봅니다. 실제 · 오탐 · 보류 중 하나를 누릅니다.',
      '실제면 「접수」를 누릅니다. 시계가 돕니다. 팀장과 현장에 알림이 갑니다.',
      '종결은 현장 회신이 오면 누릅니다. 오탐은 사유를 고릅니다 — 임계값을 고치는 데 쓰입니다.',
      '아무 일 없을 때는 「카메라 격자」를 띄워 둡니다. 검은 칸은 카메라 무응답입니다.',
      '교대 끝에는 「미처리 보기」에 남은 것을 다음 근무자에게 말로 넘기고 로그아웃합니다.',
      '「저장소에 연결할 수 없습니다」가 뜨면 사진만 안 보이는 것입니다. 알림과 목록은 계속됩니다. 관리자에게 알리십시오.',
    ],
  },
  {
    key: 'manager',
    label: '관제팀장',
    lead: '아침 인수',
    steps: [
      '로그인하면 지난 12시간 한 줄 요약이 뜹니다 — 미처리 · 오탐 · 미판정.',
      '「미처리 보기」에서 남은 것을 봅니다. 재판정할 때는 사유가 필요합니다.',
      '「내 담당 보기」에서 누가 무엇을 했는지 봅니다.',
      '오탐이 많은 카메라는 설정에서 임계값을 고칩니다. 저장 전에 시간당 알림 수를 미리 봅니다.',
      '상황보고서는 이벤트 상세에서 만듭니다.',
      '관제실 대형 화면에는 「월 모드」를 띄웁니다. 마우스 없이 멀리서 읽는 화면입니다.',
      '훈련하는 날에는 설정에서 「훈련 모드」를 켭니다. 실제 알림이 나가지 않습니다. 끝나면 끕니다.',
    ],
  },
  {
    key: 'mobile',
    label: '이동 중',
    lead: '요원 · 팀장 · 담당자의 휴대폰',
    steps: [
      '문자 링크를 누르고 로그인하면 「내게 온 이벤트」가 뜹니다.',
      '사진과 주소, 경과 시간을 보고 「접수」를 누릅니다. 문자로 1을 회신해도 됩니다.',
      '현장에서는 도착 · 사진 한 장 · 한 줄로 회신합니다.',
      '근무 외 시간 알림은 설정에서 끌 수 있습니다. 관리자 승인이 필요합니다.',
    ],
  },
  {
    key: 'officer',
    label: '재난안전과 담당자',
    lead: '월요일 오전',
    steps: [
      '로그인하면 지난 7일 요약이 뜹니다.',
      '보고서에서 이번 달 우리 센터 한 쪽을 만듭니다 — 대응 시간 · 오탐률 · 가동률 · 건수.',
      '민원은 이벤트 검색에서 기간과 카메라, 유형으로 찾아 상세의 스냅샷을 봅니다.',
      '「내 모습을 지워 달라」는 요청은 열람·삭제 청구로 접수하고 회신을 기록합니다.',
      '감사 기록에서 누가 · 언제 · 무엇을 했는지 조회합니다.',
    ],
  },
  {
    key: 'sysop',
    label: '시스템 관리자',
    lead: '설치 다음 날',
    steps: [
      '사용자를 등록하고 역할을 줍니다 — 관제요원 · 관제팀장 · 담당자 · 관리자.',
      '「카메라 일괄 등록」에서 이름 · 코드 · 주소 · 주소 상세를 붙여넣고, 표를 먼저 본 뒤 적용합니다. 「주소 없는 카메라」가 0이 되게 합니다.',
      '알림 규칙에서 등급별 수신 역할을 확인합니다. 심각 등급의 수신자가 0명이면 안 됩니다.',
      '「시스템 보기」에서 카메라 무응답과 저장 용량 임계를 봅니다. 아침마다 오던 정상 알림이 안 오면 장애입니다.',
      '「이번 달 사용량」에서 카메라 대수 · 쓰는 사람 수 · 이벤트 수를 봅니다. 표로 내려받을 수 있습니다.',
      '백업 상태와 보존 기간을 설정합니다. 「훈련 모드」가 어디 있는지 팀장에게 알려 주십시오.',
    ],
  },
  {
    key: 'partner',
    label: '외부 연계 개발자',
    lead: '연동 첫날',
    steps: [
      '관리자에게 접근 키를 받습니다.',
      '규격 문서를 보고 이벤트를 조회한 뒤, 웹훅을 구독합니다 — 서명 검증과 재시도 규약이 있습니다.',
      '연결이 살아 있는지 확인하는 자리를 마지막에 확인합니다.',
    ],
  },
];

/** 역할 첫 화면의 「?」가 붙여 오는 값 → 어느 쪽을 펼칠지. */
const ROLE_TO_CHAPTER: Record<string, string> = {
  OPERATOR: 'operator',
  MANAGER: 'manager',
  BOSS: 'officer',
  MOBILE: 'mobile',
  SYSOP: 'sysop',
};

export default function Onboarding() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const active = useMemo(() => {
    const asked = params.get('role') ?? '';
    return ROLE_TO_CHAPTER[asked.toUpperCase()] ?? CHAPTERS[0].key;
  }, [params]);

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: 24 }}>
      <Space direction="vertical" size="middle" style={{ width: '100%' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>
            {HEADLINE}
          </Title>
          <Text type="secondary">
            한 쪽에 오늘 할 일 일곱 개까지. 각 줄은 어디서 무엇을 누르면 무엇이 되는지를 말합니다.
          </Text>
        </div>

        <Card size="small">
          <Tabs
            defaultActiveKey={active}
            items={CHAPTERS.map((c) => ({
              key: c.key,
              label: c.label,
              children: (
                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                  <Text type="secondary">{c.lead}</Text>
                  <ol style={{ paddingLeft: 20, margin: 0 }}>
                    {c.steps.map((s) => (
                      <li key={s} style={{ marginBottom: 8, lineHeight: '22px' }}>
                        {s}
                      </li>
                    ))}
                  </ol>
                </Space>
              ),
            }))}
          />
        </Card>

        <Paragraph type="secondary" style={{ marginBottom: 0 }}>
          여기 없는 것이 있으면 관리자에게 문의하십시오.{' '}
          <a onClick={() => navigate('/login')}>로그인 화면으로</a>
        </Paragraph>
      </Space>
    </div>
  );
}
