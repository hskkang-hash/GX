import { useState, useEffect, useMemo } from 'react';

import { PAGE_SIZE } from '../constants';
import { PaginationState } from '../types';

interface UsePaginationProps {
  notificationStatus: 'realtime' | 'completed';
  messagesLength: number;
  currentApiPage: number;
  totalApiPages: number;
}

export const usePagination = ({
  notificationStatus,
  messagesLength,
  currentApiPage,
  totalApiPages,
}: UsePaginationProps) => {
  const [frontendPage, setFrontendPage] = useState(1);

  const isRealtime = notificationStatus === 'realtime';

  const paginationState: PaginationState = useMemo(() => {
    const currentPage = isRealtime ? frontendPage : currentApiPage;
    const totalPages = isRealtime
      ? Math.ceil(messagesLength / PAGE_SIZE)
      : totalApiPages;
    const startIndex = isRealtime
      ? (frontendPage - 1) * PAGE_SIZE
      : (currentApiPage - 1) * PAGE_SIZE;
    const endIndex = isRealtime ? startIndex + PAGE_SIZE : messagesLength;

    return {
      currentPage,
      totalPages,
      startIndex,
      endIndex,
      isRealtime,
    };
  }, [isRealtime, frontendPage, currentApiPage, messagesLength, totalApiPages]);

  // Reset frontend page when status changes
  useEffect(() => {
    setFrontendPage(1);
  }, [notificationStatus]);

  const goToPreviousPage = () => {
    setFrontendPage((prev) => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setFrontendPage((prev) => Math.min(paginationState.totalPages, prev + 1));
  };

  return {
    paginationState,
    goToPreviousPage,
    goToNextPage,
  };
};
