import React, { useState } from 'react';
import { useMap } from 'react-leaflet';
import toast from 'react-hot-toast';
import { useMapStore } from '../store/useMapStore';

export default function MapControls() {
  const map = useMap();
  const { showDem, toggleDem, showVec, toggleVec } = useMapStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [isLayersOpen, setIsLayersOpen] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    const coordsMatch = searchQuery.match(/^(\d+\.?\d*)[,\s]+(\d+\.?\d*)$/);
    if (coordsMatch) {
      map.flyTo([parseFloat(coordsMatch[1]), parseFloat(coordsMatch[2])], 14);
      return;
    }

    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}`);
      const data = await res.json();
      if (data && data.length > 0) map.flyTo([parseFloat(data[0].lat), parseFloat(data[0].lon)], 14);
      else toast.error("Место не найдено");
    } catch (err) {
      toast.error("Ошибка поиска");
    }
  };

  const handleGPS = () => {
    map.locate({ setView: true, maxZoom: 15 });
    map.once('locationerror', () => toast.error("Не удалось определить геопозицию."));
  };

  return (
    <div className="absolute left-0 right-0 top-20 p-3 md:top-0 md:right-0 md:left-auto md:p-4 flex flex-col items-stretch md:items-end space-y-3 pointer-events-none z-[1000]">
      <form onSubmit={handleSearch} className="flex bg-white/95 rounded-2xl shadow-lg overflow-hidden border border-gray-200 pointer-events-auto backdrop-blur">
        <input type="text" placeholder="Координаты или адрес..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="min-w-0 flex-1 px-4 py-3 text-sm md:text-base md:w-72 outline-none" />
        <button type="submit" className="bg-slate-900 hover:bg-slate-800 px-4 py-3 text-white border-l border-slate-900 font-semibold transition">Поиск</button>
      </form>
      <div className="flex items-center justify-end gap-2 pointer-events-auto">
        <button onClick={handleGPS} className="bg-white/95 px-4 py-3 rounded-2xl shadow-lg border border-gray-200 hover:bg-gray-100 text-gray-700 font-semibold transition">GPS</button>
        <div className="relative">
          <button onClick={() => setIsLayersOpen(!isLayersOpen)} className="bg-white/95 px-4 py-3 rounded-2xl shadow-lg border border-gray-200 hover:bg-gray-100 text-gray-700 font-semibold w-full transition">Слои</button>
        {isLayersOpen && (
          <div className="absolute top-14 right-0 bg-white p-4 rounded-2xl shadow-xl border border-gray-300 w-64 flex flex-col space-y-4">
            <h4 className="text-sm font-bold text-gray-500 uppercase border-b pb-2">Данные</h4>
            <label className="flex items-center space-x-3 cursor-pointer p-1 hover:bg-gray-50 rounded">
              <input type="checkbox" checked={showDem} onChange={toggleDem} className="h-5 w-5 text-blue-600" />
              <span>Рельеф (ЦМР)</span>
            </label>
            <label className="flex items-center space-x-3 cursor-pointer p-1 hover:bg-gray-50 rounded">
              <input type="checkbox" checked={showVec} onChange={toggleVec} className="h-5 w-5 text-blue-600" />
              <span>Реки и дороги</span>
            </label>
          </div>
        )}
        </div>
      </div>
    </div>
  );
}
