from fastapi import APIRouter

# (Aquí va el resto del código original que estaba antes del endpoint, sin cambios)
# Función para poblar la tabla permiso y rol_permiso desde la MATRIZ_PERMISOS
def poblar_permisos_y_rol_permiso(matriz_permisos):
    """
    Pobla la tabla permiso y la tabla rol_permiso usando la matriz recibida como argumento.
    """
    from sqlalchemy.orm import Session
    from .models.rol_permiso import Rol, Permiso, RolPermiso
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # 1. Poblar tabla permiso
        permisos_unicos = set()
        for permisos in matriz_permisos.values():
            permisos_unicos.update(permisos.keys())
        permisos_existentes = {p.descripcion: p.id_permiso for p in db.query(Permiso).all()}
        for permiso in permisos_unicos:
            if permiso not in permisos_existentes:
                nuevo_permiso = Permiso(descripcion=permiso)
                db.add(nuevo_permiso)
        db.commit()
        # Actualizar permisos_existentes con los nuevos ids
        permisos_existentes = {p.descripcion: p.id_permiso for p in db.query(Permiso).all()}

        # 2. Poblar tabla rol_permiso
        roles = {r.nombre: r.id_rol for r in db.query(Rol).all()}
        rol_permiso_existentes = set((rp.id_rol, rp.id_permiso) for rp in db.query(RolPermiso).all())
        for rol_nombre, permisos in matriz_permisos.items():
            id_rol = roles.get(rol_nombre)
            if not id_rol:
                continue
            for permiso, habilitado in permisos.items():
                if habilitado:
                    id_permiso = permisos_existentes.get(permiso)
                    if id_permiso and (id_rol, id_permiso) not in rol_permiso_existentes:
                        db.add(RolPermiso(id_rol=id_rol, id_permiso=id_permiso))
        db.commit()
        logging.info("Permisos y relaciones rol-permiso poblados correctamente desde la matriz.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al poblar permisos y rol_permiso: {str(e)}")
    finally:
        db.close()

import logging
from .database import engine, Base
from sqlalchemy import inspect, text

# Importamos los modelos usando el nuevo __init__.py que controla el orden
from .models import *  # Ahora el orden está controlado por __init__.py

# Función para sincronizar el esquema de la base de datos automáticamente
def sync_db_schema(drop_removed_columns=True):
    """
    Sincroniza el esquema de la base de datos con los modelos SQLAlchemy.
    - Detecta columnas nuevas en los modelos y las agrega a las tablas existentes
    - Opcionalmente elimina columnas que ya no están en los modelos
    
    Args:
        drop_removed_columns (bool): Si es True, elimina columnas que ya no están en los modelos
    """
    inspector = inspect(engine)
    metadata = Base.metadata
    
    for table_name, table in metadata.tables.items():
        if inspector.has_table(table_name):
            # La tabla existe, comprueba las columnas
            columns_in_db = {col['name'] for col in inspector.get_columns(table_name)}
            columns_in_model = {col.name for col in table.columns}
            
            # Encuentra columnas en el modelo que no están en la BD
            new_columns = columns_in_model - columns_in_db
            
            # Encuentra columnas en la BD que ya no están en el modelo
            removed_columns = columns_in_db - columns_in_model
            
            # Agrega columnas nuevas
            if new_columns:
                logging.info(f"Detectadas nuevas columnas en {table_name}: {new_columns}")
                
                # Añade cada columna nueva
                for column_name in new_columns:
                    column = next(col for col in table.columns if col.name == column_name)
                    
                    # Prepara el tipo de columna para SQL
                    col_type = column.type.compile(engine.dialect)
                    nullable = "" if column.nullable else " NOT NULL"
                    default = f" DEFAULT {column.default.arg}" if column.default is not None and column.default.arg is not None else ""
                    
                    # Ejecuta la alteración de tabla
                    with engine.connect() as conn:
                        sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type}{nullable}{default};")
                        conn.execute(sql)
                        conn.commit()
                        logging.info(f"Columna {column_name} añadida a {table_name}")
            
            # Elimina columnas que ya no están en el modelo
            if drop_removed_columns and removed_columns:
                logging.info(f"Detectadas columnas eliminadas en el modelo para {table_name}: {removed_columns}")
                
                # Elimina cada columna que ya no existe en el modelo
                for column_name in removed_columns:
                    # No eliminamos columnas clave primaria o clave foránea por seguridad
                    if column_name != 'id' and not column_name.startswith('id_'):
                        with engine.connect() as conn:
                            sql = text(f"ALTER TABLE {table_name} DROP COLUMN {column_name};")
                            conn.execute(sql)
                            conn.commit()
                            logging.info(f"Columna {column_name} eliminada de {table_name}")
        else:
            # La tabla no existe, créala
            logging.info(f"Creando tabla {table_name}")
            table.create(engine)

# Primero creamos todas las tablas necesarias
try:
    # Crear las tablas en el orden correcto
    Base.metadata.create_all(bind=engine, checkfirst=True)
    logging.info("Tablas creadas correctamente en el primer intento")
except Exception as e:
    logging.warning(f"Error al crear tablas en el primer intento: {str(e)}")
    try:
        # Si falla, intentamos una segunda vez después de que todas las clases estén cargadas
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logging.info("Tablas creadas correctamente en el segundo intento")
    except Exception as e2:
        logging.error(f"Error al crear tablas en el segundo intento: {str(e2)}")

# Sincronizamos el esquema para agregar columnas nuevas o eliminar obsoletas
sync_db_schema(drop_removed_columns=True)

# Función para crear los roles predeterminados si no existen
def crear_roles_predeterminados():
    from sqlalchemy.orm import Session
    from .models.rol_permiso import Rol
    from .database import SessionLocal
    
    # Roles predeterminados que queremos asegurar que existan
    roles_predeterminados = [
        "Comercial - Jefe de producto",
        "Comercial - Subdirector",
        "DAF - Supervisor",
        "DAF - Subdirector",
        "Administrador"
    ]
    
    db = SessionLocal()
    try:
        # Obtener los nombres de roles existentes
        roles_existentes = [rol.nombre for rol in db.query(Rol).all()]
        
        # Crear los roles que no existen
        for nombre_rol in roles_predeterminados:
            if nombre_rol not in roles_existentes:
                nuevo_rol = Rol(nombre=nombre_rol)
                db.add(nuevo_rol)
                logging.info(f"Creando rol predeterminado: {nombre_rol}")
        
        # Guardar cambios en la base de datos
        db.commit()
        logging.info("Roles predeterminados verificados/creados con éxito")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear roles predeterminados: {str(e)}")
    finally:
        db.close()



# Función para crear usuarios predeterminados vinculados a los roles por id_rol
def crear_usuarios_predeterminados():
    from sqlalchemy.orm import Session
    from .models.usuario import Usuario
    from .models.rol_permiso import Rol
    from .database import SessionLocal
    
    # Configuración de usuarios predeterminados
    usuarios_predeterminados = [
        {
            "nombres": "daf.supervisor",
            "dni": None,
            "correo": "132465789@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "DAF - Supervisor",  # Nombre del rol al que estará vinculado
        },
        {
            "nombres": "daf.subdirector",
            "dni": None,
            "correo": "132465789-sub@pucp.edu.pe",
            "celular": None, 
            "rol_nombre": "DAF - Subdirector",  # Nombre del rol al que estará vinculado
        },
        {
            "nombres": "admin",
            "dni": None,
            "correo": "amdmin@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Administrador",  # Nombre del rol al que estará vinculado
        },
        {
            "nombres": "Jefe grado",
            "dni": None,
            "correo": "jefe.grado@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",  # Nombre del rol al que estará vinculado
        },
        {
            "nombres": "Jefe ee",
            "dni": None,
            "correo": "jefe.ee@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",  # Nombre del rol al que estará vinculado
        },
        {
            "nombres": "Jefe CentrumX",
            "dni": None,
            "correo": "jefe.centrumx@pucp.edu.pe",
            "celular": None,
            "rol_nombre": "Comercial - Subdirector",  # Nombre del rol al que estará vinculado
        }
    ]
    
    db = SessionLocal()
    try:
        # Obtener todos los roles existentes
        roles = {rol.nombre: rol.id_rol for rol in db.query(Rol).all()}
        
        # Verificar cada usuario predeterminado
        for usuario_info in usuarios_predeterminados:
            # Verificar si el usuario ya existe por correo
            usuario_existente = db.query(Usuario).filter(Usuario.correo == usuario_info["correo"]).first()

            # Verificar si existe el rol necesario
            if usuario_info["rol_nombre"] not in roles:
                logging.warning(f"No se encontró el rol '{usuario_info['rol_nombre']}'. Asegúrate de que los roles existan primero.")
                continue

            id_rol = roles[usuario_info["rol_nombre"]]

            if not usuario_existente:
                # Crear el usuario si no existe, vinculándolo al id_rol correspondiente
                nuevo_usuario = Usuario(
                    dni=usuario_info["dni"],
                    correo=usuario_info["correo"],
                    nombres=usuario_info["nombres"],
                    celular=usuario_info["celular"],
                    id_rol=id_rol  # Asignar el id del rol, no el nombre
                    # El campo cartera ahora es una relación muchos-a-muchos
                )
                db.add(nuevo_usuario)
                logging.info(f"Creando usuario predeterminado: {usuario_info['nombres']} con rol_id {id_rol}")
            else:
                # Actualizar el id_rol si el usuario ya existe pero tiene un rol diferente
                if usuario_existente.id_rol != id_rol:
                    usuario_existente.id_rol = id_rol
                    logging.info(f"Actualizando rol del usuario {usuario_info['nombres']} a rol_id {id_rol}")
        
        # Guardar cambios en la base de datos
        db.commit()
        logging.info("Usuarios predeterminados verificados/creados con éxito")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear usuarios predeterminados: {str(e)}")
    finally:
        db.close()

# (Aquí va el resto del código original que estaba después de crear_usuarios_predeterminados(), sin cambios)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import (
    solicitudes_daf, usuario, cartera, oportunidad, tipo_cambio, conciliacion,
    propuesta, propuesta_programa, propuesta_oportunidad, solicitud,log, programa
)
# Import DAF routers from solicitudes_daf.py
from .routers.solicitudes_daf import programa_router as daf_programa_router

# Importamos los routers
from .routers import rol, csv_upload, roles_usuarios_carteras, propuesta_programas

# Configuración de la aplicación FastAPI con metadatos para mejorar Swagger
app = FastAPI(
    title="API de Conciliación",
    description="API para gestionar procesos de conciliación y propuestas",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS para permitir solicitudes desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(usuario.router)
app.include_router(cartera.router)
app.include_router(oportunidad.router)
app.include_router(tipo_cambio.router)
app.include_router(conciliacion.router)
app.include_router(propuesta.router)
app.include_router(propuesta_programa.router)
app.include_router(propuesta_oportunidad.router)
app.include_router(solicitud.router)
app.include_router(rol.router)
app.include_router(log.router)
app.include_router(programa.router)
app.include_router(csv_upload.router, tags=["CSV Upload"])
app.include_router(roles_usuarios_carteras.router)
app.include_router(propuesta_programas.router, tags=["Propuesta"])
app.include_router(solicitudes_daf.router)
# Include DAF routers 
app.include_router(daf_programa_router)
# Include Solicitudes Pre-Conciliacion router
from .routers.solicitudes_pre_conciliacion import router as solicitudes_pre_conciliacion_router
app.include_router(solicitudes_pre_conciliacion_router)
# Endpoint para obtener la matriz de permisos por rol
@app.get("/matriz-permisos")
async def get_matriz_permisos():
    """
    Devuelve la matriz de permisos por rol y permiso, con true/false según la relación en la base de datos.
    """
    from sqlalchemy.orm import Session
    from .models.rol_permiso import Rol, Permiso, RolPermiso
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # Obtener todos los roles y permisos
        roles = db.query(Rol).all()
        permisos = db.query(Permiso).all()
        rol_permisos = db.query(RolPermiso).all()

        # Mapear relaciones existentes (id_rol, id_permiso)
        relaciones = set((rp.id_rol, rp.id_permiso) for rp in rol_permisos)

        # Construir matriz: {rol_nombre: {permiso: true/false, ...}, ...}
        matriz = {}
        for rol in roles:
            matriz[rol.nombre] = {}
            for permiso in permisos:
                tiene_permiso = (rol.id_rol, permiso.id_permiso) in relaciones
                matriz[rol.nombre][permiso.descripcion] = tiene_permiso
        return matriz
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "FastAPI backend running"}

@app.get("/debug/usuarios")
async def debug_usuarios():
    """
    Endpoint temporal para depurar los usuarios existentes
    """
    from sqlalchemy.orm import Session
    from .models.usuario import Usuario
    from .models.rol_permiso import Rol
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        # Obtener todos los roles
        roles = {rol.id_rol: rol.nombre for rol in db.query(Rol).all()}
        
        # Obtener todos los usuarios
        usuarios = db.query(Usuario).all()
        
        # Preparar la respuesta
        resultado = []
        for usuario in usuarios:
            resultado.append({
                "id": usuario.id_usuario,
                "nombres": usuario.nombres,
                "dni": usuario.dni,
                "correo": usuario.correo,
                "celular": usuario.celular,
                "id_rol": usuario.id_rol,
                "rol_nombre": roles.get(usuario.id_rol, "Rol desconocido"),
            })
            
        return {"total": len(resultado), "usuarios": resultado}
    finally:
        db.close()
