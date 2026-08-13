import { useForm } from 'antd/es/form/Form';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper } from 'rj-core';

import { CustomRoutes } from '@/services/API';
import {
  convertPackagingData,
  convertPackagingDataForEdit,
} from '@/utils/packingDataConverter';

import FormPackaging from '../components/FormPackaging';
import useAPI from '../useAPI/useAPI';

const EditPackaging = () => {
  const { getDetailPackaging, updatePackaging } = useAPI();
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSubmit = async (formData: any) => {
    console.log('formData_edit', formData);
    setLoading(true);
    try {
      const convertedData = convertPackagingData(formData);
      console.log('convertedData_edit', convertedData);
      const payload = {
        data: convertedData,
        id: Number(id),
      };

      const { success, message } = await updatePackaging(payload);
      if (success) {
        setLoading(false);
        ToastTopHelper.success(message);
        navigate('/packaging');
      } else {
        setLoading(false);
        ToastTopHelper.error(message);
      }
    } catch (error: any) {
      // ToastTopHelper.error("Failed to update device");
      console.error('Error updating device:', error);
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.packaging.path.replace(':id', id || ''));
  };

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      if (!id) return null;
      const { success, data, message } = await getDetailPackaging({
        id: Number(id),
        edit: true,
      });
      if (success && data) {
        setInitialData(convertPackagingDataForEdit(data));
        setLoading(false);
      } else {
        setLoading(false);
        ToastTopHelper.error(message);
        return null;
      }
    };

    fetchData();
  }, [id]);

  return (
    <FormPackaging
      loading={loading}
      initialData={initialData}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Edit Packaging Specification')}
      breadcrumbItems={[
        { url: CustomRoutes.packaging.path },
        { text: t('Edit Packaging Specification') },
      ]}
    />
  );
};

export default EditPackaging;
