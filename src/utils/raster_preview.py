import tempfile
import os
import numpy as np
from PIL import Image
from minio import Minio

def generate_preview_from_array(values, minio_client, bucket, tif_key, png_key, colormap='grayscale'):
    """
    Создаёт PNG-превью из массива значений (0..1) и сохраняет в MinIO.
    colormap: 'grayscale' (чёрно-белое) или 'heatmap' (красный-жёлтый-зелёный)
    """
    # Нормализация значений в диапазон 0..255
    vmin = 0.0
    vmax = 1.0
    normalized = (np.clip(values, vmin, vmax) - vmin) / (vmax - vmin) * 255
    normalized = np.nan_to_num(normalized).astype(np.uint8)
    
    if colormap == 'grayscale':
        # Одноканальное чёрно-белое изображение
        img = Image.fromarray(normalized, mode='L')
    elif colormap == 'heatmap':
        # RGB-изображение с переходом: красный (0) -> жёлтый (0.5) -> зелёный (1)
        # Формула: R = 255 * (1 - value) * 2 для value < 0.5, иначе R = 255 * (1 - (value - 0.5)*2) - так сложно.
        # Упрощённо: R = 255 * (1 - value), G = 255 * value, B = 0
        # При value=0: (255,0,0) красный; value=0.5: (128,128,0) оливковый; value=1: (0,255,0) зелёный.
        # Жёлтый получается при value=0.5? Нет, жёлтый = (255,255,0). Поэтому нужно скорректировать:
        # Используем линейную интерполяцию:
        # R = 255 * (1 - value) * 2, но не более 255
        # G = 255 * value * 2, не более 255
        # При value<0.5: R=255*(1-2*value), G=255*2*value, B=0 => от (255,0,0) до (0,255,0) через жёлтый (255,255,0) при value=0.5? Нет, при value=0.5 будет (0,255,0) - не жёлтый.
        # Лучше использовать стандартную цветовую карту: красный (0) -> жёлтый (0.5) -> зелёный (1)
        # Создадим три канала:
        # Красный: высокий при малых value, падает к 0 при value=0.5, затем 0
        # Зелёный: низкий при малых value, растёт до 255 при value=0.5, затем остаётся 255?
        # Жёлтый = красный+зелёный, поэтому пик жёлтого в середине.
        # Реализуем:
        r = np.where(values <= 0.5, 255, 255 * (1 - (values - 0.5) * 2))
        g = np.where(values <= 0.5, 255 * (values * 2), 255)
        b = np.zeros_like(values)
        # Приводим к uint8
        r = np.clip(r, 0, 255).astype(np.uint8)
        g = np.clip(g, 0, 255).astype(np.uint8)
        b = b.astype(np.uint8)
        rgb = np.stack([r, g, b], axis=-1)
        img = Image.fromarray(rgb, mode='RGB')
    else:
        raise ValueError(f"Unknown colormap: {colormap}")
    
    # Сохраняем во временный файл
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        tmp_path = tmp.name
        img.save(tmp_path, format='PNG')
    
    # Загружаем в MinIO
    minio_client.fput_object(bucket, png_key, tmp_path, content_type='image/png')
    os.unlink(tmp_path)
    
    return f"http://{minio_client._base_url.host}:9000/{bucket}/{png_key}"