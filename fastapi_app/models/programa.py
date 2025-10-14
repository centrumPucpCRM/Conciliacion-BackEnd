from sqlalchemy import Boolean, Column, Date, Float, Integer, String
from ..database import Base

from sqlalchemy import Column, Integer, String, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base

class Programa(Base):
    __tablename__ = 'programa'
    id = Column(Integer, primary_key=True)
    codigo = Column(String(255))
    nombre = Column(String(255))
    fechaDeInaguracion = Column(Date)
    moneda = Column(String(255))
    precioDeLista = Column(Float)
    metaDeVenta = Column(Float)
    metaDeAlumnos = Column(Integer)
    puntoMinimoApertura = Column(Integer)
    subdireccion = Column(String(255))
    cartera = Column(String(255))
    comentario = Column(String(255))
    mes = Column(Integer)
    idPropuesta = Column(Integer, ForeignKey('propuesta.id'))
    propuesta = relationship('Propuesta')
    idJefeProducto = Column(Integer, ForeignKey('usuario.id'))
    jefeProducto = relationship('Usuario')
    idTipoCambio = Column(Integer, ForeignKey('tipo_cambio.id'))
    tipoCambio = relationship('TipoCambio')
    fechaInaguracionPropuesta = Column(Date)
    mesPropuesto = Column(Integer)
    noAperturar = Column(Boolean,default=False)
    noCalcular = Column(Boolean,default=False)