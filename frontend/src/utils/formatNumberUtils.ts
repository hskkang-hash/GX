/**
 * Utility functions for formatting numbers based on system configuration
 */

export interface NumberFormatConfig {
    number_format?: string; // e.g., "1,234.56", "1 234,56", "1.234,56"
    decimal_places?: string | number; // e.g., "2" or 2
}

/**
 * Parse the number format pattern to extract separators
 * @param formatPattern - Format pattern like "1,234.56", "1 234,56", "1.234,56"
 * @returns Object with thousands separator and decimal separator
 */
export const parseNumberFormat = (
    formatPattern?: string
): {
    thousandsSeparator: string;
    decimalSeparator: string;
} => {
    if (!formatPattern) {
        // Default to US format
        return {
            thousandsSeparator: ',',
            decimalSeparator: '.',
        };
    }

    // Remove digits and spaces to find separators
    const separators = formatPattern.replace(/[\d\s]/g, '');

    // Find decimal separator (last non-digit character after a digit)
    const decimalMatch = formatPattern.match(/\d([^\d\s])\d/);
    let decimalSeparator = '.';
    let thousandsSeparator = ',';

    if (decimalMatch) {
        // Check if the separator appears multiple times (thousands) or once (decimal)
        const separator = decimalMatch[1];
        const count = (formatPattern.match(new RegExp(`\\${separator}`, 'g')) || []).length;

        if (count > 1) {
            // Multiple occurrences = thousands separator
            thousandsSeparator = separator;
            // Find decimal separator (should be different)
            const lastSeparator = formatPattern.match(/([^\d\s])[\d]+$/)?.[1];
            decimalSeparator = lastSeparator || '.';
        } else {
            // Single occurrence = could be decimal
            // Check position: if near the end, it's decimal; if in the middle, it's thousands
            const separatorIndex = formatPattern.indexOf(separator);
            const totalLength = formatPattern.length;
            const digitsAfter = formatPattern.substring(separatorIndex + 1).replace(/[^\d]/g, '').length;

            if (digitsAfter <= 3 && separatorIndex > totalLength - 5) {
                // Likely decimal separator
                decimalSeparator = separator;
                // Find thousands separator (space or different character)
                const thousandsMatch = formatPattern.match(/[\d]+([^\d\s.])[\d]{3}/);
                thousandsSeparator = thousandsMatch?.[1] || (formatPattern.includes(' ') ? ' ' : ',');
            } else {
                // Likely thousands separator
                thousandsSeparator = separator;
                decimalSeparator = '.';
            }
        }
    } else {
        // No decimal part, only thousands separator
        const spaceMatch = formatPattern.match(/\d\s\d/);
        if (spaceMatch) {
            thousandsSeparator = ' ';
        } else {
            const commaMatch = formatPattern.match(/\d,\d/);
            if (commaMatch) {
                thousandsSeparator = ',';
            } else {
                const dotMatch = formatPattern.match(/\d\.\d/);
                if (dotMatch) {
                    thousandsSeparator = '.';
                }
            }
        }
    }

    // Special handling for common patterns
    if (formatPattern.includes(',') && formatPattern.includes('.')) {
        // Check which comes last (decimal is usually last)
        const lastComma = formatPattern.lastIndexOf(',');
        const lastDot = formatPattern.lastIndexOf('.');
        if (lastDot > lastComma) {
            // "1,234.56" format
            thousandsSeparator = ',';
            decimalSeparator = '.';
        } else {
            // "1.234,56" format
            thousandsSeparator = '.';
            decimalSeparator = ',';
        }
    } else if (formatPattern.includes(' ') && formatPattern.includes(',')) {
        // "1 234,56" format
        thousandsSeparator = ' ';
        decimalSeparator = ',';
    } else if (formatPattern.includes(' ') && !formatPattern.includes(',')) {
        // "1 234.56" format
        thousandsSeparator = ' ';
        decimalSeparator = '.';
    }

    return {
        thousandsSeparator,
        decimalSeparator,
    };
};

/**
 * Format a number according to the system configuration
 * @param value - Number to format
 * @param config - Format configuration
 * @returns Formatted string
 */
export const formatNumber = (
    value: number | string | null | undefined,
    config?: NumberFormatConfig
): string => {
    if (value === null || value === undefined || value === '') {
        return '';
    }

    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) {
        return '';
    }

    const formatPattern = config?.number_format || '1,234.56';
    const decimalPlaces = parseInt(
        String(config?.decimal_places ?? '2'),
        10
    );

    const { thousandsSeparator, decimalSeparator } = parseNumberFormat(formatPattern);

    // Format the number
    const parts = numValue.toFixed(decimalPlaces).split('.');
    const integerPart = parts[0];
    const decimalPart = parts[1];

    // Add thousands separator
    let formattedInteger = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSeparator);

    // Handle negative numbers
    const isNegative = numValue < 0;
    if (isNegative) {
        formattedInteger = formattedInteger.replace('-', '');
    }

    // Combine parts
    let result = formattedInteger;
    if (decimalPlaces > 0 && decimalPart) {
        result = `${formattedInteger}${decimalSeparator}${decimalPart}`;
    } else if (decimalPlaces > 0 && !decimalPart) {
        result = `${formattedInteger}${decimalSeparator}${'0'.repeat(decimalPlaces)}`;
    }

    return isNegative ? `-${result}` : result;
};

/**
 * Parse a formatted number string back to a raw number
 * @param formattedValue - Formatted string like "1,234.56"
 * @param config - Format configuration
 * @returns Raw number or null if invalid
 */
export const parseFormattedNumber = (
    formattedValue: string,
    config?: NumberFormatConfig
): number | null => {
    if (!formattedValue || formattedValue.trim() === '') {
        return null;
    }

    const formatPattern = config?.number_format || '1,234.56';
    const { thousandsSeparator, decimalSeparator } = parseNumberFormat(formatPattern);

    // Remove thousands separators and replace decimal separator with dot
    let cleaned = formattedValue.trim();

    // Handle negative sign
    const isNegative = cleaned.startsWith('-');
    if (isNegative) {
        cleaned = cleaned.substring(1);
    }

    // Remove thousands separator
    if (thousandsSeparator) {
        cleaned = cleaned.replace(
            new RegExp(`\\${thousandsSeparator.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'g'),
            ''
        );
    }

    // Replace decimal separator with dot
    if (decimalSeparator && decimalSeparator !== '.') {
        cleaned = cleaned.replace(
            new RegExp(`\\${decimalSeparator.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'g'),
            '.'
        );
    }

    // Parse to number
    const parsed = parseFloat(cleaned);
    if (isNaN(parsed)) {
        return null;
    }

    return isNegative ? -parsed : parsed;
};

/**
 * Get decimal separator from config
 */
export const getDecimalSeparator = (config?: NumberFormatConfig): string => {
    const formatPattern = config?.number_format || '1,234.56';
    return parseNumberFormat(formatPattern).decimalSeparator;
};

/**
 * Get thousands separator from config
 */
export const getThousandsSeparator = (config?: NumberFormatConfig): string => {
    const formatPattern = config?.number_format || '1,234.56';
    return parseNumberFormat(formatPattern).thousandsSeparator;
};

