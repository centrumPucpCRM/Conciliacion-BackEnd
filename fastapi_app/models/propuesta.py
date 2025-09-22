from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, CheckConstraint
from sqlalchemy.orm import validates
from ..database import Base

from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base



from sqlalchemy import Column, Integer, String, Date, Enum
from sqlalchemy.orm import relationship
from fastapi_app.database import Base
import enum

class TipoDePropuesta(Base):
    __tablename__ = 'tipo_de_propuesta'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), unique=True)

class EstadoPropuesta(Base):
    __tablename__ = 'estado_propuesta'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), unique=True)

class Propuesta(Base):
    __tablename__ = 'propuesta'
    id = Column(Integer, primary_key=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String(255))
    tipoDePropuesta_id = Column(Integer, ForeignKey('tipo_de_propuesta.id'))
    estadoPropuesta_id = Column(Integer, ForeignKey('estado_propuesta.id'))
    creadoEn = Column(Date)
    tipoDePropuesta = relationship('TipoDePropuesta')
    estadoPropuesta = relationship('EstadoPropuesta')
