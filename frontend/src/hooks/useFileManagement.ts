import API, { endpoint } from '../services/API';

interface CheckTaskResponse {
  success: boolean;
  data?: unknown;
  message?: string;
}

interface UseFileManagementReturn {
  checkTaskSocket: (task_id: string) => Promise<CheckTaskResponse>;
  checkTaskOperationalData: (task_id: string) => Promise<CheckTaskResponse>;
}

export const useFileManagement = (): UseFileManagementReturn => {
  const checkTaskSocket = async (
    task_id: string,
  ): Promise<CheckTaskResponse> => {
    try {
      const response = await API.get(endpoint.checkTaskSocket(task_id));

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        message: (error as Error)?.message,
      };
    }
  };

  const checkTaskOperationalData = async (
    task_id: string,
  ): Promise<CheckTaskResponse> => {
    try {
      const response = await API.get(
        endpoint.checkTaskOperationalData(task_id),
      );

      return {
        success: true,
        data: response.data,
      };
    } catch (error) {
      return {
        success: false,
        message: (error as Error)?.message,
      };
    }
  };

  return {
    checkTaskSocket,
    checkTaskOperationalData,
  };
};
