import React, { useRef, useState, useMemo, useEffect } from 'react';
import { useTheme } from 'rj-core';

export default function AimIframe({ url, onLoadingChange, onNavigationChange, iframeRef }) {
  const ref = useRef(null);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);
  const loadingTimeoutRef = useRef(null);
  const [theme] = useTheme();
  const navigationCountRef = useRef(0);
  const isInitialLoadRef = useRef(true);

  // Expose iframe ref to parent
  useEffect(() => {
    if (iframeRef) {
      iframeRef.current = ref.current;
    }
  }, [iframeRef]);

  const proxyUrl = useMemo(() => {
    const apiUrl = import.meta.env.VITE_API_URL || '';
    const proxyPath = '/api/proxy/proxyhtml';
    const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
    const currentTheme = theme || 'light';
    // return `${baseUrl}${proxyPath}?url=${encodeURIComponent(url)}&theme=${currentTheme}`;
    return `${baseUrl}${proxyPath}?url=https%3A%2F%2Faim.koca.go.kr%2FeaipPub%2FPackage%2F2025-11-13%2Fhtml%2Findex-en-GB.html&theme=${currentTheme}`;
  }, [url, theme]);

  const setLoadingState = (isLoading) => {
    setLoading(isLoading);
    if (onLoadingChange) {
      onLoadingChange(isLoading);
    }
  };

  const handleLoadStart = () => {
    console.log('[AimIframe] Load started');
    setErr(null);
    setLoadingState(true);
    // Clear any existing timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
    }
    // Set a timeout to ensure loading doesn't get stuck (max 30 seconds)
    loadingTimeoutRef.current = setTimeout(() => {
      console.warn('[AimIframe] Load timeout, forcing loading to false');
      setLoadingState(false);
    }, 30000);
  };

  const handleLoad = () => {
    console.log('[AimIframe] Loaded:', proxyUrl);
    setErr(null);
    // Clear timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }

    // Track navigation - increment count for every load after the initial one
    if (!isInitialLoadRef.current) {
      navigationCountRef.current += 1;
      console.log('[AimIframe] Navigation detected, count:', navigationCountRef.current);
      if (onNavigationChange) {
        onNavigationChange(navigationCountRef.current);
      }
    } else {
      console.log('[AimIframe] Initial load, not counting as navigation');
      isInitialLoadRef.current = false;
    }

    // Small delay to ensure content is fully rendered
    setTimeout(() => {
      setLoadingState(false);
    }, 100);
  };

  const handleError = () => {
    setErr('Failed to load content');
    // Clear timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }
    setLoadingState(false);
    console.error('[AimIframe] Error loading:', proxyUrl);
  };

  useEffect(() => {
    const iframe = ref.current;
    if (!iframe) return;

    // Set initial loading state
    setLoadingState(true);

    // Add event listeners for all load events
    iframe.addEventListener('loadstart', handleLoadStart);
    iframe.addEventListener('load', handleLoad);
    iframe.addEventListener('error', handleError);

    // Also listen to onload attribute for compatibility
    iframe.onload = handleLoad;
    iframe.onerror = handleError;

    // Set src
    iframe.src = proxyUrl;

    // Monitor iframe content changes (for navigation within iframe)
    // This helps detect when user clicks links inside iframe
    let lastSrc = proxyUrl;
    const checkInterval = setInterval(() => {
      if (iframe && iframe.contentWindow) {
        try {
          // Try to access iframe location (may fail due to CORS)
          const currentSrc = iframe.src;
          if (currentSrc !== lastSrc) {
            console.log('[AimIframe] Source changed, starting load');
            handleLoadStart();
            lastSrc = currentSrc;
          }
        } catch (e) {
          // Cross-origin access denied, ignore
        }
      }
    }, 500);

    // Cleanup
    return () => {
      clearInterval(checkInterval);
      if (iframe) {
        iframe.removeEventListener('loadstart', handleLoadStart);
        iframe.removeEventListener('load', handleLoad);
        iframe.removeEventListener('error', handleError);
        iframe.onload = null;
        iframe.onerror = null;
      }
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, [proxyUrl]);

  // Handle clicks on iframe to detect navigation
  useEffect(() => {
    const iframe = ref.current;
    if (!iframe) return;

    const handleIframeClick = () => {
      // When user clicks on iframe, assume navigation might happen
      // Set loading after a short delay to allow navigation to start
      setTimeout(() => {
        // Check if iframe is still loading
        try {
          if (
            iframe.contentDocument &&
            iframe.contentDocument.readyState !== 'complete'
          ) {
            setLoadingState(true);
          }
        } catch (e) {
          // Cross-origin access denied, set loading anyway
          setLoadingState(true);
        }
      }, 100);
    };

    // Add click listener to parent div
    const container = iframe.parentElement;
    if (container) {
      container.addEventListener('click', handleIframeClick);
    }

    return () => {
      if (container) {
        container.removeEventListener('click', handleIframeClick);
      }
    };
  }, []);

  // Handle theme changes and navigation events via postMessage
  useEffect(() => {
    const iframe = ref.current;
    if (!iframe || !iframe.contentWindow) return;

    let iframeReady = false;
    let themeSent = false;

    // Send theme change message to iframe
    const sendThemeToIframe = () => {
      if (themeSent) {
        console.log('[AimIframe] Theme already sent, skipping duplicate');
        return;
      }

      try {
        iframe.contentWindow.postMessage(
          {
            type: 'THEME_CHANGE',
            theme: theme || 'light',
          },
          '*',
        );
        themeSent = true;
        console.log('[AimIframe] Sent theme to iframe:', theme);
      } catch (e) {
        console.error('[AimIframe] Failed to send theme to iframe:', e);
      }
    };

    // Listen for iframe messages
    const handleMessage = (event) => {
      if (!event.data || !event.data.type) return;

      switch (event.data.type) {
        case 'IFRAME_READY':
          console.log('[AimIframe] Iframe ready, current theme:', theme);
          iframeReady = true;
          // Only send if theme is different from iframe's current theme
          if (event.data.theme !== theme) {
            console.log('[AimIframe] Theme mismatch, sending theme:', theme);
            setTimeout(sendThemeToIframe, 100);
          } else {
            console.log('[AimIframe] Theme matches, no need to send');
          }
          break;

        case 'IFRAME_NAVIGATED':
          // Iframe tells us it navigated (alternative to load event)
          console.log('[AimIframe] Received navigation event from iframe');
          if (!isInitialLoadRef.current) {
            navigationCountRef.current += 1;
            console.log('[AimIframe] Navigation count:', navigationCountRef.current);
            if (onNavigationChange) {
              onNavigationChange(navigationCountRef.current);
            }
          }
          break;

        case 'IFRAME_BACK_COMPLETED':
          // Iframe tells us back navigation completed
          console.log('[AimIframe] Back navigation completed in iframe');
          navigationCountRef.current = Math.max(0, navigationCountRef.current - 1);
          if (onNavigationChange) {
            onNavigationChange(navigationCountRef.current);
          }
          break;
      }
    };

    window.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('message', handleMessage);
    };
  }, [theme, onNavigationChange]);

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {err && (
        <div
          style={{
            color: 'red',
            padding: '10px',
            background: '#fee',
            borderRadius: '4px',
            margin: '10px',
            position: 'absolute',
            top: 0,
            left: 0,
            zIndex: 1000,
          }}
        >
          {err}
        </div>
      )}
      <iframe
        ref={ref}
        src={proxyUrl}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          display: 'block',
        }}
        // QUAN TRỌNG: Thêm allow-popups-to-escape-sandbox
        sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-modals"
        referrerPolicy="no-referrer"
        onLoad={handleLoad}
        onError={handleError}
        title="AIP iframe"
      />
    </div>
  );
}
