export type ThemeType = 'light' | 'dark';

export interface ColorTheme {
  light: string;
  dark: string;
}

export interface OrderInfo {
  label: string;
  value: string;
}

export interface PackageItem {
  label: string;
  value: string;
}

export interface InvoicePackage {
  price: string;
  items: PackageItem[];
}
