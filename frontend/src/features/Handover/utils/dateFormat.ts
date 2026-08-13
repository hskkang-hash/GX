import dayjs, { Dayjs } from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import timezone from 'dayjs/plugin/timezone';
import utc from 'dayjs/plugin/utc';

dayjs.extend(customParseFormat);
dayjs.extend(utc);
dayjs.extend(timezone);

/**
 * Converts date format code to dayjs format string
 * Supports formats like 'DD Month YYYY' and 'Month DD, YYYY'
 */
export const getDayjsFormat = (dateFormatCode: string): string => {
  switch (dateFormatCode) {
    case 'DD Month YYYY':
      return 'DD MMMM YYYY';
    case 'Month DD, YYYY':
      return 'MMMM DD, YYYY';
    case 'YYYY-MM-DD':
      return 'YYYY-MM-DD';
    case 'DD/MM/YYYY':
      return 'DD/MM/YYYY';
    case 'MM/DD/YYYY':
      return 'MM/DD/YYYY';
    case 'DD-MM-YYYY':
      return 'DD-MM-YYYY';
    case 'YYYY/MM/DD':
      return 'YYYY/MM/DD';
    case 'YY/MM/DD':
      return 'YY/MM/DD';
    default:
      return dateFormatCode;
  }
};

/**
 * Helper function to parse date with fallback
 * Tries strict parsing first, then lenient parsing
 */
export const parseDate = (
  dateString: string,
  format: string,
  locale: string,
): Dayjs | null => {
  if (!dateString) return null;

  // Ensure dateString is actually a string
  const dateStr =
    typeof dateString === 'string' ? dateString : String(dateString);
  if (!dateStr) return null;

  // If input is an ISO date string (contains 'T' or ends with 'Z'), parse it directly
  // This prevents issues with YY format misinterpreting the year
  if (dateStr.includes('T') || dateStr.endsWith('Z')) {
    const parsed = dayjs(dateStr).locale(locale);
    if (parsed.isValid()) {
      return parsed;
    }
  }

  // Special handling for YY/MM/DD format
  // Parse "25/11/20" as YY/MM/DD -> 2025/11/20
  if (format === 'YY/MM/DD') {
    const parts = dateStr.split('/');
    if (parts.length === 3) {
      const [yy, mm, dd] = parts;
      const yearNum = parseInt(yy, 10);

      // Convert 2-digit year to 4-digit year
      // dayjs default: 00-68 -> 2000-2068, 69-99 -> 1969-1999
      // But we want to ensure correct parsing: 25 -> 2025
      const fullYear = yearNum <= 68 ? 2000 + yearNum : 1900 + yearNum;
      const yyyyString = `${fullYear}/${mm}/${dd}`;

      // Parse with YYYY/MM/DD format to ensure correct year
      const parsed = dayjs(yyyyString, 'YYYY/MM/DD', true).locale(locale);
      if (parsed.isValid()) {
        return parsed;
      }
    }
  }

  // Try strict parsing first
  let parsed = dayjs(dateStr, format, true).locale(locale);
  if (parsed.isValid()) {
    return parsed;
  }

  // Try lenient parsing as fallback
  parsed = dayjs(dateStr, format, false).locale(locale);
  if (parsed.isValid()) {
    return parsed;
  }

  // If format parsing failed, try auto-detection as last resort
  parsed = dayjs(dateStr).locale(locale);
  if (parsed.isValid()) {
    return parsed;
  }

  // Log for debugging if still invalid
  console.warn(`Failed to parse date: "${dateStr}" with format: "${format}"`);

  return null;
};

/**
 * Convert date to user's timezone
 * @param date - Date to convert
 * @param timezoneCode - Timezone code (e.g., 'Asia/Bangkok', 'America/New_York')
 * @returns Dayjs object in the specified timezone, or UTC if no timezone provided
 */
export const convertToTimezone = (
  date: Dayjs | string | null | undefined,
  timezoneCode: string | null,
): Dayjs | null => {
  if (!date) return null;

  let dayjsDate: Dayjs | null = null;
  const isUTCString =
    typeof date === 'string' && (date.endsWith('Z') || date.includes('T'));

  if (typeof date === 'string') {
    // If it's a UTC string, parse as UTC
    if (isUTCString) {
      dayjsDate = dayjs.utc(date);
    } else {
      dayjsDate = dayjs(date);
    }
  } else {
    dayjsDate = date;
  }

  if (!dayjsDate || !dayjsDate.isValid()) return null;

  // If timezone code is provided, convert to that timezone
  if (timezoneCode) {
    // If date is in UTC (ends with Z or is ISO string), convert from UTC to timezone
    if (isUTCString) {
      return dayjsDate.utc().tz(timezoneCode);
    }
    // Otherwise, assume the date is already in the target timezone or local timezone
    // Convert to UTC first, then to target timezone
    return dayjsDate.tz(timezoneCode);
  }

  // If no timezone code provided, keep as UTC if it was originally UTC
  // Otherwise return as is (local time)
  if (isUTCString) {
    return dayjsDate.utc();
  }

  return dayjsDate;
};

/**
 * Format date string using dayjs with timezone support
 */
export const formatDate = (
  date: Dayjs | string | null | undefined,
  format: string,
  locale: string,
  timezoneCode?: string | null,
): string => {
  if (!date) return '';

  let dayjsDate: Dayjs | null = null;

  if (typeof date === 'string') {
    // Check if it's a UTC string (ISO format)
    const isUTCString = date.endsWith('Z') || date.includes('T');

    // If it's UTC string and no timezone code, parse as UTC
    if (isUTCString && !timezoneCode) {
      const utcParsed = dayjs.utc(date).locale(locale);
      if (utcParsed.isValid()) {
        dayjsDate = utcParsed;
      }
    }

    // Try to parse with the output format first (input might be in same format)
    if (!dayjsDate) {
      let parsed = dayjs(date, format, true).locale(locale);
      if (parsed.isValid()) {
        dayjsDate = parsed;
      } else {
        // Try common date formats as fallback
        const commonFormats = [
          'DD/MM/YYYY',
          'MM/DD/YYYY',
          'YYYY/MM/DD',
          'YY/MM/DD',
          'DD-MM-YYYY',
          'MM-DD-YYYY',
          'YYYY-MM-DD',
        ];
        let found = false;

        for (const commonFormat of commonFormats) {
          parsed = dayjs(date, commonFormat, true).locale(locale);
          if (parsed.isValid()) {
            dayjsDate = parsed;
            found = true;
            break;
          }
        }

        // If date-only formats failed, try date + time formats
        // This handles cases like "20/11/2025 20:47" when using formatDate
        if (!found) {
          const commonTimeFormats = [
            'HH:mm',
            'HH:mm:ss',
            'hh:mm A',
            'hh:mm:ss A',
          ];
          for (const commonDateFormat of commonFormats) {
            for (const timeFormat of commonTimeFormats) {
              const combinedFormat = `${commonDateFormat} ${timeFormat}`;
              parsed = dayjs(date, combinedFormat, true).locale(locale);
              if (parsed.isValid()) {
                // Reset time to 00:00:00 to ensure only date part is used
                dayjsDate = parsed.startOf('day');
                found = true;
                break;
              }
            }
            if (found) break;
          }
        }

        // If all format parsing failed, try auto-detection as last resort
        if (!found) {
          const autoParsed =
            isUTCString && !timezoneCode
              ? dayjs.utc(date).locale(locale)
              : dayjs(date).locale(locale);
          if (autoParsed.isValid()) {
            // Reset time to 00:00:00 to ensure only date part is used
            dayjsDate = autoParsed.startOf('day');
          }
        }
      }
    }
  } else {
    dayjsDate = date;
  }

  if (!dayjsDate || !dayjsDate.isValid()) return '';

  // Convert to timezone if provided, otherwise keep UTC if it was originally UTC
  dayjsDate = convertToTimezone(dayjsDate, timezoneCode || null);
  if (!dayjsDate) return '';

  return dayjsDate.format(format);
};

/**
 * Get time format from time_format__format_string or default
 * Converts strftime format (%H, %I, %M, %S, %p) to dayjs format (HH, hh, mm, ss, A)
 */
export const getDayjsTimeFormat = (timeFormatString?: string): string => {
  if (!timeFormatString) {
    return 'HH:mm';
  }

  // If it's already a dayjs format string (contains HH, hh, mm, ss, A), return as is
  if (
    timeFormatString.includes('HH') ||
    (timeFormatString.includes('hh') && !timeFormatString.includes('%h')) ||
    (timeFormatString.includes('mm') && !timeFormatString.includes('%m')) ||
    (timeFormatString.includes('ss') && !timeFormatString.includes('%s')) ||
    (timeFormatString.includes(' A') && !timeFormatString.includes('%p'))
  ) {
    return timeFormatString;
  }

  // Convert strftime format to dayjs format
  // %H -> HH (24h format)
  // %I -> hh (12h format)
  // %M -> mm (minutes)
  // %S -> ss (seconds)
  // %p -> A (AM/PM)
  const dayjsFormat = timeFormatString
    .replace(/%H/g, 'HH')
    .replace(/%I/g, 'hh')
    .replace(/%M/g, 'mm')
    .replace(/%S/g, 'ss')
    .replace(/%p/g, 'A');

  // If conversion didn't change anything, try common format codes
  if (dayjsFormat === timeFormatString) {
    switch (timeFormatString) {
      case '24':
        return 'HH:mm';
      case '12':
        return 'hh:mm A';
      case '24_full':
        return 'HH:mm:ss';
      case '12_full':
        return 'hh:mm:ss A';
      default:
        return timeFormatString;
    }
  }

  return dayjsFormat;
};

/**
 * Format datetime (date + time) using dayjs with timezone support
 */
export const formatDateTime = (
  date: Dayjs | string | null | undefined,
  dateFormat: string,
  timeFormat: string,
  locale?: string,
  timezoneCode?: string | null,
): string => {
  if (!date) return '';

  let dayjsDate: Dayjs | null = null;

  if (typeof date === 'string') {
    const dateLocale = locale || 'en';
    // Check if it's a UTC string (ISO format)
    const isUTCString = date.endsWith('Z') || date.includes('T');

    // If it's UTC string and no timezone code, parse as UTC
    if (isUTCString && !timezoneCode) {
      const utcParsed = dayjs.utc(date).locale(dateLocale);
      if (utcParsed.isValid()) {
        dayjsDate = utcParsed;
      }
    }

    // Try to parse with the combined date + time format first
    if (!dayjsDate) {
      const combinedFormat = `${dateFormat} ${timeFormat}`;
      let parsed = dayjs(date, combinedFormat, true).locale(dateLocale);
      if (parsed.isValid()) {
        dayjsDate = parsed;
      } else {
        // Try common date formats combined with time format as fallback
        const commonDateFormats = [
          'DD/MM/YYYY',
          'MM/DD/YYYY',
          'YYYY/MM/DD',
          'YY/MM/DD',
          'DD-MM-YYYY',
          'MM-DD-YYYY',
          'YYYY-MM-DD',
        ];
        let found = false;

        for (const commonDateFormat of commonDateFormats) {
          const combined = `${commonDateFormat} ${timeFormat}`;
          parsed = dayjs(date, combined, true).locale(dateLocale);
          if (parsed.isValid()) {
            dayjsDate = parsed;
            found = true;
            break;
          }
        }

        // If format parsing failed, try auto-detection as last resort
        if (!found) {
          dayjsDate =
            isUTCString && !timezoneCode
              ? dayjs.utc(date).locale(dateLocale)
              : dayjs(date).locale(dateLocale);
        }
      }
    }
  } else {
    dayjsDate = date;
  }

  if (!dayjsDate || !dayjsDate.isValid()) return '';

  // Convert to timezone if provided, otherwise keep UTC if it was originally UTC
  dayjsDate = convertToTimezone(dayjsDate, timezoneCode || null);
  if (!dayjsDate) return '';

  const formattedDate = dayjsDate.format(dateFormat);
  const formattedTime = dayjsDate.format(timeFormat);

  return `${formattedDate} ${formattedTime}`;
};
