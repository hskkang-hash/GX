import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import enTranslation from './locales/en.json';
import koTranslation from './locales/ko.json';
import thTranslation from './locales/th.json';

// Get the stored language from localStorage or use browser language
const getStoredLanguage = () => {
  const storedLanguage = localStorage.getItem('language');
  if (storedLanguage) return storedLanguage;

  const browserLanguage = navigator.language.split('-')[0];
  return ['en', 'ko', 'th'].includes(browserLanguage) ? browserLanguage : 'en';
};
i18n.use(initReactI18next).init({
  resources: {
    en: {
      translation: enTranslation,
    },
    ko: {
      translation: koTranslation,
    },
    th: {
      translation: thTranslation,
    },
  },
  lng: getStoredLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false, // React already safes from XSS
  },
});

export default i18n;
