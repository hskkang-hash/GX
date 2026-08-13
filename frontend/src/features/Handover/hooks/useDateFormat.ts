import dayjs from 'dayjs';
import { useCallback, useEffect, useMemo } from 'react';
import { useConfigSystem, useUserInfo } from 'rj-core';

import {
  formatDate,
  formatDateTime,
  getDayjsFormat,
  getDayjsTimeFormat,
} from '../utils/dateFormat';

/**
 * Configure dayjs locale based on language code
 * @param languageCode - Language code (en, th, ko, kr)
 */
const configureDayjsLocale = (languageCode: string): void => {
  switch (languageCode) {
    case 'th':
      // Thai locale is already imported in App.tsx, just set it
      import('dayjs/locale/th').then(() => {
        dayjs.locale('th');
      });
      break;
    case 'ko':
    case 'kr':
      import('dayjs/locale/ko').then(() => {
        dayjs.locale('ko');
      });
      break;
    case 'en':
    default:
      dayjs.locale('en');
      break;
  }
};

/**
 * Custom hook to get date format from user settings or system defaults
 * @returns { dateFormatCode, dateFormat }
 */
export const useDateFormat = (): {
  dateFormatCode: string;
  dateFormat: string;
} => {
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];

  const languageCode =
    (userInfo as { language__code?: string })?.language__code ?? 'en';

  // Configure dayjs locale when language code changes
  useEffect(() => {
    configureDayjsLocale(languageCode);
  }, [languageCode]);

  const dateFormatCode = useMemo(
    () =>
      (userInfo as { settings?: { date_format__code?: string } })?.settings
        ?.date_format__code ??
      unitPreferences?.date_format ??
      'DD/MM/YYYY',
    [userInfo, unitPreferences],
  );

  const dateFormat = useMemo(
    () => getDayjsFormat(dateFormatCode),
    [dateFormatCode],
  );

  return { dateFormatCode, dateFormat };
};

/**
 * Custom hook to get time format from user settings or system defaults
 * @returns { timeFormatString, timeFormat }
 */
export const useTimeFormat = (): {
  timeFormatString?: string;
  timeFormat: string;
} => {
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];

  const timeFormatString = useMemo(
    () =>
      (
        userInfo as {
          settings?: { time_format__format_string?: string };
        }
      )?.settings?.time_format__format_string ??
      unitPreferences?.time_format ??
      'HH:mm',
    [userInfo, unitPreferences],
  );

  const timeFormat = useMemo(
    () => getDayjsTimeFormat(timeFormatString),
    [timeFormatString],
  );

  return { timeFormatString, timeFormat };
};

/**
 * Custom hook to get timezone code from user settings
 * @returns { timezoneCode }
 */
export const useTimezoneCode = (): {
  timezoneCode: string | null;
} => {
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();

  const timezoneCode = useMemo(() => {
    return (
      (userInfo as { timezone__code?: string })?.timezone__code ||
      configSystem?.System?.timezone ||
      null
    );
  }, [userInfo, configSystem]);

  return { timezoneCode };
};

/**
 * Custom hook to get both date and time formats with timezone
 * @returns { dateFormatCode, dateFormat, timeFormatString, timeFormat, timezoneCode }
 */
export const useDateTimeFormat = (): {
  dateFormatCode: string;
  dateFormat: string;
  timeFormatString?: string;
  timeFormat: string;
  timezoneCode: string | null;
} => {
  const { dateFormatCode, dateFormat } = useDateFormat();
  const { timeFormatString, timeFormat } = useTimeFormat();
  const { timezoneCode } = useTimezoneCode();

  return {
    dateFormatCode,
    dateFormat,
    timeFormatString,
    timeFormat,
    timezoneCode,
  };
};

/**
 * Custom hook to get formatted date/time functions with timezone conversion
 * @returns { formatDateWithTimezone, formatDateTimeWithTimezone }
 */
export const useFormattedDateTime = (): {
  formatDateWithTimezone: (
    date: dayjs.Dayjs | string | null | undefined,
  ) => string;
  formatDateTimeWithTimezone: (
    date: dayjs.Dayjs | string | null | undefined,
  ) => string;
} => {
  const { dateFormat } = useDateFormat();
  const { timeFormat } = useTimeFormat();
  const { timezoneCode } = useTimezoneCode();
  const languageCode =
    (useUserInfo() as { language__code?: string })?.language__code ?? 'en';

  const formatDateWithTimezone = useCallback(
    (date: dayjs.Dayjs | string | null | undefined): string => {
      return formatDate(date, dateFormat, languageCode, timezoneCode);
    },
    [dateFormat, languageCode, timezoneCode],
  );

  const formatDateTimeWithTimezone = useCallback(
    (date: dayjs.Dayjs | string | null | undefined): string => {
      return formatDateTime(
        date,
        dateFormat,
        timeFormat,
        languageCode,
        timezoneCode,
      );
    },
    [dateFormat, timeFormat, languageCode, timezoneCode],
  );

  return {
    formatDateWithTimezone,
    formatDateTimeWithTimezone,
  };
};
