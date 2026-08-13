import React from 'react';
import { useFormContext } from 'react-hook-form';

import InputTemplate from '../../operationalNotice/components/InputTemplate.tsx';
import PreviewTemplate from '../../operationalNotice/components/PreviewTemplate.tsx';
import {
  ContentSection,
  OperationalNoticeFormValues,
} from '../types/operationalNotice.types.ts';

const FormOperationalNotice = ({
  spaceTableHeight,
  onContentValidationChange,
}: {
  spaceTableHeight: number;
  onContentValidationChange?: (isValid: boolean) => void;
}) => {
  const { control, setValue, watch } =
    useFormContext<OperationalNoticeFormValues>();
  return (
    <div
      className="d-flex gap-3"
      style={{ height: `${spaceTableHeight}px` }}
    >
      <div
        style={{
          width: '50%',
          height: '100%',
          flex: '0 0 50%',
        }}
      >
        <InputTemplate
          height={spaceTableHeight}
          contentSections={watch('contentSections') as ContentSection[]}
          control={control}
          setValue={setValue}
          onValidationChange={onContentValidationChange}
        />
      </div>
      <div
        style={{
          width: '50%',
          height: '100%',
        }}
      >
        <PreviewTemplate
          height={spaceTableHeight}
          contentSections={watch('contentSections') as ContentSection[]}
        />
      </div>
    </div>
  );
};

export default React.memo(FormOperationalNotice);
