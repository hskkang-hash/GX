import dayjs from 'dayjs';
import 'dayjs/locale/th';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import { lazy } from 'react';
import {
  createBrowserRouter,
  Navigate,
  Outlet,
  RouterProvider,
  useNavigate,
} from 'react-router-dom';
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

import logoExpandedLightModeDefault from './assets/images/Full Version-Black.png';
import logoExpandedDarkModeDefault from './assets/images/Full Version-White.png';
import logoLightModeDefault from './assets/images/Short Version-Black.png';
import logoDarkModeDefault from './assets/images/Short Version-White.png';
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
import DashboardPage from './features/mockupDemoUi/Dashboard';
import DisabillityDashborad from './features/mockupDemoUi/DisabillityDashborad';
import MonitoringDashboard from './features/mockupDemoUi/MonitoringDashboard';
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
const DemoPage = lazy(() => import('./features/setupData/DemoPage'));
const DemoUrlPage = lazy(() => import('./features/setupData/DemoUrlPage'));

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

            { path: CustomRoutes.setupDemo.path, element: <DemoPage /> },
            { path: CustomRoutes.setupDemoUrl.path, element: <DemoUrlPage /> },
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
            { path: '/intergrated-dashboard', element: <DashboardPage /> },
            { path: '/monitoring-dashboard', element: <MonitoringDashboard /> },
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
              path: '/disabillity-dashboard',
              element: <DisabillityDashborad />,
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
