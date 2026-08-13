export const getColorStatus = ({
  theme,
  status,
}: {
  theme: string;
  status: 'normal' | 'loading' | 'error';
}) => {
  const currentStatus = {
    normal: {
      backgroundColor: theme === 'dark' ? '#3F5848' : '#D6F8E2',
      color: '#0CBA47',
    },
    loading: {
      backgroundColor: theme === 'dark' ? '#3C3D3E' : '#F2F2F2',
      color: '#9C9D9D',
    },
    error: {
      backgroundColor: theme === 'dark' ? '#613B3B' : '#FFEBE8',
      color: '#EE533D',
    },
  };
  return (
    currentStatus[status as keyof typeof currentStatus] || currentStatus.loading
  );
};
