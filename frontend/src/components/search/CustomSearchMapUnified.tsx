import React from 'react';
import { useTranslation } from 'react-i18next';
import { useConfigGroupSystem } from 'rj-core';

import { GEOCODING_CONFIG } from '../../configs/Constant';
import { checkCodeValid } from '../../utils/CheckCodeValid';
import CustomSearchMapGoogle from './CustomSearchMapGoogle';
import CustomSearchMapNew from './CustomSearchMapNew';

// Unified interface combining both Kakao and Google suggestion types
interface LocationSuggestion {
  id: string;
  description: string;
  place_id?: string;
  structured_formatting?: {
    main_text: string;
    secondary_text: string;
  };
  lat?: number;
  lng?: number;

  // Korean-specific fields (Kakao)
  zonecode?: string;
  roadAddress?: string;
  jibunAddress?: string;
  sido?: string;
  sigungu?: string;
  bname?: string;
  road_name?: string;
  main_building_no?: string;
  sub_building_no?: string;
  building_name?: string;

  // International fields (Google Places)
  formatted_address?: string;
  address_components?: {
    long_name: string;
    short_name: string;
    types: string[];
  }[];
  country?: string;
  country_code?: string;
  administrative_area_level_1?: string; // State/Province
  administrative_area_level_2?: string; // County/District
  locality?: string; // City
  sublocality?: string; // Neighborhood
  postal_code?: string;
  route?: string; // Street name
  street_number?: string;

  disabled?: boolean;
}

interface CustomSearchMapProps {
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

  forceProvider?: 'kakao' | 'google';
  country?: string;
  language?: string;
  onError?: string;
}

const CustomSearchMapUnified: React.FC<CustomSearchMapProps> = ({
  forceProvider,
  country,
  language,
  ...props
}) => {
  const { i18n } = useTranslation();
  const { configGroupSystem } = useConfigGroupSystem();
  const isSystemUseGoogleMap =
    configGroupSystem?.use_map?.select_map?.google_map || false;
  const countryCode = configGroupSystem?.use_map?.country_code || 'KR';
  const isEmptyConfigGroupSystem =
    !configGroupSystem || Object.keys(configGroupSystem).length === 0;
  // Determine which provider to use
  const getProvider = (): 'kakao' | 'google' => {
    // Allow force override for specific use cases
    if (forceProvider) {
      return forceProvider;
    }

    // If country is specified, use it to determine provider
    if (country) {
      return country.toUpperCase() === 'KR' ? 'kakao' : 'google';
    }

    if (isSystemUseGoogleMap || isEmptyConfigGroupSystem) {
      return 'google';
    }

    return 'kakao';
  };

  const provider = getProvider();
  const finalCountry = checkCodeValid(
    countryCode.toUpperCase() || country || GEOCODING_CONFIG.COUNTRY,
  );
  const finalLanguage = i18n.language || language || GEOCODING_CONFIG.LANGUAGE;

  if (provider === 'google') {
    return (
      <CustomSearchMapGoogle
        {...props}
        apiKey={GEOCODING_CONFIG.GOOGLE_PLACES_API_KEY}
        country={finalCountry.toUpperCase()}
        language={finalLanguage}
      />
    );
  }

  // Default to Kakao for Korea
  return <CustomSearchMapNew {...props} />;
};

export default React.memo(CustomSearchMapUnified);
export type { LocationSuggestion, CustomSearchMapProps };
