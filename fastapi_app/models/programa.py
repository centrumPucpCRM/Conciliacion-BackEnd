from sqlalchemy import Column, Date, Float, Integer, String
from ..database import Base

class Programa(Base):
    __tablename__ = "programa"
    id_programa = Column(Integer, primary_key=True, index=True)
    id_jefe_producto = Column(Integer, nullable=False)
    codigo = Column(String(100), nullable=False)
    nombre = Column(String(200), nullable=False)
    fecha_de_inicio = Column(Date, nullable=False)
    fecha_de_inauguracion = Column(Date, nullable=False)
    fecha_ultima_postulante = Column(Date)
    moneda = Column(String(50), nullable=False)
    meta_venta = Column(Integer, nullable=True)
    meta_alumnos = Column(Integer, nullable=True)
    punto_minimo_apertura = Column(Integer, nullable=True)
    cartera = Column(String(100), nullable=True)
    id_propuesta = Column(Integer, nullable=True)
    precio_lista = Column(Float, nullable=False)