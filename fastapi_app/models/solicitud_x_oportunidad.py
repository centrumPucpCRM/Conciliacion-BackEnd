from sqlalchemy import Column, Integer, Float, ForeignKey
from fastapi_app.database import Base

class SolicitudXOportunidad(Base):
    __tablename__ = 'solicitud_x_oportunidad'
    id = Column(Integer, primary_key=True)
    idOportunidad = Column(Integer, ForeignKey('oportunidad.id'))
    idSolicitud = Column(Integer, ForeignKey('solicitud.id'))
    montoPropuesto = Column(Float)
    montoObjetado = Column(Float)