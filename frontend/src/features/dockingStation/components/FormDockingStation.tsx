import { yupResolver } from '@hookform/resolvers/yup';
import { styled } from '@mui/material';
import { useEffect, useMemo, useState } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  ActionBtn,
  CustomBreadcrumb,
  CustomBtn,
  CustomModal,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useConfigSystem,
} from 'rj-core';

// import "./FormTerminals.scss";
import { Tabs } from '@/components/Form/Tabs';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaDockingStation } from '@/services/schemaForm';

import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import Information from './Information';
import Specification from './Specification';
import { ExceptionData, OperatingTimeData } from '@/components/HelperCellOperatingTime';

export const GridFullWidth = styled('div')`
  grid-column: 1 / -1;
  & > div {
    margin-bottom: 0 !important;
  }
`;

export const GridOneThree = styled('div')`
  display: grid;
  grid-template-columns: 1fr 3fr;
  gap: 1rem;
  width: 100%;
  & > div > div {
    margin-bottom: 0 !important;
  }
`;

// Define types for form data and select options
interface SelectOption {
  value: string;
  label: string;
}

export interface FormData {
  code: string;
  name: string;
  group: SelectOption | null;
  terminal_type_ids: SelectOption[] | null;
  docking_station_type_id: SelectOption | null;
  function_ids: any;
  temp_function_ids: any;
  manufacturer: string | null;
  year_of_manufacture: number | null;
  latitude: number | null;
  longitude: number | null;
  street_address: string;
  full_address: string;
  city_province: string | null;
  city_county_district: string | null;
  ward_town_township: string | null;
  postal_code: string;
  manager_name: string | null;
  url: string | null;
  note: string;
  avatar: any | null;
  delete_avatar: boolean;
  address_note: string;
  time_stops: {
    value: number | null;
    unit: string;
  };
  compatible_drone: string;
  swap_time: string | null;
  temperature_range: {
    from: {
      value: number | null;
      unit: string;
    };
    to: {
      value: number | null;
      unit: string;
    };
    unit: string;
  };
  weight: {
    value: null;
    unit: string;
  };
  weather_resistant: string;
  exceptions: ExceptionData[];
  operating_times?: OperatingTimeData[];
}

interface FormTerminalsProps {
  initialData?: FormData;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  title?: string;
  breadcrumbItems?: { url?: string; text?: string }[];
  isDirtyEdit?: boolean;
  setIsDirtyEdit?: (isDirtyEdit: boolean) => void;
  isEdit?: boolean;
}

const FormDockingStation = ({
  initialData,
  onSubmit,
  loading,
  onCancel,
  breadcrumbItems,
  isDirtyEdit = true,
  setIsDirtyEdit = () => { },
  isEdit = false,
}: FormTerminalsProps) => {
  const { t } = useTranslation();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const [activeTab, setActiveTab] = useState<number | undefined>(0);

  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem &&
    configSystem['Unit Config'] &&
    configSystem['Unit Config']['unit_preferences'];

  const defaultFormValues: FormData = {
    code: '',
    name: '',
    group: null,
    terminal_type_ids: null,
    docking_station_type_id: null,
    function_ids: null,
    temp_function_ids: null,
    latitude: null,
    longitude: null,
    city_province: null,
    city_county_district: null,
    ward_town_township: null,
    street_address: '',
    full_address: '',
    note: '',
    postal_code: '',
    manufacturer: null,
    year_of_manufacture: null,
    manager_name: null,
    url: null,
    avatar: null,
    delete_avatar: false,
    address_note: '',
    time_stops: {
      value: null,
      unit: unitPreferences?.Terminal?.time_stops || 'mins',
    },
    compatible_drone: '',
    swap_time: null,
    temperature_range: {
      from: {
        value: null,
        unit: unitPreferences?.temperature_range || '°C',
      },
      to: {
        value: null,
        unit: unitPreferences?.temperature_range || '°C',
      },
      unit: unitPreferences?.temperature_range || '°C',
    },
    weight: {
      value: null,
      unit: unitPreferences?.weight || 'kg',
    },
    weather_resistant: '',
    exceptions: [],
  };

  const methods = useForm<FormData>({
    defaultValues: initialData || defaultFormValues,
    resolver: yupResolver(schemaDockingStation(t, isRoleSuperuser)) as any,
  });

  const {
    handleSubmit,
    reset,
    watch,
    clearErrors,
    formState: { isValid, isDirty, errors, isSubmitting },
  } = methods;

  console.log('form_docking_station_errors', errors);
  console.log('form_docking_station_watch', watch());

  // Reset form when initialData changes
  useEffect(() => {
    if (initialData) {
      reset(initialData);
    }
  }, [initialData, reset]);

  const [clickSave, setClickSave] = useState(false);

  const [operatingTimes, setOperatingTimes] = useState<OperatingTimeData[]>([]);
  const [operatingTimeErrors, setOperatingTimeErrors] = useState<any>({});
  const { getDayOfWeek } = useCommonAPI();


  const isOperatingTimesEdited = useMemo(() => {
    return JSON.stringify(operatingTimes) !==
      JSON.stringify(initialData?.operating_times);
  }, [operatingTimes, initialData?.operating_times]);


  console.log('isOperatingTimesEdited', isOperatingTimesEdited);

  const { showModal, setShowModal, handleModalSave, handleModalCancel } =
    useFormNavigationBlocker({
      isDirty: clickSave == false && (isDirty || isOperatingTimesEdited),
      onSave: async () => {
        const formData = watch();
        await onSubmit(formData);
        reset(formData, {
          keepDirty: false,
          keepValues: true,
        });
      },
      onCancel,
      handleSubmit,
    });

  const handleFormSubmit = async (data: FormData) => {
    setClickSave(true);
    const formattedData = {
      ...data,
      operating_times: operatingTimes,
    };
    try {
      await onSubmit(formattedData);
      reset(formattedData, {
        keepDirty: false,
        keepValues: true,
      });
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };




  useEffect(() => {
    const fetchDayOfWeek = async () => {
      const { data, status, message } = await getDayOfWeek();
      console.log('data_day_of_week', data);
      if (status) {
        setOperatingTimes(data);
      } else {
        ToastTopHelper.error(message);
      }
    }
    if (!isEdit) {
      fetchDayOfWeek()
    }
  }, [isEdit]);


  useEffect(() => {
    if (initialData?.operating_times) {
      setOperatingTimes(initialData?.operating_times as OperatingTimeData[]);
    }
  }, [initialData?.operating_times]);


  const onError = () => {
    console.log('onError', errors);

    ToastTopHelper.error(t('Please fill in all required fields'));
  };

  const listTabs = [
    {
      label: t('Information'),
      content: (
        <Information
          isEdit={isEdit}
          setIsDirtyEdit={setIsDirtyEdit}
          operatingTimes={operatingTimes}
          setOperatingTimes={setOperatingTimes}
          operatingTimeErrors={operatingTimeErrors}
          setOperatingTimeErrors={setOperatingTimeErrors}
        />
      ),
    },
    {
      label: t('Specification'),
      content: (
        <Specification
          isEdit={isEdit}
          setIsDirtyEdit={setIsDirtyEdit}
        />
      ),
    },
  ];

  useEffect(() => {
    if (watch('latitude')) {
      clearErrors('latitude');
    }
    if (watch('longitude')) {
      clearErrors('longitude');
    }
  }, [watch('latitude'), watch('longitude')]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={handleSubmit(handleFormSubmit, onError)}
        className="form-add-new-terminals"
      >
        <CustomBreadcrumb
          items={breadcrumbItems || []}
          buttons={[
            <CustomBtn
              key="cancel-btn"
              label={t('Cancel')}
              variant="outline"
              color="secondary"
              size="md"
              style={{ width: '6rem' }}
              type="button"
              onClick={onCancel}
            />,
            <CustomBtn
              key="save-btn"
              size="md"
              style={{ width: '6rem' }}
              actionType={
                isEdit ? ROLE_PERMISSION.UPDATE : ROLE_PERMISSION.CREATE
              }
              loading={loading || isSubmitting}
              disabled={
                (!isDirty && !isOperatingTimesEdited) ||
                loading ||
                isSubmitting ||
                !isValid ||
                !watch('full_address') ||
                !watch('latitude') ||
                !watch('longitude') ||
                Object.keys(operatingTimeErrors).length > 0
              }
              label={t('Save')}
              type="submit"
            />,
          ]}
        />
        <Main>
          <Tabs
            items={listTabs}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            noNeedReRender={true}
          />
          <CustomModal
            title={t('Save changes')}
            show={showModal}
            onHide={() => setShowModal(false)}
          >
            <div style={{ width: '25rem' }}>
              {t(
                'Your unsaved changes will be lost. Do you want to save changes before leaving?',
              )}
            </div>
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  key="modal-save-btn"
                  type="submit"
                  color="primary"
                  size="lg"
                  actionType={ROLE_PERMISSION.UPDATE}
                  onClick={handleModalSave}
                  label={t('Save')}
                  loading={loading || isSubmitting}
                  disabled={loading || isSubmitting}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  key="modal-cancel-btn"
                  type="button"
                  variant="outline"
                  color="secondary"
                  size="lg"
                  onClick={handleModalCancel}
                  label={t('Cancel')}
                />,
              ]}
            />
          </CustomModal>
        </Main>
      </form>
    </FormProvider>
  );
};

export default FormDockingStation;
