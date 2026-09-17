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
 * ★ [P-62 꼬리 · 2026-09-05 턴 F · 차선 S] **끊긴 화면의 한 줄.**
 *   휴대전화에서 로그인해 이 화면이 닫혔을 때, 그 사실을 화면이 말하고
 *   1클릭으로 다시 로그인한다. 안 뜨는 것이 기본값이다 — 밀려남 표식
 *   (`reason_code: session_evicted`)이 온 401 에서만 그린다.
 */
import { SessionEndedNotice } from '@/features/session/SessionEndedNotice';
import { PermissionDeniedNotice } from '@/features/session/PermissionDeniedNotice';
/**
 * ★ [P-105 · 2026-09-07 턴 M · 차선 C] **역할 0개 계정이 볼 화면은 하나다.**
 *   온보딩 표 0행. 근거와 규율은 `features/session/rolePending.ts` 머리말에 있다.
 */
import { hasNoRoles } from '@/features/session/rolePending';
import { RolePendingScreen } from '@/features/session/RolePendingScreen';
/**
 * ★ [P-122 · UX-28 · 턴 O · 차선 C2] **역할마다 사이드바에 서는 줄을 표대로 자른다.**
 *   그리는 것이 없다 — 인수 사이드바가 읽는 목록을 갈아 끼운다.
 *   표와 근거는 `features/nav/roleNav.ts` 머리말에 있다. **가림이지 자물쇠가 아니다.**
 */
import RoleNavFilter from '@/features/nav/RoleNavFilter';

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
import InheritedScreen from './components/InheritedScreen';
/**
 * ★ [P-123 · UX-31 ④ · 턴 O · 차선 C2] **빈 표가 「없다」로 읽히던 자리.**
 *   인수 목록 화면 위에 **우리가 직접 센 수**를 한 줄 얹는다. 실측과 규율은
 *   `components/InheritedScreen/ListRealityNote.tsx` 머리말에 있다.
 */
import ListRealityNote from './components/InheritedScreen/ListRealityNote';
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
import LoginDesktop from './features/login/LoginDesktop';
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
import BuildVersion from './features/dsm/components/BuildVersion';
import { KICK_SENTENCE } from './features/dsm/constants/kick';
import { dsm2Routes } from './features/dsm/routes';
import { dsmU24Redirects, dsmU24Routes } from './features/dsm/routes.u24';
import { resolveHome } from './features/nav/roleHome'; // P-141 · 첫 화면은 이 한 곳이 정한다
import {
  adoptWallToken,
  WALL_TOKEN_LEGACY_QUERY_NOTICE,
  wallTokenLegacyQuery,
} from './features/dsm/wallToken';
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
/**
 * P-147 역할 홈 2단계 — **한 라우트, 역할마다 다른 띠** (턴 R · 차선 F).
 * 경로는 `features/dsm/routes.ts` 한 곳에서 정한다(아래 다른 화면들과 같은 규약).
 */
const DsmRoleHome = lazy(() => import('./features/dsm/pages/Home'));
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
const DsmOnboarding = lazy(() => import('./features/dsm/pages/Onboarding'));
const DsmCameraAddress = lazy(() => import('./features/dsm/pages/CameraAddress'));
/**
 * 턴 D DSM 화면 셋 (2026-09-05) — UX-16 월 모드 · UX-23 카메라 격자 · LAW-07 청구.
 * 경로는 `features/dsm/routes.ts` 한 곳에서 정한다(위와 같은 이유).
 */
const DsmWall = lazy(() => import('./features/dsm/pages/Wall'));
const DsmCameraGrid = lazy(() => import('./features/dsm/pages/CameraGrid'));
// ★ 턴 S · 차선 U24 (S-10) — 조율자가 단 짝. `routes.ts` 의 `cameraTuning` 과 둘이 서야 주소가 산다.
const DsmCameraTuning = lazy(() => import('./features/dsm/pages/CameraTuning'));
// ── 턴 T (차선 U24 · U56 · 조율자 배선) ──────────────────────────────────
const DsmStats = lazy(() => import('./features/dsm/pages/Stats'));
const DsmAuditLog = lazy(() => import('./features/dsm/pages/AuditLog'));
const DsmIntegrations = lazy(() => import('./features/dsm/pages/Integrations'));
const DsmPrivacyRequests = lazy(
  () => import('./features/dsm/pages/PrivacyRequests'),
);
/** 턴 E · OPS-16 계량 표. */
const DsmMetering = lazy(() => import('./features/dsm/pages/Metering'));
/** 턴 G · P-67 보존·백업 선언 (U5 관리자). 미선언은 빨강으로 말한다. */
const DsmSystemSettings = lazy(
  () => import('./features/dsm/pages/SystemSettings'),
);
/** UX-35 요원별 현황 — 골격 (차선 U24 · 턴 R). */
const DsmTeamStatus = lazy(() => import('./features/dsm/pages/TeamStatus'));
/** S-14 사람·역할 — UX-42 (차선 U56 · 턴 R). */
const DsmPeople = lazy(() => import('./features/dsm/pages/People'));
/** S-16 알림 받는 사람·채널 — UX-43 (차선 U56 · 턴 R 골격 → 턴 S 실자료). */
const DsmNotifySettings = lazy(
  () => import('./features/dsm/pages/NotifySettings'),
);
/** S-15 내 정보 — UX-42-me (차선 U56 · 턴 S). 읽기뿐이다(설정 쓰기는 U3 의 WS-02). */
const DsmMe = lazy(() => import('./features/dsm/pages/Me'));
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
/** M4 「내 알림 설정」 — 근무 외 시간 · 담당 구역 · 채널 · 이 기기 알림 (턴 S · 차선 U3). */
const MobileSettings = lazy(
  () => import('./features/mobile/pages/MobileSettings'),
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

/**
 * UX-03 — 로그인 화면의 「처음이세요?」.
 *
 * ★ 인수 화면(`LoginPage`)을 **고치지 않는다.** 링크는 우리 층에서 그 아래에
 *   한 줄로 얹는다 — 고치면 그 화면이 인수 자산이 아니라 우리 빚이 된다.
 * ★ 첫 근무일의 사람은 아직 계정이 손에 익지 않았다. 문서가 저장소에만 있으면
 *   그것은 「있다」이지 「쓴다」가 아니다.
 */
const FirstTimeLink = () => (
  <div style={{ textAlign: 'center', padding: '12px 0' }}>
    {/*
      P-52 킥 문장 — **세 자리에 같은 글자**를 둔다(로그인 · 지금 처리할 것 상단 ·
      월간 1쪽 첫 줄). 제품이 무엇을 하는 물건인지 한 문장으로 말하는 자리이고,
      세 자리가 다른 말을 하면 그것은 문장이 아니라 장식이다.

      ★ 글자를 여기 손으로 적어 두지 않는다 — 상수 하나에서 가져온다
        (`features/dsm/constants/kick.ts`). 자리마다 적으면 한 자리를 고치는 날
        나머지가 옛말이 되고, 옛말이 된 것은 화면에서 안 보인다.
    */}
    <p style={{ margin: '0 0 8px', fontSize: 13, opacity: 0.75 }}>
      {KICK_SENTENCE}
    </p>
    <a href={dsm2Routes.onboarding.path}>처음이세요?</a>
  </div>
);

const Login = () => {
  const { isMobile } = useMobileContext();

  /*
    P-59 — 로그인 화면은 **관문 밖**이라 `PrivateLayout` 아래에 없다. 그래서 여기
    한 번 더 둔다. 지원 창구에 전화가 오는 자리가 정확히 여기다 — 아직 못 들어간
    사람은 관문 안의 어떤 화면도 못 보고, 그때 「무엇이 떠 있나」에 답할 유일한
    화면이 이 화면이다.
    ⚠ 관문 밖에 아직 하나 더 있다 — 온보딩 화면(`dsm2Routes.onboarding`)은
      두 가지 어디에도 안 걸린 홀로 선 경로다. 그 화면에 표시를 넣으려면 그 파일을
      만져야 하고, 이번 턴 그 파일은 이 차선의 것이 아니다.
  */
  if (isMobile) {
    return (
      <>
        <LoginMobile logoImage={logoExpandedLightModeDefault} />
        <FirstTimeLink />
        <BuildVersion />
      </>
    );
  }

  return (
    <>
      {/*
        ★★ [P-78 ② ③ · 2026-09-06 턴 H] **인수 로그인 화면을 우리 층의 것으로 바꿨다.**

        직전 턴의 실측: 500·503·403·타임아웃·서버 다운 **다섯 갈래 전부**에서
        화면이 실패를 한 마디도 안 했고, 빠르게 두 번 누르면 요청이 두 번 나갔다.
        원인은 글자가 아니라 **사실이 흐르는 길**이었다 — 인수 화면이 쓰는 로그인 훅이
        실패를 접으면서 상태 코드를 버린다. 감싸는 것으로는 못 고치는 자리다.

        ⚠ 인수 화면(`LoginPage`)을 **한 자도 고치지 않았다.** 같은 문을 우리 층에서
          부르고, 성공한 뒤의 절차(토큰·프로필·첫 화면)는 그 부품의 훅을 그대로 쓴다.
        ⚠ 일회용 비밀번호(OTP) 갈래는 우리가 그리지 않는다 — 그 갈래를 만나면
          화면이 사실을 말한다. 없는 화면을 지어내지 않는다.
      */}
      <LoginDesktop logoImage={logoExpandedLightModeDefault} />
      <FirstTimeLink />
      <BuildVersion />
    </>
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
  const { isMobile } = useMobileContext();
  if (!userInfo) {
    return (
      <Navigate
        to={CustomRouters.home.path}
        replace
      />
    );
  }

  // ★ [P-141] 첫 화면은 `features/nav/roleHome.ts` **한 곳**이 정한다 — 로그인 화면과
  //   같은 함수다(종전에는 같은 판단을 여기와 LoginDesktop 이 두 벌로 했다 · P-131 사양 §1).
  //   ① 고른 홈 ② 역할의 홈 ③ `/profile`(지금 가던 곳).
  return (
    <Navigate
      to={
        resolveHome(userInfo, {
          device: isMobile ? 'mobile' : 'desktop',
          fallback: CustomRouters.profile.path,
        }).path
      }
      replace
    />
  );
};

const PrivateLayout = () => {
  const privateUserInfo = useUserInfo();

  /*
   * ★ [P-105 · 턴 M · 차선 C] **역할이 0개면 여기서 끝난다.**
   *
   * 이 자리가 관문 안 **모든** 화면의 유일한 부모다(월 모드도 사이드바 화면도
   * 이 아래에 있다). 그래서 가림을 화면마다 붙이지 않고 여기 한 번 둔다 —
   * 화면마다 붙이면 다음에 생기는 화면이 그 규칙 밖에서 태어난다.
   *
   * ⚠ `<Outlet/>` 을 그리는 것은 `PrivateRouter` 다. 여기서 그것을 안 그리면
   *   **자식 라우트가 아예 안 뜬다** — 사이드바도 표도 없다. 그것이 이 결정이
   *   요구하는 바다: 「볼 수 있는 화면이 정확히 하나」.
   *
   * ⚠ 로그인하지 않은 사람은 여기 걸리지 않는다 — `hasNoRoles` 는 `userInfo` 가
   *   없으면 거짓이고, 그 사람은 아래 `PrivateRouter` 가 `/login` 으로 보낸다.
   *   `roles` 가 아직 안 온 동안에도 거짓이다(머리말의 「모르는 동안에는 거짓」).
   *
   * ⚠ **이것은 자물쇠가 아니다.** 문은 여전히 열려 있고, 닫는 것은 뒷단의 일이다
   *   (P-105 · 서버가 403 을 내기 전까지 자료는 샌다 — `rolePending.ts` 머리말).
   */
  if (hasNoRoles(privateUserInfo)) {
    return <RolePendingScreen />;
  }

  return (
    <>
      <PrivateRouter redirectPath="/login" />
      {/*
        P-122 · UX-28 — 사이드바 줄 자르기. **관문 안 모든 화면의 유일한 부모**에
        한 번 둔다(위 P-105 와 같은 자리·같은 이유): 화면마다 붙이면 다음에 생기는
        화면이 그 규칙 밖에서 태어난다. 휴대전화 화면에는 사이드바가 없지만,
        그때도 목록은 같은 자리에서 온다 — 여기 한 번이면 둘 다 덮인다.
      */}
      <RoleNavFilter />
      <ClearStoreOnRouteChange />
      <GlobalNotifications />
      <PartnerCallbackNotificationPopup />
      <GlobalLoading />
      <FileManagement />
      <FormNavigationBlocker />
      {/*
        P-59 — **관문 안의 모든 화면**이 자기 버전을 말한다. 여기 한 번 두는 것으로
        족하다: 관문 뒤의 화면은 전부 이 자리의 자식이고(월 모드도 사이드바 화면도),
        표시는 흐름 밖(`fixed`)이라 어느 화면의 배치도 밀지 않는다.
        ⚠ 이 표시는 화면당 한 번만 떠야 한다 — 화면마다 따로 넣으면 겹쳐 그린다.
      */}
      <BuildVersion />
    </>
  );
};

function App() {
  initialServices(import.meta.env.VITE_API_URL);

  /*
   * ★ P-74 — **월 표시 토큰을 라우터보다 먼저 받는다** (턴 G · 차선 C).
   *
   * 주소에 실려 온 토큰을 여기서 받아 적고 주소창에서 지운다. 라우터를 세운 뒤에
   * 부르면 이미 관문이 한 번 판정한 뒤이고, 그러면 토큰을 들고 온 대형 화면이
   * **로그인 화면으로 튕긴 다음에야** 토큰을 알게 된다.
   *
   * 돌려주는 값이 곧 갈래다: 토큰이 있으면 월 화면은 관문 **밖**에 선다.
   * 무계정 링크 금지를 깨는 것이 아니다 — 월 표시 토큰은 서버가 서명해 발급하고
   * 12시간 뒤 죽고 읽기 문 둘만 여는 **자격증명**이다. 없는 사람에게는 아무것도
   * 열리지 않는다(아래 관문 안 갈래가 그대로 남아 있다).
   */
  const wallByToken = adoptWallToken();

  const router = createBrowserRouter([
    /**
     * UX-03 온보딩 — **관문 밖에 서는 유일한 화면.**
     *
     * 로그인 화면의 「처음이세요?」와 역할 첫 화면의 「?」가 둘 다 여기로 온다.
     * 관문 안에 두면 처음 오는 사람이 못 보고, 관문 밖 공개 가지(`PublicRouter
     * restricted`) 안에 두면 **이미 로그인한 사람이 튕긴다** — 그래서 어느 쪽에도
     * 넣지 않고 맨 앞에 홀로 둔다.
     *
     * ★ 규약을 깨지 않는다: 이 화면은 서버를 한 번도 부르지 않는다(정적 글자뿐).
     * ⚠ 정적 경로라 아래 공개 가지의 `*` 가 삼키지 않는다 — 라우터는 별표보다
     *   글자를 먼저 고른다. 그래도 **맨 앞에 둔다**: 순서를 외우는 것보다 안전하다.
     */
    { path: dsm2Routes.onboarding.path, element: <DsmOnboarding /> },
    /*
     * UX-24c 월 모드 — **월 표시 토큰이 있을 때만** 관문 밖에 선다.
     *
     * ⚠ 라우터는 먼저 선언된 자리를 고른다. 그래서 이 줄이 있으면 아래 관문 안의
     *   같은 경로는 안 불린다 — 토큰이 없으면 이 줄 자체가 **없다**(빈 배열).
     *   토큰 없이 `/wall` 을 열면 종전 그대로 관문이 판정하고 로그인으로 튕긴다.
     */
    /*
     * ★ [P-78 ④ · 2026-09-06 턴 H] **옛 주소로 온 대형 화면에게 말한다.**
     *
     *   `?token=` 은 더는 받지 않는다(접근로그에 남는다 — UX-24c 닫는 조건 ①).
     *   그런데 그냥 안 받으면 관문이 로그인 화면으로 튕기고, **자판도 사람도 없는
     *   대형 화면**은 그 화면을 띄운 채 밤을 샌다. 아침에 남는 것은 「월이 죽었다」
     *   한 줄이고 원인은 아무 데도 없다. 그래서 관문 밖에 **말하는 자리 하나**를 둔다.
     *   이 화면은 서버를 한 번도 부르지 않는다 — 글자뿐이다.
     */
    ...(!wallByToken && wallTokenLegacyQuery()
      ? [
          {
            path: dsm2Routes.wall.path,
            element: (
              <>
                <div
                  style={{
                    minHeight: '100vh',
                    background: '#0b0d12',
                    color: '#ffd666',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: 32,
                    fontSize: 36,
                    lineHeight: 1.5,
                    textAlign: 'center',
                  }}
                >
                  {WALL_TOKEN_LEGACY_QUERY_NOTICE}
                </div>
                <BuildVersion />
              </>
            ),
          },
        ]
      : []),
    ...(wallByToken
      ? [
          {
            path: dsm2Routes.wall.path,
            /*
              ★ 버전 한 줄을 **함께** 세운다. P-59 는 「모든 화면이 자기 버전을
                말한다」이고, 종전에는 관문 안에 한 번 두는 것으로 족했다. 이 갈래는
                관문 밖이라 그 한 번이 안 닿는다 — 고객 지원이 「지금 무엇이 떠
                있나」를 묻는 자리는 대형 화면에서도 똑같이 있다.
            */
            element: (
              <>
                <DsmWall />
                <BuildVersion />
              </>
            ),
          },
        ]
      : []),
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
        // ── UX-16 월(Wall) 모드 — **사이드바 밖 · 관문 안** (턴 D) ─────────
        //   관제실 대형 화면에는 마우스가 없다. 사이드바는 마우스를 전제한
        //   물건이라 이 하나만 형제로 세운다. 관문은 그대로 지난다 —
        //   실제 사건이 뜨는 화면을 무계정으로 열지 않는다.
        { path: dsm2Routes.wall.path, element: <DsmWall /> },
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
            // ── 턴 R · P-147 역할 홈 (U2·U4·U5) ─────────────────────────
            //   ⚠ `/dsm/events/:id` 의 변수 조각 밑이 아니다 — 다른 가지라 삼킴이 없다.
            { path: dsm2Routes.roleHome.path, element: <DsmRoleHome /> },
            // ── 2파 · UX-13 · UX-17 · UX-18 (차선 C) ─────────────────────
            //   ⚠ `/dsm/events/:id` 가 변수 조각이라 `/dsm/events/...` 리터럴을
            //     삼킬 수 있다 — 그래서 큐는 `/dsm/queue` 로 **다른 가지**에 둔다.
            //     삼킬 수 없는 자리에 두는 것이 순서를 외우는 것보다 안전하다.
            { path: dsm2Routes.focusQueue.path, element: <DsmFocusQueue /> },
            { path: dsm2Routes.drill.path, element: <DsmDrillMode /> },
            { path: dsm2Routes.cameraImport.path, element: <DsmCameraImport /> },
            // ── 턴 T · P-164 U24 ⑤ 정본 경로 ─────────────────────────────
            //   `/dsm/cameras/tuning` 은 튜닝 절(카메라 축) · 오탐률 표는 통계 축
            //   `/dsm/stats/false-positive` 가 정본. 옛 이름은 redirect 로 남긴다(줄지 않는다).
            //   ⚠ `/dsm/stats` 와 `/dsm/stats/false-positive` 는 리터럴 둘 — 변수 조각이
            //     없으므로 서로 삼키지 않는다.
            { path: dsm2Routes.cameraTuning.path, element: <DsmCameraTuning mode="tuning" /> },
            {
              path: dsmU24Routes.falsePositive.path,
              element: <DsmCameraTuning mode="false-positive" />,
            },
            { path: dsmU24Routes.stats.path, element: <DsmStats /> },
            { path: dsmU24Routes.auditLog.path, element: <DsmAuditLog /> },
            ...dsmU24Redirects.map((r) => ({
              path: r.from,
              element: <Navigate to={r.to} replace />,
            })),
            { path: dsm2Routes.cameraAddress.path, element: <DsmCameraAddress /> },
            // ── 턴 D · UX-23 · LAW-07 ────────────────────────────────────
            {
              path: dsm2Routes.cameraGrid.path,
              element: <DsmCameraGrid />,
            },
            {
              path: dsm2Routes.privacyRequests.path,
              element: <DsmPrivacyRequests />,
            },
            { path: dsm2Routes.metering.path, element: <DsmMetering /> },
            // ── 턴 G · P-67 보존·백업 선언 (U5) ─────────────────────────
            //   ⚠ `/dsm/metering` 과 형제다. 변수 조각이 없으므로 삼키지 않는다.
            {
              path: dsm2Routes.systemSettings.path,
              element: <DsmSystemSettings />,
            },
            // ── 턴 R · UX-35 요원별 현황 골격 (차선 U24) ─────────────────
            //   ⚠ `/dsm/metering` · `/dsm/system` 과 형제다(변수 조각 없음).
            {
              path: dsm2Routes.teamStatus.path,
              element: <DsmTeamStatus />,
            },
            // ── 턴 R · S-14 사람·역할 · S-16 알림 골격 (차선 U56) ────────
            //   ⚠ `/dsm/metering` · `/dsm/system` · `/dsm/team-status` 와
            //     형제다(변수 조각 없음 — 서로 삼키지 않는다).
            { path: dsm2Routes.people.path, element: <DsmPeople /> },
            {
              path: dsm2Routes.notifySettings.path,
              element: <DsmNotifySettings />,
            },
            // ── 턴 S · S-15 내 정보 (차선 U56) ───────────────────────────
            //   ⚠ `/dsm/notify` · `/dsm/people` 과 형제다(변수 조각 없음).
            { path: dsm2Routes.me.path, element: <DsmMe /> },
            // ── 턴 T · 외부 연계 (차선 U56 · WS-17) — `/dsm/me` 와 형제 ──────
            { path: dsm2Routes.integrations.path, element: <DsmIntegrations /> },
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
            //   M4 「내 알림 설정」 — 리터럴 한 조각이라 `/m/events/:id` 와
            //   서로 삼키지 않는다(선언 순서가 곧 라우팅이다).
            { path: mobileRoutes.settings.path, element: <MobileSettings /> },
            {
              /*
                P-123 · UX-31 ④ — **빈 표가 「없다」로 읽히던 자리** (턴 O · 차선 C2).
                [실측] 서버는 사용자 30명을 내주는데 이 화면은 90바이트였다(표 요소 0개).
                인수 화면은 못 고친다(§0.4) — 위에 **직접 세어서** 한 줄을 얹는다.
                근거는 `components/InheritedScreen/ListRealityNote.tsx` 머리말에 있다.
              */
              path: CustomRouters.user.path,
              element: (
                <>
                  <ListRealityNote
                    countUrl="/api/v1/user/list/"
                    noun="사용자"
                    addPath={CustomRouters.user.subRoutes.addUser.path}
                    addLabel="사용자 추가"
                  />
                  <UserManagement />
                </>
              ),
            },
            {
              path: CustomRouters.user.subRoutes.addUser.path,
              element: <AddUser />,
            },
            { path: CustomRouters.home.path, element: <RootRedirect /> },
            {
              path: CustomRouters.menu.path,
              element: (
                <InheritedScreen title="메뉴 관리">
                  <MenuManagement />
                </InheritedScreen>
              ),
            },
            {
              path: CustomRouters.menu.subRoutes.addMenu.path,
              element: <AddMenu />,
            },
            { path: CustomRouters.profile.path, element: <ProfilePage /> },
            {
              path: CustomRouters.role.path,
              element: (
                <InheritedScreen title="역할 관리">
                  {/* P-123 · UX-31 ④ — 서버 15행 · 화면 0행이던 자리. 위 `/users` 와 같은 규율. */}
                  <ListRealityNote countUrl="/api/roles/" noun="역할" />
                  <RoleManagement />
                </InheritedScreen>
              ),
            },
            { path: CustomRouters.config.path, element: <ConfigManagement /> },
            {
              path: CustomRouters.config.subRoutes.editConfig.path,
              element: <EditConfig />,
            },
            {
              path: CustomRoutes.device.path,
              element: (
                <InheritedScreen title="드론·로봇 장비 등록">
                  <ListDevice />
                </InheritedScreen>
              ),
            },
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
              element: (
                <InheritedScreen title="조사 프로파일">
                  <SurveillanceProfile />
                </InheritedScreen>
              ),
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
              element: (
                <InheritedScreen title="항공 고시보">
                  <NoTam />
                </InheritedScreen>
              ),
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
              element: (
                <InheritedScreen title="보고서 서식">
                  <ReportTemplate />
                </InheritedScreen>
              ),
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
              element: (
                <InheritedScreen title="비행 기록 분석">
                  <FlightLogAnalysis />
                </InheritedScreen>
              ),
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
              element: (
                <InheritedScreen title="영상 자료">
                  <MediaDataPage />
                </InheritedScreen>
              ),
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
      {/* 관문 안팎 어디서 끊기든 같은 한 줄이 뜬다 — 라우터보다 바깥에 둔다. */}
      <SessionEndedNotice />
      {/* P-88 · 2026-09-07 턴 J · 차선 C — 403 을 **말하는** 자리.
          같은 이유로 라우터 바깥이다: 어느 화면이 막히든 같은 한 줄이 뜬다.
          ⚠ `SessionEndedNotice` 와 달리 뒤를 막지 않는다 — 막힌 것은 문 하나다. */}
      <PermissionDeniedNotice />
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
