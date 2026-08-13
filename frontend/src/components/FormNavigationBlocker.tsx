import { useEffect, useState } from 'react';
import { useBlocker, useNavigate } from 'react-router-dom';

import { useFormDirtyContext } from '../contexts/FormDirtyContext';
import { UnsavedChangesModal } from './UnsavedChangesModal';

/**
 * Component để chặn navigation khi form đang dirty
 * Sử dụng React Router's useBlocker để chặn navigation và hiển thị modal cảnh báo
 */
export const FormNavigationBlocker = (): React.ReactElement | null => {
  const { isDirty, triggerSubmit, setDirty } = useFormDirtyContext();
  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(
    null,
  );
  const [shouldProceedNavigation, setShouldProceedNavigation] = useState(false);

  // Chặn navigation khi form dirty và modal chưa hiển thị
  const blocker = useBlocker(isDirty && !showModal);

  useEffect(() => {
    if (blocker.state === 'blocked') {
      // Lưu path đang cố gắng navigate đến
      const targetPath = blocker.location.pathname + blocker.location.search;
      setPendingNavigation(targetPath);
      setShowModal(true);
      setShouldProceedNavigation(false);
    }
  }, [blocker]);

  // Thực hiện navigation khi cần
  // Luôn dùng navigate() thủ công để tránh lỗi "Invalid blocker state transition"
  // Vì sau khi submit, form không còn dirty nên blocker có thể đã unblock trước khi proceed được gọi
  useEffect(() => {
    if (!shouldProceedNavigation || !pendingNavigation) {
      return;
    }

    // Luôn dùng navigate() thủ công vì chúng ta đã có pendingNavigation path
    // Điều này an toàn hơn và tránh được race condition với blocker state
    navigate(pendingNavigation);
    setShouldProceedNavigation(false);
    setPendingNavigation(null);
  }, [shouldProceedNavigation, pendingNavigation, navigate]);

  const handleConfirm = async (): Promise<void> => {
    // Submit form - handleSubmit sẽ tự động trigger validation trước
    const submitSuccess = await triggerSubmit();

    if (submitSuccess) {
      // Nếu submit thành công, đánh dấu cần proceed navigation
      // Đóng modal trước, proceed sẽ được thực hiện trong useEffect
      // KHÔNG clear pendingNavigation ở đây - để useEffect có thể navigate
      setShowModal(false);
      setShouldProceedNavigation(true);
    } else {
      // Nếu submit thất bại (có validation errors), đóng modal để user thấy lỗi
      // Lỗi validation sẽ được hiển thị tự động bởi react-hook-form
      setShowModal(false);
      setPendingNavigation(null);
      setShouldProceedNavigation(false);
      // Không proceed với navigation - user sẽ thấy lỗi và có thể sửa
    }
  };

  const handleCancel = (): void => {
    // Clear dirty state trước để blocker không chặn lại sau khi navigate
    setDirty(false);
    // Đánh dấu cần proceed navigation
    // KHÔNG clear pendingNavigation ở đây - để useEffect có thể navigate
    setShowModal(false);
    setShouldProceedNavigation(true);
  };

  // Chỉ render modal khi có pending navigation
  if (!showModal || !pendingNavigation) {
    return null;
  }

  return (
    <UnsavedChangesModal
      show={showModal}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  );
};
