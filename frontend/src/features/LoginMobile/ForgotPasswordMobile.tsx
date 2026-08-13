import { yupResolver } from '@hookform/resolvers/yup';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { AiOutlineLeft } from 'react-icons/ai';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { CustomButton, CustomInputHookForm, useAPILogin } from 'rj-core';

import EmailIcon from '@/assets/images/email_icon.svg';
import '@/assets/styles/LoginMobile.scss';
import { schemaForgotPassword } from '@/services/schemaForm';

const ForgotPasswordContent = ({
  onSubmit,
  control,
  isSubmitting,
}: {
  onSubmit: () => void;
  control: any;
  isSubmitting: boolean;
}) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div>
      <div
        className="back-button py-3"
        onClick={() => navigate('/login')}
      >
        <AiOutlineLeft size={16} />
      </div>
      <div className="form-content">
        <div className="form-title">{t('Forgot-Password')}</div>
        <div className="form-description">
          {t(
            'Please enter your email address to receive an alternative password',
          )}
        </div>
        <form onSubmit={onSubmit}>
          <div className="d-flex flex-column gap-3">
            <CustomInputHookForm
              label={t('Email')}
              placeholder={t('Email')}
              control={control}
              name="email"
            />
            <div className="submit-button-container">
              <CustomButton
                type="primary"
                htmlType="submit"
                className="submit-button"
                loading={isSubmitting}
                text={t('OK')}
              />
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

const SuccessContent = ({ handleResend }: { handleResend: () => void }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();

  return (
    <div
      className="success-container text-center"
      style={{
        marginTop: '18.875rem',
      }}
    >
      <div className="success-content">
        <img
          src={EmailIcon}
          alt="email-icon"
          className="email-icon"
        />
        <div className="success-message">
          {t('Email has been sent. Kindly check your inbox.')}
        </div>
      </div>
      <div className="action-container">
        <CustomButton
          type="primary"
          htmlType="submit"
          className="login-button"
          onClick={() => navigate('/login')}
          text={t('Back to login')}
        />
        <div className="resend-container">
          {t("Don't receive email?")}{' '}
          <a
            className="resend-link"
            onClick={handleResend}
          >
            {t('Resend')}
          </a>
        </div>
      </div>
    </div>
  );
};

const ForgotPasswordMobile = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isSuccess, setIsSuccess] = useState(false);
  const [email, setEmail] = useState('');
  const { forgotPasswordAPI } = useAPILogin();
  const {
    control,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm({
    resolver: yupResolver(schemaForgotPassword),
    defaultValues: { email: '' },
  });

  useEffect(() => {
    const isSuccess = searchParams.get('isSuccess');
    if (isSuccess) {
      setIsSuccess(true);
    }
  }, [searchParams]);

  const onSubmit = async (data: { email: string }, isResend = false) => {
    setEmail(data.email);

    const { success, message } = await forgotPasswordAPI(data.email);
    if (success && !isResend) {
      setIsSuccess(true);
      setSearchParams({ isSuccess: 'true' });
    } else if (success && isResend) {
      console.log('resend', message);
    } else {
      console.log('error', message);
    }
  };

  return (
    <div
      id="forgot-password-mobile"
      className="p-3"
    >
      {isSuccess ? (
        <SuccessContent handleResend={() => onSubmit({ email }, true)} />
      ) : (
        <ForgotPasswordContent
          onSubmit={handleSubmit(onSubmit)}
          control={control}
          isSubmitting={isSubmitting}
        />
      )}
    </div>
  );
};

export default ForgotPasswordMobile;
