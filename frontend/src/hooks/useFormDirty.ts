import { useEffect } from 'react';
import type { UseFormHandleSubmit, FieldValues } from 'react-hook-form';

import { useFormDirtyContext } from '../contexts/FormDirtyContext';

interface UseFormDirtyProps<T extends FieldValues> {
  isDirty: boolean;
  triggerValidation: () => Promise<boolean>;
  handleSubmit: UseFormHandleSubmit<T>;
  onSubmit: (data: T) => Promise<void> | void;
  isValid?: boolean;
}

/**
 * Hook để đăng ký form dirty state và submit handler
 * Sử dụng trong các component form để tự động chặn navigation khi form có thay đổi
 * và submit form khi click Save Changes trong modal
 *
 * @param props - Configuration object
 * @param props.isDirty - Trạng thái dirty của form (thường từ react-hook-form's formState.isDirty)
 * @param props.triggerValidation - Function để trigger validation (thường từ react-hook-form's trigger)
 * @param props.handleSubmit - handleSubmit function từ react-hook-form
 * @param props.onSubmit - Callback khi form submit thành công
 * @param props.isValid - Trạng thái valid của form (thường từ react-hook-form's formState.isValid)
 *
 * @example
 * ```tsx
 * const MyForm = () => {
 *   const methods = useForm();
 *   const { formState: { isDirty, isValid }, trigger, handleSubmit } = methods;
 *
 *   useFormDirty({
 *     isDirty,
 *     triggerValidation: trigger,
 *     handleSubmit,
 *     onSubmit: async (data) => { // save data },
 *     isValid
 *   });
 *
 *   return <form>...</form>;
 * };
 * ```
 */
export const useFormDirty = <T extends FieldValues>({
  isDirty,
  triggerValidation,
  handleSubmit,
  onSubmit,
  isValid,
}: UseFormDirtyProps<T>): void => {
  const { setDirty, registerSubmitHandler, unregisterSubmitHandler } =
    useFormDirtyContext();

  useEffect(() => {
    setDirty(isDirty);
  }, [isDirty, setDirty]);

  useEffect(() => {
    // Kiểm tra handleSubmit và onSubmit có sẵn không
    // Đợi cho đến khi cả hai đều sẵn sàng trước khi đăng ký handler
    if (!handleSubmit) {
      return;
    }

    if (typeof handleSubmit !== 'function') {
      console.error(
        'handleSubmit is not a function',
        typeof handleSubmit,
        handleSubmit,
      );
      return;
    }

    if (!onSubmit) {
      return;
    }

    if (typeof onSubmit !== 'function') {
      console.error('onSubmit is not a function', typeof onSubmit, onSubmit);
      return;
    }

    let submitSuccess = false;

    const submitHandler = handleSubmit(
      async (data) => {
        await onSubmit(data);
        submitSuccess = true;
      },
      () => {
        // Validation errors
        submitSuccess = false;
      },
    );

    const formSubmitHandler = {
      submit: async (): Promise<boolean> => {
        // Submit form - handleSubmit sẽ tự động trigger validation
        submitSuccess = false;
        try {
          await submitHandler();
          return submitSuccess;
        } catch (error) {
          console.error('Error submitting form:', error);
          return false;
        }
      },
      triggerValidation: async (): Promise<boolean> => {
        return await triggerValidation();
      },
    };

    registerSubmitHandler(formSubmitHandler);

    // Cleanup: reset dirty state và unregister handler khi component unmount
    return () => {
      setDirty(false);
      unregisterSubmitHandler();
    };
  }, [
    triggerValidation,
    handleSubmit,
    onSubmit,
    registerSubmitHandler,
    unregisterSubmitHandler,
    setDirty,
    isValid,
  ]);
};
