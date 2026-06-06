import React, { useEffect } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';

export default function AreaSelector({ onSelect, onClose }) {
  const map = useMap();
  const markers = [];
  const polygonRef = React.useRef(null);

  useEffect(() => {
    const points = [];
    const onClick = (e) => {
      points.push(e.latlng);
      // маркер
      const marker = L.marker(e.latlng).addTo(map);
      markers.push(marker);
      if (points.length === 4) {
        // строим полигон
        const latlngs = points.map(p => [p.lat, p.lng]);
        const polygon = L.polygon(latlngs, { color: 'blue' }).addTo(map);
        polygonRef.current = polygon;
        // передаём GeoJSON
        const geojson = {
          type: 'Polygon',
          coordinates: [latlngs.map(([lng, lat]) => [lat, lng])], // [lon,lat] формат для GeoJSON
        };
        onSelect(geojson);
        // убираем обработчик
        map.off('click', onClick);
      }
    };
    map.on('click', onClick);

    return () => {
      map.off('click', onClick);
      markers.forEach(m => m.remove());
      if (polygonRef.current) polygonRef.current.remove();
    };
  }, [map, onSelect]);

  return (
    <div className="fixed bottom-4 left-1/2 z-[2100] -translate-x-1/2 rounded-lg bg-white p-3 shadow-lg">
      <p className="mb-2 text-sm">Кликните 4 точки на карте, чтобы задать область</p>
      <button onClick={onClose} className="rounded bg-gray-200 px-3 py-1 text-sm">
        Отменить
      </button>
    </div>
  );
}