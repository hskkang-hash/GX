import React from 'react';
import { useConfigGroupSystem, useUserInfo } from 'rj-core';

import CustomSearchMapAnYang from '../../../components/search/CustomSearchMapAnYang';
import CustomSearchMapGoogleDeliveryDashBoard from '../../../components/search/CustomSearchMapGoogleDeliveryDashBoard';
import { LocationSuggestion } from '../../../components/search/CustomSearchMapUnified';
import { GEOCODING_CONFIG } from '../../../configs/Constant';
import { checkCodeValid } from '../../../utils/CheckCodeValid';

interface SearchDeliveryDashBoardProps {
  placeholder?: string;
  onSelect?: (value: string, option: LocationSuggestion) => void;
  onSearch?: (searchText: string) => void;
  className?: string;
  style?: React.CSSProperties;
  disabled?: boolean;
  allowClear?: boolean;
  autoFocus?: boolean;
  value?: string;
  onChange?: (value: string) => void;
  onClear?: () => void;
  label?: string;
  isRequired?: boolean;
}

export const SearchDeliveryDashBoard = (
  props: SearchDeliveryDashBoardProps,
) => {
  const userInfo = useUserInfo();
  const { configGroupSystem } = useConfigGroupSystem();
  const countryCode = configGroupSystem?.use_map?.country_code || 'KR';
  const country = checkCodeValid(countryCode?.toUpperCase());
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  const currentLanguage = userInfo?.language__code || 'en';
  if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
    return (
      <CustomSearchMapGoogleDeliveryDashBoard
        {...props}
        apiKey={GEOCODING_CONFIG.GOOGLE_PLACES_API_KEY}
        country={country.toUpperCase()}
        language={currentLanguage}
      />
    );
  }

  return <CustomSearchMapAnYang {...props} />;
};
