# maininit.py
# Lógica para crear usuarios predeterminados vinculados por rol

from sqlalchemy.orm import Session
from .database import SessionLocal
from .models.rol_permiso import Rol
from .models.usuario import Usuario

# --------------------------------------------------------
# Sincronización de esquema (ADD/DROP columnas)
# --------------------------------------------------------
import logging
from sqlalchemy import inspect, text
from .database import engine, Base, SessionLocal

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
        print(f"Error al crear roles predeterminados: {e}")
    finally:
        db.close()

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
            "correo": "admin@pucp.edu.pe",
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
        roles_map = {rol.nombre: rol.id_rol for rol in db.query(Rol).all()}

        for info in usuarios_predeterminados:
            # Verifica que exista el rol
            if info["rol_nombre"] not in roles_map:
                continue
            id_rol = roles_map[info["rol_nombre"]]

            # Busca por correo (ideal: unique en columna 'correo')
            u = db.query(Usuario).filter(Usuario.correo == info["correo"]).first()
            if u is None:
                nuevo = Usuario(
                    nombres=info["nombres"],
                    dni=info["dni"],
                    correo=info["correo"],
                    celular=info["celular"],
                )
                db.add(nuevo)
            # Si necesitas asociar roles, usa la tabla de asociación usuario_rol
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error al crear usuarios predeterminados: {e}")
    finally:
        db.close()

def seed_defaults():
    """
    Ejecuta la siembra de datos predeterminados (usuarios, roles, permisos, etc.)
    """
    Base.metadata.create_all(bind=engine, checkfirst=True)
    sync_db_schema(drop_removed_columns=True)
    crear_roles_predeterminados()
    crear_usuarios_predeterminados()
    # Aquí puedes agregar otras funciones de seed si lo necesitas
