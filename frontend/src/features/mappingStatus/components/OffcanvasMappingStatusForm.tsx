import { yupResolver } from '@hookform/resolvers/yup';
import React, { useEffect, useMemo, useState } from 'react';
import { Control, FormProvider, useForm } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import Select, { GroupBase, MultiValue, StylesConfig } from 'react-select';
import { LoadOptions } from 'react-select-async-paginate';
import {
  ActionBtn,
  CustomBtn,
  OffCanvas,
  ROLE_PERMISSION,
  useTheme,
  useUserInfo,
} from 'rj-core';
import styled from 'styled-components';

import { SelectOption } from '../../../components/selects/CustomSelect';
import PaginationSelect from '../../../components/selects/PaginationSelect';
import { styleCustomSelect } from '../../../components/selects/styleCustomSelect';
import { CustomTable } from '../../../components/table/CustomTable';
import Colors from '../../../configs/Colors';
import {
  schemaMappingStatus,
  schemaMappingStatusIsSuperuser,
} from '../../../services/schemaForm';
import useCommonAPI from '../../useCommonAPI/useAPI';
import useMappingStatus from '../hooks/useMappingStatus';
import {
  MappingStatusFormValues,
  MappingStatusGroupState,
  MappingStatusState,
} from '../types/mappingStatus.types';
import { cleanFormSubmit } from '../utils/cleanFormSubmit';

const StyledLabel = styled('label')<{
  mode: 'light' | 'dark';
  error?: boolean;
  noMarginBottom?: boolean;
}>(({ mode, error, noMarginBottom }) => ({
  fontWeight: 600,
  fontSize: '1.2rem',
  color: mode === 'dark' ? Colors.Gray3 : Colors.Gray7,
  marginBottom: noMarginBottom ? '0rem !important' : '0.4rem',
  span: {
    color: error ? 'red' : 'inherit',
    marginLeft: '0.25rem',
  },
  alignContent: 'center',
}));

const StyledDescription = styled('p')(() => ({
  fontSize: '1rem',
  color: '#9C9D9D',
  fontFamily: 'Inter',
  fontWeight: 400,
  fontStyle: 'Regular',
  lineHeight: '140%',
  letterSpacing: '0.16px',
}));

type OffcanvasOrderStatusFormProps = {
  show: boolean;
  onHide: () => void;
  id: string;
  listIdGroup?: number[];
  initialValues?: MappingStatusState | null;
  onSubmit: (values: MappingStatusFormValues) => Promise<void>;
};

const OffcanvasOrderStatusForm = ({
  show,
  onHide,
  id,
  listIdGroup = [],
  initialValues = null,
  onSubmit,
}: OffcanvasOrderStatusFormProps): React.ReactElement => {
  const { t } = useTranslation();
  const userInfo = useUserInfo();
  const isRoleSuperuser = useMemo(
    () => userInfo?.roles?.some((role: any) => role.code === 'superuser'),
    [userInfo],
  );
  const [theme] = useTheme();
  const [mappingStatus, setMappingStatus] = useState<
    { label: string; value: number }[]
  >([]);
  const [statusList, setStatusList] = useState<MappingStatusGroupState[]>([]);
  const { getListGroup } = useCommonAPI();
  const { getOrderStatusOptions, getListMappingStatus, getStatusDelivery } =
    useMappingStatus();

  const methods = useForm({
    resolver: yupResolver(
      isRoleSuperuser ? schemaMappingStatusIsSuperuser : schemaMappingStatus,
    ),
  });

  const {
    handleSubmit,
    formState: { isSubmitting, isValid },
    control,
    reset,
    watch,
    setValue,
  } = methods;

  const groupId = watch('group')?.value as number;

  useEffect(() => {
    if (show && initialValues) {
      reset({
        id: initialValues?.id,
        group: initialValues?.group__id
          ? {
              value: initialValues?.group__id,
              label: initialValues?.group__name,
            }
          : (null as unknown as object),
      });
    } else {
      reset({
        group: null as unknown as object,
      });
    }
  }, [show, initialValues, reset]);

  useEffect(() => {
    if (show && groupId) {
      Promise.all([
        getListMappingStatus({
          currentPage: null,
          pageSize: 10000,
          objSearch: {},
          groupId,
        }),
        getStatusDelivery(),
        getOrderStatusOptions({ id: groupId }),
      ]).then(([res1, res2, res3]) => {
        const mappings: MappingStatusGroupState[] = Array.isArray(res1)
          ? (res1 as MappingStatusGroupState[])
          : ((res1?.mappings as MappingStatusGroupState[]) ?? []);

        const resultStatusList = res2.map(
          (status: { id: number; name: string }) => {
            const found = mappings.find(
              (m: MappingStatusGroupState) =>
                m.status_guardianx.id === status.id,
            );

            return {
              status_guardianx: {
                id: status.id,
                name: status.name,
              },
              status_anyang: found?.status_anyang ?? [],
            };
          },
        );

        setStatusList(resultStatusList);
        setMappingStatus((res3 ?? []) as { label: string; value: number }[]);
      });
    } else {
      setStatusList([]);
      setMappingStatus([]);
    }
  }, [groupId]); // eslint-disable-line react-hooks/exhaustive-deps

  type StatusListRow = {
    status_guardianx: { id?: number; name?: string };
    status_anyang?: (number | undefined)[];
  };

  const columns = useMemo(
    () => [
      {
        title: t('GuardianX'),
        dataIndex: 'status_guardianx',
        key: 'status_guardianx',
        render: (_: unknown, record: StatusListRow, index: number) => {
          return (
            <div
              key={`${record.status_guardianx.id}-${index}`}
              style={{
                fontSize: '1rem',
              }}
            >
              {record.status_guardianx.name}
            </div>
          );
        },
      },
      {
        title: watch('group')?.label || t('ANYANG'),
        dataIndex: 'status_anyang',
        key: 'status_anyang',
        render: (_: unknown, record: StatusListRow, index: number) => {
          const selectedOptions = (record.status_anyang || [])
            .map((id) => mappingStatus.find((opt) => opt.value === id))
            .filter(Boolean) as { label: string; value: number }[];

          return (
            <div
              key={`${record.status_guardianx.id}-${index}`}
              style={{ width: '16rem' }}
            >
              <Select<{ label: string; value: number }, true>
                isMulti
                name={`status_anyang-${index}`}
                value={selectedOptions}
                options={mappingStatus}
                className="basic-multi-select"
                classNamePrefix="select"
                noOptionsMessage={() => t('No options')}
                styles={
                  styleCustomSelect(
                    theme as 'light' | 'dark',
                    '2rem',
                  ) as unknown as StylesConfig<
                    { label: string; value: number },
                    true,
                    GroupBase<{ label: string; value: number }>
                  >
                }
                onChange={(
                  newValue: MultiValue<{ label: string; value: number }>,
                ) => {
                  const nextIds = newValue.map((opt) => opt.value);
                  setStatusList((prev) => {
                    const next = [...prev];
                    next[index] = {
                      ...next[index],
                      status_anyang: nextIds,
                    } as MappingStatusGroupState;
                    return next;
                  });
                }}
                menuPlacement="auto"
                placeholder={t('Select')}
              />
            </div>
          );
        },
      },
    ],
    [t, control, mappingStatus, setValue, theme], // eslint-disable-line react-hooks/exhaustive-deps
  );

  return (
    <OffCanvas
      title={initialValues ? t('Edit Status') : t('Add New Status')}
      show={show}
      onHide={onHide}
      id={id}
    >
      <FormProvider {...methods}>
        <form
          onSubmit={handleSubmit((data) => {
            const transformedData: MappingStatusFormValues = {
              group_id: data.group?.value || 0,
              mappings: (statusList || []).map((status) => ({
                delivery_status_id: status.status_guardianx.id || 0,
                external_order_statuses: (status.status_anyang || []).filter(
                  (statusId): statusId is number => statusId !== undefined,
                ),
              })),
            };
            onSubmit(
              cleanFormSubmit(transformedData) as MappingStatusFormValues,
            );
          })}
        >
          <div className="body-canvas d-flex gap-3">
            {isRoleSuperuser && (
              <PaginationSelect
                required
                label={t('Group')}
                name="group"
                control={control as unknown as Control<MappingStatusFormValues>}
                loadOptions={
                  getListGroup({
                    exclude_value: listIdGroup,
                  }) as unknown as LoadOptions<
                    SelectOption,
                    GroupBase<SelectOption>,
                    { page: number }
                  >
                }
                placeholder={t('Select')}
              />
            )}
            <div>
              <StyledLabel mode={theme as 'light' | 'dark'}>
                {t('Status List')}
              </StyledLabel>
              <div>
                {!watch('group') ? (
                  <>
                    <StyledDescription>
                      {t(
                        'No data available. Please select a group first, then choose the corresponding status to map.',
                      )}
                    </StyledDescription>
                  </>
                ) : (
                  <CustomTable<StatusListRow>
                    columns={columns}
                    data={statusList}
                  />
                )}
              </div>
            </div>
          </div>
          <div className="offcanvas-footer">
            <ActionBtn
              leftButtons={[
                <CustomBtn
                  actionType={
                    initialValues
                      ? ROLE_PERMISSION.UPDATE
                      : ROLE_PERMISSION.CREATE
                  }
                  type="submit"
                  size="lg"
                  disabled={isSubmitting || !isValid}
                  color="primary"
                  label={t('Save')}
                />,
              ]}
              rightButtons={[
                <CustomBtn
                  type="button"
                  variant="outline"
                  size="lg"
                  color="secondary"
                  onClick={onHide}
                  label={t('Cancel')}
                />,
              ]}
            />
          </div>
        </form>
      </FormProvider>
    </OffCanvas>
  );
};

export default React.memo(OffcanvasOrderStatusForm);
