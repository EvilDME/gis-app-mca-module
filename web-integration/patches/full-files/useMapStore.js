import { create } from 'zustand';
import toast from 'react-hot-toast';
import { apiUrl } from '../lib/api';

export const useMapStore = create((set, get) => ({
  // --- НАСТРОЙКИ КАРТЫ ---
  showDem: false, toggleDem: () => set((state) => ({ showDem: !state.showDem })),
  showVec: false, toggleVec: () => set((state) => ({ showVec: !state.showVec })),
  
  // --- ВЗАИМОДЕЙСТВИЕ ---
  clickMode: null, setClickMode: (mode) => set({ clickMode: mode }),
  selectedPoint: null, setSelectedPoint: (pt) => set({ selectedPoint: pt }),
  
  // --- БУФЕР ---
  bufferRadius: 500, setBufferRadius: (r) => set({ bufferRadius: r }),
  showBuffer: false, setShowBuffer: (show) => set({ showBuffer: show }),
  
  // --- АВТОРИЗАЦИЯ ---
  user: JSON.parse(localStorage.getItem('user')) || null,
  token: localStorage.getItem('token') || null,
  showAuth: false, setShowAuth: (show) => set({ showAuth: show }),
  login: (user, token) => {
    localStorage.setItem('user', JSON.stringify(user));
    localStorage.setItem('token', token);
    set({ user, token, showAuth: false });
    get().fetchReviews();
    toast.success(`Добро пожаловать, ${user.username}!`);
  },
  logout: () => {
    localStorage.removeItem('user');
    localStorage.removeItem('token');
    set({ user: null, token: null, selectedReview: null });
    get().fetchReviews();
    toast.success('Вы вышли из аккаунта');
  },

  // --- ОТЗЫВЫ ---
  reviews:[], 
  newReviewLocation: null, setNewReviewLocation: (loc) => set({ newReviewLocation: loc }),
  selectedReview: null, setSelectedReview: (rev) => set({ selectedReview: rev }),
  fetchReviews: async () => {
    try {
      const token = get().token;
      const res = await fetch(apiUrl('/api/reviews'), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      const reviews = await res.json();
      const selectedReviewId = get().selectedReview?.id;
      set({
        reviews,
        selectedReview: selectedReviewId ? reviews.find((review) => review.id === selectedReviewId) || null : null,
      });
    } catch (err) {
      toast.error('Не удалось загрузить отзывы');
    }
  },

  // --- МАРШРУТИЗАЦИЯ ---
  routeStart: null, setRouteStart: (pt) => set({ routeStart: pt }),
  routeEnd: null, setRouteEnd: (pt) => set({ routeEnd: pt }),
  routePath: null, setRoutePath: (path) => set({ routePath: path }),
  routeStats: null, setRouteStats: (stats) => set({ routeStats: stats }),
  routeProgress: 0, setRouteProgress: (p) => set({ routeProgress: p }),
  routeMode: 'safe',
  setRouteMode: (routeMode) => set({ routeMode }),
  exactRouting: false,
  setExactRouting: (exactRouting) => set({ exactRouting }),
  routeWeights: { field: 25, slope: 20 },
  setRouteWeights: (weights) => set({ routeWeights: weights }),
  
  // Точка, на которую навели на графике высот
  hoveredRoutePoint: null, setHoveredRoutePoint: (pt) => set({ hoveredRoutePoint: pt }),
  
  clearRoute: () => {
    set({ routeStart: null, routeEnd: null, routePath: null, routeStats: null, clickMode: null, routeProgress: 0, hoveredRoutePoint: null });
    toast.success('Маршрут очищен');
  },

  calculateRoute: async () => {
    const { routeStart, routeEnd, routeWeights, routeMode, exactRouting } = get();
    if (!routeStart || !routeEnd) {
      toast.error('Выберите точку старта и финиша!');
      return;
    }
    
    set({ routeProgress: 10, routePath: null, routeStats: null, hoveredRoutePoint: null });
    const toastId = toast.loading('Расчет оптимального маршрута...');
    
    const presets = {
      fast: { field: 55, slope: 12, waterEdge: 18, turn: 12 },
      safe: { field: 32, slope: 42, waterEdge: 58, turn: 26 },
      scenic: { field: 22, slope: 28, waterEdge: 36, turn: 18 },
    };

    const effectiveWeights = exactRouting
      ? { ...presets[routeMode], ...routeWeights }
      : presets[routeMode];
    const systemFieldWeight = 1 + (effectiveWeights.field / 100) * 9;
    const systemSlopePenalty = (effectiveWeights.slope / 100) * 5;
    const systemWaterEdgePenalty = (effectiveWeights.waterEdge / 100) * 4;
    const systemTurnPenalty = (effectiveWeights.turn / 100) * 1.5;

    try {
      const res = await fetch(apiUrl('/api/route'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          startCoord: routeStart, 
          endCoord: routeEnd, 
          weights: {
            road: 1,
            field: systemFieldWeight,
            slope: systemSlopePenalty,
            waterEdge: systemWaterEdgePenalty,
            turn: systemTurnPenalty,
            mode: routeMode,
          } 
        })
      });
      const data = await res.json();
      
      if (data.success) {
        // --- СГЛАЖИВАНИЕ ПУТИ (Moving Average Interpolation) ---
        // Устраняет "лесенку" от A* сетки, сохраняя точное количество точек
        const smoothPath = (path, iterations = 3) => {
          if (!path || path.length < 3) return path;
          let result = [...path];
          for (let iter = 0; iter < iterations; iter++) {
            let temp = [result[0]];
            for (let i = 1; i < result.length - 1; i++) {
              const lat = (result[i-1][0] + result[i][0] + result[i+1][0]) / 3;
              const lng = (result[i-1][1] + result[i][1] + result[i+1][1]) / 3;
              temp.push([lat, lng]);
            }
            temp.push(result[result.length - 1]);
            result = temp;
          }
          return result;
        };
        const finalPath = smoothPath(data.path, 3); // 3 прохода для идеальной гладкости

        // ФИЛЬТР ВЫСОТ: Имитируем сглаживание Garmin/Strava
        let smoothedGain = 0;
        let smoothedLoss = 0;
        const profile = data.stats.profile;
        if (profile && profile.length > 0) {
            let lastSignificantEle = profile[0];
            for(let i = 1; i < profile.length; i++) {
                let diff = profile[i] - lastSignificantEle;
                if(Math.abs(diff) >= 3) { 
                    if(diff > 0) smoothedGain += diff;
                    else smoothedLoss += Math.abs(diff);
                    lastSignificantEle = profile[i];
                }
            }
            data.stats.gain = Math.round(smoothedGain);
            data.stats.loss = Math.round(smoothedLoss);
        }

        set({ routePath: finalPath, routeStats: data.stats, routeProgress: 100 });
        toast.success('Маршрут успешно построен!', { id: toastId });
        setTimeout(() => set({ routeProgress: 0 }), 1000);
      } else {
        throw new Error(data.message);
      }
    } catch (err) {
      set({ routeProgress: 0 });
      toast.error("Не удалось построить: " + err.message, { id: toastId });
    }
  }
}));
