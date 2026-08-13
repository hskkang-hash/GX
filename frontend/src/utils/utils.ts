import { useEffect, useState } from 'react';

export const remToPx = (rem: number) =>
  rem * parseFloat(getComputedStyle(document.documentElement).fontSize);

// Custom debounce hook
export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
};

export const formatWithUnit = (obj: { value: number; unit: string }) => {
  if (!obj) return null;
  return obj.value != null && obj.unit != null
    ? `${obj.value} ${obj.unit}`
    : null;
};

export const haversineDistance = (
  coord1: { latitude: number; longitude: number },
  coord2: { latitude: number; longitude: number },
) => {
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const R = 6371; // Earth's radius in km

  const dLat = toRad(coord2.latitude - coord1.latitude);
  const dLon = toRad(coord2.longitude - coord1.longitude);
  const lat1 = toRad(coord1.latitude);
  const lat2 = toRad(coord2.latitude);

  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // in km
};

// convert example: 120 km to {value: 120, unit: 'km'}
export const convertValueToUnit = (value: string) => {
  const [num, unit] = value?.split(' ');
  return { value: parseFloat(num), unit: unit };
};

export const isEmptyObject = (obj: object) => {
  return obj && typeof obj === 'object' && Object.keys(obj).length === 0;
};

export const isObject = (obj: any) => {
  return obj && typeof obj === 'object' && Object.keys(obj).length > 0;
};

export const getContrastTextColor = (
  hexColor: string,
  defaultColor: string = '#FFFFFF',
) => {
  if (!hexColor) return defaultColor;
  const hex = hexColor.replace('#', '');

  const r = parseInt(hex.substr(0, 2), 16);
  const g = parseInt(hex.substr(2, 2), 16);
  const b = parseInt(hex.substr(4, 2), 16);

  const yiq = (r * 299 + g * 587 + b * 114) / 1000;

  return yiq >= 128 ? '#000000' : '#FFFFFF';
};

export function checkPhoneMaskType(phoneNumber: string) {
  if (phoneNumber) {
    if (phoneNumber.startsWith('(+82)')) {
      return 'Kr';
    } else if (phoneNumber.startsWith('(+66)')) {
      return 'Th';
    } else {
      return 'En';
    }
  } else {
    return 'Kr';
  }
}

export function getPhoneMaskTypeByLanguage(language: string) {
  switch (language) {
    case 'ko':
      return 'Kr';
    case 'th':
      return 'Th';
    case 'en':
    default:
      return 'En';
  }
}

export const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};
