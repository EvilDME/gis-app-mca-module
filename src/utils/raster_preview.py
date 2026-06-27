import tempfile
import os
import numpy as np
from PIL import Image
from minio import Minio

def generate_preview_from_array(values, minio_client, bucket, tif_key, png_key, colormap='grayscale', nodata=None):
    """
    Создаёт PNG-превью из массива значений (0..1) и сохраняет в MinIO.
    nodata: значение, которое следует сделать прозрачным.
    """
    vmin = 0.0
    vmax = 1.0
    normalized = (np.clip(values, vmin, vmax) - vmin) / (vmax - vmin) * 255
    normalized = np.nan_to_num(normalized).astype(np.uint8)
    
    # Маска валидных значений (не nodata)
    if nodata is not None:
        valid_mask = ~np.isclose(values, nodata)
    else:
        valid_mask = np.ones_like(values, dtype=bool)
    alpha = np.where(valid_mask, 255, 0).astype(np.uint8)
    
    if colormap == 'grayscale':
        rgba = np.zeros((values.shape[0], values.shape[1], 4), dtype=np.uint8)
        rgba[:, :, 0] = normalized
        rgba[:, :, 1] = normalized
        rgba[:, :, 2] = normalized
        rgba[:, :, 3] = alpha
        img = Image.fromarray(rgba, mode='RGBA')
    elif colormap == 'heatmap':
        r = np.where(values <= 0.5, 255, 255 * (1 - (values - 0.5) * 2))
        g = np.where(values <= 0.5, 255 * (values * 2), 255)
        b = np.zeros_like(values)
        r = np.clip(r, 0, 255).astype(np.uint8)
        g = np.clip(g, 0, 255).astype(np.uint8)
        b = b.astype(np.uint8)
        rgba = np.stack([r, g, b, alpha], axis=-1)
        img = Image.fromarray(rgba, mode='RGBA')
    else:
        raise ValueError(f"Unknown colormap: {colormap}")
    
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp_path, format='PNG')
    
    minio_client.fput_object(bucket, png_key, tmp_path, content_type='image/png')
    os.unlink(tmp_path)
    
    return f"http://{minio_client._base_url.host}:9000/{bucket}/{png_key}"