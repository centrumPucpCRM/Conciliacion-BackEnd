from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class EstadoConciliacion(Base):
    __tablename__ = 'estado_conciliacion'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), unique=True)

class Conciliacion(Base):
    __tablename__ = 'conciliacion'
    id = Column(Integer, primary_key=True)
    fechaConciliacion = Column(Date)
    estadoConciliacion_id = Column(Integer, ForeignKey('estado_conciliacion.id'))
    estadoConciliacion = relationship('EstadoConciliacion')
