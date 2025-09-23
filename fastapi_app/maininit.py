
import logging
from sqlalchemy.orm import Session
from sqlalchemy import insert, select, inspect, text
from .database import engine, Base, SessionLocal
from .models.rol_permiso import Rol, usuario_rol_association
from .models.usuario import Usuario
from .models.rol_permiso import Permiso

def seed_lovs():
    """
    Inserta los valores iniciales de los LOVs en las tablas correspondientes si no existen.
    """
    db: Session = SessionLocal()
    try:
        # Solicitud: tipoSolicitud y valorSolicitud
        from .models.solicitud import TipoSolicitud, ValorSolicitud
        tipo_solicitud_lovs = [
            "EXCLUSION_PROGRAMA", "ELIMINACION_BECADO", "EDICION_ALUMNO", "AGREGAR_ALUMNO",
            "APROBACION_JP", "APROBACION_COMERCIAL", "APROBACION_DAF"
        ]
        valor_solicitud_lovs = ["ACEPTADO", "REACHAZADO", "PENDIENTE"]
        existentes_tipo = {t.nombre for t in db.query(TipoSolicitud).all()}
        for nombre in tipo_solicitud_lovs:
            if nombre not in existentes_tipo:
                db.add(TipoSolicitud(nombre=nombre))
        existentes_valor = {v.nombre for v in db.query(ValorSolicitud).all()}
        for nombre in valor_solicitud_lovs:
            if nombre not in existentes_valor:
                db.add(ValorSolicitud(nombre=nombre))

        # Propuesta: tipoDePropuesta y estadoPropuesta
        from .models.propuesta import TipoDePropuesta, EstadoPropuesta
        tipo_propuesta_lovs = ["CREACION", "MODIFICACION"]
        estado_propuesta_lovs = ["PROGRAMADA", "GENERADA", "PRECONCILIADA", "APROBADA", "CONCILIADA", "CANCELADA"]
        existentes_tipo_p = {t.nombre for t in db.query(TipoDePropuesta).all()}
        for nombre in tipo_propuesta_lovs:
            if nombre not in existentes_tipo_p:
                db.add(TipoDePropuesta(nombre=nombre))
        existentes_estado_p = {e.nombre for e in db.query(EstadoPropuesta).all()}
        for nombre in estado_propuesta_lovs:
            if nombre not in existentes_estado_p:
                db.add(EstadoPropuesta(nombre=nombre))

        # Conciliacion: estadoConcilaciion
        from .models.conciliacion import EstadoConciliacion
        estado_conciliacion_lovs = ["GENERADA", "CANCELADA", "FINALIZADA"]
        existentes_estado_c = {e.nombre for e in db.query(EstadoConciliacion).all()}
        for nombre in estado_conciliacion_lovs:
            if nombre not in existentes_estado_c:
                db.add(EstadoConciliacion(nombre=nombre))

        db.commit()
        logging.info("LOVs inicializados correctamente.")
    except Exception as e:
        db.rollback()
        logging.error(f"Error al inicializar LOVs: {e}")
    finally:
        db.close()

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
                    nullable_sql = " NOT NULL" if (getattr(column, "nullable", True) is False) else ""
                    default_sql = ""
                    if getattr(column, "default", None) is not None and getattr(column.default, "arg", None) is not None:
                        raw = column.default.arg
                        default_sql = f" DEFAULT '{raw}'" if isinstance(raw, str) else f" DEFAULT {raw}"
                    ddl = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type}{nullable_sql}{default_sql};"
                    try:
                        with engine.begin() as conn:
                            conn.execute(text(ddl))
                        logging.info(f"Columna '{column_name}' añadida a '{table_name}'")
                    except Exception as e:
                        logging.error(f"Error añadiendo columna '{column_name}' a '{table_name}': {e}")

            # Eliminar columnas obsoletas
            if drop_removed_columns and removed_columns:
                logging.info(f"➖ {table_name}: columnas obsoletas detectadas: {removed_columns}")
                for column_name in removed_columns:
                    if column_name == 'id' or column_name.startswith('id_'):
                        logging.info(f"Saltando drop de columna protegida '{column_name}' en '{table_name}'")
                        continue
                    ddl = f"ALTER TABLE {table_name} DROP COLUMN {column_name};"
                    try:
                        with engine.begin() as conn:
                            conn.execute(text(ddl))
                        logging.info(f"Columna '{column_name}' eliminada de '{table_name}'")
                    except Exception as e:
                        logging.error(f"Error eliminando columna '{column_name}' de '{table_name}': {e}")
        else:
            # Crear tabla completa si no existe
            logging.info(f"🆕 Creando tabla '{table_name}'")
            table.create(engine, checkfirst=True)
    logging.info("✅ Sincronización de esquema finalizada.")




def crear_roles_predeterminados():
    roles = {
        "Administrador",
        "Comercial - Jefe de producto",
        "Comercial - Subdirector",
        "DAF - Subdirector",
        "DAF - Supervisor"
    }
    db: Session = SessionLocal()
    try:
        existentes = {rol.nombre for rol in db.query(Rol).all()}
        for nombre in roles:
            if nombre not in existentes:
                db.add(Rol(nombre=nombre))
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear roles predeterminados: {e}")
    finally:
        db.close()

def crear_usuarios_predeterminados():
    usuarios_predeterminados = [
        {
            "nombre": "daf.supervisor",
            "documentoIdentidad": None,
            "correo": "132465789@pucp.edu.pe",
            "rol_nombre": "DAF - Supervisor",
        },
        {
            "nombre": "daf.subdirector",
            "documentoIdentidad": None,
            "correo": "132465789-sub@pucp.edu.pe",
            "rol_nombre": "DAF - Subdirector",
        },
        {
            "nombre": "admin",
            "documentoIdentidad": None,
            "correo": "admin@pucp.edu.pe",
            "rol_nombre": "Administrador",
        },
        {
            "nombre": "Jefe grado",
            "documentoIdentidad": None,
            "correo": "jefe.grado@pucp.edu.pe",
            "rol_nombre": "Comercial - Subdirector",
        },
        {
            "nombre": "Jefe ee",
            "documentoIdentidad": None,
            "correo": "jefe.ee@pucp.edu.pe",
            "rol_nombre": "Comercial - Subdirector",
        },
        {
            "nombre": "Jefe CentrumX",
            "documentoIdentidad": None,
            "correo": "jefe.centrumx@pucp.edu.pe",
            "rol_nombre": "Comercial - Subdirector",
        },
    ]

    db: Session = SessionLocal()
    try:
        roles_map = {rol.nombre: rol.id for rol in db.query(Rol).all()}
        for info in usuarios_predeterminados:
            if info["rol_nombre"] not in roles_map:
                logging.warning(f"⚠️ Rol '{info['rol_nombre']}' no existe. Usuario '{info['nombre']}' no será creado.")
                continue
            id_rol = roles_map[info["rol_nombre"]]
            u = db.query(Usuario).filter(Usuario.correo == info["correo"]).first()
            if u is None:
                nuevo = Usuario(
                    nombre=info["nombre"],
                    documentoIdentidad=info["documentoIdentidad"],
                    correo=info["correo"],
                )
                db.add(nuevo)
                db.flush()
                usuario_id = nuevo.id
            else:
                usuario_id = u.id
            stmt = select(usuario_rol_association).where(
                usuario_rol_association.c.usuario_id == usuario_id,
                usuario_rol_association.c.rol_id == id_rol
            )
            existe = db.execute(stmt).fetchone()
            if not existe:
                db.execute(insert(usuario_rol_association).values(usuario_id=usuario_id, rol_id=id_rol))
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear usuarios predeterminados: {e}")
    finally:
        db.close()

def crearPermisosPredeterminados():
    permisos = [
        "BotonVerGeneracion",
        "BotonVerPreConciliacion",
        "BotonVerAprobacion",
        "BotonVerConciliacion",
        "BotonVerCancelacion",
        "BotonVerProgramacion",
        "BotonVerPuedeCancelarTodo",
        "TablaGeneracionEditar",
        "TablaPreConciliacionEditar",
        "BotonAgregarAlumnoPreConciliacion",
        "DisplayVerTodosRoles",
        "DisplayVerRolesSubComerciales",
    ]
    db: Session = SessionLocal()
    try:
        existentes = {p.descripcion for p in db.query(Permiso).all()}
        for descripcion in permisos:
            if descripcion not in existentes:
                db.add(Permiso(descripcion=descripcion))
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error al crear permisos predeterminados: {e}")
    finally:
        db.close()
def crearRolesPredeterminados():
    permisos_rol = {
        "Administrador": {
            "BotonVerGeneracion",
            "BotonVerPreConciliacion",
            "BotonVerAprobacion",
            "BotonVerConciliacion",
            "BotonVerCancelacion",
            "BotonVerProgramacion",
            "BotonVerPuedeCancelarTodo",
            "TablaGeneracionEditar",
            "TablaPreConciliacionEditar",
            "BotonAgregarAlumnoPreConciliacion",
            "DisplayVerTodosRoles",
            "DisplayVerRolesSubComerciales",
        },
        "Comercial - Jefe de producto": {
            "BotonVerPreConciliacion",
            "BotonVerAprobacion",
            "BotonVerConciliacion",
            "TablaPreConciliacionEditar",
            "BotonAgregarAlumnoPreConciliacion",
        },
        "Comercial - Subdirector": {
            "BotonVerPreConciliacion",
            "BotonVerAprobacion",
            "BotonVerConciliacion",
            "DisplayVerRolesSubComerciales",
        },
        "DAF - Subdirector": {
            "BotonVerGeneracion",
            "BotonVerPreConciliacion",
            "BotonVerAprobacion",
            "BotonVerConciliacion",
            "TablaGeneracionEditar",
        },
        "DAF - Supervisor": {
            "BotonVerGeneracion",
            "BotonVerPreConciliacion",
            "BotonVerAprobacion",
            "BotonVerConciliacion",
            "TablaGeneracionEditar",
        },
    }

    db: Session = SessionLocal()
    try:
        # Obtener todos los roles y permisos existentes
        roles_db = {r.nombre: r for r in db.query(Rol).all()}
        permisos_db = {p.descripcion: p for p in db.query(Permiso).all()}

        for rol_nombre, permisos_set in permisos_rol.items():
            rol = roles_db.get(rol_nombre)
            if not rol:
                continue
            for permiso_desc in permisos_set:
                permiso = permisos_db.get(permiso_desc)
                if permiso and permiso not in rol.permisos:
                    rol.permisos.append(permiso)
        db.commit()
    except Exception as e:
        db.rollback()
        logging.error(f"Error al asociar permisos a roles: {e}")
    finally:
        db.close()

def seed_defaults():
    """
    Ejecuta la siembra de datos predeterminados (usuarios, roles, permisos, etc.)
    """
    import time
    tiempos = {}
    total_start = time.time()

    start = time.time()
    Base.metadata.create_all(bind=engine, checkfirst=True)
    tiempos['create_all'] = time.time() - start
    logging.info(f"Tiempo create_all: {tiempos['create_all']:.4f} s")

    start = time.time()
    sync_db_schema(drop_removed_columns=True)
    tiempos['sync_db_schema'] = time.time() - start
    logging.info(f"Tiempo sync_db_schema: {tiempos['sync_db_schema']:.4f} s")

    start = time.time()
    crear_roles_predeterminados()
    tiempos['crear_roles_predeterminados'] = time.time() - start
    logging.info(f"Tiempo crear_roles_predeterminados: {tiempos['crear_roles_predeterminados']:.4f} s")

    start = time.time()
    crear_usuarios_predeterminados()
    tiempos['crear_usuarios_predeterminados'] = time.time() - start
    logging.info(f"Tiempo crear_usuarios_predeterminados: {tiempos['crear_usuarios_predeterminados']:.4f} s")

    start = time.time()
    crearPermisosPredeterminados()
    tiempos['crearPermisosPredeterminados'] = time.time() - start
    logging.info(f"Tiempo crearPermisosPredeterminados: {tiempos['crearPermisosPredeterminados']:.4f} s")

    start = time.time()
    crearRolesPredeterminados()
    tiempos['crearRolesPredeterminados'] = time.time() - start
    logging.info(f"Tiempo crearRolesPredeterminados: {tiempos['crearRolesPredeterminados']:.4f} s")

    start = time.time()
    seed_lovs()
    tiempos['seed_lovs'] = time.time() - start
    logging.info(f"Tiempo seed_lovs: {tiempos['seed_lovs']:.4f} s")

    total_time = time.time() - total_start
    logging.info(f"Tiempo total seed_defaults: {total_time:.4f} s")
