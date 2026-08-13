import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';

import FormPacking from '../components/FormPackaging';
import useAPI from '../useAPI/useAPI';

export default function AddNewPacking() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createPackaging } = useAPI();
  const [loading, setLoading] = useState<boolean>(false);
  const handleSubmit = async (data: any) => {
    setLoading(true);
    const { success, message } = await createPackaging(data);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.packaging.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.packaging.path);
  };

  return (
    <FormPacking
      loading={loading}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Add New Packaging')}
      breadcrumbItems={[
        { url: CustomRoutes.packaging.path },
        { text: t('Add New Packaging') },
      ]}
    />
  );
}
