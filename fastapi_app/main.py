# app/main.py
# -*- coding: utf-8 -*-

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from .database import engine, Base, SessionLocal

# Asegura el registro de TODOS los modelos antes de crear/sincronizar tablas
from .models import *  # noqa: F401,F403
from .models.rol_permiso import Rol, Permiso, RolPermiso
from .models.usuario import Usuario

# Routers
from .routers import (
    solicitudes_daf, usuario as usuario_router, cartera, oportunidad,
    tipo_cambio, conciliacion, propuesta, propuesta_programa,
    propuesta_oportunidad, solicitud, log, programa
)
from .routers import rol as rol_router, csv_upload, roles_usuarios_carteras, propuesta_programas
from .routers import solicitudes_jp, solicitudes_alumnos
from .routers.solicitudes_daf import programa_router as daf_programa_router

# --------------------------------------------------------
# Logging básico
# --------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --------------------------------------------------------
# Matriz de permisos por defecto (opcional). Puedes rellenarla.
# Formato: { "Nombre de Rol": {"permiso_a": True, "permiso_b": False, ...}, ... }
# --------------------------------------------------------
# --- Reemplaza SOLO este bloque en app/main.py ---

# Matriz de permisos por defecto (basada en tus dumps SQL)
# Nota: incluimos TODOS los permisos como claves por rol, aunque algunos estén en False,
# para que 'poblar_permisos_y_rol_permiso' cree/normalice la tabla 'permiso' de forma idempotente.
DEFAULT_MATRIZ_PERMISOS = {
    "Administrador": {
        "GENERADA": True,
        "PRECONCILIADA": True,
        "AUTORIZACION": True,
        "CONCILIADO": True,
        "CANCELADO": True,
        "puedeCancelar": True,
        "PROGRAMADA": True,
    },
    "Comercial - Jefe de producto": {
        "GENERADA": False,
        "PRECONCILIADA": True,
        "AUTORIZACION": False,
        "CONCILIADO": True,
        "CANCELADO": False,
        "puedeCancelar": False,
        "PROGRAMADA": False,
    },
    "Comercial - Subdirector": {
        "GENERADA": False,
        "PRECONCILIADA": True,
        "AUTORIZACION": True,
        "CONCILIADO": True,
        "CANCELADO": False,
        "puedeCancelar": False,
        "PROGRAMADA": False,
    },
    "DAF - Subdirector": {
        "GENERADA": True,
        "PRECONCILIADA": True,
        "AUTORIZACION": True,
        "CONCILIADO": True,
        "CANCELADO": False,
        "puedeCancelar": False,
        "PROGRAMADA": False,
    },
    "DAF - Supervisor": {
        "GENERADA": True,
        "PRECONCILIADA": True,
        "AUTORIZACION": False,
        "CONCILIADO": True,
        "CANCELADO": False,
        "puedeCancelar": False,
        "PROGRAMADA": False,
    },
}

# --- Catálogo de permisos (para que otro proceso lo consuma si desea poblar aparte)
PERMISOS_CATALOGO = [
    "GENERADA",
    "PRECONCILIADA",
    "AUTORIZACION",
    "CONCILIADO",
    "CANCELADO",
    "puedeCancelar",
    "PROGRAMADA",
]

def permisos_catalogo() -> list[str]:
    return list(PERMISOS_CATALOGO)

# --------------------------------------------------------
# Siembra de Permisos y Rol-Permiso
# --------------------------------------------------------
def poblar_permisos_y_rol_permiso(matriz_permisos: dict):
    """
    Pobla la tabla permiso y la tabla rol_permiso usando la matriz recibida como argumento.
    """
    db: Session = SessionLocal()
    try:
        # 1) Poblar tabla permiso (solo descripciones no existentes)
        permisos_unicos = set()
        for permisos in matriz_permisos.values():
            permisos_unicos.update(permisos.keys())

        permisos_existentes = {p.descripcion: p.id_permiso for p in db.query(Permiso).all()}
        for permiso in permisos_unicos:
            if permiso not in permisos_existentes:
                db.add(Permiso(descripcion=permiso))
        db.commit()

        # Refrescar cache de permisos
        permisos_existentes = {p.descripcion: p.id_permiso for p in db.query(Permiso).all()}

        # 2) Poblar tabla rol_permiso
        roles = {r.nombre: r.id_rol for r in db.query(Rol).all()}
        existentes = set((rp.id_rol, rp.id_permiso) for rp in db.query(RolPermiso).all())

        for rol_nombre, permisos in matriz_permisos.items():
            id_rol = roles.get(rol_nombre)
            if not id_rol:
                logging.warning(f"[permisos] Rol '{rol_nombre}' no existe; sáltalo o créalo primero.")
                continue

            for permiso_desc, habilitado in permisos.items():
                if not habilitado:
                    continue
                id_permiso = permisos_existentes.get(permiso_desc)
                if not id_permiso:
                    logging.warning(f"[permisos] Permiso '{permiso_desc}' no encontrado (rol '{rol_nombre}')")
                    continue
                par = (id_rol, id_permiso)
                if par not in existentes:
                    db.add(RolPermiso(id_rol=id_rol, id_permiso=id_permiso))
        db.commit()
        logging.info("✅ Permisos y relaciones rol-permiso poblados correctamente.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al poblar permisos y rol_permiso: {e}")
    finally:
        db.close()

# --------------------------------------------------------
# Sincronización de esquema (ADD/DROP columnas)
# --------------------------------------------------------
def sync_db_schema(drop_removed_columns: bool = True):
    """
    Sincroniza el esquema de la base de datos con los modelos SQLAlchemy.
    - Agrega columnas nuevas detectadas en los modelos
    - (Opcional) Elimina las columnas que ya no están en los modelos
    """
    logging.info("🔧 Iniciando sincronización de esquema…")
    inspector = inspect(engine)
    metadata = Base.metadata

    for table_name, table in metadata.tables.items():
        if inspector.has_table(table_name):
            # Columnas actuales en BD y en modelos
            columns_in_db = {col['name'] for col in inspector.get_columns(table_name)}
            columns_in_model = {col.name for col in table.columns}

            new_columns = columns_in_model - columns_in_db
            removed_columns = columns_in_db - columns_in_model

            # Agregar columnas nuevas
            if new_columns:
                logging.info(f"➕ {table_name}: nuevas columnas detectadas: {new_columns}")
                for column_name in new_columns:
                    column = next(col for col in table.columns if col.name == column_name)
                    col_type = column.type.compile(engine.dialect)

                    # Si el modelo declara nullable=False, añade NOT NULL
                    nullable_sql = " NOT NULL" if (getattr(column, "nullable", True) is False) else ""

                    default_sql = ""
                    if getattr(column, "default", None) is not None and getattr(column.default, "arg", None) is not None:
                        raw = column.default.arg
                        default_sql = f" DEFAULT '{raw}'" if isinstance(raw, str) else f" DEFAULT {raw}"

                    # ⚠️ Nota: Si la tabla ya tiene datos y agregas una columna NOT NULL sin DEFAULT, fallará
                    #          En ese caso, define DEFAULT en el modelo o agrega la columna como NULL, luego migra valores y cambia a NOT NULL.
                    ddl = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type}{nullable_sql}{default_sql};"
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                        logging.info(f"Columna '{column_name}' añadida a '{table_name}'")

            # Eliminar columnas obsoletas
            if drop_removed_columns and removed_columns:
                logging.info(f"➖ {table_name}: columnas obsoletas detectadas: {removed_columns}")
                for column_name in removed_columns:
                    # Seguridad básica: evita borrar PK/FK comunes por convención
                    if column_name == 'id' or column_name.startswith('id_'):
                        logging.info(f"Saltando drop de columna protegida '{column_name}' en '{table_name}'")
                        continue
                    ddl = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
                    with engine.begin() as conn:
                        conn.execute(text(ddl))
                        logging.info(f"Columna '{column_name}' eliminada de '{table_name}'")
        else:
            # Crear tabla completa si no existe
            logging.info(f"🆕 Creando tabla '{table_name}'")
            table.create(engine, checkfirst=True)

    logging.info("✅ Sincronización de esquema finalizada.")

# --------------------------------------------------------
# Roles por defecto
# --------------------------------------------------------
def crear_roles_predeterminados():
    roles_predeterminados = [
        "Comercial - Jefe de producto",
        "Comercial - Subdirector",
        "DAF - Supervisor",
        "DAF - Subdirector",
        "Administrador",
    ]

    db: Session = SessionLocal()
    try:
        existentes = {rol.nombre for rol in db.query(Rol).all()}
        for nombre in roles_predeterminados:
            if nombre not in existentes:
                db.add(Rol(nombre=nombre))
                logging.info(f"Creando rol predeterminado: {nombre}")
        db.commit()
        logging.info("✅ Roles predeterminados verificados/creados.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear roles predeterminados: {e}")
    finally:
        db.close()

# --------------------------------------------------------
# Usuarios por defecto (vinculados por id_rol)
# --------------------------------------------------------
def crear_usuarios_predeterminados():
    usuarios_predeterminados = [
        {
            "nombres": "daf.supervisor",
            "dni": None,
            "correo": "132465789@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "DAF - Supervisor",
        },
        {
            "nombres": "daf.subdirector",
            "dni": None,
            "correo": "132465789-sub@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "DAF - Subdirector",
        },
        {
            "nombres": "admin",
            "dni": None,
            "correo": "admin@pucp.edu.pe",  # <-- corregido (antes 'amdmin')
            "celular": None,
            "rol_nombre": "Administrador",
        },
        {
            "nombres": "Jefe grado",
            "dni": None,
            "correo": "jefe.grado@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",
        },
        {
            "nombres": "Jefe ee",
            "dni": None,
            "correo": "jefe.ee@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",
        },
        {
            "nombres": "Jefe CentrumX",
            "dni": None,
            "correo": "jefe.centrumx@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",
        },
    ]

    db: Session = SessionLocal()
    try:
        # Map de roles por nombre
        roles = {rol.nombre: rol.id_rol for rol in db.query(Rol).all()}

        for info in usuarios_predeterminados:
            # Verifica que exista el rol
            if info["rol_nombre"] not in roles:
                logging.warning(f"No se encontró el rol '{info['rol_nombre']}'. Crea los roles primero.")
                continue
            id_rol = roles[info["rol_nombre"]]

            # Busca por correo (ideal: unique en columna 'correo')
            u = db.query(Usuario).filter(Usuario.correo == info["correo"]).first()
            if u is None:
                # Inserta
                nuevo = Usuario(
                    dni=info["dni"],
                    correo=info["correo"],
                    nombres=info["nombres"],
                    celular=info["celular"],
                    id_rol=id_rol,
                )
                db.add(nuevo)
                logging.info(f"Creando usuario predeterminado: {info['nombres']} (rol_id={id_rol})")
            else:
                # Idempotencia: actualiza rol si difiere
                if u.id_rol != id_rol:
                    u.id_rol = id_rol
                    logging.info(f"Actualizando rol del usuario {info['nombres']} a rol_id={id_rol}")
        db.commit()
        logging.info("✅ Usuarios predeterminados verificados/creados/actualizados.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear usuarios predeterminados: {e}")
    finally:
        db.close()

# --------------------------------------------------------
# Seed compuesto (esquema + roles + permisos + usuarios)
# --------------------------------------------------------
def seed_defaults():
    Base.metadata.create_all(bind=engine, checkfirst=True)
    sync_db_schema(drop_removed_columns=True)
    crear_roles_predeterminados()
    poblar_permisos_y_rol_permiso(DEFAULT_MATRIZ_PERMISOS)
    crear_usuarios_predeterminados()

# --------------------------------------------------------
# Lifespan (se ejecuta en startup/shutdown)
# --------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 Startup: ejecutando seed (roles/usuarios/permisos)…")
    seed_defaults()
    yield
    logging.info("🛑 Shutdown")

# --------------------------------------------------------
# App FastAPI
# --------------------------------------------------------
app = FastAPI(
    title="API de Conciliación",
    description="API para gestionar procesos de conciliación y propuestas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(usuario_router.router)
app.include_router(cartera.router)
app.include_router(oportunidad.router)
app.include_router(tipo_cambio.router)
app.include_router(conciliacion.router)
app.include_router(propuesta.router)
app.include_router(propuesta_programa.router)
app.include_router(propuesta_oportunidad.router)
app.include_router(solicitud.router)
app.include_router(rol_router.router)
app.include_router(log.router)
app.include_router(programa.router)
app.include_router(csv_upload.router, tags=["CSV Upload"])
app.include_router(roles_usuarios_carteras.router)
app.include_router(propuesta_programas.router, tags=["Propuesta"])
app.include_router(solicitudes_daf.router)
app.include_router(solicitudes_jp.router)
app.include_router(daf_programa_router)            # DAF
app.include_router(solicitudes_alumnos.router)     # Solicitudes Alumnos

# --------------------------------------------------------
# Endpoints utilitarios
# --------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "FastAPI backend running"}

@app.get("/matriz-permisos")
def get_matriz_permisos():
    """
    Devuelve la matriz de permisos por rol y permiso, con true/false según la relación.
    """
    db: Session = SessionLocal()
    try:
        roles = db.query(Rol).all()
        permisos = db.query(Permiso).all()
        rol_permisos = db.query(RolPermiso).all()

        relaciones = set((rp.id_rol, rp.id_permiso) for rp in rol_permisos)

        matriz = {}
        for rol in roles:
            matriz[rol.nombre] = {}
            for permiso in permisos:
                matriz[rol.nombre][permiso.descripcion] = ((rol.id_rol, permiso.id_permiso) in relaciones)
        return matriz
    finally:
        db.close()

@app.get("/permisos/catalogo", tags=["Admin"])
def get_permisos_catalogo():
    """
    Devuelve únicamente el catálogo de permisos soportados por el sistema.
    Útil para que otro proceso los consuma y pueble/valide.
    """
    return {"permisos": PERMISOS_CATALOGO, "total": len(PERMISOS_CATALOGO)}

@app.get("/debug/usuarios")
def debug_usuarios():
    """
    Endpoint temporal para depurar los usuarios existentes
    """
    db: Session = SessionLocal()
    try:
        roles = {rol.id_rol: rol.nombre for rol in db.query(Rol).all()}
        usuarios = db.query(Usuario).all()

        resultado = []
        for u in usuarios:
            resultado.append({
                "id": u.id_usuario,
                "nombres": u.nombres,
                "dni": u.dni,
                "correo": u.correo,
                "celular": u.celular,
                "id_rol": u.id_rol,
                "rol_nombre": roles.get(u.id_rol, "Rol desconocido"),
            })
        return {"total": len(resultado), "usuarios": resultado}
    finally:
        db.close()

@app.post("/admin/seed", tags=["Admin"])
def reseed():
    """
    Fuerza la re-siembra de esquema/roles/permisos/usuarios sin reiniciar la app.
    Útil en desarrollo.
    """
    seed_defaults()
    return {"ok": True, "message": "Seed ejecutado"}
