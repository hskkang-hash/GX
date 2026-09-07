import { createApiClient } from 'rj-core';

import {
  announceSessionEnded,
  isSessionEvicted,
  sessionEndedAnnounced,
} from '@/features/session/sessionEnded';
import {
  isPermissionDenied,
  announcePermissionDenied,
} from '@/features/session/permissionDenied';

export const CustomRoutes = {
  qrCode: '/qr-code',

  /**
   * DSM 재난안전 모니터링 화면 셋 (D-371 ①).
   * 상세는 `:id` 를 받는다 — 목록에서 골라 넘기지 않고 **서버에 다시 묻는다**
   * (문지기가 목록에만 서고 상세에 안 서는 모양을 만들지 않기 위해서다).
   */
  dsm: {
    title: 'Disaster Monitoring',
    dashboard: { title: '관제 대시보드', path: '/dsm/dashboard' },
    events: { title: '이벤트 목록', path: '/dsm/events' },
    eventDetail: { title: '이벤트 상세', path: '/dsm/events/:id' },
  },

  device: {
    title: 'Device',
    path: '/device',
    subRoutes: {
      addNewDevice: {
        title: 'Add New Device',
        path: '/device/add-new-device',
      },
      detailDevice: {
        title: 'Detail Device',
        path: '/device/detail-device/:id',
      },
      editDevice: {
        title: 'Edit Device',
        path: '/device/edit-device/:id',
      },
    },
  },

  deliveryInquiry: {
    title: 'Delivery Inquiry',
    path: '/delivery-inquiry',
    subRoutes: {
      addNewDeliveryInquiry: {
        title: 'Add New Order',
        path: '/delivery-inquiry/add-new-order',
      },
      reOrder: {
        title: 'ReOrder',
        path: '/delivery-inquiry/re-order/:id',
      },
      detailDeliveryInquiry: {
        title: 'Detail Delivery Inquiry',
        path: '/delivery-inquiry/:id',
      },
    },
  },
  deliveryOperation: {
    title: 'Delivery Operation',
    path: '/delivery-operation',
    subRoutes: {
      addNewDeliveryInquiry: {
        title: 'Add New Order',
        path: '/delivery-operation/add-new-order',
      },
      orderDetail: {
        title: 'Order Detail',
        path: '/delivery-operation/order-detail/:id',
      },
      unverifiedOrder: {
        title: 'Order Detail',
        path: '/delivery-operation/unverified-orders/order-detail/:id',
      },
      verifiedOrder: {
        title: 'Order Detail',
        path: '/delivery-operation/verified-orders/order-detail/:id',
      },
      arrivedOrder: {
        title: 'Order Detail',
        path: '/delivery-operation/arrived-orders/order-detail/:id',
      },
      completedOrder: {
        title: 'Order Detail',
        path: '/delivery-operation/completed-orders/order-detail/:id',
      },
      cancelledOrder: {
        title: 'Order Detail',
        path: '/delivery-operation/cancelled-orders/order-detail/:id',
      },
    },
  },

  deliveryReport: {
    title: 'Delivery Report',
    path: '/delivery-report',
    subRoutes: {
      completedOrderDetail: {
        title: 'Completed Order Detail',
        path: '/delivery-report/completed-order-detail/:id',
      },
    },
  },

  surveyProfile: {
    title: 'Survey Profile',
    path: '/survey-profile',
    subRoutes: {
      addNewSurveyProfile: {
        title: 'Add New Profile',
        path: '/survey-profile/add-new-survey-profile',
      },
      orderDetail: {
        title: 'Survey Profile Detail',
        path: '/survey-profile/survey-profile-detail/:id',
      },
      unverifiedOrder: {
        title: 'Survey Profile Detail',
        path: '/survey-profile/unverified-orders/order-detail/:id',
      },
      arrivedOrder: {
        title: 'Survey Profile Detail',
        path: '/survey-profile/arrived-orders/order-detail/:id',
      },
      detailSurveyProfile: {
        title: 'Survey Profile Detail',
        path: '/survey-profile/survey-profile-detail/:id',
      },
      surveillanceGCS: {
        title: 'Surveillance GCS',
        path: '/survey-profile/surveillance-gcs',
      },
    },
  },

  operationalData: {
    title: 'Operational Data',
    path: '/operational-data',
    subRoutes: {
      detailOperationalData: {
        title: 'Detail Operational Data',
        path: '/operational-data/detail-operational-data/:id',
      },
    },
  },

  packaging: {
    title: 'Packaging',
    path: '/packaging',
    subRoutes: {
      addNewPackaging: {
        title: 'Add New Packaging',
        path: '/packaging/add-new-packaging',
      },
      detailPackaging: {
        title: 'Detail Packaging',
        path: '/packaging/detail-packaging/:id',
      },
      editPackaging: {
        title: 'Edit Packaging',
        path: '/packaging/edit-packaging/:id',
      },
    },
  },
  terminals: {
    title: 'Terminals',
    path: '/terminals',
    subRoutes: {
      addNewTerminals: {
        title: 'Add New Terminals',
        path: '/terminals/add-new-terminals',
      },
      editTerminals: {
        title: 'Edit Terminals',
        path: '/terminals/edit-terminals/:id',
      },
    },
  },

  routes: {
    title: 'Routes',
    path: '/routes',
    subRoutes: {
      addNewRoute: {
        title: 'Add New Route',
        path: '/routes/add-new-route',
      },
      detailRoute: {
        title: 'Detail Route',
        path: '/routes/detail-route/:id',
      },
      editRoute: {
        title: 'Edit Route',
        path: '/routes/edit-route/:id',
      },
    },
  },

  /* Mockup UI */
  intergratedDashboard: {
    title: 'Intergrated Dashboard',
    path: '/intergrated-dashboard',
  },

  monitoringDashboard: {
    title: 'Monitoring Dashboard',
    path: '/monitoring-dashboard',
  },

  deliveryDashboard: {
    title: 'Delivery Dashboard',
    path: '/delivery-dashboard',
  },
  deliveryDashboardAnYang: {
    title: 'Delivery Dashboard AnYang',
    path: '/delivery-dashboard-anyang',
  },

  surveillanceDashboard: {
    title: 'Surveillance Dashboard',
    path: '/surveillance-dashboard',
  },

  disabillityDashboard: {
    title: 'Disabillity Dashboard',
    path: '/disabillity-dashboard',
  },

  otherEquipments: {
    title: 'Other Equipments',
    path: '/other-equipments',
    subRoutes: {
      addNewOtherEquipment: {
        title: 'Add New Equipment',
        path: '/other-equipments/add-new-equipment',
      },
      detailEquipment: {
        title: 'Detail Equipment',
        path: '/other-equipments/edit-equipment/:id',
      },
    },
  },

  partnerManagement: {
    title: 'Partner Management',
    path: '/partner',
    subRoutes: {
      addNewPartner: {
        title: 'Add New Partner',
        path: '/partner/add-new-partner',
      },
      editPartner: {
        title: 'Edit Partner',
        path: '/partner/edit-partner/:id',
      },
    },
  },

  operationSettings: {
    title: 'Operation Settings',
    path: '/operation-settings',
  },

  waybillTemplate: {
    title: 'Waybill Template',
    path: '/waybill-template',
    subRoutes: {
      addNewWaybillTemplate: {
        title: 'Add New Waybill Template',
        path: '/waybill-template/add-new-waybill-template',
      },
      editWaybillTemplate: {
        title: 'Edit Waybill Template',
        path: '/waybill-template/edit-waybill-template/:id',
      },
    },
  },

  trackOrder: {
    title: 'Etri Tracking',
    path: '/etri-tracking',
    subRoutes: {
      detailTrackOrder: {
        title: 'Detail Etri Tracking',
        path: '/etri-tracking/:id/:operation_id',
      },
    },
  },

  library: {
    title: 'Device Template',
    path: '/library',
    subRoutes: {
      addNewLibrary: {
        title: 'Add New Template',
        path: '/library/add-new-library',
      },
      editLibrary: {
        title: 'Edit Template',
        path: '/library/edit-library/:id',
      },
      // detailLibrary: {
      //   title: "Detail Library",
      //   path: "/library/detail-library/:id",
      // },
    },
  },

  etriOrder: {
    title: 'Etri Order',
    path: '/etri-order',
    subRoutes: {
      addNewEtriOrder: {
        title: 'Add New Etri Order',
        path: '/etri-order/add-new-etri-order',
      },
    },
  },

  infrastructure: {
    title: 'Infrastructure',
    path: '/infrastructure',
    subRoutes: {
      detailInfrastructure: {
        title: 'Detail Infrastructure',
        path: '/infrastructure/detail-infrastructure/:id',
      },
      register: {
        title: 'Add New Infrastructure',
        path: '/infrastructure/register',
      },
    },
  },

  dockingStation: {
    title: 'Docking Stations',
    path: '/docking-stations',
    subRoutes: {
      detailDockingStation: {
        title: 'Detail Docking Station',
        path: '/docking-stations/detail-docking-station/:id',
      },
      register: {
        title: 'Add New Docking Station',
        path: '/docking-stations/register',
      },
    },
  },

  deliveryHubs: {
    title: 'Delivery Hubs',
    path: '/delivery-hubs',
    subRoutes: {
      registerDeliveryHubs: {
        title: 'Register Delivery Hub',
        path: '/delivery-hubs/register-delivery-hub',
      },
      detailDeliveryHubs: {
        title: 'Detail Delivery Hub',
        path: '/delivery-hubs/detail-delivery-hub/:id',
      },
      editDeliveryHubs: {
        title: 'Edit Delivery Hub',
        path: '/delivery-hubs/edit-delivery-hub/:id',
      },
    },
  },

  reportTemplate: {
    title: 'Report Template',
    path: '/report-template',
    subRoutes: {
      addNewReportTemplate: {
        title: 'Add New Report Template',
        path: '/report-template/add-new-report-template',
      },
      editReportTemplate: {
        title: 'Edit Report Template',
        path: '/report-template/edit-report-template/:id',
      },
    },
  },

  operationalNotice: {
    title: 'Operational Notice',
    path: '/operational-notice',
    subRoutes: {
      addNewOperationalNotice: {
        title: 'Add New Operational Notice',
        path: '/operational-notice/add-new-operational-notice',
      },
      editOperationalNotice: {
        title: 'Edit Operational Notice',
        path: '/operational-notice/edit-operational-notice/:id',
      },
    },
  },

  orderStatus: {
    title: 'Order Status',
    path: '/order-status',
  },

  mappingStatus: {
    title: 'Mapping Status',
    path: '/mapping-status',
  },

  multiStreamMonitor: {
    title: 'Multi Stream Monitor',
    path: '/multi-stream-monitor',
  },

  checklistSetting: {
    title: 'Checklist Setting',
    path: '/checklist-setting',
  },

  flightLogAnalysis: {
    title: 'Flight Log Analysis',
    path: '/flight-log-analysis',
  },

  surveyMission: {
    title: 'Survey Mission',
    path: '/survey-mission',
    subRoutes: {
      addNewSurveyMission: {
        title: 'Add New Survey Mission',
        path: '/survey-mission/add-new-survey-mission',
      },
      detailSurveyMission: {
        title: 'Detail Survey Mission',
        path: '/survey-mission/detail-survey-mission/:id',
      },
      editSurveyMission: {
        title: 'Edit Survey Mission',
        path: '/survey-mission/edit-survey-mission/:id',
      },
    },
  },

  dataAnalysis: {
    title: 'Data Analysis',
    path: '/data-analysis',
    subRoutes: {
      detailDataAnalysis: {
        title: 'Detail Data Analysis',
        path: '/data-analysis/detail-data-analysis/:id',
      },
    },
  },

  handover: {
    title: 'Handover',
    path: '/handover',
    subRoutes: {
      detailHandover: {
        title: 'Detail Handover',
        path: '/handover/detail-handover/:id',
      },
      createShiftLogHandover: {
        title: 'Create Shift Log Handover',
        path: '/handover/create-shift-log-handover/:id',
      },
      handoverDutyDetail: {
        title: 'Handover Duty Detail',
        path: '/handover/handover-duty-detail',
      },
      addNoticeManagement: {
        title: 'Add Notice Management',
        path: '/handover/add-notice-management',
      },
    },
  },

  mediaData: {
    title: 'Media Data',
    path: '/media-data',
    subRoutes: {
      videoAnalysis: {
        title: 'AI Video Data Analysis',
        path: '/media-data/video-analysis/:id',
      },
    },
  },

  gcsFlight: {
    title: 'GCS Flight',
    path: '/gcs-mavlink',
  },

  noTam: {
    title: 'NoTam',
    path: '/notam',
  },

  setupDemo: {
    title: 'Setup Demo File',
    path: '/setup-demo-file',
  },

  setupDemoUrl: {
    title: 'Setup Demo URL',
    path: '/setup-demo-url',
  },

  djiUrl: {
    title: 'DJI URL',
    path: '/dji-url',
  },

  aimProxy: {
    title: 'AIP Proxy',
    path: '/aim',
  },
};

export const endpoint = {
  // Media Data
  mediaData: '/api/media-data',
  previewFile: '/api/media-data/preview',
  downloadMediaDataFile: '/api/media-data/download',
  detectFileType: '/api/media-data/detect',

  // Handover Management
  handoverManagement: '/api/handover/handover/management',
  handoverShift: '/api/handover/handover/shift',
  noticeManagement: '/api/handover/handover/notice',
  detailNoticeManagement: `/api/handover/handover/notice/by-id-notice`,
  noticeProcess: '/api/handover/handover/notice/notice-process',
  noticeRestore: '/api/handover/handover/notice/notice-restore',
  getListNoticeHandover: '/api/handover/handover/content/by-id-management',
  completedNotice: '/api/handover/completed-notice',
  createNoticeHandover: '/api/handover/handover/content',
  handoverDutyDetail: '/api/handover/handover/content/handover-duty-detail',
  comments: '/api/handover/handover/notice-comment',
  downloadHandover: '/api/handover/handover/management/download-management',
  downloadNotice: '/api/handover/handover/notice/download-notice',
  downloadCompletedNotice:
    '/api/handover/handover/notice/download-completed-notice',

  // Day of Week
  dayOfWeek: '/api/terminals/days-of-week',

  // Data Analysis
  dataAnalysis: '/api/surveillance/video-analysis',
  detailDataAnalysis: (video_analysis_id: number) =>
    `/api/surveillance/video-analysis/${video_analysis_id}`,
  downloadVideoAnalysis: (video_analysis_id: number) =>
    `/api/surveillance/video-analysis/${video_analysis_id}/download-detail`,

  // Surveillance Profile
  surveyOperator: '/api/v1/user/list',
  changeDroneOptions: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/change-drone/options`,
  changeDroneProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/change-drone`,
  listAvalableDrones:
    '/api/surveillance/surveillance-profiles/available-devices/',
  addSurveillanceProfile: '/api/surveillance/surveillance-profiles',
  listSurveillanceProfile: '/api/surveillance/surveillance-profiles',
  detailSurveillanceProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}`,
  approveSurveillanceProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/approve`,
  rejectSurveillanceProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/reject`,
  cancelSurveillanceProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/cancel-profile`,
  profilesTimeline: `/api/surveillance/surveillance-profiles/timeline`,
  stopRepeatProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/stop-repeat`,
  cancelProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/cancel-profile`,
  downloadLogProfile: (profile_drone_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_drone_id}/download-log`,
  downloadAnalysisProfile: (profile_drone_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_drone_id}/download-analysis`,
  downloadAnalysisProfileForProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/download-analysis-for-profile`,
  checkCompleteProfile: (profile_id: number) =>
    `/api/surveillance/surveillance-profiles/${profile_id}/check-complete`,
  listOptionsProfile: `/api/surveillance/surveillance-profiles/list-selected-profiles`,

  // Confirm Drone
  confirmDrone: `/api/delivery/processing/assign-packages-to-drone`,

  // Partner
  deletePartner: (ids: string) => `/api/partner/api/partners/delete/${ids}`,
  partner: '/api/partner/api/partners/',
  updatePartner: (id: number) => `/api/partner/api/partners/${id}/api-key`,
  refreshTokenPartner: (id: number) =>
    `/api/partner/api/partners/refresh-token/${id}`,
  copyTokenPartner: (id: number) =>
    `/api/partner/api/partners/${id}/copy-api-key`,

  // Device
  deviceManagement: '/api/devices/devices-management',
  activeDeactiveDevice: (ids: string) =>
    `/api/devices/devices-management/${ids}/change-status`,
  detailDevice: (id: number, edit: boolean) =>
    `/api/devices/devices-management/${id}?edit=${edit}&depth=2`,
  getDrones: `/api/dronehw/drone-communication-management/online-drones`,
  changeStatusDrone: (id: number) =>
    `/api/devices/devices-management/${id}/active`,
  deleteDevices: (ids: string) =>
    `/api/devices/devices-management/delete/${ids}`,

  // Config Management
  genGroupConfig: `/api/user-groups/gen-schema`,

  // Packaging
  packagingSpecifications: `/api/devices/packaging-specifications`,
  activeDeactivePackaging: (ids: string) =>
    `/api/devices/packaging-specifications/${ids}/change-status`,
  detailPackaging: (id: number, edit: boolean) =>
    `/api/devices/packaging-specifications/${id}?edit=${edit}&depth=2`,

  // Other Equipments
  otherEquipments: `/api/devices/cameras`,
  detailEquipment: (id: number, edit: boolean) =>
    `/api/devices/cameras/${id}?edit=${edit}&depth=2`,
  changeStatusEquipment: (ids: string) =>
    `/api/devices/cameras/${ids}/change-status`,

  portalData: `/api/devices/protocols`,

  getMenuHtml: `/api/source/get-html`,
  getMenuUrl: `/api/source/get-url`,

  // data for selectInput
  getDataForSelectInput: `/api/advanced-table/select-data`,

  // Terminals
  terminals: '/api/terminals/terminals',
  terminalsOperatingTime: (id: number) =>
    `/api/terminals/terminals/${id}/operating-times`,
  terminalsForOrder: `/api/orders/pickup-locations`,
  changeStatusTerminal: (ids: string) =>
    `/api/terminals/terminal-types/${ids}/change-status`,

  //Group
  groups: '/api/user-groups/',
  // proxy endpoints (frontend)
  proxyHtml: '/api/proxy/proxyhtml', // returns proxied HTML
  proxyFile: '/api/proxy/proxy', // streams file (pdf, image, css...)
  proxyDiag: '/api/proxy/proxydiag', // optional diagnostic endpoint

  // Hubs
  hubs: '/api/terminals/delivery-hubs',
  hubsForOrder: `/api/orders/pickup-locations`,
  changeStatusHubs: (ids: string) =>
    `/api/terminals/terminal-types/${ids}/change-status`,

  // Delivery Option
  deliveryOption: '/api/orders/delivery-option/',

  // Order
  deliveryInquiryOrder: '/api/orders/order/',
  detailOrder: (id: number) => `/api/orders/order/${id}`,
  cancelOrder: (id: number) => `/api/orders/order/${id}/cancel-order`,
  toggleOrderWeather: '/api/orders/order/settings/allow-order-in-bad-weather',

  //Bank
  bank: '/api/orders/banks/',
  refundCash: (id: number) => `/api/orders/order/${id}/refund`,

  // Item Type
  itemType: '/api/orders/item-types/',

  //Package List
  packageList: '/api/orders/package/package-list',

  // Routes
  routes: '/api/terminals/routes',
  changeStatusRoute: (ids: string) =>
    `/api/terminals/routes/${ids}/change-status`,
  deleteRoute: (ids: string) => `/api/terminals/routes/delete/${ids}`,

  // Waybill Template
  waybillTemplate: '/api/print-format/print-formats/print-formats',
  actionWaybillTemplate: '/api/print-format/print-formats',

  getFieldsTemplate:
    '/api/print-format/print-formats/print-formats/fields/model',

  // Delivery Operation
  operationOrder: '/api/delivery/delivery/operations',
  deliveryReport: '/api/delivery/delivery-report/operations',
  // Verification
  unVerifiedOrder: '/api/delivery/verification/unverified-operations',
  verifiedOrder: '/api/delivery/verification/verified-operations',
  previewWaybill: (operation_id: number, waybill_template: number) =>
    `/api/print-format/print-formats/print-formats/${waybill_template}/preview?instance_id=${operation_id}&model_name=orders.order`,
  printWaybill: (operation_id: number, waybill_template: number) =>
    `/api/delivery/verification/print-waybill/${operation_id}/${waybill_template}`,
  verifyOders: '/api/delivery/verification/verify-orders',
  cancelOperationOrder: (operation_id: number) =>
    `/api/delivery/verification/cancel-order/${operation_id}`,

  //Processing
  packageProcessingStatus: (operation_item_id: number) =>
    `/api/delivery/processing/operation-items/${operation_item_id}`,
  processing: (operation_id: number, route_id: number) =>
    `/api/delivery/processing/update-route/${operation_id}/${route_id}`,
  confirmPackage: (package_id: number) =>
    `/api/delivery/order-confirmation/${package_id}`,
  dronesByPackageId: (operation_item_id: number) =>
    `/api/delivery/processing/select-drone-operations-items/${operation_item_id}`,
  dronesByPackageAndRoute: (operation_item_id: number, route_id: number) =>
    `/api/delivery/processing/select-drone-operations-items/${operation_item_id}/${route_id}`,

  assignPackageToDrone: '/api/delivery/processing/assign-packages-to-drones',
  changeDrone: '/api/delivery/processing/change-drone',
  cancelAwaitingOrder: '/api/delivery/processing/cancel-awaiting-order',
  cancelFlight: '/api/delivery/processing/cancel-flight',
  approveFlight: '/api/delivery/processing/approve-flight',
  uploadRoute: '/api/delivery/processing/upload-mission-to-gcs',

  // Transit
  transit: '/api/delivery/processing/in-transit-operations',
  droneStatus: '/api/delivery/drone-monitoring/drone-status',
  routeSelect: '/api/delivery/processing/routes',
  droneSelect: (operation_id: number) =>
    `/api/delivery/processing/select-drone-operations/${operation_id}`,

  // Completed
  arrivedOrder: '/api/delivery/completed/arrived-operations',
  completedOrder: '/api/delivery/completed/completed-operations',
  actionCompletedOrder: '/api/delivery/completed/complete-orders',

  // Returned
  actionPendingOrder: '/api/delivery/returned/execute-pending-timeout',
  actionReturnedOrder: '/api/delivery/returned/execute-returned',
  actionProcessedOrder: '/api/delivery/returned/execute-processed',

  // Cancelled
  cancelledOrder: '/api/delivery/cancelled/cancelled-operations',

  // Library
  library: '/api/devices/libraries-management',
  libraryDetail: (id: number) => `/api/devices/libraries-management/${id}`,
  deleteLibrary: (ids: string) =>
    `/api/devices/libraries-management/libraries/${ids}`,

  // Etri Order
  etriOrderTerminal: '/api/orders/pickup-locations/etri-terminals',

  // Etri Tracking
  etriTracking: '/api/delivery/delivery/get-delivery-for-etri',
  sendToEtri: (id: number) =>
    `/api/delivery/etri-integration/send-to-etri/${id}`,

  // Operation Settings
  operationSettings: '/api/operation-settings/operation-settings/',
  operationSettingById: (id: number) =>
    `/api/operation-settings/operation-settings/${id}`,
  getSupportedApis: '/api/operation-settings/operation-settings/supported-apis',

  // Operational Data
  operationalData: '/api/operational-data/operational-data',
  detailOperationalData: (id: number) =>
    `/api/operational-data/operational-data/${id}`,
  uploadFileDrone: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/upload-operational-log-drone`,
  uploadFileRobot: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/upload-operational-log-robot`,
  uploadVideoDrone: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/upload-operational-video-drone`,
  uploadVideoRobot: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/upload-operational-video-robot`,
  downloadFileDrone: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/download-operational-log-drone`,
  downloadFileRobot: (delivery_operation_item_id: number) =>
    `/api/operational-data/operational-data/${delivery_operation_item_id}/download-operational-log-robot`,
  downloadFileOperationalDataAll: `/api/operational-data/operational-data/download-operational-data`,

  checkTaskSocket: (task_id: string) =>
    `/api/task-status/task-status/${task_id}`,

  checkTaskOperationalData: (task_id: string) =>
    `/api/operational-data/operational-data/upload-status/${task_id}`,

  // Get Order Status
  getOrderStatus: '/api/orders/order/map-status',

  // Dashboard
  getDashboardData: '/api/dashboard/dashboard/',
  refreshDashboardData: '/api/dashboard/dashboard/refresh',

  // Dashboard Anyang
  getDashboardDataAngYang: '/api/dashboard/dashboard/anyang',
  refreshDashboardDataAngYang: '/api/dashboard/dashboard/anyang',
  saveWeatherData: '/api/dashboard/dashboard/weather-setting',
  deviceLocation: '/api/dashboard/dashboard/devices-location',
  checkDroneHealth: (drone_id: number) =>
    `/api/dashboard/dashboard/check-health/${drone_id}`,

  // Infrastructure
  infrastructure: '/api/terminals/infrastructures',
  detailInfrastructure: (id: number) => `/api/terminals/infrastructures/${id}`,
  changeStatusInfrastructure: (ids: string) =>
    `/api/terminals/terminal-types/${ids}/change-status`,

  // Docking Station
  dockingStation: '/api/terminals/docking-stations',
  detailDockingStation: (id: number) => `/api/terminals/docking-stations/${id}`,
  changeStatusDockingStation: (ids: string) =>
    `/api/terminals/terminal-types/${ids}/change-status`,

  // Report Template
  reportTemplate: '/api/report-template/',
  deleteReportTemplate: (ids: string) => `/api/report-template/delete/${ids}`,

  // Operational Notice
  operationalNotice: '/api/operational-data/operational-notice',
  operationalNoticeDetail: (id: number) =>
    `/api/operational-data/operational-notice/${id}`,
  deleteOperationalNotice: (ids: string) =>
    `/api/operational-data/operational-notice/delete/${ids}`,
  changeStatusOperationalNotice: (id: number) =>
    `/api/operational-data/operational-notice/change-status/${id}`,

  // Multi-streaming
  streamingList: '/api/stream-monitors/stream-monitors',
  aiModels: '/api/stream-monitors/stream-monitors/ai-models',
  captureVideo: '/api/stream-monitors/stream-monitors/capture',
  startRecording: '/api/stream-monitors/stream-monitors/start-record',
  stopRecording: '/api/stream-monitors/stream-monitors/stop-record',
  pauseRecording: '/api/stream-monitors/stream-monitors/pause-record',
  resumeRecording: '/api/stream-monitors/stream-monitors/resume-record',
  deleteExternalStream: (id: number) =>
    `/api/stream-monitors/stream-monitors/external-stream-monitors/${id}`,
  updateExternalStream:
    '/api/stream-monitors/stream-monitors/external-stream-monitors',

  //function
  functionTypes: '/api/terminals/functions/function-types',
  // Checklist Setting
  checklistSetting: '/api/checklist-setting/',
  toggleChecklistSetting: (id: number) =>
    `/api/checklist-setting/${id}/activate`,
  deactivateChecklistSetting: (id: number) =>
    `/api/checklist-setting/${id}/deactivate`,
  deleteChecklistSetting: (ids: string) =>
    `/api/checklist-setting/delete/${ids}`,

  // Setting Category
  settingCategory: '/api/checklist-setting/categories/',

  // Order Status
  orderStatus: '/api/orders/external-order-statuses',
  deleteOrderStatus: (ids: string) =>
    `/api/orders/external-order-statuses/external-order-statuses/${ids}`,

  // Mapping Status
  mappingStatus: '/api/orders/order-status-mappings',
  updateMappingStatus: (id: number) =>
    `/api/orders/order-status-mappings/update/${id}`,
  deleteMappingStatus: (ids: string) =>
    `/api/orders/order-status-mappings/delete/${ids}`,

  // Change Order Status
  changeOrderStatus: (id: number) => `/api/orders/order/${id}/change-status`,

  // download report
  downloadReport: (id: number) =>
    `/api/delivery/delivery-report/download-report/${id}`,

  // Active Device
  activeDevice: (ids: string) =>
    `/api/devices/devices-management/${ids}/activate`,

  // Deactive Device
  deactiveDevice: (ids: string) =>
    `/api/devices/devices-management/${ids}/deactivate`,

  // Active Terminal
  activeTerminal: (ids: string) => `/api/terminals/terminals/${ids}/activate`,

  // Deactive Terminal
  deactiveTerminal: (ids: string) =>
    `/api/terminals/terminals/${ids}/deactivate`,

  // Active Infrastructure
  activeInfrastructure: (ids: string) =>
    `/api/terminals/infrastructures/${ids}/activate`,
  // Deactive Infrastructure
  deactiveInfrastructure: (ids: string) =>
    `/api/terminals/infrastructures/${ids}/deactivate`,

  // Active Docking Station
  activeDockingStation: (ids: string) =>
    `/api/terminals/docking-stations/${ids}/activate`,
  // Deactive Docking Station
  deactiveDockingStation: (ids: string) =>
    `/api/terminals/docking-stations/${ids}/deactivate`,

  // Active Delivery Hub
  activeDeliveryHub: (ids: string) =>
    `/api/terminals/delivery-hubs/${ids}/activate`,
  // Deactive Delivery Hub
  deactiveDeliveryHub: (ids: string) =>
    `/api/terminals/delivery-hubs/${ids}/deactivate`,

  // Active Equipment
  activeEquipment: (ids: string) => `/api/devices/cameras/${ids}/activate`,

  // Deactive Equipment
  deactiveEquipment: (ids: string) => `/api/devices/cameras/${ids}/deactivate`,

  // Active Route
  activeRoute: (ids: string) => `/api/terminals/routes/${ids}/activate`,

  // Deactive Route
  deactiveRoute: (ids: string) => `/api/terminals/routes/${ids}/deactivate`,

  // Active Packaging
  activePackaging: (ids: string) =>
    `/api/devices/packaging-specifications/${ids}/activate`,

  // Deactive Packaging
  deactivePackaging: (ids: string) =>
    `/api/devices/packaging-specifications/${ids}/deactivate`,

  // etri order
  etriOrder: '/api/orders/order/etri-order',
  detailEtriOrder: (id: number) =>
    `/api/orders/order/etri-order-detail?id=${id}`,

  // mavlink
  commands: '/api/terminals/qground-control/mavlink-commands',
  frames: '/api/terminals/qground-control/mavlink-frames',

  // Import Route
  importRoute: '/api/terminals/qground-control/import-plan',
  importRoutes: '/api/terminals/qground-control/import-plans',
  exportRoute: '/api/terminals/qground-control/export-plan',

  // Flight Log Analysis
  flightLogAnalysis: '/api/flight-log/flight-log/',
  detailFlightLogAnalysis: (id: number) =>
    `/api/flight-log/flight-log/detail/${id}`,
  downloadFlightLogAnalysis: (id: number) =>
    `/api/flight-log/flight-log/download-log/${id}`,
  deleteFlightLogAnalysis: (ids: string) =>
    `/api/flight-log/flight-log/delete/${ids}`,

  // Survey Mission
  surveyMission: '/api/surveillance/survey-missions',
  detailSurveyMission: (id: number) =>
    `/api/surveillance/survey-missions/${id}`,
  approveSurveyMission: (id: number) =>
    `/api/surveillance/survey-missions/${id}/approve`,
  rejectSurveyMission: (id: number) =>
    `/api/surveillance/survey-missions/${id}/reject`,
  activateSurveyMission: (ids: string) =>
    `/api/surveillance/survey-missions/activate/${ids}`,
  deactivateSurveyMission: (ids: string) =>
    `/api/surveillance/survey-missions/deactivate/${ids}`,
  reviewSurveyMission: `/api/surveillance/survey-missions/mission/review-mission`,
  checkPermissionActionSurveyMission: `/api/surveillance/survey-missions/mission/check_permission`,
  importSurveyMission: `/api/surveillance/survey-missions/mission/import-routes-simple`,
  deleteSurveyMission: (ids: string) =>
    `/api/surveillance/survey-missions/mission/${ids}`,

  // Surveillance Profile
  surveillanceProfiles: '/api/surveillance/surveillance-profiles',
  completedSurveillanceProfiles:
    '/api/surveillance/surveillance-profiles/list-completed-profiles',
  cancelledSurveillanceProfiles:
    '/api/surveillance/surveillance-profiles/list-rejected-profiles',

  createExternalStream:
    '/api/stream-monitors/stream-monitors/external-stream-monitors',

  // Surveillance Dashboard
  surveillanceDashboardDroneStatus:
    '/api/surveillance/surveillance-dashboard/drone-status-overview',
  surveillanceDashboardDailyProfile:
    '/api/surveillance/surveillance-dashboard/daily-profile-overview',
  surveillanceDashboardAbnormalSigns:
    '/api/surveillance/surveillance-dashboard/abnormal-signs-overview',
  surveillanceDashboardAbnormalSignsMessages:
    '/api/surveillance/surveillance-dashboard/abnormal-signs-messages',
  surveillanceDashboardTodayProfilesPolygon:
    '/api/surveillance/surveillance-dashboard/today-profiles-polygon',
  surveillanceDashboardLocationWeather:
    '/api/surveillance/surveillance-dashboard/weather-setting',
  surveillanceDashboardTodayRegionDrones:
    '/api/surveillance/surveillance-dashboard/today-region-drones',
};

/* eslint-disable @typescript-eslint/no-explicit-any */
const apiClient = createApiClient({
  baseURL: import.meta.env.VITE_API_URL,
  /**
   * ★ [P-62 꼬리 · 2026-09-05 턴 F · 차선 S] **말없이 튕기지 않는다.**
   *
   * 이 제품은 동시 접속이 1개다 — 휴대전화에서 로그인하면 이 화면이 그 자리에서
   * 죽는다. 종전에는 그 401 을 보자마자 `/login` 으로 튕겼고, 사람이 보는 것은
   * 「하던 일이 사라지고 로그인 화면이 떠 있다」뿐이었다. **왜인지는 아무데도 없었다.**
   *
   * 서버는 이미 말하고 있다(`common/session_limit.py` · 턴 E):
   *     401 { detail: "다른 기기에서 로그인되었습니다", reason_code: "session_evicted" }
   * 아래 인터셉터가 그 표식을 보면 안내 한 줄을 띄우고(`SessionEndedNotice`),
   * 튕기는 것은 **사람이 「다시 로그인」을 누를 때**로 미룬다.
   *
   * ⚠ 그 밖의 401 은 **종전 그대로 튕긴다.** 넓게 잡으면 비밀번호를 틀린 사람이
   *   있지도 않은 다른 기기를 찾는다.
   */
  redirectOn401: () => {
    if (sessionEndedAnnounced()) return;
    window.location.href = '/login';
  },
}) as any;
const { API } = apiClient;

/**
 * ★ 밀려남을 **여기서** 읽는다 — `redirectOn401` 은 응답 본문을 못 본다.
 *
 * ⚠ **순서가 곧 판정이다.** [실측 2026-09-05 · `node_modules/rj-core/dist/rj-core.es.js`]
 *   rj-core 는 제 응답 인터셉터를 먼저 달아 두었고, 401 을 보면 이렇게 한다:
 *
 *       401 → 토큰 재발급 시도 → **실패** → `Promise.reject(재발급 오류)` → `redirectOn401()`
 *
 *   즉 그 뒤에 붙은 인터셉터가 받는 것은 **재발급 오류**이지 원래의 401 이 아니다 —
 *   본문(`reason_code`)이 거기 없다. `use()` 로 뒤에 붙이면 이 절은 **아무것도 못 본다.**
 *   그래서 axios 의 처리기 배열 **맨 앞**에 넣는다(axios 1.13.5 · `interceptors.response
 *   .handlers`). 우리는 **보기만 하고 오류를 그대로 다시 던진다** — rj-core 의 재발급
 *   갈래는 한 자도 안 바뀐다.
 *
 * ⚠ 배열 모양은 axios 의 내부다. 그래서 **확인하고** 넣고, 안 되면 `use()` 로 떨어지며,
 *   그마저 안 되면 아무 일도 하지 않는다 — 그때 동작은 종전과 **똑같다**(말없이 튕긴다).
 *   없는 배선을 있는 척하지 않는다.
 */
const noteEvictionOn401 = {
  fulfilled: (response: any) => response,
  rejected: (error: any) => {
    const status = error?.response?.status;
    const body = error?.response?.data;
    if (status === 401 && isSessionEvicted(body)) {
      announceSessionEnded(body);
    }
    // ★ [P-88 · 2026-09-07 턴 J] **승격은 반쪽이면 더 나쁘다.**
    //   이 턴에 `GET /api/devices/devices-management` 의 권한 거절을 200 봉투에서
    //   진짜 403 으로 승격했다(전/후 실측 200 → 403). 승격만 하고 앞단이 조용하면
    //   빈 표가 **빈 표 + 멈춘 스피너**가 된다 — 그건 나아진 것이 아니다.
    //   여기서는 **알리기만 하고 오류를 그대로 다시 던진다** — 401 갈래와 같은 규율이다.
    if (isPermissionDenied(status)) {
      announcePermissionDenied(body, error?.config?.url ?? '');
    }
    return Promise.reject(error);
  },
  synchronous: false,
  runWhen: null,
};

try {
  const handlers = API?.interceptors?.response?.handlers;
  if (Array.isArray(handlers)) {
    handlers.unshift(noteEvictionOn401);
  } else {
    API?.interceptors?.response?.use?.(
      noteEvictionOn401.fulfilled,
      noteEvictionOn401.rejected,
    );
  }
} catch {
  // 인터셉터를 못 붙였다. 안내 한 줄이 제품을 세우지 않는다 — 종전 동작으로 돈다.
}

export default API;
