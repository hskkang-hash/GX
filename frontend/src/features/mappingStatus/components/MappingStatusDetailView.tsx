import React, { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import Select, { GroupBase, MultiValue, StylesConfig } from 'react-select';
import {
  checkPermission,
  CustomBtn,
  ROLE_PERMISSION,
  ToastTopHelper,
  useMenuData,
  useTheme,
} from 'rj-core';
import styled from 'styled-components';

import { styleCustomSelect } from '../../../components/selects/styleCustomSelect';
import { CustomTable } from '../../../components/table/CustomTable';
import Colors from '../../../configs/Colors';
import useMappingStatus from '../hooks/useMappingStatus';
import {
  MappingStatusFormValues,
  MappingStatusGroupState,
} from '../types/mappingStatus.types';

const StyledContainer = styled.div``;

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
  marginBottom: '1.5rem',
}));

const StyledButtonContainer = styled.div`
  display: flex;
  justify-content: center;
  margin-top: 1rem;
  margin-bottom: 0.5rem;
  gap: 1rem;
`;

type MappingStatusDetailViewProps = {
  groupId: number;
  groupName: string;
};

const MappingStatusDetailView = ({
  groupId,
  groupName,
}: MappingStatusDetailViewProps): React.ReactElement => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [menuData] = useMenuData();
  const [mappingStatus, setMappingStatus] = useState<
    { label: string; value: number }[]
  >([]);
  const [statusList, setStatusList] = useState<MappingStatusGroupState[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Check if user has UPDATE permission
  const hasUpdatePermission = useMemo(() => {
    return checkPermission(ROLE_PERMISSION.UPDATE, menuData);
  }, [menuData]);

  const {
    getOrderStatusOptions,
    getListMappingStatus,
    getStatusDelivery,
    updateMappingStatus,
  } = useMappingStatus();

  useEffect(() => {
    if (groupId) {
      setIsLoading(true);
      Promise.all([
        getListMappingStatus({
          currentPage: null,
          pageSize: 10000,
          objSearch: {},
          groupId,
        }),
        getStatusDelivery(),
        getOrderStatusOptions({ id: groupId }),
      ])
        .then(([res1, res2, res3]) => {
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
        })
        .finally(() => {
          setIsLoading(false);
        });
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
        title: groupName,
        dataIndex: 'status_anyang',
        key: 'status_anyang',
        render: (_: unknown, record: StatusListRow, index: number) => {
          const selectedOptions = (record.status_anyang || [])
            .map((id) => mappingStatus.find((opt) => opt.value === id))
            .filter(Boolean) as { label: string; value: number }[];

          // If no update permission, show as plain text
          if (!hasUpdatePermission) {
            return (
              <div
                key={`${record.status_guardianx.id}-${index}`}
                style={{
                  fontSize: '1rem',
                }}
              >
                {selectedOptions.length > 0
                  ? selectedOptions.map((opt) => opt.label).join(', ')
                  : '-'}
              </div>
            );
          }

          // If has update permission, show as editable select
          return (
            <div
              key={`${record.status_guardianx.id}-${index}`}
              style={{ width: '100%' }}
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
    [t, mappingStatus, theme, groupName, hasUpdatePermission],
  );

  const [isSubmitting, setIsSubmitting] = useState(false);
  const handleSaveChanges = async () => {
    setIsSubmitting(true);
    const transformedData: MappingStatusFormValues = {
      group_id: groupId,
      mappings: (statusList || []).map((status) => ({
        delivery_status_id: status.status_guardianx.id || 0,
        external_order_statuses: (status.status_anyang || []).filter(
          (statusId): statusId is number => statusId !== undefined,
        ),
      })),
    };

    const { message, success } = await updateMappingStatus(
      groupId,
      transformedData,
    );

    if (success) {
      ToastTopHelper.success(message);
    } else {
      ToastTopHelper.error(message);
    }
    setIsSubmitting(false);
  };

  if (isLoading) {
    return (
      <StyledContainer>
        <StyledDescription>{t('Loading...')}</StyledDescription>
      </StyledContainer>
    );
  }

  return (
    <StyledContainer>
      <CustomTable<StatusListRow>
        columns={columns}
        data={statusList}
        customRowBg={{
          darkBg: '#1F1F20',
          lightBg: '#FFFFFF',
        }}
      />
      <StyledButtonContainer>
        <CustomBtn
          actionType={ROLE_PERMISSION.UPDATE}
          type="button"
          size="lg"
          color="primary"
          label={t('Save changes')}
          onClick={handleSaveChanges}
          loading={isSubmitting}
          disabled={isSubmitting}
        />
      </StyledButtonContainer>
    </StyledContainer>
  );
};

export default React.memo(MappingStatusDetailView);
