import { useLoadingContext } from 'rj-core';

import API, { endpoint } from '@/services/API';
import { failureLine } from '@/features/session/apiFailure';

const useEquipment = () => {
  const { showLoading, hideLoading } = useLoadingContext();
  const getEquipmentList = async ({
    pageSize = 25,
    currentPage = 1,
    objSearch = {},
  }: {
    pageSize?: number;
    currentPage?: number;
    objSearch?: any;
  }) => {
    const params = {
      page_size: pageSize,
      current_page: currentPage,
      depth: 2,
    };
    if (objSearch) {
      if (objSearch?.searchParams) {
        objSearch?.searchParams.forEach((item: any) => {
          {
            params[item.id] = item.value;
          }
        });
      }
      if (objSearch?.filters) {
        params['filters'] = objSearch.filters;
      }
      if (objSearch?.sortParams && objSearch?.sortParams.length) {
        params.sort_obj = objSearch.sortParams;
      }
    }
    // ★ [SEC-11a · 2026-09-07 턴 J · 차선 C] **`showLoading()` 뒤에 `try` 가 없었다.**
    //   차선 S 가 `settings.py` 주석에 이 파일과 이 다섯 함수를 **이름으로** 적어 두었다:
    //   「`/api/devices/cameras/` 9건을 안 켠 사유 — 승격하면 거절이 예외가 되고
    //     `hideLoading()` 이 영원히 안 돈다 = **스피너 고착**. 그 파일은 `frontend/` 라
    //     차선 S 의 손 밖이다.」 그 손이 이 차선이다. 여기가 그 자리다.
    //   ⚠ `if (success) hideLoading(); else hideLoading();` 은 갈래가 둘인 척하지만
    //     **한 갈래도 예외를 안 덮는다.** `finally` 한 곳으로 모은다.
    try {
      const { success, message, data, total_items, total_pages } = await API.get(
        'api/devices/cameras',
        { params },
      );
      return {
        success,
        message,
        data,
        totalItem: total_items,
        totalPage: total_pages,
      };
    } catch (error) {
      // 거절을 **값으로** 돌려준다 — 부르는 쪽(`OtherEquipments.tsx`)이 그 값으로
      // 사람에게 말한다. 되던지면 그 화면의 `catch` 가 받고, 그것도 이제 있다.
      return {
        success: false,
        message: failureLine('useEquipment.list', error),
        data: [],
        totalItem: 0,
        totalPage: 0,
      };
    } finally {
      hideLoading();
    }
  };

  const getDetailEquipment = async (id: number) => {
    showLoading();
    // ★ [SEC-11a · 2026-09-07 턴 J · 차선 C] **`showLoading()` 뒤에 `try` 가 없었다.**
    //   차선 S 가 `settings.py` 주석에 이 파일과 이 다섯 함수를 **이름으로** 적어 두었다:
    //   「`/api/devices/cameras/` 9건을 안 켠 사유 — 승격하면 거절이 예외가 되고
    //     `hideLoading()` 이 영원히 안 돈다 = **스피너 고착**. 그 파일은 `frontend/` 라
    //     차선 S 의 손 밖이다.」 그 손이 이 차선이다. 여기가 그 자리다.
    //   ⚠ `if (success) hideLoading(); else hideLoading();` 은 갈래가 둘인 척하지만
    //     **한 갈래도 예외를 안 덮는다.** `finally` 한 곳으로 모은다.
    try {
    const { success, message, data } = await API.get(
      endpoint.detailEquipment(id, false),
    );
    return {
      success,
      message,
      data: {
        name: data.name,
        resolution: {
          width: {
            value: data.resolution.width,
            unit: data.resolution.unit,
          },
          height: {
            value: data.resolution.height,
            unit: data.resolution.unit,
          },
        },
        frame_rate: {
          value: data.frame_rate.value,
          unit: data.frame_rate.unit,
        },
        field_of_view: {
          value: [data.field_of_view.min, data.field_of_view.max],
          unit: data.field_of_view.unit,
        },
        weight: {
          min: {
            value: data.weight.min,
            unit: data.weight.original_unit,
          },
          max: {
            value: data.weight.max,
            unit: data.weight.original_unit,
          },
        },
        image_stabilization: {
          value: data.image_stabilization_id,
          label: data.image_stabilization__name,
        },
        note: data.note || '',
        group: data.group__id
          ? {
              value: data.group__id,
              label: data.group__name,
            }
          : null,
      },
    };
    } catch (error) {
      // ⚠ **`data` 를 지어내지 않는다.** 위 매핑은 `data.resolution.width` 처럼
      //   깊이 파고든다 — 거절 갈래에서 빈 껍데기를 만들어 돌려주면 그 껍데기가
      //   서식에 그려지고 「값이 없다」가 「빈 값으로 저장됨」이 된다.
      return {
        success: false,
        message: failureLine('useEquipment.detail', error),
        data: null,
      };
    } finally {
      hideLoading();
    }
  };

  const createEquipment = async (data) => {
    // ★ [SEC-11a · 2026-09-07 턴 J · 차선 C] **`showLoading()` 뒤에 `try` 가 없었다.**
    //   차선 S 가 `settings.py` 주석에 이 파일과 이 다섯 함수를 **이름으로** 적어 두었다:
    //   「`/api/devices/cameras/` 9건을 안 켠 사유 — 승격하면 거절이 예외가 되고
    //     `hideLoading()` 이 영원히 안 돈다 = **스피너 고착**. 그 파일은 `frontend/` 라
    //     차선 S 의 손 밖이다.」 그 손이 이 차선이다. 여기가 그 자리다.
    //   ⚠ `if (success) hideLoading(); else hideLoading();` 은 갈래가 둘인 척하지만
    //     **한 갈래도 예외를 안 덮는다.** `finally` 한 곳으로 모은다.
    try {
      const { success, message } = await API.post('api/devices/cameras', data);
      return {
        success,
        message,
      };
    } catch (error) {
      return {
        success: false,
        message: failureLine('useEquipment.create', error),
      };
    } finally {
      hideLoading();
    }
  };

  const updateEquipment = async (data, id: number) => {
    // ★ [SEC-11a · 2026-09-07 턴 J · 차선 C] **`showLoading()` 뒤에 `try` 가 없었다.**
    //   차선 S 가 `settings.py` 주석에 이 파일과 이 다섯 함수를 **이름으로** 적어 두었다:
    //   「`/api/devices/cameras/` 9건을 안 켠 사유 — 승격하면 거절이 예외가 되고
    //     `hideLoading()` 이 영원히 안 돈다 = **스피너 고착**. 그 파일은 `frontend/` 라
    //     차선 S 의 손 밖이다.」 그 손이 이 차선이다. 여기가 그 자리다.
    //   ⚠ `if (success) hideLoading(); else hideLoading();` 은 갈래가 둘인 척하지만
    //     **한 갈래도 예외를 안 덮는다.** `finally` 한 곳으로 모은다.
    try {
      const { success, message } = await API.put(
        `api/devices/cameras/${id}`,
        data,
      );
      return {
        success,
        message,
      };
    } catch (error) {
      return {
        success: false,
        message: failureLine('useEquipment.update', error),
      };
    } finally {
      hideLoading();
    }
  };

  const changeStatusEquipment = async ({ ids }) => {
    // ★ [SEC-11a · 2026-09-07 턴 J · 차선 C] **`showLoading()` 뒤에 `try` 가 없었다.**
    //   차선 S 가 `settings.py` 주석에 이 파일과 이 다섯 함수를 **이름으로** 적어 두었다:
    //   「`/api/devices/cameras/` 9건을 안 켠 사유 — 승격하면 거절이 예외가 되고
    //     `hideLoading()` 이 영원히 안 돈다 = **스피너 고착**. 그 파일은 `frontend/` 라
    //     차선 S 의 손 밖이다.」 그 손이 이 차선이다. 여기가 그 자리다.
    //   ⚠ `if (success) hideLoading(); else hideLoading();` 은 갈래가 둘인 척하지만
    //     **한 갈래도 예외를 안 덮는다.** `finally` 한 곳으로 모은다.
    try {
      const { success, message } = await API.put(
        endpoint.changeStatusEquipment(ids),
      );
      return {
        success,
        message,
      };
    } catch (error) {
      return {
        success: false,
        message: failureLine('useEquipment.changeStatus', error),
      };
    } finally {
      hideLoading();
    }
  };

  const activeEquipmentAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.activeEquipment(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };

  const deactiveEquipmentAPI = async ({
    ids,
    useLoading,
  }: {
    ids: string;
    useLoading: boolean;
  }) => {
    try {
      useLoading && showLoading();
      const response = await API.put(endpoint.deactiveEquipment(ids));
      return {
        success: response.success,
        message: response.message,
      };
    } catch (error: any) {
      return {
        success: false,
        message: error.response.data.message,
      };
    } finally {
      useLoading && hideLoading();
    }
  };
  return {
    getEquipmentList,
    getDetailEquipment,
    createEquipment,
    updateEquipment,
    changeStatusEquipment,

    activeEquipmentAPI,
    deactiveEquipmentAPI,
  };
};

export default useEquipment;
