import { create } from 'zustand';

type Center = { lat: number; lng: number };

interface RouteStore {
  center: Center;
  zoom: number;
  getCenterAndZoom: () => { center: Center; zoom: number };
  setCenterAndZoom: (center: Center, zoom: number) => void;
}

export const useZustandRoutes = create<RouteStore>((set, get) => ({
  center: { lat: 0, lng: 0 },
  zoom: 0,

  getCenterAndZoom: () => {
    const { center, zoom } = get();
    return { center, zoom };
  },

  setCenterAndZoom: (center, zoom) => set({ center, zoom }),
}));
