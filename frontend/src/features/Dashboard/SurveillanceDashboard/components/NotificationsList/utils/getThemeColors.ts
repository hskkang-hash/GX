import Colors from '@/configs/Colors';

export const getThemeColors = (theme: string) => ({
  text: theme === 'dark' ? Colors.Gray3 : '#333',
  textSecondary: theme === 'dark' ? Colors.Gray5 : '#999',
  background: theme === 'dark' ? '#2D2E30' : '#F6F7F8',
  backgroundAlt: theme === 'dark' ? '#3D3E40' : '#fff',
  border: theme === 'dark' ? '#4D4E50' : '#E0E0E0',
  skeletonPrimary:
    theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
  skeletonSecondary:
    theme === 'dark' ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.08)',
});

export type ThemeColors = ReturnType<typeof getThemeColors>;

