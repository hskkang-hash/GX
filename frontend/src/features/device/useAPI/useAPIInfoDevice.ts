import API, { endpoint } from '@/services/API';

const useAPIInfoDevice = () => {
  const getOptionsByModelWithPortal = ({
    search_field,
    key = 'name',
    value = 'id',
  }: {
    search_field: string;
    key: string;
    value: string;
  }) => {
    return async (search: string, { page }: { page: number }) => {
      const response = await API.get(endpoint.portalData, {
        params: {
          name: search || '',
          page_number: page ?? 1,
          page_size: 10,
          type: search_field ?? '',
          distinct: true,
        },
      });

      const data = response.data || [];
      const hasMore = data.length === 10; // hoặc tùy vào cấu trúc response

      return {
        options: data.map((item: any) => ({
          label: item[key],
          value: item[value],
        })),
        hasMore,
        additional: {
          page: (page ?? 1) + 1,
        },
      };
    };
  };

  return {
    getOptionsByModelWithPortal,
  };
};

export default useAPIInfoDevice;
