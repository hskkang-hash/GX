/**
 * S-14 「사람·역할」 — **UX-42 #1·#2·#3** (턴 R · 차선 U56).
 *
 * 왜 이 화면이 생겼나 — `apps/dsm/people.py` 를 **처음으로 부르는 화면**
 * ------------------------------------------------------------------------
 * `people.py` 는 지난 턴(P-141)에 골격으로 만들어졌지만, 부르는 자리가 시험
 * (`tests/test_u56_people_deactivate_401.py`)뿐이었다 — `scripts/verify_dormant.py`
 * 는 그것도 "운영에서는 죽은 것"으로 본다(㉠ 호출 없음). 이 화면이 그 서버 함수를
 * 실제로 부르는 첫 자리다(경유 라우트: `apps/dsm/api_u56.py::create_person` ·
 * `deactivate_person`).
 *
 * ★ 관리자만 지난다 — 라우트의 `guard_setting` 이 문지기다. dj-core 의
 *   `create-user` 뷰 자체엔 권한 검사가 없어서(그 라우트 머리말의 실측), 이
 *   화면 뒤 문이 유일한 문지기다. 화면은 그 403 을 그대로 보여 준다.
 * ★ 비밀번호는 **한 번만** 입력칸에 있다 — 서버 응답에 담겨 돌아오지 않는다
 *   (D-204). 만든 사람이 그 값을 옆 사람에게 전할 방법은 이 화면 밖의 일이다.
 */
import { useCallback, useState } from 'react';
import { Alert, Button, Card, Form, Input, InputNumber, Space, Typography } from 'antd';

import { dsmPost, dsmPostQuery, dsmU56Endpoint } from '../api';
import { HEADLINE_COPY, userFacingError } from '../copy';

const { Title, Paragraph } = Typography;

/**
 * 이 화면에만 있는 글자 — 캡처가 이것을 보고 찍는다.
 *
 * ★ [턴 U · 차선 F 등록 요청] 지역 상수로 **두 벌** 적혀 있던 것을 사전
 *   (`copy.ts::HEADLINE_COPY`) 하나로 모았다. 두 벌이면 사전을 고친 날 화면이
 *   안 따라오고, 온보딩 48행의 「문구 정본 없음」이 그만큼 남는다.
 */
export const HEADLINE = HEADLINE_COPY.people;

interface CreatedPerson {
  user_id: number;
  username: string;
  audit_id: number;
}

interface DeactivatedPerson {
  user_id: number;
  deactivated: boolean;
  audit_id: number;
}

export default function PeoplePage() {
  const [createForm] = Form.useForm();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState<CreatedPerson | null>(null);

  const [deactivateId, setDeactivateId] = useState<number | null>(null);
  const [deactivateBusy, setDeactivateBusy] = useState(false);
  const [deactivateError, setDeactivateError] = useState('');
  const [deactivated, setDeactivated] = useState<DeactivatedPerson | null>(null);

  const onCreate = useCallback(
    async (values: {
      username: string;
      email: string;
      password: string;
      group_id: number;
      display_name?: string;
    }) => {
      setBusy(true);
      setError('');
      setCreated(null);
      try {
        const result = await dsmPostQuery<CreatedPerson>(dsmU56Endpoint.peopleCreate, {
          username: values.username,
          email: values.email,
          password: values.password,
          group_id: values.group_id,
          display_name: values.display_name ?? '',
        });
        setCreated(result);
        createForm.resetFields(['password']);
      } catch (err) {
        setError(userFacingError('People', err, '계정을 만들지 못했습니다.'));
      } finally {
        setBusy(false);
      }
    },
    [createForm],
  );

  const onDeactivate = useCallback(async () => {
    if (!deactivateId) return;
    setDeactivateBusy(true);
    setDeactivateError('');
    setDeactivated(null);
    try {
      const result = await dsmPost<DeactivatedPerson>(
        dsmU56Endpoint.peopleDeactivate(deactivateId),
      );
      setDeactivated(result);
    } catch (err) {
      setDeactivateError(userFacingError('People', err, '비활성화하지 못했습니다.'));
    } finally {
      setDeactivateBusy(false);
    }
  }, [deactivateId]);

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={3}>{HEADLINE}</Title>
        <Paragraph type="secondary">
          이 화면은 관리자 역할만 지납니다. 비밀번호는 만들 때 한 번만 입력하고,
          서버 응답에는 담겨 오지 않습니다.
        </Paragraph>
      </div>

      <Card title="계정 만들기">
        <Form form={createForm} layout="vertical" onFinish={onCreate}>
          <Form.Item name="username" label="아이디" rules={[{ required: true }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="email" label="이메일" rules={[{ required: true }]}>
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="password" label="비밀번호" rules={[{ required: true }]}>
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="group_id" label="소속(테넌트) ID" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="display_name" label="표시 이름">
            <Input autoComplete="off" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={busy}>
            계정 만들기
          </Button>
        </Form>
        {error ? (
          <Alert style={{ marginTop: 12 }} type="error" showIcon message={error} />
        ) : null}
        {created ? (
          <Alert
            style={{ marginTop: 12 }}
            type="success"
            showIcon
            message={`만들었습니다 — user_id ${created.user_id} · ${created.username}`}
            description={`감사 #${created.audit_id}`}
          />
        ) : null}
      </Card>

      <Card title="계정 비활성화">
        <Paragraph type="secondary">
          행을 지우지 않습니다 — 로그인만 막습니다. 이미 발급된 토큰도 이 순간부터
          거절됩니다(dj-core 의 기존 인증 경로).
        </Paragraph>
        <Space>
          <InputNumber
            placeholder="user_id"
            value={deactivateId ?? undefined}
            onChange={(v) => setDeactivateId(typeof v === 'number' ? v : null)}
          />
          <Button danger loading={deactivateBusy} onClick={onDeactivate} disabled={!deactivateId}>
            비활성화
          </Button>
        </Space>
        {deactivateError ? (
          <Alert style={{ marginTop: 12 }} type="error" showIcon message={deactivateError} />
        ) : null}
        {deactivated ? (
          <Alert
            style={{ marginTop: 12 }}
            type="success"
            showIcon
            message={`user_id ${deactivated.user_id} 를 비활성화했습니다.`}
            description={`감사 #${deactivated.audit_id}`}
          />
        ) : null}
      </Card>
    </Space>
  );
}
