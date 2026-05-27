import os
import tempfile
import logging
from minio import Minio
from minio.error import S3Error
import rasterio
from src.core.models import RasterData
from src.io.interfaces import BaseRasterReader

logger = logging.getLogger(__name__)


class MinIORasterReader(BaseRasterReader):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str, secure: bool = False):
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.bucket = bucket

    def read_raster(self, source: str) -> RasterData:
        """
        source: ключ объекта в MinIO (например, 'sources/dem.tif')
        """
        try:
            # Скачиваем во временный файл
            with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp:
                tmp_path = tmp.name
            self.client.fget_object(self.bucket, source, tmp_path)
            logger.debug(f"Downloaded {self.bucket}/{source} to {tmp_path}")

            # Читаем через rasterio
            with rasterio.open(tmp_path) as src:
                values = src.read(1)
                meta = src.profile.copy()
                name = os.path.splitext(os.path.basename(source))[0]

            # Удаляем временный файл
            os.unlink(tmp_path)

            return RasterData(values=values, meta=meta, name=name)

        except S3Error as e:
            raise RuntimeError(f"MinIO error reading {self.bucket}/{source}: {e}")
        except Exception as e:
            raise RuntimeError(f"Error reading raster from MinIO: {e}")