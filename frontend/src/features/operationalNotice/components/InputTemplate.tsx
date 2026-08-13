import React, { useRef } from 'react';
import { Control, UseFormSetValue, useFormContext } from 'react-hook-form';
import { useTranslation } from 'react-i18next';
import { CustomInputHookForm, FormBlock } from 'rj-core';

import PaginationSelect from '../../../components/selects/PaginationSelect';
import { CheckRoleAccount } from '../../../utils/CheckRoleAccount';
import { remToPx } from '../../../utils/utils';
import useCommonAPI from '../../useCommonAPI/useAPI';
import {
  ContentSection,
  OperationalNoticeFormValues,
} from '../types/operationalNotice.types';
import CustomTiptapWithTabs from './CustomTiptapWithTabs';

const InputTemplate = ({
  height,
  contentSections,
  control,
  setValue,
  onValidationChange,
}: {
  height: number;
  contentSections?: ContentSection[];
  control: Control<OperationalNoticeFormValues>;
  setValue: UseFormSetValue<OperationalNoticeFormValues>;
  onValidationChange?: (isValid: boolean) => void;
}) => {
  const { t } = useTranslation();
  const innerTopRef = useRef<HTMLDivElement>(null);
  const { getOptionsByModel } = useCommonAPI();
  const isRoleSuperuser = CheckRoleAccount('superuser');
  const editorHeight =
    height - (innerTopRef.current?.clientHeight || 0) - remToPx(3);
  const {
    formState: { isDirty },
  } = useFormContext();

  const handleContentSectionsChange = (sections: ContentSection[]) => {
    setValue('contentSections', sections, { shouldDirty: true });
  };

  const handleValidationChange = (isValid: boolean) => {
    onValidationChange?.(isValid);
  };

  return (
    <FormBlock className="h-100">
      <div
        ref={innerTopRef}
        className={`${isRoleSuperuser ? 'form-grid' : ''}`}
      >
        {isRoleSuperuser && (
          <PaginationSelect
            name="group"
            label={t('Group')}
            required
            control={control}
            placeholder={t('Select')}
            loadOptions={getOptionsByModel({
              name_modal: 'usergroup',
              search_field: 'name',
              key: 'name',
              value: 'id',
            })}
          />
        )}
        <CustomInputHookForm
          name="name"
          label={t('Name')}
          placeholder={t('Name')}
          required
        />
      </div>

      <div className="mt-3">
        <CustomTiptapWithTabs
          contentSections={contentSections}
          onChange={handleContentSectionsChange}
          onValidationChange={handleValidationChange}
          heightContent={`${editorHeight}px`}
          includeStyles={true}
        />
      </div>
    </FormBlock>
  );
};

export default React.memo(InputTemplate);
