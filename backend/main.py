from fastapi import FastAPI
from backend.routers import facturas

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hola, backend listo!"}

# Incluir el router de facturas
app.include_router(facturas.router)