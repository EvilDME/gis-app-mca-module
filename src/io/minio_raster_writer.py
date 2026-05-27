import os
import tempfile
import logging
from minio import Minio
from minio.error import S3Error
import rasterio
from src.core.models import RasterData
from src.io.interfaces import BaseRasterWriter

logger = logging.getLogger(__name__)


class MinIORasterWriter(BaseRasterWriter):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket = bucket
        # Убедимся, что бакет существует
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)
            logger.info(f"Created bucket: {bucket}")

    def write_raster(self, raster: RasterData, destination: str) -> None:
        """
        destination: ключ объекта в MinIO (например, 'results/suitability/eco.tif')
        """
        try:
            # Сохраняем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                tmp_path = tmp.name

            meta = raster.meta.copy()
            meta.update({
                'driver': 'GTiff',
                'count': 1,
                'dtype': raster.values.dtype
            })

            with rasterio.open(tmp_path, 'w', **meta) as dst:
                dst.write(raster.values, 1)

            # Загружаем в MinIO
            self.client.fput_object(
                self.bucket, destination, tmp_path,
                content_type='image/tiff'
            )
            logger.info(f"Uploaded to {self.bucket}/{destination}")

            # Удаляем временный файл
            os.unlink(tmp_path)

        except S3Error as e:
            raise RuntimeError(f"MinIO error writing to {self.bucket}/{destination}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error writing raster to MinIO: {e}")