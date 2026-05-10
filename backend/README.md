# Factura App Backend

Este proyecto es un backend construido con **FastAPI** y organizado en un entorno virtual administrado con `uv`.

---

## 🚀 Preparación del entorno

1. **Instalar Python**
   - Descarga la versión oficial desde [python.org](https://www.python.org/downloads/windows/).
   - Durante la instalación, marca la casilla **Add Python to PATH**.

2. **Crear entorno virtual**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
    ```
    
3. **Instalar uv en el entorno**
    ```powershell
    pip install uv
    ```

4. **Iniciar proyecto**
    ```powershell
    python -m uv init factura-app
    ```

5. **Instalar librerias por grupos**
    - Para `backend`:
    ```powershell
    python -m uv add fastapi uvicorn sqlalchemy cryptography requests --group backend
    ```

    - Para `infraestructura`:
    ```powershell
    python -m uv add docker-compose --group infra
    ```

    - Para `frontend`:
    ```powershell
    python -m uv add docker-compose --group infra
    ```

6. **Instalar un grupo en el entorno**
    ```powershell
    python -m uv pip install -g backend
    ```

7. **Correr backend local**
    Correr las APIs con FastAPI:
    ```powershell
    uvicorn backend.main:app --reload
    ```