import { format } from 'date-fns';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/en';
import 'dayjs/locale/ko';
import 'dayjs/locale/th';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';
import { useEffect, useMemo } from 'react';
import { useConfigSystem, useUserInfo } from 'rj-core';

import i18n from '@/i18n';

dayjs.extend(customParseFormat);
dayjs.extend(utc);
dayjs.extend(timezone);

export const getDateFormatString = (date_format: string): string => {
  switch (date_format) {
    case 'YYYY-MM-DD':
      return 'yyyy-MM-dd';
    case 'DD/MM/YYYY':
      return 'dd/MM/yyyy';
    case 'MM/DD/YYYY':
      return 'MM/dd/yyyy';
    case 'Short Date':
      return 'P';
    case 'DD-MM-YYYY':
      return 'dd-MM-yyyy';
    case 'Month DD, YYYY':
      return 'MMMM dd, yyyy';
    case 'DD Month YYYY':
      return 'dd MMMM yyyy';
    case 'YYYY/MM/DD':
      return 'yyyy/MM/dd';
    case 'YY/MM/DD':
      return 'yy/MM/dd';
    default:
      return 'yyyy-MM-dd';
  }
};

export const getTimeFormatString = (time_format: string): string => {
  switch (time_format) {
    case '24':
      return 'HH:mm';
    case '12':
      return 'hh:mm a';
    case '24_full':
      return 'HH:mm:ss';
    case '12_full':
      return 'hh:mm:ss a';
    default:
      return 'HH:mm';
  }
};

export const getTimeFormatString2 = (time_format: string): string => {
  switch (time_format) {
    case '24':
      return 'HH:mm';
    case '12':
      return 'hh:mm A';
    case '24_full':
      return 'HH:mm:ss';
    case '12_full':
      return 'hh:mm:ss A';
    default:
      return 'HH:mm';
  }
};

const getDateTimeFormat = (
  date_format: string,
  time_format: string,
): string => {
  const now = new Date();
  const dateStr = getDateFormatString(date_format);
  const timeStr = getTimeFormatString(time_format);
  return format(now, `${dateStr} ${timeStr}`);
};
export default getDateTimeFormat;

// Helper function to convert date format code to dayjs format string
export const getDateFormatStringForDayjs = (date_format: string): string => {
  switch (date_format) {
    case 'YYYY-MM-DD':
      return 'YYYY-MM-DD';
    case 'DD/MM/YYYY':
      return 'DD/MM/YYYY';
    case 'MM/DD/YYYY':
      return 'MM/DD/YYYY';
    case 'DD-MM-YYYY':
      return 'DD-MM-YYYY';
    case 'Month DD, YYYY':
      return 'MMMM DD, YYYY';
    case 'DD Month YYYY':
      return 'DD MMMM YYYY';
    case 'YYYY/MM/DD':
      return 'YYYY/MM/DD';
    case 'YY/MM/DD':
      return 'YY/MM/DD';
    default:
      return 'YYYY-MM-DD';
  }
};

// Convert datetime to time
export const convertDateTimeToTime = (
  datetime: string | Date | null | undefined,
  datetimeFormat: string = 'YYYY-MM-DD HH:mm:ss',
  timeFormat: string = 'HH:mm',
) => {
  if (!datetime) return '';
  return dayjs(datetime, datetimeFormat).format(timeFormat);
};

export const normalizeToStandard = (value: any) => {
  const date = new Date(value);
  if (isNaN(date.getTime())) return 'Invalid Date';
  return dayjs(date).format('DD/MM/YYYY HH:mm:ss');
};

/**
 * Hook to get convertDateFormatToUTC function with dateFormat from user settings
 * @returns Function to convert date string to UTC format
 */
export const useConvertDate = () => {
  const userInfo = useUserInfo();
  const [configSystem] = useConfigSystem();
  const unitPreferences =
    configSystem && configSystem['system_default_formats'];
  const locale = i18n.language ?? 'en';
  useEffect(() => {
    dayjs.locale(locale);
  }, [locale]);

  const timeZoneFormat = useMemo(
    () =>
      (userInfo as { timezone__code?: string })?.timezone__code ??
      configSystem?.System?.timezone ??
      'UTC',
    [userInfo, unitPreferences],
  );

  const dateFormat = useMemo(
    () =>
      getDateFormatStringForDayjs(
        (userInfo as { settings?: { date_format__code?: string } })?.settings
          ?.date_format__code ??
          unitPreferences?.date_format ??
          'YYYY/MM/DD',
      ),
    [userInfo, unitPreferences],
  );

  const timeFormat = useMemo(
    () =>
      getTimeFormatString2(
        (userInfo as { settings?: { time_format__code?: string } })?.settings
          ?.time_format__code ??
          unitPreferences?.time_format ??
          '24',
      ),
    [userInfo, unitPreferences],
  );

  const datetimeFormat = useMemo(
    () => `${dateFormat} ${timeFormat}`,
    [dateFormat, timeFormat],
  );

  // Backend timezone (Vietnam) - used for API requests
  const BACKEND_TIMEZONE = 'Asia/Ho_Chi_Minh';
  const apiTimeZone = useMemo(
    () => configSystem?.System?.timezone ?? BACKEND_TIMEZONE,
    [configSystem],
  );

  const convertDateFormatToUTC = useMemo(
    () =>
      (dateString: string | null | undefined | Date | Dayjs): string => {
        if (!dateString) return '';
        // If it's already a Dayjs object, use it directly
        if (dayjs.isDayjs(dateString)) {
          return dateString.utc().format('YYYY-MM-DDTHH:mm:ss+00:00');
        }
        // Try parsing with datetimeFormat first (for datetime strings)
        // If that fails, try with dateFormat (for date-only strings)
        let parsed = dayjs(dateString, datetimeFormat, true);
        if (!parsed.isValid()) {
          parsed = dayjs(dateString, dateFormat, true);
        }
        // If still invalid, try auto-parsing as fallback
        if (!parsed.isValid()) {
          parsed = dayjs(dateString);
        }
        // Interpret the parsed date as being in user's timezone, then convert to UTC
        // The second param `true` keeps the local time values but sets the timezone
        return parsed
          .tz(timeZoneFormat, true)
          .utc()
          .format('YYYY-MM-DDTHH:mm:ss+00:00');
      },
    [dateFormat, datetimeFormat, timeZoneFormat],
  );

  const convertDateFormatToYYYYMMDD = useMemo(
    () =>
      (dateString: string | null | undefined | Date | Dayjs): string => {
        if (!dateString) return '';
        // If it's already a Dayjs object, use it directly
        if (dayjs.isDayjs(dateString)) {
          return dateString.format('YYYY-MM-DD');
        }
        // Try parsing with datetimeFormat first (for datetime strings)
        // If that fails, try with dateFormat (for date-only strings)
        let parsed = dayjs(dateString, dateFormat, true);
        if (!parsed.isValid()) {
          parsed = dayjs(dateString);
        }
        return parsed.format('YYYY-MM-DD');
      },
    [dateFormat, datetimeFormat, timeZoneFormat],
  );

  const convertDateFormatToUTCfollowUserTimeZone = useMemo(
    () =>
      (dateString: string | null | undefined | Date | Dayjs): string => {
        if (!dateString) return '';
        // If it's already a Dayjs object, use it directly
        if (dayjs.isDayjs(dateString)) {
          return dateString.utc().format('YYYY-MM-DDTHH:mm:ss+00:00');
        }
        // Try parsing with datetimeFormat first (for datetime strings)
        // If that fails, try with dateFormat (for date-only strings)
        let parsed = dayjs(dateString, datetimeFormat, true);
        if (!parsed.isValid()) {
          parsed = dayjs(dateString, dateFormat, true);
        }
        // If still invalid, try auto-parsing as fallback
        if (!parsed.isValid()) {
          parsed = dayjs(dateString);
        }
        // Interpret the parsed date as being in user's timezone, then convert to UTC
        // The second param `true` keeps the local time values but sets the timezone
        return parsed
          .tz(timeZoneFormat, true)
          .utc()
          .format('YYYY-MM-DDTHH:mm:ss+00:00');
      },
    [dateFormat, datetimeFormat, timeZoneFormat],
  );

  // Convert date to UTC start of day (Vietnam 00:00:00 → UTC)
  const convertDateToUTCStartOfDay = useMemo(
    () =>
      (dateString: string | null | undefined | Date | Dayjs): string => {
        if (!dateString) return '';
        // IMPORTANT: Build the day boundary in the API timezone directly.
        // This avoids implicit conversion from browser local timezone that can shift the calendar day.
        if (dayjs.isDayjs(dateString)) {
          return dateString
            .tz(apiTimeZone)
            .startOf('day')
            .utc()
            .format('YYYY-MM-DDTHH:mm:ss+00:00');
        }

        // Prefer date-only parsing first (most callers pass formatted date strings)
        const dateOnly = dayjs(dateString, dateFormat, true);
        if (dateOnly.isValid()) {
          return dayjs
            .tz(dateOnly.format(dateFormat), dateFormat, apiTimeZone)
            .startOf('day')
            .utc()
            .format('YYYY-MM-DDTHH:mm:ss+00:00');
        }

        // Fallback: parse as datetime, then interpret in apiTimeZone keeping local clock
        let parsed = dayjs(dateString, datetimeFormat, true);
        if (!parsed.isValid()) parsed = dayjs(dateString);
        return parsed
          .tz(apiTimeZone, true)
          .startOf('day')
          .utc()
          .format('YYYY-MM-DDTHH:mm:ss+00:00');
      },
    [apiTimeZone, dateFormat, datetimeFormat],
  );

  // Convert date to UTC end of day (Vietnam 23:59:59 → UTC)
  const convertDateToUTCEndOfDay = useMemo(
    () =>
      (dateString: string | null | undefined | Date | Dayjs): string => {
        if (!dateString) return '';
        // IMPORTANT: Build the day boundary in the API timezone directly.
        if (dayjs.isDayjs(dateString)) {
          return dateString
            .tz(apiTimeZone)
            .endOf('day')
            .utc()
            .format('YYYY-MM-DDTHH:mm:ss+00:00');
        }

        const dateOnly = dayjs(dateString, dateFormat, true);
        if (dateOnly.isValid()) {
          return dayjs
            .tz(dateOnly.format(dateFormat), dateFormat, apiTimeZone)
            .endOf('day')
            .utc()
            .format('YYYY-MM-DDTHH:mm:ss+00:00');
        }

        let parsed = dayjs(dateString, datetimeFormat, true);
        if (!parsed.isValid()) parsed = dayjs(dateString);
        return parsed
          .tz(apiTimeZone, true)
          .endOf('day')
          .utc()
          .format('YYYY-MM-DDTHH:mm:ss+00:00');
      },
    [apiTimeZone, dateFormat, datetimeFormat],
  );

  const converRawDateToDateTimeFormat = useMemo(
    () =>
      (dateString: string | null | undefined): string => {
        if (!dateString) return '-';
        return dayjs(dateString).tz(timeZoneFormat).format(datetimeFormat);
      },
    [datetimeFormat, timeZoneFormat],
  );

  const converRawDateToTimeFormat = useMemo(
    () =>
      (dateString: string | null | undefined): string => {
        if (!dateString) return '-';
        return dayjs(dateString).tz(timeZoneFormat).format(timeFormat);
      },
    [timeFormat, timeZoneFormat],
  );

  const converRawDateToDateFormat = useMemo(
    () =>
      (dateString: string | null | undefined): string => {
        if (!dateString) return '-';
        return dayjs(dateString).tz(timeZoneFormat).format(dateFormat);
      },
    [dateFormat, timeZoneFormat],
  );

  return {
    dateFormat,
    timeFormat,
    datetimeFormat,
    timeZoneFormat,
    convertDateFormatToUTC,
    convertDateToUTCStartOfDay,
    convertDateToUTCEndOfDay,
    converRawDateToDateTimeFormat,
    converRawDateToTimeFormat,
    converRawDateToDateFormat,
    convertDateFormatToUTCfollowUserTimeZone,
    convertDateFormatToYYYYMMDD,
  };
};
