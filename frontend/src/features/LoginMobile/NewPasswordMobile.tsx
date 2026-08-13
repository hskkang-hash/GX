import { yupResolver } from '@hookform/resolvers/yup';
import { useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CustomInputHookForm } from 'rj-core';
import { CustomButton } from 'rj-core';

import { schemaNewPassword } from '@/services/schemaForm';

const NewPasswordMobile = () => {
  const { t } = useTranslation();
  const {
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: yupResolver(schemaNewPassword),
  });

  const onSubmit = (values) => {
    console.log(values);
  };

  return (
    <div className="p-3 d-flex flex-column gap-3">
      <h1 className="text-center py-3">{t('Choose New Password')}</h1>
      <div className="d-flex flex-column gap-3">
        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="d-flex flex-column gap-3">
            <CustomInputHookForm
              name="newPwd"
              control={control}
              label={t('New Password')}
              placeholder={t('New Password')}
              type="password"
              description={
                <ul className="new-password-page__requirements-list">
                  <li>
                    {t(
                      `The password must be at least {{length}} characters long.`,
                      {
                        length: 8,
                      },
                    )}
                  </li>
                  <li>{t(`The password does not contain the username.`)}</li>
                  <li>
                    {t(`The password does not contain repeated sequences.`)}
                  </li>
                  <li>
                    {t(`The password does not contain sequential characters.`)}
                  </li>
                  <li>
                    {t(
                      'The password must contain 4 types: uppercase letters, lowercase letters, numbers, and special characters.',
                    )}
                  </li>
                </ul>
              }
            />

            <CustomInputHookForm
              name="confirmPwd"
              control={control}
              label={t('Confirm Password')}
              placeholder={t('Confirm Password')}
              type="password"
            />

            <CustomButton
              text={t('Save')}
              htmlType="submit"
              disabled={isSubmitting || !errors}
            />
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewPasswordMobile;
