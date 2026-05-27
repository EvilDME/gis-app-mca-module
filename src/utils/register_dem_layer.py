import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.db.models import Layer
import uuid

def register_dem_layer():
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    session = Session(engine)

    # Проверим, не зарегистрирован ли уже слой с таким именем
    existing = session.query(Layer).filter_by(name="UFA_SRTM").first()
    if existing:
        print("DEM layer already registered")
        return

    layer = Layer(
        id=uuid.uuid4(),
        name="UFA_SRTM",
        source_type="minio_raster",
        data_path="sources/dem.tif",   # ключ в MinIO (без bucket)
        geometry_type="Raster",         # для растров
        crs="EPSG:4326",                # укажите реальную CRS вашего ЦМР
        supported_analyses=["slope"]    # какие типы анализа поддерживает
        # extent и resolution можно заполнить позже
    )
    session.add(layer)
    session.commit()
    print("DEM layer registered")

if __name__ == "__main__":
    register_dem_layer()