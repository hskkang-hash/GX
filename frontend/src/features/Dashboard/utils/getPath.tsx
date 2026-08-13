import { TabItem } from '@/components/Form/Tabs';

interface RolePermission {
  permit_read: boolean;
  permit_create: boolean;
  permit_update: boolean;
  permit_delete: boolean;
  permit_export?: boolean;
  permit_import?: boolean;
}

interface MenuItem {
  id: number;
  menu_name: string;
  path: string;
  icon_name: string;
  role_permissions: RolePermission[];
  sub_menus: MenuItem[];
  tabs?: TabItem[];
}

function GetPath() {
  const getEtriPath = (menuData: MenuItem[]): string | null => {
    const etriPaths: string[] = [];
    const checkMenu = (menus: MenuItem[]) => {
      menus.forEach((menu: MenuItem) => {
        if (menu.path === '/etri-tracking' || menu.path === '/etri-order') {
          etriPaths.push(menu.path);
        }
        if (menu.sub_menus && menu.sub_menus.length > 0) {
          checkMenu(menu.sub_menus);
        }
        if (menu.tabs && menu.tabs.length > 0) {
          menu.tabs.forEach((tab: TabItem) => {
            if (tab.path === '/etri-tracking' || tab.path === '/etri-order') {
              etriPaths.push(tab.path);
            }
          });
        }
      });
    };
    checkMenu(menuData);
    if (etriPaths.includes('/etri-tracking')) {
      return '/etri-tracking';
    } else if (etriPaths.includes('/etri-order')) {
      return '/etri-order';
    }
    return null;
  };

  const getInfrastructurePath = (menuData: MenuItem[]): string | null => {
    const etriPaths: string[] = [];
    const checkMenu = (menus: MenuItem[]) => {
      menus.forEach((menu: MenuItem) => {
        if (menu.path === '/infrastructure') {
          etriPaths.push(menu.path);
        }
        if (menu.sub_menus && menu.sub_menus.length > 0) {
          checkMenu(menu.sub_menus);
        }
        if (menu.tabs && menu.tabs.length > 0) {
          menu.tabs.forEach((tab: TabItem) => {
            if (tab.path === '/infrastructure') {
              etriPaths.push(tab.path);
            }
          });
        }
      });
    };
    checkMenu(menuData);
    if (etriPaths.includes('/infrastructure')) {
      return '/infrastructure';
    }
    return null;
  };

  const getUserManagementPath = (menuData: MenuItem[]): string | null => {
    const etriPaths: string[] = [];
    const checkMenu = (menus: MenuItem[]) => {
      menus.forEach((menu: MenuItem) => {
        if (menu.path === '/users') {
          etriPaths.push(menu.path);
        }
        if (menu.sub_menus && menu.sub_menus.length > 0) {
          checkMenu(menu.sub_menus);
        }
        if (menu.tabs && menu.tabs.length > 0) {
          menu.tabs.forEach((tab: TabItem) => {
            if (tab.path === '/users') {
              etriPaths.push(tab.path);
            }
          });
        }
      });
    };
    checkMenu(menuData);
    if (etriPaths.includes('/users')) {
      return '/users';
    }
    return null;
  };

  return { getEtriPath, getInfrastructurePath, getUserManagementPath };
}

export default GetPath;
