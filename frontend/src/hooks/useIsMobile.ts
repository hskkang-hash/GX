import { useState, useEffect } from 'react';

const useIsMobile = (breakpoint = 768) => {
  // Initialize with a function to avoid calling window during SSR
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.innerWidth < breakpoint;
    }
    return false;
  });

  useEffect(() => {
    const checkIsMobile = () => {
      const mobile = window.innerWidth < breakpoint;
      // Only update state if the value actually changed
      setIsMobile((prevIsMobile) => {
        if (prevIsMobile !== mobile) {
          return mobile;
        }
        return prevIsMobile;
      });
    };

    // Only check on mount if window is available
    if (typeof window !== 'undefined') {
      checkIsMobile();
    }

    const debounce = (func: (...args: unknown[]) => void, delay: number) => {
      let timeoutId: NodeJS.Timeout;
      return (...args: unknown[]) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func(...args), delay);
      };
    };

    const debouncedCheckIsMobile = debounce(checkIsMobile, 250);

    if (typeof window !== 'undefined') {
      window.addEventListener('resize', debouncedCheckIsMobile);
    }

    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('resize', debouncedCheckIsMobile);
      }
    };
  }, [breakpoint]);

  return isMobile;
};

export default useIsMobile;
