import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';
import { CustomRoutes } from '@/services/API';
import FormLibrary from '../components/FormLibrary';
import useLibrary from '../hooks/useLibrary';

export default function FormAddNewLibrary() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createLibrary } = useLibrary();

  const [loading, setLoading] = useState(false);
  const handleSubmit = async (data: any) => {
    setLoading(true);
    const { success, message } = await createLibrary(data);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      navigate(CustomRoutes.library.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.library.path);
  };

  return (
    <FormLibrary
      loading={loading}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Add New Template')}
      breadcrumbItems={[{ url: '/library' }, { text: t('Add New Template') }]}
    />
  );
}
