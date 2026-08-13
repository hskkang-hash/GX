import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ToastTopHelper, useConfigSystem, useLoadingContext, useUserInfo } from 'rj-core';

import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { CustomRoutes } from '@/services/API';
import {
  convertDeviceData,
  convertDeviceDataForEdit,
} from '@/utils/deviceDataConverter';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import FormDevice from '../components/FormDevice';
import useAPI from '../useAPI/useAPI';
import { useConvertDate } from '@/features/Dashboard/utils/formatDateTime';

const EditDeviceForm = () => {
  const { getDetailDevice, updateDevice } = useAPI();
  const { t } = useTranslation();
  const { id } = useParams();
  const navigate = useNavigate();
  const [initialData, setInitialData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    (configSystem &&
      configSystem['Unit Config']) ?
      configSystem['Unit Config']['unit_preferences'] : null;

  const { converRawDateToDateFormat, convertDateFormatToUTC, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay } = useConvertDate();
  console.log({ initialData });

  const handleSubmit = async (formData: any) => {
    console.log('formData_edit_form', formData);

    setLoading(true);
    const clonedFormData = JSON.parse(JSON.stringify(formData));
    const status =
      clonedFormData.data?.manufacturer_information?.insurance_status;

    try {
      if (status === false || status === 'false') {
        clonedFormData.data.manufacturer_information.insurance_type = null;
        clonedFormData.data.manufacturer_information.insurance_provider = null;
        clonedFormData.data.manufacturer_information.policy_number = null;
        clonedFormData.data.manufacturer_information.validity_period_from =
          null;
        clonedFormData.data.manufacturer_information.validity_period_to = null;
        clonedFormData.data.manufacturer_information.current_status = null;
      }

      const convertedData = convertDeviceData(clonedFormData, isRoleSuperuser, convertDateFormatToYYYYMMDD, convertDateToUTCStartOfDay, convertDateToUTCEndOfDay);
      const payload = {
        data: convertedData,
        id: Number(id),
        avatar: formData.avatar,
        delete_avatar: formData.delete_avatar,
        files: formData.files,
        removedFiles: formData.remove_files,
      };

      const { success, message } = await updateDevice(payload);
      if (success) {
        setLoading(false);
        ToastTopHelper.success(message);
        navigate(CustomRoutes.device.path);
      } else {
        setLoading(false);
        ToastTopHelper.error(message);
      }
    } catch (error) {
      ToastTopHelper.error('Failed to update device');
      console.error('Error updating device:', error);
    }
  };

  const handleCancel = () => {
    navigate(
      CustomRoutes.device.subRoutes.detailDevice.path.replace(':id', id || ''),
    );
  };

  const { getMainType } = useCommonAPI();
  const [mainTypeOptions, setMainTypeOptions] = useState<any[]>([]);

  const handleGetDataForForm = async () => {
    if (mainTypeOptions.length === 0) {
      const { data: dataMainType } = await getMainType();
      setMainTypeOptions(dataMainType);
    }
  };

  const { showLoading, hideLoading } = useLoadingContext();

  const fetchData = useCallback(async () => {
    showLoading();
    setLoading(true);
    if (!id) return null;
    const { success, data, message } = await getDetailDevice({
      id: Number(id),
      edit: true,
    });
    if (success && data) {
      setInitialData(
        convertDeviceDataForEdit({ sourceData: data, isRoleSuperuser, unitPreferences, converRawDateToDateFormat }),
      );
      setLoading(false);
      hideLoading();
    } else {
      setLoading(false);
      ToastTopHelper.error(message);
      hideLoading();
      return null;
    }
  }, [
    id,
    unitPreferences,
    getDetailDevice,
    showLoading,
    hideLoading,
    isRoleSuperuser,
  ]);

  useEffect(() => {
    if (configSystem !== undefined) {
      fetchData();
      handleGetDataForForm();
    }
  }, [id, configSystem]);

  return (
    <FormDevice
      loading={loading}
      activeTabs={true}
      isEdit={true}
      initialData={initialData}
      onSubmit={handleSubmit}
      onCancel={handleCancel}
      title={t('Edit Device')}
      breadcrumbItems={[
        { url: `/device/detail-device/${id}` },
        { text: t('Edit Device') },
      ]}
    />
  );
};

export default EditDeviceForm;
