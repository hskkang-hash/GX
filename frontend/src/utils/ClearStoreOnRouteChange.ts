import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

import { useDeliveryInquiryStore } from '../features/delivery/deliveryInquiry/store/deliveryInquiryStore';
import { useMediaDataNavigationStore } from '../features/MediaData/store/MediaData.store';
import { CustomRoutes } from '../services/API';

export const ClearStoreOnRouteChange = () => {
  const location = useLocation();

  useEffect(() => {
    if (
      !location.pathname.includes(CustomRoutes.deliveryInquiry.path) ||
      location.pathname ===
        CustomRoutes.deliveryInquiry.subRoutes.addNewDeliveryInquiry.path
    ) {
      useDeliveryInquiryStore.getState().resetStore();
      useDeliveryInquiryStore.persist.clearStorage();
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  // Clear MediaData navigation store when leaving MediaData pages
  // Keep state when navigating to video analysis page (for back navigation)
  useEffect(() => {
    const isOnMediaDataPage = location.pathname === CustomRoutes.mediaData.path;
    const isOnVideoAnalysisPage = location.pathname.startsWith(
      CustomRoutes.mediaData.path + '/video-analysis',
    );

    // If not on MediaData page AND not on video analysis page, clear the store
    if (!isOnMediaDataPage && !isOnVideoAnalysisPage) {
      useMediaDataNavigationStore.getState().clearNavigationState();
    }
  }, [location.pathname]);

  return null;
};
