declare module 'rj-core' {
  interface LoginPageProps {
    backgroundImage?: string;
    logoImage?: string;
    navigate: (path: string) => void;
    redirectPath?: string;
  }
  interface SidebarProps {
    children: React.ReactNode;
    logoDark?: string;
    logoLight?: string;
    logoExpandDark?: string;
    logoExpandLight?: string;
  }
  export const LoginPage: React.FC<LoginPageProps>;
  export const RegisterPage: React.FC<RegisterPageProps>;
  export const ForgotPasswordPage: React.FC<ForgotPasswordPageProps>;
  export const NewPasswordPage: React.FC<ResetPasswordPageProps>;
  export const OTPLoginPage: React.FC<OTPLoginPageProps>;
  export const PublicRouter: React.FC<{
    restricted?: boolean;
    redirectPath?: string;
  }>;
  export function setupStore(): any;
  export const PrivateRouter: React.FC<{
    redirectPath?: string;
  }>;
  export function initializeApp(apiUrl: string): void;
  export const Sidebar: React.FC<SidebarProps>;
  export const Header: React.FC;
  export const Customizetable: React.FC;
  export const Main: React.FC<{ children: React.ReactNode }>;
  export const Container: React.FC<{
    children: React.ReactNode;
    id?: string;
    className?: string;
    isOpenCanvas?: boolean;
  }>;
  export const CustomButton: React.FC;
  export const MenuManagementPage: React.FC;
  export const AddMenuManagement: React.FC;
  export const BackgroundDemoPage: React.FC;
  export const useActivePayment: () => boolean;
  export const CustomSelect: React.FC;
  export const useTheme: () => [string, (theme: string) => void];
  export const useUserInfo: () => object;
  export const useConfigSystem: () => [any, (config: any) => void];
  export const HeaderWithBtn: React.FC<{
    ref?: RefObject<HTMLDivElement> | undefined;
    buttons: React.ReactNode[];
    hasLineBottom?: boolean;
  }>;
  export const CustomTabs: React.FC<{
    items: { label: string; key: string }[];
    activeKey?: string;
    onChange: (key: string) => void;
    size?: string;
  }>;
  export const useMenuData: () => [any, (menuData: any) => void];
  export const CustomBtn: React.FC<{
    label?: string;
    type?: string;
    isFlag?: boolean;
    variant?: string;
    color?: string;
    size?: string;
    onClick?: () => void;
    disabled?: boolean;
    loading?: boolean;
    className?: string;
    style?: React.CSSProperties;
    children?: React.ReactNode;
    id?: string;
    icon?: React.ReactNode;
    actionType?: string;
  }>;
  export function createApiClient(options: {
    baseURL: string;
    redirectOn401: () => void;
  }): {
    API: any;
  };
  export function checkPermission(actionType: string, menuData: any): boolean;
  export const FormBlock: React.FC<{
    title?: string;
    className?: string;
    style?: React.CSSProperties;
    onClick?: () => void;
    ref?: RefObject<HTMLDivElement> | undefined;
    children: React.ReactNode;
  }>;
  export const CustomDateTimePicker: React.FC;
  export const CustomizableTable: React.FC<{
    subTable?: boolean;
    useSystemSetting?: boolean;
    stickyHeader?: boolean;
    availableHeight?: float;
    notShowSelectRow?: boolean;
    notUseGroupColumn?: boolean;
    hasPagination?: boolean;
    columns?: {
      Header: string;
      accessor: string;
      filterVariant?: string;
      filterOptions?: { label: string; value: string }[];
      cell?: (row: {
        getValue: () => string;
        row: { original: any };
      }) => React.ReactNode;
      customStyle?: React.CSSProperties;
      enableSorting?: boolean;
      enableColumnFilter?: boolean;
      notUseConfigTable?: boolean;
    }[];
    data?: {
      data: any[] | null;
      totalItem?: number | 0;
      totalPage?: number | 0;
    };
    objSearch?: any;
    setObjSearch?: (objSearch: any) => void;
    onClickRow?: (row: any) => void;
    onSelectedRows?: (rows: any[]) => void;
    refreshTable?: boolean;
    setRefreshTable?: (refresh: boolean) => void;
    buttons?: React.ReactNode[];
    currentPage?: number;
    setCurrentPage?: (page: number) => void;
    pageSize?: number | null;
    setPageSize?: (size: number | null) => void;
    offcanvas?: boolean;
    setOpenOffcanvas?: (boolean: boolean) => void;
    customHighlightRows?: any[];
    customHighlightColor?: string;
  }>;
  export const ToastTopHelper: {
    success: (message: string, extra?: { autoClose?: boolean }) => void;
    error: (message: string, extra?: { autoClose?: boolean }) => void;
    info: (message: string, extra?: { autoClose?: boolean }) => void;
    warning: (message: string, extra?: { autoClose?: boolean }) => void;
  };
  export const useCalculateHeight: (props: {
    refElements?: RefObject<HTMLElement>[] | null;
    additionalHeights?: number[] | null;
  }) => number;
  export const SearchCard: React.FC;
  export const useLoadingContext: () => {
    showLoading: () => void;
    hideLoading: () => void;
    showLoadingGlobal: () => void;
    hideLoadingGlobal: () => void;
  };
  export const CustomBreadcrumb: React.FC<{
    ref?: RefObject<HTMLDivElement> | undefined;
    headerPageRef?: RefObject<HTMLDivElement> | undefined;
    items: { url?: string; text?: string; func?: () => void }[];
    buttons?: React.ReactNode[];
  }>;
  export const CustomInputHookForm: React.FC<{
    name: string;
    control: any;
    label?: string;
    placeholder?: string;
    required?: boolean;
    disabled?: boolean;
    type?: string;
    error?: string;
    rules?: any;
    description?: React.ReactNode;
    inputSize?: string | object;
    style?: React.CSSProperties;
    onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  }>;
  export const CustomModal: React.FC<{
    title?: string;
    show: boolean;
    onHide: () => void;
    children: React.ReactNode;
    id?: string;
    size?: string;
  }>;
  export const ActionBtn: React.FC<{
    leftButtons?: React.ReactNode[];
    middleButtons?: React.ReactNode[];
    rightButtons?: React.ReactNode[];
    styles?: object;
  }>;

  export const CenterBtn: React.FC<{
    color?: string;
    type?: string;
    variant?: string;
    size?: string;
    onClick?: () => void;
    label?: string;
    className?: string;
  }>;

  export const getMenuByMainIdAndSubId: (mainId: number, subId: number) => any;
  export const OffCanvas: React.FC<{
    title?: string;
    show: boolean;
    onHide: () => void;
    id?: string;
    children: React.ReactNode;
  }>;

  export const ROLE_PERMISSION: {
    CREATE: string;
    READ: string;
    UPDATE: string;
    DELETE: string;
  };
  export const useActiveMenu: React.FC;
  export const checkHasReadPermission: React.FC;
  export const GlobalLoading: React.FC;
  export const selectActiveMenuCombined;
  export const useConfigGroupSystem: () => {
    configGroupSystem: any;
    setConfigGroupSystem: (configGroupSystem: any) => void;
    clearConfigGroup: () => void;
    fetchFreshConfigGroup: (groupId: string) => void;
  };
}
