# src/utils/vector_loader.py
import os
import glob
import logging
import geopandas as gpd
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session
from src.db.models import Layer

logger = logging.getLogger(__name__)


def discover_shapefiles(root_dir: str) -> list:
    """Рекурсивно находит все .shp файлы в указанной директории."""
    pattern = os.path.join(root_dir, "**", "*.shp")
    files = glob.glob(pattern, recursive=True)
    logger.info(f"Found {len(files)} shapefile(s) in {root_dir}")
    return files


def get_table_name(shp_path: str, base_dir: str) -> str:
    """
    Формирует имя таблицы из относительного пути.
    Пример: /app/data/vector/roads/major.shp -> roads_major
    """
    rel_path = os.path.relpath(shp_path, base_dir)
    # Убираем расширение .shp и заменяем разделители папок на _
    table_name = rel_path.replace(os.sep, '_').replace('.shp', '')
    return table_name


def load_shapefile_to_postgis(engine, shp_path: str, schema: str, table_name: str, if_exists: str = 'replace'):
    """Загружает один шейпфайл в PostGIS."""
    logger.info(f"Loading {shp_path} -> {schema}.{table_name}")
    try:
        gdf = gpd.read_file(shp_path)
    except Exception as e:
        logger.error(f"Failed to read {shp_path}: {e}")
        raise

    # Приводим к единой CRS (WGS84)
    if gdf.crs is None:
        logger.warning(f"No CRS for {table_name}, assuming EPSG:4326")
        gdf = gdf.set_crs("EPSG:4326")
    elif gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs("EPSG:4326")

    # Создаём схему, если не существует
    with engine.connect() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
        conn.commit()

    # Загружаем в БД
    gdf.to_postgis(
        name=table_name,
        con=engine,
        schema=schema,
        if_exists=if_exists,
        index=True,
        index_label='gid'
    )
    logger.info(f"Loaded {len(gdf)} features into {schema}.{table_name}")


def get_existing_tables(engine, schema: str) -> set:
    """Возвращает множество имён таблиц в указанной схеме."""
    inspector = inspect(engine)
    if schema in inspector.get_schema_names():
        return set(inspector.get_table_names(schema=schema))
    return set()


def load_all_vector_data(engine, data_dir: str, schema: str = "vector_data"):
    """Загружает все новые шейпфайлы, которых ещё нет в БД."""
    existing_tables = get_existing_tables(engine, schema)
    shp_files = discover_shapefiles(data_dir)
    loaded = []

    for shp_path in shp_files:
        table_name = get_table_name(shp_path, data_dir)
        if table_name in existing_tables:
            logger.debug(f"Table {schema}.{table_name} already exists, skipping.")
            continue

        try:
            load_shapefile_to_postgis(engine, shp_path, schema, table_name, if_exists='replace')
            loaded.append(table_name)
        except Exception as e:
            logger.error(f"Failed to load {shp_path}: {e}")

    if loaded:
        logger.info(f"Loaded new tables: {loaded}")
    else:
        logger.info("No new shapefiles to load.")
    return loaded


def register_all_vector_layers(engine, schema: str = "vector_data"):
    """
    Регистрирует все таблицы в схеме как слои в таблице layers,
    если они ещё не зарегистрированы.
    """
    session = Session(engine)
    inspector = inspect(engine)

    if schema not in inspector.get_schema_names():
        logger.warning(f"Schema {schema} does not exist, nothing to register.")
        session.close()
        return

    tables = inspector.get_table_names(schema=schema)
    registered_count = 0

    # SQL-запрос для определения типа геометрии каждой таблицы
    with engine.connect() as conn:
        for table in tables:
            full_path = f"{schema}.{table}"
            # Проверяем, есть ли уже слой с таким data_path
            existing = session.query(Layer).filter_by(data_path=full_path).first()
            if existing:
                continue

            # Получаем тип геометрии из системной таблицы geometry_columns
            result = conn.execute(
                text("""
                    SELECT type 
                    FROM geometry_columns 
                    WHERE f_table_schema = :schema AND f_table_name = :table
                """),
                {"schema": schema, "table": table}
            )
            row = result.fetchone()
            geometry_type = row[0] if row else "Unknown"

            # Преобразуем имя таблицы в читаемый вид: roads_major -> Roads Major
            readable_name = table.replace('_', ' ').title()

            layer = Layer(
                name=readable_name,
                source_type="postgis_vector",
                data_path=full_path,
                geometry_type=geometry_type,
                crs="EPSG:4326",   # все данные приведены к WGS84 при загрузке
                supported_analyses=["proximity"]
            )
            session.add(layer)
            registered_count += 1
            logger.info(f"Registered layer: {readable_name} ({full_path})")

    session.commit()
    session.close()
    logger.info(f"Registered {registered_count} new layer(s)")


def init_vector_data(engine, data_dir: str = "/app/data/vector", schema: str = "vector_data"):
    """
    Основная функция инициализации векторных данных.
    Вызывается из main.py.
    """
    logger.info("Initializing vector data...")
    # 1. Загружаем отсутствующие шейпфайлы
    load_all_vector_data(engine, data_dir, schema)
    # 2. Регистрируем все таблицы как слои (только новые)
    register_all_vector_layers(engine, schema)
    logger.info("Vector data initialization complete.")