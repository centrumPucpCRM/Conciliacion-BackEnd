"""
Script para poblar la base de datos con los archivos SQL de la carpeta db
"""
import os
import sys
import pymysql
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuración de conexión (usa las mismas credenciales que database.py)
DB_USER = "root"
DB_PASSWORD = "root"
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "conciliacion"

def execute_sql_file(file_path, connection):
    """
    Ejecuta un archivo SQL específico
    """
    logger.info(f"Ejecutando archivo SQL: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as sql_file:
            sql_content = sql_file.read()
            
        # Dividir el contenido SQL en declaraciones individuales
        # Eliminar comentarios y líneas vacías para procesar mejor
        statements = []
        current_statement = ""
        
        for line in sql_content.split('\n'):
            line = line.strip()
            
            # Saltar comentarios y líneas vacías
            if line.startswith('--') or line.startswith('/*') or line.startswith('*/') or line.startswith('/*!') or not line:
                continue
                
            current_statement += line + " "
            
            # Si la línea termina con ';', es el final de una declaración
            if line.endswith(';'):
                statements.append(current_statement.strip())
                current_statement = ""
        
        # Ejecutar cada declaración
        with connection.cursor() as cursor:
            for statement in statements:
                if statement and not statement.isspace():
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        # Algunos comandos como LOCK TABLES pueden fallar en ciertos contextos
                        # Registramos el error pero continuamos
                        logger.warning(f"Error ejecutando declaración en {file_path}: {str(e)}")
                        logger.warning(f"Declaración problemática: {statement[:100]}...")
        
        connection.commit()
        logger.info(f"Archivo {file_path} ejecutado exitosamente")
        
    except Exception as e:
        logger.error(f"Error ejecutando archivo {file_path}: {str(e)}")
        connection.rollback()
        raise

def populate_database():
    """
    Pobla la base de datos con todos los archivos SQL de la carpeta db
    """
    # Directorio donde están los archivos SQL
    db_folder = Path(__file__).parent / "db"
    
    if not db_folder.exists():
        logger.error(f"La carpeta {db_folder} no existe")
        return False
    
    # Obtener todos los archivos SQL
    sql_files = list(db_folder.glob("*.sql"))
    
    if not sql_files:
        logger.error(f"No se encontraron archivos SQL en {db_folder}")
        return False
    
    logger.info(f"Encontrados {len(sql_files)} archivos SQL")
    
    # Ordenar los archivos para ejecutarlos en un orden lógico
    # Primero las tablas básicas, luego las que tienen dependencias
    order_priority = {
        'rol': 1,
        'permiso': 2,
        'rol_permiso': 3,
        'cartera': 4,
        'usuario': 5,
        'usuario_cartera': 6,
        'programa': 7,
        'oportunidad': 8,
        'tipo_cambio': 9,
        'propuesta': 10,
        'propuesta_programa': 11,
        'propuesta_oportunidad': 12,
        'solicitud': 13,
        'solicitud_propuesta_programa': 14,
        'solicitud_propuesta_oportunidad': 15,
        'conciliacion': 16,
        'conciliacion_programa': 17,
        'log': 18
    }
    
    def get_file_priority(file_path):
        # Extraer el nombre de la tabla del nombre del archivo
        file_name = file_path.stem
        table_name = file_name.replace('conciliacion_', '')
        return order_priority.get(table_name, 999)
    
    sql_files.sort(key=get_file_priority)
    
    try:
        # Conectar a la base de datos
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset='utf8mb4'
        )
        
        logger.info(f"Conectado a la base de datos {DB_NAME}")
        
        # Deshabilitar checks de foreign key temporalmente para evitar problemas de orden
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        
        # Ejecutar cada archivo SQL
        for sql_file in sql_files:
            execute_sql_file(sql_file, connection)
        
        # Rehabilitar checks de foreign key
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        
        connection.close()
        logger.info("¡Base de datos poblada exitosamente!")
        return True
        
    except Exception as e:
        logger.error(f"Error poblando la base de datos: {str(e)}")
        return False

if __name__ == "__main__":
    success = populate_database()
    if success:
        print("✅ Base de datos poblada correctamente")
        sys.exit(0)
    else:
        print("❌ Error poblando la base de datos")
        sys.exit(1)