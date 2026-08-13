import { create } from 'zustand';

import { DeliveryHubsStore } from '../types/IDeliveryHubs';

export const useDeliveryHubsStore = create<DeliveryHubsStore>()((set) => ({
  deliveryHubDetail: null,
  setDeliveryHub: (deliveryHub) => set({ deliveryHubDetail: deliveryHub }),
}));
