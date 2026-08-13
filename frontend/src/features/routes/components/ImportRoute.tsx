import { yupResolver } from '@hookform/resolvers/yup';
import { FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { ActionBtn, CustomBtn, CustomModal } from 'rj-core';
import * as yup from 'yup';

import CustomFileInput from '../../../components/Form/CustomFileInput';
import { SelectOption } from '../../../components/selects/CustomSelect';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import useCommonAPI from '../../useCommonAPI/useAPI';

const createFileValidationSchema = (message: (key: string) => string) =>
  yup.object().shape({
    service: yup
      .object({
        value: yup.number().required(message('Service is required')),
        label: yup.string(),
      })
      .required(message('Service is required')),
    files: yup
      .mixed()
      .required(message('At least one file is required'))
      .test('fileExists', message('No file selected'), (value) => {
        const files = value as File[] | File | null;
        if (!files) return false;
        if (Array.isArray(files)) return files.length > 0;
        return true;
      })
      .test(
        'fileSize',
        message('All files must be less than or equal to 50MB'),
        (value) => {
          const files = value as File[] | File | null;
          if (!files) return false;
          const maxSize = 50 * 1024 * 1024; // 50MB in bytes

          if (Array.isArray(files)) {
            return files.every((file) => file.size <= maxSize);
          } else {
            return files.size <= maxSize;
          }
        },
      )
      .test('fileType', message('Only .plan files are allowed'), (value) => {
        const files = value as File[] | File | null;
        if (!files) return false;

        if (Array.isArray(files)) {
          return files.every((file) =>
            file.name.toLowerCase().endsWith('.plan'),
          );
        } else {
          return files.name.toLowerCase().endsWith('.plan');
        }
      }),
  });

interface ImportRouteFormData {
  files: File[] | File | null;
  service: SelectOption | null;
}

export const ImportRoute = ({
  showModal,
  setHideModal,
  handleImportRoute,
}: {
  showModal: boolean;
  setHideModal: () => void;
  handleImportRoute: (data: {
    files: File[];
    service: SelectOption | null;
  }) => void;
}) => {
  const { t } = useTranslation();
  const { getOptionsByModel } = useCommonAPI();
  const methods = useForm<ImportRouteFormData>({
    resolver: yupResolver(createFileValidationSchema(t)) as any,
    mode: 'onChange',
    defaultValues: {
      service: null,
    },
  });

  const {
    control,
    handleSubmit,
    formState: { errors },
    formState: { isSubmitting },
  } = methods;

  const onSubmit = (data: ImportRouteFormData) => {
    const files = Array.isArray(data.files)
      ? data.files
      : data.files
        ? [data.files]
        : [];

    handleImportRoute({
      files,
      service: data.service,
    });
  };

  return (
    <CustomModal
      title={t('Import Route')}
      show={showModal}
      onHide={setHideModal}
    >
      <FormProvider {...methods}>
        <form onSubmit={handleSubmit(onSubmit)}>
          <div style={{ width: '40rem' }}>
            <p>
              {t('Select a .plan file to import the route into the system.')}
            </p>
            <div style={{ marginBottom: '1rem' }}>
              <PaginationSelect
                required
                label={t('Service')}
                name="service"
                control={control as any}
                loadOptions={getOptionsByModel({
                  name_modal: 'routeService',
                  search_field: 'name',
                  key: 'name',
                  value: 'id',
                })}
                placeholder={t('Select')}
              />
            </div>

            <CustomFileInput
              name="files"
              control={control as any}
              typeAccept=".plan"
              showFile
              multiple
            />

            <div
              style={{
                fontSize: '0.75rem',
                color: '#9C9D9D',
                marginTop: '0.5rem',
              }}
            >
              {t('Maximum file size is 50MB.')}
            </div>

            {errors.files && (
              <div
                style={{
                  color: 'red',
                  fontSize: '0.875rem',
                  marginTop: '0.5rem',
                }}
              >
                {errors.files.message}
              </div>
            )}
          </div>
          <ActionBtn
            styles={{
              maxWidth: '100%',
              margin: 'unset',
              padding: '0.5rem 0 1rem 0',
            }}
            leftButtons={[
              <CustomBtn
                variant="contained"
                color="primary"
                size="lg"
                type="submit"
                label={t('Confirm')}
                disabled={!methods.formState.isValid || isSubmitting}
              />,
            ]}
            rightButtons={[
              <CustomBtn
                type="button"
                variant="outline"
                color="secondary"
                size="lg"
                onClick={() => {
                  setHideModal();
                }}
                label={t('Cancel')}
              />,
            ]}
          />
        </form>
      </FormProvider>
    </CustomModal>
  );
};
