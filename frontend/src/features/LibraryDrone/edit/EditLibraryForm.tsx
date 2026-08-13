import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper, useConfigSystem, useLoadingContext, useUserInfo } from 'rj-core';

import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { CustomRoutes } from '@/services/API';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormLibrary from '../components/FormLibrary';
import useLibrary from '../hooks/useLibrary';
import {
  convertLibraryData,
  convertLibraryDataForEdit,
} from '../utils/convertData';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const EditLibraryForm = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState<any>(null);
  const { getLibraryById, updateLibrary } = useLibrary();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [configSystem] = useConfigSystem();


  const { convertDateFormatToUTC, convertDateFormatToYYYYMMDD, converRawDateToDateFormat, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay } = useConvertDate();

  const handleSubmit = async (formData: any) => {
    const clonedFormData = JSON.parse(JSON.stringify(formData));
    console.log('clonedFormData', clonedFormData);
    const status =
      clonedFormData.data?.manufacturer_information?.insurance_status;

    try {
      console.log('indata_1');
      if (status === false || status === 'false') {
        console.log('indata_2');
        clonedFormData.data.manufacturer_information.insurance_type = null;
        clonedFormData.data.manufacturer_information.insurance_provider = null;
        clonedFormData.data.manufacturer_information.policy_number = null;
        clonedFormData.data.manufacturer_information.validity_period_from =
          null;
        clonedFormData.data.manufacturer_information.validity_period_to = null;
        clonedFormData.data.manufacturer_information.current_status = null;
      }
      const convertedData = convertLibraryData(clonedFormData, isRoleSuperuser, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay);

      const payload = {
        data: convertedData,
        id: Number(id),
        avatar: formData.avatar,
        files: formData.files,
        removedFiles: formData.remove_files,
        removedAvatar: formData.remove_avatar,
      };

      const { success, message } = await updateLibrary(payload);
      if (success) {
        ToastTopHelper.success(message);
        navigate(CustomRoutes.library.path);
      } else {
        ToastTopHelper.error(message);
      }
    } catch {
      ToastTopHelper.error('Failed to update library');
    }
  };

  const handleCancel = () => {
    navigate(CustomRoutes.library.path);
  };

  const { getMainType } = useCommonAPI();
  const [mainTypeOptions, setMainTypeOptions] = useState<any[]>([]);

  const handleGetDataForForm = async () => {
    if (mainTypeOptions.length === 0) {
      const { data: dataMainType } = await getMainType();
      setMainTypeOptions(dataMainType);
    }
  };

  const unitPreferences =
    (configSystem &&
      configSystem['Unit Config']) ?
      configSystem['Unit Config']['unit_preferences'] : null;

  const { showLoading, hideLoading } = useLoadingContext();
  const fetchData = useCallback(async () => {
    showLoading();
    if (!id) return null;
    const { success, data, message } = await getLibraryById(
      Number(id),
      true,
    );
    if (success && data) {
      hideLoading();
      setInitialData(convertLibraryDataForEdit({ sourceData: data, unitPreferences, converRawDateToDateFormat }));
    } else {
      hideLoading();
      setInitialData({});
      ToastTopHelper.error(message);
    }

  }, [id, unitPreferences, getLibraryById, showLoading, hideLoading]);


  useEffect(() => {
    if (configSystem !== undefined) {
      fetchData();
      handleGetDataForForm();
    }
  }, [id, configSystem]);

  return (
    <FormLibrary
      initialData={initialData}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Edit Template')}
      breadcrumbItems={[{ url: '/library' }, { text: t('Edit Template') }]}
    />
  );
};

export default EditLibraryForm;
