from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import pymysql
import logging

DATABASE_URL = "mysql+pymysql://admin:5QeWOnjYCvEA2lOtkCfc@conciliaciondb.ci1gweq8a0j0.us-east-1.rds.amazonaws.com:3306/conciliacion"

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
