# GIS Analytics Project (MCA Module)

Проект для мультикритериального анализа геоданных (растры высот, дорожные сети, реки).

## Как запустить проект (Windows)

1. **Создайте виртуальное окружение** (используем Python 3.12):
   ```bash
   py -3.12 -m venv venv
   ```

2. **Активируйте окружение**:
   ```bash
   .\venv\Scripts\Activate.ps1
   ```

3. **Установите зависимости**:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Проверьте окружение**:
   Запустите проверочный скрипт (например, `check_env.py`), чтобы убедиться, что библиотеки `rasterio` и `pyproj` видят базу данных координат.