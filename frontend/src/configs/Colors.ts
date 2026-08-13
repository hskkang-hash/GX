import { ThemeType } from '@/features/delivery/DeliveryOperation/types';

export const cardBg: Record<ThemeType, string> = {
  light: '#FFFFFF',
  dark: '#1F1F20',
};
export const infoBg: Record<ThemeType, string> = {
  light: '#F6F7F8',
  dark: '#2D2E30',
};
export const border: Record<ThemeType, string> = {
  light: '#E5E7EB',
  dark: '#404040',
};
export const textLabel: Record<ThemeType, string> = {
  light: '#2D2E30',
  dark: '#ECECEF',
};
export const textValue: Record<ThemeType, string> = {
  light: '#111827',
  dark: '#F3F4F6',
};
export const statusBg: Record<ThemeType, string> = {
  light: '#FEF3C7',
  dark: '#92400E',
};
export const statusText: Record<ThemeType, string> = {
  light: '#92400E',
  dark: '#FEF3C7',
};

export const axisColor: Record<ThemeType, string> = {
  light: '#dedfe3',
  dark: '#444645',
};

const Colors = {
  Primary: '#1D9BE2',
  PrimaryDark: '#1EA1EB',
  Secondary: '#1F1F20', //dark
  SubSecondary: '#1F2A80', //dark blue
  PrimaryText: '#2D2E30',

  Success: '#0CBA47',
  Error: '#EE533D',
  Warning: '#EB7509',
  Danger: '#EE533D',

  Green: '#0CBA47',
  Yellow: '#F0C418',
  Cyan: '#24A5F4',
  Blue: '#0D6DE7',
  Purple: '#8918E2',
  Magenta: '#EA0F6D',
  Red: '#ff4d4f',
  Orange: '#EB7509',
  White: '#ffffff',
  Black: '#1F1F20',

  Gray1: '#F6F7F8',
  Gray2: '#F2F2F2',
  Gray3: '#ECECEF',
  Gray4: '#DDDFE2',
  Gray5: '#9C9D9D',
  Gray6: '#444646',
  Gray7: '#2D2E30',
  Gray8: '#787A7B',
};

export const colorOpacity = (hex: string, opacity: number) => {
  const tempHex = hex.replace('#', '');
  const r = parseInt(tempHex.substring(0, 2), 16);
  const g = parseInt(tempHex.substring(2, 4), 16);
  const b = parseInt(tempHex.substring(4, 6), 16);

  return `rgba(${r},${g},${b},${opacity})`;
};

export default Colors;
