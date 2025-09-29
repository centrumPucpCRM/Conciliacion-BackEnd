import logging
from .routers import log
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .maininit import seed_defaults
from fastapi_pagination import add_pagination
from .routers import usuario as usuario_router, cartera, oportunidad, tipo_cambio, conciliacion, propuesta, programa, solicitud, log
from .routers import csv_loader
from .routers import dashboard
from .routers import informacion_preconciliacion


# Configura logging para mostrar en consola
import sys
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 Startup: ejecutando seed (roles/usuarios/permisos)…")
    seed_defaults()
    yield
    logging.info("🛑 Shutdown")

app = FastAPI(
    title="API de Conciliación",
    description="API para gestionar procesos de conciliación y propuestas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuario_router.router)
app.include_router(cartera.router)
app.include_router(oportunidad.router)
# app.include_router(tipo_cambio.router)
# app.include_router(conciliacion.router)
app.include_router(propuesta.router)
# app.include_router(programa.router)
app.include_router(solicitud.router)
# app.include_router(log.router)
from .routers import rol as rol_router
app.include_router(rol_router.router)
app.include_router(csv_loader.router, tags=["CSV Loader"])
app.include_router(dashboard.router)
app.include_router(informacion_preconciliacion.router)
app.include_router(log.router)
# app.include_router(roles_usuarios_carteras.router)
# app.include_router(propuesta_programas.router, tags=["Propuesta"])
# app.include_router(solicitudes_pre_conciliacion_router)
# app.include_router(daf_programa_router)

# Habilitar fastapi-pagination en la app
add_pagination(app)

