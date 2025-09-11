from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from ..database import Base

class SolicitudPropuestaOportunidad(Base):
    __tablename__ = "solicitud_propuesta_oportunidad"
    id = Column(Integer, primary_key=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"))
    id_propuesta_oportunidad = Column(Integer, ForeignKey("propuesta_oportunidad.id_propuesta_oportunidad"))
    monto_propuesto = Column(DECIMAL(18, 2), nullable=True)
    monto_objetado = Column(DECIMAL(18, 2), nullable=True)
