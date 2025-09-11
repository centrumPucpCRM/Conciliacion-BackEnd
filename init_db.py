"""
Script para inicializar la base de datos.
Este script crea todas las tablas en el orden correcto, respetando las dependencias entre ellas.
"""
import os
import sys

# Añadir el directorio raíz del proyecto al path de Python
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi_app.database import engine, Base, SessionLocal
import importlib

# Importar todos los modelos para que se registren en Base.metadata
import fastapi_app.models.rol_permiso
import fastapi_app.models.usuario
import fastapi_app.models.cartera
import fastapi_app.models.programa
import fastapi_app.models.oportunidad
import fastapi_app.models.propuesta
import fastapi_app.models.propuesta_oportunidad
import fastapi_app.models.propuesta_programa
import fastapi_app.models.tipo_cambio
import fastapi_app.models.log
import fastapi_app.models.conciliacion
import fastapi_app.models.conciliacion_programa
import fastapi_app.models.solicitud
import fastapi_app.models.solicitud_propuesta_oportunidad
import fastapi_app.models.solicitud_propuesta_programa
import fastapi_app.models.usuario_cartera

def init_db():
    """Inicializa la base de datos creando todas las tablas."""
    print("Creando todas las tablas...")
    
    # Crear todas las tablas
    Base.metadata.drop_all(engine)  # Eliminar todas las tablas existentes
    Base.metadata.create_all(engine)  # Crear todas las tablas nuevamente
    
    print("¡Base de datos inicializada correctamente!")

if __name__ == "__main__":
    init_db()
