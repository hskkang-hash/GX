declare module 'rj-core' {
  export function useTheme(): [string, (theme: string) => void];
  export function useProfile(): {
    profile: any;
    getProfile: () => any;
    saveProfile: (profile: any) => void;
    updateProfileData: (profile: any) => void;
    clearProfileData: () => void;
    getProfileField: (field: string) => any;
    hasProfile: () => boolean;
  };
}
