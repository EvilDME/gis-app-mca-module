import React from 'react';
import { ImageOverlay } from 'react-leaflet';
import useRasterDisplayStore from '../store/useRasterDisplayStore';
import L from 'leaflet';

export default function RasterPreviewOverlay() {
  const { displayRasterUrl, displayRasterBounds, displayResultId, displayRasterOpacity } = useRasterDisplayStore();

  if (!displayRasterUrl || !displayRasterBounds) return null;

  // Convert bbox from [minx, miny, maxx, maxy] to Leaflet format [[minY, minX], [maxY, maxX]]
  const bounds = L.latLngBounds(
    [displayRasterBounds[1], displayRasterBounds[0]],
    [displayRasterBounds[3], displayRasterBounds[2]]
  );

  console.log('[RasterPreviewOverlay] Rendering overlay:', {
    url: displayRasterUrl,
    bounds,
    opacity: displayRasterOpacity,
    key: displayResultId,
  });

  return (
    <ImageOverlay
      key={displayResultId}
      url={displayRasterUrl}
      bounds={bounds}
      opacity={displayRasterOpacity}
      zIndex={500}
    />
  );
}