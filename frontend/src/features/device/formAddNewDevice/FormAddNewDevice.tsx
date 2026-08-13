import { useState } from 'react';
import useAPI from '../useAPI/useAPI';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { CustomRoutes } from '@/services/API';
import FormDevice from '../components/FormDevice';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';
import { ToastTopHelper, useLoadingContext } from 'rj-core';

export default function FormAddNewDevice() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { createDevice } = useAPI();
  const [loading, setLoading] = useState<boolean>(false);
  const { showLoading, hideLoading } = useLoadingContext();
  const { dateFormat } = useConvertDate();


  const handleSubmit = async (data: any) => {
    setLoading(true);
    showLoading();
    const { success, message } = await createDevice(data, dateFormat);
    if (success) {
      setLoading(false);
      ToastTopHelper.success(message);
      hideLoading();
      navigate(CustomRoutes.device.path);
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
      hideLoading();
      return;
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.device.path);
  };

  return (
    <FormDevice
      activeTabs={false}
      loading={loading}
      isEdit={false}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Add New Device')}
      breadcrumbItems={[{ url: '/device' }, { text: t('Add New Device') }]}
    />
  );
}
