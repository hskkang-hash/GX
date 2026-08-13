import { useEffect, RefObject } from 'react';
import { OBSERVER_CONFIG } from '../constants';

interface UseInfiniteScrollProps {
  isRealtime: boolean;
  scrollContainerRef: RefObject<HTMLDivElement>;
  loadMoreTriggerRef: RefObject<HTMLDivElement>;
  onLoadMore?: () => void;
  hasMore: boolean;
  isLoadingMore: boolean;
}

export const useInfiniteScroll = ({
  isRealtime,
  scrollContainerRef,
  loadMoreTriggerRef,
  onLoadMore,
  hasMore,
  isLoadingMore,
}: UseInfiniteScrollProps) => {
  useEffect(() => {
    // Only use infinite scroll for realtime mode
    if (!isRealtime) return;

    const triggerElement = loadMoreTriggerRef.current;
    if (!triggerElement || !onLoadMore || !hasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && hasMore && !isLoadingMore) {
          onLoadMore();
        }
      },
      {
        root: scrollContainerRef.current,
        ...OBSERVER_CONFIG,
      },
    );

    observer.observe(triggerElement);

    return () => {
      observer.disconnect();
    };
  }, [
    isRealtime,
    scrollContainerRef,
    loadMoreTriggerRef,
    onLoadMore,
    hasMore,
    isLoadingMore,
  ]);
};

