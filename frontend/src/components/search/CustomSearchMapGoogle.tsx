import { APIProvider, useMapsLibrary } from '@vis.gl/react-google-maps';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'rj-core';

import {
  ParsedAddress,
  parseGoogleAddress,
} from '../../utils/convertAddressGGMap';
import './CustomSearchMap.scss';
import Colors from '@/configs/Colors';

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
  formatted_address?: string;
  address_components?: {
    long_name: string;
    short_name: string;
    types: string[];
  }[];
  // International address fields
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

interface CustomSearchMapGoogleProps {
  placeholder?: string;
  onSelect?: (value: string, option: ParsedAddress) => void;
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
  apiKey: string;
  country?: string; // Country code for bias (e.g., 'TH', 'VN', 'US')
  language?: string; // Language code (e.g., 'th', 'vi', 'en')
  onError?: string;
}

// Internal component that uses the Maps API
const CustomSearchMapGoogleInternal: React.FC<CustomSearchMapGoogleProps> = ({
  placeholder = 'Address',
  onSelect,
  onSearch,
  className,
  disabled = false,
  allowClear = true,
  autoFocus = false,
  value,
  label,
  isRequired,
  onChange,
  onClear,
  style,
  apiKey,
  country = '',
  language = 'en',
  onError,
}) => {
  const { t } = useTranslation();
  const [theme] = useTheme();
  const [selectedDetail, setSelectedDetail] =
    useState<LocationSuggestion | null>(null);
  const [inputValue, setInputValue] = useState(value || '');
  const [suggestions, setSuggestions] = useState<
    google.maps.places.AutocompletePrediction[]
  >([]);
  console.log('onError', onError);
  console.log('inputValue', inputValue.trim());
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);

  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Google Places library
  const places = useMapsLibrary('places');
  const [placesService, setPlacesService] =
    useState<google.maps.places.PlacesService | null>(null);
  const [autocompleteService, setAutocompleteService] =
    useState<google.maps.places.AutocompleteService | null>(null);
  const [sessionToken, setSessionToken] =
    useState<google.maps.places.AutocompleteSessionToken | null>(null);
  // Initialize Google Places services
  useEffect(() => {
    if (!places) {
      console.log('Places library not loaded yet');
      return;
    }

    // Add a small delay to ensure the library is fully initialized
    const initializeServices = async () => {
      try {
        console.log('Attempting to initialize Google Places services...');

        // Create a temporary div for PlacesService
        const tempDiv = document.createElement('div');
        const placesService = new places.PlacesService(tempDiv);
        const autocompleteService = new places.AutocompleteService();
        const token = new places.AutocompleteSessionToken();

        console.log('Successfully initialized services:', {
          placesService,
          autocompleteService,
          token,
        });

        setPlacesService(placesService);
        setAutocompleteService(autocompleteService);
        setSessionToken(token);
      } catch (error) {
        console.error('Error initializing Google Places services:', error);
        // Retry after a short delay
        setTimeout(initializeServices, 1000);
      }
    };

    // Small delay to ensure the places library is ready
    setTimeout(initializeServices, 100);
  }, [places]);

  // Parse Google Places address components
  const parseAddressComponents = (
    addressComponents: google.maps.places.PlaceResult['address_components'] = [],
  ): Partial<LocationSuggestion> => {
    const components: Partial<LocationSuggestion> = {};

    addressComponents.forEach((component) => {
      const { types } = component;

      if (types.includes('country')) {
        components.country = component.long_name;
        components.country_code = component.short_name;
      } else if (types.includes('administrative_area_level_1')) {
        components.administrative_area_level_1 = component.long_name;
      } else if (types.includes('administrative_area_level_2')) {
        components.administrative_area_level_2 = component.long_name;
      } else if (types.includes('locality')) {
        components.locality = component.long_name;
      } else if (types.includes('sublocality')) {
        components.sublocality = component.long_name;
      } else if (types.includes('postal_code')) {
        components.postal_code = component.long_name;
      } else if (types.includes('route')) {
        components.route = component.long_name;
      } else if (types.includes('street_number')) {
        components.street_number = component.long_name;
      }
    });

    return components;
  };

  // Get place details
  const getPlaceDetails = useCallback(
    async (placeId: string): Promise<LocationSuggestion | null> => {
      if (!placesService || !sessionToken) return null;

      return new Promise((resolve) => {
        placesService.getDetails(
          {
            placeId,
            fields: [
              'place_id',
              'geometry',
              'name',
              'formatted_address',
              'address_components',
              'types',
            ],
            sessionToken,
          },
          (place, status) => {
            if (status === google.maps.places.PlacesServiceStatus.OK && place) {
              const addressData = parseAddressComponents(
                place.address_components,
              );

              const result: LocationSuggestion = {
                id: place.place_id || '',
                description: place.formatted_address || place.name || '',
                place_id: place.place_id,
                formatted_address: place.formatted_address,
                lat: place.geometry?.location?.lat(),
                lng: place.geometry?.location?.lng(),
                address_components: place.address_components?.map((comp) => ({
                  long_name: comp.long_name,
                  short_name: comp.short_name,
                  types: comp.types,
                })),
                ...addressData,
              };

              resolve(result);
            } else {
              resolve(null);
            }
          },
        );
      });
    },
    [placesService, sessionToken],
  );

  // Get autocomplete predictions
  const getAutocompletePredictions = useCallback(
    async (input: string) => {
      console.log('getAutocompletePredictions called with:', {
        input,
        autocompleteService,
        sessionToken,
      });

      if (!autocompleteService || !sessionToken || input.length < 2) {
        console.log('Early return:', {
          hasAutocompleteService: !!autocompleteService,
          hasSessionToken: !!sessionToken,
          inputLength: input.length,
        });
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }

      setLoading(true);
      const request: google.maps.places.AutocompletionRequest = {
        input,
        sessionToken,
        language,
      };

      if (country) {
        request.componentRestrictions = { country: [country.toLowerCase()] };
      }

      console.log('Making autocomplete request:', request);

      try {
        autocompleteService.getPlacePredictions(
          request,
          (predictions, status) => {
            console.log('Autocomplete response:', { predictions, status });
            setLoading(false);
            if (
              status === google.maps.places.PlacesServiceStatus.OK &&
              predictions
            ) {
              setSuggestions(predictions);
              setShowSuggestions(true);
            } else {
              console.log('No predictions or error status:', status);
              setSuggestions([]);
              setShowSuggestions(false);
            }
          },
        );
      } catch (error) {
        console.error('Error making autocomplete request:', error);
        setLoading(false);
        setSuggestions([]);
        setShowSuggestions(false);
      }
    },
    [autocompleteService, sessionToken, language, country],
  );

  // Debounced search function
  const debouncedSearch = useCallback(
    (input: string) => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
      debounceTimeoutRef.current = setTimeout(() => {
        getAutocompletePredictions(input);
      }, 300);
    },
    [getAutocompletePredictions],
  );

  // Handle input changes for user typing
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value;
      setInputValue(newValue);
      onChange?.(newValue);
      onSearch?.(newValue);

      // Trigger autocomplete search
      debouncedSearch(newValue);
    },
    [onChange, onSearch, debouncedSearch],
  );

  // Handle place selection (when user clicks on a suggestion)
  const handlePlaceSelect = useCallback(
    async (placeId: string, description: string) => {
      const placeDetails = await getPlaceDetails(placeId);
      if (placeDetails) {
        console.log('placeDetails', placeDetails);
        const formattedPlaceDetails = parseGoogleAddress(placeDetails);

        setInputValue(placeDetails.description);
        setSelectedDetail(placeDetails);
        setSuggestions([]);
        setShowSuggestions(false);
        onChange?.(placeDetails.description);
        onSelect?.(placeDetails.description, formattedPlaceDetails);

        // Create new session token for next search
        if (places) {
          setSessionToken(new places.AutocompleteSessionToken());
        }
      }
    },
    [getPlaceDetails, onChange, onSelect, places],
  );

  // Handle clear button
  const handleClear = useCallback(() => {
    setInputValue('');
    setSelectedDetail(null);
    setSuggestions([]);
    setShowSuggestions(false);
    if (inputRef.current) {
      inputRef.current.value = '';
      inputRef.current.focus();
    }
    onChange?.('');
    onSearch?.('');
    onClear?.();
  }, [onChange, onSearch, onClear]);

  // Sync with external value changes
  useEffect(() => {
    if (value !== undefined && value !== inputValue) {
      setInputValue(value);
      if (inputRef.current) {
        inputRef.current.value = value;
      }
    }
  }, [value]);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    if (showSuggestions) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showSuggestions]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  return (
    <div
      className={`custom-search-map ${theme} ${className || ''}`}
      style={style}
      ref={containerRef}
    >
      {label && (
        <label
          style={{
            display: 'block',
            marginBottom: '0.4rem',
            fontWeight: 600,
            fontSize: '1rem',
            color: theme === 'dark' ? '#fff' : '#000',
          }}
        >
          {t(label)}{' '}
          {isRequired && (
            <span style={{ color: '#ff4d4f', marginLeft: '0.25rem' }}>*</span>
          )}
        </label>
      )}
      <div style={{ position: 'relative' }}>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          disabled={disabled}
          autoFocus={autoFocus}
          placeholder={t(placeholder)}
          style={{
            width: '100%',
            height: '2.9rem',
            padding: allowClear && inputValue ? '0 40px 0 12px' : '0 12px',
            border: `1px solid ${onError ? '#ff4d4f' : theme === 'dark' ? 'var(--ga-dark-line-color)' : '#d9d9d9'}`,
            borderRadius: '6px',
            fontSize: '14px',
            backgroundColor: theme === 'dark' ? 'transparent' : '#ffffff',
            color: theme === 'dark' ? '#fff' : '#000',
            outline: 'none',
            transition: 'all 0.2s',
          }}
          onFocus={(e) => {
            e.target.style.borderColor = onError ? '#ff4d4f' : Colors.Primary;
            e.target.style.boxShadow = onError
              ? '0 0 0 2px rgba(255, 77, 79, 0.2)'
              : '0 0 0 2px rgba(5, 145, 255, 0.1)';
          }}
          onBlur={(e) => {
            e.target.style.borderColor = onError
              ? '#ff4d4f'
              : theme === 'dark'
                ? 'var(--ga-dark-line-color)'
                : '#d9d9d9';
            e.target.style.boxShadow = 'none';
          }}
        />

        {showSuggestions && suggestions.length > 0 && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              right: 0,
              backgroundColor: theme === 'dark' ? '#212529' : '#fff',
              border: `1px solid ${theme === 'dark' ? 'var(--ga-dark-line-color)' : '#e5e5e5'}`,
              borderRadius: '6px',
              boxShadow: '0 4px 16px rgba(0,0,0,0.1)',
              zIndex: 1000,
              maxHeight: '300px',
              overflowY: 'auto',
              marginTop: '4px',
            }}
          >
            {loading && (
              <div
                style={{
                  padding: '12px',
                  textAlign: 'center',
                  color: '#999',
                  fontSize: '14px',
                }}
              >
                {t('Searching...')}
              </div>
            )}
            {suggestions.map((suggestion) => (
              <div
                key={suggestion.place_id}
                onClick={() =>
                  handlePlaceSelect(suggestion.place_id, suggestion.description)
                }
                style={{
                  padding: '12px',
                  cursor: 'pointer',
                  borderBottom: `1px solid ${theme === 'dark' ? 'var(--ga-dark-line-color)' : '#f0f0f0'}`,
                  transition: 'background-color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.backgroundColor =
                    theme === 'dark' ? '#333' : '#f5f5f5';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                <div
                  style={{
                    fontWeight: 500,
                    color: theme === 'dark' ? '#fff' : '#000',
                    fontSize: '14px',
                    marginBottom: '2px',
                  }}
                >
                  {suggestion.structured_formatting?.main_text ||
                    suggestion.description.split(',')[0]}
                </div>
                <div
                  style={{
                    fontSize: '12px',
                    color: '#999',
                  }}
                >
                  {suggestion.structured_formatting?.secondary_text ||
                    suggestion.description.split(',').slice(1).join(',').trim()}
                </div>
              </div>
            ))}
          </div>
        )}
        {allowClear && inputValue && (
          <button
            type="button"
            onClick={handleClear}
            style={{
              position: 'absolute',
              right: '8px',
              top: '50%',
              transform: 'translateY(-50%)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '2px',
              color: '#999',
              fontSize: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '20px',
              height: '20px',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor =
                theme === 'dark' ? '#333' : '#f0f0f0';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            ✕
          </button>
        )}
      </div>
      {onError && (
        <div
          style={{ color: 'red', fontSize: '0.875rem', marginTop: '0.5rem' }}
        >
          {onError}
        </div>
      )}
    </div>
  );
};

// Wrapper component that provides the APIProvider
const CustomSearchMapGoogle: React.FC<CustomSearchMapGoogleProps> = (props) => {
  return (
    <APIProvider
      apiKey={props.apiKey}
      libraries={['places']}
      language={props.language}
    >
      <CustomSearchMapGoogleInternal {...props} />
    </APIProvider>
  );
};

export default CustomSearchMapGoogle;
