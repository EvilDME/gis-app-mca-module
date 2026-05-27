# src/io/postgis_vector_reader.py
import logging
import geopandas as gpd
from sqlalchemy import create_engine, text
from src.io.interfaces import BaseVectorReader

logger = logging.getLogger(__name__)


class PostGISVectorReader(BaseVectorReader):
    """
    Чтение векторных данных из PostGIS.
    Поддерживает полные имена: 'schema.table' или просто 'table' (будет искаться в public).
    """
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def _get_geometry_column(self, schema: str, table: str) -> str:
        """
        Определяет имя геометрической колонки в таблице.
        Приоритет: первая колонка типа geometry.
        """
        query = text("""
            SELECT f_geometry_column 
            FROM geometry_columns 
            WHERE f_table_schema = :schema AND f_table_name = :table
        """)
        with self.engine.connect() as conn:
            result = conn.execute(query, {"schema": schema, "table": table})
            row = result.fetchone()
            if row:
                return row[0]
        # Если не нашли в geometry_columns, пробуем найти колонку с геометрией через дескриптор
        sample = gpd.read_postgis(f"SELECT * FROM {schema}.{table} LIMIT 1", self.engine)
        if sample.geometry.name:
            return sample.geometry.name
        raise ValueError(f"No geometry column found in {schema}.{table}")

    def read_vector(self, source: str) -> gpd.GeoDataFrame:
        """
        source: строка вида 'schema.table_name' или 'table_name'.
        Возвращает GeoDataFrame в исходной CRS (как сохранено в БД).
        """
        if '.' in source:
            schema, table = source.split('.', 1)
        else:
            schema = 'public'
            table = source

        logger.debug(f"Reading vector data from {schema}.{table}")

        try:
            # Определяем колонку геометрии
            geom_col = self._get_geometry_column(schema, table)
            query = f"SELECT * FROM {schema}.{table}"
            gdf = gpd.read_postgis(query, self.engine, geom_col=geom_col)
            logger.info(f"Loaded {len(gdf)} features from {schema}.{table} (geometry: {geom_col})")
            return gdf
        except Exception as e:
            raise RuntimeError(f"Error reading vector from {schema}.{table}: {e}")