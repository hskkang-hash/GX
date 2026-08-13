// import { createNumberMask } from 'text-mask-addons';

export const ROLE_PERMISION = {
  CREATE: 'permit_c',
  VIEW: 'permit_r',
  UPDATE: 'permit_u',
  DELETE: 'permit_d',
};

export const ACTION_TYPE_BTN = {
  CREATE: 'CREATE',
  UPDATE: 'UPDATE',
  DELETE: 'DELETE',
  VIEW: 'VIEW',
};

export const TIME_HELPER = {
  TODAY: 'Today',
  LAST_15_MIN: 'Last 15 minutes',
  LAST_30_MIN: 'Last 30 minutes',
  LAST_HOUR: 'Last hour',
  LAST_60_MIN: 'Last 60 minutes',
  LAST_4_HOUR: 'Last 4 hours',
  LAST_12_HOUR: 'Last 12 hours',
  LAST_24_HOUR: 'Last 24 hours',
  LAST_3_DAY: 'Last 3 days',
  LAST_7_DAY: 'Last 7 days',
  LAST_30_DAY: 'Last 30 days',
};

export const PARRENT_PATH = {
  ResetPwd: '/accounts/reset-password',
  Register: '/register',
  CompanyTerms: '/company-terms',
  RegisterSuccess: '/register-success',
  User: '/user',
  ChangePwd: '/accounts/password',
  Profile: '/accounts/profile',
  SysQueryManage: '/system-query-management',
  ConfigManagement: '/config-management',
  RoleManagement: '/role-management',
  MenuManagement: '/menu-management',
  SplunkQueryList: '/splunk-query-list',
  AddSysQuery: '/add/sysquery',
  SplunkQuery: '/splunk-query',
  RuleManagement: '/rule',
  AddNewRule: '/add-rule',
  RunSearch: '/run-search',
  ExceptionList: '/exception-list',
  ExceptionRule: '/exception-detection-rule',
  RuleReview: '/rule-review',
  Threat: '/threat',
  Report: '/report',
  Dashboard: '/dashboard/',
  Asset: '/asset',
  Handover: '/handover',
  TicketProcessingManagement: '/ticket-processing-management',
  TicketManagement: '/ticket-management',
  IncidentManagement: '/incident-management',
  TimetableWorkSchedule: '/timetable-work-schedule',
  TestModal: '/test-modal',
  ForumCategory: '/forum-categories',
  SecurityNewsConfig: '/security-news-config',
  SecurityNews: '/security-news',
  KISAAnnouncement: '/kisa-announcement',
  FocusedDetectionRule: '/focused-detection-rule',
  ThreatInformation: '/threat-information',
  AutoTicketConfiguration: '/auto-ticket-configuration',
  MailTemplateManagement: '/mail-template-management',
  TicketFormatConfig: '/ticket-format-config',
  Accounts: '/accounts',
  ForumList: '/forum/list',
  LookupManagement: '/lookup-management',
  Docfile: '/docfile',
  IPBlockingManagement: '/ip-blocking-management',
  LogManagement: '/log-management',
  AlarmManagement: '/alarm-management',
  RiskScoreManagement: '/risk-score-management',
  TicketTag: '/ticket-tag',
  DiagnosisManagement: '/diagnosis-result-management',
  ResponseManagement: '/response-management',
  TicketManagementSOP: '/sop-ticket-management',
  IncidentManagementSOP: '/sop-incident-management',
};

// Map configuration
export const MAP_CONFIG = {
  PROVIDER:
    (import.meta.env.VITE_MAP_PROVIDER as 'kakao' | 'google') || 'google',
  // W0-0: 하드코딩 폴백 제거 — 키는 환경변수에서만 온다
  GOOGLE_MAPS_API_KEY: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
  KAKAO_MAPS_API_KEY: import.meta.env.VITE_KAKAO_MAPS_API_KEY || '',
} as const;

// Geocoding configuration for address search
export const GEOCODING_CONFIG = {
  PROVIDER: MAP_CONFIG.PROVIDER, // Use same provider as maps
  COUNTRY: (import.meta.env.VITE_MAP_COUNTRY as string) || 'KR', // Default to Korea
  LANGUAGE: (import.meta.env.VITE_MAP_LANGUAGE as string) || 'ko', // Default to Korean
  GOOGLE_PLACES_API_KEY: MAP_CONFIG.GOOGLE_MAPS_API_KEY,
  KAKAO_MAPS_API_KEY: MAP_CONFIG.KAKAO_MAPS_API_KEY,
} as const;

export const MASK_PIPE = {
  IP_PIPE: (value) => {
    if (value === '.' || value.endsWith('..')) return false;

    const parts = value.split('.');

    if (
      parts.length > 4 ||
      parts.some((part) => part === '00' || part < 0 || part > 255)
    ) {
      return false;
    }

    return value;
  },
  CIDR_PIPE: (value) => {
    if (value.endsWith('..') || value === '/' || value.endsWith('//'))
      return false;

    const [ipPart, subnetPart] = value.split('/');

    // Validate IP part
    const ipChunks = ipPart.split('.');
    if (
      ipChunks.length > 4 ||
      ipChunks.some((chunk) => chunk === '00' || chunk < 0 || chunk > 255)
    ) {
      return false;
    }

    // Validate subnet mask part (if present)
    if (subnetPart !== undefined) {
      const subnet = parseInt(subnetPart, 10);
      if (isNaN(subnet) || subnet < 0 || subnet > 32) {
        return false;
      }
    }

    return value;
  },
  URL_PIPE: (value) => {
    // Ensure the value starts with http:// or https://
    if (!value.startsWith('http://') && !value.startsWith('https://')) {
      return false;
    }

    // Extract the domain part
    const afterScheme = value.replace(/^https?:\/\//, '');
    const domainParts = afterScheme.split(/[\/?#]/)[0]; // Extract domain only (up to '/' or '?' or '#')

    // Validate the domain part (basic validation for alphanumeric, dots, hyphens)
    const domainPattern = /^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!domainPattern.test(domainParts)) {
      return false;
    }

    // If there is a port, validate it
    const portMatch = afterScheme.match(/:\d+/);
    if (portMatch) {
      const port = parseInt(portMatch[0].slice(1), 10);
      if (isNaN(port) || port < 1 || port > 65535) {
        return false;
      }
    }

    // Everything looks good; return the value
    return value;
  },

  PORT_PIPE: (value) => {
    if (value === '.' || value.endsWith('..')) return false;
    return value;
  },
};
