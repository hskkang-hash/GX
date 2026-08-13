import { useFormContext } from 'react-hook-form';
import { FormBlock, useTheme } from 'rj-core';

import FileUpload from '../../../../components/Form/FileUpload';
import './Attachments.scss';

const Attachments = () => {
  const { control, watch, setValue } = useFormContext();
  const [theme] = useTheme();

  const handleFileRemove = (file: any) => {
    // Get current removed files
    const currentRemovedFiles = watch('remove_files') || [];

    // Add the removed file's ID to the list
    if (file.id) {
      setValue('remove_files', [...currentRemovedFiles, file.id]);
    }
  };
  return (
    <FormBlock>
      <div
        className={`attachments__grid mb-0 ${theme === 'dark' ? 'dark' : ''}`}
      >
        <FileUpload
          name="files"
          control={control}
          fileType="image/*"
          onFileRemove={handleFileRemove}
        />
      </div>
    </FormBlock>
  );
};

export default Attachments;
