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
  const { loginAPI, getProfileAPI } = useAPILogin();
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

  const onSubmit = async (data: FormData) => {
    const {
      success,
      data: userData,
      message,
      existing_session,
    } = await loginAPI(data.username, data.password, data.end_previous_session);

    if (success) {
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
      setShowEndSession(true);
    } else {
      setErrorMessage(message);
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
