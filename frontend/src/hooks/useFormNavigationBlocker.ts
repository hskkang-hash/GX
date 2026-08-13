import { useEffect, useState } from 'react';
import { useBlocker } from 'react-router-dom';

interface UseFormNavigationBlockerProps {
  isDirty: boolean;
  onSave: () => Promise<void>;
  onCancel: () => void;
  onError?: (errors: any) => void;
  handleSubmit: (
    onValid: () => Promise<void>,
    onInvalid?: (errors: any) => void,
  ) => (e?: any) => Promise<void>;
}

interface UseFormNavigationBlockerReturn {
  showModal: boolean;
  setShowModal: (show: boolean) => void;
  handleModalSave: () => Promise<void>;
  handleModalCancel: () => void;
}

export const useFormNavigationBlocker = ({
  isDirty,
  onSave,
  onCancel,
  onError,
  handleSubmit,
}: UseFormNavigationBlockerProps): UseFormNavigationBlockerReturn => {
  const [showModal, setShowModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(
    null,
  );

  // Block navigation when form is dirty and modal is not showing
  const blocker = useBlocker(isDirty && !showModal);

  useEffect(() => {
    if (blocker.state === 'blocked') {
      // Set pending navigation to the current path
      setPendingNavigation(blocker.location.pathname + blocker.location.search);
      setShowModal(true);
    }
  }, [blocker]);

  const handleModalSave = async () => {
    try {
      await handleSubmit(
        async () => {
          await onSave();
          setShowModal(false);

          if (pendingNavigation && blocker.state === 'blocked') {
            blocker.proceed?.();
          }
          setPendingNavigation(null);
        },
        (errors) => {
          // Handle validation errors (navigate to tab with errors)
          if (onError) {
            onError(errors);
          }
          // Close modal when validation fails
          setShowModal(false);
        },
      )();
    } catch (error) {
      console.error('Error saving form:', error);
    }
  };

  const handleModalCancel = () => {
    setShowModal(false);
    onCancel();

    // Navigate to the pending location by proceeding with the blocked navigation
    if (pendingNavigation && blocker.state === 'blocked') {
      blocker.proceed?.();
    }
    setPendingNavigation(null);
  };

  return {
    showModal,
    setShowModal,
    handleModalSave,
    handleModalCancel,
  };
};
