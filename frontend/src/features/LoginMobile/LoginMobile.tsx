import { yupResolver } from '@hookform/resolvers/yup';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  CustomButton,
  CustomInputHookForm,
  useAPILogin,
  useLogin,
  CustomModal,
  ActionBtn,
  CustomBtn,
} from 'rj-core';

import logoImageDefault from '@/assets/images/Full Version-Black.png';
import '@/assets/styles/LoginMobile.scss';
import { CustomRoutes } from '@/services/API';
import { schemaLogin } from '@/services/schemaForm';
import {
  ALREADY_SUBMITTING,
  EMPTY_PASSWORD,
  EMPTY_USERNAME,
  judgeLoginFailure,
  SUBMITTING,
} from '@/features/login/loginCopy';
import { loginInFlight, requestLogin } from '@/features/login/loginRequest';

interface FormData {
  username: string;
  password: string;
  end_previous_session?: boolean;
}

const LoginMobile = ({ logoImage }: { logoImage: string }) => {
  const { t, i18n } = useTranslation();
  const [errorMessage, setErrorMessage] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const { getProfileAPI } = useAPILogin();
  const login = useLogin();

  const [showEndSession, setShowEndSession] = useState(false);
  const methods = useForm<FormData>({
    defaultValues: {
      username: '',
      password: '',
      end_previous_session: false,
    },
    resolver: yupResolver(schemaLogin),
  });

  const {
    handleSubmit,
    control,
    setValue,
    formState: { isSubmitting },
  } = methods;

  /**
   * ★★ [P-78 ② ③ · 2026-09-06 턴 H] **다섯 갈래를 여기서도 말한다.**
   *
   *   종전에는 `loginAPI` 가 접어 준 `message` 를 그대로 그렸다. 그 값은 응답이
   *   없으면(서버 다운 · 타임아웃) `undefined` 이고, 그러면 이 화면은 **아무것도
   *   안 그렸다.** 이동 중인 사람의 화면에서 침묵은 「내가 잘못 눌렀나」로 읽힌다.
   *   그래서 데스크톱과 **같은 판정 함수**를 쓴다 — 두 화면이 다른 말을 하지 않게.
   */
  const onSubmit = async (data: FormData) => {
    const id = (data.username || '').trim();
    const pw = data.password || '';
    if (!id || !pw) {
      setErrorMessage(!id ? EMPTY_USERNAME : EMPTY_PASSWORD);
      return;
    }
    if (loginInFlight()) {
      setErrorMessage(ALREADY_SUBMITTING);
      return;
    }
    setErrorMessage(SUBMITTING);
    const outcome = await requestLogin(id, pw, Boolean(data.end_previous_session));
    const body = (outcome.body ?? null) as Record<string, any> | null;
    const auth = (body?.auth_status ?? {}) as Record<string, unknown>;
    const success = outcome.status === 200 && Boolean(body?.success) && Boolean(body?.user);
    const userData = (body?.user ?? {}) as Record<string, any>;
    const existing_session = Boolean(auth.existing_session);

    if (success) {
      setErrorMessage('');
      // First login with basic info
      login({
        token: userData.access_token,
        refreshToken: userData.refresh_token,
        isAuthenticated: true,
        userInfo: userData,
      });

      i18n.changeLanguage(userData?.language?.code || 'en');
      // Then fetch full profile
      const { success: profileSuccess } = await getProfileAPI(userData.user_id);

      if (profileSuccess) {
        const currentParams = new URLSearchParams(location.search);
        const dataValue = currentParams.get('dataQRCode');

        if (dataValue) {
          navigate(`${CustomRoutes.qrCode}?dataQRCode=${dataValue}`);
        } else {
          navigate(CustomRoutes.qrCode);
        }
      }
    } else if (existing_session) {
      setErrorMessage('');
      setShowEndSession(true);
    } else {
      setErrorMessage(judgeLoginFailure(outcome).text);
    }
  };

  const handleEndSession = async () => {
    setValue('end_previous_session', true);
    handleSubmit(onSubmit)();
  };

  return (
    <div
      className="p-3"
      id="login-mobile"
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '1em',
        }}
      >
        <img
          className="logo-image"
          src={logoImage || logoImageDefault}
          alt="logo-img"
        />
        <p className="login-description">{t('Login Description')}</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="d-flex flex-column gap-3 mt-3">
          <CustomInputHookForm
            name="username"
            control={control}
            label={t('ID-Login')}
            placeholder={t('ID-Login')}
            required
          />

          <CustomInputHookForm
            name="password"
            type="password"
            control={control}
            label={t('Password')}
            placeholder={t('Password')}
            required
          />

          {errorMessage && <div className="error-message">{errorMessage}</div>}

          <div className="forgot-password-container">
            <a
              className="forgot-password-link"
              onClick={() => navigate('/forgot-password')}
            >
              {t('Forgot Password')}
            </a>
          </div>
          <div className="login-button-container">
            <CustomButton
              type="primary"
              htmlType="submit"
              className="login-button"
              loading={isSubmitting}
              text={t('Login')}
            />
          </div>
        </div>
      </form>

      <CustomModal
        title={t('End Session')}
        show={showEndSession}
        onHide={() => setShowEndSession(false)}
        id="setting-modal-user"
      >
        <div style={{ width: '25rem' }}>
          {t(
            'This account is active on another device. Would you like to terminate the previous session and log in?',
          )}
        </div>
        <ActionBtn
          leftButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="primary"
              size="lg"
              label={t('Confirm')}
              onClick={() => handleEndSession()}
            />,
          ]}
          rightButtons={[
            <CustomBtn
              type="button"
              variant="outline"
              color="secondary"
              size="lg"
              label={t('Cancel')}
              onClick={() => setShowEndSession(false)}
            />,
          ]}
        />
      </CustomModal>
    </div>
  );
};

export default LoginMobile;
