export const formatLocalKoreanNumber = (input: string): string => {
  const cleaned = input.replace(/\D/g, '');

  if (cleaned.startsWith('2')) {
    // Seoul: 02
    if (cleaned.length <= 2) return cleaned;
    if (cleaned.length <= 5) return `02-${cleaned.slice(2)}`;
    if (cleaned.length <= 9)
      return `02-${cleaned.slice(2, 5)}-${cleaned.slice(5)}`;
    return `02-${cleaned.slice(2, 6)}-${cleaned.slice(6, 10)}`;
  } else {
    // Others
    if (cleaned.length <= 3) return cleaned;
    if (cleaned.length <= 7)
      return `${cleaned.slice(0, 3)}-${cleaned.slice(3)}`;
    return `${cleaned.slice(0, 3)}-${cleaned.slice(3, 7)}-${cleaned.slice(7, 11)}`;
  }
};
