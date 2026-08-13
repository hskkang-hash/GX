import { yupResolver } from '@hookform/resolvers/yup';
import { styled } from '@mui/material';
import { useEffect, useState } from 'react';
import context from 'react-bootstrap/esm/AccordionContext';
import { FormProvider, useForm, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomBreadcrumb,
  CustomBtn,
  CustomInputHookForm,
  FormBlock,
  Main,
  ROLE_PERMISSION,
  ToastTopHelper,
  useConfigGroupSystem,
} from 'rj-core';

// import "./FormTerminals.scss";
import CustomDatePicker from '@/components/Form/CustomDatePicker';
import CustomFileInput from '@/components/Form/CustomFileInput';
import { Tabs } from '@/components/Form/Tabs';
import UnitInput from '@/components/Form/UnitInput';
import { Map } from '@/components/maps';
import { MarkerData } from '@/components/maps/MapKakao';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import { formatKoreanStreetAddress } from '@/features/terminals/hooks/utils';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { useFormNavigationBlocker } from '@/hooks/useFormNavigationBlocker';
import { schemaDockingStation } from '@/services/schemaForm';
import { useDebounce } from '@/utils/utils';

import CustomSearchMapUnified from '../../../components/search/CustomSearchMapUnified';
import { checkCodeValid } from '../../../utils/CheckCodeValid';

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

interface IpropSpecification {
  isEdit?: boolean;
  setIsDirtyEdit?: (isDirtyEdit: boolean) => void;
}

const Specification = ({
  isEdit,
  setIsDirtyEdit = () => {},
}: IpropSpecification) => {
  const { t } = useTranslation();

  const {
    formState: { errors },
    control,
    watch,
    setValue,
    trigger,
    clearErrors,
  } = useFormContext();

  const watchedOperatingAltitudeFrom = watch('temperature_range.from.value');
  const watchedOperatingAltitudeTo = watch('temperature_range.to.value');
  useEffect(() => {
    const handleValidation = async () => {
      if (
        watchedOperatingAltitudeFrom != null &&
        watchedOperatingAltitudeTo != null &&
        watchedOperatingAltitudeFrom !== '' &&
        watchedOperatingAltitudeTo !== ''
      ) {
        const minNum = Number(watchedOperatingAltitudeFrom);
        const maxNum = Number(watchedOperatingAltitudeTo);

        if (minNum >= maxNum) {
          await trigger([
            'temperature_range.from.value',
            'temperature_range.to.value',
          ]);
        } else {
          clearErrors([
            'temperature_range.from.value',
            'temperature_range.to.value',
          ]);
        }
      } else {
        // 🧹 Khi xóa input => clear lỗi
        clearErrors([
          'temperature_range.from.value',
          'temperature_range.to.value',
        ]);
      }
    };

    const timeoutId = setTimeout(handleValidation, 200);
    return () => clearTimeout(timeoutId);
  }, [
    watchedOperatingAltitudeFrom,
    watchedOperatingAltitudeTo,
    clearErrors,
    trigger,
  ]);

  const watchedWeight = watch('swap_time');

  useEffect(() => {
    const handleValidation = async () => {
      if (watchedWeight != null) {
        const weightNum = Number(watchedWeight);
        if (weightNum < 0) {
          await trigger(['swap_time']);
        } else {
          await clearErrors(['swap_time']);
        }
      }
      const timeoutId = setTimeout(handleValidation, 200);
      return () => clearTimeout(timeoutId);
    };
  }, [watchedWeight, clearErrors, trigger]);

  return (
    <div>
      <FormBlock>
        <div className="form-grid">
          <CustomInputHookForm
            name="compatible_drone"
            label={t('Compatible Drone')}
            placeholder={t('Compatible Drone')}
          />
          <UnitInput
            name="weight.value"
            label={t('Weight')}
            placeholder="0"
            unit={watch('weight.unit')}
            type="number"
          />
          <CustomInputHookForm
            name="swap_time"
            type="text"
            label={t('Swap Time')}
            placeholder={t('Swap Time')}
          />
          <CustomInputHookForm
            name="weather_resistant"
            label={t('Weather Resistant')}
            placeholder={t('Weather Resistant')}
          />

          <div className="device-size">
            <div className="device-size__label">{t('Temperature Range')}</div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <UnitInput
                name="temperature_range.from.value"
                unit={watch('temperature_range.from.unit') || '°C'}
                placeholder="0"
                iconDivider={'to'}
                negative={true}
              />
              <UnitInput
                name="temperature_range.to.value"
                unit={watch('temperature_range.from.unit') || '°C'}
                placeholder="0"
                negative={true}
              />
            </div>
          </div>
        </div>
      </FormBlock>
    </div>
  );
};

export default Specification;
