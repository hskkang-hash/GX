import { Typography } from 'antd';
import dayjs from 'dayjs';
import { useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import {
  CustomInputHookForm,
  FormBlock,
  useConfigSystem,
  useUserInfo,
} from 'rj-core';

import CustomDatePicker from '@/components/Form/CustomDatePicker';
import PickColorInput from '@/components/Form/PickColorInput';
import PaginationSelect from '@/components/selects/PaginationSelect';
import Colors from '@/configs/Colors';
import {
  getDateFormatStringForDayjs,
  getTimeFormatString2,
} from '@/features/Dashboard/utils/formatDateTime';
import { useSurveillanceProfile } from '@/features/surveillanceProfile/hooks/useSurveillanceProfile';
import useCommonAPI from '@/features/useCommonAPI/useAPI';
import { IUserInfo } from '@/types/form';

import UnitInput from '../../../../../../components/Form/UnitInput';

const { Text } = Typography;

const FormDataProfile = () => {
  const { t } = useTranslation();
  const { control, watch, setValue } = useFormContext();
  const { getOptionsByModel } = useCommonAPI();
  const { getListMissionOptions, getListOperatorOptions } =
    useSurveillanceProfile();

  const userInfo = useUserInfo() as IUserInfo;
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const dateFormat = getDateFormatStringForDayjs(
    userInfo?.settings?.date_format__code ??
    unitPreferences?.date_format ??
    'DD/MM/YYYY',
  );
  const timeFormat =
    getTimeFormatString2(
      userInfo?.settings?.time_format__code ??
      unitPreferences?.time_format ??
      '24',
    ) ?? 'HH:mm';
  const formatDateTime = dateFormat + ' ' + timeFormat;

  return (
    <FormBlock
      style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
    >
      <Text style={{ color: Colors.Gray5 }}>
        {t(
          'Please select a mission and start time for the profile to fetch data.',
        )}
      </Text>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
        }}
      >
        <CustomInputHookForm
          control={control}
          name="name"
          label={t('Name')}
          required
          placeholder={t('Name')}
        />
        <PaginationSelect
          required
          label={t('Mission')}
          name="mission_id"
          control={control}
          loadOptions={getListMissionOptions() as any}
          placeholder={t('Select')}
        />
        <CustomDatePicker
          name="start_time"
          label={t('Start Time')}
          placeholder=" "
          picker="datetime"
          control={control}
          disablePastTime
          format={formatDateTime}
          required
          onChange={(value) => {
            setValue('repeat_until_date', null);
          }}
        />
        <PaginationSelect
          required
          label={t('Operator')}
          name="operator"
          control={control}
          loadOptions={getListOperatorOptions() as any}
          onChange={(value) => { }}
          placeholder={t('Select')}
        />
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '1.25rem',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridColumn: 'span 2',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '1.25rem',
          }}
        >
          <PaginationSelect
            required
            label={t('Repeat')}
            name="repeat_type_id"
            control={control}
            loadOptions={getOptionsByModel({
              name_modal: 'SurveillanceProfileRepeatType',
              key: 'name',
              value: 'id',
            })}
            onChange={(value) => {
              setValue('repeat_until_type_id', {
                value: null,
                label: null,
                code: null,
              });
              setValue('repeat_occurrences', null);
              setValue('repeat_until_date', null);
            }}
            placeholder={t('Select')}
          />
          <PaginationSelect
            label={t('Util')}
            name="repeat_until_type_id"
            control={control}
            disabled={
              !watch('repeat_type_id') ||
              watch('repeat_type_id')?.code === 'none'
            }
            loadOptions={getOptionsByModel({
              name_modal: 'SurveillanceProfileRepeatUntilType',
              key: 'name',
              value: 'id',
            })}
            onChange={(value) => {
              setValue('repeat_occurrences', null);
              setValue('repeat_until_date', null);
            }}
          // placeholder={t('Select')}
          />
          <div style={{ marginTop: '1.8rem' }}>
            {watch('repeat_until_type_id')?.code === 'after_occurrences' ? (
              <CustomInputHookForm
                name="repeat_occurrences"
                required
                type="number"
                min={1}
                placeholder={t('Enter number of repeats')}
                onKeyDown={(e) => {
                  const allowedKeys = [
                    'Backspace',
                    'Delete',
                    'ArrowLeft',
                    'ArrowRight',
                    'Tab',
                  ];
                  if (e.ctrlKey || e.metaKey) return;
                  const isNumberKey = e.key >= '0' && e.key <= '9';
                  const isAllowedKey = allowedKeys.includes(e.key);
                  if (!isNumberKey && !isAllowedKey) {
                    e.preventDefault();
                  }
                }}
              />
            ) : (
              <CustomDatePicker
                name="repeat_until_date"
                control={control}
                format={dateFormat}
                required
                disableDateFromDate={dayjs(
                  watch('start_time'),
                ).format('YYYY-MM-DD')}
                placeholder=" "
                onChange={(value) => { }}
                disabled={
                  !watch('repeat_type_id') ||
                  watch('repeat_type_id')?.code === 'none' ||
                  watch('repeat_until_type_id')?.value == null ||
                  watch('repeat_until_type_id')?.code === 'never' ||
                  watch('start_time') == null
                }
              />
            )}
          </div>
        </div>
        <PickColorInput
          isRequired
          name="color_code"
          label={t('Color')}
        />
        <CustomInputHookForm
          control={control}
          name="note"
          label={t('Note')}
          placeholder={t('Note')}
        />
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '1.25rem',
        }}
      >
        <UnitInput
          name="takeoff_altitude"
          label={t('SurveyMission.Takeoff Altitude')}
          placeholder={t('SurveyMission.Takeoff Altitude')}
          unit="m"
          isRequired
        />
        <UnitInput
          name="altitude_separation"
          label={t('SurveyMission.Altitude Separation')}
          placeholder={t('SurveyMission.Altitude Separation')}
          unit="m"
          isRequired
        />
      </div>
    </FormBlock>
  );
};

export default FormDataProfile;
