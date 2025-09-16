from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import pymysql
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de conexión
DB_USER = "root"
DB_PASSWORD = "root"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "conciliacion"

# Función para crear la base de datos si no existe
def create_database_if_not_exists():
    try:
        # Conectar a MySQL sin especificar base de datos
        connection = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Verificar si la base de datos existe
            cursor.execute("SHOW DATABASES LIKE %s", (DB_NAME,))
            result = cursor.fetchone()
            
            if not result:
                # Crear la base de datos si no existe
                cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                logger.info(f"Base de datos '{DB_NAME}' creada exitosamente")
            else:
                logger.info(f"La base de datos '{DB_NAME}' ya existe")
        
        connection.close()
        
    except Exception as e:
        logger.error(f"Error al crear/verificar la base de datos: {str(e)}")
        raise

# Crear la base de datos si no existe
create_database_if_not_exists()

# URL de conexión a la base de datos específica
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Función para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
