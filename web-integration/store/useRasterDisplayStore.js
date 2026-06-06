// src/store/useRasterDisplayStore.js
import { create } from 'zustand';

const useRasterDisplayStore = create((set) => ({
  displayResultId: null,
  displayRasterUrl: null,
  displayRasterBounds: null,        // [minx, miny, maxx, maxy] в WGS84
  displayRasterOpacity: 0.7,

  setDisplayResultId: (id) => set({ displayResultId: id }),
  setDisplayRasterUrl: (url) => set({ displayRasterUrl: url }),
  setDisplayRasterBounds: (bounds) => set({ displayRasterBounds: bounds }),
  clearDisplayRaster: () => set({ displayResultId: null, displayRasterUrl: null, displayRasterBounds: null }),
  setDisplayRasterOpacity: (opacity) => set({ displayRasterOpacity: opacity }),
}));

export default useRasterDisplayStore;