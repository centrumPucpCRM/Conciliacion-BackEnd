from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Oportunidad(Base):
    __tablename__ = 'oportunidad'
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    documentoIdentidad = Column(String(255))
    correo = Column(String(255))
    telefono = Column(String(50))
    etapaDeVentas = Column(String(255))
    descuento = Column(Float)
    monto = Column(Float)
    becado = Column(Boolean, default=False)
    partyNumber = Column(Integer)
    conciliado = Column(Boolean, default=False)
    posibleAtipico = Column(Boolean, default=False)
    idPropuesta = Column(Integer, ForeignKey('propuesta.id'))
    propuesta = relationship('Propuesta')
    idPrograma = Column(Integer, ForeignKey('programa.id'))
    programa = relationship('Programa')
    idTipoCambio = Column(Integer, ForeignKey('tipo_cambio.id'))
    tipoCambio = relationship('TipoCambio')
    montoPropuesto = Column(Float)
    etapaVentaPropuesta = Column(String(255))
    eliminado = Column(Boolean, default=False)
