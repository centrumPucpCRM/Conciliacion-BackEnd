from sqlalchemy import Column, Integer, String, ForeignKey, Date, Enum
from sqlalchemy.orm import relationship
from fastapi_app.database import Base
from .associations import propuesta_cartera

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
    carteras = relationship('Cartera', secondary=propuesta_cartera, back_populates='propuestas')
