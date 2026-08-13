import { yupResolver } from '@hookform/resolvers/yup';
import dayjs from 'dayjs';
import { useEffect, useMemo } from 'react';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';
import * as yup from 'yup';

import CustomDatePicker from '../../../../../../components/Form/CustomDatePicker';
import CustomRadio from '../../../../../../components/Form/CustomRadio';
import i18n from '../../../../../../i18n';
import { useDateFormat } from '../../../../hooks/useDateFormat';
import { HandoverShiftState } from '../../../../types';
import { formatDate } from '../../../../utils/dateFormat';

export const CreateHandoverModal = ({
  show,
  onHide,
  onSubmit,
  shiftList,
}: {
  show: boolean;
  onHide: () => void;
  onSubmit: (data: { date: string; shift_id: number | null }) => void;
  shiftList: HandoverShiftState[];
}) => {
  const { t } = useTranslation();
  const { dateFormat } = useDateFormat();
  const methods = useForm<{
    date: string;
    shift_id: number | null;
  }>({
    defaultValues: {
      date: dayjs(),
      shift_id: null,
    },
    resolver: yupResolver(
      yup.object().shape({
        date: yup.string().required(t('handover.Date is required')),
        shift_id: yup
          .number()
          .nullable()
          .required(t('handover.Shift is required')),
      }),
    ),
  });

  const {
    control,
    formState: { isValid, isSubmitting },
    handleSubmit,
  } = methods;

  useEffect(() => {
    if (show) {
      methods.reset();
    }
  }, [show]);

  return (
    <CustomModal
      title={t('handover.Create A Handover')}
      show={show}
      onHide={onHide}
      id="create-shift-log"
    >
      <div>
        <FormProvider {...methods}>
          <form
            onSubmit={handleSubmit((data) =>
              onSubmit({
                date: dayjs(data.date).format('YYYY/MM/DD'),
                shift_id: data.shift_id,
              }),
            )}
          >
            <CustomDatePicker
              label={t('handover.Created Date')}
              name="date"
              control={control}
              required
              format={dateFormat}
              disabledDate={(current) => {
                if (!current) return false;
                // Disable future dates - only allow today and past dates
                return current.isAfter(dayjs(), 'day');
              }}
            />
            <CustomRadio
              name="shift_id"
              control={control}
              label={t('handover.Work Shift')}
              options={shiftList.map((item) => ({
                value: item.id,
                label: item.name,
              }))}
              required
              row={true}
            />
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  variant="outline"
                  color="primary"
                  size="lg"
                  type="submit"
                  label={t('handover.Create')}
                  loading={isSubmitting}
                  disabled={!isValid || isSubmitting}
                  id="create-button"
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  variant="outline"
                  color="secondary"
                  size="lg"
                  type="button"
                  label={t('handover.Cancel')}
                  id="close-button"
                  onClick={onHide}
                />,
              ]}
            />
          </form>
        </FormProvider>
      </div>
    </CustomModal>
  );
};
