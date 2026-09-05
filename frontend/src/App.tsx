import dayjs from 'dayjs';
import 'dayjs/locale/th';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import { createElement, lazy } from 'react';
import type { ComponentType } from 'react';
import {
  createBrowserRouter,
  Navigate,
  Outlet,
  RouterProvider,
  useNavigate,
} from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import {
  AddMenu,
  AddUser,
  AuthProvider,
  BackgroundLogin,
  ChangePasswordPage,
  ConfigManagement,
  ConfigSystemProvider,
  CustomRouters,
  CustomSidebar,
  EditConfig,
  ForgotPasswordPage,
  GlobalLoading,
  initialServices,
  LoadingProvider,
  LoginPage,
  MenuManagement,
  NewPasswordPage,
  PrivateRouter,
  ProfilePage,
  PublicRouter,
  RegisterPage,
  RoleManagement,
  UserManagement,
  useUserInfo,
} from 'rj-core';

/**
 * ★ [UX-21 · 2026-09-26 · 차선 C] **로고 자산의 이름에서 공백을 뺐다.**
 *
 *   [실측 2026-09-25 · 화면 24장] 전 화면에서 로고가 깨져 `alt` 텍스트(「logo」)만
 *   떠 있었다(결함 #2). 앞판이 가리키던 파일 이름에는 **공백**이 있었고
 *   (`Full Version-Black.png`), 번들은 그것을 `assets/Full%20Version-Black-….png`
 *   로 냈다 [실측 — `backend/_fe_dist/assets/index-*.js` 에 그대로 있다].
 *   그 `%20` 은 정적 파일을 내주는 쪽(개발 서버·nginx·WhiteNoise)마다 다르게 풀리고,
 *   한 곳에서만 안 풀려도 화면에는 **깨진 그림 한 장**이 뜬다. 그 그림은
 *   「로고가 없다」와 구별되지 않는다.
 *
 *   ⚠ **원본 파일을 지우지 않았다** — 삭제는 대표 승인 사항이다. 공백 없는 이름의
 *     사본을 더하고 여기서 그것을 가리킨다. 인수 코드가 옛 이름을 쓰고 있어도 안 깨진다.
 *   ⚠ 이 한 줄이 로고를 살렸는지는 **다시 찍어 봐야 안다**(재촬영은 턴 D). 공백은
 *     원인의 후보이지 확인된 원인이 아니다 — [추정]이라고 적는다.
 */
import logoExpandedLightModeDefault from './assets/images/logo-full-black.png';
import logoExpandedDarkModeDefault from './assets/images/logo-full-white.png';
import logoLightModeDefault from './assets/images/logo-short-black.png';
import logoDarkModeDefault from './assets/images/logo-short-white.png';
import backgroundImageDefault from './assets/images/backgroundLogin.png';
import { FileManagement } from './components/FileManagement/FileManagement';
import { FormNavigationBlocker } from './components/FormNavigationBlocker';
import GlobalNotifications from './components/GlobalNotifications';
import PartnerCallbackNotificationPopup from './components/notifications/PartnerCallbackNotificationPopup';
import { FormDirtyProvider } from './contexts/FormDirtyContext';
import { MobileProvider, useMobileContext } from './contexts/MobileContext';
import DeliveryDashboardAnYang from './features/Dashboard/DeliveryDashboard/DeliveryDashboardAnYang';
import DeliveryDashboard from './features/Dashboard/DeliveryDashboard/indexV2';
import SurveillanceDashboard from './features/Dashboard/SurveillanceDashboard';
import DataAnalysisPage from './features/DataAnalysis';
import { DetailDataAnalysisPage } from './features/DataAnalysis/pages/DetailDataAnalysisPage';
import {
  DeliveryHubs,
  DetailDeliveryHubs,
  EditDeliveryHubs,
  RegisterDeliveryHubs,
} from './features/DeliveryHubs';
import FlightLogAnalysis from './features/FlightLogAnalysis';
import HandoverPage from './features/Handover';
import { CreateHandoverPage } from './features/Handover/pages/tabs/HandoverManagement/CreateHandoverPage';
import { HandoverDutyDetail } from './features/Handover/pages/tabs/HandoverManagement/HandoverDutyDetail';
import { AddNoticeManagement } from './features/Handover/pages/tabs/NoticeManagement/AddNoticeManagement';
import LibraryDroneList from './features/LibraryDrone';
import FormAddNewLibrary from './features/LibraryDrone/add/FormAddNewLibrary';
import EditLibraryForm from './features/LibraryDrone/edit/EditLibraryForm';
import LoginMobile from './features/LoginMobile';
import ForgotPasswordMobile from './features/LoginMobile/ForgotPasswordMobile';
import NewPasswordMobile from './features/LoginMobile/NewPasswordMobile';
import MediaDataPage from './features/MediaData';
import { MediaDataVideoAnalysisPage } from './features/MediaData/pages/MediaDataVideoAnalysisPage';
import MultiStreamMonitor from './features/MultiStreamMonitor';
import NoTam from './features/NoTamPage';
import ScanQRMobile from './features/ScanQRMobile/ScanQRMobile';
import SurveyMissionPage from './features/SurveyMission';
import { AddSurveyMissionPage } from './features/SurveyMission/pages/AddSurveyMissionPage';
import { DetailSurveyMissionPage } from './features/SurveyMission/pages/DetailSurveyMissionPage';
import { EditSurveyMissionPage } from './features/SurveyMission/pages/EditSurveyMissionPage';
import AimProxyPage from './features/aimProxy/AimProxyPage';
import CheckListSetting from './features/checklistSetting';
import DeliveryOperation from './features/delivery/DeliveryOperation';
import FormAddNewOrder from './features/delivery/DeliveryOperation/MainTabs/VerificationTab/AddNewOrder/AddNewOrder';
import OrderDetail from './features/delivery/DeliveryOperation/OrderDetail';
import DeliveryReport from './features/delivery/DeliveryReport';
import DeliveryReportOrderDetail from './features/delivery/DeliveryReport/components/OrderDetail';
import FormAddNewOrderDeliveryInquiry from './features/delivery/deliveryInquiry/AddNewOrder/AddNewOrder';
import DetailOrder from './features/delivery/deliveryInquiry/detailOrder/DetailOrder';
import ListDeliveryInquiry from './features/delivery/deliveryInquiry/listDeliveryInquiry/ListDeliveryInquiry';
import DockingStation from './features/dockingStation';
import DetailDockingStation from './features/dockingStation/Detail';
import RegisterDockingStation from './features/dockingStation/RegisterDockingStation';
import ReceivingSystem from './features/entriOder';
import AddNewEtriOrder from './features/entriOder/AddNewOrder';
import Infrastruture from './features/infrastructure';
import DetailInfrastructure from './features/infrastructure/Detail';
import RegisterInfrastructure from './features/infrastructure/RegisterInfrastructure';
import MappingStatus from './features/mappingStatus';
// 모바일 · 이동 중 수신 모드 경로 (U3 · 차선 D) — 경로는 이 파일 한 곳에서 정한다.
import { mobileRoutes } from './features/mobile/routes';
import OperationSetting from './features/operationSetting';
import DetailOperationalData from './features/operationalData/detailOperationalData/DetailOperationalData';
import ListOperationalData from './features/operationalData/listOperationalData/ListOperationalData';
import AddOperationalNotice from './features/operationalNotice/pages/AddOperationalNotice';
import EditOperationalNotice from './features/operationalNotice/pages/EditOperationalNotice';
import OperationalNotice from './features/operationalNotice/pages/OperationalNotice';
import OrderStatus from './features/orderStatus';
import OtherEquipments from './features/otherEquipments';
import AddNewEquipment from './features/otherEquipments/AddNewEquipment';
import DetailEquipment from './features/otherEquipments/DetailEquipment';
import ListPartner from './features/partnerManagement/listPartner/ListPartner';
import {
  AddReportTemplate,
  EditReportTemplate,
  ReportTemplate,
} from './features/reportTemplate';
import AddNewRoute from './features/routes/AddNewRoute/AddNewRoute';
import DetailRoute from './features/routes/detailRoute/DetailRoute';
import EditRoute from './features/routes/editRoute/EditRoute';
import ListRoute from './features/routes/listRoute/ListRoute';
import DJIPage from './features/setupData/DJIPage';
import GCSPage from './features/setupData/GCSPage';
import SurveillanceGCSPage from './features/setupData/SurveillanceGCSPage';
import SurveillanceProfile from './features/surveillanceProfile';
import { ProfileDetailPage } from './features/surveillanceProfile/MainTabs/CompletedTab/components/ProfileDetailPage';
import AddNewOrderSurveillanceProfile from './features/surveillanceProfile/MainTabs/ProcessingTab/AddNewProfile/AddNewProfile';
import AddNewTerminals from './features/terminals/addNewTerminals/AddNewTerminals';
import EditTerminals from './features/terminals/editTerminals/EditTerminals';
import ListTerminals from './features/terminals/listTerminals/ListTerminals';
import DetailEtriOrder from './features/trackOrder/detailEtriOrder/DetailEtriOrder';
import ListEtriOrder from './features/trackOrder/listEntriOrder/ListEtriOrder';
import WaybillTemplate from './features/waybillTemplate';
import AddNewTemplate from './features/waybillTemplate/AddNewTemplate';
import EditTemplate from './features/waybillTemplate/EditTemplate';
import './index.css';
import { CustomRoutes } from './services/API';
import { dsm2Routes } from './features/dsm/routes';
import { ClearStoreOnRouteChange } from './utils/ClearStoreOnRouteChange';

dayjs.extend(customParseFormat);

const FormAddNewDevice = lazy(
  () => import('./features/device/formAddNewDevice/FormAddNewDevice'),
);
const ListDevice = lazy(
  () => import('./features/device/listDevice/ListDevice'),
);
const ConfigDataWrap = lazy(
  () => import('./features/setupData/ConfigDataWrap'),
);
const DetailDevice = lazy(
  () => import('./features/device/detailDevice/DetailDevice'),
);
const EditDeviceForm = lazy(
  () => import('./features/device/editDevice/EditDeviceForm'),
);

/**
 * DSM(재난안전 모니터링) 화면 셋 — D-371 ① · E2E-1 전 구간을 덮는다.
 *
 * 탐지 → **목록 → 상세 → 알림 확인**. 셋을 한 벌로 두는 이유는 그 셋이
 * 한 시나리오이기 때문이고, 그래서 화면이 서면 E2E 캡처도 함께 선다(D-347).
 *
 * ★ 새 앱을 만들지 않는다 — 기존 관제 화면 위에 얹는다(D-370 additive).
 *   그래서 `PrivateLayout` + `Sidebar` 아래에 그대로 들어간다.
 */
const DsmControlDashboard = lazy(
  () => import('./features/dsm/pages/ControlDashboard'),
);
const DsmEventList = lazy(() => import('./features/dsm/pages/EventList'));
const DsmEventDetail = lazy(() => import('./features/dsm/pages/EventDetail'));
/**
 * 2파 DSM 화면 셋 (차선 C · 2026-09-24) — UX-13 · UX-17 · UX-18.
 *
 * ★ 경로는 `features/dsm/routes.ts` 한 곳에서 정한다. `CustomRoutes` 에 넣지 않은
 *   이유는 그 파일이 이번 파에 네 차선이 같이 쓰는 공용 자리라서다 — 충돌하면
 *   그 충돌은 **라우팅 침묵**으로 나타난다(화면이 안 뜨는데 오류도 안 난다).
 */
const DsmFocusQueue = lazy(() => import('./features/dsm/pages/FocusQueue'));
const DsmDrillMode = lazy(() => import('./features/dsm/pages/DrillMode'));
const DsmCameraImport = lazy(() => import('./features/dsm/pages/CameraImport'));
/**
 * 모바일 — 이동 중 수신 모드 (U3 · 차선 D).
 *
 * ★ 경로는 `features/mobile/routes.ts` 한 곳에서 정한다. `CustomRoutes` 에 넣지
 *   않은 이유는 그 파일이 이번 턴 공용 자리라서다 — 충돌하면 조각으로 보고한다.
 * ★ **무계정 링크 금지**(불변 제약): 모바일은 링크로 들어오지만 이 둘은 다른 화면과
 *   똑같이 `PrivateLayout` 아래에 선다. 토큰이 없으면 `/login` 으로 튕긴다.
 */
const MobileInbox = lazy(() => import('./features/mobile/pages/MobileInbox'));
const MobileEventDetail = lazy(
  () => import('./features/mobile/pages/MobileEventDetail'),
);
/**
 * W0-4 — 데모·목업 화면 격리
 *
 * `__DEMO_ENABLED__` 는 vite.config.ts 의 define 이 빌드 시점에 `true`/`false`
 * 리터럴로 치환한다(환경변수 `VITE_ENABLE_DEMO`). 프로덕션 빌드에서는 `false` 로
 * 접히므로 아래 배열 전체가 dead code 로 제거된다 —
 * **라우트가 등록되지 않고, mockupDemoUi·setup-demo 청크도 생성되지 않는다.**
 *
 * 데모를 켜려면: `VITE_ENABLE_DEMO=true npm run build` (또는 dev 서버 실행 시 동일)
 */
const lazyDemoElement = (
  loader: () => Promise<{ default: ComponentType }>,
) => createElement(lazy(loader));

const demoRoutes: RouteObject[] = __DEMO_ENABLED__
  ? [
      {
        path: CustomRoutes.setupDemo.path,
        element: lazyDemoElement(() => import('./features/setupData/DemoPage')),
      },
      {
        path: CustomRoutes.setupDemoUrl.path,
        element: lazyDemoElement(
          () => import('./features/setupData/DemoUrlPage'),
        ),
      },
      {
        path: CustomRoutes.intergratedDashboard.path,
        element: lazyDemoElement(
          () => import('./features/mockupDemoUi/Dashboard'),
        ),
      },
      {
        path: CustomRoutes.monitoringDashboard.path,
        element: lazyDemoElement(
          () => import('./features/mockupDemoUi/MonitoringDashboard'),
        ),
      },
      {
        path: CustomRoutes.disabillityDashboard.path,
        element: lazyDemoElement(
          () => import('./features/mockupDemoUi/DisabillityDashborad'),
        ),
      },
    ]
  : [];

const ListPackaging = lazy(
  () => import('./features/packaging/listPackaging/ListPackaging'),
);
const AddNewPackaging = lazy(
  () => import('./features/packaging/addNewPacking/AddNewPacking'),
);
const EditPacking = lazy(
  () => import('./features/packaging/editPackaging/EditPackaging'),
);

// import AddReceivingSystem from "./features/entriOder/AddReceivingSystem";

const Background = () => {
  const { isMobile } = useMobileContext();
  return isMobile ? (
    <Outlet />
  ) : (
    <BackgroundLogin backgroundImage={backgroundImageDefault} />
  );
};

const Sidebar = () => {
  const { isMobile } = useMobileContext();
  return isMobile ? (
    <Outlet />
  ) : (
    <CustomSidebar
      logoDark={logoDarkModeDefault}
      logoLight={logoLightModeDefault}
      logoExpandDark={logoExpandedDarkModeDefault}
      logoExpandLight={logoExpandedLightModeDefault}
    />
  );
};

const Login = () => {
  const { isMobile } = useMobileContext();
  const navigate = useNavigate();

  if (isMobile) {
    return <LoginMobile logoImage={logoExpandedLightModeDefault} />;
  }

  return (
    <LoginPage
      logoImage={logoExpandedLightModeDefault}
      navigate={navigate}
    />
  );
};

const Register = () => {
  const navigate = useNavigate();
  return (
    <RegisterPage
      logoImage={logoExpandedLightModeDefault}
      navigate={navigate}
    />
  );
};

const ForgotPassword = () => {
  const navigate = useNavigate();
  const { isMobile } = useMobileContext();

  if (isMobile) {
    return <ForgotPasswordMobile />;
  }

  return <ForgotPasswordPage navigate={navigate} />;
};

const NewPassword = () => {
  const navigate = useNavigate();
  const { isMobile } = useMobileContext();

  if (isMobile) {
    return <NewPasswordMobile />;
  }

  return (
    <NewPasswordPage
      logoImage={logoExpandedLightModeDefault}
      navigate={navigate}
    />
  );
};

const RootRedirect = () => {
  const userInfo = useUserInfo();
  if (!userInfo) {
    return (
      <Navigate
        to={CustomRouters.home.path}
        replace
      />
    );
  }

  const homeScreenPath = userInfo?.settings?.home_screen_setting__path;
  const homeScreenId = userInfo?.settings?.home_screen_setting_id;

  if (homeScreenPath && homeScreenPath !== '/' && homeScreenId) {
    return (
      <Navigate
        to={`${homeScreenPath}?menuId=${homeScreenId}`}
        replace
      />
    );
  } else {
    return (
      <Navigate
        to={CustomRouters.profile.path}
        replace
      />
    );
  }
};

const PrivateLayout = () => {
  return (
    <>
      <PrivateRouter redirectPath="/login" />
      <ClearStoreOnRouteChange />
      <GlobalNotifications />
      <PartnerCallbackNotificationPopup />
      <GlobalLoading />
      <FileManagement />
      <FormNavigationBlocker />
    </>
  );
};

function App() {
  initialServices(import.meta.env.VITE_API_URL);

  const router = createBrowserRouter([
    {
      element: <PublicRouter restricted={true} />,
      children: [
        {
          element: <Background />,
          children: [
            { path: CustomRouters.login, element: <Login /> },
            { path: CustomRouters.register, element: <Register /> },
            {
              path: CustomRouters.forgotPassword,
              element: <ForgotPassword />,
            },
            { path: CustomRouters.newPassword, element: <NewPassword /> },
            {
              path: '*',
              element: (
                <Navigate
                  to="/login"
                  replace
                />
              ),
            },
          ],
        },
      ],
    },
    {
      element: <PrivateLayout />,
      children: [
        {
          element: <Sidebar />,
          children: [
            { path: CustomRoutes.qrCode, element: <ScanQRMobile /> },
            // ── DSM 재난안전 모니터링 (D-371 ①) ──────────────────────────
            //   경로는 `CustomRoutes.dsm` 한 곳에서 정한다 — 문자열을 화면에
            //   흩으면 경로를 바꾸는 날 어느 화면이 옛말인지 안 보인다.
            {
              path: CustomRoutes.dsm.dashboard.path,
              element: <DsmControlDashboard />,
            },
            { path: CustomRoutes.dsm.events.path, element: <DsmEventList /> },
            // ── 2파 · UX-13 · UX-17 · UX-18 (차선 C) ─────────────────────
            //   ⚠ `/dsm/events/:id` 가 변수 조각이라 `/dsm/events/...` 리터럴을
            //     삼킬 수 있다 — 그래서 큐는 `/dsm/queue` 로 **다른 가지**에 둔다.
            //     삼킬 수 없는 자리에 두는 것이 순서를 외우는 것보다 안전하다.
            { path: dsm2Routes.focusQueue.path, element: <DsmFocusQueue /> },
            { path: dsm2Routes.drill.path, element: <DsmDrillMode /> },
            { path: dsm2Routes.cameraImport.path, element: <DsmCameraImport /> },
            {
              path: CustomRoutes.dsm.eventDetail.path,
              element: <DsmEventDetail />,
            },
            // ── 모바일 · 이동 중 수신 모드 (U3 · 차선 D) ──────────────────
            //   M1 은 발송 기록이 정본이다(이벤트 목록이 아니다). 상세는 목록의
            //   값을 물려받지 않고 서버에 다시 묻는다 — 문지기가 목록에만 서고
            //   상세에 안 서는 모양을 만들지 않기 위해서다.
            { path: mobileRoutes.inbox.path, element: <MobileInbox /> },
            {
              path: mobileRoutes.eventDetail.path,
              element: <MobileEventDetail />,
            },
            { path: CustomRouters.user.path, element: <UserManagement /> },
            {
              path: CustomRouters.user.subRoutes.addUser.path,
              element: <AddUser />,
            },
            { path: CustomRouters.home.path, element: <RootRedirect /> },
            { path: CustomRouters.menu.path, element: <MenuManagement /> },
            {
              path: CustomRouters.menu.subRoutes.addMenu.path,
              element: <AddMenu />,
            },
            { path: CustomRouters.profile.path, element: <ProfilePage /> },
            { path: CustomRouters.role.path, element: <RoleManagement /> },
            { path: CustomRouters.config.path, element: <ConfigManagement /> },
            {
              path: CustomRouters.config.subRoutes.editConfig.path,
              element: <EditConfig />,
            },
            { path: CustomRoutes.device.path, element: <ListDevice /> },
            {
              path: CustomRoutes.device.subRoutes.addNewDevice.path,
              element: <FormAddNewDevice />,
            },
            {
              path: CustomRoutes.device.subRoutes.detailDevice.path,
              element: <DetailDevice />,
            },
            {
              path: CustomRoutes.device.subRoutes.editDevice.path,
              element: <EditDeviceForm />,
            },
            { path: CustomRoutes.packaging.path, element: <ListPackaging /> },
            {
              path: CustomRoutes.packaging.subRoutes.addNewPackaging.path,
              element: <AddNewPackaging />,
            },
            {
              path: CustomRoutes.packaging.subRoutes.detailPackaging.path,
              element: <EditPacking />,
            },
            {
              path: CustomRoutes.etriOrder.subRoutes.addNewEtriOrder.path,
              element: <AddNewEtriOrder />,
            },
            {
              path: CustomRoutes.deliveryInquiry.path,
              element: <ListDeliveryInquiry />,
            },
            {
              path: CustomRoutes.deliveryOperation.path,
              element: <DeliveryOperation />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.orderDetail.path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.unverifiedOrder
                .path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.verifiedOrder.path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.arrivedOrder.path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.completedOrder
                .path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes.cancelledOrder
                .path,
              element: <OrderDetail />,
            },
            {
              path: CustomRoutes.deliveryOperation.subRoutes
                .addNewDeliveryInquiry.path,
              element: <FormAddNewOrder />,
            },

            // Delivery Report
            {
              path: CustomRoutes.deliveryReport.path,
              element: <DeliveryReport />,
            },
            {
              path: CustomRoutes.deliveryReport.subRoutes.completedOrderDetail
                .path,
              element: <DeliveryReportOrderDetail />,
            },

            // Survey Profile
            {
              path: CustomRoutes.surveyProfile.path,
              element: <SurveillanceProfile />,
            },
            {
              path: CustomRoutes.surveyProfile.subRoutes.addNewSurveyProfile
                .path,
              element: <AddNewOrderSurveillanceProfile />,
            },
            {
              path: CustomRoutes.surveyProfile.subRoutes.detailSurveyProfile
                .path,
              element: <ProfileDetailPage />,
            },

            {
              path: CustomRoutes.deliveryInquiry.subRoutes.detailDeliveryInquiry
                .path,
              element: <DetailOrder />,
            },
            {
              path: CustomRoutes.deliveryInquiry.subRoutes.addNewDeliveryInquiry
                .path,
              element: <FormAddNewOrderDeliveryInquiry />,
            },

            // Operation Setting
            {
              path: CustomRoutes.operationSettings.path,
              element: <OperationSetting />,
            },

            { path: CustomRoutes.terminals.path, element: <ListTerminals /> },
            {
              path: CustomRoutes.terminals.subRoutes.addNewTerminals.path,
              element: <AddNewTerminals />,
            },
            {
              path: CustomRoutes.terminals.subRoutes.editTerminals.path,
              element: <EditTerminals />,
            },
            { path: CustomRoutes.routes.path, element: <ListRoute /> },
            {
              path: CustomRoutes.routes.subRoutes.addNewRoute.path,
              element: <AddNewRoute />,
            },
            {
              path: CustomRoutes.routes.subRoutes.detailRoute.path,
              element: <DetailRoute />,
            },
            {
              path: CustomRoutes.routes.subRoutes.editRoute.path,
              element: <EditRoute />,
            },
            {
              path: CustomRoutes.otherEquipments.path,
              element: <OtherEquipments />,
            },
            {
              path: CustomRoutes.otherEquipments.subRoutes.addNewOtherEquipment
                .path,
              element: <AddNewEquipment />,
            },
            {
              path: CustomRoutes.otherEquipments.subRoutes.detailEquipment.path,
              element: <DetailEquipment />,
            },

            {
              path: CustomRoutes.partnerManagement.path,
              element: <ListPartner />,
            },

            // W0-4: 데모·목업 라우트는 VITE_ENABLE_DEMO=true 빌드에서만 등록된다.
            ...demoRoutes,
            {
              path: CustomRoutes.aimProxy.path,
              element: <AimProxyPage />,
            },
            {
              path: CustomRoutes.noTam.path,
              element: <NoTam />,
            },
            {
              path: '*',
              element: (
                <Navigate
                  to={CustomRouters.home.path}
                  replace
                />
              ),
            },
            { path: '/delivery-dashboard', element: <DeliveryDashboard /> },
            {
              path: CustomRoutes.deliveryDashboardAnYang.path,
              element: <DeliveryDashboardAnYang />,
            },
            {
              path: '/surveillance-dashboard',
              element: <SurveillanceDashboard />,
            },
            {
              path: CustomRoutes.waybillTemplate.path,
              element: <WaybillTemplate />,
            },
            {
              path: CustomRoutes.waybillTemplate.subRoutes.addNewWaybillTemplate
                .path,
              element: <AddNewTemplate />,
            },
            {
              path: CustomRoutes.waybillTemplate.subRoutes.editWaybillTemplate
                .path,
              element: <EditTemplate />,
            },
            {
              path: CustomRoutes.library.path,
              element: <LibraryDroneList />,
            },
            {
              path: CustomRoutes.library.subRoutes.addNewLibrary.path,
              element: <FormAddNewLibrary />,
            },
            {
              path: CustomRoutes.library.subRoutes.editLibrary.path,
              element: <EditLibraryForm />,
            },

            {
              path: CustomRoutes.trackOrder.path,
              element: <ListEtriOrder />,
            },
            {
              path: CustomRoutes.trackOrder.subRoutes.detailTrackOrder.path,
              element: <DetailEtriOrder />,
            },

            // {
            //   path: CustomRoutes.library.subRoutes.detailLibrary.path,
            //   element: <DetailLibrary />,
            // },

            // Receiving System
            {
              path: CustomRoutes.etriOrder.path,
              element: <ReceivingSystem />,
            },

            {
              path: CustomRoutes.deliveryHubs.path,
              element: <DeliveryHubs />,
            },

            {
              path: CustomRoutes.deliveryHubs.subRoutes.registerDeliveryHubs
                .path,
              element: <RegisterDeliveryHubs />,
            },
            {
              path: CustomRoutes.deliveryHubs.subRoutes.editDeliveryHubs.path,
              element: <EditDeliveryHubs />,
            },
            {
              path: CustomRoutes.deliveryHubs.subRoutes.detailDeliveryHubs.path,
              element: <DetailDeliveryHubs />,
            },

            // Change Password
            {
              path: CustomRouters.changePassword,
              element: <ChangePasswordPage />,
            },

            // Infrastructure
            {
              path: CustomRoutes.infrastructure.path,
              element: <Infrastruture />,
            },
            {
              path: CustomRoutes.infrastructure.subRoutes.register.path,
              element: <RegisterInfrastructure />,
            },
            {
              path: CustomRoutes.infrastructure.subRoutes.detailInfrastructure
                .path,
              element: <DetailInfrastructure />,
            },
            {
              path: CustomRoutes.dockingStation.path,
              element: <DockingStation />,
            },
            {
              path: CustomRoutes.dockingStation.subRoutes.register.path,
              element: <RegisterDockingStation />,
            },
            {
              path: CustomRoutes.dockingStation.subRoutes.detailDockingStation
                .path,
              element: <DetailDockingStation />,
            },

            // Report Template
            {
              path: CustomRoutes.reportTemplate.path,
              element: <ReportTemplate />,
            },
            {
              path: CustomRoutes.reportTemplate.subRoutes.addNewReportTemplate
                .path,
              element: <AddReportTemplate />,
            },
            {
              path: CustomRoutes.reportTemplate.subRoutes.editReportTemplate
                .path,
              element: <EditReportTemplate />,
            },

            // Operational Notice
            {
              path: CustomRoutes.operationalNotice.path,
              element: <OperationalNotice />,
            },
            {
              path: CustomRoutes.operationalNotice.subRoutes
                .addNewOperationalNotice.path,
              element: <AddOperationalNotice />,
            },
            {
              path: CustomRoutes.operationalNotice.subRoutes
                .editOperationalNotice.path,
              element: <EditOperationalNotice />,
            },

            // Multi Stream Monitor
            {
              path: CustomRoutes.multiStreamMonitor.path,
              element: <MultiStreamMonitor />,
            },

            // Checklist Setting
            {
              path: CustomRoutes.checklistSetting.path,
              element: <CheckListSetting />,
            },

            // Order Status
            {
              path: CustomRoutes.orderStatus.path,
              element: <OrderStatus />,
            },

            // Mapping Status
            {
              path: CustomRoutes.mappingStatus.path,
              element: <MappingStatus />,
            },

            // Operational Data
            {
              path: CustomRoutes.operationalData.path,
              element: <ListOperationalData />,
            },
            {
              path: CustomRoutes.operationalData.subRoutes.detailOperationalData
                .path,
              element: <DetailOperationalData />,
            },

            // Flight Log Analysis
            {
              path: CustomRoutes.flightLogAnalysis.path,
              element: <FlightLogAnalysis />,
            },

            // Mission
            {
              path: CustomRoutes.surveyMission.path,
              element: <SurveyMissionPage />,
            },
            {
              path: CustomRoutes.surveyMission.subRoutes.addNewSurveyMission
                .path,
              element: <AddSurveyMissionPage />,
            },
            {
              path: CustomRoutes.surveyMission.subRoutes.detailSurveyMission
                .path,
              element: <DetailSurveyMissionPage />,
            },
            {
              path: CustomRoutes.surveyMission.subRoutes.editSurveyMission.path,
              element: <EditSurveyMissionPage />,
            },
            {
              path: CustomRoutes.dataAnalysis.path,
              element: <DataAnalysisPage />,
            },
            {
              path: CustomRoutes.dataAnalysis.subRoutes.detailDataAnalysis.path,
              element: <DetailDataAnalysisPage />,
            },
            {
              path: CustomRoutes.handover.path,
              element: <HandoverPage />,
            },
            {
              path: CustomRoutes.handover.subRoutes.createShiftLogHandover.path,
              element: <CreateHandoverPage />,
            },
            {
              path: CustomRoutes.handover.subRoutes.handoverDutyDetail.path,
              element: <HandoverDutyDetail />,
            },
            {
              path: CustomRoutes.handover.subRoutes.addNoticeManagement.path,
              element: <AddNoticeManagement />,
            },
            {
              path: CustomRoutes.mediaData.path,
              element: <MediaDataPage />,
            },
            {
              path: CustomRoutes.mediaData.subRoutes.videoAnalysis.path,
              element: <MediaDataVideoAnalysisPage />,
            },
            {
              path: CustomRoutes.djiUrl.path,
              element: <DJIPage />,
            },
            {
              path: '/gcs-mavlink',
              element: <GCSPage />,
            },
            {
              path: '/survey-profile/surveillance-gcs',
              element: <SurveillanceGCSPage />,
            },
          ],
        },
      ],
    },
  ]);

  return (
    <AuthProvider>
      <LoadingProvider>
        <ConfigDataWrap>
          <ConfigSystemProvider>
            <MobileProvider>
              <FormDirtyProvider>
                <RouterProvider router={router} />
              </FormDirtyProvider>
            </MobileProvider>
          </ConfigSystemProvider>
        </ConfigDataWrap>
      </LoadingProvider>
    </AuthProvider>
  );
}

export default App;
